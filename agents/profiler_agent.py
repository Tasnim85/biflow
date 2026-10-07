"""Data Profiler Agent: detects anomalous rows with an Isolation Forest.

Responsibility: make the DECISION (score + label). It does not explain it.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from data.data_generator import FEATURES


@dataclass
class ProfilerResult:
    """Everything the Profiler hands over to the rest of the system."""
    data: pd.DataFrame        # original data + score + is_anomaly columns
    model: IsolationForest    # the fitted model (the Auditor needs it for SHAP)
    features: list            # columns used by the model
    contamination: float      # assumption: expected share of anomalies
    n_estimators: int
    random_state: int


def run_profiler(
    df: pd.DataFrame,
    contamination: float = 0.03,
    n_estimators: int = 100,
    random_state: int = 42,
) -> ProfilerResult:
    X = df[FEATURES]

    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
    )
    model.fit(X)

    # score_samples: LOWER = more anomalous. We flip the sign so that
    # HIGHER anomaly_score = MORE anomalous, which is easier to read.
    anomaly_score = -model.score_samples(X)

    # predict: -1 = anomaly, 1 = normal. This applies the threshold
    # derived from `contamination`.
    is_anomaly = model.predict(X) == -1

    result_df = df.copy()
    result_df["anomaly_score"] = anomaly_score
    result_df["is_anomaly"] = is_anomaly

    return ProfilerResult(
        data=result_df,
        model=model,
        features=FEATURES,
        contamination=contamination,
        n_estimators=n_estimators,
        random_state=random_state,
    )


if __name__ == "__main__":
    from data.data_generator import generate_dataset

    result = run_profiler(generate_dataset())
    out = result.data

    print("Rows analyzed:      ", len(out))
    print("Anomalies detected: ", int(out["is_anomaly"].sum()))

    print("\nTop 10 most anomalous rows:")
    print(out.sort_values("anomaly_score", ascending=False)
             .head(10)[FEATURES + ["anomaly_score", "is_anomaly", "anomaly_type"]]
             .round(2))

    # Sanity check against the hidden ground truth
    caught = out[out["true_anomaly"] & out["is_anomaly"]]
    print(f"\nPlanted anomalies caught: {len(caught)} / {int(out['true_anomaly'].sum())}")
    print("Caught by type:")
    print(caught["anomaly_type"].value_counts())
    print("False alarms (normal rows flagged):",
          int((~out["true_anomaly"] & out["is_anomaly"]).sum()))