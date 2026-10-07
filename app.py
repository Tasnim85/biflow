"""Explainable preparation workspace with explicit human approval."""
import copy
import json
import pandas as pd
import streamlit as st
from data_generator import generate_data
from pipeline import run_pipeline,load_registry,build_artifacts,zip_artifacts,execute_reviewed
from core.cleaning_engine import validate_plan,execute_plan,generate_code,plan_digest
from core.profiling import profile_dataset
from core.quality_engine import assess_quality
from core.semantic_classifier import TYPES,parse_date
from ui.components import PAGES,pipeline_strip,explain,metrics,live_callback,display_execution
from ui.filters import global_filters,names,table_filter
from ui.audit import record,events
from ui.dashboard import mean_quality,issue_rows
from utils.helpers import ROOT,load_csv,safe_name,json_text
from utils.visualization import dag_figure,similarity_figure,quality_figure,timeline_figure

st.set_page_config(page_title='Intelligent Data Preparation & Integration',page_icon='◈',layout='wide')
st.markdown('''<style>
.stApp{background:#f5f7fb} section[data-testid="stSidebar"]{background:#edf2f7}
h1,h2,h3{color:#14354b} div[data-testid="stMetric"]{background:white;border:1px solid #dce5ee;border-radius:12px;padding:16px}
div[data-testid="stMetricValue"]{color:#087f79} .hero{background:#15394c;color:#d9edf4;padding:14px 22px;border-radius:12px;margin-bottom:16px}
.block-container{padding-top:2rem}
</style>''',unsafe_allow_html=True)
st.title('Intelligent Data Preparation & Integration')
st.caption('From heterogeneous raw data to reliable BI-ready data')
st.markdown('<div class="hero">MULTIMODAL BUSINESS INTELLIGENCE AGENT &nbsp; / &nbsp; Explainable preparation workspace</div>',unsafe_allow_html=True)
if 'datasets' not in st.session_state: st.session_state.datasets=generate_data(500,42,balanced=True)
st.session_state.setdefault('nav','Overview')

def invalidate():
    for k in ['result','preview','reviewed_plans','analysis','semantic_overrides']: st.session_state.pop(k,None)
    for k in list(st.session_state):
        if k.startswith(('plan_editor_','plan_json_','scope')): st.session_state.pop(k,None)

st.sidebar.header('Preparation workspace')
page=st.sidebar.radio('Navigation',PAGES,key='nav')
with st.sidebar.expander('Demo & uploads',expanded=True):
    rows=st.selectbox('Rows per demo dataset',[100,500,1000,5000],index=1)
    seed=st.number_input('Random seed',min_value=0,value=42)
    if st.button('Generate Demo Data',key='generate'):
        invalidate(); st.session_state.datasets=generate_data(rows,int(seed),ROOT/'data/generated',balanced=True)
        record('Data Sources','Generate demo data',result=f'{rows} base rows per dataset'); st.rerun()
    uploads=st.file_uploader('Upload multiple CSV files',type='csv',accept_multiple_files=True)
    if st.button('Load uploaded CSV files',disabled=not uploads):
        loaded={}; errors=[]
        for file in uploads or []:
            try:
                name=safe_name(file.name); base=name; i=2
                while name in loaded or name in st.session_state.datasets: name=f'{base}_{i}'; i+=1
                loaded[name]=load_csv(file)
            except Exception as error: errors.append(f'{file.name}: {error}')
        if loaded:
            invalidate(); st.session_state.datasets.update(loaded); record('Data Sources','Upload CSV',result=', '.join(loaded))
        for error in errors: st.error(error)
        if loaded and not errors: st.rerun()
datasets=st.session_state.datasets
scope=st.sidebar.multiselect('Datasets to analyze',list(datasets),default=list(datasets),key='scope')
with st.sidebar.expander('Engine configuration'):
    threshold=st.slider('Similarity threshold %',0,100,75)
    quality_gate=st.slider('BI quality threshold %',50,100,85)
    embedding=st.selectbox('Embedding engine',['Local concept + hashing','Local Sentence Transformers / MiniLM'])
    backend=st.selectbox('DAG scheduler',['asyncio','langgraph'])
    llm=st.checkbox('Enable optional LLM',help='On analysis, sends names, types and aggregate statistics to OpenAI. No sample rows. Requires OPENAI_API_KEY; local fallback remains available.')
    st.caption('No API key needed. Local embeddings and confidence are heuristic. No implicit model downloads.')
run=st.sidebar.button('Analyze selected datasets',type='primary',disabled=not scope,key='analyze')
if page=='Overview':
    st.info('Analyze → review meanings and operations → preview → approve → validate. Raw data is preserved.')
    run=st.button('Launch Demonstration',type='primary',disabled=not scope) or run
progress=st.empty()
if run:
    config={'similarity_threshold':threshold/100,'quality_threshold':quality_gate,'embedding_backend':'minilm' if embedding.startswith('Local Sentence') else 'local','orchestration_backend':backend,'llm_enabled':llm,'review_only':True,'semantic_overrides':copy.deepcopy(st.session_state.get('semantic_overrides',{}))}
    try:
        with st.spinner('Profiling, comparing and understanding your data…'):
            r=run_pipeline({n:datasets[n] for n in scope},config,load_registry(),live_callback(progress),persist_outputs=False)
        st.session_state.result=r; st.session_state.analysis=r; st.session_state.reviewed_plans=copy.deepcopy(r['plans']); st.session_state.pop('preview',None)
        for k in list(st.session_state):
            if k.startswith(('plan_editor_','plan_json_')): st.session_state.pop(k,None)
        record('Orchestration','Analyze selected datasets',result=f'{len(scope)} datasets; awaiting approval')
        if r['execution']['all_completed']: st.success('Analysis complete. Review and preview the cleaning plan, then approve execution.')
        else: st.warning('Some components failed. Inspect the DAG; completed analysis remains available.')
    except Exception as error: st.error(f'Analysis failed: {error}')
    finally: progress.empty()
result=st.session_state.get('result')
global_filters(datasets,result); pipeline_strip(result,datasets)
st.subheader(page); explain(page)

def table(data):
    frame=data if isinstance(data,pd.DataFrame) else pd.DataFrame(data)
    filtered=table_filter(frame); st.dataframe(filtered,width='stretch',hide_index=True); return filtered

def choose(key,source=None):
    available=names(source if source is not None else (result['datasets'] if result else datasets),result)
    if not available: st.info('No datasets match. Reset Filters to see all data.'); st.stop()
    if st.session_state.get(key) not in available: st.session_state[key]=available[0]
    return st.selectbox('Dataset',available,key=key)

def impact(name,cleaned):
    before=result['quality_before'][name]; after=cleaned['after']
    metrics([('Quality before',f"{before['score']:.1f}%"),('Quality after',f"{after['score']:.1f}%"),('Quality improvement',f"{after['score']-before['score']:+.1f} pp"),('Rows removed',cleaned['impact']['rows_removed']),('Values transformed',cleaned['impact']['values_transformed']),('Rows affected',cleaned['impact']['rows_affected']),('Columns affected',cleaned['impact']['columns_affected']),('Operations applied',len(cleaned['audit']))])
    st.plotly_chart(quality_figure(before,after),width='stretch')
    table([{'metric':k,'before':before[k],'after':after[k]} for k in ['missing_rate','duplicate_rate','invalid_rate','categorical_inconsistency_rate']])

if page=='Overview':
    visible=names(datasets,result)
    metrics([('Datasets loaded',len(visible)),('Rows loaded',sum(len(datasets[n]) for n in visible)),('Columns loaded',sum(len(datasets[n].columns) for n in visible))])
    if result:
        active=[n for n in visible if n in result['datasets']]; qs={n:result['quality_before'][n] for n in active if n in result['quality_before']}; after={n:r['after'] for n,r in result['cleaning'].items() if n in active}
        metrics([('Datasets analyzed',len(qs)),('Rows processed',sum(len(result['datasets'][n]) for n in active)),('Similar datasets found',len({n for p in result['similarity'].get('pairs',[]) if p['similar'] for n in (p['left'],p['right']) if n in active})),('Semantic classifications',sum(len(result['semantics'].get(n,[])) for n in active)),('Quality issues detected',sum(len(issue_rows(n,q)) for n,q in qs.items())),('Quality before',f'{mean_quality(qs):.1f}%' if qs else '—'),('Final quality score',f'{mean_quality(after):.1f}%' if after else 'Awaiting approval'),('Cleaning transformations',sum(len(r['audit']) for n,r in result['cleaning'].items() if n in active)),('Total execution time',f"{result['execution']['elapsed_seconds']:.3f} s")])
        table([{'dataset':n,'quality_before':q['score'],'quality_after':after.get(n,{}).get('score'),'status':'Completed' if n in after else 'Pending'} for n,q in qs.items()])
    for col,title,text in zip(st.columns(4),['Parallel Agent Orchestration with a DAG','Dataset Similarity Detection with Embeddings','Automatic Semantic Classification of Columns','LLM-generated Cleaning and Transformation Code'],['Coordinate independent tasks and dependencies.','Find compatible sources and review reusable knowledge.','Understand business meaning with evidence and confidence.','Review generated code from approved operations; local rules work without an API key.']):
        with col: st.markdown('**'+title+'**'); st.caption(text)
elif page=='Data Sources':
    catalog=[]
    for n in names(datasets,result):
        df=datasets[n]; p=profile_dataset(n,df); q=result['quality_before'].get(n) if result else None
        catalog.append({'dataset':n,'rows':len(df),'columns':len(df.columns),'size_KB':round(df.memory_usage(deep=True).sum()/1024,1),'missing_%':p['missing_percentage'],'duplicate_%':p['duplicate_percentage'],'status':'Completed' if q else 'Pending','quality':q['score'] if q else assess_quality(df)['score']})
    maximum=max([r['rows'] for r in catalog]+[1]); bounds=st.slider('Row count range',0,maximum,(0,maximum))
    table([r for r in catalog if bounds[0]<=r['rows']<=bounds[1] and st.session_state.filter_quality[0]<=r['quality']<=st.session_state.filter_quality[1]])
    name=choose('source',datasets); frame=datasets[name]
    dates=[c for c in frame if 'date' in c.lower() or 'time' in c.lower()]
    if dates:
        date_column=st.selectbox('Date column',['All rows',*dates])
        if date_column!='All rows':
            parsed=parse_date(frame[date_column]); valid=parsed.dropna()
            if not valid.empty:
                limits=st.date_input('Date range',(valid.min().date(),valid.max().date()),key='filter_date')
                if isinstance(limits,(tuple,list)) and len(limits)==2: frame=frame[parsed.dt.date.between(*limits)]
    table(frame); st.download_button('Download raw dataset',datasets[name].to_csv(index=False),file_name=name+'.csv')
    if st.button('Remove dataset'):
        record('Data Sources','Remove dataset',name); invalidate(); del datasets[name]; st.rerun()
else:
    if not result: st.info('Analyze selected datasets or Launch Demonstration to calculate results.'); st.stop()
    if page=='Data Profiling':
        name=choose('profile'); p=result['profiles'].get(name)
        if not p: st.warning('Profiling unavailable. Inspect orchestration errors.'); st.stop()
        metrics([(k.replace('_',' ').title(),p[k]) for k in ['rows','columns','missing_percentage','duplicate_percentage']])
        semantics={s['column']:s for s in result['semantics'].get(name,[])}; records=[]
        for c in p['column_profiles']:
            item=semantics.get(c['column'],{})
            records.append({**c,'dataset':name,'unique_percentage':100*c['unique_values']/max(1,p['rows']),'duplicate_values':int(result['datasets'][name][c['column']].dropna().duplicated().sum()),'semantic_type':item.get('semantic_type','Unknown'),'confidence':item.get('confidence',0),'quality':100-c['missing_percentage'],'status':'Warning' if item.get('confidence',0)<.8 else 'Completed'})
        data=pd.DataFrame(records); dtype=st.selectbox('Technical type',['All',*sorted(data.dtype.unique())]); missing=st.slider('Missing percentage range',0,100,(0,100)); unique=st.slider('Unique percentage range',0,100,(0,100))
        if dtype!='All': data=data[data.dtype==dtype]
        table(data[data.missing_percentage.between(*missing)&data.unique_percentage.between(*unique)&data.quality.between(*st.session_state.filter_quality)])
        st.caption('Click any header to sort. Column quality measures completeness.')
    elif page=='Dataset Similarity Detection':
        sim=result['similarity']
        if not sim: st.warning('Similarity analysis unavailable. Inspect orchestration errors.'); st.stop()
        st.caption(f"{sim['backend']} · {sim['embedding_dimensions']} dimensions · {sim['formula']}")
        if sim.get('warning'): st.warning(sim['warning'])
        minimum=st.slider('Minimum similarity %',0,100,0); relation=st.selectbox('Relationship type',['All','Similar','Related','Unrelated']); confidence=st.selectbox('Match confidence',['All','High','Medium','Low']); selected=names(result['datasets'],result); pairs=[]
        for p in sim['pairs']:
            band='High' if p['score']>=.8 else 'Medium' if p['score']>=.7 else 'Low'; rel='Similar' if p['similar'] else 'Related' if p['score']>=.5 else 'Unrelated'
            if p['score']*100>=minimum and (p['left'] in selected or p['right'] in selected) and (relation=='All' or relation==rel) and (confidence=='All' or confidence==band): pairs.append({**p,'confidence':p['score'],'confidence_band':band,'relationship':rel,'status':'Warning' if .7<=p['score']<.8 else 'Completed'})
        filtered=table_filter(pd.DataFrame(pairs)); involved=sorted({n for p in filtered.to_dict('records') for n in (p['left'],p['right'])}) if not filtered.empty else []
        if involved: st.plotly_chart(similarity_figure(sim['matrix'].loc[involved,involved]),width='stretch')
        table(filtered.drop(columns=['matches'],errors='ignore'))
        if not filtered.empty:
            options=filtered.to_dict('records'); index=st.selectbox('Inspect top match',range(len(options)),format_func=lambda i:f"{options[i]['left']} ↔ {options[i]['right']} · {options[i]['score']:.1%}")
            pair=options[index]; st.write(pair['explanation']); table(pair['matches'])
            if pair['status']=='Warning': st.warning('Human Review Required: similarity is between 70% and 80%.')
        st.subheader('Reusable Preparation Recipe'); registry=load_registry(); candidates=[p for p in sim['recipes'] if p['target'] in selected and p['source'] in registry]
        if not candidates: st.info('Execute an approved plan to save a validated recipe, then analyze again.')
        else:
            idx=st.selectbox('Source recipe',range(len(candidates)),format_func=lambda i:candidates[i]['source']+' → '+candidates[i]['target']); candidate=candidates[idx]; source=registry[candidate['source']]
            types={s['column']:s['semantic_type'] for s in result['semantics'][candidate['target']]}; source_types={s['column']:s['semantic_type'] for s in source['semantics']}; mapped=[]
            for step in source['plan']['steps']:
                target=candidate['mapping'].get(step.get('column'))
                if target and step['operation'] in {'strip','lowercase','normalize_phone','validate_phone','validate_email','convert_numeric','convert_dates','normalize_categories','convert_boolean'} and types.get(target)==source_types.get(step['column']): mapped.append({**step,'column':target,'origin':'recipe:'+candidate['source']})
            table(mapped); reviewed=st.checkbox('Review recipe: I reviewed these compatible mapped operations')
            st.caption('Business imputation and ranges are excluded. Preview and approval are still required.')
            if st.button('Reuse this preparation recipe',disabled=not(mapped and reviewed)):
                name=candidate['target']; plan=copy.deepcopy(st.session_state.reviewed_plans[name])
                for step in mapped:
                    existing=next((s for s in plan['steps'] if s['operation']==step['operation'] and s.get('column')==step['column'] and s.get('params',{})==step.get('params',{})),None)
                    if existing: existing['origin']=step['origin']
                    else: plan['steps'].append(step)
                st.session_state.reviewed_plans[name]=validate_plan(plan,result['datasets'][name],result['semantics'][name]); st.session_state.pop('preview',None); st.session_state.pop('plan_editor_'+name,None)
                record('Similarity','Review recipe',name,status='Modified',reason='Compatible operations selected for later approval'); st.success('Recipe added to the review plan. Preview it on Cleaning.')
    elif page=='Automatic Semantic Classification':
        name=choose('semantic'); items=result['semantics'].get(name,[])
        if not items: st.warning('Semantic classification unavailable.'); st.stop()
        data=pd.DataFrame([{**s,'dataset':name,'status':'Warning' if s['confidence']<.8 else 'Completed','evidence':' | '.join(s['evidence'])} for s in items])
        if st.checkbox('Show only low-confidence classifications'): data=data[data.confidence<.8]
        dtype=st.selectbox('Technical type',['All',*sorted(data.pandas_type.unique())])
        if dtype!='All': data=data[data.pandas_type==dtype]
        filtered=table(data.drop(columns=['pattern_rates'],errors='ignore'))
        if filtered.empty: st.info('No columns match.'); st.stop()
        column=st.selectbox('Column reasoning',filtered.column.tolist()); item=next(s for s in items if s['column']==column)
        st.markdown(f"**{column} → {item['semantic_type']}**"); st.progress(item['confidence'],text=f"Rule confidence {item['confidence']:.1%}")
        for evidence in item['evidence']: st.write('• '+evidence)
        st.json(item['pattern_rates']); st.caption('Pattern rates use up to 500 present values. Confidence is rule strength, not calibrated prediction accuracy.')
        if item['confidence']<.8: st.warning('Human Review Required — review recommended below 80% confidence.')
        decision=st.selectbox('Review decision',['Approve','Reject','Modify']); meaning=st.selectbox('Reviewed semantic type',TYPES,index=TYPES.index(item['semantic_type'])); reason=st.text_input('Reason for semantic decision')
        if st.button('Save semantic decision',disabled=not reason.strip()):
            if decision in ['Reject','Modify']:
                reviewed=copy.deepcopy(items); target=next(s for s in reviewed if s['column']==column); target['semantic_type']=meaning if decision=='Modify' else 'TEXT'; target['evidence'].append('Human review: '+reason)
                st.session_state.setdefault('semantic_overrides',{})[name]=reviewed; st.session_state.pop('preview',None)
                st.warning('Run analysis again to regenerate quality evidence and cleaning plans with this meaning.')
            record('Semantic','Review '+column,name,result=meaning,status={'Approve':'Approved','Reject':'Rejected','Modify':'Modified'}[decision],reason=reason); st.success('Decision recorded.')
    elif page=='Data Quality':
        name=choose('quality'); q=result['quality_before'].get(name)
        if not q: st.warning('Quality analysis unavailable.'); st.stop()
        metrics([(k.replace('_',' ').title(),f'{q[k]:.1f}%') for k in ['score','completeness','uniqueness','validity','type_consistency','categorical_consistency','format_consistency']]); st.info('Accuracy is not automatically measurable without external business truth.')
        column=st.selectbox('Column',['All',*result['datasets'][name].columns]); issues=pd.DataFrame(issue_rows(name,q))
        if column!='All' and not issues.empty: issues=issues[issues.column==column]
        visible=table(issues)
        if not visible.empty: st.bar_chart(visible.groupby('issue_type')['count'].sum())
        st.caption(q['formula']); st.caption('Issue counts can overlap: one cell may have several problems.')
    elif page=='Intelligent Cleaning & Transformation':
        name=choose('clean'); plans=st.session_state.get('reviewed_plans',{})
        if name not in plans: st.warning('Cleaning recommendations unavailable.'); st.stop()
        st.success('Safe execution environment · validated operation allowlist · raw data preserved')
        st.caption('Detected problems → recommendations → generated code → preview → human approval → execution')
        plan=copy.deepcopy(plans[name]); st.caption(plan['provider']+' · '+plan['provider_message']); st.info(plan['missing_policy'])
        steps=pd.DataFrame([{'selected':True,'step':i,**s,'priority':'High' if s['operation'].startswith(('validate','remove')) else 'Medium'} for i,s in enumerate(plan['steps'])])
        if not steps.empty:
            confidence_by_column={s['column']:s['confidence'] for s in result['semantics'][name]}
            problems=issue_rows(name,result['quality_before'][name])
            steps['confidence']=steps['column'].map(confidence_by_column).fillna(1.)
            steps['problem']=steps['column'].map(lambda c:'; '.join(f"{r['issue_type']}: {r['count']}" for r in problems if r['column']==(c or '(record)')) or 'Preventive normalization')
            steps['severity']=steps['priority']
            steps['params']=steps.params.map(json_text); visible=table_filter(steps)
            edited=st.data_editor(visible,hide_index=True,width='stretch',key='plan_editor_'+name,disabled=[c for c in visible.columns if c!='selected'])
            rejected=set(edited.loc[~edited.selected,'step']) if not edited.empty else set(); plan['steps']=[s for i,s in enumerate(plan['steps']) if i not in rejected]
        st.caption('Only visible deselected operations are removed. Reset view filters to review the full plan.')
        if st.button('Save selected transformations'):
            plans[name]=validate_plan(plan,result['datasets'][name],result['semantics'][name])
            st.session_state.pop('preview',None); st.session_state.pop('plan_editor_'+name,None); st.session_state.pop('plan_json_'+name,None)
            record('Cleaning','Select transformations',name,status='Modified',reason='Explicit operation selection'); st.rerun()
        reason=st.text_input('Approval / rejection reason',key='clean_reason')
        with st.expander('Modify transformation parameters'):
            text=st.text_area('Structured allowlisted plan (JSON)',json_text(plan),key='plan_json_'+name,height=180)
            if st.button('Save modified plan'):
                try:
                    plans[name]=validate_plan(json.loads(text),result['datasets'][name],result['semantics'][name]); st.session_state.pop('preview',None); st.session_state.pop('plan_editor_'+name,None)
                    record('Cleaning','Modify plan',name,status='Modified',reason=reason); st.rerun()
                except Exception as error: st.error(f'Plan rejected: {error}')
        st.code(generate_code(plan),language='python')
        if st.button('Explain transformation'):
            for step in plan['steps']: st.write(f"**{step['operation']} · {step.get('column') or 'all rows'}:** {step['explanation']}")
        if st.button('Reject plan'):
            st.session_state.pop('preview',None); record('Cleaning','Reject plan',name,status='Rejected',reason=reason); st.warning('Rejected. No transformations executed.')
        all_plans=copy.deepcopy(plans); all_plans[name]=plan; digest=plan_digest({'plans':all_plans})
        if st.button('Preview Cleaning',type='primary'):
            try:
                preview={n:execute_plan(result['datasets'][n],p,result['semantics'][n]) for n,p in all_plans.items()}; st.session_state.preview={'digest':digest,'plans':all_plans,'outputs':preview}
                record('Cleaning','Preview on copy',name,reason=reason)
            except Exception as error: st.error(f'Preview rejected: {error}')
        preview=st.session_state.get('preview'); valid_preview=preview and preview['digest']==digest
        pending_semantics=st.session_state.get('semantic_overrides',{})!=result['config'].get('semantic_overrides',{})
        if valid_preview:
            st.subheader('Before / after preview'); impact(name,preview['outputs'][name]); table(preview['outputs'][name]['changes'][:200])
            st.warning('Human Review Required: approval applies to every listed dataset. Invalid values may become missing and duplicates may be removed.')
            table([{'dataset':n,'steps':len(p['steps']),'rows_removed':preview['outputs'][n]['impact']['rows_removed'],'values_transformed':preview['outputs'][n]['impact']['values_transformed']} for n,p in all_plans.items()])
        if pending_semantics: st.warning('Semantic decisions changed. Analyze again before approving cleaning.')
        approved=st.checkbox('I reviewed the preview and approve all listed dataset plans')
        if st.button('Approve & Execute',disabled=not(valid_preview and approved and reason.strip()) or pending_semantics,type='primary'):
            try:
                executed=execute_reviewed(st.session_state.analysis,preview['plans'],live_callback(progress)); st.session_state.result=executed; st.session_state.reviewed_plans=copy.deepcopy(preview['plans']); st.session_state.pop('preview',None)
                for n,p in preview['plans'].items(): record('Cleaning','Approve & Execute',n,result=plan_digest(p),status='Approved',reason=reason)
                if not executed['execution']['all_completed']: st.error('Some execution components failed. Inspect the DAG for partial outputs and errors.')
                else: st.rerun()
            except Exception as error: st.error(f'Execution failed: {error}')
            finally: progress.empty()
    elif page=='Parallel Agent Orchestration':
        execution=result['execution']; nodes,edges=display_execution(execution); st.plotly_chart(dag_figure(nodes,edges),width='stretch')
        total=execution['sum_task_seconds']; elapsed=execution['elapsed_seconds']; savings=100*(total-elapsed)/total if total else 0
        metrics([('Sequential estimate',f'{total:.3f} s'),('Measured parallel time',f'{elapsed:.3f} s'),('Estimated time saved',f'{savings:+.1f}%')])
        st.caption('Estimate sums measured component durations. Parallel time includes live rendering overhead; negative savings are possible. Human review waiting is excluded.')
        visible=table([{'component':n,'status':s['status'].title(),'seconds':s['duration_seconds'],'dependencies':', '.join(s['dependencies']),'error':s['error']} for n,s in nodes.items()])
        if not visible.empty: st.bar_chart(visible.set_index('component')['seconds'])
        st.plotly_chart(timeline_figure(nodes),width='stretch'); node=st.selectbox('Inspect component input / output',list(nodes)); st.json(nodes[node])
        with st.expander('Execution log'): table(events(result))
    elif page in ['Transformation Impact','BI Readiness']:
        if not result['cleaning']: st.info('Awaiting human approval. Preview and approve the cleaning plans to see validated outputs.'); st.stop()
        name=choose('impact' if page=='Transformation Impact' else 'final',result['cleaning']); cleaned=result['cleaning'][name]; impact(name,cleaned)
        if page=='Transformation Impact':
            changes=pd.DataFrame(cleaned['changes']); column=st.selectbox('Changed column',['All',*sorted(set(changes.column))] if not changes.empty else ['All'])
            if column!='All': changes=changes[changes.column==column]
            table(changes); st.caption('Every row records one operation on an original row position; a cell may change multiple times.')
        else:
            gate=result['final'].get('gates',{}).get(name,{}); coverage=100*sum(s['semantic_type']!='TEXT' and s['confidence']>=.8 for s in result['semantics'][name])/max(1,len(result['semantics'][name]))
            metrics([('Data readiness score',f"{cleaned['after']['score']:.1f}%"),('Semantic coverage',f'{coverage:.1f}%')])
            if gate.get('ready_for_bi'): st.success('Dataset is ready for downstream BI analysis under the configured quality gate.')
            else: st.warning('Additional review required: readiness gate not satisfied.')
            st.caption(gate.get('meaning','')); st.json(gate); st.write('Raw Dataset → Processed Dataset → BI-Ready Dataset')
            left,right=st.columns(2)
            with left: st.write('Raw'); st.dataframe(result['datasets'][name].head(30),width='stretch')
            with right: st.write('Processed'); st.dataframe(cleaned['cleaned'].head(30),width='stretch')
            artifacts=build_artifacts(result); st.download_button('Download Clean Dataset',cleaned['cleaned'].to_csv(index=False),file_name=name+'_cleaned.csv')
            for title,filename in [('Quality Report','quality_report_after.json'),('Cleaning Plan','cleaning_plan.json'),('Similarity Report','similarity_evidence.json'),('Semantic Classification','semantic_classification.csv')]:
                if filename in artifacts: st.download_button('Download '+title,artifacts[filename],file_name=filename)
            artifacts['human_decisions.json']=json_text(st.session_state.get('human_audit',[])); st.download_button('Download all results & audit',zip_artifacts(artifacts),file_name='intelligent_data_results.zip')
            integration=result['final'].get('integration',{})
            with st.expander('Validated integration relationships'): table(integration.get('relationships',[])); st.caption(integration.get('note',''))
    elif page=='Audit Trail':
        audit=table(events(result)); st.download_button('Download Audit Trail',audit.to_csv(index=False),file_name='audit_trail.csv')
