"""BIFlow KPI Governance prototype: Streamlit UI only. No business logic here."""

import pandas as pd
import streamlit as st

from agents.orchestrator import run_pipeline
from agents.semantic_kpi_agent import list_versions, load_definition

KPI_NAME = "Revenue"

SCENARIOS = {
    "Correct calculation: SUM(order_total) on orders": "correct",
    "Faulty calculation: join orders with order_items, then SUM": "faulty",
}


def key_value_table(values):
    """Display helper: dictionary -> two-column table of text."""
    return pd.DataFrame(
        {"Field": list(values.keys()), "Value": [str(v) for v in values.values()]}
    )


st.title("BIFlow: KPI Governance Auditor")
st.caption("Definition → Calculation → Validation → Evidence → Explanation → Audit trail")

# ---- Section 1: KPI definition -------------------------------------------
st.header("1. KPI Definition")

versions = list_versions(KPI_NAME)
version = st.selectbox("KPI version", options=versions, index=len(versions) - 1)
selected = load_definition(KPI_NAME, version)

c1, c2, c3, c4 = st.columns(4)
c1.metric("KPI", selected["name"])
c2.metric("Version", selected["version"])
c3.metric("Owner", selected["owner"])
c4.metric("Status", selected["status"].capitalize())

if selected["status"] != "approved":
    st.warning(
        f"Version {selected['version']} has status '{selected['status']}'. "
        "It is no longer the approved definition for official reporting."
    )

st.dataframe(
    key_value_table(
        {
            "Description": selected["description"],
            "Formula": selected["formula"],
            "Source": f"{selected['source_table']}.{', '.join(selected['source_columns'])}",
            "Aggregation grain": f"{selected['aggregation_grain']} (one row per {selected['grain_key']})",
            "Filters": ", ".join(selected["filters"]) or "none",
            "Definition file": selected["source_file"],
        }
    ),
    hide_index=True,
)

# ---- Section 2: Calculation ----------------------------------------------
st.header("2. Calculation")

scenario_label = st.radio(
    "Which calculation should the ETL Agent perform?",
    list(SCENARIOS),
    horizontal=True,
)

if st.button("Run calculation and validation", type="primary"):
    new_run = run_pipeline(KPI_NAME, version=version, scenario=SCENARIOS[scenario_label])
    st.session_state["kpi_run"] = new_run
    st.session_state.setdefault("kpi_history", []).append(
        new_run["explanation"]["log_entry"]
    )

run = st.session_state.get("kpi_run")

if run is None:
    st.info("Choose a version and a calculation above, then click the button to run the pipeline.")
    st.stop()

used = run["definition"]
calc = run["calc_result"]
validation = run["validation"]
explanation = run["explanation"]
checks = validation["checks"]
reference = next(c for c in checks if c["name"] == "reference_value")["evidence"]

st.caption(f"Results of the last run: {used['name']} v{used['version']}")

m1, m2, m3 = st.columns(3)
m1.metric("Reference Revenue", reference["reference"])
m2.metric(
    "Calculated Revenue",
    reference["calculated"],
    delta=reference["difference"] if reference["difference"] != 0 else None,
    delta_color="inverse",
)
m3.metric("Rows summed", calc["receipt"]["rows_summed"])

with st.expander("Calculation receipt (what the ETL Agent actually did)"):
    st.json(calc["receipt"])
with st.expander("Data that was summed"):
    st.dataframe(calc["data"], hide_index=True)

# ---- Section 3: Validation -----------------------------------------------
st.header("3. Validation")

title = f"{used['name']} v{used['version']}"
if validation["status"] == "FAIL":
    st.error(f"❌ KPI Validation FAILED ({title})")
else:
    st.success(f"✅ KPI Validation PASSED ({title})")

for check in checks:
    icon = "✅" if check["status"] == "PASS" else "❌"
    st.write(f"{icon} **{check['label']}**: {check['message']}")

# ---- Section 4: Evidence -------------------------------------------------
st.header("4. Evidence")

join_check = next(c for c in checks if c["name"] == "join_multiplicity")
duplicated = join_check["evidence"].get("duplicated_keys", {})
grain_key = used["grain_key"]

if duplicated:
    st.write(f"Rows whose `{grain_key}` appears more than once are highlighted:")
    styled = calc["data"].style.apply(
        lambda row: ["background-color: rgba(214, 39, 40, 0.25)"] * len(row)
        if row[grain_key] in duplicated
        else [""] * len(row),
        axis=1,
    )
    st.dataframe(styled, hide_index=True)

for check in checks:
    icon = "✅" if check["status"] == "PASS" else "❌"
    with st.expander(f"{icon} {check['label']}", expanded=(check["status"] == "FAIL")):
        st.dataframe(key_value_table(check["evidence"]), hide_index=True)

# ---- Section 5: Auditor explanation --------------------------------------
st.header("5. Auditor explanation")
st.write(explanation["narrative"])
st.caption(
    "Every sentence is a template filled with validation evidence: no free text "
    "generation, so the same evidence always gives the same explanation."
)

with st.expander("Ground-truth check (demo only)"):
    scenario = calc["scenario"]
    expected = "PASS" if scenario == "correct" else "FAIL"
    st.write(
        f"The ETL Agent was told to run the **{scenario}** calculation, so the expected "
        f"verdict is **{expected}**. The validator never saw this label."
    )
    if validation["status"] == expected:
        st.success("The validator's verdict matches the ground truth.")
    else:
        st.warning("The validator's verdict differs from the ground truth.")

# ---- Section 6: Audit log ------------------------------------------------
st.header("6. Audit log")

log_df = run["logger"].as_dataframe()
st.dataframe(log_df[["timestamp", "stage", "event", "status"]], hide_index=True)

with st.expander("Full log entries (with details)"):
    st.dataframe(log_df, hide_index=True)
with st.expander("Audit record (structured)"):
    st.json(explanation["log_entry"])

st.subheader("Run history")
history = pd.DataFrame(st.session_state["kpi_history"])
st.dataframe(
    history[
        ["timestamp", "kpi", "version", "status", "failed_checks",
         "reference", "calculated", "main_issue"]
    ].iloc[::-1],
    hide_index=True,
)