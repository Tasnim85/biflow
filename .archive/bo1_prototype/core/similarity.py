from difflib import SequenceMatcher
from itertools import combinations
import numpy as np
from core.semantic_types import canonical,infer_types

def values(series): return set(series.dropna().astype(str).str.strip().str.lower())

def compare_columns(a,ca,b,cb,ta,tb):
    name=SequenceMatcher(None,canonical(ca),canonical(cb)).ratio()
    semantic=float(ta==tb)
    va,vb=values(a[ca]),values(b[cb]); overlap=len(va&vb)/max(1,len(va|vb))
    cardinality=1-abs(a[ca].nunique()/max(1,len(a))-b[cb].nunique()/max(1,len(b)))
    vector=np.array([name,semantic,overlap,cardinality]); score=float(vector@np.array([.45,.25,.2,.1]))
    return dict(left_column=ca,right_column=cb,score=round(score,4),name_similarity=round(name,3),semantic_match=bool(semantic),value_overlap=round(overlap,3),cardinality_similarity=round(cardinality,3),
        explanation=f'Canonical names {canonical(ca)} / {canonical(cb)}; types {ta} / {tb}; value Jaccard {overlap:.2f}; cardinality agreement {cardinality:.2f}')

def detect_similarity(datasets):
    results=[]
    for left,right in combinations(datasets,2):
        a,b=datasets[left],datasets[right]; ta={x['column']:x['semantic_type'] for x in infer_types(a)}; tb={x['column']:x['semantic_type'] for x in infer_types(b)}
        candidates=[compare_columns(a,ca,b,cb,ta[ca],tb[cb]) for ca in a for cb in b]
        matches=[]; used_a=set(); used_b=set()
        for m in sorted(candidates,key=lambda x:x['score'],reverse=True):
            if m['left_column'] not in used_a and m['right_column'] not in used_b:
                matches.append(m); used_a.add(m['left_column']); used_b.add(m['right_column'])
        score=sum(m['score'] for m in matches)/max(len(a.columns),len(b.columns))
        results.append(dict(left=left,right=right,score=round(score,4),matches=matches,candidates=sorted(candidates,key=lambda x:x['score'],reverse=True)))
    return sorted(results,key=lambda x:x['score'],reverse=True)
