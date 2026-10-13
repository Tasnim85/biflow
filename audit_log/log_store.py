"""Append-only audit log on SQLite, protected by triggers and a SHA-256 hash chain.

This class is the ONLY place that writes to the log.
"""

import hashlib
import json
import sqlite3
from datetime import datetime

from audit_log.rules import RULES, Change

GENESIS_HASH = "0" * 64   # "previous hash" of the very first entry

SCHEMA = """
CREATE TABLE IF NOT EXISTS audit_log (
    entry_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id    TEXT NOT NULL,
    row_id      INTEGER NOT NULL,
    position    INTEGER NOT NULL,
    column_name TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT,
    rule_id     TEXT NOT NULL,
    agent       TEXT NOT NULL,
    timestamp   TEXT NOT NULL,
    prev_hash   TEXT NOT NULL,
    entry_hash  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rules (
    rule_id     TEXT PRIMARY KEY,
    description TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS audit_log_no_update
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is append-only: UPDATE is forbidden');
END;

CREATE TRIGGER IF NOT EXISTS audit_log_no_delete
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'audit_log is append-only: DELETE is forbidden');
END;
"""


def compute_hash(prev_hash, batch_id, row_id, position, column_name,
                 old_value, new_value, rule_id, agent, timestamp) -> str:
    """SHA-256 of the entry's content + the previous entry's hash."""
    payload = json.dumps(
        [prev_hash, batch_id, row_id, position, column_name,
         old_value, new_value, rule_id, agent, timestamp],
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AuditLogStore:
    def __init__(self, db_path: str = "audit_log.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.executemany(
            "INSERT OR IGNORE INTO rules (rule_id, description) VALUES (?, ?)",
            RULES.items(),
        )
        self.conn.commit()

    def _last_hash(self) -> str:
        row = self.conn.execute(
            "SELECT entry_hash FROM audit_log ORDER BY entry_id DESC LIMIT 1"
        ).fetchone()
        return row["entry_hash"] if row else GENESIS_HASH

    def append_batch(self, changes: list[Change], agent: str, batch_id: str | None = None) -> str:
        """Append all changes in one transaction. Returns the batch id."""
        batch_id = batch_id or datetime.now().strftime("batch-%Y%m%d-%H%M%S")
        prev_hash = self._last_hash()

        with self.conn:   # one transaction: all entries are written, or none
            for c in changes:
                timestamp = datetime.now().isoformat(timespec="seconds")
                entry_hash = compute_hash(
                    prev_hash, batch_id, c.row_id, c.position, c.column,
                    c.old_value, c.new_value, c.rule_id, agent, timestamp,
                )
                self.conn.execute(
                    "INSERT INTO audit_log (batch_id, row_id, position, column_name, "
                    "old_value, new_value, rule_id, agent, timestamp, prev_hash, entry_hash) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (batch_id, c.row_id, c.position, c.column, c.old_value,
                     c.new_value, c.rule_id, agent, timestamp, prev_hash, entry_hash),
                )
                prev_hash = entry_hash
        return batch_id

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0]


if __name__ == "__main__":
    import os

    from audit_log.dirty_data import generate_dirty_dataset
    from audit_log.rules import (rule_r1_fill_median, rule_r2_negative_to_abs,
                                 rule_r3_normalize_city, rule_r4_drop_duplicate)

    db = "test_audit_log.db"
    if os.path.exists(db):
        os.remove(db)

    store = AuditLogStore(db)
    df = generate_dirty_dataset().drop(columns="planted_defect")
    changes = (rule_r1_fill_median(df) + rule_r2_negative_to_abs(df)
               + rule_r3_normalize_city(df) + rule_r4_drop_duplicate(df))

    batch = store.append_batch(changes, agent="CleaningAgent")
    print("Batch id:       ", batch)
    print("Entries logged: ", store.count())

    print("\nFirst 3 entries:")
    for row in store.conn.execute(
        "SELECT entry_id, row_id, column_name, old_value, new_value, rule_id, "
        "substr(prev_hash,1,8) AS prev, substr(entry_hash,1,8) AS hash "
        "FROM audit_log LIMIT 3"
    ):
        print(dict(row))

    print("\nTrying to tamper through the normal API:")
    for sql in ["UPDATE audit_log SET new_value = 'HACKED' WHERE entry_id = 1",
                "DELETE FROM audit_log WHERE entry_id = 1"]:
        try:
            store.conn.execute(sql)
            print("  NOT BLOCKED:", sql)
        except sqlite3.DatabaseError as e:
            print("  blocked ->", e)

    print("\nEntries still in the log:", store.count())