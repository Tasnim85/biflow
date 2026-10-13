"""Deterministic, context-bound cleaning with explicit review events."""

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
import math
import re
from pathlib import Path

import pandas as pd

POLICY_DIR = Path(__file__).resolve().parents[1] / "policies"
EVENT_COLUMNS = ["row_position", "column", "rule", "action", "before", "after", "reason"]


def load_policy(version):
    if version not in {"1.0.0", "1.1.0", "1.2.0"}:
        raise ValueError("Unknown policy version")
    return json.loads((POLICY_DIR / f"customers-{version}.json").read_text(encoding="utf-8"))


@dataclass
class CleaningResult:
    data: pd.DataFrame
    events: pd.DataFrame
    manifest: dict

    @property
    def review_positions(self):
        return sorted(self.events.loc[self.events.action == "review", "row_position"].unique().tolist())


def clean_dataset(df, policy, context="synthetic_customers"):
    """DQ selects a context; SEM validates declared roles; ETL executes.

    Approval metadata describes repository demo policies, not external sign-off.
    Source row positions stay stable; ambiguous duplicates are never dropped.
    """
    if policy.get("context") != context or policy.get("status") != "approved_demo":
        raise ValueError("Policy is not approved for this dataset context")
    if not df.columns.is_unique:
        raise ValueError("Column names must be unique")
    roles = policy["roles"]
    allowed = {"review_missing", "fill_category", "normalize_date", "review_duplicates", "normalize_numeric"}
    for rule in policy["rules"]:
        if rule["action"] not in allowed:
            raise ValueError("Unsupported policy action")
        col = rule["column"]
        if col not in roles:
            raise ValueError(f"Missing semantic role: {col}")
        if rule["action"] == "normalize_numeric" and roles[col] not in {"numeric", "financial"}:
            raise ValueError("Numeric normalization requires a numeric or financial role")
        if rule["action"] == "fill_category" and roles[col] != "category":
            raise ValueError("Category replacement requires a categorical role")
        if rule["action"] == "normalize_date" and roles[col] != "date":
            raise ValueError("Date normalization requires a date role")
        if col not in df and not rule.get("optional", False):
            raise ValueError(f"Required column absent: {col}")

    out = df.copy(deep=True)
    events = []
    skipped = []

    def record(pos, col, rule, action, before, after, reason):
        events.append(dict(zip(EVENT_COLUMNS, [pos, col, rule["id"], action,
                                               str(before), str(after), reason])))

    for rule in policy["rules"]:
        col, action = rule["column"], rule["action"]
        if col not in out:
            skipped.append(rule["id"])
            continue
        series = out[col]
        if action == "review_duplicates":
            mask = series.notna() & series.duplicated(keep=False)
            for pos in range(len(out)):
                if mask.iloc[pos]:
                    record(pos, col, rule, "review", series.iloc[pos], series.iloc[pos],
                           "Duplicate identifier; no approved resolution")
            continue
        for pos in range(len(out)):
            value = out.iloc[pos][col]
            missing = pd.isna(value) or (isinstance(value, str) and not value.strip())
            if missing:
                if action == "fill_category":
                    out[col] = out[col].astype(object)
                    out.iat[pos, out.columns.get_loc(col)] = rule["value"]
                    record(pos, col, rule, "change", value, rule["value"], "Approved missing category")
                else:
                    record(pos, col, rule, "review", value, value, "Missing value; no automatic replacement")
            elif action == "normalize_numeric":
                token = str(value).strip()
                # Demo locale: comma is a decimal separator, never a grouping separator.
                token = token.replace(",", ".")
                valid = re.fullmatch(r"[+-]?\d+(?:\.\d+)?", token)
                number = float(token) if valid else float("nan")
                if (not math.isfinite(number) or number < rule.get("min", -math.inf)
                        or number > rule.get("max", math.inf)
                        or (rule.get("integer", False) and not number.is_integer())):
                    record(pos, col, rule, "review", value, value, "Invalid numeric value or domain constraint; manual review")
                elif isinstance(value, str):
                    out[col] = out[col].astype(object)
                    out.iat[pos, out.columns.get_loc(col)] = number
                    record(pos, col, rule, "change", value, number, "Approved decimal-comma numeric parsing and whitespace removal")
            elif action == "normalize_date":
                parsed = None
                for fmt in rule["formats"]:
                    try:
                        parsed = datetime.strptime(str(value), fmt).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        continue
                if parsed is None:
                    record(pos, col, rule, "review", value, value, "Unrecognized date format")
                elif parsed != value:
                    out[col] = out[col].astype(object)
                    out.iat[pos, out.columns.get_loc(col)] = parsed
                    record(pos, col, rule, "change", value, parsed, "Explicit approved date format")

    def fingerprint(frame):
        return sha256(frame.to_csv(index=True).encode()).hexdigest()

    manifest = {
        "policy_id": policy["id"], "policy_version": policy["version"],
        "policy_sha256": sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest(),
        "policy_snapshot": policy, "context": context,
        "input_sha256": fingerprint(df), "output_sha256": fingerprint(out),
        "rows": len(out), "skipped_optional_rules": skipped,
        "approval_scope": "Demonstration only; production requires business approval",
    }
    return CleaningResult(out, pd.DataFrame(events, columns=EVENT_COLUMNS), manifest)


def demo_quality_issues(df):
    """Explicit test copy of project data; does not alter its generator."""
    out = df.copy(deep=True)
    out["customer_id"] = [f"C{i:04d}" for i in range(len(out))]
    out["channel"] = "Web"
    out["signup_date"] = "2026-10-01"
    if len(out) >= 5:
        out.loc[out.index[0], "channel"] = None
        out.loc[out.index[1], "transaction_amount"] = float("nan")
        out.loc[out.index[2], "signup_date"] = "02/10/2026"
        out.loc[out.index[3], "signup_date"] = "invalid-date"
        out.loc[out.index[4], "customer_id"] = out.iloc[0]["customer_id"]
    return out
