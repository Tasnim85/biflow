from concurrent.futures import ThreadPoolExecutor
from core.dag_engine import DagEngine
from core.cleaning_engine import validate_plan,execute_plan,generate_code,plan_digest
from core.integration import integrate
from core.validation_engine import readiness_gates
from utils.configuration import DEFAULT_CONFIG
from agents.profiler_agent import ProfilerAgent
from agents.semantic_agent import SemanticTypeAgent
from agents.quality_agent import DataQualityAgent
from agents.similarity_agent import SimilarityAgent
from agents.cleaning_agent import CleaningAgent

class OrchestratorAgent:
    def __init__(self,datasets,config=None,registry=None,callback=None):
        self.datasets=datasets; self.config={**DEFAULT_CONFIG,**(config or {})}
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
            'Dataset Similarity':lambda state:SimilarityAgent(config['embedding_backend'],config.get('model_path')).run(data,state['Profiling'],config['similarity_threshold'],self.registry),
            'Semantic Understanding':lambda _:self.parallel(lambda n:config.get('semantic_overrides',{}).get(n) or SemanticTypeAgent().run(data[n])),
            'Data Quality':lambda state:self.parallel(lambda n:DataQualityAgent().run(data[n],config.get('semantic_overrides',{}).get(n) or SemanticTypeAgent().run(data[n]))),
            'Cleaning Recommendations':lambda state:self.parallel(lambda n:CleaningAgent(config['llm_enabled']).generate_cleaning_plan(n,data[n],state['Profiling'][n],state['Semantic Understanding'][n],state['Data Quality'][n],state['Dataset Similarity']['recipes'],self.registry)),
            'Plan Validation':lambda state:self.parallel(lambda n:{'plan':validate_plan(config.get('plan_overrides',{}).get(n,state['Cleaning Recommendations'][n]),data[n],state['Semantic Understanding'][n]),'plan_hash':plan_digest(config.get('plan_overrides',{}).get(n,state['Cleaning Recommendations'][n])),'valid':True}),
            'Controlled Execution':lambda state:self.parallel(lambda n:execute_plan(data[n],state['Plan Validation'][n]['plan'],state['Semantic Understanding'][n])),
            'Final Validation & BI':lambda state:self.finalize(state)
        }
        dependencies={
            'Profiling':[],
            'Dataset Similarity':['Profiling'],
            'Semantic Understanding':['Profiling'],
            'Data Quality':['Profiling'],
            'Cleaning Recommendations':['Profiling','Dataset Similarity','Semantic Understanding','Data Quality'],
            'Plan Validation':['Cleaning Recommendations','Semantic Understanding'],
            'Controlled Execution':['Plan Validation','Semantic Understanding'],
            'Final Validation & BI':['Controlled Execution','Data Quality']}
        if config.get('review_only'):
            for node in ['Controlled Execution','Final Validation & BI']:
                functions.pop(node); dependencies.pop(node)
        self.engine=DagEngine(functions,dependencies,self.callback,config['orchestration_backend'])
        self.engine.states['Profiling'].input={n:{'rows':len(df),'columns':list(df.columns)} for n,df in data.items()}
        return self.engine.graph

    def finalize(self,state):
        cleaned={n:r['cleaned'] for n,r in state['Controlled Execution'].items()}
        gates=readiness_gates(state['Controlled Execution'],state['Data Quality'],self.config['quality_threshold'])
        return {'gates':gates,'integration':integrate(cleaned)}

    def run(self):
        self.build_dag(); run=self.engine.run(); state=run['results']
        return {'datasets':self.datasets,'config':self.config,'profiles':state.get('Profiling',{}),
            'similarity':state.get('Dataset Similarity',{}),'semantics':state.get('Semantic Understanding',{}),
            'quality_before':state.get('Data Quality',{}),'plans':{n:v['plan'] for n,v in state.get('Plan Validation',{}).items()},
            'cleaning':state.get('Controlled Execution',{}),'final':state.get('Final Validation & BI',{}),
            'execution':run['execution'],'code':{n:generate_code(v['plan']) for n,v in state.get('Plan Validation',{}).items()}}

    def schedule_agents(self): return self.engine.schedule_agents()
    execute_parallel_tasks=parallel
    def manage_dependencies(self): return self.engine.dependencies
    def track_state(self): return {n:s.model_dump() for n,s in self.engine.states.items()}
    def handle_errors(self): return {n:s.error for n,s in self.engine.states.items() if s.status=='FAILED'}
    def calculate_execution_time(self): return self.engine.elapsed
