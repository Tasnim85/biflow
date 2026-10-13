"""BO2 Deep-Dive View: Data Governance, Playbooks, PII, and Lineage."""
from __future__ import annotations
import json
import pandas as pd
import streamlit as st

from data.data_generator import generate_dataset, FEATURES
from governance.playbooks import clean_dataset, load_policy
from governance.pii import protect_pii
from agents.anomaly_agent import profile_anomalies
from governance.lineage import build_lineage, graph_dot, ancestors


def render_governance_view(datasets: dict[str, pd.DataFrame]):
    st.markdown("""
    <div style="background: #15394c; color: white; padding: 18px 24px; border-radius: 12px; margin-bottom: 20px;">
        <h3 style="color: #63b3ed; margin: 0 0 4px 0;">🛡️ BO2: Standardize & Automate Data Governance</h3>
        <p style="margin: 0; color: #cbd5e0;">
            Playbooks de nettoyage versionnés, Détection d'anomalies, Masquage PII déterministe et Graphe de lignage (Provenance).
        </p>
    </div>
    """, unsafe_allow_html=True)

    tab_playbooks, tab_pii, tab_anomalies, tab_lineage = st.tabs([
        "📋 Playbooks Versionnés (YAML/JSON)",
        "🔒 Détection & Masquage PII (HMAC)",
        "🚨 Détection d'Anomalies (Profiling)",
        "🔗 Graphe de Lignage (KPI ➔ Source)"
    ])

    # 1. Playbooks
    with tab_playbooks:
        st.subheader("Playbooks de Nettoyage Versionnés")
        st.caption("Comparaison des règles et politiques déclaratives (1.0.0 vs 1.1.0 vs 1.2.0).")
        col_p1, col_p2 = st.columns([1, 2])
        with col_p1:
            ver = st.selectbox("Version de la politique", ["1.2.0", "1.1.0", "1.0.0"], index=0)
            pol = load_policy(ver)
            st.json(pol)
        with col_p2:
            st.write(f"**Exécution sur données synthétiques avec la politique `{ver}` :**")
            sample_df = generate_dataset(150)
            clean_res = clean_dataset(sample_df.astype(str), pol)
            st.write(f"Événements de transformation enregistrés : **{len(clean_res.events)}**")
            st.dataframe(clean_res.events.head(10), use_container_width=True)

    # 2. PII
    with tab_pii:
        st.subheader("Protection des Données Personnelles (PII)")
        st.caption("Reconnaissance locale d'expressions sensibles et pseudonymisation HMAC sans table réversible.")
        col_pii_opt, col_pii_out = st.columns([1, 2])
        with col_pii_opt:
            mode = st.radio("Mode de protection :", ["mask", "pseudonymize"], index=0)
            salt_input = st.text_input("Clé secrète HMAC (min 32 bytes) :", "biflow_secure_salt_key_32_bytes_ok!")
        with col_pii_out:
            demo_pii_df = pd.DataFrame({
                "client_id": ["C001", "C002", "C003"],
                "full_name": ["Mohamed Ben Ali", "Samar Omrani", "Ahmed Trabelsi"],
                "email": ["mohamed@esprit.tn", "samar@biflow.io", "ahmed.trabelsi@example.com"],
                "phone": ["+1 202 555 0143", "+1 202 555 0199", "+1 202 555 0188"],
                "income": ["45000", "52000", "38000"]
            })
            st.write("**Données avant protection :**")
            st.dataframe(demo_pii_df, hide_index=True)
            res_pii = protect_pii(demo_pii_df, salt_input.encode("utf-8"), mode=mode)
            st.write(f"**Données après protection ({mode}) :**")
            st.dataframe(res_pii.data, hide_index=True)

    # 3. Anomalies
    with tab_anomalies:
        st.subheader("Détection d'Anomalies lors du Profiling (Isolation Forest & MAD)")
        st.caption("Signaux statistiques combinés sans correction automatique aveugle.")
        df_anom = generate_dataset(200, anomaly_rate=0.05)
        prof_anom = profile_anomalies(df_anom.astype(str))
        flagged = prof_anom.rows[prof_anom.rows["isolation_flag"] | prof_anom.rows["robust_flag"]]
        st.metric("Lignes signalées comme anomalies", len(flagged))
        st.dataframe(flagged.head(10), use_container_width=True)

    # 4. Lineage
    with tab_lineage:
        st.subheader("Graphe de Lignage des Données")
        st.caption("Remontez de n'importe quel KPI jusqu'aux transformations et aux colonnes brutes.")
        df_lin = generate_dataset(100)
        lin_data = build_lineage(df_lin.astype(str))
        dot_code = graph_dot(lin_data)
        st.graphviz_chart(dot_code, use_container_width=True)
