"""BO2-07: statistical signals plus constraints, without automatic correction."""
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from data.data_generator import FEATURES
from governance.playbooks import clean_dataset, load_policy


@dataclass
class AnomalyResult:
    rows: pd.DataFrame
    robust_scores: pd.DataFrame
    cleaning: object
    metadata: dict


def profile_anomalies(source, contamination=0.03, robust_threshold=3.5, contexts=None):
    """Contexts map source row positions to analyst-supplied event explanations.

    A contextual exception is plausible, never a confirmed error-free record.
    Rows pending cleaning review cannot enter statistical models.
    """
    if not 0 < contamination <= 0.5 or not np.isfinite(robust_threshold) or robust_threshold <= 0:
        raise ValueError("Invalid detection thresholds")
    contexts = contexts or {}
    if any(not isinstance(p, int) or not 0 <= p < len(source) or not isinstance(v, str) or not v.strip()
           for p, v in contexts.items()):
        raise ValueError("Context requires valid row positions and nonempty descriptions")
    cleaned = clean_dataset(source, load_policy("1.2.0"))
    numeric = cleaned.data[FEATURES].reset_index(drop=True).apply(pd.to_numeric, errors="coerce")
    eligible = pd.Series(np.isfinite(numeric.to_numpy(dtype=float)).all(axis=1), index=numeric.index)
    eligible.iloc[cleaned.review_positions] = False
    rows = pd.DataFrame({"row_position": range(len(source)), "eligible": eligible,
                         "robust_max": np.nan, "isolation_score": np.nan,
                         "robust_flag": False, "isolation_flag": False,
                         "status": "Non évalué", "reason": "Effectif valide insuffisant",
                         "context": [contexts.get(i, "") for i in range(len(source))]})
    scores = pd.DataFrame(np.nan, index=rows.index, columns=FEATURES)
    for pos in cleaned.review_positions:
        events = cleaned.events[(cleaned.events.row_position == pos) & (cleaned.events.action == "review")]
        rows.loc[pos, "status"] = "Erreur probable / contrainte"
        rows.loc[pos, "reason"] = "; ".join(events.column + ": " + events.reason)
    usable = numeric[eligible]
    zero_mad = []
    if len(usable) >= 10:
        for col in FEATURES:
            median = usable[col].median()
            mad = (usable[col] - median).abs().median()
            if mad == 0:
                zero_mad.append(col)
                # No division by zero or claim of a calibrated score.
                scores.loc[eligible, col] = 0.0
            else:
                scores.loc[eligible, col] = 0.67448975 * (usable[col] - median).abs() / mad
        model = IsolationForest(n_estimators=100, contamination=contamination, random_state=42)
        model.fit(usable)
        rows.loc[eligible, "robust_max"] = scores.loc[eligible].max(axis=1)
        rows.loc[eligible, "isolation_score"] = -model.score_samples(usable)
        rows.loc[eligible, "robust_flag"] = rows.loc[eligible, "robust_max"] > robust_threshold
        rows.loc[eligible, "isolation_flag"] = model.predict(usable) == -1
        rows.loc[eligible, "status"] = "Aucun signal détecté"
        rows.loc[eligible, "reason"] = "Aucun seuil dépassé ; ne garantit pas la qualité"
        flagged = eligible & (rows.robust_flag | rows.isolation_flag)
        rows.loc[flagged, "status"] = "À réviser / sans contexte"
        rows.loc[flagged, "reason"] = "Signal statistique ; validation ANA/ORCH nécessaire"
        plausible = flagged & rows.context.str.strip().ne("")
        rows.loc[plausible, "status"] = "Exception plausible"
        rows.loc[plausible, "reason"] = "Contexte fourni par ANA ; validation humaine encore nécessaire"
    metadata = {"features": FEATURES, "contamination": contamination, "robust_threshold": robust_threshold,
                "n_estimators": 100, "random_state": 42, "eligible_rows": int(eligible.sum()),
                "minimum_rows": 10, "zero_mad_columns": zero_mad,
                "score_warning": "Scores are not calibrated error probabilities",
                "time_series": "Not applicable: no timestamp or ordered time series in this schema",
                "cleaning_manifest": cleaned.manifest}
    return AnomalyResult(rows, scores, cleaned, metadata)
