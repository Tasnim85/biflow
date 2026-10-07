import pandas as pd
import streamlit as st
from data_generator import generate_data
from pipeline import run_pipeline,load_registry,build_artifacts,zip_artifacts,persist
from core.cleaning_engine import validate_plan,execute_plan
from utils.helpers import ROOT,load_csv,safe_name,json_text
from utils.visualization import dag_figure,similarity_figure,quality_figure,timeline_figure

st.set_page_config(page_title='BO1 · Intelligent Data',page_icon='🔗',layout='wide')
st.markdown('''<style>
.stApp {background: #f6f8fc;} section[data-testid="stSidebar"] {background: #eaf0f7;}
h1,h2,h3 {color:#15334b;} div[data-testid="stMetric"] {background:white;border:1px solid #dbe5ef;border-radius:12px;padding:15px;}
div[data-testid="stMetricValue"] {color:#087f79;} .bo1-banner {background:linear-gradient(100deg,#12354b,#087f79);color:white;padding:18px 24px;border-radius:12px;margin-bottom:20px;}
</style>''',unsafe_allow_html=True)
st.title('BO1 — Intelligent Data Understanding & Preparation')
st.caption('Similarity • Semantic Understanding • Cleaning • DAG Orchestration')
st.markdown('<div class="bo1-banner">Multimodal Business Intelligence Agent · Four connected DSO · Explainable tabular preparation</div>',unsafe_allow_html=True)

PAGES=['Overview','Data Sources','Data Profiling','Dataset Similarity — DSO 6','Semantic Classification — DSO 7','Data Quality','Cleaning & Transformation — DSO 5','DAG Orchestration — DSO 1','Final Results']
st.sidebar.header('BO1 workspace')
page=st.sidebar.radio('Navigation',PAGES)
st.sidebar.subheader('Data source')
rows=st.sidebar.slider('Synthetic customer rows',30,1000,200,10)
seed=st.sidebar.number_input('Random seed',min_value=0,value=42)
if st.sidebar.button('Generate Synthetic Data'):
    st.session_state['datasets']=generate_data(rows,int(seed),ROOT/'data/generated')
    st.session_state.pop('result',None); st.session_state.pop('artifacts',None)
    st.sidebar.success('Five datasets generated. Run the BO1 pipeline.')
uploads=st.sidebar.file_uploader('Upload CSV files',type='csv',accept_multiple_files=True,help='UTF-8 or Windows-1252; commas, semicolons, tabs or pipes. Headers must be unique. Identifiers retain leading zeros.')
if st.sidebar.button('Load uploaded CSV files',disabled=not uploads):
    data={}; errors=[]
    for file in uploads or []:
        try:
            base=safe_name(file.name); name=base; index=2
            while name in data: name=f'{base}_{index}'; index+=1
            data[name]=load_csv(file)
        except Exception as error: errors.append(f'{file.name}: {error}')
    if errors: st.sidebar.error('\n'.join(errors))
    else:
        st.session_state['datasets']=data; st.session_state.pop('result',None); st.session_state.pop('artifacts',None)
        st.sidebar.success(f'{len(data)} datasets loaded.')
st.sidebar.subheader('Configuration')
similarity_threshold=st.sidebar.slider('Similarity threshold',.5,.99,.75,.01)
quality_threshold=st.sidebar.slider('BI quality threshold',50.,100.,85.,1.)
embedding_backend=st.sidebar.selectbox('Embeddings',['Local Sentence Transformers / MiniLM','Local concept + hashing'])
backend=st.sidebar.selectbox('DAG scheduler',['asyncio','langgraph'])
llm=st.sidebar.checkbox('Enable optional LLM',value=False,help='Only after an explicit pipeline run: sends names, inferred types and aggregate quality statistics to OpenAI. Raw sample rows are excluded. Requires OPENAI_API_KEY; failures use local rules.')
st.sidebar.caption('Controls take effect on the next run. No API key is required. MiniLM never auto-downloads a model.')
datasets=st.session_state.get('datasets',{})
run=st.sidebar.button('Run BO1 Pipeline',type='primary',disabled=not datasets)
progress=st.empty()
if run:
    config={'similarity_threshold':similarity_threshold,'quality_threshold':quality_threshold,'embedding_backend':'minilm' if embedding_backend.startswith('Local Sentence') else 'local','orchestration_backend':backend,'llm_enabled':llm}
    def update(states,edges,events):
        with progress.container():
            completed=sum(s['status']=='COMPLETED' for s in states.values())
            st.progress(completed/len(states),text=f'{completed}/{len(states)} agents completed · '+events[-1]['agent']+' '+events[-1]['status'])
            st.plotly_chart(dag_figure(states,edges),width='stretch',key='live_'+str(len(events)))
    try:
        with st.spinner('Executing the dependency graph…'):
            result=run_pipeline(datasets,config,load_registry(),update)
        st.session_state['result']=result; st.session_state['artifacts']=build_artifacts(result)
        progress.empty()
        if result['execution']['all_completed']: st.success(f"BO1 completed in {result['execution']['elapsed_seconds']:.2f}s. All plans were validated before controlled execution.")
        else: st.error('Some tasks failed. Inspect the DAG execution details; partial completed outputs are available.')
    except Exception as error: progress.empty(); st.error(f'Pipeline could not run: {error}')
result=st.session_state.get('result')

def select_dataset(key): return st.selectbox('Dataset',list(datasets),key=key)

def contributions():
    st.subheader('BO1 — DSO Contribution')
    for col,title,description in zip(st.columns(4),['DSO 1 · Orchestration','DSO 6 · Similarity','DSO 7 · Semantics','DSO 5 · Cleaning'],['Coordinates dependencies and parallel agents','Finds related datasets and reusable recipes','Infers column business meaning','Generates and applies validated transformations']):
        with col: st.info(title+'\n\n'+description)

if page=='Overview':
    contributions()
    st.write('Raw data → Profiling → **Similarity ∥ Semantics** → Quality → Cleaning plan → Validation → Controlled execution → BI data')
    if not datasets: st.info('1. Generate Synthetic Data or load CSV files. 2. Run BO1 Pipeline. 3. Explore the nine pages.')
    else:
        metrics=[('Datasets',len(datasets)),('Input rows',sum(len(df) for df in datasets.values())),('Input columns',sum(len(df.columns) for df in datasets.values()))]
        if result:
            metrics.extend([('Average quality before',f"{sum(q['score'] for q in result['quality_before'].values())/max(1,len(result['quality_before'])):.1f}%"),
                ('Similar pairs',sum(p['similar'] for p in result['similarity'].get('pairs',[]))),
                ('Semantic columns',sum(len(x) for x in result['semantics'].values())),
                ('Transformation steps',sum(len(r['audit']) for r in result['cleaning'].values())),
                ('Execution time',f"{result['execution']['elapsed_seconds']:.2f}s")])
        for start in range(0,len(metrics),4):
            for col,(label,value) in zip(st.columns(4),metrics[start:start+4]): col.metric(label,value)
        if result and result['final']: st.dataframe(pd.DataFrame(result['final']['gates']).T,width='stretch')
elif page=='Data Sources':
    if datasets:
        name=select_dataset('source'); st.dataframe(datasets[name],width='stretch')
        st.download_button('Download raw CSV',datasets[name].to_csv(index=False),file_name=name+'.csv',mime='text/csv')
    else: st.info('Generate or load datasets from the sidebar.')
else:
    if not result: st.info('Run BO1 Pipeline to compute results for this page.'); st.stop()
    if page=='Data Profiling':
        if result['profiles']:
            name=select_dataset('profile'); profile=result['profiles'][name]
            cols=st.columns(4)
            for col,k in zip(cols,['rows','columns','missing_percentage','duplicate_percentage']): col.metric(k.replace('_',' ').title(),profile[k])
            st.dataframe(profile['column_profiles'],width='stretch'); st.json(profile)
    elif page=='Dataset Similarity — DSO 6':
        similarity=result['similarity']
        if not similarity: st.error('Similarity task failed. See the DAG page.'); st.stop()
        st.caption(f"Embedding backend: {similarity['backend']} · {similarity['embedding_dimensions']} dimensions · threshold {similarity['threshold']:.0%}")
        if similarity['warning']: st.warning(similarity['warning'])
        st.plotly_chart(similarity_figure(similarity['matrix']),width='stretch')
        st.caption(similarity['formula'])
        pairs=similarity['pairs']
        if pairs:
            index=st.selectbox('Inspect dataset pair',range(len(pairs)),format_func=lambda i:f"{pairs[i]['left']} ↔ {pairs[i]['right']} · {pairs[i]['score']:.1%}")
            pair=pairs[index]; st.metric('Computed similarity',f"{pair['score']:.1%}"); st.write(pair['explanation']); st.dataframe(pair['matches'],width='stretch')
            st.subheader('Most similar source per dataset')
            best=[]
            for n in datasets:
                candidates=[p for p in pairs if n in [p['left'],p['right']]]
                p=max(candidates,key=lambda p:p['score']); best.append({'dataset':n,'most_similar':p['right'] if p['left']==n else p['left'],'score':p['score'],'above_threshold':p['similar']})
            st.dataframe(best,width='stretch')
        else: st.info('Load at least two datasets for similarity comparison.')
        st.subheader('Reusable preparation recipes'); st.json(similarity['recipes'])
        st.caption('Recipes saved by a completed run become available on the next run. Only compatible mapped operations are reused and target data is revalidated.')
    elif page=='Semantic Classification — DSO 7':
        if not result['semantics']: st.error('Semantic task failed.'); st.stop()
        name=select_dataset('semantic'); semantics=result['semantics'][name]
        st.dataframe([{'column':s['column'],'Pandas type':s['pandas_type'],'semantic_type':s['semantic_type'],'confidence':f"{s['confidence']:.1%}",'evidence':' | '.join(s['evidence'])} for s in semantics],width='stretch')
        c=st.selectbox('Column reasoning',[s['column'] for s in semantics]); item=next(s for s in semantics if s['column']==c)
        st.subheader(c+' → '+item['semantic_type']); st.metric('Heuristic confidence',f"{item['confidence']:.1%}")
        for evidence in item['evidence']: st.write('• '+evidence)
        st.json(item['pattern_rates']); st.caption('Confidence measures rule strength, not calibrated prediction accuracy.')
    elif page=='Data Quality':
        if not result['quality_before']: st.error('Quality task failed.'); st.stop()
        name=select_dataset('quality'); q=result['quality_before'][name]
        for col,(label,k) in zip(st.columns(4),[('Quality score','score'),('Missing %','missing_rate'),('Duplicate %','duplicate_rate'),('Invalid %','invalid_rate')]): col.metric(label,q[k])
        st.dataframe(q['issues'],width='stretch'); st.info(q['formula']); st.json(q)
    elif page=='Cleaning & Transformation — DSO 5':
        if not result['plans']: st.error('Cleaning plan task failed.'); st.stop()
        name=select_dataset('clean'); plan=result['plans'][name]
        st.caption(plan['provider']+' · '+plan['provider_message']); st.info(plan['missing_policy'])
        st.dataframe(plan['steps'],width='stretch'); st.metric('Steps reused from saved recipes',plan['reused_steps'])
        st.code(result['code'][name],language='python')
        st.caption('The pipeline validates and executes these operations automatically. This button revalidates the displayed plan and reruns it on the original data. Generated Python text is never evaluated by the app.')
        if st.button('Validate & Execute Cleaning',type='primary'):
            try:
                checked=validate_plan(plan,datasets[name],result['semantics'][name]); executed=execute_plan(datasets[name],checked,result['semantics'][name])
                previous=result['cleaning'].get(name)
                if previous is not None and not previous['cleaned'].equals(executed['cleaned']): raise ValueError('Re-execution differs from the completed DAG output; rerun the pipeline.')
                st.success('Plan validated and executed; result matches the pipeline output.')
                st.dataframe(executed['cleaned'].head(30),width='stretch')
            except Exception as error: st.error(f'Validation/execution rejected: {error}')
        if name in result['cleaning']:
            st.subheader('Transformation audit'); st.dataframe(result['cleaning'][name]['audit'],width='stretch')
        st.download_button('Download transformation code',result['code'][name],file_name='clean_'+name+'.py')
    elif page=='DAG Orchestration — DSO 1':
        execution=result['execution']; states=execution['nodes']
        st.caption(f"Scheduler: {execution['backend']} · elapsed {execution['elapsed_seconds']:.3f}s · sum of task durations {execution['sum_task_seconds']:.3f}s")
        st.plotly_chart(dag_figure(states,execution['edges']),width='stretch')
        st.dataframe([{'agent':n,'status':s['status'],'seconds':s['duration_seconds'],'dependencies':', '.join(s['dependencies']),'error':s['error']} for n,s in states.items()],width='stretch')
        node=st.selectbox('Inspect agent state',list(states)); st.json(states[node])
        st.subheader('Measured execution timeline'); st.plotly_chart(timeline_figure(states),width='stretch')
        st.caption('Overlapping bars show actual concurrent execution. UI rendering adds overhead to elapsed time; no simulated waits or fabricated speedup.')
        with st.expander('Status transitions'): st.dataframe(execution['events'],width='stretch')
    elif page=='Final Results':
        if not result['cleaning']: st.error('No clean outputs; inspect failed DAG nodes.'); st.stop()
        name=select_dataset('final'); before=result['quality_before'][name]; after=result['cleaning'][name]['after']
        for label,q in [('Before',before),('After',after)]:
            st.subheader(label)
            for col,(title,key) in zip(st.columns(4),[('Quality score','score'),('Missing %','missing_rate'),('Duplicate %','duplicate_rate'),('Invalid %','invalid_rate')]): col.metric(title,q[key])
        st.plotly_chart(quality_figure(before,after),width='stretch')
        st.caption('Invalid values become missing; completeness can decrease. Unknown business values are preserved rather than fabricated. Outliers remain flagged for review.')
        left,right=st.columns(2)
        with left: st.write('Raw data'); st.dataframe(datasets[name].head(30),width='stretch')
        with right: st.write('Cleaned data'); st.dataframe(result['cleaning'][name]['cleaned'].head(30),width='stretch')
        st.download_button('Download cleaned_dataset.csv',result['cleaning'][name]['cleaned'].to_csv(index=False),file_name='cleaned_dataset.csv',mime='text/csv')
        final=result['final']
        if final:
            st.subheader('BI readiness'); st.json(final['gates'][name])
            st.subheader('Integration'); st.dataframe(final['integration']['relationships'],width='stretch'); st.caption(final['integration']['note'])
            integrated=final['integration']['datasets']
            if integrated:
                chosen=st.selectbox('Enriched dataset',list(integrated)); st.dataframe(integrated[chosen].head(100),width='stretch')
        st.subheader('Download outputs')
        artifacts=st.session_state.get('artifacts') or build_artifacts(result)
        st.download_button('Download complete BO1 results (ZIP)',zip_artifacts(artifacts),file_name='bo1_results.zip',mime='application/zip')
        for filename in ['dataset_profiles.json','similarity_matrix.csv','semantic_classification.csv','quality_report_before.json','cleaning_plan.json','quality_report_after.json','dag_execution.json']:
            if filename in artifacts: st.download_button(filename,artifacts[filename],file_name=filename,mime='text/csv' if filename.endswith('.csv') else 'application/json',key='download_'+filename)
