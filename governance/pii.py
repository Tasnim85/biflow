"""Local deterministic PII recognition and session-scoped HMAC pseudonyms.

No reversible mapping is stored. Not anonymization, not production NER.
"""
from dataclasses import dataclass
import hashlib
import hmac
import re

import pandas as pd
from data.pii_generator import DEMO_NAMES

PATTERNS = [
    ("EMAIL", re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)),
    ("PHONE", re.compile(r"(?<!\w)\+1[- .]?\d{3}[- .]?\d{3}[- .]?\d{4}(?!\d)")),
    ("DEMO_IDENTIFIER", re.compile(r"\bDEMO-ID-\d{6}\b", re.I)),
    ("PERSON", re.compile(r"\b(?:" + "|".join(map(re.escape, DEMO_NAMES)) + r")\b", re.I)),
]
ROLES = {"full_name": "PERSON", "email": "EMAIL", "phone": "PHONE", "national_id": "DEMO_IDENTIFIER"}


@dataclass
class PIIResult:
    data: pd.DataFrame
    detections: pd.DataFrame
    manifest: dict


def protect_pii(source, key, mode="pseudonymize", sensitive_types=None):
    selected = set(ROLES.values()) if sensitive_types is None else set(sensitive_types)
    if not selected <= set(ROLES.values()):
        raise ValueError("Unknown sensitive category")
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("A secret key of at least 32 bytes is required")
    if mode not in {"pseudonymize", "mask"}:
        raise ValueError("Unknown PII policy")
    if not source.columns.is_unique:
        raise ValueError("Column names must be unique")
    out = source.copy(deep=True)
    events = []

    def replacement(kind, value):
        if mode == "mask":
            return f"[MASKED_{kind}]"
        normalized = " ".join(value.strip().casefold().split())
        if kind == "PHONE":
            normalized = re.sub(r"\D", "", normalized)
        digest = hmac.new(key, (kind + ":" + normalized).encode(), hashlib.sha256).hexdigest()[:32]
        return f"[{kind}_{digest}]"

    for column in source.columns:
        for position, value in enumerate(source[column]):
            if not isinstance(value, str) or not value.strip():
                continue
            spans = []
            if column in ROLES:
                spans = [(0, len(value), ROLES[column], "declared_column_role")]
            else:
                for kind, pattern in PATTERNS:
                    for match in pattern.finditer(value):
                        spans.append((match.start(), match.end(), kind, "dictionary" if kind == "PERSON" else "regex"))
            accepted = []
            for span in sorted(spans, key=lambda s: (s[0], -(s[1] - s[0]))):
                if not accepted or span[0] >= accepted[-1][1]:
                    accepted.append(span)
            protected = value
            for start, end, kind, method in reversed(accepted):
                if kind in selected:
                    protected = protected[:start] + replacement(kind, value[start:end]) + protected[end:]
                # Never put raw PII, plaintext hashes or secret keys in the audit.
                events.append({"row_position": position, "column": column, "entity": kind,
                               "method": method, "action": mode if kind in selected else "detected_only"})
            if protected != value:
                out[column] = out[column].astype(object)
                out.iat[position, out.columns.get_loc(column)] = protected
    report = pd.DataFrame(events, columns=["row_position", "column", "entity", "method", "action"])
    return PIIResult(out, report, {
        "policy_id": "pii-demo", "policy_version": "1.1.0", "approval_scope": "demo_only",
        "sensitive_types": sorted(selected),
        "mode": mode, "rows": len(out), "detections": len(report),
        "token_scope": "same key and entity type; session key is never exported",
        "mapping_storage": "none", "recognizers": ["column roles", "regex", "synthetic name dictionary"],
        "limitations": "No general NER, no global phone or national ID coverage; pseudonymization is not anonymization",
    })
