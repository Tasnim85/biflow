"""Pure statistical tools: PSI, KS test, p-chart, control chart."""

import numpy as np
from scipy import stats as sps

PSI_WATCH = 0.10    # industry convention, not a law
PSI_DRIFT = 0.25
KS_ALPHA = 0.01


def psi(reference, current, bins: int = 10) -> float:
    """Population Stability Index. Bins are built on the REFERENCE quantiles."""
    reference = np.asarray(reference, float)
    current = np.asarray(current, float)
    edges = np.quantile(reference, np.linspace(0, 1, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    edges = np.unique(edges)                       # discrete data can repeat quantiles
    ref_pct = np.histogram(reference, bins=edges)[0] / len(reference)
    cur_pct = np.histogram(current, bins=edges)[0] / len(current)
    ref_pct = np.clip(ref_pct, 1e-4, None)         # avoid log(0)
    cur_pct = np.clip(cur_pct, 1e-4, None)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def ks_test(reference, current) -> tuple[float, float]:
    """Returns (KS statistic D, p-value)."""
    r = sps.ks_2samp(reference, current)
    return float(r.statistic), float(r.pvalue)


def p_chart_limits(p0: float, n: int, k: float = 3.0) -> tuple[float, float]:
    """Control limits for a proportion: p0 +/- k * sqrt(p0 (1 - p0) / n)."""
    sigma = np.sqrt(p0 * (1 - p0) / n)
    return max(0.0, p0 - k * sigma), min(1.0, p0 + k * sigma)


def control_limits(values, k: float = 3.0, min_rel_sigma: float = 0.0):
    """Mean +/- k sigma. Returns (center, lower, upper).

    With only 3 reference points sigma is poorly estimated, so we impose a
    floor on it (min_rel_sigma * |mean|). This is an explicit assumption.
    """
    values = np.asarray(values, float)
    center = float(values.mean())
    sigma = max(float(values.std(ddof=1)), min_rel_sigma * abs(center))
    return center, center - k * sigma, center + k * sigma


if __name__ == "__main__":
    rng = np.random.default_rng(0)
    ref = rng.normal(0, 1, 1500)
    same = rng.normal(0, 1, 500)
    shifted = rng.normal(1, 1, 500)

    print("PSI same distribution:  ", round(psi(ref, same), 3), "(expected < 0.1)")
    print("PSI shifted by 1 sigma: ", round(psi(ref, shifted), 3), "(expected > 0.25)")
    print("KS same:    D=%.3f p=%.3f   (expected small D, large p)" % ks_test(ref, same))
    print("KS shifted: D=%.3f p=%.2g   (expected large D, tiny p)" % ks_test(ref, shifted))
    print("p-chart p0=0.03, n=500:", tuple(round(x, 3) for x in p_chart_limits(0.03, 500)),
          "(expected about (0.007, 0.053))")
    print("control [10, 11, 9]:   ", control_limits([10, 11, 9]), "(expected (10.0, 7.0, 13.0))")
    print("control [8, 8, 8], floor 5%:", control_limits([8, 8, 8], min_rel_sigma=0.05),
          "(expected (8.0, 6.8, 9.2))")