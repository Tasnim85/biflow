"""Orchestrator (simplified).

Responsibility: run the pipeline stages in order, pass each output to the
next stage, and write the audit log. It is the only module that knows all
the stages; the stages never import each other.
"""

from agents.etl_agent import calculate, load_tables
from agents.kpi_auditor_agent import explain
from agents.semantic_kpi_agent import get_latest_approved, load_definition
from utils.audit_logger import AuditLogger
from validation.kpi_validator import validate


def run_pipeline(kpi_name, version=None, scenario="correct"):
    """Run the full story: data -> definition -> calculation -> validation -> explanation.

    version=None means "use the latest approved version".
    A fresh audit logger is created for every run.
    """
    logger = AuditLogger()

    # 1. Data
    tables = load_tables()
    logger.log(
        "Data",
        "Dataset loaded",
        details={f"{name}_rows": len(df) for name, df in tables.items()},
    )

    # 2. KPI definition
    if version is None:
        definition = get_latest_approved(kpi_name)
    else:
        definition = load_definition(kpi_name, version)
    logger.log(
        "Semantic KPI Agent",
        f"KPI {definition['name']} v{definition['version']} loaded",
        details={
            "status": definition["status"],
            "owner": definition["owner"],
            "file": definition["source_file"],
        },
    )
    source_data = tables[definition["source_table"]]

    # 3. Calculation (calculate() loads the tables itself; fine for the MVP)
    logger.log("ETL Agent", "KPI calculation started")
    calc_result = calculate(definition, scenario)
    logger.log(
        "ETL Agent",
        "KPI calculation finished",
        details={
            "value": calc_result["value"],
            "rows_summed": calc_result["receipt"]["rows_summed"],
        },
    )

    # 4. Validation
    validation = validate(definition, calc_result, source_data)
    for check in validation["checks"]:
        logger.log(
            "Validator",
            f"{check['label']} executed",
            status=check["status"],
            details={"message": check["message"]},
        )
    logger.log(
        "Validator",
        "Validation finished",
        status=validation["status"],
        details={"failed_checks": ", ".join(validation["failed_checks"]) or "none"},
    )

    # 5. Explanation
    explanation = explain(definition, validation)
    logger.log(
        "Auditor",
        "Explanation generated",
        details={"main_issue": explanation["main_issue"]},
    )

    return {
        "definition": definition,
        "calc_result": calc_result,
        "source_data": source_data,
        "validation": validation,
        "explanation": explanation,
        "logger": logger,
    }