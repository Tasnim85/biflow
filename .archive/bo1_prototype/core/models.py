from typing import Literal
from pydantic import BaseModel,Field

class SemanticColumn(BaseModel):
    column: str
    semantic_type: Literal['identifier','email','date','currency','age','person_name','text','location','numeric','category']
    confidence: float = Field(ge=0,le=1)
    evidence: list[str]

class CleaningPlan(BaseModel):
    types: list[SemanticColumn]
    steps: list[dict]
    missing_policy: str
