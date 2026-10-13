from core.integration_plan import integration_plan

class DAGAgent:
    def run(self,datasets,similarities,threshold=.7): return integration_plan(datasets,similarities,threshold)
