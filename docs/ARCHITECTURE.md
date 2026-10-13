# BO1 — Intelligent Data Understanding & Preparation

A connected, functional academic prototype for the **Multimodal Business Intelligence Agent**. BO1 prepares tabular datasets; the larger multimodal project can add document, image or audio agents later. This application accepts CSV files, generates five realistic synthetic datasets, executes real algorithms and exports actual results. Demonstration percentages are calculated, never hardcoded.

## BO1 objective and four DSO

Automatically understand, analyze, prepare, clean and integrate heterogeneous datasets before BI analysis.

| DSO | Responsibility | What the demo actually executes |
|---|---|---|
| **1 — Orchestration** | Manage agent dependencies and parallel execution | NetworkX DAG; asyncio scheduler or compiled LangGraph graph; state transitions, timings, failure propagation and live UI updates |
| **6 — Similarity** | Recognize related sources and preparation opportunities | Column vector embeddings and cosine similarity; optimal schema alignment; similarity matrix and stored recipe matching |
| **7 — Semantic understanding** | Classify business meanings rather than only Pandas types | Name aliases, regex/value patterns, dtype and statistics; 16 semantic classes; confidence and evidence |
| **5 — Cleaning** | Generate and execute safe preparation recipes | Rule-based or optional LLM JSON plans; Pydantic validation; allowlisted operation dispatch; code export, audit and quality comparison |

## Architecture

```text
Raw datasets
    ↓
Profiling
    ├───────────────┐
    ↓               ↓
Similarity DSO 6    Semantics DSO 7
    │               ↓
    │             Quality
    └───────┬───────┘
            ↓
      Cleaning Plan DSO 5
            ↓
      Plan Validation
            ↓
      Controlled Execution
            ↓
      Final Validation & BI
```

DSO 1 owns this graph. Profiling must finish before similarity and semantic tasks start. Similarity and semantics are independent and run concurrently. Quality waits for semantic classification because email/phone/age checks depend on meaning. Cleaning waits for profiles, similarity, semantic classes and quality results. Execution receives only a validated structured plan. Final validation evaluates the quality gate and infers guarded enrichment joins.

Independent per-dataset work also uses a bounded thread pool. The asyncio backend schedules each node as soon as its parents complete. LangGraph uses dependency barriers and a reducer for parallel results. Both use the same agent functions, graph and recorded status model. No artificial sleeps create an illusion of concurrency. The UI timeline shows measured intervals; rendering overhead contributes to overall elapsed time, so task sums are not presented as a guaranteed speedup.

## Technologies and installation

Python 3.11+, Pandas, NumPy, Scikit-learn, SciPy (via Scikit-learn), NetworkX, LangGraph, Streamlit, Plotly, Pydantic and Sentence Transformers. OpenAI is optional; no API key is needed for the default offline path. The neural package is installed by requirements.txt; its model weights are a separate, explicit setup step.

From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

If your shell has a disabled Python alias, use the actual Python executable. In the supplied BO1 workspace, the parent `.venv` already contains the runtime and installed dependencies:

```powershell
cd C:\Users\omran\Downloads\BO1
.\run_demo.bat
```

The updated Windows launcher opens the new application on port **8502**, allowing the earlier two-DSO prototype to remain on 8501. Keep its terminal open; Ctrl+C stops it. Portable project installation and `streamlit run app.py` use Streamlit's default port 8501.

`requirements-lock.txt` records the exact verified Windows/Python 3.12 environment. Use `pip install -r requirements-lock.txt` to reproduce that environment; use `requirements.txt` for compatible versions on other supported Python platforms. MiniLM setup pins model revision `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`.

Headless execution and verification from this project:

```powershell
python pipeline.py --rows 200 --backend asyncio
python pipeline.py --rows 200 --backend langgraph
python -m unittest discover -s tests -v
```

Windows asyncio and Streamlit require local socket access. If running under a restricted execution sandbox, permit loopback sockets or run from a normal terminal.

### Optional MiniLM embeddings

The default selection attempts **local MiniLM**, a learned 384-dimensional sentence encoder, and falls back safely if its weights are absent. The supplied workspace has the package and model installed and both neural and hashing pipelines verified. You can explicitly select reproducible offline **lexical/concept hashing embeddings** with 1024 dimensions and cosine similarity. Hashing is a real vector baseline, but it is not a learned sentence encoder. Known aliases and business concepts supply its semantic vocabulary.

For the requested neural alternative:

```powershell
pip install -r requirements-embeddings.txt
python download_embedding_model.py
```

The second command explicitly downloads `sentence-transformers/all-MiniLM-L6-v2` into `models/all-MiniLM-L6-v2`. It is a one-time setup with Internet access. Choose **Local Sentence Transformers / MiniLM** in the UI. The application only loads local files with `trust_remote_code=False`; it never initiates a model download. If the package/model is unavailable, processing continues with local hashing and displays the fallback reason. You can also point `BO1_EMBEDDING_MODEL` to a local model directory. The selected backend is always visible and exported.

### Optional LLM plans

Set `OPENAI_API_KEY` and optionally `OPENAI_MODEL` in the process environment, then enable the sidebar checkbox and run the pipeline. `.env.example` documents the variables; `.env` is not automatically loaded. Only column names, heuristic semantic metadata and aggregate quality statistics are sent; raw sample rows are excluded.

The provider returns a JSON plan that must match the Pydantic schema, column list and semantic protection rules. Remote imputation, arbitrary replacement and custom category mappings are rejected under the default preservation policy. Bad responses, unsupported operations, timeout/authentication failures and missing keys fall back to the deterministic local plan. Actual remote execution requires a user-supplied key and is not validated by offline tests; mocked tests cover timeout and malicious plan rejection. There is no `exec` or `eval` path for remote or generated Python.

## Agent modules

| Agent | File | Inputs → Outputs |
|---|---|---|
| ProfilerAgent | `agents/profiler_agent.py` | Raw datasets → counts, schema, missing/duplicate percentages, samples and numeric statistics |
| SimilarityAgent | `agents/similarity_agent.py` | Raw datasets + profiles → vector comparisons, optimal matches, matrix and recipe opportunities |
| SemanticTypeAgent | `agents/semantic_agent.py` | Raw columns → class, confidence, canonical name and value-pattern evidence |
| DataQualityAgent | `agents/quality_agent.py` | Raw datasets + semantic classes → typed quality issues and transparent scores |
| CleaningAgent | `agents/cleaning_agent.py` | Profile + similarity recipes + semantics + quality → plan, validation and controlled transformations |
| OrchestratorAgent | `agents/orchestrator_agent.py` | Datasets + settings → connected DAG execution, recorded task state and final BI outputs |

`core/` contains algorithms. `pipeline.py` provides a reusable headless entry point and exports. Call `run_pipeline(datasets, config, registry, callback, persist_outputs)` from Python for an embedded workflow.

## Algorithms and explainability

### Similarity

Descriptors encode canonical column names and shared concepts. The local embedding concatenates weighted word-ngram and character-ngram hash vectors; MiniLM replaces the encoder with normalized learned sentence vectors. Each candidate column pair records:

```text
score = 0.50 embedding cosine
      + 0.15 canonical-name similarity
      + 0.10 value-pattern compatibility
      + 0.10 technical type compatibility
      + 0.10 cardinality compatibility
      + 0.05 shared identifier overlap
```

The Hungarian assignment finds an optimal one-to-one alignment. Dataset similarity is the sum of matched scores divided by the larger number of columns. Extra unmatched columns lower the score. This makes column order irrelevant. In this example, customers has separate first/last names and clients has one full-name column: one-to-one alignment intentionally penalizes that structural difference. Scores around **82%** in the local 120-row seed-42 example are real; the request's illustrative 94% is not forced. Scores and alias coverage are heuristics, not probabilities or measured generalization accuracy.

Saved validated cleaning recipes are recorded in `outputs/cleaning/recipe_registry.json`. A first run recommends potential reuse; subsequent runs can actually reuse compatible mapped steps. Reuse requires a sufficiently strong column match and the same semantic class. It transfers only matching existing safe operations/parameters; business-value fills and custom numeric ranges are not copied blindly. Each reused step names its origin and is revalidated against target data. This is local knowledge reuse, not a production versioned recipe store.

### Semantic classification

Classes: IDENTIFIER, PERSON_NAME, EMAIL, PHONE_NUMBER, AGE, DATE, DATETIME, LOCATION, ADDRESS, POSTAL_CODE, CURRENCY, NUMERIC, BOOLEAN, CATEGORY, TEXT and URL. Name rules are supported by populated-value regex rates, dtype, distinct-value counts and business constraints. Pattern evidence samples up to 500 populated values. Confidence measures heuristic rule strength, not calibrated statistical certainty.

### Quality score

The overall score is the equally weighted mean of six 0–100 components:

```text
Completeness           = 100 × (1 − missing cells / total cells)
Uniqueness             = 100 × (1 − duplicate rows / total rows)
Validity               = 100 × (1 − invalid cells / populated cells)
Type consistency       = 100 × (1 − storage-type anomalies / populated cells)
Categorical consistency= 100 × (1 − noncanonical category cells / populated cells)
Format consistency     = 100 × (1 − whitespace/email-case anomalies / populated cells)
```

Blank strings count as missing. Empty denominators use 1 to avoid errors. Numeric/currency strings count as storage-type anomalies until conversion. Category consistency uses an explicit lowercase/casefold convention; a title-cased category is not necessarily wrong in its original business context. Missing values can increase when invalid values are masked, so completeness and raw counts remain visible. An improved overall score does not imply every component improved. IQR outliers are advisory and are not automatically deleted. Unknown free text cannot be validated against external truth.

### Controlled cleaning

Allowlisted operations: strip, lowercase, uppercase, literal replace, explicit fill_missing, convert_numeric, convert_dates, remove_duplicates, normalize_categories, validate_email, normalize_phone, validate_phone, remove_impossible_values, validate_url and convert_boolean. Identifiers allow only whitespace normalization and retain case and leading zeros. Default recipes never fabricate missing business values. Whitespace and case variants of categories are merged by exact normalized spelling; fuzzy categories are not conflated. Phone formatting follows an 8–15-digit structural check with optional `+`, not country-level deliverability validation. Slash dates use day-first interpretation; timestamps use UTC. Currency parsing assumes the demonstration's dot-decimal/comma-thousands convention and does not convert currencies.

Every step has its reason, origin, changed-cell count and missing-value impact. Exact duplicates are removed after normalization. Validation verifies the schema and allowlist before dispatch, then checks preserved columns and nonincreasing row count. The generated Python export calls this engine with a literal plan; it is syntax-checkable and reviewable, but the app executes the plan rather than that Python text.

### BI readiness and integration

Readiness requires the configured quality threshold plus zero detected invalid cells and zero exact duplicate rows. Remaining missing values are disclosed. This is a demo acceptance gate, not a promise that facts are correct or every BI model can consume them. Failed gates retain their cleaned outputs for review.

Inferred enrichment joins require matching identifier concepts, a unique nonmissing parent key, repeated child keys and at least 80% distinct-key coverage. Execution enforces many-to-one joins and prefixes parent columns to preserve lineage. The two customer sources may both enrich transactions; no automatic cross-source entity merge is claimed. Relationship evidence is separate from the execution DAG.

## Five-minute demonstration

1. **Generate Synthetic Data**: five differently structured CSVs, renamed/reordered columns and deliberately dirty data.
2. **Run BO1 Pipeline**: watch PENDING → RUNNING → COMPLETED states with real live DAG updates.
3. **DAG Orchestration — DSO 1**: inspect dependencies, input/output summaries and measured parallel intervals.
4. **Dataset Similarity — DSO 6**: show the matrix and customers/clients_2026 matching evidence. Explain the chosen vector backend and real computed score.
5. **Semantic Classification — DSO 7**: show client_identifier → IDENTIFIER, email_address → EMAIL, telephone → PHONE_NUMBER, customer_age → AGE; inspect confidence and reasoning.
6. **Data Quality**: review detected missing, duplicate, format, numeric, phone, email and category issues; display the formula.
7. **Cleaning & Transformation — DSO 5**: review plans and generated code. **Validate & Execute Cleaning** revalidates and safely reexecutes the displayed plan on raw input, verifying agreement with the completed pipeline output.
8. **Final Results**: compare before/after charts and data samples, inspect readiness/joins and download outputs.
9. Run again to demonstrate reuse of previously validated recipes.

The pipeline automatically validates and executes all plans in a full run; the cleaning-page button is a transparent reexecution, not a claim that the previous results were still uncleaned.

## Data and outputs

Synthetic CSVs in `data/generated/`: customers, clients_2026, transactions, employees and products. They include missing cells, duplicates, whitespace, mixed email/category case, mixed/invalid dates, malformed email/phone strings, impossible ages, monetary strings, identifier whitespace variants and a flagged amount outlier. Seeded generation is reproducible.

Uploaded CSVs support UTF-8/Windows-1252 and comma, semicolon, tab or pipe delimiters. Headers must be distinct and nonempty; at least one data row is required. Values load as strings to preserve identifiers. This interface does not accept XLSX, JSON, PDF, images or audio. CSV upload size is governed by Streamlit; all algorithms run in memory, so use moderate files for a presentation.

Downloads include:

```text
dataset_profiles.json
similarity_matrix.csv
similarity_evidence.json
semantic_classification.csv
quality_report_before.json
cleaning_plan.json
quality_report_after.json
dag_execution.json
bi_readiness.json
integration_plan.json
cleaned/<dataset>.csv
cleaning/clean_<dataset>.py
cleaning/plan_<dataset>.json
cleaning/audit_<dataset>.json
integrated/transactions_enriched.csv
bo1_results.zip
```

The selected dataset also downloads as `cleaned_dataset.csv`. All requested report filenames have individual UI download buttons. Results are persisted under grouped `outputs/` directories; existing same-name files are overwritten and unrelated older outputs can remain. The current-run ZIP is the authoritative current artifact set. The recipe registry intentionally persists between runs. Raw generated data is separate from cleaned outputs. `bo1_intelligent_data_source.zip` contains the complete source and sample outputs, excluding virtual environments, secrets, caches and large model weights. On another computer, install requirements and explicitly download the model, or use the offline fallback.

Example seed-42 run with 120 customers: customers/clients_2026 similarity **0.8191 with hashing**, **0.8160 with MiniLM**; customer quality **91.49 → 99.18**; transaction quality **91.24 → 99.52**; enriched transaction count **360**. Other row counts/backends change these measured values.

## Complete source tree

```text
bo1_intelligent_data/
├── app.py
├── pipeline.py
├── package_project.py
├── data_generator.py
├── download_embedding_model.py
├── requirements.txt
├── requirements-lock.txt
├── requirements-embeddings.txt
├── README.md
├── .env.example
├── agents/
│   ├── __init__.py
│   ├── profiler_agent.py
│   ├── similarity_agent.py
│   ├── semantic_agent.py
│   ├── quality_agent.py
│   ├── cleaning_agent.py
│   └── orchestrator_agent.py
├── core/
│   ├── __init__.py
│   ├── profiling.py
│   ├── embeddings.py
│   ├── semantic_classifier.py
│   ├── quality_engine.py
│   ├── cleaning_engine.py
│   ├── llm_provider.py
│   ├── dag_engine.py
│   └── integration.py
├── utils/
│   ├── __init__.py
│   ├── visualization.py
│   ├── logging_config.py
│   └── helpers.py
├── tests/
│   ├── test_core.py
│   └── test_app.py
├── data/generated/ [five CSVs]
├── models/ [optional local MiniLM]
└── outputs/
    ├── similarity/
    ├── quality/
    ├── cleaning/
    ├── integration/
    └── bo1_results.zip
```

The full source is in these files. The Windows launchers live one directory above the project.

## Limitations and future improvements

This is a functional academic prototype, not a production platform. Similarity weights, aliases and confidence are heuristic. One-to-one matching cannot fully model split/merged columns. The hashing fallback cannot infer arbitrary unseen multilingual synonyms. Neural embeddings need an explicitly installed local model. Quality components are structural proxies, not ground-truth correctness. Locale-specific currency/date/phone rules, real postal validation, entity resolution and declared foreign keys would improve robustness.

Future extensions: labeled evaluations and calibrated thresholds, expanded multilingual ontology, editable reviewed rules, user-approved imputation, richer schema matching, FAISS for large catalogs, a versioned recipe store, provenance/checkpoint persistence, retries/timeouts per task, multimodal extraction agents and a BI semantic layer. The current independent agents and structured state interfaces provide the extension points without requiring a distributed architecture.

## Primary technical references

- [LangGraph StateGraph dependency edges](https://reference.langchain.com/python/langgraph/graph/state/StateGraph/add_edge)
- [Sentence Transformers model loading and local_files_only](https://www.sbert.net/docs/package_reference/sentence_transformer/model.html)
- [Sentence Transformers embedding encoding](https://sbert.net/examples/sentence_transformer/applications/computing-embeddings/README.html)
