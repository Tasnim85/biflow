from core.quality import assess_quality

class DataQualityAgent:
    def run(self,frame): return assess_quality(frame)
