"""Local synthetic PII demonstration. Protected data is the default output."""
import json
import secrets
import streamlit as st
from data.pii_generator import generate_pii_dataset
from governance.pii import protect_pii

st.set_page_config(page_title="BIFlow • BO2-03", layout="wide")
st.title("BO2-03 · Détection et protection des données personnelles")
st.caption("DQ détecte · ETL protège · Démonstration locale sur données fictives")
st.info("Copie dédiée : les 7 colonnes initiales sont conservées ; full_name, email, phone, national_id et notes sont ajoutées. Le dataset original reste inchangé.")
st.warning("Prototype : règles, rôles de colonnes et dictionnaire de noms fictifs. Pas de reconnaissance générale des noms (NER), ni d’authentification multiutilisateur. Ne pas importer de données personnelles réelles dans cette démonstration.")
source = generate_pii_dataset()
if "pii_secret" not in st.session_state:
    st.session_state.pii_secret = secrets.token_bytes(32)
mode_label = st.radio("Politique de protection", ["Pseudonymisation (conserver les liens)", "Masquage (cacher les valeurs)"])
mode = "pseudonymize" if mode_label.startswith("Pseudonymisation") else "mask"
labels = {"PERSON": "Noms", "EMAIL": "Emails", "PHONE": "Téléphones", "DEMO_IDENTIFIER": "Identifiants personnels"}
selected = st.multiselect("Catégories personnelles à protéger", list(labels), default=list(labels), format_func=labels.get)
st.caption("Seules les catégories sélectionnées sont transformées. Dans les notes, seuls les fragments personnels sont remplacés : le reste du texte reste lisible. Les champs métier numériques restent inchangés dans cette démonstration ; cela ne signifie pas qu’ils ne sont jamais confidentiels.")
if len(selected) < len(labels):
    st.warning("Protection partielle : les catégories décochées seront détectées mais resteront lisibles, y compris dans l’export.")
st.caption("Les pseudonymes restent identiques pour une même valeur et un même type pendant la session, y compris dans les notes. Une nouvelle session change la clé. Aucune table de correspondance ni clé n’est exportée.")
if st.checkbox("Afficher les données fictives avant protection", value=False):
    st.dataframe(source.head(20).astype("string"), width="stretch")
selection_key = (mode, tuple(sorted(selected)))
if st.session_state.get("pii_mode") != selection_key:
    st.session_state.pop("pii_result", None)
if st.button("Détecter et protéger", type="primary"):
    st.session_state.pii_result = protect_pii(source, st.session_state.pii_secret, mode, selected)
    st.session_state.pii_mode = selection_key
result = st.session_state.get("pii_result")
if result is not None:
    a, b, c = st.columns(3)
    a.metric("Lignes", len(result.data))
    protected = result.detections[result.detections.action != "detected_only"]
    b.metric("Occurrences protégées", len(protected))
    c.metric("Colonnes concernées", protected.column.nunique())
    st.subheader("Données métier conservées")
    st.dataframe(result.data.iloc[:10, :7].astype("string"), width="stretch")
    st.subheader("Données protégées")
    st.dataframe(result.data.astype("string"), width="stretch")
    st.subheader("Détections par type")
    st.bar_chart(result.detections.entity.value_counts())
    st.subheader("Journal sans valeurs personnelles")
    st.dataframe(result.detections, width="stretch", hide_index=True)
    st.download_button("Exporter le résultat selon la sélection", result.data.to_csv(index=False), "customers-protected.csv", "text/csv")
    st.download_button("Exporter le journal", json.dumps({"manifest": result.manifest, "events": result.detections.to_dict(orient="records")}, ensure_ascii=False, indent=2), "pii-audit.json", "application/json")
    st.caption("Les données restent pseudonymisées, pas anonymes : les autres attributs peuvent permettre une réidentification. Les sorties ne sont pas automatiquement transmises aux autres agents.")
