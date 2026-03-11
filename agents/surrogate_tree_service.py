"""Surrogate Decision Tree service using LLM-extracted legal features.

Builds a per-request decision tree by:
1. Taking boolean legal features from extract_legal_features()
2. Generating synthetic perturbations (flip booleans)
3. Labelling via Groq oracle
4. Training a shallow DecisionTreeClassifier
5. Serialising the full tree structure for frontend rendering
"""

import json
import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from groq import Groq

from config import Config

_logger = logging.getLogger(__name__)

# ── Feature schema (boolean features from extract_legal_features) ─────
FEATURE_NAMES: List[str] = [
    "is_mandatory_sentence",
    "allows_judicial_discretion",
    "cites_fundamental_rights",
    "is_central_legislation",
    "has_criminal_provision",
]

FEATURE_DISPLAY: Dict[str, str] = {
    "is_mandatory_sentence": "Mandatory sentence",
    "allows_judicial_discretion": "Judicial discretion",
    "cites_fundamental_rights": "Fundamental Rights cited",
    "is_central_legislation": "Central legislation",
    "has_criminal_provision": "Criminal provision",
}


def _generate_perturbations(base: Dict[str, Any], n: int = 150) -> pd.DataFrame:
    """Generate n synthetic rows by randomly flipping boolean features."""
    rng = np.random.default_rng(seed=42)
    base_row = np.array([int(bool(base.get(f, 0))) for f in FEATURE_NAMES], dtype=int)
    rows = np.tile(base_row, (n, 1))
    flip_mask = rng.random((n, len(FEATURE_NAMES))) < 0.4
    rows = np.where(flip_mask, 1 - rows, rows)
    # Ensure the original row is included as the first row
    rows[0] = base_row
    return pd.DataFrame(rows, columns=FEATURE_NAMES)


def _label_with_groq(X_df: pd.DataFrame) -> np.ndarray:
    """Batch-label all perturbation rows via a single Groq prompt."""
    try:
        # Build compact CSV table
        header = ",".join(FEATURE_NAMES)
        csv_rows = "\n".join(
            ",".join(str(int(row[f])) for f in FEATURE_NAMES)
            for _, row in X_df.iterrows()
        )
        csv_table = f"{header}\n{csv_rows}"

        client = Groq(api_key=Config.GROQ_API_KEY)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0,
            max_tokens=2000,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a legal classifier for Indian constitutional law. "
                        "For each row of boolean legal features below, predict whether "
                        "the law would be 'struck_down' or 'upheld'. "
                        "Reply ONLY with a JSON array of strings, one per row, in order. "
                        "No markdown, no explanation."
                    ),
                },
                {"role": "user", "content": csv_table},
            ],
        )
        raw = resp.choices[0].message.content.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        labels = json.loads(raw)
        y = np.array([0 if str(l).lower() == "struck_down" else 1 for l in labels])
        if len(y) != len(X_df):
            raise ValueError(f"Label count {len(y)} != row count {len(X_df)}")
        return y
    except Exception as e:
        _logger.warning("Groq oracle labelling failed, using heuristic: %s", e)
        # Heuristic fallback: mandatory sentences more likely struck down
        return (1 - X_df["is_mandatory_sentence"].values).astype(int)


class SurrogateTreeService:
    """Service for surrogate decision tree explanations using legal features."""

    def __init__(self) -> None:
        _logger.info("SurrogateTreeService initialised (per-request training)")

    def build_from_query(self, legal_features: Dict[str, Any]) -> Dict[str, Any]:
        """Build and serialise a surrogate tree from LLM-extracted legal features."""
        # Step A: Generate perturbations
        X_df = _generate_perturbations(legal_features, n=150)
        X = X_df.values

        # Step B: Label via Groq oracle
        y = _label_with_groq(X_df)

        # Step C: Train tree
        clf = DecisionTreeClassifier(max_depth=3, min_samples_leaf=5, random_state=42)
        clf.fit(X, y)

        # Training accuracy
        accuracy = float(clf.score(X, y))

        # Predict for the original input (first row)
        original_pred = bool(clf.predict(X[:1])[0])

        # Step D: Serialise FULL tree structure
        tree_ = clf.tree_
        nodes = []
        n_nodes = tree_.node_count

        for node_id in range(n_nodes):
            feature_idx = tree_.feature[node_id]
            threshold = tree_.threshold[node_id]
            is_leaf = feature_idx < 0  # TREE_UNDEFINED = -2

            left_child = int(tree_.children_left[node_id])
            right_child = int(tree_.children_right[node_id])

            if is_leaf:
                class_counts = tree_.value[node_id][0]
                predicted_class = int(np.argmax(class_counts))
                nodes.append({
                    "id": node_id,
                    "is_leaf": True,
                    "value": "Upheld" if predicted_class == 1 else "Struck Down",
                    "feature": "",
                    "threshold": 0.0,
                    "gini": round(float(tree_.impurity[node_id]), 3),
                    "samples": int(tree_.n_node_samples[node_id]),
                    "children_left": -1,
                    "children_right": -1,
                })
            else:
                fname = FEATURE_NAMES[feature_idx] if feature_idx < len(FEATURE_NAMES) else f"feature_{feature_idx}"
                display_name = FEATURE_DISPLAY.get(fname, fname)
                nodes.append({
                    "id": node_id,
                    "is_leaf": False,
                    "value": "",
                    "feature": display_name,
                    "threshold": round(float(threshold), 2),
                    "gini": round(float(tree_.impurity[node_id]), 3),
                    "samples": int(tree_.n_node_samples[node_id]),
                    "children_left": left_child,
                    "children_right": right_child,
                })

        return {
            "nodes": nodes,
            "accuracy": round(accuracy, 4),
            "prediction": original_pred,
            "feature_names": list(FEATURE_NAMES),
        }


_instance: SurrogateTreeService | None = None


def get_surrogate_service() -> SurrogateTreeService:
    global _instance
    if _instance is None:
        _instance = SurrogateTreeService()
    return _instance
