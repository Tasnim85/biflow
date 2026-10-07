from core.cleaning_engine import generate_plan,generate_code,validate_plan,execute_plan
from core.llm_provider import CleaningProvider

class CleaningAgent:
    def __init__(self,llm_enabled=False): self.provider=CleaningProvider(llm_enabled)
    def generate_cleaning_plan(self,name,frame,profile,semantics,quality,recipes=None,registry=None):
        plan=generate_plan(name,frame,semantics,quality,recipes,registry)
        return self.provider.improve(plan,profile,semantics,quality,frame)
    generate_transformation_code=staticmethod(generate_code)
    validate_transformation=staticmethod(validate_plan)
    execute_safe_transformation=staticmethod(execute_plan)
