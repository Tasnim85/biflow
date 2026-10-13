"""BIFlow prototype: router. Declares the pages; contains no logic."""

import streamlit as st

st.set_page_config(page_title="BIFlow Auditor", layout="wide")

home = st.Page("views/home.py", title="Home", icon="🏠", default=True)
xai = st.Page("views/xai_view.py", title="XAI: Explain a decision", icon="🔍")
audit = st.Page("views/audit_view.py", title="Audit log: Trace a change", icon="📜")

st.navigation([home, xai, audit]).run()