from pathlib import Path
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]

def load_csv(source):
    frame=pd.read_csv(source,dtype='string')
    if frame.empty or not len(frame.columns): raise ValueError('CSV must contain a header and at least one data row')
    if not frame.columns.is_unique: raise ValueError('Column names must be unique')
    return frame

def save_json(path,data):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
