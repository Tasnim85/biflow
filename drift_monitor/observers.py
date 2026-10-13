"""Observers: one per agent. Each turns the agent's month into an Observation
(input distributions + output metrics). The monitor only sees Observations.

Profiler and CleaningAgent are REAL. The other four are SIMULATED metric emitters.
"""

from dataclasses import dataclass, field

import numpy as np
from sklearn.ensemble import IsolationForest

from audit_log.dirty_data import generate_dirty_dataset
from audit_log.rules import (rule_r1_fill_median, rule_r2_negative_to_abs,
                             rule_r3_normalize_city, rule_r4_drop_duplicate)
from data.data_generator import FEATURES
from drift_monitor.scenario import build_scenario, get_training_batch


@dataclass(frozen=True)
class Metric:
    value: float
    kind: str = "value"           # "rate" -> p-chart, "value" -> mean +/- 3 sigma chart
    n: int | None = None          # sample size (rates only)
    min_rel_sigma: float = 0.0    # sigma floor, see stats.control_limits


@dataclass
class Observation:
    agent: str
    month: int
    inputs: dict = field(default_factory=dict)    # name -> array (for PSI / KS)
    metrics: dict = field(default_factory=dict)   # name -> Metric


class ProfilerObserver:
    """REAL. The model is trained ONCE on a separate batch, then frozen.
    A change of `contamination` only moves the decision threshold."""
    agent = "Profiler"

    def __init__(self):
        train = get_training_batch()[FEATURES]
        self.model = IsolationForest(n_estimators=100, contamination=0.03,
                                     random_state=42).fit(train)
        self.train_scores = -self.model.score_samples(train)

    def observe(self, cfg, df) -> Observation:
        X = df[FEATURES]
        scores = -self.model.score_samples(X)          # higher = more anomalous
        threshold = np.quantile(self.train_scores, 1 - cfg.profiler_contamination)
        return Observation(
            self.agent, cfg.month,
            inputs={f: X[f].to_numpy() for f in FEATURES},
            metrics={
                "anomaly_rate": Metric(float((scores > threshold).mean()), "rate", n=len(X)),
                "mean_score": Metric(float(scores.mean()), "value", min_rel_sigma=0.01),
            },
        )


class CleaningObserver:
    """REAL. Counts the changes each rule proposes (nothing is written to any log)."""
    agent = "CleaningAgent"

    def observe(self, cfg, df) -> Observation:
        dirty = generate_dirty_dataset(seed=cfg.month, base=df).drop(columns="planted_defect")
        rules = {"R1_changes": rule_r1_fill_median, "R2_changes": rule_r2_negative_to_abs,
                 "R3_changes": rule_r3_normalize_city, "R4_changes": rule_r4_drop_duplicate}
        return Observation(self.agent, cfg.month, metrics={
            name: Metric(float(len(fn(dirty))), "value", min_rel_sigma=0.05)
            for name, fn in rules.items()
        })


class _Simulated:
    agent = ""
    idx = 0

    def _rng(self, month):
        return np.random.default_rng(7000 + self.idx * 100 + month)


class EtlObserver(_Simulated):
    """SIMULATED. Share of received rows that were loaded."""
    agent, idx = "ETL", 1

    def observe(self, cfg, df) -> Observation:
        ratio = 0.99 + self._rng(cfg.month).normal(0, 0.003) - cfg.etl_loss_rate
        return Observation(self.agent, cfg.month,
                           metrics={"load_ratio": Metric(float(ratio), "value", min_rel_sigma=0.01)})


class KpiObserver(_Simulated):
    """SIMULATED. Share of KPIs computed without missing values."""
    agent, idx = "SemanticKPI", 2

    def observe(self, cfg, df) -> Observation:
        rate = 0.97 + self._rng(cfg.month).normal(0, 0.005)
        return Observation(self.agent, cfg.month,
                           metrics={"kpi_success_rate": Metric(float(rate), "value", min_rel_sigma=0.01)})


class AnalystObserver(_Simulated):
    """SIMULATED. Number of insights generated."""
    agent, idx = "Analyst", 3

    def observe(self, cfg, df) -> Observation:
        n = round(12 + self._rng(cfg.month).normal(0, 0.5))
        return Observation(self.agent, cfg.month,
                           metrics={"insights_count": Metric(float(n), "value", min_rel_sigma=0.05)})


class DashboardObserver(_Simulated):
    """SIMULATED. Share of charts flagged as misleading."""
    agent, idx = "Dashboard", 4

    def observe(self, cfg, df) -> Observation:
        share = max(0.0, 0.10 + self._rng(cfg.month).normal(0, 0.005))
        return Observation(self.agent, cfg.month,
                           metrics={"misleading_share": Metric(float(share), "value", min_rel_sigma=0.10)})


def collect_observations() -> list[Observation]:
    observers = [ProfilerObserver(), CleaningObserver(), EtlObserver(),
                 KpiObserver(), AnalystObserver(), DashboardObserver()]
    return [o.observe(cfg, df)
            for _, (cfg, df) in build_scenario().items()
            for o in observers]


if __name__ == "__main__":
    for obs in collect_observations():
        values = ", ".join(f"{k}={m.value:.3f}" for k, m in obs.metrics.items())
        print(f"month {obs.month} | {obs.agent:<13} | {values}")