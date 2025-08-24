from pydantic import BaseModel
from typing import Literal, List, Dict, Any

Mode = Literal["qa", "summary", "dashboard"]

class QueryRequest(BaseModel):
    mode: Mode
    prompt: str

class QAResponse(BaseModel):
    answer: str
    citations: List[Dict[str, Any]]

class SummaryResponse(BaseModel):
    summary: str

class DashboardSpec(BaseModel):
    spec: dict
