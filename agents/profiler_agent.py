from core.profiling import profile_dataset

class ProfilerAgent:
    def run(self,name,frame): return profile_dataset(name,frame)
