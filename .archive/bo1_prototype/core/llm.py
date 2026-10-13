"""Optional remote suggestions. Deterministic local cleaning remains executable authority."""
import json
import os
import urllib.request

def suggest(profile, enabled=False):
    key=os.getenv('OPENAI_API_KEY')
    if not enabled or not key: return dict(mode='local',message='Local mode active; no API key required.')
    # Only column metadata is shared, never raw row samples.
    payload={'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini'),'messages':[
        {'role':'system','content':'You advise data preparation. Return JSON with semantic_type_suggestions, recommendations, and cleaning_code (Python pandas). Code is for human review only. Do not invent business values.'},
        {'role':'user','content':json.dumps({'columns':profile['semantic_types'],'quality':profile['quality']})}],
        'response_format':{'type':'json_object'}}
    request=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(request,timeout=20) as response: result=json.load(response)
        return dict(mode='remote_advisory',suggestions=json.loads(result['choices'][0]['message']['content']))
    except Exception as error:
        return dict(mode='local_fallback',message=f'Optional provider unavailable ({type(error).__name__}); local processing continues.')
