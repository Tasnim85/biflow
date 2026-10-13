"""Prototype 3 view: drift monitoring. Display only, no business logic."""

import os

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from audit_log.log_auditor import LogAuditor
from audit_log.log_store import AuditLogStore
from data.data_generator import FEATURES
from drift_monitor.monitor import ALERT_RULES, run_full_monitoring
from drift_monitor.scenario import N_MONTHS, PLANTED_TRUTH, REFERENCE_MONTHS
from xai.narrator import LABELS

DB_PATH = "app_drift_log.db"
EXPECTED = {"stable": "reference", "data_drift": "data_drift",
            "agent_changed": "agent_changed", "etl_bug": "agent_changed"}


@st.cache_resource
def load_run():
    """Runs once: simulate 6 months, monitor them, write the alerts to the log."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    store = AuditLogStore(DB_PATH, extra_rules=ALERT_RULES)
    return store, run_full_monitoring(store)


store, run = load_run()
monitor, reports = run.monitor, run.reports
obs = {(o.month, o.agent): o for o in run.observations}
months = list(range(1, N_MONTHS + 1))
agents = sorted({o.agent for o in run.observations})

st.title("Drift: Monitor the agents over time")
st.caption("Observed behaviour → Comparison with the reference → Alert → Diagnosis of the cause")
st.info(f"Reference months: {REFERENCE_MONTHS}. Profiler and CleaningAgent are real; "
        "ETL, SemanticKPI, Analyst and Dashboard are simulated metric emitters.")

# ---- 1. Summary --------------------------------------------------------------
st.header("1. Diagnosis per month")
rows = []
for m in months:
    r, truth = reports[m], PLANTED_TRUTH[m]
    if r.status == "reference":
        match = "reference"
    else:
        ok = EXPECTED[truth] == r.status
        if truth == "etl_bug":
            ok = ok and r.flagged_agents == ["ETL"]
        match = "✅" if ok else "❌"
    rows.append({"Month": m, "Detected": r.status,
                 "Agents flagged": ", ".join(r.flagged_agents) or "-",
                 "Planted truth (demo only)": truth, "Match": match})
st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
st.caption("The monitor never sees the planted truth: it is only compared here, after the fact.")

# ---- 2. Control charts ---------------------------------------------------------
st.header("2. Control charts (decision drift)")
agent = st.selectbox("Agent", agents)
names = monitor.metric_names(agent)
cols = st.columns(2)
for i, name in enumerate(names):
    values = [obs[(m, agent)].metrics[name].value for m in months]
    center, lo, hi = monitor.limits(agent, name)
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.axvspan(0.5, max(REFERENCE_MONTHS) + 0.5, color="#cccccc", alpha=0.4, label="reference")
    ax.axhline(center, color="black", linewidth=0.8)
    ax.axhline(lo, color="#d62728", linestyle="--", linewidth=0.8)
    ax.axhline(hi, color="#d62728", linestyle="--", linewidth=0.8)
    ax.plot(months, values, marker="o", color="#1f77b4")
    for m, v in zip(months, values):
        if m not in REFERENCE_MONTHS and not (lo <= v <= hi):
            ax.plot(m, v, "o", color="#d62728", markersize=10)
    ax.set_title(name)
    ax.set_xlabel("Month")
    ax.legend(loc="upper left", fontsize=7)
    fig.tight_layout()
    cols[i % 2].pyplot(fig)
st.caption("Grey = reference months. Dashed red = control limits. Red dot = out of control.")

# ---- 3. Data drift --------------------------------------------------------------
st.header("3. Data drift (Profiler inputs)")
psi_table = pd.DataFrame(
    {m: {LABELS[c.name]: round(c.psi, 3) for c in reports[m].input_checks}
     for m in months if m not in REFERENCE_MONTHS})
st.dataframe(psi_table, use_container_width=True)
st.caption("PSI < 0.10 stable, 0.10 to 0.25 watch, > 0.25 drift (industry convention, not a law).")

c1, c2 = st.columns(2)
feature = c1.selectbox("Variable", FEATURES, format_func=lambda f: LABELS[f])
month_h = c2.selectbox("Month", [m for m in months if m not in REFERENCE_MONTHS], index=0)
fig, ax = plt.subplots(figsize=(6, 3))
ax.hist(monitor.reference_input("Profiler", feature), bins=30, density=True,
        alpha=0.5, label="reference (months 1-3)")
ax.hist(obs[(month_h, "Profiler")].inputs[feature], bins=30, density=True,
        alpha=0.5, label=f"month {month_h}")
ax.legend()
fig.tight_layout()
st.pyplot(fig)

# ---- 4. Diagnosis detail ----------------------------------------------------------
st.header("4. Diagnosis detail")
month_d = st.selectbox("Month to inspect", months, index=3)
r = reports[month_d]
if r.status in ("stable", "reference"):
    st.success(r.narrative)
elif r.status == "agent_changed":
    st.error(r.narrative)
else:
    st.warning(r.narrative)
flagged = [{"Agent": c.agent, "Metric": c.name, "Value": round(c.value, 4),
            "Lower": round(c.lower, 4), "Upper": round(c.upper, 4)}
           for c in r.metric_checks if c.out_of_control]
if flagged:
    st.write("**Metrics outside their limits**")
    st.dataframe(pd.DataFrame(flagged), hide_index=True, use_container_width=True)
disagree = [c for c in r.input_checks if c.agreement != "agree"]
if disagree:
    st.write("**PSI and KS disagree on:** " +
             ", ".join(f"{LABELS[c.name]} ({c.agreement})" for c in disagree))

# ---- 5. Alerts in the append-only log -----------------------------------------------
st.header("5. Alerts in the append-only log")
log_df = pd.read_sql_query(
    "SELECT entry_id, row_id AS month, column_name, old_value, new_value, rule_id, agent, "
    "timestamp, substr(prev_hash,1,8) AS prev_hash, substr(entry_hash,1,8) AS entry_hash "
    "FROM audit_log ORDER BY entry_id", store.conn)
st.dataframe(log_df, hide_index=True, use_container_width=True)

if st.button("Verify the alert log", type="primary"):
    st.session_state["drift_integrity"] = LogAuditor(store).verify_integrity()
rep = st.session_state.get("drift_integrity")
if rep is not None:
    (st.success if rep.ok else st.error)(f"{rep.problem} ({rep.entries_checked} entries checked)")