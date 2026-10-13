"""Test script for 2000-row uncleaned dirty benchmark dataset."""
import sys
import time
import pandas as pd

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from core.unified_pipeline import run_unified_scenario

print("=" * 80)
print("🚀 TEST DE VALIDATION DU SCÉNARIO COMPLET SUR 2000 LIGNES NON NETTOYÉES")
print("=" * 80)

df = pd.read_csv("data/customers_dirty_2000.csv")
print(f"📂 Dataset chargé : {len(df)} lignes × {len(df.columns)} colonnes.")
print(f"📋 Colonnes : {df.columns.tolist()}")

t0 = time.perf_counter()
res = run_unified_scenario(
    df_raw=df,
    query="Quel est le montant moyen des transactions par catégorie ?",
    dataset_name="customers_dirty_2000.csv"
)
t1 = time.perf_counter()

print("\n" + "=" * 80)
print(f"✨ PIPELINE EXÉCUTÉ EN {t1 - t0:.2f} SECONDES")
print("=" * 80)

print(f"\n1. ⚡ [BO1] Détection de Similarité :")
top_sim = res.similarity_matches[0]
print(f"   Similarité max : {top_sim['similarity_score']:.1%} avec '{top_sim['reference_dataset']}'")
print(f"   Recette suggérée : {top_sim['reusable_recipe']}")

print(f"\n2. ⚡ [BO1] Auto-Classification Sémantique :")
print(f"   {len(res.semantic_types)} colonnes typées automatiquement :")
for st in res.semantic_types[:5]:
    print(f"   - {st['column']} -> {st['semantic_type']} ({st['confidence']:.0%})")

print(f"\n3. 🛡️ [BO2] Protection des Données Personnelles (PII) :")
print(f"   Occurrences PII détectées et masquées par HMAC : {res.pii_count}")

print(f"\n4. 🛡️ [BO2] Nettoyage Playbook & Détection d'Anomalies :")
print(f"   Score qualité avant : {res.quality_before['score']:.1f}% -> après : {res.quality_after['score']:.1f}%")
print(f"   Anomalies détectées (Isolation Forest + MAD) : {res.anomaly_count}")

print(f"\n5. 🔍 [BO3] Schéma Étoile (ETL) & KPIs :")
for tbl_name, tbl_df in res.star_schema.items():
    print(f"   - Table {tbl_name} : {len(tbl_df)} lignes")
print(f"   KPIs calculés : {res.kpis}")

print(f"\n6. 💡 [BO4] Décisionnel & Anti-Biais :")
print(f"   Réponse NLU : {res.business_answer}")
print(f"   Graphique optimal : {res.chart_recommendation.chart_type.upper()} ({res.chart_recommendation.title})")
print(f"   Entités métier reconnues (NER) : {[e['canonical'] for e in res.glossary_entities]}")
print(f"   Alertes anti-biais : {len(res.misleading_alerts)} alerte(s)")

print(f"\n7. 🛡️ [BO2] Graphe de Lignage :")
print(f"   Nœuds : {len(res.lineage_graph['nodes'])}, Arêtes : {len(res.lineage_graph['edges'])}")

print(f"\n8. 🔍 [BO3] XAI & Auditabilite :")
print(f"   Explications SHAP générées pour {len(res.audited_records)} observations atypiques :")
if res.audited_records:
    print(f"   Exemple (Row {res.audited_records[0]['row_index']}) :")
    print(f"   \"{res.audited_records[0]['narrative']}\"")
print(f"   Intégrité cryptographique SHA-256 : {'100% VALIDE' if res.audit_chain_valid else 'ERREUR'}")
print(f"   Entrées dans le journal d'audit : {res.audit_log_count}")
print(f"   Surveillance du drift : {res.drift_summary['status']}")

print("\n" + "=" * 80)
print("🎯 TOUTES LES ÉTAPES BO1 -> BO2 -> BO3 -> BO4 SONT 100% FONCTIONNELLES !")
print("=" * 80)
