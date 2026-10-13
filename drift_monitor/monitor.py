"""DriftMonitor (Auditor in supervision mode). Read-only on the agents.

It NEVER imports PLANTED_TRUTH: it only knows the reference months.
Decision rule (fixed, written in plain language):
  data drift     = at least one input variable with PSI > 0.25
  decision drift = at least one output metric outside its control limits
"""

from dataclasses import dataclass, field

import numpy as np

from audit_log.log_store import AuditLogStore
from audit_log.rules import Change
from drift_monitor import stats
from drift_monitor.observers import Observation, collect_observations
from drift_monitor.scenario import N_MONTHS, REFERENCE_MONTHS
from xai.narrator import LABELS

MONITOR_AGENT = "DriftMonitor"

ALERT_RULES = {
    "D1_data_drift": "An input variable has a PSI above 0.25 compared with the reference months.",
    "D2_decision_drift": "An output metric of an agent is outside the control limits computed on the reference months.",
    "D3_diagnosis": "Cross-check of data drift and decision drift to guess the cause of a change.",
}


@dataclass
class InputCheck:
    agent: str
    name: str
    psi: float
    ks_stat: float
    ks_p: float
    flagged: bool          # PSI > 0.25
    agreement: str         # "agree" | "KS only" | "PSI only"


@dataclass
class MetricCheck:
    agent: str
    name: str
    value: float
    center: float
    lower: float
    upper: float
    out_of_control: bool


@dataclass
class MonthReport:
    month: int
    status: str            # reference | stable | data_drift | data_drift_only | agent_changed
    narrative: str
    input_checks: list = field(default_factory=list)
    metric_checks: list = field(default_factory=list)
    flagged_agents: list = field(default_factory=list)


class DriftMonitor:
    def __init__(self):
        self._ref_inputs: dict = {}
        self._ref_metrics: dict = {}

    # ---- reference ("normal") -------------------------------------------------
    def fit_reference(self, observations: list[Observation]) -> None:
        for o in observations:
            for name, arr in o.inputs.items():
                self._ref_inputs.setdefault((o.agent, name), []).append(arr)
            for name, m in o.metrics.items():
                d = self._ref_metrics.setdefault(
                    (o.agent, name),
                    {"kind": m.kind, "floor": m.min_rel_sigma, "values": [], "ns": []})
                d["values"].append(m.value)
                d["ns"].append(m.n)
        self._ref_inputs = {k: np.concatenate(v) for k, v in self._ref_inputs.items()}

    def reference_input(self, agent: str, name: str):
        return self._ref_inputs[(agent, name)]

    def metric_names(self, agent: str) -> list:
        return [n for (a, n) in self._ref_metrics if a == agent]

    def limits(self, agent: str, name: str, n: int | None = None):
        d = self._ref_metrics[(agent, name)]
        if d["kind"] == "rate":
            p0 = sum(v * k for v, k in zip(d["values"], d["ns"])) / sum(d["ns"])
            lo, hi = stats.p_chart_limits(p0, n or d["ns"][0])
            return p0, lo, hi
        return stats.control_limits(d["values"], min_rel_sigma=d["floor"])

    # ---- detection + diagnosis ----------------------------------------------------
    def check_month(self, observations: list[Observation]) -> MonthReport:
        month = observations[0].month
        input_checks, metric_checks = [], []

        for o in observations:
            for name, arr in o.inputs.items():
                ref = self._ref_inputs[(o.agent, name)]
                p = stats.psi(ref, arr)
                d, pv = stats.ks_test(ref, arr)
                flagged, ks_flag = p > stats.PSI_DRIFT, pv < stats.KS_ALPHA
                agreement = "agree" if flagged == ks_flag else ("KS only" if ks_flag else "PSI only")
                input_checks.append(InputCheck(o.agent, name, p, d, pv, flagged, agreement))
            for name, m in o.metrics.items():
                center, lo, hi = self.limits(o.agent, name, m.n)
                metric_checks.append(MetricCheck(o.agent, name, m.value, center, lo, hi,
                                                 not (lo <= m.value <= hi)))

        data_flags = [c for c in input_checks if c.flagged]
        out_flags = [c for c in metric_checks if c.out_of_control]
        agents_out = sorted({c.agent for c in out_flags})

        data_txt = ", ".join(f"{LABELS.get(c.name, c.name)} (PSI {c.psi:.2f})" for c in data_flags)
        out_txt = ", ".join(f"{c.agent}.{c.name} = {c.value:.3f} (limits {c.lower:.3f} to {c.upper:.3f})"
                            for c in out_flags)

        if data_flags and agents_out:
            status = "data_drift"
            text = (f"Month {month}: the input data changed ({data_txt}) and the decisions changed too "
                    f"({out_txt}). The decisions most likely follow the data (for example a new customer "
                    f"segment). Check that this change is legitimate.")
        elif data_flags:
            status = "data_drift_only"
            text = (f"Month {month}: the input data changed ({data_txt}) but no agent output left its "
                    f"control limits. The models may no longer fit the data: keep watching.")
        elif agents_out:
            status = "agent_changed"
            text = (f"Month {month}: the input data is stable, yet {', '.join(agents_out)} behave "
                    f"differently ({out_txt}). The change does not come from the data: suspect a setting "
                    f"change, a bug or a replaced model.")
        else:
            status = "stable"
            text = f"Month {month}: inputs and outputs are within the reference limits."

        text += " This is a diagnosis, not a proof: a human decides."
        return MonthReport(month, status, text, input_checks, metric_checks, agents_out)

    # ---- alerts -> append-only log entries ------------------------------------------
    def alerts_as_changes(self, report: MonthReport) -> list[Change]:
        changes = []
        for c in report.input_checks:
            if c.flagged:
                changes.append(Change(report.month, 0, f"{c.agent}.{c.name}", "reference",
                                      f"PSI={c.psi:.3f}", "D1_data_drift"))
        for c in report.metric_checks:
            if c.out_of_control:
                changes.append(Change(report.month, 0, f"{c.agent}.{c.name}",
                                      f"limits [{c.lower:.4f}, {c.upper:.4f}]",
                                      f"{c.value:.4f}", "D2_decision_drift"))
        if report.status != "stable":
            changes.append(Change(report.month, 0, "diagnosis", "stable", report.status, "D3_diagnosis"))
        return changes


@dataclass
class MonitoringRun:
    monitor: DriftMonitor
    observations: list
    reports: dict


def run_full_monitoring(store: AuditLogStore | None = None) -> MonitoringRun:
    observations = collect_observations()
    by_month: dict = {}
    for o in observations:
        by_month.setdefault(o.month, []).append(o)

    monitor = DriftMonitor()
    monitor.fit_reference([o for o in observations if o.month in REFERENCE_MONTHS])

    reports = {}
    for m in range(1, N_MONTHS + 1):
        if m in REFERENCE_MONTHS:
            reports[m] = MonthReport(m, "reference", "Reference month: it defines 'normal'.")
            continue
        report = monitor.check_month(by_month[m])
        reports[m] = report
        if store is not None:
            changes = monitor.alerts_as_changes(report)
            if changes:
                store.append_batch(changes, agent=MONITOR_AGENT, batch_id=f"drift-month-{m}")
    return MonitoringRun(monitor, observations, reports)


if __name__ == "__main__":
    import os

    from audit_log.log_auditor import LogAuditor
    from drift_monitor.scenario import PLANTED_TRUTH

    db = "test_drift_log.db"
    if os.path.exists(db):
        os.remove(db)
    store = AuditLogStore(db, extra_rules=ALERT_RULES)
    run = run_full_monitoring(store)

    for m, r in run.reports.items():
        print(f"\nMonth {m} | planted: {PLANTED_TRUTH[m]:<13} | detected: {r.status:<15} "
              f"| agents flagged: {r.flagged_agents or '-'}")
        print("  ", r.narrative)

    print("\nAlerts logged:", store.count())
    print(LogAuditor(store).verify_integrity())