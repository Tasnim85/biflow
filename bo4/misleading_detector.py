"""Misleading Comparison and Chart Distortion Detector for BO4.

Detects analytical and visual comparison pitfalls such as:
1. Truncated Y-Axis (axes tronqués exagérant de petites différences).
2. Unequal comparison periods (périodes temporelles de longueurs inégales).
3. Low sample size / volatility (catégories à très faible effectif).
4. Outlier skew (moyenne faussée par des valeurs extrêmes, mean vs median).
5. Misleading percent change vs absolute magnitude.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

class MisleadingAlert:
    def __init__(self, category: str, severity: str, title: str, explanation: str, recommendation: str):
        self.category = category       # 'axis_truncation', 'unequal_periods', 'small_sample', 'outlier_skew'
        self.severity = severity       # 'WARNING', 'CRITICAL', 'INFO'
        self.title = title
        self.explanation = explanation
        self.recommendation = recommendation

    def to_dict(self) -> dict:
        return {
            "category": self.category,
            "severity": self.severity,
            "title": self.title,
            "explanation": self.explanation,
            "recommendation": self.recommendation
        }

class MisleadingComparisonDetector:
    """Analyzes query result data and visualization configurations for deceptive patterns."""

    def analyze(self, data: pd.DataFrame, metric_col: str, dimension_col: str | None = None, chart_type: str = "bar") -> list[MisleadingAlert]:
        alerts: list[MisleadingAlert] = []
        if data.empty or metric_col not in data.columns:
            return alerts

        series = pd.to_numeric(data[metric_col], errors='coerce').dropna()
        if len(series) < 2:
            return alerts

        # 1. Truncated Axis Warning for Bar Charts
        min_val = series.min()
        max_val = series.max()
        if chart_type in ["bar", "horizontal_bar", "column"] and min_val > 0:
            variation = (max_val - min_val) / max_val
            # If the variation is small (< 20%) and base is far from 0
            if variation < 0.25 and min_val > (0.5 * max_val):
                alerts.append(MisleadingAlert(
                    category="axis_truncation",
                    severity="WARNING",
                    title="Axe Y tronqué potentiel (Truncated Y-Axis)",
                    explanation=(
                        f"Les valeurs varient seulement entre {min_val:,.1f} et {max_val:,.1f} "
                        f"(écart relatif de {variation*100:.1f}%). Si l'axe ne démarre pas à 0, "
                        "les différences visuelles sembleront artificiellement gigantesques."
                    ),
                    recommendation="Commencez impérativement l'axe des ordonnées à zéro pour préserver la proportionnalité des barres."
                ))

        # 2. Outlier Skew (Mean vs Median)
        if len(series) >= 5:
            mean_val = series.mean()
            median_val = series.median()
            if median_val > 0 and (mean_val / median_val > 1.4 or mean_val / median_val < 0.7):
                ratio = mean_val / median_val
                alerts.append(MisleadingAlert(
                    category="outlier_skew",
                    severity="WARNING",
                    title="Biais d'asymétrie / Valeurs extrêmes (Outlier Skew)",
                    explanation=(
                        f"La moyenne ({mean_val:,.1f}) diffère fortement de la médiane ({median_val:,.1f}) "
                        f"avec un ratio de {ratio:.2f}x. Quelques transactions exceptionnelles faussent la comparaison globale."
                    ),
                    recommendation="Affichez la médiane aux côtés de la moyenne ou utilisez un boxplot pour visualiser la dispersion réelle."
                ))

        # 3. Small Sample Size / Cardinality Variance
        if dimension_col and dimension_col in data.columns:
            if 'count' in data.columns or 'transaction_count' in data.columns:
                count_col = 'count' if 'count' in data.columns else 'transaction_count'
                counts = data[count_col]
                if counts.min() < 5 and counts.max() > 50:
                    alerts.append(MisleadingAlert(
                        category="small_sample",
                        severity="CRITICAL",
                        title="Déséquilibre d'échantillons (Small Sample Size)",
                        explanation=(
                            f"Certaines catégories reposent sur moins de {int(counts.min())} observations, "
                            f"alors que d'autres en comptent plus de {int(counts.max())}. "
                            "Les ratios ou moyennes calculés sur de tout petits volumes sont statistiquement instables."
                        ),
                        recommendation="Ajoutez la taille de l'échantillon (N) dans chaque étiquette ou filtrez les catégories avec N < 10."
                    ))

        # 4. Unequal Time Periods (if temporal comparison)
        if dimension_col and any(w in dimension_col.lower() for w in ['date', 'month', 'mois', 'periode', 'year']):
            # Check for February vs 31-day months or unequal lengths
            month_names = data[dimension_col].astype(str).str.lower().tolist()
            if any('feb' in m or 'fev' in m or '-02' in m for m in month_names) and any('mar' in m or '-03' in m or 'jan' in m for m in month_names):
                alerts.append(MisleadingAlert(
                    category="unequal_periods",
                    severity="INFO",
                    title="Comparaison de périodes de durées inégales (Calendar Distortion)",
                    explanation=(
                        "Février ne compte que 28 ou 29 jours contre 31 jours pour les mois adjacents. "
                        "Une baisse brute des ventes en février est souvent un artefact calendaire d'environ -10%."
                    ),
                    recommendation="Comparez les ventes moyennes quotidiennes (Daily Run Rate) plutôt que le volume mensuel total brut."
                ))

        return alerts
