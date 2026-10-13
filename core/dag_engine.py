import asyncio
import time
from datetime import datetime,timezone
from typing import Annotated,TypedDict,Literal
import networkx as nx
from pydantic import BaseModel,Field
from utils.helpers import summarize
from utils.logging_config import get_logger

def merge_results(left,right): return {**left,**right}
class GraphState(TypedDict):
    results:Annotated[dict,merge_results]

class TaskState(BaseModel):
    agent:str
    status:Literal['PENDING','RUNNING','COMPLETED','FAILED']='PENDING'
    dependencies:list[str]=Field(default_factory=list)
    started_at:str|None=None
    ended_at:str|None=None
    start_offset_seconds:float|None=None
    end_offset_seconds:float|None=None
    duration_seconds:float=0.
    input:dict=Field(default_factory=dict)
    output:dict=Field(default_factory=dict)
    confidence:float|None=None
    error:str|None=None
    explanation:str=''

class DagEngine:
    def __init__(self,functions,dependencies,callback=None,backend='asyncio'):
        self.functions=functions; self.dependencies=dependencies; self.callback=callback; self.backend=backend
        self.graph=nx.DiGraph(); self.graph.add_nodes_from(functions)
        for node,parents in dependencies.items():
            for parent in parents: self.graph.add_edge(parent,node)
        if set(self.graph)!=set(functions): raise ValueError('Unknown DAG dependency')
        if not nx.is_directed_acyclic_graph(self.graph): raise ValueError('Dependency cycle rejected')
        self.states={n:TaskState(agent=n,dependencies=dependencies.get(n,[]),explanation='Waits for '+', '.join(dependencies.get(n,[])) if dependencies.get(n) else 'No dependencies; ready at pipeline start.') for n in functions}
        self.events=[]; self.outputs={}; self.started=0.; self.elapsed=0.; self.logger=get_logger()

    def publish(self,node):
        snapshot={n:s.model_dump() for n,s in self.states.items()}
        self.events.append({'agent':node,'status':self.states[node].status,'offset_seconds':round(time.perf_counter()-self.started,6)})
        if self.callback: self.callback(snapshot,list(self.graph.edges),self.events.copy())

    async def invoke(self,node,results):
        task=self.states[node]
        if any(self.states[p].status=='FAILED' for p in task.dependencies):
            task.status='FAILED'; task.error='Skipped because a dependency failed'; self.publish(node); return None
        task.status='RUNNING'; task.started_at=datetime.now(timezone.utc).isoformat(); task.start_offset_seconds=time.perf_counter()-self.started
        if task.dependencies: task.input={p:summarize(results.get(p)) for p in task.dependencies}
        self.publish(node)
        start=time.perf_counter()
        try:
            value=await asyncio.to_thread(self.functions[node],{p:results[p] for p in task.dependencies})
            task.status='COMPLETED'; task.output=summarize(value)
            if isinstance(value,dict) and 'confidence' in value: task.confidence=value['confidence']
            elif isinstance(value,dict):
                predictions=[x['confidence'] for items in value.values() if isinstance(items,list) for x in items if isinstance(x,dict) and 'confidence' in x]
                if predictions: task.confidence=round(sum(predictions)/len(predictions),4)
            self.outputs[node]=value
        except Exception as error:
            value=None; task.status='FAILED'; task.error=f'{type(error).__name__}: {error}'; self.logger.error('%s failed: %s',node,task.error)
        task.duration_seconds=round(time.perf_counter()-start,6); task.ended_at=datetime.now(timezone.utc).isoformat(); task.end_offset_seconds=time.perf_counter()-self.started
        self.publish(node); return value

    async def schedule_agents(self):
        pending=set(self.functions); running={}
        while pending or running:
            for node in sorted(pending.copy()):
                if all(self.states[p].status in ['COMPLETED','FAILED'] for p in self.states[node].dependencies):
                    pending.remove(node); running[asyncio.create_task(self.invoke(node,self.outputs))]=node
            if not running:
                if pending: raise RuntimeError('DAG scheduler stalled')
                break
            done,_=await asyncio.wait(running,return_when=asyncio.FIRST_COMPLETED)
            for task in done: await task; running.pop(task)

    async def execute_langgraph(self):
        from langgraph.graph import StateGraph,START,END
        builder=StateGraph(GraphState)
        def wrap(node):
            async def execute(state):
                value=await self.invoke(node,state['results'])
                return {'results':{node:value}}
            return execute
        for node in self.functions: builder.add_node(node,wrap(node))
        for node,parents in self.dependencies.items():
            if parents: builder.add_edge(parents,node)
            else: builder.add_edge(START,node)
        for node in self.functions:
            if self.graph.out_degree(node)==0: builder.add_edge(node,END)
        compiled=builder.compile()
        await compiled.ainvoke({'results':{}},config={'recursion_limit':100})

    def run(self):
        self.started=time.perf_counter()
        self.started_at=datetime.now(timezone.utc).isoformat()
        for node in self.functions: self.publish(node)
        asyncio.run(self.execute_langgraph() if self.backend=='langgraph' else self.schedule_agents())
        elapsed=time.perf_counter()-self.started
        self.elapsed=elapsed
        return {'results':self.outputs,'execution':{'backend':self.backend,'started_at':self.started_at,'elapsed_seconds':round(elapsed,6),
            'sum_task_seconds':round(sum(s.duration_seconds for s in self.states.values()),6),
            'nodes':{n:s.model_dump() for n,s in self.states.items()},'edges':list(self.graph.edges),'events':self.events,
            'acyclic':True,'all_completed':all(s.status=='COMPLETED' for s in self.states.values()),
            'execution_order':list(nx.topological_sort(self.graph))}}
