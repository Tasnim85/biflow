from pathlib import Path

import pandas as pd

# Build the path relative to this file, so it works from any folder
DATA_DIR = Path(__file__).parent / "data"

orders = pd.read_csv(DATA_DIR / "orders.csv")
order_items = pd.read_csv(DATA_DIR / "order_items.csv")

print("=== orders ===")
print(orders)
print()
print("=== order_items ===")
print(order_items)
print()

print("Rows in orders:", len(orders))
print("Rows in order_items:", len(order_items))
print("Is order_id unique in orders?", orders["order_id"].is_unique)
print("Is order_id unique in order_items?", order_items["order_id"].is_unique)
print()

print("Correct Revenue:", orders["order_total"].sum())
print()

# The faulty approach: join first, then sum
joined = orders.merge(order_items, on="order_id")
print("=== after join ===")
print(joined)
print("Rows after join:", len(joined))
print("Faulty Revenue:", joined["order_total"].sum())