from datetime import datetime,timezone
import json
import streamlit as st
from utils.helpers import ROOT,json_text

def record(component,action,dataset='',result='',status='Completed',reason=''):
    item={'timestamp':datetime.now(timezone.utc).isoformat(),'component':component,'action':action,'dataset':dataset,'result':result,'status':status,'reason':reason}
    st.session_state.setdefault('human_audit',[]).append(item)
    path=ROOT/'outputs/logs/human_decisions.jsonl'; path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('a',encoding='utf-8') as f: f.write(json_text(item).replace('\n','')+'\n')
    return item

def events(result):
    rows=list(st.session_state.get('human_audit',[]))
    if result:
        from ui.components import label
        for phase in [*result.get('prior_executions',[]),result['execution']]:
            from datetime import timedelta
            base=datetime.fromisoformat(phase['started_at']) if phase.get('started_at') else None
            for event in phase['events']:
                s=phase['nodes'][event['agent']]
                timestamp=(base+timedelta(seconds=event['offset_seconds'])).isoformat() if base else s.get('ended_at') or s.get('started_at')
                rows.append({'timestamp':timestamp,'component':label(event['agent']),'action':'Task '+event['status'].lower(),'dataset':'','result':s.get('error') or s.get('explanation'),'status':event['status'].title(),'reason':''})
        for n,r in result['cleaning'].items():
            for a in r['audit']: rows.append({'timestamp':result['execution']['nodes']['Controlled Execution']['ended_at'],'component':'Cleaning','action':a['operation'],'dataset':n,'result':f"{a.get('changed_cells',0)} cells changed; {a.get('rows_removed',0)} rows removed",'status':'Approved','reason':a['explanation']})
    return sorted(rows,key=lambda r:r['timestamp'] or '')
