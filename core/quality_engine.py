import numpy as np
import pandas as pd
from core.semantic_classifier import classify_dataset,parse_numeric,parse_date,normalize_phone
from utils.helpers import missing_mask

def invalid_mask(series,kind):
    present=~missing_mask(series); s=series.astype('string').str.strip()
    if kind=='EMAIL': valid=s.str.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').fillna(False)
    elif kind=='PHONE_NUMBER': valid=normalize_phone(series).str.match(r'^\+?\d{8,15}$').fillna(False)
    elif kind in ['DATE','DATETIME']: valid=parse_date(series).notna()
    elif kind in ['AGE','NUMERIC','CURRENCY']:
        nums=parse_numeric(series); valid=nums.notna() & np.isfinite(nums.fillna(0).astype(float))
        if kind=='AGE': valid &= nums.between(0,120) & (nums%1==0)
    elif kind=='BOOLEAN': valid=s.str.lower().isin(['true','false','yes','no','0','1','oui','non'])
    elif kind=='URL': valid=s.str.match(r'^https?://[^\s.]+\.[^\s]+$').fillna(False)
    elif kind=='POSTAL_CODE': valid=s.str.match(r'^[A-Za-z0-9][A-Za-z0-9 -]{1,11}$').fillna(False)
    else: valid=pd.Series(True,index=series.index)
    return present & ~valid.fillna(False)

def assess_quality(frame,semantics=None):
    semantics=semantics or classify_dataset(frame); missing=invalid=formatting=types=categories=0; issues=[]
    for item in semantics:
        c=item['column']; kind=item['semantic_type']; s=frame[c]; absent=missing_mask(s); bad=invalid_mask(s,kind)
        fmt=s.map(lambda v:isinstance(v,str) and (v!=v.strip() or (kind=='EMAIL' and v!=v.lower())))
        category_bad=pd.Series(False,index=s.index)
        if kind in ['CATEGORY','LOCATION']:
            category_bad=(~absent) & s.astype('string').ne(s.astype('string').str.strip().str.casefold()).fillna(False)
        type_bad=pd.Series(False,index=s.index)
        if kind in ['NUMERIC','AGE','CURRENCY']: type_bad=(~absent) & ~s.map(lambda v:isinstance(v,(int,float,np.number)) and not isinstance(v,bool))
        elif kind=='BOOLEAN': type_bad=(~absent) & ~s.map(lambda v:isinstance(v,(bool,np.bool_)))
        outliers=0
        if kind in ['NUMERIC','CURRENCY']:
            nums=parse_numeric(s); nums=nums.mask(~np.isfinite(nums.fillna(0).astype(float))); q1,q3=nums.quantile(.25),nums.quantile(.75)
            if pd.notna(q1) and q3>q1: outliers=int(((nums<q1-1.5*(q3-q1)) | (nums>q3+1.5*(q3-q1))).sum())
        counts={'missing':int(absent.sum()),'invalid':int(bad.sum()),'formatting':int(fmt.sum()),'type_inconsistent':int(type_bad.sum()),'category_inconsistent':int(category_bad.sum()),'outliers_flagged':outliers}
        missing+=counts['missing']; invalid+=counts['invalid']; formatting+=counts['formatting']; types+=counts['type_inconsistent']; categories+=counts['category_inconsistent']
        issues.append({'column':c,'semantic_type':kind,**counts})
    cells=max(1,frame.size); populated=max(1,frame.size-missing); rows=max(1,len(frame)); duplicate=int(frame.duplicated().sum())
    components={'completeness':100*(1-missing/cells),'uniqueness':100*(1-duplicate/rows),
        'validity':100*(1-invalid/populated),'type_consistency':100*(1-types/populated),
        'categorical_consistency':100*(1-categories/populated),'format_consistency':100*(1-formatting/populated)}
    return {'rows':len(frame),'cells':frame.size,'missing_cells':missing,'duplicate_rows':duplicate,'invalid_cells':invalid,
        'formatting_cells':formatting,'type_inconsistent_cells':types,'category_inconsistent_cells':categories,
        'missing_rate':round(100*missing/cells,2),'duplicate_rate':round(100*duplicate/rows,2),'invalid_rate':round(100*invalid/populated,2),
        'type_inconsistency_rate':round(100*types/populated,2),'categorical_inconsistency_rate':round(100*categories/populated,2),
        **{k:round(v,2) for k,v in components.items()},'score':round(sum(components.values())/6,2),'issues':issues,
        'formula':'Mean of completeness, uniqueness, validity, type consistency, categorical consistency and format consistency; each component ranges 0–100. Invalid/type/category/format rates use populated cells; missing uses all cells; duplicates uses rows. Outliers are advisory, not automatically removed.'}
