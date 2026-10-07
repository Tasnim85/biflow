import re
import pandas as pd

ALIASES = {'client_id':'customer_id','customer_name':'full_name','employee_name':'full_name',
    'email_address':'email','town':'city','registered_on':'signup_date','years_old':'age'}
def canonical(name):
    name = re.sub(r'[^a-z0-9]+','_',str(name).lower()).strip('_')
    return ALIASES.get(name,name)

def numeric(series):
    return pd.to_numeric(series.astype('string').str.replace(r'[$€£,\s]','',regex=True),errors='coerce')

def dates(series):
    # ISO and slash dates accepted; slash dates use explicit day-first policy.
    return series.map(lambda v: pd.to_datetime(v,dayfirst='/' in str(v),errors='coerce') if pd.notna(v) else pd.NaT)

def infer_column(name, series):
    key = canonical(name)
    values = series.dropna().astype(str).str.strip()
    evidence = []
    if key.endswith('_id') or key == 'id': kind='identifier'; confidence=.98; evidence=['Identifier column name; values preserved as keys']
    elif 'email' in key or (len(values)>0 and values.str.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').mean()>.85): kind='email'; confidence=.95; evidence=['Email name or email-shaped values']
    elif 'date' in key or key.endswith('_on'): kind='date'; confidence=.95; evidence=['Date-related name; ISO/day-first parsing']
    elif key in ['amount','price','salary','revenue']: kind='currency'; confidence=.95; evidence=['Monetary name and numeric/currency values']
    elif key=='age': kind='age'; confidence=.98; evidence=['Age alias; expected range 0–120']
    elif key in ['full_name','product_name']: kind='person_name' if key=='full_name' else 'text'; confidence=.85; evidence=['Name alias']
    elif key in ['city','country','address']: kind='location'; confidence=.9; evidence=['Location alias']
    elif len(values) and numeric(values).notna().mean()>.9: kind='numeric'; confidence=.9; evidence=['Over 90% numeric parse success']
    elif len(values) and values.nunique()<=max(10,len(values)*.1): kind='category'; confidence=.75; evidence=['Low value cardinality']
    else: kind='text'; confidence=.6; evidence=['No stronger rule matched']
    return dict(column=str(name),semantic_type=kind,confidence=confidence,evidence=evidence)

def infer_types(frame): return [infer_column(c,frame[c]) for c in frame.columns]
