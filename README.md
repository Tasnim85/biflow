# BIFlow: XAI Auditor Prototype (BO3)

## BO2-05 — Column lineage

### Neo4j storage (current implementation)

The BO2-05 page now writes native `BIFlowRun` and `BIFlowNode` nodes, `HAS_NODE`
membership and `FLOWS_TO` dependency relationships to Neo4j. The upstream path
is queried with Cypher, not calculated from SQLite. Each node is scoped by run
ID; uniqueness constraints protect execution/node identity. A transactional save
creates the run and graph together. Reimporting an identical run is idempotent;
conflicting content for an existing ID is rejected. A full snapshot is retained
alongside native nodes for exact JSON exports and metadata retrieval.

1. Install dependencies with `pip install -r requirements.txt`.
2. Use `.env.example` as the template for a local `.env` (ignored by Git).
   Set a strong `NEO4J_PASSWORD`; the initial setup has generated one locally.
3. Run `docker compose -f compose.neo4j.yml up -d`.
4. Run `python -m streamlit run governance_app.py`.

Neo4j Browser is at http://localhost:7474 ; Bolt is at localhost:7687.
The user is `neo4j`; retrieve the password locally from `.env`, never commit it.
The container binds only to localhost and keeps its data in a dedicated Docker
volume. Changing `.env` does not reset the password of an initialized volume.
Stop using `docker compose -f compose.neo4j.yml stop` without deleting the volume.

Import earlier SQLite runs explicitly with `python -m governance.migrate_lineage`.
The original database remains intact. The UI reports connectivity failures and
does not silently fall back to SQLite. For remote Neo4j, set the URI, username,
password and database in environment variables (these override `.env`).

Example Neo4j Browser query (set `$run_id` to an execution UUID):

```cypher
MATCH p=(source:BIFlowNode)-[:FLOWS_TO*0..]->(kpi:BIFlowNode)
WHERE kpi.run_id = $run_id AND kpi.id = 'kpi:amount_sum'
RETURN p
```

Live integration tests are opt-in: in PowerShell set
`$env:BIFLOW_TEST_NEO4J='1'`, then run `python -m unittest discover -s tests -v`.
The integration test creates and removes only its own uniquely identified run.
The earlier BO2-05 PDF describes the SQLite prototype and predates this upgrade.

Setup references: [Neo4j Docker Compose](https://neo4j.com/docs/operations-manual/current/docker/docker-compose-standalone/),
[official Python driver](https://neo4j.com/docs/python-manual/current/).

The BO2-05 page in `governance_app.py` computes three demo KPIs from the actual
BO2-02 cleaning output: sum of transaction amounts, mean income and sum of
transaction counts. Amount sum is not labelled revenue without a business
definition. All five numeric fields must pass cleaning review for a row to
contribute. No joins, temporal lineage or external operations are invented.

`governance/lineage.py` emits dataset, column, cleaning transformation, filtering
and KPI nodes with typed, versioned edges per unique execution. Value dependencies
are distinct from row-selection dependencies. Selecting a KPI shows its upstream
graph; selecting a node displays its formula, policy, counts or fingerprint.
Graphs include the policy snapshot and input/output hashes, and can be exported
as JSON. Current run metadata is persisted in Neo4j; the earlier SQLite
database at `output/lineage/runs.sqlite3` is kept as an importable archive.
Source records and personal values are not stored in that graph database.

The graph is rendered with Streamlit Graphviz and stored in Neo4j, without an
OpenLineage service. Lineage for PII, anomaly models and other
external pipelines is not instrumented yet. Empty eligible datasets yield no
KPI value. Tests cover arithmetic, dependency paths, persistence and navigation.

## BO2-03 — PII detection and protection (local demo)

Open `python -m streamlit run governance_app.py` and select BO2-03.
`data/pii_generator.py` creates a separate copy with the original seven columns
plus full_name, email, phone, national_id and notes. Names are synthetic,
emails use example.com, phones use the fictional +1-202-555-01xx range, and
identifiers are explicitly DEMO-ID values, not real national identifiers.

`governance/pii.py` detects sensitive content using declared column roles,
regular expressions and a synthetic-name dictionary. Structured PII fields
are protected completely, even for names absent from the dictionary. Free
text recognition has limited coverage: no general NER/Presidio model and no
international phone or national-identifier detector is implemented.

Two demo policies are available: typed masking and HMAC-SHA256 pseudonyms.
Pseudonyms preserve links for matching normalized values and entity types
across cells, including notes. A random 32-byte key is created per Streamlit
session; it is neither displayed nor exported. No reversible mapping is kept.
New sessions change pseudonyms. Pseudonymization is not anonymization.

Raw fictional data is hidden unless explicitly enabled. Only protected data
and an audit without raw values/keys are downloadable. The first seven columns
are untouched; the source is never mutated. This UI visibility control is not
authentication or role-based access control: there is no production access
control, secure key service or downstream enforcement integration. Use only
synthetic data here. The demo reports 3,500 protected occurrences on 500 rows.

## BO2-07 — Anomaly profiling

Run `python -m streamlit run governance_app.py` for the BO2 navigation
(cleaning and anomaly profiling). BO3 remains available through `app.py`.

`agents/anomaly_agent.py` first applies cleaning policy 1.2.0. Rows with
unresolved exceptions stay visible but are excluded from statistical fitting;
there is no imputation or automatic anomaly removal. The five numerical
features are used, never the simulation annotations.

- Robust absolute scores: `0.67448975 * abs(x - median) / MAD`; default threshold
  3.5. With zero MAD, the column's robust score is noninformative (zero) and the
  UI reports this limitation. Isolation Forest still examines eligible data.
- Isolation Forest: 100 trees, random state 42, default assumed contamination
  0.03. The displayed score negates `score_samples` so larger means more unusual.
  Contamination determines the threshold, not a measured error prevalence.
- Classification: constraint exceptions, statistical signals requiring review,
  plausible contextual exceptions, no detected signal, or insufficient data.
  Analyst context is supplied by zero-based row position and cannot override
  a violated constraint. Contextual plausibility is not confirmation of validity.
- At least 10 eligible rows are required. No time-series residual analysis or
  formula validation is invented for a schema without dates or approved formulas.
- CSV/JSON exports record scores, decisions, parameters and cleaning provenance.
  Results and analyst context are session-local. DQ/SEM/ANA/ORCH responsibilities
  are simulated locally; routing means a review classification, not messaging.
- The model fits and scores the same sample for exploratory profiling. Scores
  are not calibrated error probabilities; no production accuracy claim is made.

Reference: [scikit-learn IsolationForest documentation](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html).

## BO2-02 — Versioned cleaning playbooks

On branch `ahmed-ikbel`, the Streamlit sidebar includes **BO2 Playbooks**.
Run `python -m streamlit run app.py`, then open that page. For a standalone
BO2 session: `python -m streamlit run pages/1_BO2_Playbooks.py`.

- Uses the existing 500-row synthetic customer generator, with no source mutation.
- The default test dataset is a newly generated 500-row synthetic dataset with
  exactly the original seven columns, saved as `data/customers_dirty.csv`.
  Regenerate it with `python -m data.dirty_generator`. Each field is sampled
  directly from a raw-value distribution (normal, formatted, missing, blank,
  text, negative, invalid domain, unit, ambiguous separators, nonfinite).
  There is no clean intermediate dataset or positional defect replacement.
  The seed makes generation reproducible; defects are spread across records.
  The separate `data/customers_dirty_defects.csv` records generation modes.
  Statistical anomaly labels remain False/none, independently of cleaning
  defects. The original BO3 generator remains unchanged.
- Policy 1.2.0 normalizes numeric strings with whitespace and decimal commas;
  missing and invalid values go to review. Commas mean decimals in this demo
  context, never thousands separators. Ground-truth annotations are untouched.
- JSON policies in `policies/` declare context, semantic column roles, demo approval
  metadata and rule IDs. Version 1.0.0 accepts ISO dates; 1.1.0 also accepts
  day/month/year (optional columns, absent in the new dataset). Add a new
  file/version to evolve a policy; retain old versions.
- Missing categories become `Unknown` only under the categorical policy.
  Missing financial/numeric values, invalid dates and duplicate identifiers go
  to review. No median imputation, automatic row removal or outlier correction.
- Optional absent columns are reported as skipped. Required missing columns,
  incompatible context and incompatible transformation roles block execution.
- Before/after tables, cell-level events, review row positions (zero-based),
  policy snapshot and SHA-256 fingerprints are available in the UI and exports.
- Results are session-local; download the JSON audit to retain evidence. The CSV
  includes unresolved rows and is not automatically passed to downstream agents.
- DQ selection, SEM validation and ETL execution are local prototype functions,
  not autonomous agents or a production approval/access-control service.
  Policy approval is scoped to this demonstration; business sign-off is still
  required for real data. BO2-07, BO2-03 and BO2-05 are separate future work.

Run automated engine and Streamlit interaction tests:

```powershell
python -m unittest discover -s tests -v
```

Small prototype demonstrating **BO3: Explainability & Auditability** for BIFlow.

**Chain shown:** Decision → Explanation → Evidence → Audit trail

## What it does

1. **Data Profiler Agent** (`agents/profiler_agent.py`): trains an Isolation Forest on a
   synthetic customer dataset and flags anomalous rows (the *decision*).
2. **BI Auditor / XAI Agent** (`agents/auditor_agent.py`): reads the decision, computes SHAP
   contributions (`xai/shap_explainer.py`), writes a template-based sentence
   (`xai/narrator.py`) and records an audit log entry.
3. **Streamlit UI** (`app.py`): display layer only, no business logic.

## Run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Test each module

```powershell
python -m data.data_generator
python -m agents.profiler_agent
python -m xai.shap_explainer
python -m xai.narrator
python -m agents.auditor_agent
```

## Design choices

- **SHAP explains the model's score, not business truth.** Contributions are in isolation-path
  splits and add up exactly to the gap between a typical row and the audited row
  (verified in `xai/shap_explainer.py`).
- **Template-based explanations** (no LLM): every word traces back to a number.
- **Synthetic data with planted anomalies**: lets us check the explanations against ground truth.
  The model never sees the `true_anomaly` and `anomaly_type` columns.
- **Logic is separate from the UI**, so the modules can later become real BIFlow agents.

## Known limitations

- Isolation Forest caught 11 of 15 planted anomalies and had 4 false alarms. Type B
  (extreme transaction counts) is the weak spot.
- `contamination=0.03` is an assumption; real data would not tell us the anomaly rate.
- The audit log lives in memory and resets when the server restarts.
- The "ordinary observation" rule (within 1 split of typical) is a judgment call.

## Future work

- CSV upload, LIME as a second explainer, persistent audit log
- Connect to the other BIFlow agents through an orchestrator
