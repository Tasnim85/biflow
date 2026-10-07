import copy
import re
import streamlit as st
from utils.visualization import dag_figure

NAMES={'Dataset Similarity':'Dataset Similarity','Semantic Understanding':'Semantic Understanding','Cleaning Recommendations':'Cleaning Recommendations'}
def label(name): return NAMES.get(name,name)
def display_execution(execution):
    nodes={label(n):{**s,'dependencies':[label(p) for p in s['dependencies']]} for n,s in execution['nodes'].items()}
    return nodes,[(label(a),label(b)) for a,b in execution['edges']]

PAGES=['Overview','Data Sources','Data Profiling','Dataset Similarity Detection','Automatic Semantic Classification','Data Quality','Intelligent Cleaning & Transformation','Parallel Agent Orchestration','Transformation Impact','Audit Trail','BI Readiness']
STAGES=[('Data Sources','Data Sources',None),('Profiling','Data Profiling','Profiling'),('Similarity','Dataset Similarity Detection','Dataset Similarity'),('Semantic Understanding','Automatic Semantic Classification','Semantic Understanding'),('Quality','Data Quality','Data Quality'),('Cleaning','Intelligent Cleaning & Transformation','Controlled Execution'),('Validation','BI Readiness','Final Validation & BI'),('BI-ready Data','BI Readiness','Final Validation & BI')]
EXPLANATIONS={
    'Overview':('Coordinate the preparation journey','Loaded tables','Actual independent tasks execute concurrently, then a human reviews proposed changes.','Validated tables and reports','NetworkX dependency graph + asynchronous agents'),
    'Data Sources':('Receive heterogeneous data','CSV files or reproducible synthetic data','Parse delimiters and preserve identifiers; choose the analysis scope.','Named tables and previews','Pandas, safe CSV ingestion'),
    'Data Profiling':('Understand structure and anomalies','Selected raw dataset','Count missing, unique and duplicate values; calculate numeric statistics.','Column profiles','Pandas aggregation'),
    'Dataset Similarity Detection':('Find reusable preparation knowledge','Column names, types and value patterns','Encode columns and align compatible concepts irrespective of column order.','Cosine scores, evidence and reviewed recipe candidates','Local hashing or local Sentence Transformers + cosine + Hungarian matching'),
    'Automatic Semantic Classification':('Identify business meaning','Names and observed values','Combine name signals, patterns, ranges and uniqueness. Review uncertain meanings.','Semantic classes and heuristic confidence','Rule ensemble for 16 business types'),
    'Data Quality':('Identify concrete quality problems','Data and reviewed semantic meanings','Measure completeness, uniqueness, validity and consistency. Accuracy requires external truth.','Quality scores and issue counts','Six-component quality assessment; IQR outliers are advisory'),
    'Intelligent Cleaning & Transformation':('Safely correct identified problems','Quality evidence and semantic types','Select operations, preview on a copy and explicitly approve before execution.','Clean data, generated code and change audit','Pydantic-validated operation allowlist; no arbitrary code execution'),
    'Parallel Agent Orchestration':('Reduce unnecessary waiting while respecting dependencies','Loaded data and dependency graph','Similarity, semantic and quality tasks overlap after profiling; cleaning waits for all three.','Real task statuses, inputs, outputs and durations','asyncio / LangGraph + NetworkX'),
    'Transformation Impact':('Explain exactly what changed','Original data and approved plan','Track value changes at each operation and original row positions.','Before/after values, reasons and affected rows','Controlled engine change capture'),
    'Audit Trail':('Make decisions and execution traceable','Agent events and human actions','Record timestamps, decisions, reasons, statuses and transformations.','Downloadable audit records','Append-only JSON Lines decision log + task event log'),
    'BI Readiness':('Validate downstream suitability','Approved clean data','Recalculate quality and enforce configured score, uniqueness and validity gates.','Readiness decision, reports and clean CSV files','Quality gate + many-to-one integration validation')}

def navigate(page): st.session_state['nav']=page
def pipeline_strip(result,datasets):
    for col,(title,page,node) in zip(st.columns(8),STAGES):
        status='COMPLETED' if node is None and datasets else result['execution']['nodes'].get(node,{}).get('status','PENDING') if result else 'PENDING'
        if title=='Cleaning' and result and not result['cleaning']: status='WARNING'
        if title=='BI-ready Data' and result and result.get('final',{}).get('gates') and not all(g['ready_for_bi'] for g in result['final']['gates'].values()): status='WARNING'
        symbol={'COMPLETED':'✓','RUNNING':'●','PENDING':'○','WARNING':'⚠','FAILED':'✕'}[status]
        col.button(symbol+' '+title,key='stage_'+title,on_click=navigate,args=(page,),width='stretch',help=status.title())

def explain(page):
    purpose,input_,processing,output,method=EXPLANATIONS[page]
    with st.expander('Why this step matters'):
        st.write(purpose+'.')
        st.write('**Input:** '+input_); st.write('**Processing:** '+processing)
        st.write('**Output:** '+output); st.write('**Technical method:** '+method)
        st.caption('Tables, metrics and examples below are computed from your current data. Sidebar view filters do not silently change the execution scope.')

def metrics(items):
    for start in range(0,len(items),4):
        for col,(title,value) in zip(st.columns(4),items[start:start+4]): col.metric(title,value)

def live_callback(placeholder):
    def update(states,edges,events):
        with placeholder.container():
            completed=sum(s['status']=='COMPLETED' for s in states.values())
            current=events[-1]
            st.progress(completed/len(states),text=f"{completed}/{len(states)} tasks · {label(current['agent'])} {current['status'].lower()}")
            nodes,links=display_execution({'nodes':states,'edges':edges})
            st.plotly_chart(dag_figure(nodes,links),width='stretch',key='live_'+str(len(events)))
            st.caption('Independent analyses overlap. Cleaning waits for human approval; the graph represents tasks that actually execute.')
    return update
