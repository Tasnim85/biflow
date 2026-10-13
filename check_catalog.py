from pprint import pprint

from agents.semantic_kpi_agent import (
    get_latest_approved,
    list_versions,
    load_definition,
)

print("Available versions:", list_versions("Revenue"))
print()

definition = load_definition("Revenue", "2.0")
print("=== Revenue v2.0 ===")
pprint(definition, sort_dicts=False)
print()

latest = get_latest_approved("Revenue")
print("Latest approved version:", latest["version"], "| owner:", latest["owner"])
print()

old = load_definition("Revenue", "1.0")
print("Revenue v1.0 status:", old["status"], "| owner:", old["owner"])
print()

# A version that does not exist should produce a clear error
try:
    load_definition("Revenue", "9.9")
except ValueError as error:
    print("Expected error:", error)