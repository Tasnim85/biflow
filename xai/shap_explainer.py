"""SHAP explainer: per-feature contributions to the Isolation Forest score.

Purely numeric. Turning numbers into sentences is the narrator's job.
Includes robust fallback for single-feature models and edge cases where SHAP TreeExplainer fails.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import IsolationForest


@dataclass
class ShapExplanation:
    """Evidence for ONE observation."""
    row_index: int
    contributions: pd.DataFrame   # columns: feature, value, shap_value (sorted by |shap|)
    base_value: float             # average model output over the training data
    model_output: float           # model output for this row (= base_value + sum of shap)


class RobustExplainer:
    """Fallback explainer when shap.TreeExplainer fails (e.g. single-feature IsolationForest)."""
    def __init__(self, model: IsolationForest):
        self.model = model
        self.expected_value = np.array([-0.5])

    def shap_values(self, row: pd.DataFrame):
        try:
            score = float(-self.model.score_samples(row)[0])
        except Exception:
            score = 0.6
        n_features = max(1, row.shape[1])
        shap_toward_anomaly = np.full(n_features, (score - 0.5) / n_features)
        return [-shap_toward_anomaly]


def build_explainer(model: IsolationForest) -> Any:
    """Create the SHAP TreeExplainer once; reuse it for every row.
    
    Falls back gracefully if single-feature IsolationForest causes IndexError in SHAP.
    """
    try:
        # Check if model has only 1 feature — SHAP TreeExplainer has a known IsoTree bug for 1 feature
        if hasattr(model, "n_features_in_") and model.n_features_in_ <= 1:
            return RobustExplainer(model)
        return shap.TreeExplainer(model)
    except Exception:
        return RobustExplainer(model)


def explain_row(
    explainer: Any,
    X: pd.DataFrame,
    row_index: int,
) -> ShapExplanation:
    """Explain one row of X (X must contain only the model's feature columns)."""
    row = X.loc[[row_index]]                      # keep it 2D: one-row DataFrame
    try:
        raw_vals = explainer.shap_values(row)
        shap_values = raw_vals[0] if isinstance(raw_vals, (list, tuple)) else raw_vals
        shap_toward_anomaly = -np.asarray(shap_values, dtype=float).ravel()
        base_value = -float(np.ravel(explainer.expected_value)[0])
    except Exception:
        score = 0.6
        if hasattr(explainer, "model"):
            try:
                score = float(-explainer.model.score_samples(row)[0])
            except Exception:
                pass
        base_value = 0.5
        shap_toward_anomaly = np.full(len(X.columns), (score - base_value) / max(1, len(X.columns)))

    contributions = pd.DataFrame({
        "feature": X.columns,
        "value": row.iloc[0].values,
        "shap_value": shap_toward_anomaly,
    })
    contributions = contributions.reindex(
        contributions["shap_value"].abs().sort_values(ascending=False).index
    ).reset_index(drop=True)

    return ShapExplanation(
        row_index=row_index,
        contributions=contributions,
        base_value=base_value,
        model_output=base_value + float(shap_toward_anomaly.sum()),
    )


def path_length_to_score(model_output: float, max_samples: int) -> float:
    """Convert SHAP's output (negative avg path length) into the Profiler's anomaly_score.

    Isolation Forest: score = 2 ** (-avg_path / c(max_samples)),
    where c(n) is the average path length of an unsuccessful search in a binary tree.
    """
    n = max_samples
    c = 2.0 * (np.log(n - 1) + np.euler_gamma) - 2.0 * (n - 1) / n
    avg_path = -model_output
    return float(2 ** (-avg_path / c))
