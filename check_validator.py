from agents.etl_agent import calculate, load_tables
from agents.semantic_kpi_agent import load_definition
from validation.kpi_validator import validate

definition = load_definition("Revenue", "2.0")
source_data = load_tables()[definition["source_table"]]

for scenario in ["correct", "faulty"]:
    calc_result = calculate(definition, scenario)
    result = validate(definition, calc_result, source_data)

    print(f"=== scenario: {scenario} ===")
    print("Overall:", result["status"])
    print("Failed checks:", result["failed_checks"])
    print()
    for check in result["checks"]:
        print(f"[{check['status']}] {check['label']}: {check['message']}")
        for key, value in check["evidence"].items():
            print(f"      {key}: {value}")
        print()

# Validating a v2.0 receipt against the v1.0 definition must fail clearly
old_definition = load_definition("Revenue", "1.0")
try:
    validate(old_definition, calc_result, source_data)
except ValueError as error:
    print("Expected error:", error)