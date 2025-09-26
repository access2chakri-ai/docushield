#!/usr/bin/env python3
"""
Document Enrichment MCP Server
Provides external data enrichment for document analysis
"""
import json
import requests
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DocumentEnrichmentServer:
    """MCP Server for document enrichment with external data"""
    
    def __init__(self):
        self.sec_api_base = "https://www.sec.gov/api"
        self.federal_register_api = "https://www.federalregister.gov/api/v1"
        self.court_listener_api = "https://www.courtlistener.com/api/rest/v3"
        self.alpha_vantage_api = "https://www.alphavantage.co/query"
        
        # Rate limiting
        self.last_request_time = {}
        self.min_request_interval = 1.0  # 1 second between requests
    
    def _rate_limit(self, api_name: str):
        """Simple rate limiting"""
        now = datetime.now()
        if api_name in self.last_request_time:
            elapsed = (now - self.last_request_time[api_name]).total_seconds()
            if elapsed < self.min_request_interval:
                time.sleep(self.min_request_interval - elapsed)
        self.last_request_time[api_name] = now
    
    async def get_company_filings(self, company_name: str, company_cik: Optional[str] = None) -> Dict[str, Any]:
        """Get SEC filings for a company - FREE API"""
        try:
            self._rate_limit("sec")
            
            if company_cik:
                # Direct CIK lookup
                url = f"{self.sec_api_base}/xbrl/companyfacts/CIK{company_cik.zfill(10)}.json"
                response = requests.get(url, headers={"User-Agent": "DocuShield/1.0"})
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "company_name": data.get("entityName", company_name),
                        "cik": company_cik,
                        "filings_summary": {
                            "recent_filings": len(data.get("facts", {})),
                            "last_updated": datetime.now().isoformat()
                        },
                        "financial_data": self._extract_key_financials(data),
                        "source": "SEC EDGAR API"
                    }
            
            # If no CIK, return basic info
            return {
                "success": False,
                "message": f"No CIK provided for {company_name}. SEC data requires company CIK number.",
                "suggestion": "Try searching SEC.gov for the company's CIK number",
                "source": "SEC EDGAR API"
            }
            
        except Exception as e:
            logger.error(f"SEC API error: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": "SEC EDGAR API"
            }
    
    def _extract_key_financials(self, sec_data: Dict) -> Dict[str, Any]:
        """Extract key financial metrics from SEC data"""
        try:
            facts = sec_data.get("facts", {})
            us_gaap = facts.get("us-gaap", {})
            
            financials = {}
            
            # Common financial metrics
            metrics = {
                "Assets": "Assets",
                "Liabilities": "Liabilities", 
                "Revenues": "Revenues",
                "NetIncomeLoss": "NetIncome",
                "CashAndCashEquivalentsAtCarryingValue": "Cash"
            }
            
            for sec_key, display_key in metrics.items():
                if sec_key in us_gaap:
                    metric_data = us_gaap[sec_key]
                    if "units" in metric_data and "USD" in metric_data["units"]:
                        recent_values = metric_data["units"]["USD"][-3:]  # Last 3 values
                        financials[display_key] = recent_values
            
            return financials
            
        except Exception as e:
            logger.error(f"Financial extraction error: {e}")
            return {}
    
    async def get_regulatory_updates(self, industry: str, document_type: str) -> Dict[str, Any]:
        """Get recent regulatory updates - FREE API"""
        try:
            self._rate_limit("federal_register")
            
            # Map industries to agency searches
            industry_agencies = {
                "financial services": ["treasury", "sec", "cftc"],
                "healthcare": ["hhs", "fda"],
                "technology": ["ftc", "fcc"],
                "legal": ["justice"],
                "education": ["education"],
                "default": ["federal-register"]
            }
            
            agencies = industry_agencies.get(industry.lower(), industry_agencies["default"])
            
            # Search for recent regulations
            params = {
                "conditions[publication_date][gte]": (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d"),
                "conditions[type][]": "RULE",
                "per_page": 10
            }
            
            if agencies[0] != "federal-register":
                params["conditions[agencies][]"] = agencies[0]
            
            response = requests.get(f"{self.federal_register_api}/documents.json", params=params)
            
            if response.status_code == 200:
                data = response.json()
                regulations = []
                
                for doc in data.get("results", [])[:5]:  # Top 5 results
                    regulations.append({
                        "title": doc.get("title", ""),
                        "summary": doc.get("abstract", "")[:200] + "..." if doc.get("abstract") else "",
                        "publication_date": doc.get("publication_date", ""),
                        "url": doc.get("html_url", ""),
                        "agency": doc.get("agencies", [{}])[0].get("name", "") if doc.get("agencies") else ""
                    })
                
                return {
                    "success": True,
                    "industry": industry,
                    "regulations": regulations,
                    "search_period": "Last 90 days",
                    "source": "Federal Register API"
                }
            
            return {
                "success": False,
                "message": f"No recent regulations found for {industry}",
                "source": "Federal Register API"
            }
            
        except Exception as e:
            logger.error(f"Federal Register API error: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": "Federal Register API"
            }
    
    async def get_legal_precedents(self, document_type: str, keywords: List[str]) -> Dict[str, Any]:
        """Get legal precedents from court cases - FREE API"""
        try:
            self._rate_limit("court_listener")
            
            # Build search query
            search_terms = " AND ".join(keywords[:3])  # Limit to 3 keywords
            
            params = {
                "q": search_terms,
                "type": "o",  # Opinions
                "order_by": "dateFiled desc",
                "format": "json"
            }
            
            response = requests.get(f"{self.court_listener_api}/search/", params=params)
            
            if response.status_code == 200:
                data = response.json()
                cases = []
                
                for result in data.get("results", [])[:3]:  # Top 3 cases
                    cases.append({
                        "case_name": result.get("caseName", ""),
                        "court": result.get("court", ""),
                        "date_filed": result.get("dateFiled", ""),
                        "snippet": result.get("snippet", "")[:150] + "..." if result.get("snippet") else "",
                        "url": f"https://www.courtlistener.com{result.get('absolute_url', '')}" if result.get('absolute_url') else ""
                    })
                
                return {
                    "success": True,
                    "document_type": document_type,
                    "search_terms": keywords,
                    "cases": cases,
                    "source": "CourtListener API"
                }
            
            return {
                "success": False,
                "message": f"No legal precedents found for {search_terms}",
                "source": "CourtListener API"
            }
            
        except Exception as e:
            logger.error(f"CourtListener API error: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": "CourtListener API"
            }
    
    async def get_market_data(self, company_symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get market data using free APIs"""
        try:
            if not company_symbol:
                return {
                    "success": False,
                    "message": "No company symbol provided",
                    "source": "Market Data API"
                }
            
            # Use yfinance for free market data
            try:
                import yfinance as yf
                
                ticker = yf.Ticker(company_symbol)
                info = ticker.info
                
                return {
                    "success": True,
                    "symbol": company_symbol,
                    "company_name": info.get("longName", ""),
                    "sector": info.get("sector", ""),
                    "industry": info.get("industry", ""),
                    "market_cap": info.get("marketCap", 0),
                    "current_price": info.get("currentPrice", 0),
                    "52_week_high": info.get("fiftyTwoWeekHigh", 0),
                    "52_week_low": info.get("fiftyTwoWeekLow", 0),
                    "source": "Yahoo Finance API"
                }
                
            except ImportError:
                return {
                    "success": False,
                    "message": "yfinance library not available. Install with: pip install yfinance",
                    "source": "Market Data API"
                }
            
        except Exception as e:
            logger.error(f"Market data error: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": "Market Data API"
            }
    
    async def enrich_document_context(
        self, 
        document_type: str, 
        industry_type: str, 
        content_keywords: List[str],
        company_names: List[str] = None
    ) -> Dict[str, Any]:
        """Main enrichment function that combines multiple data sources"""
        
        enrichment_data = {
            "document_type": document_type,
            "industry_type": industry_type,
            "enrichment_timestamp": datetime.now().isoformat(),
            "data_sources": []
        }
        
        try:
            # 1. Get regulatory updates for the industry
            regulatory_data = await self.get_regulatory_updates(industry_type, document_type)
            if regulatory_data.get("success"):
                enrichment_data["regulatory_context"] = regulatory_data
                enrichment_data["data_sources"].append("Federal Register")
            
            # 2. Get legal precedents for document type
            if content_keywords:
                legal_data = await self.get_legal_precedents(document_type, content_keywords)
                if legal_data.get("success"):
                    enrichment_data["legal_context"] = legal_data
                    enrichment_data["data_sources"].append("CourtListener")
            
            # 3. Get company data if company names found
            if company_names:
                company_data = []
                for company in company_names[:2]:  # Limit to 2 companies
                    # Try to get market data (requires symbol)
                    market_info = await self.get_market_data(company)
                    if market_info.get("success"):
                        company_data.append(market_info)
                
                if company_data:
                    enrichment_data["company_context"] = company_data
                    enrichment_data["data_sources"].append("Market Data")
            
            enrichment_data["success"] = True
            enrichment_data["sources_count"] = len(enrichment_data["data_sources"])
            
            return enrichment_data
            
        except Exception as e:
            logger.error(f"Document enrichment error: {e}")
            enrichment_data["success"] = False
            enrichment_data["error"] = str(e)
            return enrichment_data

# MCP Server Interface Functions
server = DocumentEnrichmentServer()

async def get_company_filings(company_name: str, company_cik: str = None):
    """MCP tool: Get SEC company filings"""
    return await server.get_company_filings(company_name, company_cik)

async def get_regulatory_updates(industry: str, document_type: str):
    """MCP tool: Get regulatory updates"""
    return await server.get_regulatory_updates(industry, document_type)

async def get_legal_precedents(document_type: str, keywords: list):
    """MCP tool: Get legal precedents"""
    return await server.get_legal_precedents(document_type, keywords)

async def get_market_data(company_symbol: str):
    """MCP tool: Get market data"""
    return await server.get_market_data(company_symbol)

async def enrich_document_context(document_type: str, industry_type: str, content_keywords: list, company_names: list = None):
    """MCP tool: Comprehensive document enrichment"""
    return await server.enrich_document_context(document_type, industry_type, content_keywords, company_names)

if __name__ == "__main__":
    # Test the server
    async def test_server():
        print("🧪 Testing Document Enrichment MCP Server")
        
        # Test regulatory updates
        result = await get_regulatory_updates("technology", "contract")
        print(f"Regulatory updates: {result.get('success', False)}")
        
        # Test legal precedents
        result = await get_legal_precedents("contract", ["software", "license", "agreement"])
        print(f"Legal precedents: {result.get('success', False)}")
        
        # Test comprehensive enrichment
        result = await enrich_document_context(
            "contract", 
            "technology", 
            ["software", "saas", "subscription"],
            ["MSFT"]
        )
        print(f"Document enrichment: {result.get('success', False)}")
        print(f"Data sources: {result.get('data_sources', [])}")
    
    asyncio.run(test_server())