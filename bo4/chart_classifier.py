"""Automatic Chart Type Classification and Optimal Visualization Builder for BO4.

Recommends and builds the most suitable Plotly chart based on:
- Dimension data type (temporal, categorical, continuous).
- Cardinality of categories (few vs many).
- Intent of the query (distribution, trend, comparison, composition).
- Best practices in data visualization to avoid misleading representations.
"""
from __future__ import annotations
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

class ChartRecommendation:
    def __init__(self, chart_type: str, title: str, rationale: str, figure: go.Figure | None = None):
        self.chart_type = chart_type   # 'kpi_card', 'line', 'bar', 'horizontal_bar', 'donut', 'scatter', 'table'
        self.title = title
        self.rationale = rationale
        self.figure = figure

    def to_dict(self) -> dict:
        return {
            "chart_type": self.chart_type,
            "title": self.title,
            "rationale": self.rationale
        }

class ChartClassifier:
    """Classifies dataset columns and builds the optimal Plotly chart."""

    def recommend(self, df: pd.DataFrame, metric_col: str, dimension_col: str | None = None, query_intent: str = "comparison") -> ChartRecommendation:
        if df.empty or metric_col not in df.columns:
            # Fallback KPI card or empty
            return ChartRecommendation("kpi_card", "Aucune donnée", "Jeu de données vide.")

        # Palette de couleurs professionnelle
        PALETTE = ["#1E3A8A", "#0D9488", "#3B82F6", "#F59E0B", "#8B5CF6", "#EC4899", "#10B981"]

        # Case 1: No dimension -> Single Metric Card
        if not dimension_col or dimension_col not in df.columns:
            val = df[metric_col].sum() if pd.api.types.is_numeric_dtype(df[metric_col]) else len(df)
            fig = go.Figure()
            fig.add_trace(go.Indicator(
                mode="number",
                value=val,
                title={"text": f"<b>{metric_col.replace('_', ' ').title()}</b>", "font": {"size": 20, "color": "#1E3A8A"}},
                number={"font": {"size": 48, "color": "#0D9488"}, "valueformat": ",.2f"}
            ))
            fig.update_layout(height=260, margin=dict(l=20, r=20, t=40, b=20), paper_bgcolor="white")
            return ChartRecommendation(
                chart_type="kpi_card",
                title="Indicateur Clé Unique (KPI Metric)",
                rationale="Une seule valeur scalaire globale demandée sans axe de décomposition.",
                figure=fig
            )

        cardinality = df[dimension_col].nunique()
        is_temporal = (
            pd.api.types.is_datetime64_any_dtype(df[dimension_col]) or
            any(w in dimension_col.lower() for w in ["date", "month", "mois", "year", "annee", "jour", "time"])
        )

        # Case 2: Temporal Evolution -> Line Chart
        if is_temporal or query_intent == "trend":
            df_sorted = df.sort_values(by=dimension_col)
            fig = px.line(
                df_sorted,
                x=dimension_col,
                y=metric_col,
                markers=True,
                title=f"Évolution de {metric_col.replace('_', ' ').title()} par {dimension_col.replace('_', ' ').title()}",
                color_discrete_sequence=["#1E3A8A"]
            )
            fig.update_traces(line=dict(width=3), marker=dict(size=8))
            fig.update_layout(
                xaxis_title=dimension_col.replace('_', ' ').title(),
                yaxis_title=metric_col.replace('_', ' ').title(),
                hovermode="x unified",
                template="plotly_white",
                height=420
            )
            return ChartRecommendation(
                chart_type="line",
                title="Graphique Linéaire d'Évolution (Line Chart)",
                rationale="La dimension est temporelle. La courbe continue permet de visualiser les tendances, pics et creux sans rupture.",
                figure=fig
            )

        # Case 3: Composition / Part of Whole with few categories (<= 5)
        if cardinality <= 5 and query_intent in ["composition", "part", "repartition"]:
            fig = px.pie(
                df,
                names=dimension_col,
                values=metric_col,
                hole=0.45,
                title=f"Répartition de {metric_col.replace('_', ' ').title()} par {dimension_col.replace('_', ' ').title()}",
                color_discrete_sequence=PALETTE
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(template="plotly_white", height=420)
            return ChartRecommendation(
                chart_type="donut",
                title="Graphique en Anneau (Donut Chart)",
                rationale="Faible nombre de catégories (<= 5) et objectif de composition (part du tout).",
                figure=fig
            )

        # Case 4: Medium/High Cardinality (> 7) -> Horizontal Bar Chart (Meilleure lisibilité des labels)
        if cardinality > 7:
            df_sorted = df.sort_values(by=metric_col, ascending=True).tail(20)  # Top 20 for readability
            fig = px.bar(
                df_sorted,
                x=metric_col,
                y=dimension_col,
                orientation='h',
                title=f"Classement de {metric_col.replace('_', ' ').title()} par {dimension_col.replace('_', ' ').title()}",
                color=metric_col,
                color_continuous_scale="Tealgrn"
            )
            fig.update_layout(
                xaxis=dict(rangemode="tozero"),
                yaxis_title=dimension_col.replace('_', ' ').title(),
                xaxis_title=metric_col.replace('_', ' ').title(),
                template="plotly_white",
                height=max(400, cardinality * 25)
            )
            return ChartRecommendation(
                chart_type="horizontal_bar",
                title="Barres Horizontales Classées (Horizontal Bar Chart)",
                rationale="Plus de 7 catégories : l'orientation horizontale permet de lire facilement les étiquettes sans encombrement.",
                figure=fig
            )

        # Case 5: Standard Low Cardinality (2 to 7 categories) -> Vertical Bar Chart
        df_sorted = df.sort_values(by=metric_col, ascending=False)
        fig = px.bar(
            df_sorted,
            x=dimension_col,
            y=metric_col,
            title=f"Comparaison de {metric_col.replace('_', ' ').title()} par {dimension_col.replace('_', ' ').title()}",
            color_discrete_sequence=["#1D4ED8"]
        )
        # Règle anti-tronquage : démarrer l'axe Y à 0 impérativement
        fig.update_layout(
            yaxis=dict(rangemode="tozero"),
            xaxis_title=dimension_col.replace('_', ' ').title(),
            yaxis_title=metric_col.replace('_', ' ').title(),
            template="plotly_white",
            height=420
        )
        return ChartRecommendation(
            chart_type="bar",
            title="Histogramme Vertical (Standard Column Bar Chart)",
            rationale="Comparaison directe entre un petit nombre de catégories distinctes avec axe commençant à 0.",
            figure=fig
        )
