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

# ── Feature schema ────────────────────────────────────────────────────
CONTINUOUS_FEATURES = ["year_of_legislation", "year_of_judgment"]
CATEGORICAL_FEATURES = [
    "court_level",
    "is_central_act",
    "has_fundamental_rights_article",
    "has_criminal_provision",
]
OUTCOME_COL = "law_status"

FEATURE_DISPLAY: Dict[str, str] = {
    "year_of_legislation": "Year of legislation",
    "year_of_judgment": "Year of judgment",
    "court_level": "Court level",
    "is_central_act": "Central Act",
    "has_fundamental_rights_article": "Fundamental Rights article",
    "has_criminal_provision": "Criminal provision",
}

# ── Seed dataset (landmark Indian cases) ──────────────────────────────
_SEED_DATA = [
    # Struck down
    {"year_of_legislation": 2000, "year_of_judgment": 2015, "court_level": "Supreme Court",
     "is_central_act": 1, "has_fundamental_rights_article": 1, "has_criminal_provision": 1,
     "law_status": "struck_down"},  # S.66A IT Act
    {"year_of_legislation": 1860, "year_of_judgment": 1983, "court_level": "Supreme Court",
     "is_central_act": 1, "has_fundamental_rights_article": 1, "has_criminal_provision": 1,
     "law_status": "struck_down"},  # S.303 IPC — Mithu v State of Punjab
    {"year_of_legislation": 1860, "year_of_judgment": 2018, "court_level": "Supreme Court",
     "is_central_act": 1, "has_fundamental_rights_article": 1, "has_criminal_provision": 1,
     "law_status": "struck_down"},  # S.497 IPC — Joseph Shine
    {"year_of_legislation": 1860, "year_of_judgment": 2018, "court_level": "Supreme Court",
     "is_central_act": 1, "has_fundamental_rights_article": 1, "has_criminal_provision": 1,
     "law_status": "struck_down"},  # S.377 IPC (partial) — Navtej Singh Johar
    {"year_of_legislation": 1985, "year_of_judgment": 2005, "court_level": "Supreme Court",
     "is_central_act": 1, "has_fundamental_rights_article": 1, "has_criminal_provision": 0,
     "law_status": "struck_down"},  # IMDT Act — Sarbananda Sonowal
    # Stayed / under review
    {"year_of_legislation": 1860, "year_of_judgment": 2022, "court_level": "Supreme Court",
     "is_central_act": 1, "has_fundamental_rights_article": 1, "has_criminal_provision": 1,
     "law_status": "stayed"},  # S.124A IPC — Sedition
    {"year_of_legislation": 2019, "year_of_judgment": 2020, "court_level": "Supreme Court",
     "is_central_act": 1, "has_fundamental_rights_article": 1, "has_criminal_provision": 0,
     "law_status": "under_review"},  # CAA challenges
    {"year_of_legislation": 2019, "year_of_judgment": 2023, "court_level": "Supreme Court",
     "is_central_act": 1, "has_fundamental_rights_article": 1, "has_criminal_provision": 0,
     "law_status": "under_review"},  # Article 370 abrogation
    # Valid
    {"year_of_legislation": 1950, "year_of_judgment": 1978, "court_level": "Supreme Court",
     "is_central_act": 1, "has_fundamental_rights_article": 1, "has_criminal_provision": 0,
     "law_status": "valid"},  # Maneka Gandhi
    {"year_of_legislation": 1950, "year_of_judgment": 1973, "court_level": "Supreme Court",
     "is_central_act": 1, "has_fundamental_rights_article": 1, "has_criminal_provision": 0,
     "law_status": "valid"},  # Kesavananda Bharati
    {"year_of_legislation": 2016, "year_of_judgment": 2017, "court_level": "Supreme Court",
     "is_central_act": 1, "has_fundamental_rights_article": 0, "has_criminal_provision": 0,
     "law_status": "valid"},  # Aadhaar Act — partial validity
    {"year_of_legislation": 2013, "year_of_judgment": 2014, "court_level": "Supreme Court",
     "is_central_act": 1, "has_fundamental_rights_article": 0, "has_criminal_provision": 0,
     "law_status": "valid"},  # Companies Act 2013
    {"year_of_legislation": 1955, "year_of_judgment": 1965, "court_level": "High Court",
     "is_central_act": 1, "has_fundamental_rights_article": 0, "has_criminal_provision": 0,
     "law_status": "valid"},  # Hindu Marriage Act
    {"year_of_legislation": 1986, "year_of_judgment": 2019, "court_level": "Supreme Court",
     "is_central_act": 1, "has_fundamental_rights_article": 0, "has_criminal_provision": 0,
     "law_status": "valid"},  # Consumer Protection Act
    {"year_of_legislation": 1970, "year_of_judgment": 1980, "court_level": "High Court",
     "is_central_act": 0, "has_fundamental_rights_article": 0, "has_criminal_provision": 0,
     "law_status": "valid"},  # State rent-control act
    {"year_of_legislation": 1990, "year_of_judgment": 2000, "court_level": "Tribunal",
     "is_central_act": 0, "has_fundamental_rights_article": 0, "has_criminal_provision": 0,
     "law_status": "valid"},  # Service tribunal matter
]


class DiceCounterfactualService:
    """Singleton service for DiCE counterfactual generation."""

    def __init__(self) -> None:
        df = pd.DataFrame(_SEED_DATA)

        # dice-ml data object
        self._dice_data = dice_ml.Data(
            dataframe=df,
            continuous_features=CONTINUOUS_FEATURES,
            outcome_name=OUTCOME_COL,
        )

        # Train classifier
        X = df.drop(columns=[OUTCOME_COL])
        y = df[OUTCOME_COL]
        self._model_clf = RandomForestClassifier(
            n_estimators=100, max_depth=6, random_state=42
        )
        self._model_clf.fit(
            pd.get_dummies(X, columns=["court_level"]),
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
        # Build a single-row DataFrame
        input_df = pd.DataFrame([case_features])

        # Predict original outcome
        input_encoded = pd.get_dummies(input_df, columns=["court_level"])
        # Align columns with training data
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
                "original": {**case_features, "outcome": original_outcome},
                "counterfactuals": [],
            }

        counterfactuals = []
        all_feature_cols = [c for c in cf_df.columns if c != OUTCOME_COL]
        for _, row in cf_df.iterrows():
            cf_features = {col: row[col] for col in all_feature_cols}
            cf_outcome = str(row.get(OUTCOME_COL, ""))
            changed = [
                col for col in all_feature_cols
                if str(cf_features.get(col)) != str(case_features.get(col))
            ]
            counterfactuals.append({
                "features": cf_features,
                "outcome": cf_outcome,
                "changed_fields": changed,
            })

        return {
            "original": {**case_features, "outcome": original_outcome},
            "counterfactuals": counterfactuals,
        }


_instance: DiceCounterfactualService | None = None


def get_dice_service() -> DiceCounterfactualService:
    global _instance
    if _instance is None:
        _instance = DiceCounterfactualService()
    return _instance
