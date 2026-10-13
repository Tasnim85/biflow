from core.semantic_types import infer_types
from core.quality import assess_quality

def profile(name,frame):
    types=infer_types(frame)
    return dict(dataset=name,rows=len(frame),columns=len(frame.columns),semantic_types=types,quality=assess_quality(frame,types),
        column_profiles=[dict(column=c,dtype=str(frame[c].dtype),distinct=int(frame[c].nunique()),missing=int(frame[c].isna().sum()),sample=frame[c].dropna().astype(str).head(5).tolist()) for c in frame.columns])
