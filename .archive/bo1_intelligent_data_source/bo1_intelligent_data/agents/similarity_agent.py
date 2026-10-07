from core.embeddings import EmbeddingEngine,recommend_recipes

class SimilarityAgent:
    def __init__(self,backend='local',model_path=None): self.engine=EmbeddingEngine(backend,model_path)
    def generate_embeddings(self,texts): return self.engine.generate_embeddings(texts)
    def calculate_similarity(self,datasets,profiles,threshold): return self.engine.compare_datasets(datasets,profiles,threshold)
    compare_datasets=calculate_similarity
    def find_similar_datasets(self,result): return [p for p in result['pairs'] if p['similar']]
    def recommend_reusable_recipe(self,result,registry=None): return recommend_recipes(result,registry)
    def run(self,datasets,profiles,threshold,registry=None):
        result=self.compare_datasets(datasets,profiles,threshold); result['recipes']=self.recommend_reusable_recipe(result,registry)
        result['confidence']=max((p['score'] for p in result['pairs']),default=0.)
        return result
