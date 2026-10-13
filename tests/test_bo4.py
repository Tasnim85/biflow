"""Comprehensive Unit Tests for BO4 Module."""
import unittest
import pandas as pd
from bo4.glossary import BusinessGlossaryNER
from bo4.misleading_detector import MisleadingComparisonDetector
from bo4.chart_classifier import ChartClassifier
from bo4.semantic_search import SemanticSearchEngine
from bo4.agent import BusinessIntelligenceAgent

class TestBO4(unittest.TestCase):

    def setUp(self):
        # Sample realistic transactions dataframe
        self.df = pd.DataFrame({
            "transaction_id": [1, 2, 3, 4, 5, 6],
            "city": ["Paris", "Lyon", "Paris", "Marseille", "Lyon", "Paris"],
            "amount": [120.5, 450.0, 95.0, 1200.0, 310.0, 80.0],
            "quantity": [2, 5, 1, 10, 3, 1],
            "category": ["Electronics", "Fashion", "Electronics", "Furniture", "Fashion", "Electronics"],
            "transaction_date": ["2026-01-15", "2026-01-20", "2026-02-10", "2026-02-15", "2026-03-01", "2026-03-12"]
        })

    def test_business_glossary_ner(self):
        ner = BusinessGlossaryNER()
        query = "Quel est le chiffre d'affaires total et la quantite vendue par region ?"
        entities = ner.extract_entities(query, available_columns=list(self.df.columns))
        
        canonicals = [e.canonical for e in entities]
        self.assertIn("total_amount", canonicals)
        self.assertIn("quantity", canonicals)
        self.assertIn("city", canonicals)
        self.assertIn("sum", canonicals)

    def test_semantic_search_execution(self):
        engine = SemanticSearchEngine()
        query = "Donne-moi le chiffre d'affaires par ville"
        res_df, intent, summary = engine.execute(query, self.df)

        self.assertFalse(res_df.empty)
        self.assertEqual(intent.metric, "amount")
        self.assertEqual(intent.dimension, "city")
        self.assertIn("amount", res_df.columns)
        self.assertIn("city", res_df.columns)
        self.assertIn("maximum", summary.lower())

    def test_chart_classifier(self):
        classifier = ChartClassifier()
        grouped = self.df.groupby("city", as_index=False)["amount"].sum()
        recommendation = classifier.recommend(grouped, metric_col="amount", dimension_col="city")

        self.assertIn(recommendation.chart_type, ["bar", "horizontal_bar"])
        self.assertIsNotNone(recommendation.figure)

    def test_misleading_comparison_detection(self):
        detector = MisleadingComparisonDetector()
        
        # Data with small relative variation and high baseline
        distorted_data = pd.DataFrame({
            "group": ["A", "B", "C"],
            "amount": [1000.0, 1050.0, 1020.0]
        })
        alerts = detector.analyze(distorted_data, metric_col="amount", dimension_col="group", chart_type="bar")
        
        self.assertTrue(any(a.category == "axis_truncation" for a in alerts))
        self.assertTrue(len(alerts) > 0)

    def test_bi_agent_end_to_end(self):
        agent = BusinessIntelligenceAgent()
        response = agent.ask("Montre-moi le total des ventes par categorie", self.df)

        self.assertIsNotNone(response.data)
        self.assertGreater(len(response.data), 0)
        self.assertIsNotNone(response.chart.figure)
        self.assertTrue(len(response.entities) > 0)
        self.assertIn("total", response.summary.lower())

if __name__ == "__main__":
    unittest.main()
