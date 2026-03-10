"""Surrogate Decision Tree service for the XAI validation logic.

Trains a shallow DecisionTreeClassifier that approximates the
XAIValidationAgent's ``is_grounded`` prediction, then serialises
the decision path as a JSON graph for frontend rendering.

Never calls Groq — all computation is local.
"""

import logging
from typing import Any, Dict, List

import numpy as np
from sklearn.tree import DecisionTreeClassifier

_logger = logging.getLogger(__name__)

# ── Feature schema ────────────────────────────────────────────────────
FEATURE_NAMES: List[str] = [
    "citation_count",
    "verified_citation_ratio",
    "bad_law_count",
    "article_ref_count",
    "statute_count",
    "ik_available",
    "springer_paper_count",
]

FEATURE_DISPLAY: Dict[str, str] = {
    "citation_count": "Total citations",
    "verified_citation_ratio": "Verified citation ratio",
    "bad_law_count": "Repealed/bad laws found",
    "article_ref_count": "Constitutional article refs",
    "statute_count": "Statute citations",
    "ik_available": "IK API available",
    "springer_paper_count": "Springer papers",
}

# ── Seed training data ───────────────────────────────────────────────
# [citation_count, verified_ratio, bad_law_count, article_refs, statutes, ik_avail, springer]
_SEED_X = np.array([
    # Grounded (is_grounded = True)
    [4, 1.0, 0, 3, 2, 1, 2],
    [3, 0.67, 0, 2, 1, 1, 1],
    [2, 1.0, 1, 1, 1, 1, 0],
    [5, 0.8, 0, 4, 3, 1, 3],
    [1, 1.0, 0, 2, 1, 1, 0],
    [3, 1.0, 0, 1, 2, 1, 1],
    [2, 0.5, 0, 3, 2, 1, 2],
    [4, 0.75, 1, 2, 2, 1, 1],
    [0, 0.0, 0, 2, 1, 0, 0],  # no citations but articles + statutes
    [1, 1.0, 0, 1, 0, 1, 1],
    # Not grounded (is_grounded = False)
    [0, 0.0, 0, 0, 0, 1, 0],
    [2, 0.0, 2, 0, 0, 1, 0],
    [1, 0.0, 1, 0, 0, 1, 0],
    [0, 0.0, 0, 0, 0, 0, 0],
    [3, 0.0, 3, 0, 0, 1, 0],
    [0, 0.0, 1, 0, 0, 0, 0],
    [1, 0.0, 0, 0, 0, 1, 0],  # one citation but unverified
    [0, 0.0, 0, 1, 0, 0, 0],  # minimal article ref, no IK
], dtype=float)

_SEED_Y = np.array([
    1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
    0, 0, 0, 0, 0, 0, 0, 0,
])


class SurrogateTreeService:
    """Singleton service for surrogate decision tree explanations."""

    def __init__(self) -> None:
        self._tree = DecisionTreeClassifier(max_depth=4, random_state=42)
        self._tree.fit(_SEED_X, _SEED_Y)
        _logger.info("SurrogateTreeService initialised (depth=%d)", self._tree.get_depth())

    def explain(self, validation_features: Dict[str, float]) -> Dict[str, Any]:
        """Return the decision path as a node/edge graph."""
        x = np.array([[validation_features.get(f, 0.0) for f in FEATURE_NAMES]])

        prediction = bool(self._tree.predict(x)[0])
        proba = self._tree.predict_proba(x)[0]
        confidence = float(proba[1] if prediction else proba[0])

        # Extract decision path
        path_indicator = self._tree.decision_path(x)
        node_indices = path_indicator.indices.tolist()

        tree_ = self._tree.tree_
        nodes = []
        edges = []

        for idx, node_id in enumerate(node_indices):
            feature_idx = tree_.feature[node_id]
            threshold = tree_.threshold[node_id]
            is_leaf = feature_idx < 0  # -2 means leaf

            if is_leaf:
                # Leaf: determine class
                class_counts = tree_.value[node_id][0]
                predicted_class = int(np.argmax(class_counts))
                node_info = {
                    "id": node_id,
                    "feature": "",
                    "threshold": 0.0,
                    "direction": "",
                    "is_leaf": True,
                    "value": "Grounded" if predicted_class == 1 else "Not Grounded",
                }
            else:
                fname = FEATURE_NAMES[feature_idx] if feature_idx < len(FEATURE_NAMES) else f"feature_{feature_idx}"
                display_name = FEATURE_DISPLAY.get(fname, fname)

                # Determine direction: did we go left (<=) or right (>)?
                if idx + 1 < len(node_indices):
                    next_node = node_indices[idx + 1]
                    left_child = tree_.children_left[node_id]
                    direction = "left" if next_node == left_child else "right"
                else:
                    direction = ""

                node_info = {
                    "id": node_id,
                    "feature": display_name,
                    "threshold": round(float(threshold), 2),
                    "direction": direction,
                    "is_leaf": False,
                    "value": "",
                }

            nodes.append(node_info)

            # Edge to next node
            if idx + 1 < len(node_indices):
                edges.append({
                    "from": node_id,
                    "to": node_indices[idx + 1],
                })

        return {
            "nodes": nodes,
            "edges": edges,
            "prediction": prediction,
            "confidence": round(confidence, 4),
        }


_instance: SurrogateTreeService | None = None


def get_surrogate_service() -> SurrogateTreeService:
    global _instance
    if _instance is None:
        _instance = SurrogateTreeService()
    return _instance
