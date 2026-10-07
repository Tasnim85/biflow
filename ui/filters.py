import pandas as pd
import streamlit as st

DEFAULTS={'filter_dataset':'All','filter_quality':(0,100),'filter_confidence':(0,100),'filter_severity':'All','filter_status':'All','filter_semantic':'All','filter_issue':'All','filter_operation':'All','filter_search':''}
def reset_filters():
    for k,v in DEFAULTS.items(): st.session_state[k]=v
    st.session_state.pop('filter_date',None)

def global_filters(datasets,result):
    with st.sidebar.expander('Global view filters',expanded=False):
        if st.session_state.get('filter_dataset','All') not in ['All',*datasets]: st.session_state['filter_dataset']='All'
        st.selectbox('Dataset view',['All',*datasets],key='filter_dataset')
        st.slider('Quality range',0,100,(0,100),key='filter_quality')
        st.slider('Confidence range',0,100,(0,100),key='filter_confidence')
        st.selectbox('Severity',['All','Critical','High','Medium','Low'],key='filter_severity')
        st.selectbox('Status',['All','Completed','Pending','Running','Warning','Failed','Approved','Rejected','Modified'],key='filter_status')
        kinds=sorted({s['semantic_type'] for items in (result or {}).get('semantics',{}).values() for s in items})
        if st.session_state.get('filter_semantic','All') not in ['All',*kinds]: st.session_state['filter_semantic']='All'
        st.selectbox('Semantic type',['All',*kinds],key='filter_semantic')
        st.selectbox('Issue type',['All','Missing','Duplicate','Invalid format','Inconsistent value','Type problem','Outlier','Formatting'],key='filter_issue')
        operations=sorted({s['operation'] for p in (result or {}).get('plans',{}).values() for s in p['steps']})
        if st.session_state.get('filter_operation','All') not in ['All',*operations]: st.session_state['filter_operation']='All'
        st.selectbox('Transformation type',['All',*operations],key='filter_operation')
        st.text_input('Search visible records',key='filter_search')
        st.button('Reset Filters',on_click=reset_filters)
        st.caption('Applicable view filters affect tables and their charts. Analysis uses the explicitly selected datasets. Date filtering is available in Data Sources when a date column exists.')

def names(datasets,result=None):
    selected=st.session_state.get('filter_dataset','All')
    out=[n for n in datasets if selected=='All' or selected==n]
    lo,hi=st.session_state.get('filter_quality',(0,100))
    if result:
        out=[n for n in out if n not in result['quality_before'] or lo<=result['cleaning'].get(n,{}).get('after',result['quality_before'][n])['score']<=hi]
    return out

def table_filter(frame):
    df=frame.copy()
    for key,col in [('filter_dataset','dataset'),('filter_severity','severity'),('filter_status','status'),('filter_semantic','semantic_type'),('filter_issue','issue_type'),('filter_operation','operation')]:
        value=st.session_state.get(key,'All')
        if value!='All' and col in df: df=df[df[col].astype(str).str.casefold()==value.casefold()]
    if 'confidence' in df:
        lo,hi=st.session_state.get('filter_confidence',(0,100)); df=df[df.confidence.between(lo/100,hi/100)]
    search=st.session_state.get('filter_search','').strip()
    if search and not df.empty: df=df[df.astype(str).apply(lambda s:s.str.contains(search,case=False,regex=False)).any(axis=1)]
    return df
