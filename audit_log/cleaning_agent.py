"""Cleaning Agent: applies the rules, logs every change, returns clean data.

Design rule: no change is applied without being logged first.
"""

from dataclasses import dataclass

import pandas as pd

from audit_log.log_store import AuditLogStore
from audit_log.rules import (
    R1, R2, R3, R4, Change,
    rule_r1_fill_median, rule_r2_negative_to_abs,
    rule_r3_normalize_city, rule_r4_drop_duplicate,
)

AGENT_NAME = "CleaningAgent"


@dataclass
class CleaningResult:
    clean_data: pd.DataFrame
    changes: list
    batch_id: str


class CleaningAgent:
    def __init__(self, store: AuditLogStore):
        self.store = store

    def run(self, df: pd.DataFrame) -> CleaningResult:
        # 1. Rules PROPOSE changes (all computed on the same input data)
        changes: list[Change] = (
            rule_r1_fill_median(df)
            + rule_r2_negative_to_abs(df)
            + rule_r3_normalize_city(df)
            + rule_r4_drop_duplicate(df)
        )

        # 2. LOG first (one transaction: all entries or none)
        batch_id = self.store.append_batch(changes, agent=AGENT_NAME)

        # 3. APPLY only after the log is safely written
        clean = df.copy()
        for c in changes:
            if c.rule_id == R1:
                clean.at[c.position, c.column] = float(c.new_value)
            elif c.rule_id == R2:
                clean.at[c.position, c.column] = float(c.new_value)
            elif c.rule_id == R3:
                clean.at[c.position, c.column] = c.new_value

        to_drop = [c.position for c in changes if c.rule_id == R4]
        clean = clean.drop(index=to_drop).reset_index(drop=True)

        return CleaningResult(clean_data=clean, changes=changes, batch_id=batch_id)


if __name__ == "__main__":
    import os

    from audit_log.dirty_data import generate_dirty_dataset

    db = "test_audit_log.db"
    if os.path.exists(db):
        os.remove(db)

    store = AuditLogStore(db)
    raw = generate_dirty_dataset().drop(columns="planted_defect")
    result = CleaningAgent(store).run(raw)
    clean = result.clean_data

    print("Rows before:", len(raw), "| after:", len(clean))
    print("Changes logged:", store.count(), "| batch:", result.batch_id)

    print("\nChecks on the clean data:")
    print("  missing age/income:   ", int(clean[["age", "income"]].isna().sum().sum()))
    print("  negative amounts:     ", int((clean["transaction_amount"] < 0).sum()))
    print("  duplicated customers: ", int(clean["customer_id"].duplicated().sum()))
    print("  distinct cities:      ", sorted(clean["city"].unique()))