from core.quality_engine import assess_quality,invalid_mask
from utils.helpers import missing_mask

class DataQualityAgent:
    def detect_missing_values(self,frame): return {c:int(missing_mask(frame[c]).sum()) for c in frame}
    def detect_duplicates(self,frame): return int(frame.duplicated().sum())
    def detect_invalid_values(self,frame,semantics): return {s['column']:int(invalid_mask(frame[s['column']],s['semantic_type']).sum()) for s in semantics}
    def detect_inconsistencies(self,frame,semantics): return assess_quality(frame,semantics)['issues']
    calculate_quality_score=staticmethod(assess_quality)
    def run(self,frame,semantics): return assess_quality(frame,semantics)
