"""DiCE counterfactual explanation service for Indian legal outcomes.

Uses dice-ml with a RandomForestClassifier trained on a curated seed
dataset of landmark Indian cases.  Never calls Groq.
"""

import logging
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import dice_ml

_logger = logging.getLogger(__name__)

# ── Feature schema (matches extract_legal_features output) ────────────
BOOLEAN_FEATURES = [
    "is_mandatory_sentence",
    "allows_judicial_discretion",
    "cites_fundamental_rights",
    "is_central_legislation",
    "has_criminal_provision",
]
CATEGORICAL_FEATURES = ["applicable_act"]
CONTINUOUS_FEATURES: List[str] = []
OUTCOME_COL = "law_status"

FEATURE_DISPLAY: Dict[str, str] = {
    "is_mandatory_sentence": "Mandatory sentence",
    "allows_judicial_discretion": "Judicial discretion",
    "cites_fundamental_rights": "Fundamental Rights cited",
    "is_central_legislation": "Central legislation",
    "has_criminal_provision": "Criminal provision",
    "applicable_act": "Applicable Act",
}

# ── Seed dataset (landmark Indian cases — binary outcomes only) ───────
_SEED_DATA = [
    # Struck down
    {"is_mandatory_sentence": 1, "allows_judicial_discretion": 0, "cites_fundamental_rights": 1,
     "is_central_legislation": 1, "has_criminal_provision": 1, "applicable_act": "IT Act",
     "law_status": "struck_down"},  # S.66A IT Act — Shreya Singhal
    {"is_mandatory_sentence": 1, "allows_judicial_discretion": 0, "cites_fundamental_rights": 1,
     "is_central_legislation": 1, "has_criminal_provision": 1, "applicable_act": "IPC",
     "law_status": "struck_down"},  # S.303 IPC — Mithu v State of Punjab
    {"is_mandatory_sentence": 0, "allows_judicial_discretion": 0, "cites_fundamental_rights": 1,
     "is_central_legislation": 1, "has_criminal_provision": 1, "applicable_act": "IPC",
     "law_status": "struck_down"},  # S.497 IPC — Joseph Shine
    {"is_mandatory_sentence": 0, "allows_judicial_discretion": 0, "cites_fundamental_rights": 1,
     "is_central_legislation": 1, "has_criminal_provision": 1, "applicable_act": "IPC",
     "law_status": "struck_down"},  # S.377 IPC — Navtej Singh Johar
    {"is_mandatory_sentence": 0, "allows_judicial_discretion": 0, "cites_fundamental_rights": 1,
     "is_central_legislation": 1, "has_criminal_provision": 0, "applicable_act": "IMDT Act",
     "law_status": "struck_down"},  # IMDT Act — Sarbananda Sonowal
    {"is_mandatory_sentence": 0, "allows_judicial_discretion": 0, "cites_fundamental_rights": 1,
     "is_central_legislation": 1, "has_criminal_provision": 0, "applicable_act": "Constitution",
     "law_status": "struck_down"},  # NJAC — Fourth Judges Case
    {"is_mandatory_sentence": 1, "allows_judicial_discretion": 0, "cites_fundamental_rights": 1,
     "is_central_legislation": 1, "has_criminal_provision": 1, "applicable_act": "IPC",
     "law_status": "struck_down"},  # S.309 IPC attempt (Mental Healthcare Act 2017)
    # Upheld (binary mapping: valid / stayed / under_review → upheld)
    {"is_mandatory_sentence": 0, "allows_judicial_discretion": 1, "cites_fundamental_rights": 1,
     "is_central_legislation": 1, "has_criminal_provision": 0, "applicable_act": "Constitution",
     "law_status": "upheld"},  # Maneka Gandhi — Art 21 expansion
    {"is_mandatory_sentence": 0, "allows_judicial_discretion": 1, "cites_fundamental_rights": 1,
     "is_central_legislation": 1, "has_criminal_provision": 0, "applicable_act": "Constitution",
     "law_status": "upheld"},  # Kesavananda Bharati — Basic Structure
    {"is_mandatory_sentence": 0, "allows_judicial_discretion": 1, "cites_fundamental_rights": 0,
     "is_central_legislation": 1, "has_criminal_provision": 0, "applicable_act": "Companies Act",
     "law_status": "upheld"},  # Companies Act 2013
    {"is_mandatory_sentence": 0, "allows_judicial_discretion": 1, "cites_fundamental_rights": 0,
     "is_central_legislation": 1, "has_criminal_provision": 0, "applicable_act": "Consumer Protection Act",
     "law_status": "upheld"},  # Consumer Protection Act
    {"is_mandatory_sentence": 0, "allows_judicial_discretion": 1, "cites_fundamental_rights": 0,
     "is_central_legislation": 1, "has_criminal_provision": 0, "applicable_act": "Aadhaar Act",
     "law_status": "upheld"},  # Aadhaar Act — partial validity
    {"is_mandatory_sentence": 0, "allows_judicial_discretion": 1, "cites_fundamental_rights": 1,
     "is_central_legislation": 1, "has_criminal_provision": 1, "applicable_act": "IPC",
     "law_status": "upheld"},  # S.124A IPC — Sedition (stayed, treat as upheld)
    {"is_mandatory_sentence": 0, "allows_judicial_discretion": 1, "cites_fundamental_rights": 0,
     "is_central_legislation": 0, "has_criminal_provision": 0, "applicable_act": "State Act",
     "law_status": "upheld"},  # State rent-control act
    {"is_mandatory_sentence": 0, "allows_judicial_discretion": 1, "cites_fundamental_rights": 1,
     "is_central_legislation": 1, "has_criminal_provision": 0, "applicable_act": "CAA",
     "law_status": "upheld"},  # CAA challenges (under review, treat as upheld)
]


class DiceCounterfactualService:
    """Singleton service for DiCE counterfactual generation."""

    def __init__(self) -> None:
        df = pd.DataFrame(_SEED_DATA)

        # dice-ml data object — no continuous features
        self._dice_data = dice_ml.Data(
            dataframe=df,
            continuous_features=CONTINUOUS_FEATURES,
            outcome_name=OUTCOME_COL,
        )

        # Train classifier on one-hot encoded categoricals
        X = df.drop(columns=[OUTCOME_COL])
        y = df[OUTCOME_COL]
        self._model_clf = RandomForestClassifier(
            n_estimators=100, max_depth=6, random_state=42
        )
        self._model_clf.fit(
            pd.get_dummies(X, columns=CATEGORICAL_FEATURES),
            y,
        )

        # dice-ml model wrapper (sklearn backend)
        self._dice_model = dice_ml.Model(
            model=self._model_clf, backend="sklearn"
        )

        self._dice_exp = dice_ml.Dice(
            self._dice_data, self._dice_model, method="random"
        )
        _logger.info("DiceCounterfactualService initialised")

    def generate(self, case_features: Dict[str, Any], k: int = 3) -> Dict[str, Any]:
        """Generate k diverse counterfactuals for the given case features."""
        # Normalise booleans to int for the DataFrame
        cleaned: Dict[str, Any] = {}
        for feat in BOOLEAN_FEATURES:
            cleaned[feat] = int(bool(case_features.get(feat, 0)))
        cleaned["applicable_act"] = str(case_features.get("applicable_act", "IPC"))

        input_df = pd.DataFrame([cleaned])

        # Predict original outcome
        input_encoded = pd.get_dummies(input_df, columns=CATEGORICAL_FEATURES)
        for col in self._model_clf.feature_names_in_:
            if col not in input_encoded.columns:
                input_encoded[col] = 0
        input_encoded = input_encoded[list(self._model_clf.feature_names_in_)]
        original_outcome = str(self._model_clf.predict(input_encoded)[0])

        try:
            dice_result = self._dice_exp.generate_counterfactuals(
                input_df,
                total_CFs=k,
                desired_class="opposite",
            )
            cf_df = dice_result.cf_examples_list[0].final_cfs_df
        except Exception as e:
            _logger.warning("DiCE generation failed: %s", e)
            return {
                "original": {**cleaned, "outcome": original_outcome},
                "counterfactuals": [],
            }

        counterfactuals = []
        all_feature_cols = [c for c in cf_df.columns if c != OUTCOME_COL]
        for _, row in cf_df.iterrows():
            cf_features = {col: row[col] for col in all_feature_cols}
            cf_outcome = str(row.get(OUTCOME_COL, ""))
            changed = [
                col for col in all_feature_cols
                if str(cf_features.get(col)) != str(cleaned.get(col))
            ]
            counterfactuals.append({
                "features": cf_features,
                "outcome": cf_outcome,
                "changed_fields": changed,
            })

        return {
            "original": {**cleaned, "outcome": original_outcome},
            "counterfactuals": counterfactuals,
        }


_instance: DiceCounterfactualService | None = None


def get_dice_service() -> DiceCounterfactualService:
    global _instance
    if _instance is None:
        _instance = DiceCounterfactualService()
    return _instance
