"""Cleaning rules: deterministic, named, described.

A rule only PROPOSES changes (it never edits the data and never writes to the log).
"""

import json
from dataclasses import dataclass

import pandas as pd

R1 = "R1_fill_median"
R2 = "R2_negative_to_abs"
R3 = "R3_normalize_city"
R4 = "R4_drop_duplicate"

RULES = {
    R1: "Replace a missing value in 'age' or 'income' with the median of that column.",
    R2: "Replace a negative 'transaction_amount' with its absolute value.",
    R3: "Remove surrounding spaces from 'city' and apply Title Case.",
    R4: "Delete a row that is an exact duplicate of an earlier row (the first one is kept).",
}


@dataclass(frozen=True)
class Change:
    """One proposed modification of the data."""
    row_id: int              # customer_id
    position: int            # DataFrame index (distinguishes a duplicate from its original)
    column: str              # column name, or "*" for a whole row
    old_value: str | None    # None = the value was missing
    new_value: str | None    # None = the row was deleted
    rule_id: str


def _fmt(value) -> str | None:
    """Turn any cell value into text for the log (None for missing values)."""
    if pd.isna(value):
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def rule_r1_fill_median(df: pd.DataFrame) -> list[Change]:
    changes = []
    for col in ["age", "income"]:
        median = df[col].median()
        for idx in df.index[df[col].isna()]:
            changes.append(Change(int(df.at[idx, "customer_id"]), int(idx), col,
                                  None, _fmt(median), R1))
    return changes


def rule_r2_negative_to_abs(df: pd.DataFrame) -> list[Change]:
    changes = []
    for idx in df.index[df["transaction_amount"] < 0]:
        old = df.at[idx, "transaction_amount"]
        changes.append(Change(int(df.at[idx, "customer_id"]), int(idx), "transaction_amount",
                              _fmt(old), _fmt(abs(old)), R2))
    return changes


def rule_r3_normalize_city(df: pd.DataFrame) -> list[Change]:
    changes = []
    for idx, city in df["city"].items():
        clean = city.strip().title()
        if clean != city:
            changes.append(Change(int(df.at[idx, "customer_id"]), int(idx), "city",
                                  city, clean, R3))
    return changes


def rule_r4_drop_duplicate(df: pd.DataFrame) -> list[Change]:
    changes = []
    for idx in df.index[df.duplicated(keep="first")]:
        row_text = json.dumps({k: _fmt(v) for k, v in df.loc[idx].items()})
        changes.append(Change(int(df.at[idx, "customer_id"]), int(idx), "*",
                              row_text, None, R4))
    return changes


if __name__ == "__main__":
    from audit_log.dirty_data import generate_dirty_dataset

    # The cleaning side never sees the hidden column
    df = generate_dirty_dataset().drop(columns="planted_defect")

    total = 0
    for rule_fn in [rule_r1_fill_median, rule_r2_negative_to_abs,
                    rule_r3_normalize_city, rule_r4_drop_duplicate]:
        changes = rule_fn(df)
        total += len(changes)
        print(f"{changes[0].rule_id}: {len(changes)} changes")
        print("   example:", changes[0])

    print("\nTotal proposed changes:", total)
    print("\nRule descriptions:")
    for rule_id, description in RULES.items():
        print(f" - {rule_id}: {description}")