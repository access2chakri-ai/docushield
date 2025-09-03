"""
Request schemas for DocuShield API
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Document Management
class DocumentUploadRequest(BaseModel):
    filename: str
    source: str = "upload"

class ProcessContractRequest(BaseModel):
    contract_id: str
    trigger: str = "manual"
    resume_from_step: Optional[str] = None

# Digital Twin
class SimulationRequest(BaseModel):
    scenario_name: str
    description: str
    document_ids: List[str]
    parameter_changes: Dict[str, Any]

# LLM Factory
class LLMRequest(BaseModel):
    prompt: str
    task_type: str = "completion"
    provider: Optional[str] = None
    max_tokens: int = 1000
    temperature: float = 0.7

# Authentication
class UserRegistrationRequest(BaseModel):
    email: str
    name: str
    password: str

class UserLoginRequest(BaseModel):
    email: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# Search
class AdvancedSearchRequest(BaseModel):
    query: str
    search_type: str = "hybrid"  # semantic, keyword, hybrid, structured
    document_filter: str = "all"  # all, contracts, invoices, policies, high_risk, recent
    limit: int = 20
    filters: Optional[Dict[str, Any]] = None

# Chat/Agent
class ChatRequest(BaseModel):
    question: str
    document_id: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None

class RunRequest(BaseModel):
    query: str
    dataset_id: Optional[str] = "default"
    document_filter: Optional[str] = None
