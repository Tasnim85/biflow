from agents.orchestrator import run_pipeline

for scenario in ["correct", "faulty"]:
    run = run_pipeline("Revenue", scenario=scenario)
    definition = run["definition"]
    record = run["explanation"]["log_entry"]

    print(f"=== {scenario} ===")
    print("KPI:", definition["name"], "v" + definition["version"])
    print("Reference:", record["reference"], "| Calculated:", record["calculated"])
    print("Status:", run["validation"]["status"])
    print()
    print("Audit log:")
    for line in run["logger"].as_lines():
        print(line)
    print()
    print("Log entries:", len(run["logger"]))
    print()

# Using the deprecated v1.0 definition: the explanation should mention its status
old = run_pipeline("Revenue", version="1.0", scenario="correct")
print("=== Revenue v1.0 (deprecated) ===")
print(old["explanation"]["narrative"].split("\n\n")[1])
print()

# A KPI that does not exist should fail clearly
try:
    run_pipeline("Margin")
except ValueError as error:
    print("Expected error:", error)