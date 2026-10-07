"""BIFlow XAI Auditor prototype: Streamlit UI only. No business logic here."""

import streamlit as st
import matplotlib.pyplot as plt

from xai.narrator import LABELS
from agents.auditor_agent import AuditorAgent
from agents.profiler_agent import run_profiler
from data.data_generator import FEATURES, generate_dataset

st.set_page_config(page_title="BIFlow XAI Auditor", layout="wide")


@st.cache_resource
def load_system():
    """Runs once: generate data, run the Profiler, create the Auditor."""
    result = run_profiler(generate_dataset())
    return result, AuditorAgent(result)


profiler_result, auditor = load_system()
data = profiler_result.data

st.title("BIFlow: XAI Auditor Prototype")
st.caption("Decision → Explanation → Evidence → Audit trail")

# ---- Section 1: Data quality / anomaly detection ------------------------
st.header("1. Data Quality / Anomaly Detection")

c1, c2, c3 = st.columns(3)
c1.metric("Rows analyzed", len(data))
c2.metric("Anomalies detected", int(data["is_anomaly"].sum()))
c3.metric("Contamination assumed", f"{profiler_result.contamination:.0%}")

flagged = data[data["is_anomaly"]].sort_values("anomaly_score", ascending=False)
st.subheader("Flagged observations")
st.dataframe(flagged[FEATURES + ["anomaly_score"]].round(2), use_container_width=True)

# ---- Section 2: Choose an observation -----------------------------------
st.header("2. Select an observation to audit")
scope = st.radio(
    "Which observations?",
    ["Flagged as anomalies", "Normal observations"],
    horizontal=True,
)
if scope == "Flagged as anomalies":
    options = flagged.index.tolist()
else:
    options = data[~data["is_anomaly"]].index.tolist()
row_index = st.selectbox("Observation (row index)", options=options)

st.write("Selected observation:")
st.dataframe(data.loc[[row_index], FEATURES + ["anomaly_score", "is_anomaly"]].round(2))



# ---- Section 3: Audit the selected observation ---------------------------
st.header("3. XAI Audit")

if st.button("Run audit on selected observation", type="primary"):
    st.session_state["record"] = auditor.audit_row(row_index)

record = st.session_state.get("record")

if record is None:
    st.info("Select an observation above and click the button to run the audit.")
else:
    entry = record.log_entry

    # Decision
    st.subheader("Decision")
    if entry["decision"] == "Anomaly detected":
        st.error(f"Observation {entry['observation']}: {entry['decision']} (score {entry['anomaly_score']})")
    else:
        st.success(f"Observation {entry['observation']}: {entry['decision']} (score {entry['anomaly_score']})")

    # Explanation
    st.subheader("Auditor explanation")
    st.write(record.narrative)

    # Evidence
    st.subheader("Evidence: SHAP contributions")
    contrib = record.explanation.contributions.copy()
    contrib["label"] = contrib["feature"].map(LABELS)

    left, right = st.columns([3, 2])

    with left:
        plot_df = contrib.iloc[::-1]  # reverse so the largest bar is on top
        fig, ax = plt.subplots(figsize=(6, 3))
        colors = ["#d62728" if v > 0 else "#1f77b4" for v in plot_df["shap_value"]]
        ax.barh(plot_df["label"], plot_df["shap_value"], color=colors)
        ax.axvline(0, color="black", linewidth=0.8)
        ax.set_xlabel("Contribution in splits (red = toward anomaly, blue = toward normal)")
        fig.tight_layout()
        st.pyplot(fig)

    with right:
        st.dataframe(
            contrib[["label", "value", "shap_value"]].round(3).rename(
                columns={"label": "Feature", "value": "Value", "shap_value": "SHAP (splits)"}
            ),
            use_container_width=True,
            hide_index=True,
        )

    st.caption(
        "SHAP explains the model's score, not business truth. Contributions are in "
        "isolation-path splits and add up exactly to the gap between a typical row "
        "and this row."
    )
        # Ground-truth check (demo only: the model never saw these columns)
    FEATURE_OF_TYPE = {"A": "transaction_amount", "B": "num_transactions", "C": "income"}
    truth = data.loc[entry["observation"], "anomaly_type"]
    top_feature = record.explanation.contributions.iloc[0]["feature"]

    with st.expander("Ground-truth check (demo only)"):
        if truth == "none":
            if entry["decision"] == "Anomaly detected":
                st.warning("This row was NOT a planted anomaly: the flag is a false alarm. "
                           "The explanation shows what made a normal row look unusual.")
            else:
                st.success("Correct: this row is normal and was not flagged.")
        else:
            planted = FEATURE_OF_TYPE[truth]
            st.write(f"Planted anomaly type **{truth}**: we tampered with **{LABELS[planted]}**.")
            if entry["decision"] != "Anomaly detected":
                st.warning("The model missed this planted anomaly (a false negative).")
            elif top_feature == planted:
                st.success(f"SHAP's top feature is **{LABELS[top_feature]}**: it matches the planted flaw.")
            else:
                st.warning(f"SHAP's top feature is **{LABELS[top_feature]}**, not the planted one. "
                           "The model reacted to a combination of features.")

# ---- Section 4: Audit trail ----------------------------------------------
st.header("4. Audit log")
log_df = auditor.log_as_dataframe()
if log_df.empty:
    st.write("No audits yet.")
else:
    short = log_df.drop(columns=["dataset", "rows_in_dataset", "model", "explainer", "explanation"])
    st.dataframe(short.iloc[::-1], use_container_width=True, hide_index=True)
    with st.expander("Full log entries (model settings and explanations)"):
        st.dataframe(log_df.iloc[::-1], use_container_width=True, hide_index=True)