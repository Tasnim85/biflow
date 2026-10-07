"""Narrator: turns SHAP numbers into a natural-language explanation.

Template-based on purpose: every word is traceable to a number.
"""

import pandas as pd

from xai.shap_explainer import ShapExplanation

# Pretty labels for the UI and sentences
LABELS = {
    "age": "Age",
    "income": "Income",
    "spending_score": "Spending Score",
    "transaction_amount": "Transaction Amount",
    "num_transactions": "Number of Transactions",
}


def _format_value(feature: str, value: float) -> str:
    if feature == "income":
        return f"{value:,.0f}"
    if feature == "transaction_amount":
        return f"{value:,.2f}"
    return f"{value:,.0f}"


def _compare_to_typical(feature: str, value: float, typical: float) -> str:
    """Describe the value relative to the dataset median."""
    if typical == 0:
        return "different from"
    ratio = value / typical
    if ratio >= 2:
        return "far above"
    if ratio >= 1.3:
        return "above"
    if ratio <= 0.5:
        return "far below"
    if ratio <= 0.77:
        return "below"
    return "close to"


def top_features(explanation: ShapExplanation, k: int = 2, min_share: float = 0.10) -> pd.DataFrame:
    """Features that pushed TOWARD anomaly and carry a meaningful share of the push."""
    c = explanation.contributions
    positive = c[c["shap_value"] > 0]
    total = positive["shap_value"].sum()
    if total == 0:
        return positive.head(0)
    positive = positive.assign(share=positive["shap_value"] / total)
    return positive[positive["share"] >= min_share].head(k)


def narrate(
    explanation: ShapExplanation,
    is_anomaly: bool,
    medians: pd.Series,
    k: int = 2,
) -> str:
    """Build the explanation sentence for one observation."""
    typical_splits = -explanation.base_value
    this_splits = -explanation.model_output

    # Guard: a non-flagged row isolated about as slowly as a typical row
    # has nothing meaningful to blame. Percentages of a tiny push would mislead.
    if not is_anomaly and this_splits >= typical_splits - 1.0:
        return (
            f"Not flagged. The model needed {this_splits:.1f} splits to isolate this "
            f"observation, versus {typical_splits:.1f} for a typical row. "
            f"It looks like an ordinary observation: no feature pushed it "
            f"meaningfully toward anomaly."
        )

    top = top_features(explanation, k=k)
    if top.empty:
        return "No single feature stands out; the model's score is close to a typical row."

    parts = []
    for _, r in top.iterrows():
        f = r["feature"]
        label = LABELS.get(f, f)
        rel = _compare_to_typical(f, r["value"], medians[f])
        parts.append(
            f"{label} ({_format_value(f, r['value'])}, {rel} the typical "
            f"{_format_value(f, medians[f])}) accounted for {r['share']:.0%} of the push toward anomaly"
        )
    joined = " and ".join(parts)

    if is_anomaly:
        return (
            f"Flagged as anomalous because {joined}. "
            f"The model isolated this observation in {this_splits:.1f} splits, "
            f"versus {typical_splits:.1f} for a typical row."
        )
    return (
        f"Not flagged. The most unusual aspects were {joined}, "
        f"but not enough to cross the anomaly threshold. "
        f"Isolation took {this_splits:.1f} splits versus {typical_splits:.1f} for a typical row."
    )

if __name__ == "__main__":
    from agents.profiler_agent import run_profiler
    from data.data_generator import FEATURES, generate_dataset
    from xai.shap_explainer import build_explainer, explain_row

    result = run_profiler(generate_dataset())
    X = result.data[FEATURES]
    medians = X.median()
    explainer = build_explainer(result.model)

    for idx in [30, 354, 217]:
        exp = explain_row(explainer, X, idx)
        is_anom = bool(result.data.loc[idx, "is_anomaly"])
        print(f"\nRow {idx}:")
        print(narrate(exp, is_anom, medians))