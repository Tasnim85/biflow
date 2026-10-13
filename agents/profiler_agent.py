"""Data Profiler Agent: profiling datasets and detecting anomalous rows.

Combines Isolation Forest (BO3) and Robust Median Absolute Deviation (MAD) (BO2).
"""
from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from core.profiling import profile_dataset
from data.data_generator import FEATURES


class ProfilerAgent:
    """BO1 Profiler Agent."""
    def run(self, name: str, frame: pd.DataFrame):
        return profile_dataset(name, frame)


@dataclass
class ProfilerResult:
    """Unified result containing IsolationForest model, anomaly scores, and MAD metrics."""
    data: pd.DataFrame        # original data + score + is_anomaly + robust metrics
    model: IsolationForest    # fitted model for SHAP explainer
    features: list[str]       # columns used by the model
    contamination: float
    n_estimators: int
    random_state: int
    robust_scores: pd.DataFrame = field(default_factory=pd.DataFrame)
    metadata: dict = field(default_factory=dict)


def run_profiler(
    df: pd.DataFrame,
    contamination: float = 0.03,
    n_estimators: int = 100,
    robust_threshold: float = 3.5,
    random_state: int = 42,
) -> ProfilerResult:
    """Unified profiling & anomaly detection combining Isolation Forest and MAD."""
    available_features = [f for f in FEATURES if f in df.columns]
    if not available_features:
        available_features = df.select_dtypes(include=[np.number]).columns.tolist()
    if not available_features:
        raise ValueError("No numeric features found for profiler.")

    X = df[available_features].copy()
    for col in available_features:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(X.median())

    # 1. Isolation Forest (BO3)
    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
    )
    model.fit(X)

    isolation_score = -model.score_samples(X)
    isolation_flag = model.predict(X) == -1

    # 2. Robust MAD (BO2)
    robust_scores = pd.DataFrame(index=X.index, columns=available_features, dtype=float)
    zero_mad_cols = []
    for col in available_features:
        med = X[col].median()
        mad = (X[col] - med).abs().median()
        if mad == 0:
            zero_mad_cols.append(col)
            robust_scores[col] = 0.0
        else:
            robust_scores[col] = 0.67448975 * (X[col] - med).abs() / mad

    robust_max = robust_scores.max(axis=1)
    robust_flag = robust_max > robust_threshold

    # 3. Combined classification
    result_df = df.copy()
    result_df["anomaly_score"] = isolation_score
    result_df["is_anomaly"] = isolation_flag
    result_df["robust_max"] = robust_max
    result_df["robust_flag"] = robust_flag

    def _determine_status(row):
        iso = row["is_anomaly"]
        rob = row["robust_flag"]
        if iso and rob:
            return "Anomalie confirmée (Isolation Forest + MAD)"
        elif iso:
            return "Atypique (Isolation Forest)"
        elif rob:
            return "Atypique (Écart MAD)"
        return "Conforme"

    result_df["anomaly_status"] = result_df.apply(_determine_status, axis=1)

    metadata = {
        "features": available_features,
        "contamination": contamination,
        "robust_threshold": robust_threshold,
        "n_estimators": n_estimators,
        "random_state": random_state,
        "zero_mad_columns": zero_mad_cols,
        "isolation_flagged_count": int(isolation_flag.sum()),
        "robust_flagged_count": int(robust_flag.sum()),
    }

    return ProfilerResult(
        data=result_df,
        model=model,
        features=available_features,
        contamination=contamination,
        n_estimators=n_estimators,
        random_state=random_state,
        robust_scores=robust_scores,
        metadata=metadata
    )
