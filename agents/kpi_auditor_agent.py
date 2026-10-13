"""BI Auditor / XAI Agent (simplified).

Responsibility: turn validation evidence into a human-readable explanation
and a structured audit record.

Rule: every sentence is a template filled with values from the validation
evidence. The Auditor never invents causes, numbers or opinions.
"""

from datetime import datetime


def _format_repeated_keys(duplicated_keys):
    """{1: 2, 3: 2} -> '1 (2 rows), 3 (2 rows)'"""
    return ", ".join(f"{key} ({count} rows)" for key, count in duplicated_keys.items())


def _main_issue(failed):
    """Short label for the main problem, based only on which checks failed."""
    if not failed:
        return "none"

    issues = []
    if "source" in failed:
        issues.append("calculation does not use the approved source")
    if "grain" in failed and "join_multiplicity" in failed:
        issues.append("aggregation grain mismatch caused by join multiplicity")
    elif "grain" in failed:
        issues.append("aggregation grain mismatch")
    elif "join_multiplicity" in failed:
        issues.append("join multiplicity")
    if not issues:
        issues.append(
            "result differs from the reference value "
            "(cause not identified by the available checks)"
        )

    text = "; ".join(issues)
    return text[0].upper() + text[1:]


def explain(definition, validation):
    """Build the explanation and the audit record from a validation result."""
    checks = {check["name"]: check for check in validation["checks"]}
    failed = validation["failed_checks"]
    passed = validation["status"] == "PASS"

    name = definition["name"]
    version = definition["version"]
    key = definition["grain_key"]
    column = definition["source_columns"][0]
    source = f"{definition['source_table']}.{column}"
    reference = checks["reference_value"]["evidence"]

    headline = f"{name} calculation {'passed' if passed else 'failed'} validation."
    main_issue = _main_issue(failed)

    paragraphs = []

    # 1. The approved definition (always)
    text = (
        f"The approved definition ({name}, version {version}, owner: "
        f"{definition['owner']}) specifies `{definition['formula']}` at "
        f"{definition['aggregation_grain']} level, meaning one row per `{key}`."
    )
    if definition["status"] != "approved":
        text += f" Note: this version of the definition has status '{definition['status']}'."
    paragraphs.append(text)

    if passed:
        paragraphs.append(
            f"All {len(checks)} checks passed: the approved table and column "
            f"(`{source}`) were used, the data has one row per `{key}`, no join "
            f"multiplied rows, and the result ({reference['calculated']}) matches "
            f"the reference value ({reference['reference']})."
        )
    else:
        # 2. Cause: join multiplicity
        if "join_multiplicity" in failed:
            join = checks["join_multiplicity"]["evidence"]
            paragraphs.append(
                f"During processing, a join ({join['join']}) increased the row count "
                f"from {join['rows_before']} to {join['rows_after']}. The `{key}` values "
                f"that appear more than once are: "
                f"{_format_repeated_keys(join['duplicated_keys'])}. Their `{column}` "
                f"values were counted once per row, adding {join['extra_amount']} to the total."
            )

        # 3. Consequence: grain
        if "grain" in failed:
            grain = checks["grain"]["evidence"]
            text = (
                f"The data used in the calculation had {grain['rows']} rows for "
                f"{grain['distinct_keys']} distinct `{key}` values, so the approved "
                f"grain (one row per `{key}`) was not respected."
            )
            if "join_multiplicity" not in failed:
                text += " No join multiplication was detected, so the origin of the extra rows is not identified by the available checks."
            paragraphs.append(text)

        # 4. Source problem
        if "source" in failed:
            src = checks["source"]["evidence"]
            paragraphs.append(
                f"The calculation used tables {src['tables_used']} and columns "
                f"{src['columns_summed']}, which do not match the approved source "
                f"`{source}` and filters."
            )

        # 5. Result vs reference
        if "reference_value" in failed:
            pct = reference["difference_pct"]
            pct_text = f", {pct:+}%" if pct is not None else ""
            paragraphs.append(
                f"The calculated {name} was {reference['calculated']}, while the "
                f"reference value is {reference['reference']} "
                f"(difference: {reference['difference']:+}{pct_text})."
            )

        # 6. Honesty: only the reference check failed
        if set(failed) == {"reference_value"}:
            paragraphs.append(
                "No structural cause was detected by the available checks "
                "(source, grain, join multiplicity)."
            )

        # 7. Ruled-out cause
        if "source" not in failed:
            paragraphs.append(
                f"The approved table and column (`{source}`) were used, so a "
                f"wrong-column error is ruled out."
            )

    verdict = "PASSED" if passed else "FAILED"
    closing = f"**Validation result: {verdict}.**"
    if not passed:
        closing += f" Main issue: {main_issue}."

    narrative = "\n\n".join([f"**{headline}**"] + paragraphs + [closing])

    log_entry = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "kpi": name,
        "version": version,
        "owner": definition["owner"],
        "status": validation["status"],
        "failed_checks": ", ".join(failed) if failed else "none",
        "reference": reference["reference"],
        "calculated": reference["calculated"],
        "main_issue": main_issue,
        "checks": {name_: check["status"] for name_, check in checks.items()},
        "explanation": narrative,
    }

    return {
        "headline": headline,
        "main_issue": main_issue,
        "narrative": narrative,
        "log_entry": log_entry,
        "validation": validation,
    }