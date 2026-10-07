from concurrent.futures import ThreadPoolExecutor
from core.dag_engine import DagEngine
from core.cleaning_engine import validate_plan,execute_plan,generate_code,plan_digest
from core.integration import integrate
from agents.profiler_agent import ProfilerAgent
from agents.semantic_agent import SemanticTypeAgent
from agents.quality_agent import DataQualityAgent
from agents.similarity_agent import SimilarityAgent
from agents.cleaning_agent import CleaningAgent

class OrchestratorAgent:
    def __init__(self,datasets,config=None,registry=None,callback=None):
        self.datasets=datasets; self.config={'similarity_threshold':.75,'quality_threshold':85.,'embedding_backend':'minilm','orchestration_backend':'asyncio','llm_enabled':False,**(config or {})}
        self.registry=registry or {}; self.callback=callback; self.engine=None

    def parallel(self,worker):
        names=list(self.datasets)
        with ThreadPoolExecutor(max_workers=min(4,len(names))) as pool:
            return dict(zip(names,pool.map(worker,names)))

    def build_dag(self):
        data=self.datasets; config=self.config
        if not data or any(df.empty or not df.columns.is_unique for df in data.values()): raise ValueError('Provide nonempty datasets with unique columns')
        functions={
            'Profiling':lambda _:self.parallel(lambda n:ProfilerAgent().run(n,data[n])),
            'Similarity · DSO 6':lambda state:SimilarityAgent(config['embedding_backend'],config.get('model_path')).run(data,state['Profiling'],config['similarity_threshold'],self.registry),
            'Semantics · DSO 7':lambda _:self.parallel(lambda n:SemanticTypeAgent().run(data[n])),
            'Data Quality':lambda state:self.parallel(lambda n:DataQualityAgent().run(data[n],state['Semantics · DSO 7'][n])),
            'Cleaning Plan · DSO 5':lambda state:self.parallel(lambda n:CleaningAgent(config['llm_enabled']).generate_cleaning_plan(n,data[n],state['Profiling'][n],state['Semantics · DSO 7'][n],state['Data Quality'][n],state['Similarity · DSO 6']['recipes'],self.registry)),
            'Plan Validation':lambda state:self.parallel(lambda n:{'plan':validate_plan(state['Cleaning Plan · DSO 5'][n],data[n],state['Semantics · DSO 7'][n]),'plan_hash':plan_digest(state['Cleaning Plan · DSO 5'][n]),'valid':True}),
            'Controlled Execution':lambda state:self.parallel(lambda n:execute_plan(data[n],state['Plan Validation'][n]['plan'],state['Semantics · DSO 7'][n])),
            'Final Validation & BI':lambda state:self.finalize(state)
        }
        dependencies={
            'Profiling':[],
            'Similarity · DSO 6':['Profiling'],
            'Semantics · DSO 7':['Profiling'],
            'Data Quality':['Semantics · DSO 7'],
            'Cleaning Plan · DSO 5':['Profiling','Similarity · DSO 6','Semantics · DSO 7','Data Quality'],
            'Plan Validation':['Cleaning Plan · DSO 5','Semantics · DSO 7'],
            'Controlled Execution':['Plan Validation','Semantics · DSO 7'],
            'Final Validation & BI':['Controlled Execution','Data Quality']}
        self.engine=DagEngine(functions,dependencies,self.callback,config['orchestration_backend'])
        self.engine.states['Profiling'].input={n:{'rows':len(df),'columns':list(df.columns)} for n,df in data.items()}
        return self.engine.graph

    def finalize(self,state):
        cleaned={n:r['cleaned'] for n,r in state['Controlled Execution'].items()}
        gates={n:{'score':r['after']['score'],'threshold':self.config['quality_threshold'],
            'ready_for_bi':r['after']['score']>=self.config['quality_threshold'] and r['after']['invalid_cells']==0 and r['after']['duplicate_rows']==0,
            'remaining_missing':r['after']['missing_cells'],'score_delta':round(r['after']['score']-state['Data Quality'][n]['score'],2),
            'meaning':'Readiness is a configured demo quality gate, not a guarantee of business correctness. Missing values are disclosed.'} for n,r in state['Controlled Execution'].items()}
        return {'gates':gates,'integration':integrate(cleaned)}

    def run(self):
        self.build_dag(); run=self.engine.run(); state=run['results']
        return {'datasets':self.datasets,'config':self.config,'profiles':state.get('Profiling',{}),
            'similarity':state.get('Similarity · DSO 6',{}),'semantics':state.get('Semantics · DSO 7',{}),
            'quality_before':state.get('Data Quality',{}),'plans':state.get('Cleaning Plan · DSO 5',{}),
            'cleaning':state.get('Controlled Execution',{}),'final':state.get('Final Validation & BI',{}),
            'execution':run['execution'],'code':{n:generate_code(p) for n,p in state.get('Cleaning Plan · DSO 5',{}).items()}}

    def schedule_agents(self): return self.engine.schedule_agents()
    execute_parallel_tasks=parallel
    def manage_dependencies(self): return self.engine.dependencies
    def track_state(self): return {n:s.model_dump() for n,s in self.engine.states.items()}
    def handle_errors(self): return {n:s.error for n,s in self.engine.states.items() if s.status=='FAILED'}
    def calculate_execution_time(self): return self.engine.elapsed
