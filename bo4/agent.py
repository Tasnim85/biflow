"""Unified Business Intelligence Agent for BO4 (Democratize BI).

Connects Natural Language Querying, Business Glossary (NER),
Misleading Comparison Detection, and Optimal Chart Recommendation.
"""
from __future__ import annotations
import pandas as pd
from bo4.glossary import BusinessGlossaryNER, RecognizedEntity
from bo4.semantic_search import SemanticSearchEngine, QueryIntent
from bo4.chart_classifier import ChartClassifier, ChartRecommendation
from bo4.misleading_detector import MisleadingComparisonDetector, MisleadingAlert

class BIResponse:
    def __init__(
        self,
        query: str,
        entities: list[RecognizedEntity],
        intent: QueryIntent,
        data: pd.DataFrame,
        chart: ChartRecommendation,
        alerts: list[MisleadingAlert],
        summary: str
    ):
        self.query = query
        self.entities = entities
        self.intent = intent
        self.data = data
        self.chart = chart
        self.alerts = alerts
        self.summary = summary

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "entities": [e.to_dict() for e in self.entities],
            "intent": self.intent.to_dict(),
            "summary": self.summary,
            "chart": self.chart.to_dict(),
            "alerts": [a.to_dict() for a in self.alerts],
            "row_count": len(self.data)
        }

class BusinessIntelligenceAgent:
    """End-to-end Conversational BI Agent for business personas like Sarra."""

    def __init__(self):
        self.ner = BusinessGlossaryNER()
        self.search_engine = SemanticSearchEngine(self.ner)
        self.chart_classifier = ChartClassifier()
        self.misleading_detector = MisleadingComparisonDetector()

    def ask(self, query: str, df: pd.DataFrame) -> BIResponse:
        # 1. Extract Business Glossary Entities (NER)
        entities = self.ner.extract_entities(query, available_columns=list(df.columns))

        # 2. Parse & Execute Query on DataFrame
        result_df, intent, summary = self.search_engine.execute(query, df)

        # 3. Classify & Generate Optimal Plotly Chart
        chart = self.chart_classifier.recommend(
            df=result_df,
            metric_col=intent.metric,
            dimension_col=intent.dimension
        )

        # 4. Check for Misleading Comparisons & Visual Biases
        alerts = self.misleading_detector.analyze(
            data=result_df,
            metric_col=intent.metric,
            dimension_col=intent.dimension,
            chart_type=chart.chart_type
        )

        return BIResponse(
            query=query,
            entities=entities,
            intent=intent,
            data=result_df,
            chart=chart,
            alerts=alerts,
            summary=summary
        )
