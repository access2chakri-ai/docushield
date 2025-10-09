"""
Response schemas for DocuShield API
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

# Authentication
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class UserResponse(BaseModel):
    user_id: str
    email: str
    name: str
    is_active: bool
    profile_photo_url: Optional[str] = None
    profile_photo_prompt: Optional[str] = None
    created_at: str

class ProfilePhotoResponse(BaseModel):
    success: bool
    image_url: str
    prompt: str
    model: str
    provider: str
    estimated_cost: float

# Document Management
class ContractAnalysisResponse(BaseModel):
    contract_id: str
    processing_run_id: str
    status: str
    overall_score: Optional[int]
    risk_level: Optional[str]
    findings_count: int
    suggestions_count: int

# Digital Twin
class DigitalTwinInsightsResponse(BaseModel):
    workflow_type: str
    metrics: Dict[str, Any]
    risk_patterns: List[Dict[str, Any]]
    recommendations: List[str]

# Search
class SearchResultItem(BaseModel):
    document_id: str
    title: str
    document_type: str
    content_snippet: str
    relevance_score: float
    match_type: str
    highlights: List[str]
    metadata: Dict[str, Any]

class AdvancedSearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    total_results: int
    search_time_ms: float
    search_type: str
    applied_filters: Dict[str, Any]
    suggestions: List[str]

# Chat/Agent
class ChatResponse(BaseModel):
    response: str
    sources: List[Dict[str, Any]]
    confidence: float
    processing_time: float

class RunResponse(BaseModel):
    run_id: str
    status: str
    query: str
    started_at: float