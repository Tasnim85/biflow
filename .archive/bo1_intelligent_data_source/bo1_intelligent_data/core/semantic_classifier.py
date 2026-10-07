import re
import pandas as pd
from utils.helpers import normalize_name,missing_mask

TYPES=['IDENTIFIER','PERSON_NAME','EMAIL','PHONE_NUMBER','AGE','DATE','DATETIME','LOCATION','ADDRESS','POSTAL_CODE','CURRENCY','NUMERIC','BOOLEAN','CATEGORY','TEXT','URL']
ALIASES={'client_identifier':'customer_id','client_id':'customer_id','customer_age':'age','years_old':'age',
    'email_address':'email','telephone':'phone','phone_number':'phone','location':'city','town':'city',
    'registration_date':'signup_date','registered_on':'signup_date','customer_name':'full_name','name':'full_name'}

def canonical(name):
    name=normalize_name(name); return ALIASES.get(name,name)

def parse_numeric(series):
    return pd.to_numeric(series.astype('string').str.replace(r'[$€£,\s]','',regex=True),errors='coerce').astype('Float64')

def parse_date(series):
    def parse(value):
        if pd.isna(value) or not str(value).strip(): return pd.NaT
        value=str(value).strip()
        return pd.to_datetime(value,dayfirst=bool(re.match(r'^\d{1,2}/\d{1,2}/\d{4}',value)),errors='coerce',utc=True)
    return pd.to_datetime(series.map(parse),errors='coerce',utc=True)

def normalize_phone(series):
    return series.astype('string').str.strip().str.replace(r'[\s().-]','',regex=True).str.replace(r'^00','+',regex=True)

def pattern_rates(series):
    s=series[~missing_mask(series)].astype('string').str.strip().head(500)
    if not len(s): return {x:0. for x in ['EMAIL','PHONE_NUMBER','URL','BOOLEAN','NUMERIC','DATE']}
    return {'EMAIL':float(s.str.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').mean()),
        'PHONE_NUMBER':float(normalize_phone(s).str.match(r'^\+?\d{8,15}$').mean()),
        'URL':float(s.str.match(r'^https?://[^\s.]+\.[^\s]+$').mean()),
        'BOOLEAN':float(s.str.lower().isin(['true','false','yes','no','0','1','oui','non']).mean()),
        'NUMERIC':float(parse_numeric(s).notna().mean()),
        'DATE':float(parse_date(s).notna().mean()) if s.str.contains(r'[-/:]',regex=True).mean()>.6 else 0.}

def classify_column(name,series):
    key=canonical(name); raw=normalize_name(name); rates=pattern_rates(series); values=series[~missing_mask(series)]
    rules=[(key.endswith('_id') or raw in ['id','identifier'],'IDENTIFIER','identifier name'),
        ('email' in key,'EMAIL','email name'),('phone' in key,'PHONE_NUMBER','phone alias/name'),
        (key=='age','AGE','age alias'),('postal' in key or key in ['zip','zip_code'],'POSTAL_CODE','postal name'),
        ('address' in key,'ADDRESS','address name'),('timestamp' in key or 'datetime' in key,'DATETIME','timestamp name'),
        ('date' in key or key.endswith('_on'),'DATE','date name'),
        (key in ['first_name','last_name','full_name','employee_name'],'PERSON_NAME','person name'),
        (key in ['city','country','region'],'LOCATION','location alias'),
        (key in ['amount','price','salary','revenue','cost'],'CURRENCY','monetary business name'),
        (key in ['url','website','link'],'URL','URL name'),
        (key.startswith('is_') or key in ['active','enabled'],'BOOLEAN','boolean name'),
        (key in ['department','category','payment_method','status'],'CATEGORY','categorical business name')]
    kind='TEXT'; reason='No strong name or value rule matched'; confidence=.55
    for hit,prediction,evidence in rules:
        if hit: kind=prediction; reason=evidence; confidence=.92; break
    else:
        for candidate in ['EMAIL','URL','BOOLEAN','DATE','NUMERIC']:
            if rates[candidate]>=.9: kind=candidate; reason='At least 90% of populated sample values match'; confidence=.88; break
        else:
            if len(values) and values.nunique()<=max(8,len(values)*.08): kind='CATEGORY'; reason='Low distinct-value ratio'; confidence=.72
    pattern=rates.get(kind,rates['NUMERIC'] if kind in ['AGE','CURRENCY'] else None)
    if pattern is not None: confidence=min(.99,confidence*.65+.35*pattern)
    evidence=[f'Canonical name: {key}; {reason}',f'Pandas dtype: {series.dtype}; populated values: {len(values)}; distinct: {values.nunique()}']
    if pattern is not None: evidence.append(f'{pattern:.1%} of populated sample values match the relevant pattern (up to 500 values)')
    if kind=='AGE': evidence.append('Business validation range: 0–120; integers expected')
    return {'column':str(name),'pandas_type':str(series.dtype),'semantic_type':kind,'confidence':round(confidence,3),'evidence':evidence,'pattern_rates':rates,'canonical_name':key}

def classify_dataset(frame): return [classify_column(c,frame[c]) for c in frame]
