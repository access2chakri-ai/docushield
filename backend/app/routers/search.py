"""
Advanced search router for DocuShield API
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from app.core.dependencies import get_current_active_user
from app.schemas.requests import AdvancedSearchRequest
from app.schemas.responses import AdvancedSearchResponse
from app.services.advanced_search import advanced_search_service, SearchType

router = APIRouter(prefix="/api/search", tags=["search"])

@router.post("/advanced", response_model=AdvancedSearchResponse)
async def advanced_search(
    request: AdvancedSearchRequest, 
    current_user = Depends(get_current_active_user)
):
    """
    Advanced hybrid search with intelligent query parsing
    Supports complex queries like:
    - "Find contracts with auto-renewal clauses"
    - "Show invoices above $50k missing PO reference"
    - "High risk liability agreements"
    """
    try:
        # Convert string search type to enum
        search_type = SearchType(request.search_type.lower())
        
        # Execute search
        search_response = await advanced_search_service.search(
            query=request.query,
            user_id=current_user.user_id,
            search_type=search_type,
            document_filter=request.document_filter,
            limit=request.limit,
            filters=request.filters or {}
        )
        
        return search_response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid search parameters: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/suggestions")
async def get_search_suggestions(current_user = Depends(get_current_active_user)):
    """Get intelligent search suggestions based on user's document collection"""
    try:
        # This would analyze user's documents and suggest relevant searches
        suggestions = [
            "Find high-risk contract clauses",
            "Show recent uploaded documents",
            "Search for payment terms",
            "Find contracts expiring soon",
            "Show documents with missing signatures"
        ]
        
        return {
            "suggestions": suggestions,
            "categories": ["contracts", "invoices", "policies", "agreements"],
            "user_id": current_user.user_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")
