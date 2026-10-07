# Multimodal Business Intelligence Agent — BO1 prototype

Functional Python prototype for **DSO 1 (selected): Similarity + DAG** and **DSO 2 (backup): generated cleaning code + automatic semantic type detection**. BO1 accepts tabular CSV inputs; image/audio processing is outside this prototype's scope. No API key or model download is required.

## Run

From this project's directory, using Python 3.11 or later:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python data_generator.py
python -m streamlit run app.py
```

Open the address printed by Streamlit (usually http://localhost:8501). Click **Generate demo and run both DSO**, or upload multiple CSV files and click **Run uploaded CSV files**. Settings take effect on the next run. CSVs load as strings to preserve leading zeros in identifiers. The generated demo includes reordered/renamed columns, mixed date formats, currency strings, missing values, exact duplicates, invalid emails and invalid ages.

In the supplied BO1 workspace, dependencies are installed in the parent `.venv`. From `C:\Users\omran\Downloads\BO1`, run `./run_demo.ps1` to launch the app. Alternatively run `.\.venv\Scripts\python.exe -m streamlit run bo1_prototype\app.py`. The environment uses bundled Python 3.12 because the system `python` alias is unavailable on this computer.

For a headless run and meaningful algorithm checks:

```powershell
python pipeline.py
python -m unittest discover -s tests -v
```

## DSO 1

Profiling reports rows, storage types, distinct counts, missing values, samples, semantic types and quality metrics. Column scores combine **45% canonical name similarity + 25% semantic type agreement + 20% normalized value Jaccard + 10% cardinality agreement**. Known business aliases map client/customer names to a shared vocabulary; fuzzy names use Python SequenceMatcher. Greedy one-to-one column alignment produces a dataset score divided by the larger schema width, so column order is irrelevant and missing columns reduce the score. Every match exposes its evidence. This is a lightweight lexical/value baseline, not a pretrained embedding model; it does not claim cosine embeddings or FAISS performance.

Dataset union candidates use a configurable threshold (default 0.70). Relationships require matching canonical identifier names, a unique parent key after exact duplicate removal, repeated child keys and at least 80% distinct child-key coverage. Relationship evidence is separate from the processing DAG. The directed graph models input → profile → clean → integrate → output dependencies and is validated by NetworkX. Independent profiling and cleaning jobs use a thread pool. This is local orchestration, without a distributed scheduler.

The prototype executes suggested unions and many-to-one enrichment joins. Unions retain `_source_dataset` lineage and do not resolve cross-source entity duplicates. Both customer source tables can enrich transactions, retaining source-specific columns with suffixes. Joins enforce cardinality to prevent accidental row multiplication. Outputs are exploratory inferred integrations; inspect evidence before treating them as declared business constraints.

## DSO 2

Rule-based semantic inference covers identifiers, email, dates, currency, numeric, age, person names, locations, categories and free text. Confidence values express heuristic strength rather than calibrated model probabilities. Cleaning trims strings, lowercases email addresses, parses ISO and day-first slash dates, converts currency strings, masks invalid emails/ages/numbers/dates, and removes exact duplicate rows after normalization. Identifiers are preserved. Missing values remain missing; business values are never fabricated. Date interpretation assumes slash dates are day-first and currency punctuation follows the demo's format (not a universal locale parser).

Each dataset has an explained structured plan, generated executable Python, changed-cell audit and before/after metrics. Generated local code calls the trusted deterministic engine with a literal plan; it is compiled and actually executed, and its result must equal the direct engine result. Downloaded code runs from this project with its dependencies on the Python path.

Completeness = nonmissing cells / total cells. Validity = valid populated cells / populated cells. Uniqueness = rows minus duplicate rows / rows. Consistency measures freedom from detected whitespace/email-case problems. Overall score is their equally weighted average. Invalid-to-missing conversion can improve validity while reducing completeness, so raw counts and all components are displayed alongside the score. Unknown text values are not validated against external ground truth.

## Optional LLM advice

Set `OPENAI_API_KEY` in the process environment; optionally set `OPENAI_MODEL`. `.env.example` documents these variables; `.env` is **not** automatically loaded. Enable the sidebar checkbox and explicitly request advice. Only column metadata and aggregate metrics are sent. Returned semantic suggestions, recommendations and pandas code are displayed for review. Remote code is not executed and does not silently replace local decisions. Missing keys, request failures and malformed responses fall back to local mode. Remote execution was not validated without an API key.

## Files and results

`agents/` wraps each responsibility; `core/` implements algorithms; `utils/` contains CSV/JSON and Plotly helpers. `pipeline.py` coordinates dependency order. `data/` contains reproducible demonstration CSVs. `outputs/` contains cleaning/integration plans, per-dataset generated Python, cleaned CSVs, union CSVs and enriched transactions. The UI also downloads a ZIP of the current run. Persisted filenames are overwritten on subsequent runs; older unrelated outputs may remain, so use the ZIP for a precise current-run bundle.

The default 120-customer seed-42 demo detects customers/clients similarity around 0.96, produces a 240-row source-preserving union and a 360-row enriched transaction table. Tests cover expected links, reordered columns, unrelated sources, leading-zero identifiers, code equivalence, idempotence, missing values and nonunique-parent rejection.

This research prototype computes all-pairs column comparisons and stores values in memory. Use moderate CSV files; large production inputs would need sampling, indexed candidate search, measured thresholds, stronger locale handling, persistent execution tracking and entity-resolution policies.
