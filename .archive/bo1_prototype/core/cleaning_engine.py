import pandas as pd
from core.semantic_types import infer_types,numeric,dates
from core.quality import invalid_mask,assess_quality
from core.models import CleaningPlan

def make_plan(frame):
    types=infer_types(frame)
    steps=[dict(column=x['column'],semantic_type=x['semantic_type'],operation='normalize_and_validate',explanation='Trim whitespace; lowercase emails; parse dates/currency; replace invalid values with missing. Preserve identifiers and existing missing values.') for x in types]
    steps.append(dict(operation='drop_duplicates',explanation='Remove identical rows after normalization. No unsupported imputation of identities or business facts.'))
    return CleaningPlan(types=types,steps=steps,missing_policy='Preserve missing values for explicit downstream handling').model_dump()

def apply_plan(frame,plan):
    plan=CleaningPlan.model_validate(plan).model_dump()
    result=frame.copy(deep=True); audit=[]
    for item in plan['types']:
        c=item['column']; kind=item['semantic_type']; before=result[c].copy()
        s=before.map(lambda v:v.strip() if isinstance(v,str) else v).replace('',pd.NA)
        if kind=='email': s=s.astype('string').str.lower(); s=s.mask(invalid_mask(s,kind))
        elif kind=='date': s=dates(s).dt.strftime('%Y-%m-%d')
        elif kind in ['currency','numeric','age']:
            s=numeric(s).astype('Float64')
            if kind=='age': s=s.mask(~s.between(0,120))
        result[c]=s
        changed=int((before.astype('string').fillna('<NA>')!=s.astype('string').fillna('<NA>')).sum())
        audit.append(dict(column=c,changed_cells=changed,new_missing=int(s.isna().sum()-before.isna().sum())))
    count=len(result); result=result.drop_duplicates().reset_index(drop=True)
    return result,dict(columns=audit,duplicates_removed=count-len(result),before=assess_quality(frame,plan['types']),after=assess_quality(result,plan['types']))

def generate_code(plan):
    # Executable code uses a fixed trusted engine and a literal structured plan.
    return 'from core.cleaning_engine import apply_plan\n\nPLAN = '+repr(plan)+'\n\ndef clean(df):\n    return apply_plan(df, PLAN)[0]\n'

def execute_code(frame,code):
    namespace={}
    exec(compile(code,'generated_cleaning.py','exec'),namespace)
    return namespace['clean'](frame.copy(deep=True))
