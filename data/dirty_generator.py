"""Generate raw imperfect records directly, without modifying a clean dataset."""
from pathlib import Path

import numpy as np
import pandas as pd

from data.data_generator import FEATURES


def _generate(seed=2026, n_rows=500):
    rng = np.random.default_rng(seed)
    records, catalog = [], []
    for position in range(n_rows):
        record = {}
        for column in FEATURES:
            mode = rng.choice(["normal", "format", "missing", "blank", "text", "negative", "domain", "unit", "ambiguous", "nonfinite"],
                              p=[.76, .08, .03, .02, .02, .02, .02, .02, .02, .01])
            if mode in {"normal", "format"}:
                if column == "age":
                    value = int(rng.integers(18, 76))
                elif column == "income":
                    value = round(float(rng.uniform(12000, 100000)), 2)
                elif column == "spending_score":
                    value = int(rng.integers(1, 101))
                elif column == "transaction_amount":
                    value = round(float(rng.uniform(5, 200)), 2)
                else:
                    value = int(rng.poisson(20))
                if mode == "format":
                    value = f"  {float(value):.2f}  ".replace(".", ",")
            elif mode == "missing":
                value = None
            elif mode == "blank":
                value = "   "
            elif mode == "text":
                value = "inconnu"
            elif mode == "negative":
                value = -int(rng.integers(1, 100))
            elif mode == "domain":
                value = {"age": 180, "spending_score": 150, "num_transactions": 2.5,
                         "income": "non renseigné", "transaction_amount": "non renseigné"}[column]
            elif mode == "unit":
                value = "42 EUR" if column in {"income", "transaction_amount"} else "42 unités"
            elif mode == "ambiguous":
                value = "1,234.56"
            else:
                value = "Infinity"
            record[column] = value
            if mode != "normal":
                catalog.append((position, column, mode, "Correction" if mode == "format" else "Révision"))
        # These labels describe planted statistical anomalies, not cleaning defects.
        record["true_anomaly"] = False
        record["anomaly_type"] = "none"
        records.append(record)
    return (pd.DataFrame(records, columns=FEATURES + ["true_anomaly", "anomaly_type"]),
            pd.DataFrame(catalog, columns=["Ligne", "Colonne", "Mode de génération", "Traitement attendu"]))


def generate_dirty_dataset(seed=2026, n_rows=500):
    return _generate(seed, n_rows)[0]


def defect_catalog(seed=2026, n_rows=500):
    """Generation metadata kept outside the original dataset schema."""
    return _generate(seed, n_rows)[1]


if __name__ == "__main__":
    destination = Path(__file__).with_name("customers_dirty.csv")
    data, catalog = _generate()
    data.to_csv(destination, index=False)
    catalog.to_csv(destination.with_name("customers_dirty_defects.csv"), index=False)
    print(f"{len(data)} rows, {len(catalog)} imperfect cells: {destination}")
