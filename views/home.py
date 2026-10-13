import streamlit as st

st.title("BIFlow: BO3 Explainability & Auditability")
st.caption("Three prototypes of the future BI Auditor / XAI Agent: explain, trace, monitor")

col1, col2, col3 = st.columns(3)

with col1:
    st.subheader("1. XAI: explain a decision")
    st.write("The Profiler flags anomalies with an Isolation Forest. "
             "The Auditor explains each decision with SHAP, in natural language.")
    st.page_link("views/xai_view.py", label="Open the XAI prototype", icon="🔍")

with col2:
    st.subheader("2. Audit log: trace a change")
    st.write("The Cleaning Agent fixes data defects. Every change goes into an append-only, "
             "hash-chained log that the Auditor can query and verify.")
    st.page_link("views/audit_view.py", label="Open the audit log prototype", icon="📜")

with col3:
    st.subheader("3. Drift: monitor the agents")
    st.write("The Auditor watches every agent over six months and tells apart "
             "'the data changed' from 'the agent changed'.")
    st.page_link("views/drift_view.py", label="Open the drift prototype", icon="📈")

st.divider()
st.write("**Chain 1:** Decision → Explanation → Evidence → Audit trail")
st.write("**Chain 2:** Modification → Record → Integrity proof → Answer to *why?*")
st.write("**Chain 3:** Observed behaviour → Comparison with the reference → Alert → Diagnosis")