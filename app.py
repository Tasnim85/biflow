"""BIFlow prototype: router. Declares the pages; contains no logic."""

import streamlit as st

st.set_page_config(page_title="BIFlow Auditor", layout="wide")

home = st.Page("views/home.py", title="Home", icon="🏠", default=True)
kpi = st.Page("views/kpi_view.py", title="KPI: Validate a calculation", icon="✅")

st.navigation([home, kpi]).run()