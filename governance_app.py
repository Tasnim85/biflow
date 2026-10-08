"""Shared entry point for the two BO2 demonstrations."""
import streamlit as st

st.navigation([
    st.Page("pages/1_BO2_Playbooks.py", title="BO2-02 · Nettoyage"),
    st.Page("pages/2_BO2_Anomalies.py", title="BO2-07 · Anomalies"),
    st.Page("pages/3_BO2_PII.py", title="BO2-03 · Données personnelles"),
    st.Page("pages/4_BO2_Lineage.py", title="BO2-05 · Traçabilité", default=True),
]).run()
