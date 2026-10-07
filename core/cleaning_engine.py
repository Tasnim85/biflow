"""Allowlisted structured transformations. No exec/eval of generated code."""
import hashlib
import json
import math
from pprint import pformat
from typing import Literal
import pandas as pd
from pydantic import BaseModel,ConfigDict,Field,model_validator
from core.semantic_classifier import parse_numeric,parse_date,normalize_phone
from core.quality_engine import invalid_mask,assess_quality
from utils.helpers import missing_mask

Operation=Literal['strip','lowercase','uppercase','replace','fill_missing','convert_numeric','convert_dates','remove_duplicates','normalize_categories','validate_email','validate_phone','remove_impossible_values','validate_url','convert_boolean','normalize_phone']

class Step(BaseModel):
    model_config=ConfigDict(extra='forbid')
    operation:Operation
    column:str|None=None
    params:dict=Field(default_factory=dict)
    explanation:str
    origin:str='local_rule'

    @model_validator(mode='after')
    def check_operation(self):
        if self.operation!='remove_duplicates' and not self.column: raise ValueError('Column required')
        allowed={'replace':{'old','new'},'fill_missing':{'value'},'remove_impossible_values':{'min','max','integer'},'convert_dates':{'datetime'},'normalize_categories':{'mapping'}}.get(self.operation,set())
        if set(self.params)-allowed: raise ValueError('Unsupported operation parameters')
        if self.operation=='replace' and not {'old','new'}<=set(self.params): raise ValueError('replace needs old/new')
        if self.operation=='fill_missing' and 'value' not in self.params: raise ValueError('fill_missing needs value')
        if self.operation=='normalize_categories' and not isinstance(self.params.get('mapping',{}),dict): raise ValueError('Category mapping must be a literal dictionary')
        for value in self.params.values():
            if not isinstance(value,(str,int,float,bool,dict,type(None))): raise ValueError('Only JSON parameters allowed')
            if isinstance(value,float) and not math.isfinite(value): raise ValueError('Nonfinite parameters rejected')
        if self.operation=='remove_impossible_values':
            for key in ['min','max']:
                if key in self.params and (not isinstance(self.params[key],(int,float)) or isinstance(self.params[key],bool)): raise ValueError('Range limits must be numeric')
            if self.params.get('min',float('-inf'))>self.params.get('max',float('inf')): raise ValueError('Invalid range')
        return self

class Plan(BaseModel):
    model_config=ConfigDict(extra='forbid')
    dataset:str
    steps:list[Step]=Field(max_length=5000)
    missing_policy:str='Preserve unknown business values; explicit fill_missing is opt-in only.'
    provider:str='local_rules'
    provider_message:str='No API key required.'
    reused_steps:int=0

def plan_digest(plan):
    return hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()

def generate_plan(name,frame,semantics,quality,recipes=None,registry=None):
    steps=[]; issues={x['column']:x for x in quality['issues']}
    for item in semantics:
        c=item['column']; kind=item['semantic_type']; issue=issues[c]
        def add(op,reason,params=None): steps.append({'operation':op,'column':c,'params':params or {},'explanation':reason,'origin':'local_rule'})
        add('strip',f"Normalize surrounding spaces and blank cells in {c}; {issue['formatting']} formatting anomalies detected. Identifier case and leading zeros are retained.")
        if kind=='EMAIL': add('lowercase','Normalize email case under the demo policy.'); add('validate_email',f"Mask invalid email formats ({issue['invalid']} detected).")
        elif kind=='PHONE_NUMBER': add('normalize_phone','Remove phone presentation separators and convert international 00 prefix to +.'); add('validate_phone',f"Require 8–15 digits with optional +; {issue['invalid']} invalid phones detected. No country prefix is invented.")
        elif kind in ['DATE','DATETIME']: add('convert_dates','Parse ISO/day-first slash dates; preserve timestamp UTC where applicable; invalid values become missing.',{'datetime':kind=='DATETIME'})
        elif kind in ['NUMERIC','CURRENCY','AGE']:
            add('convert_numeric',f"Convert currency/number strings to nullable numeric values; {issue['type_inconsistent']} storage-type anomalies.")
            if kind=='AGE': add('remove_impossible_values','Age must be an integer between 0 and 120.',{'min':0,'max':120,'integer':True})
        elif kind in ['CATEGORY','LOCATION']: add('normalize_categories',f"Canonical casefolded categories; {issue['category_inconsistent']} noncanonical cells. No fuzzy merging of distinct categories.")
        elif kind=='BOOLEAN': add('convert_boolean','Map true/false, yes/no, oui/non and 1/0 to nullable booleans.')
        elif kind=='URL': add('validate_url','Mask malformed HTTP(S) URLs.')
    reused=0; registry=registry or {}
    target_types={s['column']:s['semantic_type'] for s in semantics}
    for recommendation in recipes or []:
        if recommendation['target']!=name or recommendation['source'] not in registry: continue
        recipe=registry[recommendation['source']]; source_types={x['column']:x['semantic_type'] for x in recipe.get('semantics',[])}
        for original in recipe.get('plan',{}).get('steps',[]):
            # Do not transfer business-value imputation/ranges blindly.
            if original['operation'] not in ['strip','lowercase','normalize_phone','validate_phone','validate_email','convert_numeric','convert_dates','normalize_categories','convert_boolean']: continue
            target=recommendation['mapping'].get(original.get('column'))
            if not target or source_types.get(original['column'])!=target_types.get(target): continue
            for step in steps:
                if step['column']==target and step['operation']==original['operation'] and step['params']==original.get('params',{}):
                    step['origin']='recipe:'+recommendation['source']; step['explanation']+=' Reused from a prior validated recipe with matching semantic class.'; reused+=1; break
    steps.append({'operation':'remove_duplicates','explanation':f"Remove identical normalized rows; {quality['duplicate_rows']} raw duplicates detected.",'origin':'local_rule'})
    return Plan(dataset=name,steps=steps,reused_steps=reused).model_dump()

def validate_plan(plan,frame,semantics=None):
    checked=Plan.model_validate(plan).model_dump(); types={x['column']:x['semantic_type'] for x in semantics or []}
    incompatible={'lowercase':{'IDENTIFIER'},'uppercase':{'IDENTIFIER'},'convert_numeric':{'IDENTIFIER','EMAIL','PHONE_NUMBER','POSTAL_CODE'},'convert_dates':{'IDENTIFIER','EMAIL','PHONE_NUMBER','POSTAL_CODE'},'fill_missing':{'IDENTIFIER','PERSON_NAME','EMAIL','PHONE_NUMBER'}}
    for step in checked['steps']:
        c=step['column']; op=step['operation']
        if c and c not in frame: raise ValueError(f'Unknown column: {c}')
        if types.get(c)=='IDENTIFIER' and op!='strip': raise ValueError(f'Only whitespace normalization is allowed for identifier {c}')
        if types.get(c) in incompatible.get(op,set()): raise ValueError(f'{op} would corrupt protected semantic column {c}')
    return checked

def transform(series,step):
    op=step['operation']; p=step['params']
    if op=='strip': return series.map(lambda v:v.strip() if isinstance(v,str) else v).mask(missing_mask(series))
    if op in ['lowercase','uppercase']: return getattr(series.astype('string').str,'lower' if op=='lowercase' else 'upper')()
    if op=='replace': return series.replace(p['old'],p['new'])
    if op=='fill_missing': return series.mask(missing_mask(series),p['value'])
    if op=='convert_numeric': return parse_numeric(series).mask(lambda s:~s.isna() & ~s.map(lambda x:bool(pd.notna(x) and float('-inf')<float(x)<float('inf'))))
    if op=='convert_dates':
        parsed=parse_date(series); return parsed.dt.strftime('%Y-%m-%dT%H:%M:%SZ' if p.get('datetime') else '%Y-%m-%d').astype('string')
    if op=='normalize_phone': return normalize_phone(series)
    if op=='normalize_categories': return series.astype('string').str.strip().str.casefold().replace(p.get('mapping',{}))
    if op in ['validate_email','validate_phone','validate_url']:
        kind={'validate_email':'EMAIL','validate_phone':'PHONE_NUMBER','validate_url':'URL'}[op]; return series.mask(invalid_mask(series,kind))
    if op=='convert_boolean': return series.astype('string').str.strip().str.lower().map({'true':True,'yes':True,'oui':True,'1':True,'false':False,'no':False,'non':False,'0':False}).astype('boolean')
    if op=='remove_impossible_values':
        s=parse_numeric(series); valid=s.between(p.get('min',float('-inf')),p.get('max',float('inf')))
        if p.get('integer'): valid &= s%1==0
        return s.mask(~valid)
    raise ValueError(f'Unsupported operation {op}')

def execute_plan(frame,plan,semantics):
    plan=validate_plan(plan,frame,semantics); result=frame.copy(deep=True); audit=[]; changes=[]; affected=set()
    for index,step in enumerate(plan['steps']):
        if step['operation']=='remove_duplicates':
            before=len(result); removed=result.index[result.duplicated()].tolist(); affected.update(removed)
            for row in removed: changes.append({'row':int(row),'column':'(record)','before':'Duplicate record','after':'Removed','reason':step['explanation'],'operation':step['operation']})
            result=result.drop_duplicates()
            audit.append({'step':index,'operation':step['operation'],'rows_removed':before-len(result),'explanation':step['explanation'],'origin':step['origin']}); continue
        c=step['column']; before=result[c].copy(); after=transform(before,step); result[c]=after
        changed=(before.astype('string').fillna('<missing>')!=after.astype('string').fillna('<missing>'))
        affected.update(changed.index[changed].tolist())
        for row in changed.index[changed]:
            changes.append({'row':int(row),'column':c,'before':None if pd.isna(before.loc[row]) else str(before.loc[row]),'after':None if pd.isna(after.loc[row]) else str(after.loc[row]),'reason':step['explanation'],'operation':step['operation']})
        audit.append({'step':index,'column':c,'operation':step['operation'],'changed_cells':int(changed.sum()),'missing_before':int(missing_mask(before).sum()),'missing_after':int(missing_mask(after).sum()),'explanation':step['explanation'],'origin':step['origin']})
    after=assess_quality(result,semantics)
    if len(result)>len(frame) or list(result.columns)!=list(frame.columns): raise ValueError('Cleaning violated shape invariants')
    return {'cleaned':result.reset_index(drop=True),'audit':audit,'changes':changes,'impact':{'rows_affected':len(affected),'values_transformed':sum(a.get('changed_cells',0) for a in audit),'rows_removed':len(frame)-len(result),'columns_affected':len({a['column'] for a in audit if a.get('changed_cells',0)>0})},'after':after,'validation':{'plan_valid':True,'schema_preserved':True,'row_count_not_increased':True,'plan_hash':plan_digest(plan)}}

def generate_code(plan):
    # A reviewable export; runtime dispatches validated operations, never evaluates this text.
    return '# Generated from a validated allowlisted plan. Run from this project.\nfrom core.cleaning_engine import execute_plan\n\nPLAN = '+pformat(plan,width=100,sort_dicts=False)+'\n\ndef clean(df, semantics):\n    return execute_plan(df, PLAN, semantics)["cleaned"]\n'
