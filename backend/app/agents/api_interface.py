"""
Clean API Interface for Agent System - AWS Bedrock AgentCore Compatible
Provides simple, production-ready endpoints for agent interactions
Enterprise-grade architecture designed for AWS Bedrock AgentCore migration
"""
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import asdict

from .agent_factory import agent_factory
from .base_agent import AgentPriority
from .orchestrator import document_orchestrator

logger = logging.getLogger(__name__)

class AgentAPI:
    """
    Clean API interface for the agent system - AWS Bedrock AgentCore Compatible
    Provides simple methods for common operations with enterprise-grade reliability
    """
    
    def __init__(self):
        self.factory = agent_factory
        self.orchestrator = document_orchestrator
        self.logger = logging.getLogger("agent_api")
    
    async def search_document(
        self,
        query: str,
        contract_id: str,
        user_id: str,
        timeout_seconds: int = 90
    ) -> Dict[str, Any]:
        """
        Search within a specific document
        
        Args:
            query: Search query
            contract_id: Document ID to search
            user_id: User making the request
            timeout_seconds: Request timeout
            
        Returns:
            Dict with search results, findings, and recommendations
        """
        try:
            self.logger.info(f"Document search: '{query}' in {contract_id} for user {user_id}")
            
            result = await self.orchestrator.process_request(
                contract_id=contract_id,
                user_id=user_id,
                query=query,
                priority=AgentPriority.MEDIUM,
                timeout_seconds=timeout_seconds
            )
            
            return {
                "success": result.success,
                "confidence": result.confidence,
                "findings": result.findings,
                "recommendations": result.recommendations,
                "execution_time_ms": result.execution_time_ms,
                "agents_used": result.agents_used,
                "run_id": result.run_id
            }
            
        except Exception as e:
            self.logger.error(f"Document search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "findings": [],
                "recommendations": ["Search failed - please try again"],
                "execution_time_ms": 0,
                "agents_used": []
            }
    
    async def analyze_document(
        self,
        contract_id: str,
        user_id: str,
        document_type: Optional[str] = None,
        priority: str = "medium",
        timeout_seconds: int = 60
    ) -> Dict[str, Any]:
        """
        Perform comprehensive document analysis
        
        Args:
            contract_id: Document ID to analyze
            user_id: User making the request
            document_type: Type of document (contract, invoice, etc.)
            priority: Analysis priority (low, medium, high, critical)
            timeout_seconds: Request timeout
            
        Returns:
            Dict with analysis results, findings, and recommendations
        """
        try:
            self.logger.info(f"Document analysis: {contract_id} ({document_type}) for user {user_id}")
            
            # Convert priority string to enum
            priority_map = {
                "low": AgentPriority.LOW,
                "medium": AgentPriority.MEDIUM,
                "high": AgentPriority.HIGH,
                "critical": AgentPriority.CRITICAL
            }
            priority_enum = priority_map.get(priority.lower(), AgentPriority.MEDIUM)
            
            result = await self.orchestrator.process_request(
                contract_id=contract_id,
                user_id=user_id,
                document_type=document_type,
                priority=priority_enum,
                timeout_seconds=timeout_seconds
            )
            
            return {
                "success": result.success,
                "confidence": result.confidence,
                "findings": result.findings,
                "recommendations": result.recommendations,
                "execution_time_ms": result.execution_time_ms,
                "agents_used": result.agents_used,
                "run_id": result.run_id,
                "analysis_summary": self._generate_analysis_summary(result)
            }
            
        except Exception as e:
            self.logger.error(f"Document analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "findings": [],
                "recommendations": ["Analysis failed - please try again"],
                "execution_time_ms": 0,
                "agents_used": []
            }
    
    async def quick_search(
        self,
        query: str,
        contract_id: str,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Quick search with minimal processing
        
        Args:
            query: Search query
            contract_id: Document ID
            user_id: User ID
            
        Returns:
            Dict with search results
        """
        try:
            # Use search agent directly for quick search
            search_agent = self.factory.get_agent('search_agent')
            if not search_agent:
                raise Exception("Search agent not available")
            
            from .base_agent import AgentContext
            context = AgentContext(
                contract_id=contract_id,
                user_id=user_id,
                run_id=f"quick_search_{int(datetime.now().timestamp())}",
                query=query,
                timeout_seconds=15,
                cache_enabled=True
            )
            
            result = await search_agent.analyze(context)
            
            return {
                "success": result.status.value == "completed",
                "confidence": result.confidence,
                "findings": result.findings,
                "recommendations": result.recommendations,
                "execution_time_ms": result.execution_time_ms
            }
            
        except Exception as e:
            self.logger.error(f"Quick search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "findings": [],
                "recommendations": []
            }
    
    async def quick_analysis(
        self,
        contract_id: str,
        user_id: str,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Quick analysis with minimal processing
        
        Args:
            contract_id: Document ID
            user_id: User ID
            document_type: Document type hint
            
        Returns:
            Dict with analysis results
        """
        try:
            # Use document analyzer directly for quick analysis
            analyzer = self.factory.get_agent('document_analyzer')
            if not analyzer:
                raise Exception("Document analyzer not available")
            
            from .base_agent import AgentContext
            context = AgentContext(
                contract_id=contract_id,
                user_id=user_id,
                run_id=f"quick_analysis_{int(datetime.now().timestamp())}",
                document_type=document_type,
                timeout_seconds=90,
                cache_enabled=True
            )
            
            result = await analyzer.analyze(context)
            
            return {
                "success": result.status.value == "completed",
                "confidence": result.confidence,
                "findings": result.findings,
                "recommendations": result.recommendations,
                "execution_time_ms": result.execution_time_ms
            }
            
        except Exception as e:
            self.logger.error(f"Quick analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "findings": [],
                "recommendations": []
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """
        Get system health and status information
        
        Returns:
            Dict with system status
        """
        try:
            agent_info = self.factory.get_agent_info()
            
            return {
                "status": "healthy" if len(agent_info) > 0 else "degraded",
                "timestamp": datetime.now().isoformat(),
                "agents": agent_info,
                "orchestrator": {
                    "version": self.orchestrator.version,
                    "status": "healthy"
                },
                "available_agents": self.factory.get_available_agent_names()
            }
            
        except Exception as e:
            self.logger.error(f"System status check failed: {e}")
            return {
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def get_agent_info(self, agent_type: str) -> Dict[str, Any]:
        """
        Get information about a specific agent
        
        Args:
            agent_type: Type of agent (search, analyzer)
            
        Returns:
            Dict with agent information
        """
        try:
            agent = self.factory.get_agent(agent_type)
            if not agent:
                return {
                    "error": f"Unknown agent type: {agent_type}",
                    "available_types": self.factory.get_available_agent_names()
                }
            
            return {
                "name": agent.agent_name,
                "version": agent.version,
                "type": type(agent).__name__,
                "status": "available"
            }
        except Exception as e:
            self.logger.error(f"Agent info retrieval failed: {e}")
            return {
                "error": str(e)
            }
    
    def _generate_analysis_summary(self, result) -> Dict[str, Any]:
        """Generate summary of analysis results"""
        try:
            # Count findings by severity
            severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
            
            for finding in result.findings:
                severity = finding.get("severity", "low")
                if severity in severity_counts:
                    severity_counts[severity] += 1
            
            # Determine overall risk level
            if severity_counts["critical"] > 0:
                risk_level = "critical"
            elif severity_counts["high"] > 2:
                risk_level = "high"
            elif severity_counts["high"] > 0 or severity_counts["medium"] > 3:
                risk_level = "medium"
            else:
                risk_level = "low"
            
            return {
                "total_findings": len(result.findings),
                "severity_breakdown": severity_counts,
                "overall_risk_level": risk_level,
                "confidence_score": result.confidence,
                "processing_time_ms": result.execution_time_ms,
                "agents_involved": len(result.agents_used)
            }
            
        except Exception as e:
            self.logger.error(f"Analysis summary generation failed: {e}")
            return {
                "error": "Could not generate summary",
                "total_findings": len(result.findings) if hasattr(result, 'findings') else 0
            }

# Global API instance
agent_api = AgentAPI()