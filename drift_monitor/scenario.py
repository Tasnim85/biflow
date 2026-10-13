"""6-month scenario with planted events.

The DriftMonitor NEVER reads PLANTED_TRUTH. It exists only to check,
at the end, that the alerts fall in the right months.
"""

from dataclasses import dataclass

import pandas as pd

from data.data_generator import generate_dataset

N_MONTHS = 6
REFERENCE_MONTHS = [1, 2, 3]          # months that define "normal"
TRAIN_SEED = 1000                     # training batch for the frozen Profiler
MONTH_SEED_BASE = 100                 # month m uses seed 100 + m


@dataclass(frozen=True)
class MonthConfig:
    """What REALLY happens in a month (the monitor does not see this)."""
    month: int
    income_factor: float = 1.0           # data drift: multiplies every income
    profiler_contamination: float = 0.03  # Profiler threshold setting
    etl_loss_rate: float = 0.0           # share of rows silently lost by the ETL


CONFIGS = [
    MonthConfig(1),
    MonthConfig(2),
    MonthConfig(3),
    MonthConfig(4, income_factor=1.4),             # data drift
    MonthConfig(5, profiler_contamination=0.10),   # agent changed
    MonthConfig(6, etl_loss_rate=0.08),            # silent ETL bug
]

# Ground truth, used ONLY to validate the monitor at the end
PLANTED_TRUTH = {
    1: "stable",
    2: "stable",
    3: "stable",
    4: "data_drift",
    5: "agent_changed",
    6: "etl_bug",
}


def get_training_batch() -> pd.DataFrame:
    """Separate batch used to train the Profiler once (then frozen)."""
    return generate_dataset(seed=TRAIN_SEED)


def get_month_data(cfg: MonthConfig) -> pd.DataFrame:
    """500 customers for one month, with the planted data change if any."""
    df = generate_dataset(seed=MONTH_SEED_BASE + cfg.month)
    if cfg.income_factor != 1.0:
        df["income"] = (df["income"] * cfg.income_factor).round()
    return df


def build_scenario() -> dict:
    """All months at once: {month: (config, dataframe)}."""
    return {cfg.month: (cfg, get_month_data(cfg)) for cfg in CONFIGS}


if __name__ == "__main__":
    train = get_training_batch()
    print("Training batch:", train.shape)

    print("\nMonth | rows | mean income | mean amount | planted anomalies | config")
    for month, (cfg, df) in build_scenario().items():
        print(f"  {month}   | {len(df)} | {df['income'].mean():>11,.0f} | "
              f"{df['transaction_amount'].mean():>11.1f} | "
              f"{int(df['true_anomaly'].sum()):>17} | "
              f"income x{cfg.income_factor}, contamination {cfg.profiler_contamination}, "
              f"ETL loss {cfg.etl_loss_rate:.0%}")

    print("\nPlanted truth (hidden from the monitor):")
    for m, label in PLANTED_TRUTH.items():
        print(f"  month {m}: {label}")