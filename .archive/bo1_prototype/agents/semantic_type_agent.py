from core.semantic_types import infer_types

class SemanticTypeAgent:
    def run(self,frame): return infer_types(frame)
