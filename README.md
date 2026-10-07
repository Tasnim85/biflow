# BIFlow: XAI Auditor Prototype (BO3)

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