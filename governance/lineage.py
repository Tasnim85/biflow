"""Versioned column dependencies recorded from an actual cleaning/KPI run."""
from datetime import datetime, timezone
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

import pandas as pd

from data.data_generator import FEATURES
from governance.playbooks import clean_dataset, load_policy

STORE = Path(__file__).resolve().parents[1] / "output" / "lineage" / "runs.sqlite3"


def build_lineage(source):
    cleaned = clean_dataset(source, load_policy("1.2.0"))
    excluded = set(cleaned.review_positions)
    valid_positions = [i for i in range(len(source)) if i not in excluded]
    valid = cleaned.data.iloc[valid_positions][FEATURES].apply(pd.to_numeric)
    run_id = str(uuid4())
    nodes, edges = [], []

    def node(id, kind, label, **attributes):
        nodes.append(dict(id=id, kind=kind, label=label, **attributes))

    def edge(start, end, relation):
        edges.append(dict(source=start, target=end, relation=relation, run_id=run_id, version="1.0.0"))

    node("source", "dataset", "Clients bruts", fingerprint=cleaned.manifest["input_sha256"], rows=len(source))
    node("cleaned", "dataset", "Clients nettoyés", fingerprint=cleaned.manifest["output_sha256"], rows=len(source))
    for col in FEATURES:
        node("src:" + col, "column", "Source · " + col)
        node("rule:" + col, "transformation", "Nettoyage · " + col, policy_version="1.2.0",
             rule_id=col + "-numeric", changes=int(((cleaned.events.column == col) & (cleaned.events.action == "change")).sum()),
             exceptions=int(((cleaned.events.column == col) & (cleaned.events.action == "review")).sum()))
        node("out:" + col, "column", "Nettoyé · " + col)
        edge("source", "src:" + col, "contains")
        edge("src:" + col, "rule:" + col, "input")
        edge("rule:" + col, "out:" + col, "produces")
        edge("out:" + col, "cleaned", "belongs_to")
    node("filter", "transformation", "Filtre qualité · 5 colonnes", excluded=len(cleaned.review_positions),
         included=len(valid), formula="Exclude a row if any of the five numeric fields has an unresolved cleaning exception")
    for col in FEATURES:
        edge("out:" + col, "filter", "eligibility_dependency")
    definitions = [("amount_sum", "Somme des montants", "transaction_amount", "sum"),
                   ("income_mean", "Revenu moyen", "income", "mean"),
                   ("transaction_sum", "Total des transactions", "num_transactions", "sum")]
    for key, label, col, op in definitions:
        node("eligible:" + col, "column", "Éligible · " + col)
        edge("out:" + col, "eligible:" + col, "value_dependency")
        edge("filter", "eligible:" + col, "row_selection")
        value = float(getattr(valid[col], op)()) if len(valid) else None
        node("kpi:" + key, "kpi", label, value=value, formula=f"{op}({col}) on eligible rows",
             semantic_version="1.0.0", contributing_rows=len(valid))
        edge("eligible:" + col, "kpi:" + key, "aggregation")
    return {"run_id": run_id, "created_at": datetime.now(timezone.utc).isoformat(), "schema_version": "1.0.0",
            "nodes": nodes, "edges": edges, "cleaning_manifest": cleaned.manifest,
            "scope": "Actual demo cleaning, complete-case filtering and three KPI calculations; no invented joins or PII lineage"}


def ancestors(graph, target):
    ids = {n["id"] for n in graph["nodes"]}
    if target not in ids:
        raise ValueError("Unknown lineage node")
    found, pending = {target}, [target]
    while pending:
        current = pending.pop()
        for edge in graph["edges"]:
            if edge["target"] == current and edge["source"] not in found:
                found.add(edge["source"])
                pending.append(edge["source"])
    return {**graph, "nodes": [n for n in graph["nodes"] if n["id"] in found],
            "edges": [e for e in graph["edges"] if e["source"] in found and e["target"] in found]}


def graph_dot(graph):
    lines = ['digraph lineage { rankdir=LR; node [shape=box, style="rounded,filled", fillcolor="#e4f2f4"];']
    for n in graph["nodes"]:
        lines.append(f'{json.dumps(n["id"])} [label={json.dumps(n["label"], ensure_ascii=False)}];')
    for e in graph["edges"]:
        lines.append(f'{json.dumps(e["source"])} -> {json.dumps(e["target"])};')
    return "\n".join(lines + ["}"])


def save_run(graph, path=STORE):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(path)) as db, db:
        db.execute("CREATE TABLE IF NOT EXISTS runs (id TEXT PRIMARY KEY, created_at TEXT, payload TEXT)")
        db.execute("INSERT INTO runs VALUES (?, ?, ?)", (graph["run_id"], graph["created_at"], json.dumps(graph)))


def load_runs(path=STORE):
    if not Path(path).exists():
        return []
    with closing(sqlite3.connect(path)) as db:
        return [json.loads(row[0]) for row in db.execute("SELECT payload FROM runs ORDER BY created_at DESC")]
