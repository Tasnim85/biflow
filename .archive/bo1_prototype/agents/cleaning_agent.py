from core.cleaning_engine import make_plan,apply_plan,generate_code,execute_code

class CleaningAgent:
    def run(self,frame):
        plan=make_plan(frame); code=generate_code(plan)
        cleaned,audit=apply_plan(frame,plan)
        executed=execute_code(frame,code)
        if not executed.equals(cleaned): raise RuntimeError('Generated code output differs from cleaning engine')
        return dict(plan=plan,code=code,cleaned=executed,audit=audit)
