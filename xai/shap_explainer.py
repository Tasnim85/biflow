"""SHAP explainer: per-feature contributions to the Isolation Forest score.

Purely numeric. Turning numbers into sentences is the narrator's job.
"""

from dataclasses import dataclass

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


def build_explainer(model: IsolationForest) -> shap.TreeExplainer:
    """Create the SHAP TreeExplainer once; reuse it for every row."""
    return shap.TreeExplainer(model)


def explain_row(
    explainer: shap.TreeExplainer,
    X: pd.DataFrame,
    row_index: int,
) -> ShapExplanation:
    """Explain one row of X (X must contain only the model's feature columns)."""
    row = X.loc[[row_index]]                      # keep it 2D: one-row DataFrame
    shap_values = explainer.shap_values(row)[0]   # array: one value per feature

    # sklearn's score is "lower = more anomalous". SHAP explains that raw output.
    # We flip the sign so that POSITIVE shap = pushes TOWARD anomaly,
    # matching the flipped anomaly_score used by the Profiler.
    shap_toward_anomaly = -shap_values
    base_value = -float(np.ravel(explainer.expected_value)[0])

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
    

if __name__ == "__main__":
    from agents.profiler_agent import run_profiler
    from data.data_generator import FEATURES, generate_dataset

    result = run_profiler(generate_dataset())
    X = result.data[FEATURES]
    explainer = build_explainer(result.model)

    # One planted anomaly of each type, plus rows we know about
    for idx in [30, 354, 217]:
        exp = explain_row(explainer, X, idx)
        actual_score = result.data.loc[idx, "anomaly_score"]
        kind = result.data.loc[idx, "anomaly_type"]
        print(f"\n=== Row {idx} (planted type: {kind}) ===")
        print(f"Profiler anomaly_score: {actual_score:.3f}")
        rebuilt = path_length_to_score(exp.model_output, result.model.max_samples_)
        print(f"Score rebuilt from SHAP: {rebuilt:.3f}  (should equal the line above)")
        print(f"Base (typical row): {-exp.base_value:.1f} splits | this row: {-exp.model_output:.1f} splits")
        print(exp.contributions.round(3))