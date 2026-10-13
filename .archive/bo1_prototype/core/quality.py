import pandas as pd
from core.semantic_types import infer_types,numeric,dates

def invalid_mask(series, kind):
    present=series.notna() & series.astype('string').str.strip().ne('').fillna(False)
    if kind=='email': valid=series.astype('string').str.strip().str.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').fillna(False)
    elif kind=='date': valid=dates(series).notna()
    elif kind in ['currency','numeric','age']:
        values=numeric(series); valid=values.notna()
        if kind=='age': valid &= values.between(0,120)
    else: valid=pd.Series(True,index=series.index)
    return present & ~valid

def assess_quality(frame, types=None):
    types=types or infer_types(frame); cells=max(1,frame.size)
    missing=int((frame.isna() | frame.astype('string').apply(lambda s:s.str.strip().eq('').fillna(False))).sum().sum())
    duplicates=int(frame.duplicated().sum())
    issues=[]; invalid=0; formatting=0
    for item in types:
        c=item['column']; s=frame[c]; bad=int(invalid_mask(s,item['semantic_type']).sum()); invalid+=bad
        fmt=int(s.map(lambda v:isinstance(v,str) and (v!=v.strip() or (item['semantic_type']=='email' and v!=v.lower()))).sum()); formatting+=fmt
        issues.append(dict(column=c,semantic_type=item['semantic_type'],missing=int(s.isna().sum()),invalid=bad,formatting=fmt))
    completeness=1-missing/cells; validity=1-invalid/max(1,cells-missing); uniqueness=1-duplicates/max(1,len(frame)); consistency=1-formatting/cells
    return dict(rows=len(frame),missing_cells=missing,invalid_cells=invalid,duplicate_rows=duplicates,formatting_cells=formatting,
        completeness=round(100*completeness,2),validity=round(100*validity,2),uniqueness=round(100*uniqueness,2),consistency=round(100*consistency,2),
        score=round(25*(completeness+validity+uniqueness+consistency),2),issues=issues)
