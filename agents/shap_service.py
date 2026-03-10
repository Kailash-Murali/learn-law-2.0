"""SHAP-based confidence breakdown service for bad-law findings.

Trains a lightweight LogisticRegression on binary legal features extracted
from law text, then uses shap.LinearExplainer to attribute the confidence
prediction to individual features.

This module never calls Groq — all computation is local.
"""

import re
import logging
from typing import Any, Dict, List

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
import shap

_logger = logging.getLogger(__name__)

# ── Feature definitions ───────────────────────────────────────────────
FEATURE_NAMES: List[str] = [
    "has_explicit_struck_down_phrase",
    "has_sc_citation",
    "has_year",
    "ik_verified",
    "has_section_number",
    "has_constitution_article",
    "has_enforcement_stay_phrase",
    "is_dicta",
]

FEATURE_DISPLAY: Dict[str, str] = {
    "has_explicit_struck_down_phrase": "Explicit 'struck down' language",
    "has_sc_citation": "SC citation present",
    "has_year": "Year of judgment cited",
    "ik_verified": "IK verified",
    "has_section_number": "Section number cited",
    "has_constitution_article": "Constitutional Article cited",
    "has_enforcement_stay_phrase": "Enforcement stay language",
    "is_dicta": "Discussion only (dicta)",
}

_STRUCK_PHRASES = re.compile(
    r"struck\s+down|declared\s+unconstitutional|struck\s+as\s+void|ultra\s+vires|read\s+down|"
    r"quashed|set\s+aside|nullified|held\s+unconstitutional",
    re.IGNORECASE,
)
_STAY_PHRASES = re.compile(
    r"stayed|stay\s+of\s+enforcement|suspended|moratorium|abeyance",
    re.IGNORECASE,
)
_SC_CITATION = re.compile(
    r"Supreme\s+Court|S\.?C\.?R?\b|\bSCC\b|\bAIR\s+\d{4}\s+SC\b",
    re.IGNORECASE,
)
_YEAR_RE = re.compile(r"\b(1[89]\d{2}|20[0-2]\d)\b")
_SECTION_RE = re.compile(r"\bSection\s+\d+[A-Z]?\b", re.IGNORECASE)
_ARTICLE_RE = re.compile(r"\bArticle\s+\d+[A-Z]?\b", re.IGNORECASE)


def extract_features(law_text: str, context: str = "") -> Dict[str, float]:
    """Extract binary features from law_text + context."""
    combined = f"{law_text} {context}"
    return {
        "has_explicit_struck_down_phrase": float(bool(_STRUCK_PHRASES.search(combined))),
        "has_sc_citation": float(bool(_SC_CITATION.search(combined))),
        "has_year": float(bool(_YEAR_RE.search(combined))),
        "ik_verified": float("indiankanoon" in combined.lower() or "verified" in combined.lower()),
        "has_section_number": float(bool(_SECTION_RE.search(combined))),
        "has_constitution_article": float(bool(_ARTICLE_RE.search(combined))),
        "has_enforcement_stay_phrase": float(bool(_STAY_PHRASES.search(combined))),
        "is_dicta": float(
            "discussion only" in combined.lower()
            or "dicta" in combined.lower()
            or "obiter" in combined.lower()
        ),
    }


# ── Seed training data (curated from known Indian cases) ─────────────
# Each row: [features in FEATURE_NAMES order], label
_SEED_X = np.array([
    # High confidence: clear struck-down with SC citation, year, section, verified
    [1, 1, 1, 1, 1, 0, 0, 0],  # Section 66A IT Act — Shreya Singhal
    [1, 1, 1, 1, 1, 1, 0, 0],  # Section 303 IPC — Mithu v State of Punjab
    [1, 1, 1, 1, 0, 1, 0, 0],  # TADA struck down
    [1, 1, 1, 0, 1, 0, 0, 0],  # POTA repealed
    [1, 1, 1, 1, 1, 1, 0, 0],  # Section 497 IPC struck down
    # Medium confidence: some indicators present
    [0, 1, 1, 0, 1, 0, 0, 0],  # SC citation + year + section but no struck phrase
    [1, 0, 1, 0, 1, 0, 0, 0],  # Struck phrase + year + section but no SC
    [0, 1, 1, 1, 0, 1, 0, 0],  # SC + year + verified + article but no struck phrase
    [1, 0, 0, 1, 1, 0, 0, 0],  # Struck + verified + section
    [0, 1, 0, 0, 1, 1, 1, 0],  # SC + section + article + stay
    # Low confidence: few indicators, or dicta
    [0, 0, 1, 0, 0, 0, 0, 1],  # Year only + dicta
    [0, 0, 0, 0, 1, 0, 0, 1],  # Section only + dicta
    [0, 0, 1, 0, 0, 0, 0, 0],  # Year only
    [0, 0, 0, 0, 0, 0, 1, 1],  # Stay phrase + dicta
    [0, 0, 0, 0, 0, 1, 0, 1],  # Article + dicta
], dtype=float)

_SEED_Y = np.array([
    "high", "high", "high", "high", "high",
    "medium", "medium", "medium", "medium", "medium",
    "low", "low", "low", "low", "low",
])


class ShapConfidenceService:
    """Singleton service trained once, reused across requests."""

    def __init__(self) -> None:
        self._le = LabelEncoder()
        self._le.fit(["high", "low", "medium"])
        y_encoded = self._le.transform(_SEED_Y)

        self._model = LogisticRegression(max_iter=500, random_state=42)
        self._model.fit(_SEED_X, y_encoded)

        self._explainer = shap.LinearExplainer(
            self._model,
            _SEED_X,
            feature_names=FEATURE_NAMES,
        )
        _logger.info("ShapConfidenceService initialised (classes=%s)", list(self._le.classes_))

    def predict_confidence(self, law_text: str, context: str = "") -> str:
        """Return predicted confidence label."""
        feats = extract_features(law_text, context)
        x = np.array([[feats[f] for f in FEATURE_NAMES]])
        pred_idx = self._model.predict(x)[0]
        return str(self._le.inverse_transform([pred_idx])[0])

    def explain(self, law_text: str, context: str = "") -> Dict[str, Any]:
        """Return full SHAP breakdown."""
        feats = extract_features(law_text, context)
        x = np.array([[feats[f] for f in FEATURE_NAMES]])

        predicted_class_idx = int(self._model.predict(x)[0])
        predicted_label = str(self._le.inverse_transform([predicted_class_idx])[0])

        shap_values = self._explainer.shap_values(x)  # shape: (1, n_features) per class or (n_classes, 1, n_features)

        # shap_values may be list-of-arrays (one per class) or single array
        if isinstance(shap_values, list):
            sv = np.array(shap_values[predicted_class_idx])[0]
            base = float(self._explainer.expected_value[predicted_class_idx])
        else:
            sv = np.array(shap_values)[0]
            base = float(
                self._explainer.expected_value[predicted_class_idx]
                if hasattr(self._explainer.expected_value, "__getitem__")
                else self._explainer.expected_value
            )

        features_out = []
        for i, fname in enumerate(FEATURE_NAMES):
            features_out.append({
                "name": FEATURE_DISPLAY.get(fname, fname),
                "value": bool(feats[fname]),
                "shap_value": round(float(sv[i]), 4),
            })

        # Sort by absolute SHAP contribution descending
        features_out.sort(key=lambda f: abs(f["shap_value"]), reverse=True)

        return {
            "base_value": round(base, 4),
            "features": features_out,
            "predicted_confidence": predicted_label,
        }


# Module-level lazy singleton
_instance: ShapConfidenceService | None = None


def get_shap_service() -> ShapConfidenceService:
    global _instance
    if _instance is None:
        _instance = ShapConfidenceService()
    return _instance
