"""Unified End-to-End Scenario View for Persona Sarra.

Implements the single platform experience connecting BO1, BO2, BO3, and BO4.
"""
from __future__ import annotations
import json
import time
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from core.unified_pipeline import run_unified_scenario, UnifiedScenarioResult
from data.data_generator import generate_dataset
from audit_log.dirty_data import generate_dirty_dataset


def render_unified_scenario_view(datasets: dict[str, pd.DataFrame]):
    st.markdown("""
    <div style="background: linear-gradient(135deg, #102a43 0%, #1e3a5f 100%); color: white; padding: 22px 28px; border-radius: 14px; margin-bottom: 24px; box-shadow: 0 4px 14px rgba(0,0,0,0.12);">
        <h2 style="color: #63b3ed; margin: 0 0 6px 0; font-size: 26px;">🎯 Parcours Décisionnel Unifié E2E — Espace Sarra</h2>
        <p style="margin: 0; color: #cbd5e0; font-size: 15px;">
            De la donnée brute à la décision éclairée et gouvernée : <strong>Orchestration complète du DAG multi-agents</strong> (BO1, BO2, BO3, BO4).
        </p>
        <div style="margin-top: 14px; display: flex; gap: 8px; flex-wrap: wrap;">
            <span style="background: rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 6px; font-size: 12px;">⚡ BO1: Accélération TTI & Similarité</span>
            <span style="background: rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 6px; font-size: 12px;">🛡️ BO2: Gouvernance, Playbooks & Lignage</span>
            <span style="background: rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 6px; font-size: 12px;">🔍 BO3: Explicabilité SHAP & Audit SHA-256</span>
            <span style="background: rgba(255,255,255,0.15); padding: 4px 10px; border-radius: 6px; font-size: 12px;">💡 BO4: Démocratisation BI & Anti-Biais</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # -------------------------------------------------------------------------
    # Étape 1 : Choix ou Dépôt du CSV & Question Métier
    # -------------------------------------------------------------------------
    col_input_left, col_input_right = st.columns([1.1, 1.4], gap="large")

    with col_input_left:
        st.markdown("### 📥 1. Données Sources")
        data_source_mode = st.radio(
            "Origine du fichier CSV :",
            ["Jeu de démonstration intégré", "Téléverser mon propre fichier CSV (Sarra)"],
            horizontal=True
        )

        selected_df = None
        dataset_name = "clients_transactions.csv"

        if data_source_mode == "Jeu de démonstration intégré":
            demo_choice = st.selectbox(
                "Sélectionner un jeu de données :",
                [
                    "Clients & Transactions (500 clients avec anomalies réelles)",
                    "Clients avec Défauts de Qualité (Dirty Data)",
                    "Données Retail Multi-Tables (Transactions)",
                ]
            )
            if "500 clients" in demo_choice:
                selected_df = generate_dataset(500, anomaly_rate=0.04, seed=42)
                dataset_name = "customers_transactions_synthetic.csv"
            elif "Défauts" in demo_choice:
                selected_df = generate_dirty_dataset(seed=7)
                dataset_name = "customers_dirty_defects.csv"
            else:
                if datasets and "transactions" in datasets:
                    selected_df = datasets["transactions"]
                    dataset_name = "retail_transactions.csv"
                elif datasets:
                    first_k = list(datasets.keys())[0]
                    selected_df = datasets[first_k]
                    dataset_name = f"{first_k}.csv"
                else:
                    selected_df = generate_dataset(300)
                    dataset_name = "customers_demo.csv"
        else:
            uploaded_file = st.file_uploader("Déposez votre fichier CSV ici :", type=["csv"])
            if uploaded_file is not None:
                try:
                    selected_df = pd.read_csv(uploaded_file)
                    dataset_name = uploaded_file.name
                    st.success(f"Fichier '{dataset_name}' chargé avec succès ({len(selected_df)} lignes, {len(selected_df.columns)} colonnes).")
                except Exception as e:
                    st.error(f"Erreur de lecture du CSV : {e}")
            else:
                st.info("Aucun fichier téléversé. Utilisation du jeu par défaut pour la prévisualisation.")
                selected_df = generate_dataset(200)
                dataset_name = "sample_default.csv"

        if selected_df is not None:
            st.caption(f"Aperçu des données : **{len(selected_df)} lignes** × **{len(selected_df.columns)} colonnes**")
            st.dataframe(selected_df.head(4), use_container_width=True, hide_index=True)

    with col_input_right:
        st.markdown("### 💬 2. Question Métier en Langage Naturel")
        st.caption("Posez une question en français comme le ferait Sarra (analyste métier) :")

        # Quick question buttons
        st.write("**Suggestions rapides :**")
        q_cols = st.columns(2)
        q1 = q_cols[0].button("💰 Quel est le montant moyen des transactions ?")
        q2 = q_cols[1].button("📊 Comparer le revenu et le score de dépense")
        q3 = q_cols[0].button("🚨 Quelles sont les transactions suspectes ?")
        q4 = q_cols[1].button("📈 Montant total par niveau de dépenses")

        default_query = "Quel est le montant moyen des transactions et la tendance globale ?"
        if q1:
            default_query = "Quel est le montant moyen des transactions ?"
        elif q2:
            default_query = "Comparer le revenu et le score de dépense moyen"
        elif q3:
            default_query = "Quelles sont les transactions avec un montant anormal ?"
        elif q4:
            default_query = "Quel est le montant total des transactions ?"

        query_input = st.text_input(
            "Votre question décisionnelle :",
            value=st.session_state.get("last_query", default_query),
            key="sarra_query_input"
        )
        st.session_state["last_query"] = query_input

        # Policy selector
        col_pol1, col_pol2 = st.columns(2)
        with col_pol1:
            policy_version = st.selectbox(
                "Version du Playbook de Nettoyage (BO2) :",
                ["1.2.0 (Dernière version approuvée)", "1.1.0", "1.0.0"],
                index=0
            ).split()[0]
        with col_pol2:
            st.write("")
            st.write("")
            launch_clicked = st.button(
                "🚀 Exécuter l'Orchestrateur Complet (DAG)",
                type="primary",
                use_container_width=True
            )

    st.markdown("---")

    # -------------------------------------------------------------------------
    # Exécution du DAG
    # -------------------------------------------------------------------------
    if launch_clicked or "unified_scenario_result" not in st.session_state:
        if launch_clicked:
            progress_bar = st.progress(0, text="Initialisation de l'orchestrateur DAG...")
            progress_status = st.empty()

            def on_progress(node):
                step_map = {
                    "node_0": (12, "Étape 0: Similarité vectorielle des datasets (BO1)..."),
                    "node_1a": (25, "Étape 1a: Auto-classification sémantique NLP+ML (BO1)..."),
                    "node_1b": (38, "Étape 1b: Détection et masquage PII HMAC (BO2)..."),
                    "node_2": (52, "Étape 2: Nettoyage par playbook et détection d'anomalies (BO2/BO1)..."),
                    "node_3_4": (68, "Étapes 3 & 4: Schéma étoile ETL & NER glossaire métier (BO3/BO4)..."),
                    "node_5_6": (82, "Étapes 5 & 6: Synthèse NLU, graphique optimal et anti-biais (BO4)..."),
                    "node_lineage": (92, "Traçabilité: Construction du graphe de lignage (BO2)..."),
                    "node_7": (100, "Étape 7: Explicabilité SHAP, journal SHA-256 et drift (BO3)..."),
                }
                pct, msg = step_map.get(node.node_id, (50, "Exécution en cours..."))
                progress_bar.progress(pct, text=msg)
                progress_status.info(f"⏳ **{node.label}** [{node.owner_bo}] : {node.summary}")
                time.sleep(0.08)

            with st.spinner("Exécution du pipeline décisionnel de bout en bout..."):
                res = run_unified_scenario(
                    df_raw=selected_df,
                    query=query_input,
                    dataset_name=dataset_name,
                    policy_version=policy_version,
                    progress_callback=on_progress
                )
                st.session_state["unified_scenario_result"] = res

            progress_bar.empty()
            progress_status.empty()
            st.rerun()

    result: UnifiedScenarioResult = st.session_state.get("unified_scenario_result")
    if not result:
        st.stop()

    # -------------------------------------------------------------------------
    # Bannière de statut d'exécution
    # -------------------------------------------------------------------------
    st.success(
        f"✅ **Orchestration DAG terminée avec succès en {result.total_duration:.2f} secondes.** "
        f"Tous les 8 nœuds multi-agents sont validés pour le jeu **'{result.dataset_name}'**."
    )

    # -------------------------------------------------------------------------
    # Onglets de présentation structurée des 4 BO
    # -------------------------------------------------------------------------
    tab_bo4, tab_bo2, tab_bo3, tab_bo1, tab_export = st.tabs([
        "📊 Réponse & Dashboard Décisionnel (BO4)",
        "🛡️ Gouvernance, Qualité & Lignage (BO2)",
        "🔍 Explicabilité (XAI) & Audit Sécurisé (BO3)",
        "⚡ Orchestrateur DAG & Intelligence Sources (BO1)",
        "📜 Données BI-Ready & Export d'Audit"
    ])

    # -------------------------------------------------------------------------
    # TAB 1 : BO4 - Réponse Métier, Graphique Optimal & Anti-Biais
    # -------------------------------------------------------------------------
    with tab_bo4:
        st.subheader("💡 Synthèse Décisionnelle & Recommandation Visuelle")
        
        # Metrics KPI banner
        kpi_cols = st.columns(min(5, len(result.kpis) + 1))
        for i, (k, v) in enumerate(list(result.kpis.items())[:4]):
            kpi_cols[i].metric(label=k, value=v)
        kpi_cols[-1].metric(label="Anomalies Détectées", value=result.anomaly_count)

        # NLU Business Answer
        st.markdown(f"""
        <div style="background: #ebf8fa; border-left: 5px solid #087f79; padding: 14px 18px; border-radius: 8px; margin: 16px 0;">
            <h4 style="margin: 0 0 6px 0; color: #15394c;">💡 Réponse Analytique à la question de Sarra :</h4>
            <p style="margin: 0; font-size: 16px; color: #2d3748; line-height: 1.5;">{result.business_answer}</p>
        </div>
        """, unsafe_allow_html=True)

        # Anti-Bias Misleading Comparison Alert
        if result.misleading_alerts:
            st.markdown("#### ⚠️ Contrôle Anti-Biais : Alertes de Comparaisons Trompeuses")
            for alert in result.misleading_alerts:
                st.warning(f"**{alert['title']}** ({alert['severity']})\n\n{alert['explanation']}\n\n👉 *Recommandation :* {alert['recommendation']}")
        else:
            st.success("✅ **Contrôle visuel valide :** Aucune comparaison trompeuse ni distorsion d'axe détectée. La visualisation respecte les règles d'intégrité cognitive.")

        # Optimal Plotly Chart
        st.markdown(f"#### 📈 Graphique Optimal Recommandé : {result.chart_recommendation.title}")
        st.caption(f"**Type sélectionné automatiquement :** `{result.chart_recommendation.chart_type.upper()}` — **Raisonnement :** {result.chart_recommendation.rationale}")
        
        if result.plotly_figure:
            st.plotly_chart(result.plotly_figure, use_container_width=True)

        # Recognized Business Entities (NER)
        with st.expander("🏷️ Entités Reconnues dans le Glossaire Métier (NER)", expanded=True):
            if result.glossary_entities:
                e_cols = st.columns(min(4, len(result.glossary_entities)))
                for idx, e in enumerate(result.glossary_entities):
                    col_idx = idx % len(e_cols)
                    with e_cols[col_idx]:
                        st.metric(
                            label=f"{e['canonical']} ({e['kind']})",
                            value=f"{int(e['confidence']*100)}%",
                            help=e['explanation']
                        )
            else:
                st.info("Aucun terme spécifique n'a nécessité de mapping complexe dans le glossaire métier.")

    # -------------------------------------------------------------------------
    # TAB 2 : BO2 - Gouvernance, PII, Playbooks & Lignage
    # -------------------------------------------------------------------------
    with tab_bo2:
        st.subheader("🛡️ Gouvernance des Données & Traçabilité de Bout en Bout")

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.markdown("#### 🔒 Protection des Données Personnelles (PII)")
            st.write(f"**Occurrences sensibles identifiées :** `{result.pii_count}`")
            st.caption("Masquage déterministe via HMAC (Emails, Téléphones, Identifiants).")
            if result.pii_count > 0:
                st.dataframe(result.pii_detections.head(5), use_container_width=True, hide_index=True)
            else:
                st.info("Aucune donnée PII directe non masquée détectée dans ce jeu.")

        with col_g2:
            st.markdown("#### 📋 Playbook Versionné de Nettoyage")
            st.write(f"**Playbook appliqué :** `{result.playbook_used}`")
            q_diff = result.quality_after['score'] - result.quality_before['score']
            st.metric(
                label="Score de Qualité Global",
                value=f"{result.quality_after['score']:.1f}%",
                delta=f"{q_diff:+.1f} points de pourcentage"
            )

        st.markdown("---")
        st.markdown("#### 🔗 Graphe de Lignage des Données (Trace Each KPI to its Source)")
        st.caption("Visualisation de la chaîne causale complète : Données Sources ➔ Transformations de Nettoyage ➔ Filtres Qualité ➔ Métriques & KPIs Décisionnels.")

        if result.lineage_dot:
            st.graphviz_chart(result.lineage_dot, use_container_width=True)
        else:
            st.info("Graphe de lignage non disponible.")

    # -------------------------------------------------------------------------
    # TAB 3 : BO3 - Explicabilité SHAP, Journal SHA-256 & Drift
    # -------------------------------------------------------------------------
    with tab_bo3:
        st.subheader("🔍 Explicabilité Mathématique (XAI) & Audit Immuable")

        col_xai_left, col_xai_right = st.columns([1.2, 1], gap="medium")

        with col_xai_left:
            st.markdown("#### 🤖 Explicabilité des Décisions d'Anomalie (SHAP)")
            st.caption("Chaque décision de l'agent Profiler est explicitée via TreeExplainer :")
            
            if result.audited_records:
                for rec in result.audited_records:
                    with st.expander(f"Observation #{rec['row_index']} — {rec['decision']} (Score: {rec['score']:.3f})", expanded=True):
                        st.markdown(f"**Explication en langage naturel :**\n> *\"{rec['narrative']}\"*")
                        if rec["top_shap"]:
                            shap_df = pd.DataFrame(rec["top_shap"])
                            fig_shap = px.bar(
                                shap_df,
                                x="shap_value",
                                y="feature",
                                orientation="h",
                                color="shap_value",
                                color_continuous_scale="Reds",
                                labels={"shap_value": "Contribution SHAP (Pousse vers anomalie)", "feature": "Variable"},
                                title=f"Importance des variables (Row {rec['row_index']})"
                            )
                            fig_shap.update_layout(height=240, margin=dict(l=20, r=20, t=35, b=20))
                            st.plotly_chart(fig_shap, use_container_width=True)
            else:
                st.info("Aucune anomalie significative à auditer sur cet échantillon.")

        with col_xai_right:
            st.markdown("#### 📜 Journal d'Audit Append-Only (Chaîne SHA-256)")
            if result.audit_chain_valid:
                st.success("✅ **Intégrité Cryptographique : 100% INTACTE**\nToutes les opérations sont chaînées par hachage SHA-256 avec triggers SQLite anti-modification.")
            else:
                st.error("❌ Anomalie d'intégrité détectée dans la chaîne de hachage !")

            st.write(f"**Entrées tracées dans le registre :** `{result.audit_log_count}` transactions")

            st.markdown("#### 📈 Surveillance du Drift des Décisions (6 Mois)")
            st.caption("L'auditeur supervise la dérive des données (PSI > 0.25) et des agents (Limites de contrôle) :")
            if "reports" in result.drift_summary:
                drift_rows = []
                for m_name, rep in result.drift_summary["reports"].items():
                    drift_rows.append({
                        "Période": m_name,
                        "Statut": rep["status"],
                        "Agents signalés": ", ".join(rep["flagged_agents"]) if rep["flagged_agents"] else "Aucun"
                    })
                st.dataframe(pd.DataFrame(drift_rows), use_container_width=True, hide_index=True)

    # -------------------------------------------------------------------------
    # TAB 4 : BO1 - Orchestration DAG & Intelligence Sources
    # -------------------------------------------------------------------------
    with tab_bo1:
        st.subheader("⚡ Orchestration Asynchrone & Découverte de Sources")

        st.markdown("#### ⏱️ Temps d'Exécution et Statuts des Nœuds du DAG")
        node_records = []
        for n_id, n in result.nodes.items():
            node_records.append({
                "Nœud": n.label,
                "Module": n.owner_bo,
                "Statut": n.status,
                "Durée (s)": f"{n.duration:.3f} s",
                "Description": n.summary
            })
        st.dataframe(pd.DataFrame(node_records), use_container_width=True, hide_index=True)

        col_bo1_a, col_bo1_b = st.columns(2)
        with col_bo1_a:
            st.markdown("#### 🧬 Détection de Similarité de Datasets (BO1)")
            st.caption("Comparaison vectorielle de schémas pour identifier des recettes réutilisables :")
            st.dataframe(pd.DataFrame(result.similarity_matches), use_container_width=True, hide_index=True)

        with col_bo1_b:
            st.markdown("#### 🏷️ Classification Sémantique Automatique (NLP+ML)")
            st.caption("Inférence des rôles sémantiques métier sur les colonnes sources :")
            sem_rows = [{"Colonne": s["column"], "Type Sémantique": s["semantic_type"], "Confiance": f"{s['confidence']:.1%}"} for s in result.semantic_types]
            st.dataframe(pd.DataFrame(sem_rows), use_container_width=True, hide_index=True)

    # -------------------------------------------------------------------------
    # TAB 5 : Données BI-Ready & Export
    # -------------------------------------------------------------------------
    with tab_export:
        st.subheader("💾 Données Nettoyées & Export des Artefacts d'Audit")
        st.caption("Les données ci-dessous ont passé avec succès l'ensemble des filtres de gouvernance et de qualité :")
        st.dataframe(result.cleaned_df.head(15), use_container_width=True)

        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            csv_data = result.cleaned_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Télécharger les Données Nettoyées (CSV)",
                data=csv_data,
                file_name=f"biflow_cleaned_{result.dataset_name}",
                mime="text/csv",
                use_container_width=True
            )

        with col_exp2:
            manifest_dict = {
                "dataset_name": result.dataset_name,
                "timestamp": result.start_time,
                "total_duration_seconds": result.total_duration,
                "query": result.query,
                "quality_score_final": result.quality_after["score"],
                "anomalies_detected": result.anomaly_count,
                "audit_chain_verified": result.audit_chain_valid,
                "chart_type": result.chart_recommendation.chart_type,
                "kpis": result.kpis
            }
            st.download_button(
                "📜 Télécharger le Manifeste d'Audit (JSON)",
                data=json.dumps(manifest_dict, indent=2, ensure_ascii=False).encode("utf-8"),
                file_name=f"biflow_manifest_{result.dataset_name}.json",
                mime="application/json",
                use_container_width=True
            )
