"""Prototype 2 view: append-only audit log. Display only, no business logic."""

import os

import pandas as pd
import streamlit as st

from audit_log.cleaning_agent import CleaningAgent
from audit_log.dirty_data import generate_dirty_dataset
from audit_log.log_auditor import LogAuditor
from audit_log.log_store import AuditLogStore
from audit_log.rules import RULES

DB_PATH = "app_audit_log.db"


@st.cache_resource
def load_audit_system():
    """Runs once: create a fresh log, clean the data (and log every change)."""
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    store = AuditLogStore(DB_PATH)
    full = generate_dirty_dataset()
    raw = full.drop(columns="planted_defect")          # the agent never sees it
    result = CleaningAgent(store).run(raw)
    planted = int((full["planted_defect"] != "none").sum())   # ground truth count
    return store, raw, result, planted


store, raw, result, planted = load_audit_system()
auditor = LogAuditor(store)
clean = result.clean_data

st.title("Audit log: Trace a change")
st.caption("Modification → Record → Integrity proof → Answer to why?")

# ---- Section 1: before / after -------------------------------------------
st.header("1. Cleaning result")
c1, c2, c3 = st.columns(3)
c1.metric("Rows before", len(raw))
c2.metric("Rows after", len(clean))
c3.metric("Changes logged", store.count())

ok, message = auditor.check_completeness(planted)
if ok:
    st.success(f"{message} (ground truth: {planted} defects were planted)")
else:
    st.error(message)

with st.expander("Cleaning rules (the source of the 'why')"):
    for rule_id, description in RULES.items():
        st.write(f"**{rule_id}**: {description}")

# ---- Section 2: the log ------------------------------------------------------
st.header("2. The audit log")
log_df = pd.read_sql_query(
    "SELECT entry_id, batch_id, row_id AS customer_id, column_name, old_value, "
    "new_value, rule_id, agent, timestamp, "
    "substr(prev_hash, 1, 8) AS prev_hash, substr(entry_hash, 1, 8) AS entry_hash "
    "FROM audit_log ORDER BY entry_id",
    store.conn,
)
rule_filter = st.multiselect("Filter by rule", options=list(RULES), default=list(RULES))
st.dataframe(log_df[log_df["rule_id"].isin(rule_filter)],
             use_container_width=True, hide_index=True)
st.caption("Each entry stores the hash of the previous one (prev_hash). "
           "Hashes are shortened to 8 characters here.")

# ---- Section 3: why was this row modified? --------------------------------
st.header("3. Why was this customer modified?")
modified_ids = sorted({c.row_id for c in result.changes})
customer_id = st.number_input(
    "Customer ID (try a modified one, then customer 1)",
    min_value=1, max_value=int(raw["customer_id"].max()),
    value=modified_ids[0], step=1,
)
customer_id = int(customer_id)

st.markdown(auditor.why(customer_id))

left, right = st.columns(2)
with left:
    st.write("**Before cleaning**")
    st.dataframe(raw[raw["customer_id"] == customer_id], hide_index=True)
with right:
    st.write("**After cleaning**")
    st.dataframe(clean[clean["customer_id"] == customer_id], hide_index=True)

st.caption(f"{len(modified_ids)} customers were modified. "
           f"Examples: {', '.join(map(str, modified_ids[:8]))}...")

# ---- Section 4: integrity ------------------------------------------------------
st.header("4. Integrity verification")

if st.button("Verify integrity", type="primary"):
    st.session_state["integrity"] = auditor.verify_integrity()

report = st.session_state.get("integrity")
if report is None:
    st.info("Click the button to verify the hash chain.")
elif report.ok:
    st.success(f"{report.problem} ({report.entries_checked} entries checked)")
else:
    st.error(f"TAMPERING DETECTED. {report.problem}")

st.write("**Anchor (final hash of the chain):**")
st.code(store._last_hash())
st.caption("In production this hash would be stored somewhere else (another system, "
           "a signature, write-once storage). Anyone could then detect even a fully "
           "recomputed chain by comparing it.")

# ---- Section 5: attacker simulation and reset ---------------------------------
st.header("5. Tampering test (demo only)")
st.write("Simulate an attacker with access to the database file. They remove the "
         "protection trigger, then edit one entry directly.")

target = st.number_input("Entry to tamper with", min_value=1,
                         max_value=store.count(), value=5, step=1)

if st.button("Simulate tampering"):
    store.conn.execute("DROP TRIGGER IF EXISTS audit_log_no_update")
    store.conn.execute("UPDATE audit_log SET new_value = 'HACKED' WHERE entry_id = ?",
                       (int(target),))
    store.conn.commit()
    st.session_state.pop("integrity", None)      # old report is now stale
    st.session_state["tampered"] = int(target)
    st.rerun()

if "tampered" in st.session_state:
    st.warning(f"Entry {st.session_state['tampered']} was modified directly in the database. "
               "Click 'Verify integrity' in section 4 to see if the Auditor notices.")

if st.button("Reset demo"):
    store.conn.close()
    os.remove(DB_PATH)
    st.cache_resource.clear()
    st.session_state.pop("integrity", None)
    st.session_state.pop("tampered", None)
    st.rerun()