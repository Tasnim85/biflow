"""Log Auditor: answers "why was this row modified?" and verifies log integrity.

Read-only: it never writes to the log.
"""

from dataclasses import dataclass

import pandas as pd

from audit_log.log_store import GENESIS_HASH, AuditLogStore, compute_hash


@dataclass
class IntegrityReport:
    ok: bool
    entries_checked: int
    first_bad_entry: int | None   # entry_id of the first corrupted entry
    problem: str                  # human-readable description


class LogAuditor:
    def __init__(self, store: AuditLogStore):
        self.store = store

    # ---- 1. History of a row -------------------------------------------------
    def row_history(self, row_id: int) -> pd.DataFrame:
        query = (
            "SELECT a.entry_id, a.batch_id, a.position, a.column_name, a.old_value, "
            "a.new_value, a.rule_id, r.description, a.agent, a.timestamp "
            "FROM audit_log a JOIN rules r ON r.rule_id = a.rule_id "
            "WHERE a.row_id = ? ORDER BY a.entry_id"
        )
        rows = self.store.conn.execute(query, (row_id,)).fetchall()
        return pd.DataFrame([dict(r) for r in rows])

    # ---- 2. Natural-language answer ---------------------------------------------
    def why(self, row_id: int) -> str:
        history = self.row_history(row_id)
        if history.empty:
            return f"Customer {row_id} was never modified: the log has no entry for it."

        sentences = []
        for _, h in history.iterrows():
            if h["column_name"] == "*":
                sentences.append(
                    f"Entry {h['entry_id']}: a duplicate row (position {h['position']}) "
                    f"was deleted by {h['agent']} on {h['timestamp']} "
                    f"under rule {h['rule_id']} ({h['description']})"
                )
            else:
                old = "missing" if h["old_value"] is None else repr(h["old_value"])
                sentences.append(
                    f"Entry {h['entry_id']}: column '{h['column_name']}' changed from "
                    f"{old} to {h['new_value']!r} by {h['agent']} on {h['timestamp']} "
                    f"under rule {h['rule_id']} ({h['description']})"
                )
        return f"Customer {row_id} has {len(history)} logged change(s):\n- " + "\n- ".join(sentences)

    # ---- 3. Integrity verification --------------------------------------------
    def verify_integrity(self) -> IntegrityReport:
        rows = self.store.conn.execute(
            "SELECT * FROM audit_log ORDER BY entry_id"
        ).fetchall()

        expected_prev = GENESIS_HASH
        for r in rows:
            if r["prev_hash"] != expected_prev:
                return IntegrityReport(
                    False, len(rows), r["entry_id"],
                    f"Entry {r['entry_id']}: broken link. An earlier entry was altered, "
                    f"removed or inserted.",
                )
            recomputed = compute_hash(
                r["prev_hash"], r["batch_id"], r["row_id"], r["position"],
                r["column_name"], r["old_value"], r["new_value"], r["rule_id"],
                r["agent"], r["timestamp"],
            )
            if recomputed != r["entry_hash"]:
                return IntegrityReport(
                    False, len(rows), r["entry_id"],
                    f"Entry {r['entry_id']}: content does not match its hash. "
                    f"This entry was modified after being written.",
                )
            expected_prev = r["entry_hash"]

        return IntegrityReport(True, len(rows), None, "All entries verified: the chain is intact.")

    # ---- 4. Completeness ----------------------------------------------------------
    def check_completeness(self, expected_changes: int) -> tuple[bool, str]:
        logged = self.store.count()
        if logged == expected_changes:
            return True, f"Complete: {logged} logged entries for {expected_changes} applied changes."
        return False, f"INCOMPLETE: {logged} logged entries but {expected_changes} applied changes."


if __name__ == "__main__":
    import os
    import sqlite3

    from audit_log.cleaning_agent import CleaningAgent
    from audit_log.dirty_data import generate_dirty_dataset

    db = "test_audit_log.db"
    if os.path.exists(db):
        os.remove(db)

    store = AuditLogStore(db)
    raw = generate_dirty_dataset().drop(columns="planted_defect")
    result = CleaningAgent(store).run(raw)
    auditor = LogAuditor(store)

    print("=== Why was customer 40 modified? ===")
    print(auditor.why(40))

    print("\n=== Why was customer 340 modified? (duplicate) ===")
    print(auditor.why(340))

    print("\n=== Customer 1 (never modified) ===")
    print(auditor.why(1))

    print("\n=== Completeness ===")
    print(auditor.check_completeness(len(result.changes))[1])

    print("\n=== Integrity BEFORE tampering ===")
    print(auditor.verify_integrity())

    # ---- Tamper test: bypass the triggers like an attacker with file access ----
    print("\n=== Tampering: drop the trigger, edit entry 5 ===")
    store.conn.execute("DROP TRIGGER audit_log_no_update")
    store.conn.execute("UPDATE audit_log SET new_value = 'HACKED' WHERE entry_id = 5")
    store.conn.commit()

    print("\n=== Integrity AFTER tampering ===")
    print(auditor.verify_integrity())