"""BI Auditor / XAI Agent: explains a decision and records an audit trail.

Responsibility: it never makes the decision. It receives the Profiler's
decision, explains it with SHAP, narrates it, and logs everything.
"""

from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from agents.profiler_agent import ProfilerResult
from xai.narrator import LABELS, narrate, top_features
from xai.shap_explainer import ShapExplanation, build_explainer, explain_row


@dataclass
class AuditRecord:
    """Everything the UI needs to show for one audited observation."""
    log_entry: dict               # flat dictionary for the audit log table
    explanation: ShapExplanation  # numeric evidence (for the SHAP plot)
    narrative: str                # natural-language explanation


@dataclass
class AuditorAgent:
    profiler_result: ProfilerResult
    dataset_name: str = "Synthetic customers (demo)"
    audit_log: list = field(default_factory=list)

    def __post_init__(self):
        self._X = self.profiler_result.data[self.profiler_result.features]
        self._medians = self._X.median()
        self._explainer = build_explainer(self.profiler_result.model)

    def audit_row(self, row_index: int) -> AuditRecord:
        data = self.profiler_result.data

        # 1. The DECISION, taken from the Profiler (read-only)
        is_anomaly = bool(data.loc[row_index, "is_anomaly"])
        score = float(data.loc[row_index, "anomaly_score"])
        decision = "Anomaly detected" if is_anomaly else "Normal"

        # 2. The EVIDENCE: SHAP contributions for that row
        explanation = explain_row(self._explainer, self._X, row_index)

        # 3. The NATURAL-LANGUAGE explanation
        narrative = narrate(explanation, is_anomaly, self._medians)

        # 4. The AUDIT TRAIL entry
        typical_splits = -explanation.base_value
        this_splits = -explanation.model_output
        ordinary = (not is_anomaly) and this_splits >= typical_splits - 1.0
        top = top_features(explanation)
        top_names = [] if ordinary else [LABELS.get(f, f) for f in top["feature"]]
        pr = self.profiler_result
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dataset": self.dataset_name,
            "rows_in_dataset": len(data),
            "model": f"IsolationForest(n_estimators={pr.n_estimators}, "
                     f"contamination={pr.contamination}, random_state={pr.random_state})",
            "explainer": "SHAP TreeExplainer",
            "observation": row_index,
            "decision": decision,
            "anomaly_score": round(score, 3),
            "main_features": ", ".join(top_names) if top_names else "none",
            "explanation": narrative,
        }
        self.audit_log.append(entry)

        return AuditRecord(log_entry=entry, explanation=explanation, narrative=narrative)

    def log_as_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.audit_log)


if __name__ == "__main__":
    from agents.profiler_agent import run_profiler
    from data.data_generator import generate_dataset

    result = run_profiler(generate_dataset())
    auditor = AuditorAgent(result)

    # Audit an anomaly of type A, a false alarm candidate, and a normal row
    false_alarms = result.data[~result.data["true_anomaly"] & result.data["is_anomaly"]].index
    normal_row = result.data[~result.data["is_anomaly"]].index[0]

    for idx in [30, int(false_alarms[0]), int(normal_row)]:
        record = auditor.audit_row(idx)
        print(f"\n--- Row {idx} ---")
        print(record.log_entry["decision"], "| score", record.log_entry["anomaly_score"])
        print(record.narrative)

    print("\n=== Audit log ===")
    pd.set_option("display.max_colwidth", 60)
    pd.set_option("display.width", 200)
    print(auditor.log_as_dataframe().drop(columns=["explanation"]).to_string(index=False))