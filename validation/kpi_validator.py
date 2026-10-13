"""Validation Engine (simplified).

Responsibility: compare what the ETL agent actually did (receipt + data)
with the approved KPI definition, using deterministic checks. Every check
returns PASS/FAIL plus the evidence behind the verdict.

The validator never reads files and never looks at the demo scenario label.
"""

import math


def _result(name, label, passed, message, evidence):
    """Build the standard result dictionary returned by every check."""
    return {
        "name": name,
        "label": label,
        "status": "PASS" if passed else "FAIL",
        "message": message,
        "evidence": evidence,
    }


def check_source(definition, calc_result):
    """Were the approved table, columns and filters used?"""
    receipt = calc_result["receipt"]
    expected_table = definition["source_table"]
    tables_used = receipt["tables_used"]
    columns_summed = receipt["columns_summed"]

    extra_tables = [t for t in tables_used if t != expected_table]
    unexpected_columns = [
        c for c in columns_summed if c not in definition["source_columns"]
    ]
    filters_match = receipt["filters_applied"] == definition["filters"]

    passed = (
        expected_table in tables_used and not unexpected_columns and filters_match
    )

    if passed:
        message = (
            f"Approved table and columns were used "
            f"({expected_table}: {', '.join(columns_summed)})"
        )
        if extra_tables:
            message += f". Note: additional table(s) also used: {', '.join(extra_tables)}"
    else:
        message = "The calculation does not use the approved table, columns or filters"

    evidence = {
        "expected_table": expected_table,
        "tables_used": tables_used,
        "extra_tables": extra_tables,
        "expected_columns": definition["source_columns"],
        "columns_summed": columns_summed,
        "unexpected_columns": unexpected_columns,
        "filters_match": filters_match,
    }
    return _result("source", "Source check", passed, message, evidence)


def check_grain(definition, calc_result):
    """Does the summed data have exactly one row per grain unit?"""
    data = calc_result["data"]
    grain_key = definition["grain_key"]

    if grain_key not in data.columns:
        return _result(
            "grain",
            "Aggregation grain check",
            False,
            f"The grain key '{grain_key}' is missing from the data that was summed",
            {"grain_key": grain_key, "columns_available": list(data.columns)},
        )

    rows = len(data)
    distinct_keys = int(data[grain_key].nunique())
    max_rows_per_key = int(data[grain_key].value_counts().max())
    passed = rows == distinct_keys

    if passed:
        message = (
            f"Data has one row per {grain_key} "
            f"({rows} rows, {distinct_keys} distinct {grain_key} values)"
        )
    else:
        message = (
            f"Data has {rows} rows for {distinct_keys} distinct {grain_key} values: "
            f"more than one row per {grain_key}"
        )

    evidence = {
        "expected_grain": f"1 row per {grain_key}",
        "actual_grain": (
            f"1 row per {grain_key}" if passed else f"multiple rows per {grain_key}"
        ),
        "rows": rows,
        "distinct_keys": distinct_keys,
        "max_rows_per_key": max_rows_per_key,
    }
    return _result("grain", "Aggregation grain check", passed, message, evidence)


def check_join_multiplicity(definition, calc_result):
    """Did a join multiply the rows, and which keys were repeated?"""
    receipt = calc_result["receipt"]
    join = receipt["join"]

    if join is None:
        return _result(
            "join_multiplicity",
            "Join multiplicity check",
            True,
            "No join was performed, so no join could multiply rows",
            {"join_performed": False},
        )

    data = calc_result["data"]
    grain_key = definition["grain_key"]
    column = receipt["columns_summed"][0]

    rows_before = join["rows_before"]
    rows_after = join["rows_after"]
    fan_out = rows_after > rows_before

    # Keys that appear more than once, e.g. {1: 2, 3: 2}
    counts = data[grain_key].value_counts()
    repeated = counts[counts > 1].sort_index()
    duplicated_keys = dict(zip(repeated.index.tolist(), repeated.tolist()))

    # Amount added by the repeated copies (every copy after the first)
    repeated_rows = data[data.duplicated(subset=[grain_key], keep="first")]
    extra_amount = repeated_rows[column].sum().item()

    description = f"{join['left_table']} -> {join['right_table']} on {join['on']}"
    if fan_out:
        message = (
            f"The join of {join['left_table']} with {join['right_table']} on "
            f"{join['on']} increased the row count from {rows_before} to {rows_after}"
        )
    else:
        message = (
            f"The join of {join['left_table']} with {join['right_table']} on "
            f"{join['on']} did not change the row count ({rows_before} rows)"
        )

    evidence = {
        "join_performed": True,
        "join": description,
        "rows_before": rows_before,
        "rows_after": rows_after,
        "extra_rows": rows_after - rows_before,
        "duplicated_keys": duplicated_keys,
        "extra_amount": extra_amount,
    }
    return _result(
        "join_multiplicity", "Join multiplicity check", not fan_out, message, evidence
    )


def check_reference(definition, calc_result, source_data):
    """Does the result equal a reference value computed independently?"""
    column = definition["source_columns"][0]
    reference = source_data[column].sum().item()
    calculated = calc_result["value"]
    difference = calculated - reference
    passed = math.isclose(calculated, reference, rel_tol=1e-9, abs_tol=1e-9)
    difference_pct = round(difference / reference * 100, 1) if reference else None

    if passed:
        message = f"Calculated value ({calculated}) matches the reference value ({reference})"
    else:
        message = (
            f"Calculated value ({calculated}) differs from the reference value "
            f"({reference}) by {difference:+}"
        )

    evidence = {
        "reference": reference,
        "calculated": calculated,
        "difference": difference,
        "difference_pct": difference_pct,
    }
    return _result("reference_value", "Reference value check", passed, message, evidence)


def validate(definition, calc_result, source_data):
    """Run all checks (always all of them) and return the combined result."""
    receipt = calc_result["receipt"]
    if (receipt["kpi_name"], receipt["kpi_version"]) != (
        definition["name"],
        definition["version"],
    ):
        raise ValueError(
            f"Receipt is for {receipt['kpi_name']} v{receipt['kpi_version']}, "
            f"but the definition passed is {definition['name']} v{definition['version']}."
        )

    checks = [
        check_source(definition, calc_result),
        check_grain(definition, calc_result),
        check_join_multiplicity(definition, calc_result),
        check_reference(definition, calc_result, source_data),
    ]
    failed_checks = [c["name"] for c in checks if c["status"] == "FAIL"]

    return {
        "kpi_name": definition["name"],
        "kpi_version": definition["version"],
        "status": "FAIL" if failed_checks else "PASS",
        "failed_checks": failed_checks,
        "checks": checks,
    }