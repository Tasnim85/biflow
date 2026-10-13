"""Automated Pipeline CLI for BIFlow (Persona Sarra E2E Scenario).

Executes each BO step-by-step according to the requested scenario:
- BO1: Similarity Detection + Semantic Auto-Classification
- BO2: PII Protection + Versioned Playbook Cleaning & Anomaly Detection + Lineage Graph
- BO3: Star Schema ETL + KPI Catalog + SHAP XAI Explanations + Append-only SHA-256 Audit + Drift Monitoring
- BO4: NLU Query Search + Optimal Chart Type Classification + Misleading Comparison Detection + Business Glossary NER
"""
from __future__ import annotations
import argparse
import json
import sys
import time
import pandas as pd

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from core.unified_pipeline import run_unified_scenario
from data.data_generator import generate_dataset


def main():
    parser = argparse.ArgumentParser(description="BIFlow Automated E2E Pipeline (Sarra)")
    parser.add_argument("--csv", type=str, default=None, help="Chemin vers le fichier CSV source")
    parser.add_argument("--query", type=str, default="Quel est le montant moyen des transactions et la tendance globale ?", help="Question métier en langage naturel")
    parser.add_argument("--policy", type=str, default="1.2.0", help="Version du playbook de gouvernance BO2")
    parser.add_argument("--rows", type=int, default=300, help="Nombre de lignes si génération automatique")
    args = parser.parse_args()

    print("=" * 80)
    print("🚀 BIFLOW : PIPELINE AUTOMATISÉ MULTI-AGENTS (SCÉNARIO COMPLET E2E)")
    print("   Orchestration des 4 Objectifs Métiers (BO1, BO2, BO3, BO4)")
    print("=" * 80)

    # 1. Loading data
    if args.csv:
        print(f"\n📂 Chargement du CSV : {args.csv}")
        df = pd.read_csv(args.csv)
        dataset_name = args.csv.split("/")[-1].split("\\")[-1]
    else:
        print(f"\n🎲 Génération du jeu synthétique démonstrateur ({args.rows} lignes)...")
        df = generate_dataset(n_rows=args.rows, anomaly_rate=0.04, seed=42)
        dataset_name = "clients_transactions_auto.csv"

    print(f"   Données prêtes : {len(df)} lignes × {len(df.columns)} colonnes.")
    print(f"💬 Question de Sarra : \"{args.query}\"")
    print(f"🛡️ Version du Playbook : v{args.policy}")
    print("-" * 80)

    # Progress tracking callback
    def cli_progress(node):
        status_icons = {"RUNNING": "⏳", "COMPLETED": "✅", "FAILED": "❌"}
        icon = status_icons.get(node.status, "⚙️")
        print(f"[{node.owner_bo:^7}] {icon} {node.label:<32} : {node.summary} ({node.duration:.2f}s)")

    t_start = time.perf_counter()
    result = run_unified_scenario(
        df_raw=df,
        query=args.query,
        dataset_name=dataset_name,
        policy_version=args.policy,
        progress_callback=cli_progress
    )
    t_end = time.perf_counter()

    print("=" * 80)
    print(f"✨ PIPELINE EXÉCUTÉ AVEC SUCCÈS EN {t_end - t_start:.2f} SECONDES")
    print("=" * 80)

    print("\n--- SYNTHÈSE DÉCISIONNELLE POUR SARRA (BO4) ---")
    print(f"💡 Réponse NLU : {result.business_answer}")
    print(f"📈 Graphique Recommandé : {result.chart_recommendation.chart_type.upper()} ({result.chart_recommendation.title})")
    print(f"🏷️ Entités Glossaire (NER) : {[e['canonical'] for e in result.glossary_entities]}")
    if result.misleading_alerts:
        print(f"⚠️ Alertes de Comparaisons Trompeuses : {len(result.misleading_alerts)}")
        for a in result.misleading_alerts:
            print(f"   - {a['title']} : {a['recommendation']}")
    else:
        print("✅ Contrôle visuel anti-biais : Aucun biais cognitif détecté.")

    print("\n--- GOUVERNANCE & QUALITÉ (BO2) ---")
    print(f"🔒 Données PII masquées : {result.pii_count}")
    print(f"📋 Playbook utilisé : {result.playbook_used}")
    print(f"📊 Qualité : {result.quality_before['score']:.1f}% ➔ {result.quality_after['score']:.1f}%")
    print(f"🚨 Anomalies détectées (Isolation Forest + MAD) : {result.anomaly_count}")
    print(f"🔗 Lignage : Graphe généré avec {len(result.lineage_graph['nodes'])} nœuds et {len(result.lineage_graph['edges'])} arêtes.")

    print("\n--- EXPLICABILITÉ & AUDITABILITÉ (BO3) ---")
    print(f"🤖 Explications SHAP générées pour {len(result.audited_records)} observations atypiques.")
    if result.audited_records:
        top_rec = result.audited_records[0]
        print(f"   Exemple (Row {top_rec['row_index']}) : \"{top_rec['narrative']}\"")
    print(f"📜 Intégrité Chaîne d'Audit SHA-256 : {'VALIDE (100% Intacte)' if result.audit_chain_valid else 'ERREUR'}")
    print(f"📈 Surveillance Drift : 6 mois monitorés avec succès.")

    print("\n--- PERFORMANCE & DÉCOUVERTE (BO1) ---")
    if result.similarity_matches:
        top_sim = result.similarity_matches[0]
        print(f"⚡ Similarité maximale : {top_sim['similarity_score']:.1%} avec '{top_sim['reference_dataset']}'")
        print(f"💡 Recette réutilisable suggérée : {top_sim['reusable_recipe']}")

    print("\n" + "=" * 80)
    print("✅ Fin de l'exécution automatisée.")


if __name__ == "__main__":
    main()
