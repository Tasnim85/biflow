from pprint import pprint

from agents.etl_agent import calculate
from agents.semantic_kpi_agent import load_definition

definition = load_definition("Revenue", "2.0")

for scenario in ["correct", "faulty"]:
    result = calculate(definition, scenario)
    print(f"=== scenario: {scenario} ===")
    print("Revenue:", result["value"])
    print("Receipt:")
    pprint(result["receipt"], sort_dicts=False)
    print("Data that was summed:")
    print(result["data"])
    print()

# An unknown scenario should fail clearly
try:
    calculate(definition, "banana")
except ValueError as error:
    print("Expected error:", error)