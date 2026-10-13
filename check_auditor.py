from pprint import pprint

from agents.etl_agent import calculate, load_tables
from agents.kpi_auditor_agent import explain
from agents.semantic_kpi_agent import load_definition
from validation.kpi_validator import validate

definition = load_definition("Revenue", "2.0")
source_data = load_tables()[definition["source_table"]]


def run(scenario):
    calc_result = calculate(definition, scenario)
    return calc_result, validate(definition, calc_result, source_data)


# 1. Correct run
_, validation = run("correct")
print("=== correct ===")
print(explain(definition, validation)["narrative"])
print()

# 2. Faulty run
_, validation = run("faulty")
result = explain(definition, validation)
print("=== faulty ===")
print(result["narrative"])
print()
print("Audit record (without the long explanation):")
record = {k: v for k, v in result["log_entry"].items() if k != "explanation"}
pprint(record, sort_dicts=False)
print()

# 3. Only the reference value is wrong: tamper with the number, not the data
calc_result, _ = run("correct")
tampered = dict(calc_result)
tampered["value"] = 460
validation = validate(definition, tampered, source_data)
print("=== tampered value (only the reference check fails) ===")
print(explain(definition, validation)["narrative"])
print()

# 4. Same input must always give the same text
first = explain(definition, validation)["narrative"]
second = explain(definition, validation)["narrative"]
print("Deterministic:", first == second)