import io
import json
import zipfile
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from data_generator import generate_data
from pipeline import run_pipeline
from core.llm import suggest
from utils.data_utils import load_csv,ROOT
from utils.visualization import dag_figure,similarity_figure

st.set_page_config(page_title='Multimodal BI · BO1',page_icon='🔗',layout='wide')
st.title('Multimodal Business Intelligence Agent')
st.caption('BO1 · Intelligent data preparation and integration · Functional tabular prototype')
st.sidebar.header('Experiment settings')
rows=st.sidebar.slider('Synthetic customer rows',30,1000,120,30)
seed=st.sidebar.number_input('Random seed',min_value=0,value=42)
threshold=st.sidebar.slider('Union similarity threshold',.5,.95,.7,.01)
uploaded=st.sidebar.file_uploader('Upload heterogeneous CSV files',type='csv',accept_multiple_files=True)
remote=st.sidebar.checkbox('Request optional LLM advice',value=False,help='Explicitly sends column names, inferred types and aggregate quality metrics to OpenAI. Raw samples are excluded. Set OPENAI_API_KEY in the process environment.')
st.sidebar.info('Default mode runs locally without API keys or model downloads.')
if st.sidebar.button('Generate demo and run both DSO',type='primary'):
    with st.spinner('Generating datasets and executing agents…'):
        data=generate_data(rows,int(seed),ROOT/'data')
        st.session_state['data']=data; st.session_state['results']=run_pipeline(data,threshold)
if st.sidebar.button('Run uploaded CSV files',disabled=not uploaded):
    data={}; errors=[]
    for index,file in enumerate(uploaded or []):
        try:
            name=Path(file.name).stem
            if name in data: name=f'{name}_{index}'
            data[name]=load_csv(file)
        except Exception as error: errors.append(f'{file.name}: {error}')
    if errors: st.error('\n'.join(errors))
    elif data:
        try:
            with st.spinner('Profiling, matching and cleaning…'):
                st.session_state['data']=data; st.session_state['results']=run_pipeline(data,threshold)
        except Exception as error: st.error(f'Processing failed: {error}')
if 'results' not in st.session_state:
    st.info('Generate the demo or upload CSVs and run the agents to see computed results.')
    st.stop()
data=st.session_state['data']; result=st.session_state['results']
a,b,c,d=st.columns(4)
a.metric('Datasets',len(data)); b.metric('Input rows',sum(len(df) for df in data.values()))
c.metric('Candidate relationships',len(result['integration_plan']['relationships']))
d.metric('Cleaned quality',f"{sum(r['audit']['after']['score'] for r in result['cleaning'].values())/len(data):.1f}%")
tabs=st.tabs(['Input & profiling','DSO 1 · Similarity + DAG','DSO 2 · Semantic cleaning','Integrated results & exports'])
with tabs[0]:
    name=st.selectbox('Inspect input dataset',list(data)); st.dataframe(data[name],width='stretch')
    st.dataframe(result['profiles'][name]['column_profiles'],width='stretch')
    st.json(result['profiles'][name]['quality'])
with tabs[1]:
    st.subheader('Dataset similarity'); st.plotly_chart(similarity_figure(data,result['similarity']),width='stretch')
    pairs=result['similarity']
    if pairs:
        index=st.selectbox('Column alignment evidence',range(len(pairs)),format_func=lambda i:f"{pairs[i]['left']} ↔ {pairs[i]['right']} · {pairs[i]['score']:.3f}")
        st.dataframe(pairs[index]['matches'],width='stretch')
        with st.expander('All candidate column comparisons'): st.dataframe(pairs[index]['candidates'])
    plan=result['integration_plan']; st.subheader('Processing dependency DAG'); st.plotly_chart(dag_figure(plan),width='stretch')
    st.caption(plan['explanation']); st.subheader('Inferred key relationships'); st.dataframe(plan['relationships'])
    st.subheader('Suggested unions'); st.json(plan['union_candidates'])
    with st.expander('Full integration plan'): st.json(plan)
with tabs[2]:
    name=st.selectbox('Dataset to clean',list(data),key='clean_dataset'); r=result['cleaning'][name]
    st.dataframe(r['plan']['types'],width='stretch')
    metrics=['completeness','validity','uniqueness','consistency','score']
    fig=go.Figure()
    for stage in ['before','after']: fig.add_bar(name=stage.title(),x=metrics,y=[r['audit'][stage][m] for m in metrics])
    fig.update_layout(barmode='group',yaxis=dict(range=[0,100],title='Percent')); st.plotly_chart(fig,width='stretch')
    st.caption('Invalid values become missing: validity can rise while completeness falls. Missing values are preserved; no fabricated business data.')
    left,right=st.columns(2)
    with left: st.write('Before'); st.dataframe(data[name].head(30))
    with right: st.write('After'); st.dataframe(r['cleaned'].head(30))
    st.subheader('Transformation explanations'); st.json(r['plan']['steps']); st.json(r['audit']['columns'])
    st.subheader('Generated and executed Python'); st.code(r['code'],language='python')
    st.download_button('Download executable cleaning code',r['code'],file_name=f'clean_{name}.py')
    if remote and st.button('Request LLM suggestions for this dataset'):
        with st.spinner('Requesting optional advice…'): st.session_state['advice']=suggest(result['profiles'][name],True)
    if 'advice' in st.session_state: st.json(st.session_state['advice'])
with tabs[3]:
    if result['integrated']:
        name=st.selectbox('Executed integration output',list(result['integrated'])); st.dataframe(result['integrated'][name],width='stretch')
        st.caption('Unions preserve source lineage. Enrichment joins enforce many-to-one cardinality to prevent row multiplication.')
    else: st.info('No unions or joins met the current evidence thresholds.')
    buffer=io.BytesIO()
    with zipfile.ZipFile(buffer,'w',zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('integration_plan.json',json.dumps(result['integration_plan'],indent=2))
        archive.writestr('cleaning_plan.json',json.dumps({n:dict(plan=r['plan'],audit=r['audit']) for n,r in result['cleaning'].items()},indent=2))
        for n,r in result['cleaning'].items():
            archive.writestr(f'cleaned_data/{n}.csv',r['cleaned'].to_csv(index=False)); archive.writestr(f'clean_{n}.py',r['code'])
        for n,df in result['integrated'].items(): archive.writestr(f'integrated/{n}.csv',df.to_csv(index=False))
    st.download_button('Download all results (ZIP)',buffer.getvalue(),file_name='bo1_results.zip',mime='application/zip')
    st.caption('Plans, generated code, cleaned CSVs and integrated CSVs are also saved in outputs/.')
