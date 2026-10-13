"""Standalone Runner and Interactive Demonstration for BO4: Democratize BI.

Executes a full demonstration of BO4 on real datasets:
1. Natural language query processing (NLU)
2. Business glossary recognition (NER)
3. Safe query aggregation
4. Chart type recommendation
5. Misleading comparisons analysis
"""
import sys
from pathlib import Path
import pandas as pd
from bo4.agent import BusinessIntelligenceAgent
from data_generator import generate_data

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

def run_demo():
    print("=" * 70)
    print("🚀 BIFlow - MODULE BO4 : DEMOCRATIZE BUSINESS INTELLIGENCE")
    print("=" * 70)

    # 1. Load or Generate Dataset
    root = Path(__file__).resolve().parent
    trans_path = root / "data/generated/transactions.csv"
    cust_path = root / "data/generated/customers.csv"

    if trans_path.exists() and cust_path.exists():
        print("📂 Chargement des données existantes...")
        transactions = pd.read_csv(trans_path)
        customers = pd.read_csv(cust_path)
        prod_path = root / "data/generated/products.csv"
        products = pd.read_csv(prod_path) if prod_path.exists() else pd.DataFrame()
    else:
        print("⚙️ Génération d'un jeu de données synthétique pour le test...")
        data = generate_data(500, 42)
        transactions = data["transactions"]
        customers = data["customers"]
        products = data.get("products", pd.DataFrame())

    # Intelligent join for realistic BI analytics
    client_key = 'client_id' if 'client_id' in transactions.columns else 'customer_id'
    cust_key = 'client_identifier' if 'client_identifier' in customers.columns else ('customer_id' if 'customer_id' in customers.columns else 'client_id')
    df = transactions.merge(customers, left_on=client_key, right_on=cust_key, how='left')
    if not products.empty and 'product_id' in df.columns and 'product_id' in products.columns:
        df = df.merge(products, on='product_id', how='left')

    print(f"📊 Dataset actif pour BO4 : {len(df)} lignes, colonnes : {list(df.columns)}")
    print("-" * 70)

    # 2. Test Questions for Persona Sarra
    questions = [
        "Quel est le chiffre d'affaires par région ?",
        "Donne-moi le volume de vente et la quantite par categorie",
        "Top 5 des clients par montant total",
        "Quelle est l'evolution des ventes par date ?"
    ]

    agent = BusinessIntelligenceAgent()

    for idx, q in enumerate(questions, 1):
        print(f"\n[{idx}] 👤 Question de Sarra : \"{q}\"")
        resp = agent.ask(q, df)

        print("\n  🏷️ Entités reconnues dans le Glossaire Métier (NER) :")
        for e in resp.entities:
            print(f"     • Terme : '{e.raw_term}' ➔ Canonique : '{e.canonical}' ({e.kind}) | Confiance : {int(e.confidence*100)}%")

        print(f"\n  💡 Réponse factuelle en langage naturel :")
        print(f"     ➔ {resp.summary}")

        print(f"\n  📈 Recommandation de Graphique :")
        print(f"     • Type optimal : {resp.chart.chart_type.upper()} ({resp.chart.title})")
        print(f"     • Justification : {resp.chart.rationale}")

        print(f"\n  ⚠️ Contrôle des Comparaisons Trompeuses (Anti-Biais) :")
        if resp.alerts:
            for alert in resp.alerts:
                print(f"     ⚠️ [{alert.severity}] {alert.title} : {alert.explanation}")
                print(f"        👉 Conseil : {alert.recommendation}")
        else:
            print("     ✅ Aucun biais visuel ni axe tronqué détecté. Comparaison proportionnelle et fiable.")

        print(f"\n  📋 Aperçu des résultats ({len(resp.data)} lignes) :")
        print(resp.data.head(5).to_string(index=False))
        print("-" * 70)

    # Export a sample chart to HTML for inspection
    sample_resp = agent.ask(questions[0], df)
    if sample_resp.chart.figure:
        out_html = root / "outputs/bo4_sample_chart.html"
        out_html.parent.mkdir(exist_ok=True)
        sample_resp.chart.figure.write_html(str(out_html))
        print(f"\n💾 Graphique Plotly interactif exporté dans : {out_html}")

    print("\n✅ Démonstration du module BO4 terminée avec succès !")

if __name__ == "__main__":
    run_demo()
