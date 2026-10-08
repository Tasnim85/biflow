"""BO2-07 profiling and analyst context."""
import json
import streamlit as st
from agents.anomaly_agent import profile_anomalies
from data.dirty_generator import generate_dirty_dataset
from data.data_generator import generate_dataset, FEATURES

st.set_page_config(page_title="BIFlow • BO2-07", layout="wide")
st.title("BO2-07 · Anomalies pendant le profilage")
st.caption("DQ détecte · SEM fournit les contraintes · ANA examine le contexte · ORCH oriente la révision")
dataset = st.selectbox("Données", ["Données brutes générées (BO2-02)", "Clients synthétiques du projet (BO3)"])
contamination = st.slider("Fraction supposée atypique pour Isolation Forest", 0.01, 0.20, 0.03, 0.01)
threshold = st.slider("Seuil robuste (écart à la médiane / MAD)", 2.0, 6.0, 3.5, 0.5)
st.info("Les scores ne sont pas des probabilités d’erreur. Aucun point atypique n’est supprimé ni remplacé. Les lignes non résolues par BO2-02 sont exclues du modèle et restent visibles.")
st.caption("Pas d’analyse temporelle : le schéma ne contient pas de date. Les annotations true_anomaly et anomaly_type ne sont jamais utilisées comme variables du modèle.")
context_text = st.text_area("Contexte ANA facultatif : une ligne 'position: justification' par observation", placeholder="42: promotion confirmée par l’équipe métier")
source = generate_dirty_dataset() if dataset.startswith("Données brutes") else generate_dataset()
key = (dataset, contamination, threshold, context_text)
if st.session_state.get("anomaly_key") != key:
    st.session_state.pop("anomaly_result", None)
if st.button("Lancer le profilage", type="primary"):
    try:
        contexts = {}
        for line in context_text.splitlines():
            if line.strip():
                position, reason = line.split(":", 1)
                position = int(position.strip())
                if position in contexts:
                    raise ValueError("Position répétée dans le contexte")
                contexts[position] = reason.strip()
        st.session_state.anomaly_result = profile_anomalies(source, contamination, threshold, contexts)
        st.session_state.anomaly_key = key
    except ValueError as error:
        st.error(f"Paramètres ou contexte invalides : {error}")
result = st.session_state.get("anomaly_result")
if result is not None:
    rows = result.rows
    a, b, c = st.columns(3)
    a.metric("Lignes évaluables", int(rows.eligible.sum()))
    b.metric("Lignes avec contraintes à réviser", int((~rows.eligible).sum()))
    c.metric("Signaux statistiques", int((rows.robust_flag | rows.isolation_flag).sum()))
    st.bar_chart(rows.status.value_counts())
    st.dataframe(rows, width="stretch", hide_index=True)
    if result.metadata["zero_mad_columns"]:
        st.warning("MAD nulle : score robuste non informatif pour " + ", ".join(result.metadata["zero_mad_columns"]))
    if rows.eligible.sum() < 10:
        st.warning("Moins de 10 lignes évaluables : modèles statistiques non exécutés.")
    position = st.selectbox("Position de ligne à examiner", rows.row_position.tolist())
    st.dataframe(result.cleaning.data.iloc[[position]][FEATURES].astype("string"), width="stretch")
    st.write(rows.loc[position, ["status", "reason", "context"]].to_dict())
    st.subheader("Scores robustes par colonne")
    st.dataframe(result.robust_scores.iloc[[position]], width="stretch")
    st.caption("Une justification peut rendre un signal plausible, mais ne neutralise jamais une violation de contrainte. Les responsabilités ANA/ORCH sont simulées localement ; aucune notification externe n’est envoyée.")
    st.download_button("Exporter les résultats", rows.to_csv(index=False), "bo2-07-profiling.csv", "text/csv")
    payload = {"metadata": result.metadata, "rows": json.loads(rows.to_json(orient="records")),
               "robust_scores": json.loads(result.robust_scores.to_json(orient="records"))}
    st.download_button("Exporter la traçabilité JSON", json.dumps(payload, ensure_ascii=False, indent=2), "bo2-07-audit.json", "application/json")
    with st.expander("Paramètres et politique utilisés"):
        st.json(result.metadata)
