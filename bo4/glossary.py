"""Business Glossary Recognition and Named Entity Recognition (NER) for BO4.

Maps business terms, vernacular, and user vocabulary in French and English
to canonical KPIs, metrics, dimensions, and filter conditions.
"""
from __future__ import annotations
import re
import unicodedata
from difflib import SequenceMatcher
from typing import TypedDict

def normalize_text(text: str) -> str:
    """Normalize text: lowercase, remove accents and punctuation."""
    text = text.lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8')
    text = re.sub(r'[^\w\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()

class GlossaryTerm(TypedDict):
    term: str
    canonical: str
    type: str  # 'metric', 'dimension', 'aggregation', 'temporal'
    formula: str
    description: str
    synonyms: list[str]

# Rich business glossary covering retail, e-commerce, finance and operations
BUSINESS_GLOSSARY: list[GlossaryTerm] = [
    # Metrics
    {
        "term": "Chiffre d'Affaires",
        "canonical": "total_amount",
        "type": "metric",
        "formula": "SUM(amount)",
        "description": "Total des revenus générés par les transactions",
        "synonyms": [
            "chiffre d affaires", "chiffre d affaire", "ca", "revenu", "revenus", 
            "ventes", "total des ventes", "revenue", "sales", "turnover", "montant total", "montant"
        ]
    },
    {
        "term": "Quantité Vendue",
        "canonical": "quantity",
        "type": "metric",
        "formula": "SUM(quantity)",
        "description": "Nombre total d'unités d'articles vendues",
        "synonyms": [
            "quantite", "quantites", "unites", "volumes", "volume", 
            "volume de vente", "quantity", "qty", "units", "items sold", "nombre d articles"
        ]
    },
    {
        "term": "Panier Moyen",
        "canonical": "average_basket",
        "type": "metric",
        "formula": "AVG(amount)",
        "description": "Montant moyen dépensé par transaction",
        "synonyms": [
            "panier moyen", "ticket moyen", "montant moyen", "prix moyen", 
            "average order value", "aov", "average basket", "moyenne des ventes"
        ]
    },
    {
        "term": "Nombre de Transactions",
        "canonical": "transaction_count",
        "type": "metric",
        "formula": "COUNT(transaction_id)",
        "description": "Volume total des commandes ou transactions",
        "synonyms": [
            "nombre de transactions", "commandes", "achats", "nombre de ventes", 
            "orders", "transactions", "count", "nombre", "total commandes"
        ]
    },
    {
        "term": "Âge des Clients",
        "canonical": "age",
        "type": "metric",
        "formula": "AVG(age)",
        "description": "Âge moyen des clients ou utilisateurs",
        "synonyms": ["age", "ages", "anciennete", "age moyen", "customer age"]
    },
    {
        "term": "Salaire",
        "canonical": "salary",
        "type": "metric",
        "formula": "AVG(salary)",
        "description": "Rémunération des employés",
        "synonyms": ["salaire", "salaires", "remuneration", "salary", "pay", "revenu employe"]
    },
    
    # Dimensions
    {
        "term": "Région / Localisation",
        "canonical": "city",
        "type": "dimension",
        "formula": "GROUP BY city",
        "description": "Zone géographique ou ville du client/magasin",
        "synonyms": ["region", "regions", "ville", "villes", "localisation", "zone", "pays", "city", "location", "country"]
    },
    {
        "term": "Catégorie de Produit",
        "canonical": "category",
        "type": "dimension",
        "formula": "GROUP BY category",
        "description": "Famille ou rayon de produits",
        "synonyms": ["categorie", "categories", "rayon", "famille", "type de produit", "category", "department", "genre"]
    },
    {
        "term": "Nom du Produit",
        "canonical": "product_name",
        "type": "dimension",
        "formula": "GROUP BY product_name",
        "description": "Désignation individuelle de l'article",
        "synonyms": ["produit", "produits", "article", "articles", "item", "items", "product", "product name", "nom produit"]
    },
    {
        "term": "Nom du Client",
        "canonical": "full_name",
        "type": "dimension",
        "formula": "GROUP BY full_name",
        "description": "Identité du client ou consommateur",
        "synonyms": ["client", "clients", "acheteur", "acheteurs", "consommateur", "customer", "customer name", "nom client"]
    },
    {
        "term": "Méthode de Paiement",
        "canonical": "payment_method",
        "type": "dimension",
        "formula": "GROUP BY payment_method",
        "description": "Mode de règlement (Carte, Virement, Espèces, etc.)",
        "synonyms": ["paiement", "moyen de paiement", "mode de paiement", "payment", "payment method", "carte", "especes"]
    },
    {
        "term": "Date / Période",
        "canonical": "transaction_date",
        "type": "temporal",
        "formula": "DATE_TRUNC('month', transaction_date)",
        "description": "Dimension temporelle de l'événement",
        "synonyms": ["date", "dates", "periode", "mois", "annee", "jour", "trimestre", "temps", "time", "month", "year", "day"]
    }
]

# Aggregation keywords mapping
AGGREGATIONS = {
    "sum": ["total", "somme", "chiffre", "cumul", "totalite", "sum"],
    "avg": ["moyen", "moyenne", "moyennes", "average", "avg", "mean"],
    "count": ["nombre", "combien", "frequence", "volume", "totalite", "count"],
    "max": ["maximum", "max", "meilleur", "plus grand", "plus eleve", "plus cher", "top"],
    "min": ["minimum", "min", "pire", "plus bas", "plus faible", "moins cher"]
}

class RecognizedEntity:
    def __init__(self, raw_term: str, canonical: str, kind: str, confidence: float, explanation: str):
        self.raw_term = raw_term
        self.canonical = canonical
        self.kind = kind
        self.confidence = confidence
        self.explanation = explanation

    def to_dict(self) -> dict:
        return {
            "raw_term": self.raw_term,
            "canonical": self.canonical,
            "kind": self.kind,
            "confidence": round(self.confidence, 2),
            "explanation": self.explanation
        }

class BusinessGlossaryNER:
    """Named Entity Recognizer that links natural language terms to formal schema entities."""

    def __init__(self, terms: list[GlossaryTerm] | None = None):
        self.glossary = terms or BUSINESS_GLOSSARY

    def extract_entities(self, query: str, available_columns: list[str] | None = None) -> list[RecognizedEntity]:
        normalized_query = normalize_text(query)
        words = normalized_query.split()
        found: list[RecognizedEntity] = []
        matched_spans: set[str] = set()

        # 1. Exact & Synonym matching from Glossary
        for entry in self.glossary:
            for syn in entry["synonyms"]:
                norm_syn = normalize_text(syn)
                # Check for word boundary substring
                pattern = r'\b' + re.escape(norm_syn) + r'\b'
                if re.search(pattern, normalized_query):
                    if norm_syn not in matched_spans:
                        matched_spans.add(norm_syn)
                        found.append(RecognizedEntity(
                            raw_term=syn,
                            canonical=entry["canonical"],
                            kind=entry["type"],
                            confidence=0.95,
                            explanation=f"Reconnu dans le glossaire métier comme '{entry['term']}' ({entry['type']})"
                        ))
                        break

        # 2. Dynamic column name matching (if table columns provided)
        if available_columns:
            for col in available_columns:
                norm_col = normalize_text(col)
                if norm_col in words or any(norm_col in syn for syn in matched_spans):
                    continue
                # Sequence matcher for close fuzzy matches
                for word in words:
                    if len(word) >= 4 and len(norm_col) >= 4:
                        ratio = SequenceMatcher(None, word, norm_col).ratio()
                        if ratio >= 0.85 and word not in matched_spans:
                            matched_spans.add(word)
                            found.append(RecognizedEntity(
                                raw_term=word,
                                canonical=col,
                                kind="dimension" if not col.endswith(("_id", "_amount", "price", "age", "salary")) else "metric",
                                confidence=round(ratio, 2),
                                explanation=f"Correspondance floue ({round(ratio*100)}%) avec la colonne '{col}'"
                            ))

        # 3. Aggregation extraction
        for agg_type, keywords in AGGREGATIONS.items():
            for kw in keywords:
                if re.search(r'\b' + re.escape(kw) + r'\b', normalized_query):
                    found.append(RecognizedEntity(
                        raw_term=kw,
                        canonical=agg_type,
                        kind="aggregation",
                        confidence=0.90,
                        explanation=f"Opérateur d'agrégation détecté : '{agg_type.upper()}'"
                    ))
                    break

        return found
