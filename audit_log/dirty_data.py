"""Dataset with planted data-quality defects, built on the prototype 1 data.

The cleaning agent NEVER sees the column `planted_defect`.
It exists only so we can check that the audit log is complete.
"""

import numpy as np
import pandas as pd

from data.data_generator import FEATURES, generate_dataset

CITIES = ["Tunis", "Sfax", "Sousse", "Bizerte", "Gabès", "Nabeul"]


def generate_dirty_dataset(seed: int = 7, base: pd.DataFrame | None = None) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    # ---- 1. Clean base: same customers as prototype 1 --------------------
    source = base if base is not None else generate_dataset()
    df = source[FEATURES].copy()
    df.insert(0, "customer_id", range(1, len(df) + 1))
    df["city"] = rng.choice(CITIES, size=len(df))
    df["planted_defect"] = "none"

    # ---- 2. Pick distinct rows: 24 for defects + 6 to be duplicated -------
    picked = rng.choice(len(df), size=30, replace=False)
    missing_age, missing_income = picked[0:4], picked[4:8]
    negative_amount = picked[8:16]
    messy_city = picked[16:24]
    to_duplicate = picked[24:30]

    # ---- 3. Plant the defects ----------------------------------------------
    df.loc[missing_age, "age"] = np.nan
    df.loc[missing_income, "income"] = np.nan
    df.loc[np.r_[missing_age, missing_income], "planted_defect"] = "missing_value"

    df.loc[negative_amount, "transaction_amount"] *= -1
    df.loc[negative_amount, "planted_defect"] = "negative_amount"

    def mess_up(city: str) -> str:
        variants = [city.lower(), city.upper(), f"  {city.lower()} ", f" {city} "]
        return variants[rng.integers(len(variants))]

    df.loc[messy_city, "city"] = df.loc[messy_city, "city"].map(mess_up)
    df.loc[messy_city, "planted_defect"] = "messy_city"

    # ---- 4. Exact duplicates appended at the end ---------------------------
    duplicates = df.loc[to_duplicate].copy()
    duplicates["planted_defect"] = "duplicate"
    df = pd.concat([df, duplicates], ignore_index=True)

    return df


if __name__ == "__main__":
    data = generate_dirty_dataset()
    print("Shape:", data.shape)
    print("\nPlanted defects:")
    print(data["planted_defect"].value_counts())
    print("\nMissing values per column:")
    print(data[["age", "income"]].isna().sum())
    print("\nNegative amounts:", int((data["transaction_amount"] < 0).sum()))
    print("Duplicated customer_id:", int(data["customer_id"].duplicated().sum()))
    print("\nMessy city examples:")
    print(data.loc[data["planted_defect"] == "messy_city", "city"].head(5).map(repr).to_string())