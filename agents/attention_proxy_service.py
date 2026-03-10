"""Source-attribution service using TF-IDF cosine similarity.

Acts as a proxy for cross-attention weights: given an answer split into
sentences and a set of source citations, computes how similar each answer
sentence is to each source document.

Uses scikit-learn's TfidfVectorizer (lightweight, no GPU needed).
Never calls Groq.
"""

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_logger = logging.getLogger(__name__)

# ── In-memory cache ──────────────────────────────────────────────────
_cache: Dict[str, Dict[str, Any]] = {}
_MAX_CACHE = 256


def _cache_key(sentences: List[str], citations: List[Dict[str, str]]) -> str:
    raw = "|".join(sentences) + "||" + "|".join(c.get("name", "") for c in citations)
    return hashlib.sha256(raw.encode()).hexdigest()


# ── Sentence splitting ───────────────────────────────────────────────
_SENT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z])")


def split_sentences(text: str) -> List[str]:
    """Naive sentence splitter on period/!/? followed by uppercase."""
    parts = _SENT_RE.split(text.strip())
    return [s.strip() for s in parts if s.strip()]


# ── Singleton vectorizer kept in memory ──────────────────────────────
_vectorizer: TfidfVectorizer | None = None


def _get_vectorizer() -> TfidfVectorizer:
    global _vectorizer
    if _vectorizer is None:
        _vectorizer = TfidfVectorizer(
            max_features=10000,
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
    return _vectorizer


def compute_attention_map(
    answer_sentences: List[str],
    citation_texts: List[Dict[str, str]],
) -> Dict[str, Any]:
    """Compute normalised similarity scores between answer sentences and sources.

    Parameters
    ----------
    answer_sentences : list[str]
        Sentences of the generated answer.
    citation_texts : list[dict]
        Each dict must have ``name``, ``url``, and ``text`` (the source content).

    Returns
    -------
    dict with key ``sentence_source_map`` — a list of dicts, one per sentence.
    """
    key = _cache_key(answer_sentences, citation_texts)
    if key in _cache:
        return _cache[key]

    source_bodies = [c.get("text", c.get("name", "")) for c in citation_texts]
    if not answer_sentences or not source_bodies:
        result: Dict[str, Any] = {"sentence_source_map": []}
        return result

    # Fit vectorizer on all texts together
    vectorizer = TfidfVectorizer(
        max_features=10000,
        stop_words="english",
        ngram_range=(1, 2),
        sublinear_tf=True,
    )
    all_texts = answer_sentences + source_bodies
    tfidf_matrix = vectorizer.fit_transform(all_texts)

    n_sent = len(answer_sentences)
    sent_vectors = tfidf_matrix[:n_sent]
    source_vectors = tfidf_matrix[n_sent:]

    sim_matrix = cosine_similarity(sent_vectors, source_vectors)  # (n_sent, n_sources)

    # Normalise each row to [0, 1]
    row_maxes = sim_matrix.max(axis=1, keepdims=True)
    row_maxes[row_maxes == 0] = 1.0  # avoid division by zero
    norm_matrix = sim_matrix / row_maxes

    sentence_source_map = []
    for i, sent in enumerate(answer_sentences):
        sources = []
        for j, cit in enumerate(citation_texts):
            sources.append({
                "name": cit.get("name", ""),
                "url": cit.get("url", ""),
                "score": round(float(norm_matrix[i, j]), 4),
            })
        # Sort by score descending
        sources.sort(key=lambda s: s["score"], reverse=True)
        sentence_source_map.append({
            "sentence": sent,
            "sources": sources,
        })

    result = {"sentence_source_map": sentence_source_map}

    # Cache management
    if len(_cache) >= _MAX_CACHE:
        oldest = next(iter(_cache))
        del _cache[oldest]
    _cache[key] = result

    return result
