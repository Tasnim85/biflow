"""Generator for a comprehensive 2000-row dirty dataset for BIFlow.

Tests all 4 Business Objectives (BO1, BO2, BO3, BO4) with realistic defects:
- BO1: Multi-type schema for similarity & semantic auto-classification (NLP+ML)
- BO2: Real PII (emails, phones, names), dirty numeric formats (" 181,50 "), units, missing, negative values
- BO3: Core features for Isolation Forest + MAD + SHAP explanations + append-only SHA-256 audit
- BO4: Categorical dimensions (city, category, date) for NLU search, optimal chart & anti-bias
"""
from __future__ import annotations
import random
import numpy as np
import pandas as pd


def generate_comprehensive_dirty_dataset(n_rows: int = 2000, seed: int = 42) -> pd.DataFrame:
    random.seed(seed)
    rng = np.random.default_rng(seed)

    first_names = ["Jean", "Marie", "Mohamed", "Sarra", "Ahmed", "Fatma", "Pierre", "Sophie", "Ali", "Yasmine", "Lucas", "Camille"]
    last_names = ["Dupont", "Martin", "Ben Salah", "Trabelsi", "Bernard", "Petit", "Hammami", "Gharbi", "Dubois", "Moreau"]
    cities = ["Tunis", "Paris", "Sousse", "Lyon", "Sfax", "Marseille", "Bizerte", "Nabeul", "Toulouse", "Monastir"]
    categories = ["Électronique", "Mode & Habillement", "Maison & Déco", "Alimentation", "Cosmétique & Beauté", "Sport & Loisirs"]

    records = []

    for i in range(1, n_rows + 1):
        # 1. PII data (BO2)
        fn = random.choice(first_names)
        ln = random.choice(last_names)
        full_name = f"{fn} {ln}"
        
        # Email variations
        email_r = rng.random()
        if email_r < 0.03:
            email = "non renseigné"
        elif email_r < 0.06:
            email = ""
        elif email_r < 0.08:
            email = "invalid_email_format"
        else:
            domain = random.choice(["gmail.com", "yahoo.fr", "outlook.com", "esprit.tn", "entreprise.com"])
            clean_fn = fn.lower().replace("é", "e").replace("è", "e")
            clean_ln = ln.lower().replace(" ", "").replace("é", "e")
            email = f"{clean_fn}.{clean_ln}{random.randint(1, 99)}@{domain}"

        # Phone variations
        phone_r = rng.random()
        if phone_r < 0.03:
            phone = "inconnu"
        elif phone_r < 0.05:
            phone = "   "
        elif phone_r < 0.50:
            phone = f"+216 {rng.choice([20, 50, 98, 22])} {rng.integers(100, 999)} {rng.integers(100, 999)}"
        else:
            phone = f"+33 6 {rng.integers(10, 99)} {rng.integers(10, 99)} {rng.integers(10, 99)} {rng.integers(10, 99)}"

        # 2. Dimensions (BO4)
        city_r = rng.random()
        if city_r < 0.02:
            city = None
        elif city_r < 0.05:
            city = "PARIS" if rng.random() < 0.5 else "tunis"
        else:
            city = random.choice(cities)

        category = random.choice(categories) if rng.random() > 0.02 else "Autre / Inconnu"
        
        # Dates (mixed formats)
        day = rng.integers(1, 29)
        month = rng.integers(1, 13)
        if rng.random() < 0.3:
            date_str = f"{day:02d}/{month:02d}/2026"
        else:
            date_str = f"2026-{month:02d}-{day:02d}"

        # 3. Quantitative fields (BO1, BO2, BO3) with realistic dirty defects
        # Customer ID (occasional duplicates or formatting)
        cust_id = f"CUST-{i:05d}"
        if rng.random() < 0.01:
            cust_id = f"CUST-00042"  # duplicate

        # Age
        age_mode = rng.choice(["normal", "comma_format", "unit", "negative", "extreme", "missing", "text"],
                              p=[0.80, 0.06, 0.04, 0.03, 0.02, 0.03, 0.02])
        if age_mode == "normal":
            age = int(rng.integers(18, 75))
        elif age_mode == "comma_format":
            age = f"  {rng.integers(18, 75)},00  "
        elif age_mode == "unit":
            age = f"{rng.integers(20, 65)} ans"
        elif age_mode == "negative":
            age = -int(rng.integers(15, 60))
        elif age_mode == "extreme":
            age = rng.choice([150, 180, 220])
        elif age_mode == "missing":
            age = None
        else:
            age = "inconnu"

        # Income
        inc_mode = rng.choice(["normal", "comma_format", "currency", "negative", "outlier", "missing", "text"],
                              p=[0.78, 0.08, 0.04, 0.02, 0.02, 0.03, 0.03])
        if inc_mode == "normal":
            income = round(float(rng.uniform(15000, 95000)), 2)
        elif inc_mode == "comma_format":
            val = round(float(rng.uniform(20000, 85000)), 2)
            income = f"  {val:.2f}  ".replace(".", ",")
        elif inc_mode == "currency":
            income = f"{rng.integers(25000, 75000)} EUR"
        elif inc_mode == "negative":
            income = -round(float(rng.uniform(500, 5000)), 2)
        elif inc_mode == "outlier":
            income = round(float(rng.uniform(350000, 950000)), 2)  # High wealth outlier for XAI
        elif inc_mode == "missing":
            income = "   "
        else:
            income = "non renseigné"

        # Spending Score
        sp_mode = rng.choice(["normal", "comma_format", "outlier", "negative", "missing"],
                             p=[0.85, 0.06, 0.03, 0.02, 0.04])
        if sp_mode == "normal":
            spending_score = int(rng.integers(1, 101))
        elif sp_mode == "comma_format":
            spending_score = f" {rng.integers(1, 100)},00 "
        elif sp_mode == "outlier":
            spending_score = int(rng.integers(180, 350))
        elif sp_mode == "negative":
            spending_score = -int(rng.integers(5, 50))
        else:
            spending_score = None

        # Transaction Amount
        tr_mode = rng.choice(["normal", "comma_format", "currency", "spike_outlier", "negative", "missing", "text"],
                             p=[0.78, 0.08, 0.04, 0.03, 0.02, 0.03, 0.02])
        if tr_mode == "normal":
            transaction_amount = round(float(rng.uniform(10, 250)), 2)
        elif tr_mode == "comma_format":
            v = round(float(rng.uniform(15, 220)), 2)
            transaction_amount = f"  {v:.2f}  ".replace(".", ",")
        elif tr_mode == "currency":
            transaction_amount = f"{round(float(rng.uniform(20, 180)), 2)} €"
        elif tr_mode == "spike_outlier":
            transaction_amount = round(float(rng.uniform(2500, 15000)), 2)  # Giant fraud/whale transaction for XAI
        elif tr_mode == "negative":
            transaction_amount = -round(float(rng.uniform(10, 150)), 2)
        elif tr_mode == "missing":
            transaction_amount = None
        else:
            transaction_amount = "N/A"

        # Number of transactions
        num_mode = rng.choice(["normal", "float_defect", "unit", "negative", "missing"],
                              p=[0.85, 0.05, 0.04, 0.02, 0.04])
        if num_mode == "normal":
            num_transactions = int(rng.poisson(18))
        elif num_mode == "float_defect":
            num_transactions = "3.5"
        elif num_mode == "unit":
            num_transactions = f"{rng.integers(5, 40)} trans."
        elif num_mode == "negative":
            num_transactions = -int(rng.integers(1, 10))
        else:
            num_transactions = None

        records.append({
            "customer_id": cust_id,
            "full_name": full_name,
            "email": email,
            "phone": phone,
            "city": city,
            "product_category": category,
            "transaction_date": date_str,
            "age": age,
            "income": income,
            "spending_score": spending_score,
            "transaction_amount": transaction_amount,
            "num_transactions": num_transactions,
        })

    return pd.DataFrame(records)


if __name__ == "__main__":
    df = generate_comprehensive_dirty_dataset(2000, seed=2026)
    out_path = "data/customers_dirty_2000.csv"
    df.to_csv(out_path, index=False, encoding="utf-8")
    print(f"Generated {len(df)} dirty rows saved to {out_path}.")
    print("Columns:", df.columns.tolist())
    print("\nHead sample:\n", df.head(3))
