# Intelligent Data Preparation & Integration

A working local Streamlit prototype for the Multimodal Business Intelligence Agent. All scores, similarity matrices, profiles, changes and charts are computed from generated or uploaded data. No API key is required.

## Run locally

On this machine, double-click `run_demo.bat`. Or run from this directory:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app.py
```

For a new machine (Python 3.11+):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py
```

## Demonstration walkthrough

1. Open Overview. Five reproducible dirty datasets are loaded automatically. Generate Demo Data offers 100, 500, 1000 or 5000 base rows per dataset; intentional duplicates add rows.
2. Select the datasets to analyze and click Launch Demonstration. Watch the live execution graph: profiling precedes parallel similarity, semantics and quality analysis. Recommendations and plan validation follow.
3. Explore the clickable pipeline and dedicated analysis pages. Each page explains its input, purpose, method and output. Global and contextual filters update applicable tables and charts.
4. Review semantic meanings. Approve, reject or modify a meaning and provide a reason. Changed meanings require a new analysis before cleaning can be approved.
5. In Intelligent Cleaning & Transformation, select/deselect operations, optionally modify the structured JSON plan, and inspect generated Python and explanations.
6. Click Preview Cleaning. This transforms copies only. Inspect before/after scores, individual changes and the summary of every dataset in the approval scope.
7. Enter an approval reason, check the confirmation, and click Approve & Execute. Execution uses the exact previewed plans; changed selections invalidate the preview. The live graph resumes through controlled execution and final validation.
8. Inspect Transformation Impact, Audit Trail and BI Readiness. Download clean CSVs, individual reports or the complete ZIP with session decisions.

Recipe reuse is available from earlier executed plans. The Similarity page displays mapped operations and requires recipe review before adding them to a plan. The target still needs preview and execution approval.

## Architecture

The existing project is kept at this repository root to preserve the working launcher; there is no second nested application.

```text
app.py                  Streamlit workspace and human review workflow
pipeline.py             analysis, reviewed execution and artifact exports
data_generator.py       reproducible dirty customer/client/transaction/employee/product data
agents/                 profiler, similarity, semantic, quality, cleaning, orchestrator
core/                   DAG scheduler, embeddings, semantic classifier, quality,
                        controlled cleaning, structured optional LLM and integration
ui/                     shared stages, explanations, filtering, audit and charts
utils/                  safe CSV ingestion, logging and Plotly visualizations
tests/                  engine tests and Streamlit interaction tests
data/generated/         generated CSV inputs
outputs/                approved cleaned data, plans, reports and recipe registry
outputs/logs/           timestamped human decisions (JSON Lines)
logs/                   runtime diagnostics
```

The NetworkX DAG is executed by asyncio or LangGraph. Independent branches use worker threads and per-dataset work uses a bounded thread pool. Quality derives its own semantic validation signals so it can run concurrently with the semantic review branch; both use the same configured reviewed meanings.

## Measured methods and limits

- Similarity uses real vector embeddings and cosine similarity, concept alignment, observed pattern/type/cardinality compatibility and column assignment. Default local hashing is an offline baseline. Select local Sentence Transformers / MiniLM for learned embeddings when model weights are available; failure falls back visibly. No model is downloaded automatically.
- Semantic classification uses 16 business classes and evidence from names, values, ranges and uniqueness. Confidence is heuristic rule strength, not calibrated accuracy. Pattern inspection samples up to 500 present values.
- Quality is the mean of completeness, uniqueness, validity, type consistency, categorical consistency and format consistency. Accuracy requires external truth. Missing business values are preserved; invalid values can become missing. IQR outliers are flagged for review.
- Without an API key, local rules generate structured cleaning plans and reviewable code exports. Optional OpenAI enrichment returns validated JSON only. No arbitrary generated Python is executed. Pydantic and semantic checks reject unsupported operations, columns and protected identifier transformations.
- Readiness requires the configured score threshold, zero detected invalid cells and zero duplicate rows. Semantic coverage is separately disclosed as the share of non-text meanings at confidence >=80%. Readiness is a demo gate, not proof of business correctness.
- Sequential time is an estimate from the sum of measured task durations. Parallel time is actual elapsed processing including live UI overhead. Negative savings are possible. Human review waiting is excluded; there are no artificial delays or fabricated speedups.
- CSVs are processed in memory. Date parsing follows ISO and day-first slash conventions. Category normalization uses casefolding without fuzzy merging. Cleaned data and decision logs persist locally; treat exports as containing the same information as the inputs.

`.env.example` lists optional environment variables; `.env` is not automatically loaded. Install local MiniLM explicitly using `download_embedding_model.py` if required.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Tests cover actual quality improvements, unsafe plan rejection, identifier preservation, CSV ingestion, embedding alignment, DAG concurrency and failure handling, both scheduler backends, all 11 interface pages, explicit approval gating, downloads, filters and clickable navigation.
