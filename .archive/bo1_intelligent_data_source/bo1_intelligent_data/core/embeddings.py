"""Offline lexical/concept embeddings or an optional local neural encoder."""
from itertools import combinations
from difflib import SequenceMatcher
import os
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import HashingVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.optimize import linear_sum_assignment
from core.semantic_classifier import canonical,pattern_rates
from utils.helpers import missing_mask,ROOT

def concept(name):
    key=canonical(name)
    if key in ['first_name','last_name','full_name','employee_name']: return 'person_name'
    return key

class EmbeddingEngine:
    def __init__(self,backend='local',model_path=None):
        self.backend='local_hashing'; self.warning=None; self.model=None
        if backend=='minilm':
            try:
                from sentence_transformers import SentenceTransformer
                bundled=ROOT/'models/all-MiniLM-L6-v2'
                model=model_path or os.getenv('BO1_EMBEDDING_MODEL') or (str(bundled) if (bundled/'model.safetensors').exists() else 'sentence-transformers/all-MiniLM-L6-v2')
                self.model=SentenceTransformer(model,local_files_only=True,device='cpu',trust_remote_code=False)
                self.backend='sentence_transformers_minilm'
            except Exception as error:
                self.warning=f'Local MiniLM unavailable ({type(error).__name__}); using deterministic hashing embeddings.'

    def generate_embeddings(self,texts):
        if self.model is not None: return self.model.encode(texts,normalize_embeddings=True,show_progress_bar=False)
        # Real fixed-dimensional vectors; a lexical/concept baseline, not a learned neural representation.
        word=HashingVectorizer(n_features=512,alternate_sign=False,norm='l2',ngram_range=(1,2))
        char=HashingVectorizer(n_features=512,alternate_sign=False,norm='l2',analyzer='char_wb',ngram_range=(3,5))
        return np.hstack([word.transform(texts).toarray()*.9,char.transform(texts).toarray()*.1])

    def compare_datasets(self,datasets,profiles,threshold=.75):
        descriptors={}; vectors={}; patterns={}
        for name,frame in datasets.items():
            descriptors[name]=[(concept(c)+' ')*4+canonical(c).replace('_',' ') for c in frame]
            vectors[name]=self.generate_embeddings(descriptors[name])
            patterns[name]={c:pattern_rates(frame[c]) for c in frame}
        pairs=[]
        for left,right in combinations(datasets,2):
            a,b=datasets[left],datasets[right]; ac=list(a); bc=list(b)
            embedding=np.clip(cosine_similarity(vectors[left],vectors[right]),0,1)
            scores=np.zeros((len(ac),len(bc))); all_matches={}
            for i,ca in enumerate(ac):
                for j,cb in enumerate(bc):
                    name_score=SequenceMatcher(None,canonical(ca),canonical(cb)).ratio()
                    pa=np.array(list(patterns[left][ca].values())); pb=np.array(list(patterns[right][cb].values()))
                    pattern=1-float(np.mean(np.abs(pa-pb)))
                    type_score=float(pd.api.types.is_numeric_dtype(a[ca])==pd.api.types.is_numeric_dtype(b[cb]))
                    card=1-abs(a[ca].nunique()/max(1,len(a))-b[cb].nunique()/max(1,len(b)))
                    va=set(a[ca][~missing_mask(a[ca])].astype(str).str.strip().str.casefold())
                    vb=set(b[cb][~missing_mask(b[cb])].astype(str).str.strip().str.casefold())
                    overlap=len(va&vb)/max(1,len(va|vb))
                    shared_id=float(canonical(ca).endswith('_id') and canonical(cb)==canonical(ca))*overlap
                    score=.50*embedding[i,j]+.15*name_score+.10*pattern+.10*type_score+.10*card+.05*shared_id
                    scores[i,j]=score
                    all_matches[i,j]={'left_column':ca,'right_column':cb,'score':round(float(score),4),
                        'embedding_cosine':round(float(embedding[i,j]),4),'name_similarity':round(name_score,4),
                        'type_compatibility':type_score,'value_pattern_similarity':round(pattern,4),
                        'cardinality_similarity':round(card,4),'shared_identifier_overlap':round(shared_id,4),
                        'same_concept':concept(ca)==concept(cb),
                        'explanation':f'{concept(ca)} ↔ {concept(cb)}; embedding cosine {embedding[i,j]:.3f}; name {name_score:.3f}; pattern {pattern:.3f}; type {type_score:.0f}; cardinality {card:.3f}; shared key {shared_id:.3f}'}
            ii,jj=linear_sum_assignment(-scores)
            matches=[all_matches[i,j] for i,j in zip(ii,jj)]
            coverage=len(matches)/max(len(ac),len(bc)); score=float(sum(m['score'] for m in matches)/max(len(ac),len(bc)))
            pairs.append({'left':left,'right':right,'score':round(score,4),'schema_coverage':round(coverage,4),'matches':matches,
                'similar':score>=threshold,'matched_concepts':sum(m['same_concept'] for m in matches),
                'explanation':f'{sum(m["same_concept"] for m in matches)}/{max(len(ac),len(bc))} matching concepts; one-to-one optimal alignment; schema coverage {coverage:.0%}; weighted vector/name/pattern/type/cardinality/key evidence.'})
        matrix=pd.DataFrame(np.eye(len(datasets)),index=list(datasets),columns=list(datasets))
        for p in pairs: matrix.loc[p['left'],p['right']]=matrix.loc[p['right'],p['left']]=p['score']
        pairs.sort(key=lambda p:p['score'],reverse=True)
        return {'pairs':pairs,'matrix':matrix,'backend':self.backend,'warning':self.warning,'threshold':threshold,
            'embedding_dimensions':next(iter(vectors.values())).shape[1] if vectors else 0,
            'formula':'Column score = .50 embedding cosine + .15 canonical name + .10 pattern + .10 dtype compatibility + .10 cardinality + .05 shared ID. Hungarian assignment; sum divided by maximum schema width. Profiles are inputs to the similarity task; embeddings use column concepts/names and values are compared locally.'}

def recommend_recipes(similarity,registry=None):
    registry=registry or {}; recommendations=[]
    for pair in similarity['pairs']:
        if not pair['similar']: continue
        source,target=pair['left'],pair['right']
        if target in registry and source not in registry: source,target=target,source
        reverse=source!=pair['left']
        mapping={(m['right_column'] if reverse else m['left_column']):(m['left_column'] if reverse else m['right_column']) for m in pair['matches'] if m['score']>=.7 and m['same_concept']}
        available=source in registry
        recommendations.append({'source':source,'target':target,'score':pair['score'],'mapping':mapping,
            'available_recipe':available,'recommendation':f'Reuse validated compatible steps from {source}' if available else f'Potential reuse from {source}; save the first run to create its recipe',
            'explanation':'Only mapped columns with the same semantic class may reuse allowlisted steps; current target data is validated again.'})
    return recommendations
