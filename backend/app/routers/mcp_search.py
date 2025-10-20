"""
MCP-Enhanced Search Router
Provides endpoints for web search, news search, and external data enrichment
"""

import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.core.dependencies import get_current_active_user
from app.services.mcp_integration import mcp_service, MCPResult
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/mcp", tags=["MCP Search"])

class WebSearchRequest(BaseModel):
    query: str
    max_results: int = 10
    region: str = "us-en"
    safesearch: str = "moderate"

class NewsSearchRequest(BaseModel):
    query: str
    max_results: int = 5
    time_range: str = "d"  # d=day, w=week, m=month

class DocumentEnrichmentRequest(BaseModel):
    document_type: str
    industry_type: str
    content_keywords: List[str]
    company_names: Optional[List[str]] = None

class IndustryAnalysisRequest(BaseModel):
    industry: str
    document_type: str
    keywords: List[str]

class ComprehensiveSearchRequest(BaseModel):
    query: str
    document_type: Optional[str] = None
    industry_type: Optional[str] = None
    include_web: bool = True
    include_news: bool = True
    include_legal: bool = True
    include_industry: bool = True

@router.post("/web-search")
async def web_search(
    request: WebSearchRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Perform web search using DuckDuckGo"""
    try:
        async with mcp_service:
            result = await mcp_service.web_search(
                query=request.query,
                max_results=request.max_results,
                region=request.region,
                safesearch=request.safesearch
            )
        
        if result.success:
            return {
                "success": True,
                "query": request.query,
                "results": result.data,
                "timestamp": result.timestamp.isoformat(),
                "source": result.source
            }
        else:
            raise HTTPException(status_code=500, detail=result.error)
            
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/news-search")
async def news_search(
    request: NewsSearchRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Search for recent news articles"""
    try:
        async with mcp_service:
            result = await mcp_service.news_search(
                query=request.query,
                max_results=request.max_results,
                time_range=request.time_range
            )
        
        if result.success:
            return {
                "success": True,
                "query": request.query,
                "results": result.data,
                "timestamp": result.timestamp.isoformat(),
                "source": result.source
            }
        else:
            raise HTTPException(status_code=500, detail=result.error)
            
    except Exception as e:
        logger.error(f"News search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/document-enrichment")
async def document_enrichment(
    request: DocumentEnrichmentRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Enrich document with external context data"""
    try:
        async with mcp_service:
            result = await mcp_service.enrich_document_context(
                document_type=request.document_type,
                industry_type=request.industry_type,
                content_keywords=request.content_keywords,
                company_names=request.company_names
            )
        
        if result.success:
            return {
                "success": True,
                "document_type": request.document_type,
                "industry_type": request.industry_type,
                "enrichment_data": result.data,
                "timestamp": result.timestamp.isoformat(),
                "source": result.source
            }
        else:
            raise HTTPException(status_code=500, detail=result.error)
            
    except Exception as e:
        logger.error(f"Document enrichment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/industry-analysis")
async def industry_analysis(
    request: IndustryAnalysisRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Analyze industry context for document"""
    try:
        async with mcp_service:
            result = await mcp_service.analyze_industry_context(
                industry=request.industry,
                document_type=request.document_type,
                keywords=request.keywords
            )
        
        if result.success:
            return {
                "success": True,
                "industry": request.industry,
                "document_type": request.document_type,
                "analysis": result.data,
                "timestamp": result.timestamp.isoformat(),
                "source": result.source
            }
        else:
            raise HTTPException(status_code=500, detail=result.error)
            
    except Exception as e:
        logger.error(f"Industry analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/company-filings/{company_name}")
async def get_company_filings(
    company_name: str,
    company_cik: Optional[str] = Query(None),
    current_user: User = Depends(get_current_active_user)
):
    """Get SEC filings for a company"""
    try:
        async with mcp_service:
            result = await mcp_service.get_company_filings(
                company_name=company_name,
                company_cik=company_cik
            )
        
        if result.success:
            return {
                "success": True,
                "company_name": company_name,
                "filings": result.data,
                "timestamp": result.timestamp.isoformat(),
                "source": result.source
            }
        else:
            raise HTTPException(status_code=500, detail=result.error)
            
    except Exception as e:
        logger.error(f"Company filings search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/legal-precedents")
async def get_legal_precedents(
    document_type: str,
    keywords: List[str],
    current_user: User = Depends(get_current_active_user)
):
    """Get legal precedents related to document type and keywords"""
    try:
        async with mcp_service:
            result = await mcp_service.get_legal_precedents(
                document_type=document_type,
                keywords=keywords
            )
        
        if result.success:
            return {
                "success": True,
                "document_type": document_type,
                "keywords": keywords,
                "precedents": result.data,
                "timestamp": result.timestamp.isoformat(),
                "source": result.source
            }
        else:
            raise HTTPException(status_code=500, detail=result.error)
            
    except Exception as e:
        logger.error(f"Legal precedents search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/industry-trends/{industry}")
async def get_industry_trends(
    industry: str,
    time_period: str = Query("1year", description="Time period: 1month, 6months, 1year, 2years"),
    current_user: User = Depends(get_current_active_user)
):
    """Get industry trends and insights"""
    try:
        async with mcp_service:
            result = await mcp_service.get_industry_trends(
                industry=industry,
                time_period=time_period
            )
        
        if result.success:
            return {
                "success": True,
                "industry": industry,
                "time_period": time_period,
                "trends": result.data,
                "timestamp": result.timestamp.isoformat(),
                "source": result.source
            }
        else:
            raise HTTPException(status_code=500, detail=result.error)
            
    except Exception as e:
        logger.error(f"Industry trends search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/comprehensive-search")
async def comprehensive_search(
    request: ComprehensiveSearchRequest,
    current_user: User = Depends(get_current_active_user)
):
    """Perform comprehensive search using all available MCP services"""
    try:
        # Extract keywords from query for MCP services
        keywords = request.query.split()[:10]  # Use first 10 words as keywords
        
        async with mcp_service:
            if request.document_type and request.industry_type:
                # Use comprehensive document analysis
                results = await mcp_service.comprehensive_document_analysis(
                    document_type=request.document_type,
                    industry_type=request.industry_type,
                    content_keywords=keywords,
                    company_names=None,
                    include_web_search=request.include_web,
                    include_legal_precedents=request.include_legal,
                    include_industry_analysis=request.include_industry
                )
            else:
                # Use enhanced query search
                results = await mcp_service.search_enhanced_query(
                    query=request.query,
                    document_type=request.document_type,
                    industry_type=request.industry_type,
                    include_news=request.include_news,
                    include_legal=request.include_legal
                )
        
        # Process results
        processed_results = {}
        for source, result in results.items():
            processed_results[source] = {
                "success": result.success,
                "data": result.data if result.success else None,
                "error": result.error if not result.success else None,
                "timestamp": result.timestamp.isoformat(),
                "source": result.source
            }
        
        return {
            "success": True,
            "query": request.query,
            "results": processed_results,
            "total_sources": len(results),
            "successful_sources": len([r for r in results.values() if r.success])
        }
            
    except Exception as e:
        logger.error(f"Comprehensive search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def mcp_status(
    current_user: User = Depends(get_current_active_user)
):
    """Get status of all MCP services"""
    try:
        # Test each MCP service
        status = {
            "web_search": {"available": False, "error": None},
            "document_enrichment": {"available": False, "error": None},
            "industry_intelligence": {"available": False, "error": None}
        }
        
        async with mcp_service:
            # Test web search
            try:
                result = await mcp_service.web_search("test query", max_results=1)
                status["web_search"]["available"] = True
            except Exception as e:
                status["web_search"]["error"] = str(e)
            
            # Test document enrichment
            try:
                result = await mcp_service.enrich_document_context(
                    "contract", "technology", ["test"]
                )
                status["document_enrichment"]["available"] = True
            except Exception as e:
                status["document_enrichment"]["error"] = str(e)
            
            # Test industry intelligence
            try:
                result = await mcp_service.analyze_industry_context(
                    "technology", "contract", ["test"]
                )
                status["industry_intelligence"]["available"] = True
            except Exception as e:
                status["industry_intelligence"]["error"] = str(e)
        
        return {
            "success": True,
            "services": status,
            "timestamp": MCPResult(success=True).timestamp.isoformat()
        }
        
    except Exception as e:
        logger.error(f"MCP status check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))