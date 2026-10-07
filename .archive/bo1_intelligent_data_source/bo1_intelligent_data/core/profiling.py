import numpy as np
from utils.helpers import missing_mask
from core.semantic_classifier import parse_numeric

def profile_dataset(name,frame):
    columns=[]
    for c in frame:
        s=frame[c]; numeric=parse_numeric(s); finite=numeric.dropna()
        finite=finite[np.isfinite(finite.astype(float))]
        stats=None
        if len(finite) and len(finite)>=max(1,int((~missing_mask(s)).sum()*.8)):
            stats={'min':float(finite.min()),'max':float(finite.max()),'mean':float(finite.mean()),'median':float(finite.median())}
            stats={k:v if np.isfinite(v) else None for k,v in stats.items()}
        columns.append({'column':c,'dtype':str(s.dtype),'missing_count':int(missing_mask(s).sum()),
            'missing_percentage':round(100*missing_mask(s).mean(),2),'unique_values':int(s.nunique()),
            'sample_values':s[~missing_mask(s)].astype(str).head(5).tolist(),'statistics':stats})
    missing=sum(c['missing_count'] for c in columns); duplicate=int(frame.duplicated().sum())
    return {'dataset':name,'rows':len(frame),'columns':len(frame.columns),'column_names':list(frame.columns),
        'missing_count':missing,'missing_percentage':round(100*missing/max(1,frame.size),2),'duplicate_count':duplicate,
        'duplicate_percentage':round(100*duplicate/max(1,len(frame)),2),'column_profiles':columns}
