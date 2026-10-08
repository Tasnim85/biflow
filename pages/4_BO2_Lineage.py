"""Navigable provenance for actually computed demonstration KPIs."""
import json
import streamlit as st
from data.dirty_generator import generate_dirty_dataset
from governance.lineage import build_lineage, graph_dot
from governance.neo4j_store import ancestors, load_runs, save_run
from neo4j.exceptions import Neo4jError, ServiceUnavailable, SessionExpired

st.set_page_config(page_title="BIFlow • BO2-05", layout="wide")
st.title("BO2-05 · Traçabilité des colonnes et indicateurs")
st.caption("ETL émet les dépendances · SEM décrit les calculs · DQ trace les règles · XAI expose le graphe")
st.info("Calculs réels sur le dataset synthétique BO2-02, nettoyé avec la politique 1.2.0. Une ligne est exclue des indicateurs si une des cinq colonnes métier reste à réviser.")
st.caption("La somme des montants n’est pas présentée comme un chiffre d’affaires : le sens métier de transaction_amount ne permet pas de l’affirmer. Aucune jointure n’est inventée.")
st.caption("Stockage et parcours du graphe : Neo4j. Les exécutions SQLite antérieures restent archivées.")
try:
    if st.button("Calculer les indicateurs et enregistrer la traçabilité", type="primary"):
        save_run(build_lineage(generate_dirty_dataset()))
    runs = load_runs()
except (Neo4jError, ServiceUnavailable, SessionExpired, ValueError, OSError):
    st.error("Neo4j indisponible ou configuration invalide. Démarrer le service avec docker compose -f compose.neo4j.yml up -d et vérifier la configuration locale .env. Aucun repli automatique vers SQLite.")
    st.stop()
if not runs:
    st.info("Lance un calcul pour créer la première exécution et son graphe.")
else:
    selected = st.selectbox("Exécution enregistrée (UTC)", range(len(runs)), format_func=lambda i: runs[i]["created_at"] + " · " + runs[i]["run_id"][:8])
    graph = runs[selected]
    kpis = [n for n in graph["nodes"] if n["kind"] == "kpi"]
    for column, kpi in zip(st.columns(len(kpis)), kpis):
        column.metric(kpi["label"], "Non calculable" if kpi["value"] is None else f'{kpi["value"]:,.2f}')
    target = st.selectbox("Indicateur à retracer", [n["id"] for n in kpis], format_func=lambda id: next(n["label"] for n in kpis if n["id"] == id))
    try:
        lineage = ancestors(graph, target)
    except (Neo4jError, ServiceUnavailable, SessionExpired, ValueError, OSError):
        st.error("Le parcours Neo4j a échoué. Vérifier la connexion et relancer.")
        st.stop()
    st.graphviz_chart(graph_dot(lineage))
    st.caption("Les cinq colonnes contribuent à la sélection des lignes ; seule la colonne agrégée contribue à la valeur de l’indicateur. Les relations détaillées distinguent ces dépendances.")
    node_id = st.selectbox("Inspecter un nœud du parcours", [n["id"] for n in lineage["nodes"]], format_func=lambda id: next(n["label"] for n in lineage["nodes"] if n["id"] == id))
    st.json(next(n for n in lineage["nodes"] if n["id"] == node_id))
    with st.expander("Relations versionnées"):
        st.dataframe(lineage["edges"], width="stretch", hide_index=True)
    with st.expander("Politique et empreintes de données"):
        st.json(graph["cleaning_manifest"])
    st.download_button("Exporter le graphe complet JSON", json.dumps(graph, ensure_ascii=False, indent=2), "lineage.json", "application/json")
    st.caption("Historique persistant dans Neo4j ; parcours calculés par Cypher. Métadonnées uniquement, sans valeurs personnelles sources. Prototype local : pas de serveur OpenLineage, ni graphe automatique des DSO PII/anomalies ou des systèmes externes.")
