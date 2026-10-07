"""Synthetic customer dataset with planted anomalies.

The model NEVER sees the columns `true_anomaly` and `anomaly_type`.
They exist only so we can check that the explanations are credible.
"""

import numpy as np
import pandas as pd

# Columns the model is allowed to use
FEATURES = [
    "age",
    "income",
    "spending_score",
    "transaction_amount",
    "num_transactions",
]


def generate_dataset(n_rows: int = 500, anomaly_rate: float = 0.03, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # ---- 1. Normal customers -------------------------------------------
    age = np.clip(rng.normal(40, 12, n_rows), 18, 75).round()
    income = 20000 + age * 800 + rng.normal(0, 6000, n_rows)
    income = np.clip(income, 12000, None).round()
    spending_score = np.clip(30 + income / 2000 + rng.normal(0, 12, n_rows), 1, 100).round()
    num_transactions = rng.poisson(20, n_rows)
    transaction_amount = np.clip(20 + income / 1500 + rng.normal(0, 8, n_rows), 5, None).round(2)

    df = pd.DataFrame({
        "age": age,
        "income": income,
        "spending_score": spending_score,
        "transaction_amount": transaction_amount,
        "num_transactions": num_transactions,
    })
    df["true_anomaly"] = False
    df["anomaly_type"] = "none"

    # ---- 2. Plant anomalies ---------------------------------------------
    n_anomalies = int(round(n_rows * anomaly_rate))
    idx = rng.choice(n_rows, size=n_anomalies, replace=False)
    types = ["A", "B", "C"]

    for i, row_idx in enumerate(idx):
        kind = types[i % 3]
        if kind == "A":    # extremely high transaction amount (fraud-like)
            df.loc[row_idx, "transaction_amount"] = round(rng.uniform(400, 900), 2)
        elif kind == "B":  # extreme number of transactions (very high or near zero)
            df.loc[row_idx, "num_transactions"] = int(rng.choice([0, 1, rng.integers(70, 100)]))
        else:              # C: income unusually high for the age
            df.loc[row_idx, "income"] = float(round(rng.uniform(150000, 250000)))
        df.loc[row_idx, "true_anomaly"] = True
        df.loc[row_idx, "anomaly_type"] = kind

    return df


if __name__ == "__main__":
    data = generate_dataset()
    print(data.head())
    print("\nShape:", data.shape)
    print("\nAnomalies by type:")
    print(data["anomaly_type"].value_counts())
    print("\nSummary statistics:")
    print(data[FEATURES].describe().round(1))