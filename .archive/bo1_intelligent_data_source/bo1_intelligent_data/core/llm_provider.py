import json
import os
import urllib.request
from core.cleaning_engine import Plan,validate_plan

class CleaningProvider:
    """Structured plans only; generated remote code is never accepted."""
    def __init__(self,enabled=False): self.enabled=enabled

    def improve(self,local_plan,profile,semantics,quality,frame):
        key=os.getenv('OPENAI_API_KEY')
        if not self.enabled: return local_plan
        if not key:
            return {**local_plan,'provider_message':'LLM enabled but no API key: deterministic local plan used.'}
        payload={'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini'),'response_format':{'type':'json_object'},'messages':[
            {'role':'system','content':'You propose a safe data cleaning PLAN as JSON matching the provided schema. Never return arbitrary executable code. Preserve missing business values and identifiers. Do not add fill_missing, replace, uppercase or custom category mappings. You may refine explanations or use the allowed transformations. Keep dataset and column names unchanged.'},
            {'role':'user','content':json.dumps({'schema':Plan.model_json_schema(),'local_plan':local_plan,'profile':{'rows':profile['rows'],'columns':profile['column_names']},'semantics':semantics,'quality':quality})}]}
        request=urllib.request.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        try:
            with urllib.request.urlopen(request,timeout=20) as response: result=json.load(response)
            candidate=json.loads(result['choices'][0]['message']['content'])
            candidate=validate_plan(candidate,frame,semantics)
            if candidate['dataset']!=local_plan['dataset']: raise ValueError('Dataset mismatch')
            for step in candidate['steps']:
                if step['operation'] in ['fill_missing','replace','uppercase'] or step['params'].get('mapping'): raise ValueError('Remote plan violates preservation policy')
                step['origin']='llm_validated'
            candidate['provider']='openai_structured_plan'; candidate['provider_message']='Remote JSON plan passed schema and semantic safety checks. No remote Python executed.'
            return candidate
        except Exception as error:
            return {**local_plan,'provider':'local_fallback','provider_message':f'Provider unavailable or unsafe plan rejected ({type(error).__name__}); local plan used.'}
