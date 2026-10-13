from core.semantic_classifier import canonical
import pandas as pd

def integrate(cleaned):
    relationships=[]; outputs={}
    for child,b in cleaned.items():
        for parent,a in cleaned.items():
            if parent==child: continue
            for ca in a:
                if not canonical(ca).endswith('_id') or a[ca].isna().any() or not a[ca].is_unique: continue
                for cb in b:
                    if canonical(cb)!=canonical(ca) or b[cb].is_unique: continue
                    av=set(a[ca].dropna().astype(str)); bv=set(b[cb].dropna().astype(str)); coverage=len(av&bv)/max(1,len(bv))
                    if coverage>=.8: relationships.append({'parent':parent,'child':child,'parent_key':ca,'child_key':cb,'coverage':round(coverage,4),'reason':'Unique parent key, repeated child key and at least 80% distinct-key coverage.'})
    for child in {r['child'] for r in relationships}:
        frame=cleaned[child].copy()
        for relation in [r for r in relationships if r['child']==child]:
            a=cleaned[relation['parent']]; ca=relation['parent_key']; cb=relation['child_key']
            parent=a.rename(columns={c:f"{relation['parent']}__{c}" for c in a})
            # Nullable string keys on both sides avoid incompatible inferred storage types.
            frame[cb]=frame[cb].astype('string'); parent[f"{relation['parent']}__{ca}"]=parent[f"{relation['parent']}__{ca}"].astype('string')
            frame=frame.merge(parent,how='left',left_on=cb,right_on=f"{relation['parent']}__{ca}",validate='many_to_one')
        outputs[child+'_enriched']=frame
    return {'relationships':relationships,'datasets':outputs,'note':'Inferred joins are exploratory. No entity merging or invented values. Many-to-one validation prevents row multiplication.'}
