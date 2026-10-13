import streamlit as st

st.title("BIFlow: BO3 Explainability & Auditability")
st.caption("Two prototypes of the future BI Auditor / XAI Agent")

col1, col2 = st.columns(2)

with col1:
    st.subheader("1. XAI: explain a decision")
    st.write("The Profiler flags anomalies with an Isolation Forest. "
             "The Auditor explains each decision with SHAP and writes it in natural language.")
    st.page_link("views/xai_view.py", label="Open the XAI prototype", icon="🔍")

with col2:
    st.subheader("2. Audit log: trace a change")
    st.write("The Cleaning Agent fixes data defects. Every change goes into an append-only, "
             "hash-chained log that the Auditor can query and verify.")
    st.page_link("views/audit_view.py", label="Open the audit log prototype", icon="📜")

st.divider()
st.write("**Chain 1:** Decision → Explanation → Evidence → Audit trail")
st.write("**Chain 2:** Modification → Record → Integrity proof → Answer to *why?*")