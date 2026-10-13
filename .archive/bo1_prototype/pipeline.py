"""Headless demo and reusable orchestration entry point."""
from concurrent.futures import ThreadPoolExecutor
from data_generator import generate_data
from core.profiler import profile
from core.integration_plan import execute_integration
from agents.similarity_agent import SimilarityAgent
from agents.dag_agent import DAGAgent
from agents.cleaning_agent import CleaningAgent
from utils.data_utils import ROOT,save_json

def run_pipeline(datasets,threshold=.7,persist=True):
    names=list(datasets)
    # Independent profiling and cleaning jobs run concurrently; integration waits.
    with ThreadPoolExecutor(max_workers=4) as pool:
        profiles=dict(zip(names,pool.map(lambda name:profile(name,datasets[name]),names)))
        cleaning=dict(zip(names,pool.map(lambda name:CleaningAgent().run(datasets[name]),names)))
    similarity=SimilarityAgent().run(datasets)
    plan=DAGAgent().run(datasets,similarity,threshold)
    integrated=execute_integration({n:r['cleaned'] for n,r in cleaning.items()},plan)
    if persist:
        (ROOT/'outputs/cleaned_data').mkdir(parents=True,exist_ok=True)
        save_json(ROOT/'outputs/integration_plan.json',plan)
        save_json(ROOT/'outputs/cleaning_plan.json',{n:dict(plan=r['plan'],audit=r['audit']) for n,r in cleaning.items()})
        for name,r in cleaning.items():
            r['cleaned'].to_csv(ROOT/'outputs/cleaned_data'/f'{name}.csv',index=False)
            (ROOT/'outputs'/f'clean_{name}.py').write_text(r['code'],encoding='utf-8')
        for name,frame in integrated.items(): frame.to_csv(ROOT/'outputs'/f'{name}.csv',index=False)
    return dict(profiles=profiles,similarity=similarity,integration_plan=plan,cleaning=cleaning,integrated=integrated)

if __name__=='__main__':
    result=run_pipeline(generate_data(directory=ROOT/'data'))
    print('Similarity pairs:',[(x['left'],x['right'],x['score']) for x in result['similarity']])
    print('Relationships:',result['integration_plan']['relationships'])
    print('Integrated outputs:',{n:len(df) for n,df in result['integrated'].items()})
    for n,r in result['cleaning'].items(): print(n,r['audit']['before']['score'],'->',r['audit']['after']['score'])
