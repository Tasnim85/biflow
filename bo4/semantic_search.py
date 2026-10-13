"""Natural Language Semantic Search & Query Execution Engine for BO4.

Parses natural language queries in French or English, resolves business terminology
via the Business Glossary, and executes safe aggregation queries on tabular data.
"""
from __future__ import annotations
import re
from typing import Any
import pandas as pd
from bo4.glossary import BusinessGlossaryNER, normalize_text

class QueryIntent:
    def __init__(self, raw_query: str, metric: str, dimension: str | None, aggregation: str, limit: int | None, sort_desc: bool, filters: dict[str, Any]):
        self.raw_query = raw_query
        self.metric = metric
        self.dimension = dimension
        self.aggregation = aggregation  # 'sum', 'mean', 'count', 'min', 'max'
        self.limit = limit
        self.sort_desc = sort_desc
        self.filters = filters

    def to_dict(self) -> dict:
        return {
            "metric": self.metric,
            "dimension": self.dimension,
            "aggregation": self.aggregation,
            "limit": self.limit,
            "sort_desc": self.sort_desc,
            "filters": self.filters
        }

class SemanticSearchEngine:
    """Understands natural language questions and executes analytic queries."""

    def __init__(self, ner: BusinessGlossaryNER | None = None):
        self.ner = ner or BusinessGlossaryNER()

    def parse(self, query: str, df: pd.DataFrame) -> QueryIntent:
        columns = list(df.columns)
        entities = self.ner.extract_entities(query, available_columns=columns)

        # 1. Metric extraction
        def find_matching_col(target: str, cols: list[str]) -> str | None:
            if target in cols: return target
            for c in cols:
                if c.endswith(f"__{target}") or c.endswith(f"_{target}") or target in c:
                    return c
            return None

        metric_col = None
        for e in entities:
            if e.kind == "metric":
                matched = find_matching_col(e.canonical, columns)
                if matched:
                    metric_col = matched
                    break

        if not metric_col:
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            preferred = [c for c in ['total_amount', 'amount', 'price', 'quantity', 'salary', 'age'] if find_matching_col(c, columns)]
            metric_col = find_matching_col(preferred[0], columns) if preferred else (numeric_cols[0] if numeric_cols else columns[0])

        # 2. Dimension extraction
        dimension_col = None
        for e in entities:
            if e.kind in ["dimension", "temporal"] and e.canonical != metric_col:
                matched = find_matching_col(e.canonical, columns)
                if matched and matched != metric_col:
                    dimension_col = matched
                    break

        if not dimension_col:
            norm_q = normalize_text(query)
            match_par = re.search(r'\b(?:par|selon|by|pour chaque)\s+([a-z0-9_]+)\b', norm_q)
            if match_par:
                term = match_par.group(1)
                for col in columns:
                    if normalize_text(col) == term or term in normalize_text(col):
                        dimension_col = col
                        break

        # 3. Aggregation function extraction
        agg_candidates = [e.canonical for e in entities if e.kind == "aggregation"]
        if agg_candidates:
            agg_func = agg_candidates[0]
            agg = "mean" if agg_func == "avg" else agg_func
        else:
            if any(w in metric_col.lower() for w in ['amount', 'price', 'quantity', 'revenue', 'sales', 'chiffre']):
                agg = "sum"
            elif any(w in metric_col.lower() for w in ['age', 'score', 'rate', 'salary']):
                agg = "mean"
            else:
                agg = "count"

        # 4. Limit (Top N / Bottom N)
        limit = None
        match_top = re.search(r'\b(?:top|premiers|meilleurs|plus grands)\s+(\d+)\b', normalize_text(query))
        if match_top:
            limit = int(match_top.group(1))

        # 5. Sort direction
        sort_desc = True
        if any(w in normalize_text(query) for w in ['pire', 'moins', 'plus petit', 'plus bas', 'croissant', 'bottom', 'lowest']):
            sort_desc = False

        # 6. Basic value filters
        filters: dict[str, Any] = {}
        for col in columns:
            if df[col].dtype == 'object' or pd.api.types.is_string_dtype(df[col]):
                uniques = df[col].dropna().unique()[:30]
                for u in uniques:
                    val_str = str(u).strip()
                    if len(val_str) >= 3 and normalize_text(val_str) in normalize_text(query):
                        filters[col] = u
                        break

        return QueryIntent(
            raw_query=query,
            metric=metric_col,
            dimension=dimension_col,
            aggregation=agg,
            limit=limit,
            sort_desc=sort_desc,
            filters=filters
        )

    def execute(self, query: str, df: pd.DataFrame) -> tuple[pd.DataFrame, QueryIntent, str]:
        """Parses query, filters and aggregates dataframe, returns result df and natural language summary."""
        intent = self.parse(query, df)
        filtered_df = df.copy()

        # Coerce metric to numeric safely
        if intent.metric in filtered_df.columns:
            if not pd.api.types.is_numeric_dtype(filtered_df[intent.metric]):
                filtered_df[intent.metric] = pd.to_numeric(
                    filtered_df[intent.metric].astype(str).str.replace(r'[$€,\s]', '', regex=True),
                    errors='coerce'
                ).fillna(0)

        # Apply detected filters
        for col, val in intent.filters.items():
            filtered_df = filtered_df[filtered_df[col] == val]

        if filtered_df.empty:
            summary = "Aucun résultat trouvé pour les filtres spécifiés."
            return pd.DataFrame(), intent, summary

        # Aggregation execution
        if intent.dimension and intent.dimension in filtered_df.columns:
            if pd.api.types.is_datetime64_any_dtype(filtered_df[intent.dimension]) or 'date' in intent.dimension.lower():
                try:
                    dates = pd.to_datetime(filtered_df[intent.dimension], errors='coerce')
                    filtered_df['_period'] = dates.dt.strftime('%Y-%m')
                    dim_col = '_period'
                except Exception:
                    dim_col = intent.dimension
            else:
                dim_col = intent.dimension

            grouped = filtered_df.groupby(dim_col, as_index=False).agg(
                result_metric=(intent.metric, intent.aggregation),
                record_count=(intent.metric, 'count')
            )
            grouped = grouped.rename(columns={'result_metric': intent.metric, 'record_count': 'transaction_count'})
            grouped = grouped.sort_values(by=intent.metric, ascending=not intent.sort_desc)

            if intent.limit:
                grouped = grouped.head(intent.limit)

            total_val = grouped[intent.metric].sum()
            best_row = grouped.iloc[0]
            val_fmt = f"{float(best_row[intent.metric]):,.2f}" if isinstance(best_row[intent.metric], (int, float)) else str(best_row[intent.metric])
            tot_fmt = f"{float(total_val):,.2f}" if isinstance(total_val, (int, float)) else str(total_val)
            summary = (
                f"Pour la métrique '{intent.metric}' agrégée par '{intent.dimension}' : "
                f"le maximum est atteint par '{best_row[dim_col]}' avec {val_fmt}. "
                f"Le total cumulé sur l'ensemble est de {tot_fmt}."
            )
            return grouped, intent, summary

        else:
            # Scalar metric calculation
            if intent.aggregation == 'sum':
                val = filtered_df[intent.metric].sum()
            elif intent.aggregation == 'mean':
                val = filtered_df[intent.metric].mean()
            elif intent.aggregation == 'count':
                val = filtered_df[intent.metric].count()
            elif intent.aggregation == 'max':
                val = filtered_df[intent.metric].max()
            else:
                val = filtered_df[intent.metric].min()

            res_df = pd.DataFrame([{intent.metric: val, "count": len(filtered_df)}])
            val_fmt = f"{float(val):,.2f}" if isinstance(val, (int, float)) else str(val)
            summary = f"Le résultat global pour '{intent.metric}' ({intent.aggregation}) est de {val_fmt}."
            return res_df, intent, summary
