"""Explicit, idempotent import of retained SQLite executions into Neo4j."""
from governance.lineage import load_runs
from governance.neo4j_store import Neo4jStore


if __name__ == '__main__':
    runs = load_runs()
    with Neo4jStore() as store:
        store.initialize()
        for run in runs:
            store.save(run)
    print(f'{len(runs)} executions imported or already present; SQLite preserved.')
