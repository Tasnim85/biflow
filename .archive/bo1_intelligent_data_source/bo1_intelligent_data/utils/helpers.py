import csv
import io
import json
import re
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def missing_mask(series):
    return series.isna() | series.astype('string').str.strip().eq('').fillna(False)

def normalize_name(value):
    return re.sub(r'[^a-z0-9]+','_',str(value).lower()).strip('_')

def safe_name(value):
    name=normalize_name(Path(str(value)).stem)
    return name or 'dataset'

def load_csv(source):
    raw=source.getvalue() if hasattr(source,'getvalue') else Path(source).read_bytes()
    try: text=raw.decode('utf-8-sig')
    except UnicodeDecodeError: text=raw.decode('cp1252')
    try: delimiter=csv.Sniffer().sniff(text[:8192],delimiters=',;\t|').delimiter
    except csv.Error: delimiter=','
    header=next(csv.reader(io.StringIO(text),delimiter=delimiter),[])
    if not header or any(not h.strip() for h in header) or len(set(header))!=len(header):
        raise ValueError('CSV header must contain distinct, nonempty column names.')
    frame=pd.read_csv(io.StringIO(text),sep=delimiter,dtype='string')
    if frame.empty: raise ValueError('CSV needs at least one data row.')
    return frame

def json_text(value): return json.dumps(value,indent=2,ensure_ascii=False,default=str,allow_nan=False)

def write_json(path,value):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json_text(value),encoding='utf-8')

def summarize(value):
    if isinstance(value,pd.DataFrame): return {'rows':len(value),'columns':len(value.columns)}
    if isinstance(value,dict): return {str(k):summarize(v) for k,v in list(value.items())[:12]}
    if isinstance(value,list): return {'items':len(value)}
    if isinstance(value,(int,float,bool,type(None))): return value
    return str(value)[:180]
