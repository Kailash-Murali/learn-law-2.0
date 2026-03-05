"""XAIValidationAgent - Enforces anti-hallucination measures through cross-verification.

This agent validates legal research via Indian Kanoon API cross-verification,
extracting citations, checking for repealed laws, and computing hallucination risk.
"""

import json
import re
import uuid
import requests
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .base_agent import LegalAgent, _remove_markdown_formatting
from config import Config

_logger = logging.getLogger(__name__)


class XAIValidationAgent(LegalAgent):
    """
    XAI Validation Agent — Enforces four anti-hallucination measures:
      1. Factual Grounding  : every claim must be anchored to a real Indian legal source
      2. Source Citation    : requires explicit citations (case name / Article / Section)
      3. Scope Limiting     : restricts output to summarisation/search — no invented law
      4. User Feedback      : stamps every response with a unique ID so users can report issues
    """

    # Regex patterns for constitutional articles/sections (verified by rule, not IK)
    ARTICLE_PATTERNS = [
        r'\bArticle\s+\d+[A-Z]?(?:\(\d+\))?\b',   # Article 21, Article 14A, Article 32(1)
        r'\bSection\s+\d+[A-Z]?\b',                 # Section 302
    ]

    # Regex patterns for Indian statute/act citations
    STATUTE_PATTERNS = [
        r'\bThe\s+[A-Z][\w\s]+Act,?\s+\d{4}\b',              # "The XYZ Act, 1950"
        r'\b(?:Indian\s+Penal\s+Code|Code\s+of\s+Criminal\s+Procedure|Code\s+of\s+Civil\s+Procedure)(?:,?\s+\d{4})?\b',
        r'\b(?:IPC|CrPC|CPC)\b',                              # Common shorthand
    ]

    # Rule-based registry of repealed / struck-down / bad Indian laws.
    # Keys are REGEX PATTERNS (not simple substrings) with word boundaries to avoid false positives.
    # EVALUATION: Rule-based is unambiguously correct for most critical laws.
    # Only include laws that are DEFINITELY repealed or struck down.
    REPEALED_OR_BAD_LAWS: Dict[str, tuple] = {
        # Most critical and unambiguous bad laws
        r'\bsection\s+66a(?:\s+|$)': (
            "Section 66A of the IT Act, 2000",
            "Struck down as unconstitutional — Shreya Singhal v. Union of India (2015)",
        ),
        r'\bsection\s+124a(?:\s+ipc)?(?:\s+|$)': (
            "Section 124A IPC — Sedition",
            "SC stayed all prosecutions in 2022 (S.G. Vombatkere v. UoI); under constitutional review",
        ),
    }
    
    # DEPRECATED: Removed overly aggressive patterns that caused false positives:
    # - "tada", "pota" — too short, match in unrelated contexts
    # - "section 377 ipc" — partially struck down (affects consenting adults only), not fully repealed
    # - "imdt act" — less commonly cited, risk of false positives
    # - "prevention of terrorism ordinance" — too vague

    def __init__(self):
        super().__init__(
            name="XAIValidationAgent",
            system_prompt="""You are an Indian legal citation extractor.
Given legal research text, extract the names of all judicial cases cited.
Return ONLY a JSON array of strings — no explanation, no markdown.
Example: ["Maneka Gandhi v. Union of India (1978)", "A.K. Kraipak v. Union of India (1970)"]
If no cases are cited, return: []"""
        )

    def _ik_search(self, case_name: str) -> Optional[Dict[str, str]]:
        """
        Search Indian Kanoon for a case citation and return the best-matching
        result.  Uses quoted party names and scans top results for a title
        match instead of blindly returning docs[0].

        Returns ``{"title": ..., "url": ...}`` or *None*.
        """
        token = Config.IK_API_TOKEN
        if not token:
            return None

        # ── Parse party names and year from the citation ──────────────
        parts = re.split(
            r'\s+v\.?\s+|\s+vs\.?\s+', case_name, maxsplit=1, flags=re.IGNORECASE
        )
        party1 = re.sub(r'\(?\d{4}\)?', '', parts[0]).strip()
        party2 = re.sub(r'\(?\d{4}\)?', '', parts[1]).strip() if len(parts) > 1 else None
        year_m = re.search(r'\b(1[89]\d{2}|20[0-2]\d)\b', case_name)
        year   = year_m.group(1) if year_m else None

        party1_lower = party1.lower()

        # ── Build up to 2 query strategies ────────────────────────────
        queries: List[str] = []
        if year:
            # Best strategy: party1 + year  (avoids party2 abbreviation issues)
            queries.append(f'"{party1}" {year}')
        if party2:
            queries.append(f'"{party1}" "{party2}"')
        if not queries:
            queries.append(f'"{party1}"')

        # ── Try each query, return on first title-matched hit ─────────
        for query in queries:
            try:
                resp = requests.post(
                    "https://api.indiankanoon.org/search/",
                    data={"formInput": query, "pagenum": 0},
                    headers={"Authorization": f"Token {token}"},
                    timeout=8,
                )
                if resp.status_code != 200:
                    continue

                docs = resp.json().get("docs", [])

                for d in docs[:10]:
                    title_raw = d.get("title", "")
                    title_clean = (
                        title_raw.replace("<b>", "").replace("</b>", "")
                    )
                    tid = d.get("tid")
                    if not tid:
                        continue

                    # Accept only if the first party name appears in the title
                    if party1_lower in title_clean.lower():
                        return {
                            "title": title_clean,
                            "url": f"https://indiankanoon.org/doc/{tid}/",
                        }
            except Exception:
                continue

        return None

    def _ik_statute_search(self, statute_name: str) -> Optional[Dict[str, str]]:
        """
        Search Indian Kanoon for a statute / act and return the first matching
        document whose title shares key capitalised words with *statute_name*.
        Returns ``{"title": ..., "url": ...}`` or *None*.
        """
        token = Config.IK_API_TOKEN
        if not token:
            return None
        # Build query from the statute name, quoted for precision
        query = f'"{statute_name.strip()}"'
        try:
            resp = requests.post(
                "https://api.indiankanoon.org/search/",
                data={"formInput": query, "pagenum": 0},
                headers={"Authorization": f"Token {token}"},
                timeout=8,
            )
            if resp.status_code != 200:
                return None
            docs = resp.json().get("docs", [])
            # Key words from the statute name (skip generic words)
            _SKIP = {"the", "of", "and", "for", "in", "an", "a", "act", "code"}
            key_words = [
                w.lower() for w in re.findall(r'[A-Za-z]{3,}', statute_name)
                if w.lower() not in _SKIP
            ]
            for d in docs[:8]:
                title_clean = d.get("title", "").replace("<b>", "").replace("</b>", "")
                tid = d.get("tid")
                if not tid or not key_words:
                    continue
                # Accept if at least half the key words appear in the title
                matches = sum(1 for kw in key_words if kw in title_clean.lower())
                if matches >= max(1, len(key_words) // 2):
                    return {
                        "title": title_clean,
                        "url": f"https://indiankanoon.org/doc/{tid}/",
                    }
        except Exception:
            pass
        return None

    def validate(self, query: str, research: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate research via Indian Kanoon API cross-verification.

        Steps:
          1. Regex extracts Article/Section refs (always reliable).
          2. Regex extracts statute/act citations.
          3. Rule-based scan for repealed / struck-down laws.
          4. LLM extracts case names; each is looked up on Indian Kanoon.
          5. Statutes are looked up on Indian Kanoon.
          6. Hallucination risk = f(unverified cases, bad laws, missing statutes).
        """
        research_content = research.get("research_content", "")

        self.log_reasoning_step(
            "validation_started",
            {
                "action": "extracting_citations_for_ik_verification",
                "content_length": len(research_content),
                "rationale": "Cross-verify case citations against Indian Kanoon API"
            }
        )

        # ── Step 1a: Extract Article/Section refs by regex (always reliable) ──
        article_refs: List[str] = []
        for pat in self.ARTICLE_PATTERNS:
            article_refs.extend(re.findall(pat, research_content, re.IGNORECASE))
        article_refs = sorted(set(article_refs))

        # ── Step 1b: Extract statute/act citations by regex (rule-based) ─────
        statute_refs: List[str] = []
        for pat in self.STATUTE_PATTERNS:
            statute_refs.extend(re.findall(pat, research_content, re.IGNORECASE))
        statute_refs = sorted(set(s.strip() for s in statute_refs if len(s.strip()) > 3))

        # ── Step 1c: Bad-law scan (regex-based, accurate matching) ──────────────
        # Uses regex patterns with word boundaries instead of simple substring matching
        # to avoid false positives (e.g., "section 66a" shouldn't match in "section 66 approach")
        bad_laws_found: List[Dict[str, str]] = []
        for pattern, (display_name, reason) in self.REPEALED_OR_BAD_LAWS.items():
            try:
                if re.search(pattern, research_content, re.IGNORECASE):
                    bad_laws_found.append({"law": display_name, "reason": reason})
            except Exception:
                # Skip if regex is invalid
                pass

        # ── Step 2: Ask LLM to extract case names ────────────────────────
        raw = self.call_llm(
            f"Extract all case names from this text:\n\n{research_content[:2000]}",
            log_reasoning=False
        )
        extracted_cases: List[str] = []
        try:
            bracket_start = raw.index("[")
            bracket_end   = raw.rindex("]") + 1
            extracted_cases = json.loads(raw[bracket_start:bracket_end])
            if not isinstance(extracted_cases, list):
                extracted_cases = []
        except Exception:
            # fallback: grab any "X v. Y" patterns
            extracted_cases = re.findall(
                r'[A-Z][\w\s&.]+\bv\.\s+[A-Z][\w\s&.]+(?:\(\d{4}\))?',
                research_content
            )[:8]
        extracted_cases = [c.strip() for c in extracted_cases if isinstance(c, str) and c.strip()][:10]

        # ── Step 3: Cross-verify each case on Indian Kanoon ──────────────
        ik_available      = bool(Config.IK_API_TOKEN)
        citation_links: Dict[str, Optional[str]] = {}   # case → URL or None
        verified: List[str]   = []
        unverified: List[str] = []

        for case in extracted_cases:
            hit = self._ik_search(case)
            if hit:
                verified.append(case)
                citation_links[case] = hit["url"]
            else:
                unverified.append(case)
                citation_links[case] = None

        # ── Step 3b: Verify statutes on Indian Kanoon ─────────────────────
        statute_links: Dict[str, Optional[str]] = {}
        if ik_available:
            for statute in statute_refs[:6]:   # cap at 6 to limit API calls
                hit = self._ik_statute_search(statute)
                statute_links[statute] = hit["url"] if hit else None

        # ── Step 4: Compute hallucination risk ───────────────────────────
        total = len(extracted_cases)
        flags: List[str] = []

        # 4a — case citation risk
        if total == 0:
            is_grounded = bool(article_refs) or bool(statute_refs)
            risk        = 0.25 if (article_refs or statute_refs) else 0.65
            if not article_refs and not statute_refs:
                flags.append("No case citations, article references, or statute citations detected")
        elif ik_available:
            unverified_ratio = len(unverified) / total
            risk             = round(unverified_ratio * 0.85, 2)
            is_grounded      = len(verified) > 0 or bool(article_refs) or bool(statute_refs)
            for c in unverified[:3]:
                flags.append(f"Case not found on Indian Kanoon: {c}")
        else:
            risk        = 0.30
            is_grounded = total > 0 or bool(article_refs) or bool(statute_refs)
            flags.append("IK_API_TOKEN not set — Indian Kanoon verification skipped")

        # 4b — statute-absent penalty
        if not statute_refs and not article_refs:
            risk = min(1.0, risk + 0.10)
            flags.append("No statute or constitutional article citations — answer may lack legal grounding")

        # 4c — bad-law penalty (rule-based, each bad law adds 0.15 to risk)
        for bl in bad_laws_found:
            risk = min(1.0, risk + 0.15)
            flags.append(f"BAD LAW CITED: {bl['law']} — {bl['reason']}")

        risk = round(risk, 2)
        feedback_id = str(uuid.uuid4())[:8].upper()

        result = {
            "feedback_id"      : feedback_id,
            "is_grounded"      : is_grounded,
            "citation_links"   : citation_links,     # {case_name: IK_url | None}
            "statute_links"    : statute_links,      # {statute_name: IK_url | None}
            "bad_laws_found"   : bad_laws_found,     # [{"law": ..., "reason": ...}]
            "article_refs"     : article_refs,
            "statute_refs"     : statute_refs,
            "verified_on_ik"   : verified,
            "unverified_on_ik" : unverified,
            "ik_available"     : ik_available,
            "citations_found"  : list(citation_links.keys()) + article_refs + statute_refs,
            "hallucination_risk": risk,
            "validated_content": research_content,
            "flags"            : flags,
            "scope_violations" : [],
            "original_content" : research_content,
            "status"           : "validated"
        }

        risk_label = (
            "LOW"    if risk < 0.35 else
            "MEDIUM" if risk < 0.65 else
            "HIGH"
        )

        self.log_reasoning_step(
            "validation_completed",
            {
                "action"              : "ik_cross_verification_done",
                "cases_extracted"     : total,
                "verified_on_ik"      : len(verified),
                "unverified_on_ik"    : len(unverified),
                "statutes_extracted"  : len(statute_refs),
                "statutes_verified"   : sum(1 for u in statute_links.values() if u),
                "bad_laws_found"      : len(bad_laws_found),
                "ik_available"        : ik_available,
                "hallucination_risk"  : risk,
                "risk_label"          : risk_label,
                "is_grounded"         : is_grounded,
                "feedback_id"         : feedback_id,
                "rationale"           : "Cases + statutes cross-verified on IK; bad-law rule scan applied"
            }
        )

        return result
