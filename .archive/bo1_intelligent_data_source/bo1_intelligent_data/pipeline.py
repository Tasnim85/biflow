import argparse
import io
import zipfile
import json
import pandas as pd
from data_generator import generate_data
from agents.orchestrator_agent import OrchestratorAgent
from utils.helpers import ROOT,json_text,write_json,safe_name

def load_registry():
    path=ROOT/'outputs/cleaning/recipe_registry.json'
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError): return {}

def build_artifacts(result):
    artifacts={'dataset_profiles.json':json_text(result['profiles']),
        'quality_report_before.json':json_text(result['quality_before']),
        'cleaning_plan.json':json_text(result['plans']),'dag_execution.json':json_text(result['execution']),
        'quality_report_after.json':json_text({n:r['after'] for n,r in result['cleaning'].items()}),
        'bi_readiness.json':json_text(result['final'].get('gates',{}))}
    if result['similarity']:
        artifacts['similarity_matrix.csv']=result['similarity']['matrix'].to_csv(index=True)
        artifacts['similarity_evidence.json']=json_text({k:v for k,v in result['similarity'].items() if k!='matrix'})
    records=[{'dataset':n,**{k:v for k,v in s.items() if k!='pattern_rates'},'evidence':' | '.join(s['evidence'])} for n,types in result['semantics'].items() for s in types]
    artifacts['semantic_classification.csv']=pd.DataFrame(records).to_csv(index=False)
    for n,r in result['cleaning'].items():
        name=safe_name(n); artifacts[f'cleaned/{name}.csv']=r['cleaned'].to_csv(index=False)
        artifacts[f'cleaning/clean_{name}.py']=result['code'][n]
        artifacts[f'cleaning/audit_{name}.json']=json_text(r['audit'])
        artifacts[f'cleaning/plan_{name}.json']=json_text(result['plans'][n])
    integration=result['final'].get('integration',{})
    artifacts['integration_plan.json']=json_text({k:v for k,v in integration.items() if k!='datasets'})
    for n,df in integration.get('datasets',{}).items(): artifacts[f'integrated/{safe_name(n)}.csv']=df.to_csv(index=False)
    return artifacts

def zip_artifacts(artifacts):
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,content in artifacts.items(): archive.writestr(name,content)
    return buffer.getvalue()

def persist(result):
    artifacts=build_artifacts(result)
    for name,content in artifacts.items():
        group='similarity' if name.startswith('similarity') else 'quality' if name.startswith(('quality','semantic','dataset')) else 'integration' if name.startswith(('integrat','bi_','dag_')) else 'cleaning'
        path=ROOT/'outputs'/group/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(content,encoding='utf-8')
    # Only recipes whose plans and transformations completed become reusable.
    registry=load_registry()
    for n,r in result['cleaning'].items():
        registry[n]={'plan':result['plans'][n],'semantics':result['semantics'][n],'validation':r['validation']}
    write_json(ROOT/'outputs/cleaning/recipe_registry.json',registry)
    (ROOT/'outputs/bo1_results.zip').write_bytes(zip_artifacts(artifacts))
    return artifacts

def run_pipeline(datasets,config=None,registry=None,callback=None,persist_outputs=True):
    result=OrchestratorAgent(datasets,config,registry,callback).run()
    if persist_outputs: persist(result)
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--backend',choices=['asyncio','langgraph'],default='asyncio'); parser.add_argument('--rows',type=int,default=200)
    args=parser.parse_args()
    data=generate_data(args.rows,directory=ROOT/'data/generated')
    result=run_pipeline(data,{'orchestration_backend':args.backend},load_registry())
    print('Completed:',result['execution']['all_completed'],'Seconds:',result['execution']['elapsed_seconds'])
    print('Similarity:',[(p['left'],p['right'],p['score']) for p in result['similarity'].get('pairs',[])])
    for n,r in result['cleaning'].items(): print(n,result['quality_before'][n]['score'],'->',r['after']['score'],'BI ready:',result['final']['gates'][n]['ready_for_bi'])
