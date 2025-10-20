"""
Request schemas for DocuShield API
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Document Management
class DocumentUploadRequest(BaseModel):
    filename: str
    source: str = "upload"
    document_type: Optional[str] = None
    industry_type: Optional[str] = None
    user_description: Optional[str] = None

class ProcessContractRequest(BaseModel):
    contract_id: str
    trigger: str = "manual"
    resume_from_step: Optional[str] = None

# Digital Twin
class SimulationRequest(BaseModel):
    scenario_name: str  # e.g., "volume_surge", "quality_degradation", "compliance_change", "system_optimization"
    description: Optional[str] = None
    parameter_changes: Optional[Dict[str, Any]] = None  # Custom parameters to override defaults

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

# Profile Management
class UpdateProfileRequest(BaseModel):
    name: Optional[str] = None
    profile_photo_url: Optional[str] = None
    profile_photo_prompt: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class GenerateProfilePhotoRequest(BaseModel):
    prompt: str
    size: str = "1024x1024"
    quality: str = "standard"
    style: str = "vivid"

# Search
class AdvancedSearchRequest(BaseModel):
    query: str
    search_type: str = "hybrid"  # semantic, keyword, hybrid, structured
    document_filter: str = "all"  # all, contracts, invoices, policies, high_risk, recent
    limit: int = 20
    filters: Optional[Dict[str, Any]] = None
    # New filtering options
    document_types: Optional[List[str]] = None  # Filter by document types
    industry_types: Optional[List[str]] = None  # Filter by industry types

# Chat/Agent
class ChatRequest(BaseModel):
    question: str
    document_id: Optional[str] = None
    conversation_history: Optional[List[Dict[str, str]]] = None
    # New filtering options for chat
    document_types: Optional[List[str]] = None  # Filter documents by type
    industry_types: Optional[List[str]] = None  # Filter documents by industry
    chat_mode: Optional[str] = "documents"  # "documents", "all_documents", "general"
    search_all_documents: Optional[bool] = False  # Search across all user documents

class RunRequest(BaseModel):
    query: str
    dataset_id: Optional[str] = "default"
    document_filter: Optional[str] = None