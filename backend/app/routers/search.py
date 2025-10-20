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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"🔍 Search request: query='{request.query}', user={current_user.user_id}, type={request.search_type}")
        
        # Convert string search type to enum
        search_type = SearchType(request.search_type.lower())
        
        # Prepare filters including document filter
        filters = request.filters or {}
        if hasattr(request, 'document_filter') and request.document_filter:
            filters['document_filter'] = request.document_filter
        
        logger.info(f"🔍 Calling advanced_search_service.search with filters: {filters}")
        
        # Check if service has search method
        if not hasattr(advanced_search_service, 'search'):
            logger.error("❌ advanced_search_service.search method not found!")
            # Return empty response
            from app.services.advanced_search import SearchResponse
            return SearchResponse(
                query=request.query,
                results=[],
                total_results=0,
                search_time_ms=0.0,
                search_type=search_type,
                applied_filters=filters,
                suggestions=["Search service not properly configured. Please check backend logs."]
            )
        
        # Execute search with document type and industry filtering
        search_response = await advanced_search_service.search(
            query=request.query,
            user_id=current_user.user_id,
            search_type=search_type,
            limit=request.limit,
            filters=filters,
            document_types=getattr(request, 'document_types', None),
            industry_types=getattr(request, 'industry_types', None)
        )
        
        logger.info(f"🔍 Search response: {len(search_response.results) if hasattr(search_response, 'results') else 0} results")
        
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
            "Show documents with missing signatures",
            "Find documents with dollar amounts",
            "Search for liability limits",
            "Show auto-renewal clauses",
            "Find termination conditions"
        ]
        
        return {
            "suggestions": suggestions,
            "categories": ["contracts", "invoices", "policies", "agreements", "financial"],
            "user_id": current_user.user_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get suggestions: {str(e)}")


