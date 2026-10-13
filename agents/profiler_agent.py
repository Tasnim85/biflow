"""Data Profiler Agent: profiling datasets and detecting anomalous rows."""

from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from core.profiling import profile_dataset
from data.data_generator import FEATURES


class ProfilerAgent:
    """BO1 Profiler Agent."""
    def run(self, name, frame):
        return profile_dataset(name, frame)


@dataclass
class ProfilerResult:
    """Everything the Profiler hands over to the rest of the system."""
    data: pd.DataFrame        # original data + score + is_anomaly columns
    model: IsolationForest    # fitted model for SHAP
    features: list            # columns used by the model
    contamination: float
    n_estimators: int
    random_state: int


def run_profiler(
    df: pd.DataFrame,
    contamination: float = 0.03,
    n_estimators: int = 100,
    random_state: int = 42,
) -> ProfilerResult:
    """BO3 Profiler function with IsolationForest."""
    # Ensure features exist or pick numeric columns
    available_features = [f for f in FEATURES if f in df.columns]
    if not available_features:
        available_features = df.select_dtypes(include=[np.number]).columns.tolist()
    if not available_features:
        raise ValueError("No numeric features found for profiler.")

    X = df[available_features].fillna(df[available_features].median())

    model = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
    )
    model.fit(X)

    anomaly_score = -model.score_samples(X)
    is_anomaly = model.predict(X) == -1

    result_df = df.copy()
    result_df["anomaly_score"] = anomaly_score
    result_df["is_anomaly"] = is_anomaly

    return ProfilerResult(
        data=result_df,
        model=model,
        features=available_features,
        contamination=contamination,
        n_estimators=n_estimators,
        random_state=random_state,
    )
