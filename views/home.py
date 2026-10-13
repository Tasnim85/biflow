import streamlit as st

st.title("BIFlow: BO3 Explainability & Auditability")
st.caption("Prototype of the future BI Auditor / XAI Agent")

col1, _ = st.columns(2)

with col1:
    st.subheader("KPI governance: validate a calculation")
    st.write("The Semantic KPI Agent holds the approved, versioned KPI definition. "
             "The Validator checks the calculation against it with deterministic rules, "
             "and the Auditor explains the result in natural language from the evidence.")
    st.page_link("views/kpi_view.py", label="Open the KPI validation prototype", icon="✅")

st.divider()
st.write("**Chain:** KPI definition → Calculation → Validation → Evidence → Explanation → Audit trail")