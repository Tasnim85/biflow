from core.semantic_types import canonical
from core.similarity import values

def integration_plan(datasets,similarities,threshold=.7):
    unions=[dict(left=p['left'],right=p['right'],score=p['score'],mapping={m['right_column']:m['left_column'] for m in p['matches'] if m['score']>=threshold},operation='candidate_union',explanation='One-to-one schema alignment; review entity identity before concatenation') for p in similarities if p['score']>=threshold]
    relationships=[]
    for child,b in datasets.items():
        for parent,a in datasets.items():
            if child==parent: continue
            for ca in a:
                if not canonical(ca).endswith('_id'): continue
                for cb in b:
                    if canonical(ca)!=canonical(cb): continue
                    va,vb=values(a[ca]),values(b[cb]); coverage=len(va&vb)/max(1,len(vb))
                    # Deduplicated parent key must be unique; child has repeated keys.
                    unique=a.drop_duplicates()[ca].is_unique and a[ca].notna().all()
                    repeated=not b.drop_duplicates()[cb].is_unique
                    if unique and repeated and coverage>=.8:
                        relationships.append(dict(parent=parent,child=child,parent_key=ca,child_key=cb,coverage=round(coverage,3),operation='left_join',explanation=f'{coverage:.0%} of child distinct keys occur in unique parent keys; inferred many-to-one relationship'))
    nodes=[]; edges=[]
    for name in datasets:
        nodes.extend([dict(id=f'raw:{name}',label=name,stage='input'),dict(id=f'profile:{name}',label=f'Profile {name}',stage='profile'),dict(id=f'clean:{name}',label=f'Clean {name}',stage='clean')])
        edges.extend([('raw:'+name,'profile:'+name),('profile:'+name,'clean:'+name)])
    nodes.append(dict(id='integrate',label='Integration plan',stage='integration'))
    edges.extend((f'clean:{n}','integrate') for n in datasets)
    nodes.append(dict(id='output',label='Integrated output',stage='output')); edges.append(('integrate','output'))
    return dict(threshold=threshold,union_candidates=unions,relationships=relationships,nodes=nodes,edges=edges,
        explanation='The DAG models processing dependencies. Business relationships are separate evidence; they do not create arbitrary source-to-source cycles.',execution_order=[n['id'] for n in nodes],warnings=['Relationships are inferred, not declared constraints. Review suggested unions and joins.'])

def execute_integration(datasets,plan):
    results={}
    for u in plan['union_candidates']:
        import pandas as pd
        left=datasets[u['left']].assign(_source_dataset=u['left'])
        right=datasets[u['right']].rename(columns=u['mapping']).assign(_source_dataset=u['right'])
        results[f"union_{u['left']}_{u['right']}"]=pd.concat([left,right],ignore_index=True,sort=False)
    for child in {r['child'] for r in plan['relationships']}:
        frame=datasets[child].copy()
        for r in [r for r in plan['relationships'] if r['child']==child]:
            parent=datasets[r['parent']].drop_duplicates().copy()
            if not parent[r['parent_key']].is_unique: raise ValueError('Parent key is not unique')
            frame=frame.merge(parent,how='left',left_on=r['child_key'],right_on=r['parent_key'],suffixes=('',f"_{r['parent']}"),validate='many_to_one')
        results[f'{child}_enriched']=frame
    return results
