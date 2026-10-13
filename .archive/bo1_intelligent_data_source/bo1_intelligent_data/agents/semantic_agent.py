from core.semantic_classifier import classify_dataset,classify_column,pattern_rates

class SemanticTypeAgent:
    extract_features=staticmethod(pattern_rates)
    infer_semantic_type=staticmethod(classify_column)
    def calculate_confidence(self,prediction): return prediction['confidence']
    def generate_explanation(self,prediction): return prediction['evidence']
    def run(self,frame): return classify_dataset(frame)
