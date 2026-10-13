"""Native Neo4j graph storage. No silent SQLite fallback."""
import json
import os
from pathlib import Path
from neo4j import GraphDatabase


def configuration():
    settings = {}
    path = Path(__file__).resolve().parents[1] / '.env'
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.lstrip().startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                settings[key.strip()] = value.strip()
    for key in ['NEO4J_URI', 'NEO4J_USER', 'NEO4J_PASSWORD', 'NEO4J_DATABASE']:
        if key in os.environ:
            settings[key] = os.environ[key]
    if not settings.get('NEO4J_PASSWORD'):
        raise ValueError('NEO4J_PASSWORD absent : configurer le fichier .env local.')
    return settings


class Neo4jStore:
    def __init__(self):
        config = configuration()
        self.database = config.get('NEO4J_DATABASE', 'neo4j')
        self.driver = GraphDatabase.driver(config.get('NEO4J_URI', 'bolt://127.0.0.1:7687'),
                    auth=(config.get('NEO4J_USER', 'neo4j'), config['NEO4J_PASSWORD']),
                    connection_timeout=5, connection_acquisition_timeout=10, max_transaction_retry_time=5)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.driver.close()

    def initialize(self):
        self.driver.verify_connectivity()
        for query in [
            'CREATE CONSTRAINT biflow_run_id IF NOT EXISTS FOR (r:BIFlowRun) REQUIRE r.id IS UNIQUE',
            'CREATE CONSTRAINT biflow_node_key IF NOT EXISTS FOR (n:BIFlowNode) REQUIRE n.key IS UNIQUE',
        ]:
            self.driver.execute_query(query, database_=self.database)

    def save(self, graph):
        ids = [n['id'] for n in graph['nodes']]
        if len(set(ids)) != len(ids) or any(e['source'] not in ids or e['target'] not in ids for e in graph['edges']):
            raise ValueError('Invalid lineage graph')
        nodes = [dict(n, key=graph['run_id'] + '/' + n['id'], run_id=graph['run_id'], order=i)
                 for i, n in enumerate(graph['nodes'])]
        metadata = {k: v for k, v in graph.items() if k not in {'nodes', 'edges'}}

        def write(tx):
            # Identical retries/migration are safe; conflicting snapshots are rejected.
            serialized = json.dumps(graph, sort_keys=True)
            existing = tx.run('MATCH (r:BIFlowRun {id:$id}) RETURN r.snapshot AS snapshot', id=graph['run_id']).single()
            if existing:
                if existing['snapshot'] != serialized:
                    raise ValueError('Execution already exists with different content')
                return
            tx.run('CREATE (r:BIFlowRun {id:$id, created_at:$created, metadata:$metadata, snapshot:$snapshot})',
                   id=graph['run_id'], created=graph['created_at'], metadata=json.dumps(metadata), snapshot=serialized).consume()
            tx.run('UNWIND $nodes AS props CREATE (n:BIFlowNode) SET n = props '
                   'WITH n MATCH (r:BIFlowRun {id:$run}) CREATE (r)-[:HAS_NODE]->(n)',
                   nodes=nodes, run=graph['run_id']).consume()
            tx.run('UNWIND $edges AS item MATCH (a:BIFlowNode {key:$run + "/" + item.source}), '
                   '(b:BIFlowNode {key:$run + "/" + item.target}) '
                   'CREATE (a)-[e:FLOWS_TO]->(b) SET e = item',
                   edges=graph['edges'], run=graph['run_id']).consume()
        with self.driver.session(database=self.database) as session:
            session.execute_write(write)

    def runs(self):
        records, _, _ = self.driver.execute_query('MATCH (r:BIFlowRun) RETURN r.snapshot AS snapshot ORDER BY r.created_at DESC', database_=self.database)
        return [json.loads(r['snapshot']) for r in records]

    def upstream(self, run_id, target):
        # Real graph traversal in Neo4j, scoped to the selected run.
        records, _, _ = self.driver.execute_query(
            'MATCH (t:BIFlowNode {key:$key}) MATCH (n:BIFlowNode)-[:FLOWS_TO*0..]->(t) '
            'WHERE n.run_id=$run RETURN DISTINCT n.id AS id',
            key=run_id + '/' + target, run=run_id, database_=self.database)
        if not records:
            raise ValueError('Unknown node or execution')
        ids = [r['id'] for r in records]
        nodes, _, _ = self.driver.execute_query(
            'MATCH (n:BIFlowNode) WHERE n.run_id=$run AND n.id IN $ids RETURN properties(n) AS props ORDER BY n.order',
            run=run_id, ids=ids, database_=self.database)
        edges, _, _ = self.driver.execute_query(
            'MATCH (a:BIFlowNode)-[e:FLOWS_TO]->(b:BIFlowNode) '
            'WHERE a.run_id=$run AND b.run_id=$run AND a.id IN $ids AND b.id IN $ids RETURN properties(e) AS props',
            run=run_id, ids=ids, database_=self.database)
        restored = [{k: v for k, v in r['props'].items() if k not in {'key', 'run_id', 'order'}} for r in nodes]
        # Neo4j omits null properties; retain the exported KPI contract.
        for node in restored:
            if node.get('kind') == 'kpi':
                node.setdefault('value', None)
        return {'nodes': restored,
                'edges': [r['props'] for r in edges]}


def save_run(graph):
    with Neo4jStore() as store:
        store.initialize()
        store.save(graph)


def load_runs():
    with Neo4jStore() as store:
        store.driver.verify_connectivity()
        return store.runs()


def ancestors(graph, target):
    with Neo4jStore() as store:
        return {**graph, **store.upstream(graph['run_id'], target)}
