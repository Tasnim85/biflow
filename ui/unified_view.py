"""Unified End-to-End Scenario View for Persona Sarra — Step-by-Step.

Displays each BO sequentially: BO1 → BO2 → BO3 → BO4, with results
rendered inline as each step completes, like a progressive report.
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
            De la donnée brute à la décision éclairée : <strong>Scénario complet étape par étape</strong> (BO1 → BO2 → BO3 → BO4).
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ─────────────────────────────────────────────────────────────────────────
    # Étape 0 : Entrées — CSV + Question
    # ─────────────────────────────────────────────────────────────────────────
    st.markdown("## 📥 Étape 0 — Données Sources & Question Métier")

    col_left, col_right = st.columns([1.1, 1.4], gap="large")

    with col_left:
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
                st.info("Aucun fichier téléversé. Utilisation du jeu par défaut.")
                selected_df = generate_dataset(200)
                dataset_name = "sample_default.csv"

        if selected_df is not None:
            st.caption(f"Aperçu : **{len(selected_df)} lignes** × **{len(selected_df.columns)} colonnes**")
            st.dataframe(selected_df.head(4), width='stretch', hide_index=True)

    with col_right:
        st.markdown("### 💬 Question Métier en Langage Naturel")
        st.caption("Posez une question en français comme le ferait Sarra :")

        st.write("**Suggestions rapides :**")
        q_cols = st.columns(2)
        q1 = q_cols[0].button("💰 Montant moyen des transactions")
        q2 = q_cols[1].button("📊 Comparer revenu et dépenses")
        q3 = q_cols[0].button("🚨 Transactions suspectes")
        q4 = q_cols[1].button("📈 Montant total par catégorie")

        default_query = "Quel est le montant moyen des transactions et la tendance globale ?"
        if q1: default_query = "Quel est le montant moyen des transactions ?"
        elif q2: default_query = "Comparer le revenu et le score de dépense moyen"
        elif q3: default_query = "Quelles sont les transactions avec un montant anormal ?"
        elif q4: default_query = "Quel est le montant total des transactions ?"

        query_input = st.text_input(
            "Votre question décisionnelle :",
            value=st.session_state.get("last_query", default_query),
            key="sarra_query_input"
        )
        st.session_state["last_query"] = query_input

        col_pol1, col_pol2 = st.columns(2)
        with col_pol1:
            policy_version = st.selectbox(
                "Version du Playbook (BO2) :",
                ["1.2.0 (Dernière version)", "1.1.0", "1.0.0"],
                index=0
            ).split()[0]
        with col_pol2:
            st.write("")
            st.write("")
            launch_clicked = st.button(
                "🚀 Lancer le Scénario Complet (Étape par Étape)",
                type="primary",
                use_container_width=True
            )

    st.markdown("---")

    # ─────────────────────────────────────────────────────────────────────────
    # Exécution du pipeline puis affichage séquentiel
    # ─────────────────────────────────────────────────────────────────────────
    if launch_clicked and selected_df is not None:
        progress_bar = st.progress(0, text="Initialisation de l'orchestrateur DAG...")
        progress_status = st.empty()

        step_map = {
            "node_0":       (8,  "⚡ Étape 1/8 — BO1 : Détection de Similarité..."),
            "node_1a":      (20, "⚡ Étape 2/8 — BO1 : Classification Sémantique NLP+ML..."),
            "node_1b":      (32, "🛡️ Étape 3/8 — BO2 : Détection & Masquage PII..."),
            "node_2":       (48, "🛡️ Étape 4/8 — BO2 : Nettoyage Playbook & Anomalies..."),
            "node_3_4":     (62, "🔍 Étape 5/8 — BO3 : ETL Star Schema & Glossaire NER..."),
            "node_5_6":     (76, "💡 Étape 6/8 — BO4 : Dashboard BI & Anti-Biais..."),
            "node_lineage": (88, "🛡️ Étape 7/8 — BO2 : Graphe de Lignage..."),
            "node_7":       (100,"🔍 Étape 8/8 — BO3 : SHAP XAI & Audit SHA-256..."),
        }

        def on_progress(node):
            pct, msg = step_map.get(node.node_id, (50, "Exécution en cours..."))
            progress_bar.progress(pct, text=msg)
            progress_status.info(f"⏳ **{node.label}** [{node.owner_bo}] : {node.summary}")
            time.sleep(0.05)

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
        st.info("👆 Choisissez vos données et votre question, puis cliquez sur **Lancer le Scénario Complet**.")
        st.stop()

    # ─────────────────────────────────────────────────────────────────────────
    # Bannière de succès
    # ─────────────────────────────────────────────────────────────────────────
    st.success(
        f"✅ **Scénario complet terminé en {result.total_duration:.2f}s** — "
        f"8 étapes exécutées séquentiellement pour **'{result.dataset_name}'**"
    )

    # ═══════════════════════════════════════════════════════════════════════
    #  ÉTAPE 1 — BO1 : Détection de Similarité entre Datasets
    # ═══════════════════════════════════════════════════════════════════════
    _step_header(1, "BO1", "⚡", "Détection de Similarité entre Datasets",
                 "Encodage vectoriel des schémas et comparaison par cosinus pour identifier des recettes réutilisables.",
                 result.nodes.get("node_0"))

    col_s1, col_s2 = st.columns([1.3, 1])
    with col_s1:
        st.dataframe(pd.DataFrame(result.similarity_matches), width='stretch', hide_index=True)
    with col_s2:
        if result.similarity_matches:
            top = result.similarity_matches[0]
            st.metric("Meilleure similarité", f"{top['similarity_score']:.1%}", help=f"Avec {top['reference_dataset']}")
            st.metric("Recette suggérée", top['reusable_recipe'])
            st.caption(f"Concepts partagés : {', '.join(top['shared_concepts']) or 'aucun'}")
    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    #  ÉTAPE 2 — BO1 : Auto-Classification Sémantique des Colonnes
    # ═══════════════════════════════════════════════════════════════════════
    _step_header(2, "BO1", "⚡", "Auto-Classification Sémantique des Colonnes (NLP+ML)",
                 "Inférence automatique du rôle métier de chaque colonne : EMAIL, PHONE, AGE, CATEGORY, etc.",
                 result.nodes.get("node_1a"))

    sem_rows = [{"Colonne": s["column"], "Type Sémantique": s["semantic_type"],
                 "Confiance": f"{s['confidence']:.0%}"} for s in result.semantic_types]
    st.dataframe(pd.DataFrame(sem_rows), width='stretch', hide_index=True)
    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    #  ÉTAPE 3 — BO2 : Détection & Masquage des Données Personnelles (PII)
    # ═══════════════════════════════════════════════════════════════════════
    _step_header(3, "BO2", "🛡️", "Détection & Masquage Automatique des Données Personnelles (PII)",
                 "Analyse regex multi-patrons (Email, Téléphone, Nom) et pseudonymisation déterministe HMAC.",
                 result.nodes.get("node_1b"))

    col_p1, col_p2 = st.columns([1, 1])
    with col_p1:
        st.metric("Données PII identifiées et masquées", result.pii_count)
    with col_p2:
        st.caption("Masquage déterministe : même entrée → même hash. Aucune donnée PII en clair dans le pipeline en aval.")
    if result.pii_count > 0:
        st.dataframe(result.pii_detections.head(8), width='stretch', hide_index=True)
    else:
        st.info("Aucune donnée personnelle directe (PII) non masquée détectée dans ce jeu de données.")
    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    #  ÉTAPE 4 — BO2 : Nettoyage par Playbook Versionné & Anomalies
    # ═══════════════════════════════════════════════════════════════════════
    _step_header(4, "BO2", "🛡️", "Nettoyage par Playbook Versionné & Détection d'Anomalies",
                 f"Application de '{result.playbook_used}' + Isolation Forest & MAD robuste.",
                 result.nodes.get("node_2"))

    col_q1, col_q2, col_q3, col_q4 = st.columns(4)
    col_q1.metric("Qualité Avant", f"{result.quality_before['score']:.1f}%")
    q_diff = result.quality_after['score'] - result.quality_before['score']
    col_q2.metric("Qualité Après", f"{result.quality_after['score']:.1f}%", delta=f"{q_diff:+.1f} pp")
    col_q3.metric("Anomalies Détectées", result.anomaly_count)
    col_q4.metric("Playbook", result.playbook_used.split("'")[1] if "'" in result.playbook_used else "Dynamique")

    if result.anomaly_count > 0:
        with st.expander(f"🔎 Détail des {result.anomaly_count} anomalies détectées", expanded=False):
            display_cols = [c for c in result.anomalies_df.columns if c not in ["robust_scores"]]
            st.dataframe(result.anomalies_df[display_cols].head(10), width='stretch', hide_index=True)
    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    #  ÉTAPE 5 — BO3 : ETL Star Schema + Catalogue de KPIs + Glossaire NER
    # ═══════════════════════════════════════════════════════════════════════
    _step_header(5, "BO3", "🔍", "ETL Star Schema, Catalogue de KPIs & Glossaire Métier (NER)",
                 "Construction du schéma en étoile, calcul des indicateurs clés et extraction d'entités métier de la question.",
                 result.nodes.get("node_3_4"))

    # KPI Cards
    kpi_cols = st.columns(min(6, len(result.kpis)))
    for i, (k, v) in enumerate(list(result.kpis.items())[:6]):
        kpi_cols[i % len(kpi_cols)].metric(label=k, value=v)

    col_ner, col_star = st.columns(2)
    with col_ner:
        st.markdown("**🏷️ Entités Glossaire Métier (NER) extraites de la question :**")
        if result.glossary_entities:
            for e in result.glossary_entities:
                st.write(f"• **{e['canonical']}** ({e['kind']}) — confiance {int(e['confidence']*100)}% — _{e['explanation']}_")
        else:
            st.info("Aucun terme spécifique nécessitant un mapping dans le glossaire.")
    with col_star:
        st.markdown("**⭐ Tables du Schéma Étoile (ETL) :**")
        for tbl_name, tbl_df in result.star_schema.items():
            st.caption(f"`{tbl_name}` — {len(tbl_df)} lignes × {len(tbl_df.columns)} colonnes")
            st.dataframe(tbl_df.head(3), width='stretch', hide_index=True)
    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    #  ÉTAPE 6 — BO4 : Dashboard BI, Graphique Optimal & Anti-Biais
    # ═══════════════════════════════════════════════════════════════════════
    _step_header(6, "BO4", "💡", "Dashboard BI : Réponse NLU, Graphique Optimal & Détection Anti-Biais",
                 "Synthèse en langage naturel, sélection automatique du type de graphique et contrôle des comparaisons trompeuses.",
                 result.nodes.get("node_5_6"))

    # Business answer
    st.markdown(f"""
    <div style="background: #ebf8fa; border-left: 5px solid #087f79; padding: 14px 18px; border-radius: 8px; margin: 12px 0;">
        <h4 style="margin: 0 0 6px 0; color: #15394c;">💡 Réponse Analytique à la question de Sarra :</h4>
        <p style="margin: 0; font-size: 16px; color: #2d3748; line-height: 1.5;">{result.business_answer}</p>
    </div>
    """, unsafe_allow_html=True)

    # Anti-bias
    if result.misleading_alerts:
        st.markdown("#### ⚠️ Alertes de Comparaisons Trompeuses Détectées")
        for alert in result.misleading_alerts:
            st.warning(f"**{alert['title']}** ({alert['severity']})\n\n{alert['explanation']}\n\n👉 *Recommandation :* {alert['recommendation']}")
    else:
        st.success("✅ **Contrôle visuel valide :** Aucune comparaison trompeuse ni distorsion d'axe détectée.")

    # Optimal chart
    st.markdown(f"#### 📈 Graphique Optimal : {result.chart_recommendation.title}")
    st.caption(f"**Type :** `{result.chart_recommendation.chart_type.upper()}` — **Raisonnement :** {result.chart_recommendation.rationale}")
    if result.plotly_figure:
        st.plotly_chart(result.plotly_figure, width='stretch')
    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    #  ÉTAPE 7 — BO2 : Graphe de Lignage des Données
    # ═══════════════════════════════════════════════════════════════════════
    _step_header(7, "BO2", "🛡️", "Graphe de Lignage des Données (Trace Each KPI → Source)",
                 "Visualisation de la chaîne de provenance complète : Données Sources ➔ Transformations ➔ KPIs Décisionnels.",
                 result.nodes.get("node_lineage"))

    if result.lineage_dot:
        st.graphviz_chart(result.lineage_dot, use_container_width=True)
    else:
        st.info("Graphe de lignage non disponible pour ce schéma.")
    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    #  ÉTAPE 8 — BO3 : Explicabilité SHAP, Audit SHA-256 & Drift
    # ═══════════════════════════════════════════════════════════════════════
    _step_header(8, "BO3", "🔍", "Explicabilité SHAP (XAI), Journal d'Audit SHA-256 & Surveillance Drift",
                 "Chaque décision d'anomalie expliquée mathématiquement, chaîne cryptographique inviolable et monitoring de dérive sur 6 mois.",
                 result.nodes.get("node_7"))

    col_xai, col_audit = st.columns([1.3, 1], gap="medium")

    with col_xai:
        st.markdown("**🤖 Explications SHAP des Décisions d'Anomalie :**")
        if result.audited_records:
            for rec in result.audited_records:
                with st.expander(f"Row #{rec['row_index']} — {rec['decision']} (Score: {rec['score']:.3f})", expanded=True):
                    st.markdown(f"> *\"{rec['narrative']}\"*")
                    if rec["top_shap"]:
                        shap_df = pd.DataFrame(rec["top_shap"])
                        fig_shap = px.bar(
                            shap_df, x="shap_value", y="feature", orientation="h",
                            color="shap_value", color_continuous_scale="Reds",
                            labels={"shap_value": "Contribution SHAP", "feature": "Variable"},
                            title=f"Importance des variables (Row {rec['row_index']})"
                        )
                        fig_shap.update_layout(height=220, margin=dict(l=20, r=20, t=35, b=20))
                        st.plotly_chart(fig_shap, width='stretch')
        else:
            st.info("Aucune anomalie significative à auditer.")

    with col_audit:
        st.markdown("**📜 Journal d'Audit Append-Only (SHA-256) :**")
        if result.audit_chain_valid:
            st.success("✅ **Intégrité : 100% INTACTE**\nChaîne SHA-256 avec triggers SQLite anti-modification.")
        else:
            st.error("❌ Anomalie d'intégrité détectée !")
        st.metric("Entrées tracées", f"{result.audit_log_count} transactions")

        st.markdown("**📈 Surveillance du Drift (6 Mois) :**")
        if "reports" in result.drift_summary:
            drift_rows = []
            for m_name, rep in result.drift_summary["reports"].items():
                drift_rows.append({
                    "Période": m_name,
                    "Statut": rep["status"],
                    "Agents signalés": ", ".join(rep["flagged_agents"]) if rep["flagged_agents"] else "Aucun"
                })
            st.dataframe(pd.DataFrame(drift_rows), width='stretch', hide_index=True)
        else:
            st.caption(f"Drift monitor : {result.drift_summary.get('status', 'N/A')}")

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════════════════
    #  RÉSUMÉ FINAL & EXPORT
    # ═══════════════════════════════════════════════════════════════════════
    st.markdown("## ✅ Résumé Final & Données BI-Ready pour Sarra")

    # DAG execution summary
    st.markdown("#### ⏱️ Récapitulatif d'Exécution du DAG")
    node_records = []
    for n_id, n in result.nodes.items():
        node_records.append({
            "# Étape": n.label, "Module": n.owner_bo,
            "Statut": "✅ " + n.status, "Durée": f"{n.duration:.3f}s",
            "Résumé": n.summary
        })
    st.dataframe(pd.DataFrame(node_records), width='stretch', hide_index=True)

    # Export
    st.markdown("#### 💾 Export des Artefacts")
    col_exp1, col_exp2, col_exp3 = st.columns(3)
    with col_exp1:
        csv_data = result.cleaned_df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Données Nettoyées (CSV)", data=csv_data,
            file_name=f"biflow_cleaned_{result.dataset_name}", mime="text/csv",
            use_container_width=True
        )
    with col_exp2:
        manifest_dict = {
            "dataset_name": result.dataset_name, "timestamp": result.start_time,
            "total_duration_seconds": result.total_duration, "query": result.query,
            "quality_before": result.quality_before["score"],
            "quality_after": result.quality_after["score"],
            "anomalies_detected": result.anomaly_count,
            "pii_masked": result.pii_count,
            "audit_chain_verified": result.audit_chain_valid,
            "chart_type": result.chart_recommendation.chart_type,
            "kpis": result.kpis
        }
        st.download_button(
            "📜 Manifeste d'Audit (JSON)",
            data=json.dumps(manifest_dict, indent=2, ensure_ascii=False).encode("utf-8"),
            file_name=f"biflow_manifest_{result.dataset_name}.json", mime="application/json",
            use_container_width=True
        )
    with col_exp3:
        st.dataframe(result.cleaned_df.head(8), width='stretch', hide_index=True)


def _step_header(step_num: int, bo: str, icon: str, title: str, description: str, node=None):
    """Renders a consistent step header with BO badge and timing."""
    duration_str = f" — ⏱️ {node.duration:.3f}s" if node else ""
    bo_colors = {"BO1": "#2b6cb0", "BO2": "#2f855a", "BO3": "#9b2c2c", "BO4": "#744210", "BO3/BO4": "#6b46c1"}
    bg = bo_colors.get(bo, "#4a5568")
    st.markdown(f"""
    <div style="display: flex; align-items: center; gap: 12px; margin: 24px 0 12px 0;">
        <span style="background: {bg}; color: white; padding: 4px 12px; border-radius: 8px; font-weight: bold; font-size: 13px;">{bo}</span>
        <h3 style="margin: 0; color: #14354b;">{icon} Étape {step_num} — {title}</h3>
        <span style="color: #718096; font-size: 13px;">{duration_str}</span>
    </div>
    <p style="color: #4a5568; margin: 0 0 12px 0; font-size: 14px;">{description}</p>
    """, unsafe_allow_html=True)
