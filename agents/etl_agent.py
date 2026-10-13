"""ETL / Data Engineering Agent (simplified).

Responsibility: calculate a KPI from the raw tables and describe exactly
what was done (the "receipt"), so that the validator can check it.
"""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).parent.parent / "data"

SCENARIOS = ["correct", "faulty"]


def load_tables():
    """Load the raw tables as a dictionary of dataframes."""
    return {
        "orders": pd.read_csv(DATA_DIR / "orders.csv"),
        "order_items": pd.read_csv(DATA_DIR / "order_items.csv"),
    }


def calculate(definition, scenario="correct"):
    """Calculate the KPI described by `definition`.

    scenario="correct": sum the column directly on the source table.
    scenario="faulty":  join the source table with order_items first,
                        then sum (this duplicates rows).
    """
    if scenario not in SCENARIOS:
        raise ValueError(f"Unknown scenario '{scenario}'. Use one of {SCENARIOS}.")

    # The MVP only supports simple SUM(column) KPIs without filters.
    if definition["filters"]:
        raise NotImplementedError("Filters are not supported in the MVP.")
    if not definition["formula"].upper().startswith("SUM("):
        raise NotImplementedError("Only SUM(...) formulas are supported in the MVP.")

    tables = load_tables()
    source_table = definition["source_table"]
    column = definition["source_columns"][0]
    grain_key = definition["grain_key"]
    base = tables[source_table]

    if scenario == "correct":
        data = base.copy()
        tables_used = [source_table]
        join = None
    else:
        data = base.merge(tables["order_items"], on=grain_key)
        tables_used = [source_table, "order_items"]
        join = {
            "left_table": source_table,
            "right_table": "order_items",
            "on": grain_key,
            "type": "inner",
            "rows_before": len(base),
            "rows_after": len(data),
        }

    value = data[column].sum().item()

    receipt = {
        "kpi_name": definition["name"],
        "kpi_version": definition["version"],
        "tables_used": tables_used,
        "join": join,
        "columns_summed": [column],
        "filters_applied": [],
        "rows_summed": len(data),
    }

    return {
        "scenario": scenario,
        "value": value,
        "receipt": receipt,
        "data": data,
    }