"""BO2-02 interactive demonstration on the project's customer data."""

import json

import streamlit as st

from data.data_generator import generate_dataset
from governance.playbooks import clean_dataset, load_policy
from data.dirty_generator import generate_dirty_dataset, defect_catalog

st.set_page_config(page_title="BIFlow • BO2-02", layout="wide")
st.title("BO2-02 · Playbooks de nettoyage versionnés")
st.caption("DQ choisit la politique · SEM valide les rôles · ETL applique les règles")
st.info("Données synthétiques du projet. Les politiques sont approuvées pour cette démonstration uniquement.")

version = st.selectbox("Version de la politique", ["1.2.0", "1.1.0", "1.0.0"])
scenario = st.checkbox("Utiliser le nouveau dataset avec défauts", value=True, key="new_dirty_dataset")
source = generate_dirty_dataset() if scenario else generate_dataset()
st.caption("Même schéma que le projet : age, income, spending_score, transaction_amount, num_transactions, true_anomaly, anomaly_type. Les deux dernières colonnes restent des annotations de simulation : aucune anomalie statistique étiquetée dans ce générateur.")
if scenario:
    st.info("500 clients créés directement sous forme de données brutes imparfaites, avec les mêmes 7 colonnes. Aucun dataset propre intermédiaire. Formats numériques, valeurs absentes, champs vides, texte inattendu, valeurs négatives, limites dépassées, entiers attendus, unités et séparateurs ambigus, valeurs non finies.")
    with st.expander("Voir les modes de génération et le traitement attendu", expanded=True):
        st.dataframe(defect_catalog(), width="stretch", hide_index=True)
    st.dataframe(source.head(22).astype("string"), width="stretch")
else:
    st.info("Données originales : aucune correction attendue selon les règles actuelles.")
st.download_button("Télécharger les données avant nettoyage", source.to_csv(index=False), "customers-dirty.csv" if scenario else "customers-original.csv", "text/csv")

policy = load_policy(version)
with st.expander("Politique et validation sémantique"):
    st.json(policy)
st.caption("1.2.0 normalise les nombres : espaces retirés et virgule interprétée comme séparateur décimal. Les valeurs manquantes ou invalides restent à réviser. Les anciennes versions ne corrigent pas ces formats numériques.")

key = ("raw-generation-v3", version, scenario)
if st.session_state.get("cleaning_key") != key:
    st.session_state.pop("cleaning_result", None)
if st.button("Appliquer le playbook", type="primary"):
    st.session_state.cleaning_result = clean_dataset(source, policy)
    st.session_state.cleaning_key = key

result = st.session_state.get("cleaning_result")
if result is None:
    st.subheader("Données à traiter")
    st.dataframe(source.astype("string"), width="stretch")
else:
    events = result.events
    a, b, c = st.columns(3)
    a.metric("Lignes", len(result.data))
    b.metric("Cellules modifiées", int((events.action == "change").sum()))
    c.metric("Lignes à réviser", len(result.review_positions))
    changes = events[events.action == "change"]
    if not changes.empty:
        st.subheader("Corrections effectuées — avant / après")
        st.dataframe(changes[["row_position", "column", "before", "after", "rule"]], width="stretch", hide_index=True)
    elif events.empty:
        st.info("Aucune correction nécessaire selon cette politique. Cela ne garantit pas l’absence d’autres problèmes de qualité.")
    left, right = st.columns(2)
    with left:
        st.subheader("Avant")
        st.dataframe(source.astype("string"), width="stretch")
    with right:
        st.subheader("Après")
        st.dataframe(result.data.astype("string"), width="stretch")
    st.subheader("Journal des changements et exceptions")
    st.dataframe(events, width="stretch", hide_index=True)
    if result.review_positions:
        st.warning("Ces lignes restent à réviser : les valeurs absentes ou invalides ne sont pas inventées. L’export complet contient encore ces exceptions.")
        st.dataframe(result.data.iloc[result.review_positions].astype("string"), width="stretch")
    skipped = result.manifest["skipped_optional_rules"]
    if skipped:
        st.caption("Règles optionnelles non applicables : " + ", ".join(skipped))
    st.download_button("Exporter les données (exceptions incluses)", result.data.to_csv(index=False), "customers-cleaned.csv", "text/csv")
    st.download_button("Exporter le journal et la politique", json.dumps({"manifest": result.manifest, "events": events.to_dict(orient="records")}, indent=2, ensure_ascii=False), "cleaning-audit.json", "application/json")
    with st.expander("Traçabilité de l’exécution"):
        st.json(result.manifest)
