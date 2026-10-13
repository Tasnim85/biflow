"""BO3 Deep-Dive View: Explainability (XAI), Cryptographic Audit Log, and Drift Monitoring."""
from __future__ import annotations
import os
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from data.data_generator import generate_dataset, FEATURES
from agents.profiler_agent import run_profiler
from agents.auditor_agent import AuditorAgent
from audit_log.log_store import AuditLogStore
from audit_log.log_auditor import LogAuditor
from audit_log.rules import Change
from drift_monitor.monitor import run_full_monitoring


def render_xai_audit_view(datasets: dict[str, pd.DataFrame]):
    st.markdown("""
    <div style="background: #15394c; color: white; padding: 18px 24px; border-radius: 12px; margin-bottom: 20px;">
        <h3 style="color: #63b3ed; margin: 0 0 4px 0;">🔍 BO3: Ensure Explainability & Auditability (XAI)</h3>
        <p style="margin: 0; color: #cbd5e0;">
            Feature Importance SHAP, Journal d'audit Append-Only (SHA-256) et Surveillance du Drift des décisions.
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_xai, tab_audit, tab_drift = st.tabs([
        "🤖 Explicabilité SHAP & Narration",
        "📜 Journal d'Audit Cryptographique (SHA-256)",
        "📈 Surveillance du Drift (6 Mois)"
    ])

    # 1. SHAP XAI
    with tab_xai:
        st.subheader("Explicabilité des Décisions (SHAP + Narration)")
        st.caption("Chaque observation étiquetée comme anormale est justifiée par ses contributions SHAP et une phrase explicative.")
        
        sample_df = generate_dataset(250)
        prof_res = run_profiler(sample_df)
        auditor = AuditorAgent(prof_res)
        
        flagged_idx = prof_res.data[prof_res.data["is_anomaly"]].index.tolist()
        if flagged_idx:
            sel_idx = st.selectbox("Sélectionner une observation anormale à inspecter :", flagged_idx)
            rec = auditor.audit_row(int(sel_idx))
            
            st.info(f"🗣️ **Explication en langage naturel :**\n\n{rec.narrative}")
            
            c_df = rec.explanation.contributions
            fig = px.bar(
                c_df,
                x="shap_value",
                y="feature",
                orientation="h",
                color="shap_value",
                color_continuous_scale="Viridis",
                labels={"shap_value": "Impact SHAP", "feature": "Variable"},
                title=f"Contributions SHAP pour la ligne #{sel_idx}"
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune anomalie détectée sur cet échantillon.")

    # 2. Audit Log
    with tab_audit:
        st.subheader("Journal d'Audit Append-Only Protégé par SHA-256")
        st.caption("Base SQLite avec triggers interdisant UPDATE/DELETE et chaîne de blocs mathématiquement vérifiée.")
        
        db_file = "app_audit_demo.db"
        store = AuditLogStore(db_file)
        try:
            if store.count() == 0:
                changes = [
                    Change(1, 0, "income", "nan", "45000", "r_fill_median"),
                    Change(2, 1, "transaction_amount", "-150", "150", "r_abs_amount"),
                    Change(3, 2, "city", "tuniss", "Tunis", "r_normalize_city"),
                ]
                store.append_batch(changes, agent="DemoCleaningAgent", batch_id="batch-demo-01")
            
            auditor_check = LogAuditor(store)
            status = auditor_check.verify_integrity()
            if status.ok:
                st.success(f"✅ **Intégrité de la chaîne d'audit : VALIDE ({status.entries_checked} entrées vérifiées).**")
            else:
                st.error(f"❌ **Alerte corruption :** {status.problem}")
            
            # Read rows
            rows = store.conn.execute("SELECT entry_id, batch_id, column_name, old_value, new_value, rule_id, agent, timestamp, entry_hash FROM audit_log ORDER BY entry_id DESC LIMIT 10").fetchall()
            st.dataframe(pd.DataFrame([dict(r) for r in rows]), use_container_width=True, hide_index=True)
        finally:
            store.conn.close()

    # 3. Drift Monitor
    with tab_drift:
        st.subheader("Surveillance du Drift des Données et des Décisions")
        st.caption("Supervision sur 6 mois pour distinguer 'les données ont changé' (Data Drift) de 'l'agent a changé' (Decision Drift).")
        
        with st.spinner("Exécution de la supervision statistique sur 6 mois..."):
            mon_run = run_full_monitoring(None)
        
        reps = []
        for m, r in mon_run.reports.items():
            reps.append({
                "Mois": f"Mois {m}",
                "Diagnostic": r.status,
                "Agents signalés": ", ".join(r.flagged_agents) if r.flagged_agents else "Normal",
                "Synthèse": r.narrative
            })
        st.dataframe(pd.DataFrame(reps), use_container_width=True, hide_index=True)
