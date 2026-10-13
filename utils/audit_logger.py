"""Audit logger: an append-only list of timestamped pipeline events."""

from datetime import datetime

import pandas as pd

COLUMNS = ["timestamp", "stage", "event", "status", "details"]


class AuditLogger:
    def __init__(self):
        self._entries = []

    def log(self, stage, event, status="INFO", details=None):
        """Add one entry. status is INFO, PASS or FAIL."""
        entry = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "stage": stage,
            "event": event,
            "status": status,
            "details": details or {},
        }
        self._entries.append(entry)
        return entry

    @property
    def entries(self):
        """A copy of the entries, so callers cannot modify the log."""
        return list(self._entries)

    def __len__(self):
        return len(self._entries)

    def as_lines(self):
        """Human-readable lines such as: [10:32:01] Validator: Grain check executed [FAIL]"""
        lines = []
        for entry in self._entries:
            time_part = entry["timestamp"].split("T")[1]
            line = f"[{time_part}] {entry['stage']}: {entry['event']}"
            if entry["status"] != "INFO":
                line += f" [{entry['status']}]"
            lines.append(line)
        return lines

    def as_dataframe(self):
        """The log as a table, ready for st.dataframe later."""
        if not self._entries:
            return pd.DataFrame(columns=COLUMNS)
        df = pd.DataFrame(self._entries, columns=COLUMNS)
        df["details"] = df["details"].apply(
            lambda d: ", ".join(f"{key}={value}" for key, value in d.items())
        )
        return df