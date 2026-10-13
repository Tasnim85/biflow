from utils.audit_logger import AuditLogger

logger = AuditLogger()

logger.log("Data", "Dataset loaded", details={"orders_rows": 3, "order_items_rows": 5})
logger.log("Semantic KPI Agent", "KPI Revenue v2.0 loaded", details={"owner": "Finance"})
logger.log("ETL Agent", "KPI calculation started")
logger.log("ETL Agent", "KPI calculation finished", details={"value": 700})
logger.log("Validator", "Grain check executed", status="FAIL")
logger.log("Validator", "Reference value check executed", status="FAIL")
logger.log("Validator", "Validation finished", status="FAIL")

print("Entries:", len(logger))
print()

for line in logger.as_lines():
    print(line)
print()

print(logger.as_dataframe()[["stage", "event", "status"]])
print()

print("Details of entry 0:", logger.entries[0]["details"])

# The log is append-only: clearing the returned copy must not change it
logger.entries.clear()
print("Entries after trying to clear the copy:", len(logger))