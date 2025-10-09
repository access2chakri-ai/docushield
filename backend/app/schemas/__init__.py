"""
Schemas package for DocuShield API
Exports all request and response schemas
"""
from .requests import (
    DocumentUploadRequest,
    ProcessContractRequest,
    SimulationRequest,
    LLMRequest,
    UserRegistrationRequest,
    UserLoginRequest,
    RefreshTokenRequest,
    UpdateProfileRequest,
    ChangePasswordRequest,
    GenerateProfilePhotoRequest,
    AdvancedSearchRequest,
    ChatRequest,
    RunRequest
)
from .responses import (
    Token,
    UserResponse,
    ProfilePhotoResponse,
    ContractAnalysisResponse,
    DigitalTwinInsightsResponse,
    SearchResultItem,
    AdvancedSearchResponse,
    ChatResponse,
    RunResponse
)

__all__ = [
    # Document
    "DocumentUploadRequest",
    "ProcessContractRequest",
    "ContractAnalysisResponse",
    # Digital Twin
    "SimulationRequest",
    "DigitalTwinInsightsResponse",
    # LLM
    "LLMRequest",
    # Auth
    "UserRegistrationRequest",
    "UserLoginRequest",
    "RefreshTokenRequest",
    "Token",
    "UserResponse",
    # Profile
    "UpdateProfileRequest",
    "ChangePasswordRequest",
    "GenerateProfilePhotoRequest",
    "ProfilePhotoResponse",
    # Search
    "AdvancedSearchRequest",
    "SearchResultItem",
    "AdvancedSearchResponse",
    # Chat
    "ChatRequest",
    "ChatResponse",
    "RunRequest",
    "RunResponse"
]