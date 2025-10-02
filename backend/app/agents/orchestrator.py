"""
Production Agent Orchestrator - AWS Bedrock AgentCore Compatible
Streamlined orchestration with intelligent routing and robust error handling
Enterprise-grade architecture designed for AWS Bedrock AgentCore migration
"""
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from .base_agent import BaseAgent, AgentContext, AgentResult, AgentStatus, AgentPriority
from app.database import get_operational_db
from app.models import ProcessingRun, ProcessingStep

logger = logging.getLogger(__name__)

@dataclass
class OrchestrationResult:
    """AWS Bedrock AgentCore compatible orchestration result"""
    run_id: str
    contract_id: str
    user_id: str
    query: Optional[str]
    success: bool
    confidence: float
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    execution_time_ms: float
    agents_used: List[str]
    error_message: Optional[str] = None
    # AWS Bedrock AgentCore compatibility fields
    agent_trace: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None

class DocumentOrchestrator:
    """
    Production orchestrator with intelligent agent routing and robust error handling
    AWS Bedrock AgentCore compatible with enterprise-grade architecture
    """
    
    def __init__(self):
        # Use agent factory to get properly configured agents (remote/local/agentcore)
        from .agent_factory import agent_factory
        
        self.agents = {
            "document_search_agent": agent_factory.get_agent("document_search_agent"),
            "document_analysis_agent": agent_factory.get_agent("document_analysis_agent"), 
            "clause_analysis_agent": agent_factory.get_agent("clause_analysis_agent"),
            "risk_analysis_agent": agent_factory.get_agent("risk_analysis_agent")
        }
        
        self.version = "3.0.0"
        self.logger = logging.getLogger("document_orchestrator")
        
        # Log which agents were loaded
        for agent_name, agent in self.agents.items():
            if agent:
                agent_type = type(agent).__name__
                if 'Remote' in agent_type:
                    self.logger.info(f"🐳 Orchestrator loaded DOCKER agent for {agent_name}: {agent_type}")
                elif 'AgentCore' in agent_type:
                    self.logger.info(f"☁️ Orchestrator loaded AGENTCORE agent for {agent_name}: {agent_type}")
                else:
                    self.logger.info(f"🏠 Orchestrator loaded LOCAL agent for {agent_name}: {agent_type}")
            else:
                self.logger.warning(f"❌ Orchestrator failed to load agent: {agent_name}")
        
        # AWS Bedrock AgentCore compatibility
        self.agent_metadata = {
            "orchestrator_type": "document_processing",
            "bedrock_compatible": True,
            "agent_framework": "docushield_v3",
            "supported_models": ["claude-3", "gpt-4", "bedrock-titan"]
        }
    
    async def process_request(
        self,
        contract_id: str,
        user_id: str,
        query: Optional[str] = None,
        document_type: Optional[str] = None,
        priority: AgentPriority = AgentPriority.MEDIUM,
        timeout_seconds: int = 60
    ) -> OrchestrationResult:
        """
        Main entry point for processing requests with intelligent routing
        """
        start_time = datetime.now()
        run_id = f"run_{contract_id[:8]}_{int(start_time.timestamp())}"
        
        try:
            # Add timeout protection
            return await asyncio.wait_for(
                self._process_request_impl(
                    contract_id, user_id, query, document_type, priority, run_id
                ),
                timeout=timeout_seconds
            )
            
        except asyncio.TimeoutError:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"Request timeout after {timeout_seconds}s")
            
            return OrchestrationResult(
                run_id=run_id,
                contract_id=contract_id,
                user_id=user_id,
                query=query,
                success=False,
                confidence=0.0,
                findings=[{
                    "type": "timeout_error",
                    "title": "Request timeout",
                    "severity": "high",
                    "confidence": 1.0,
                    "description": f"Processing timed out after {timeout_seconds} seconds"
                }],
                recommendations=["Try again with a simpler request"],
                execution_time_ms=execution_time,
                agents_used=[],
                error_message=f"Timeout after {timeout_seconds}s"
            )
    
    async def _process_request_impl(
        self,
        contract_id: str,
        user_id: str,
        query: Optional[str],
        document_type: Optional[str],
        priority: AgentPriority,
        run_id: str
    ) -> OrchestrationResult:
        """Internal request processing implementation"""
        start_time = datetime.now()
        
        try:
            # Create processing run
            await self._create_processing_run(run_id, contract_id, user_id)
            
            # Create shared context
            context = AgentContext(
                contract_id=contract_id,
                user_id=user_id,
                run_id=run_id,
                query=query,
                document_type=document_type,
                priority=priority,
                timeout_seconds=30,  # Per-agent timeout
                cache_enabled=True
            )
            
            # Determine execution strategy
            strategy = self._determine_strategy(query, document_type, priority)
            
            # Execute based on strategy
            if strategy == "search_only":
                results = await self._execute_search_only(context)
            elif strategy == "analysis_only":
                results = await self._execute_analysis_only(context)
            else:  # comprehensive
                results = await self._execute_comprehensive(context)
            
            # Consolidate results
            consolidated = self._consolidate_results(results, query)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update processing run
            await self._update_processing_run(run_id, "completed", execution_time)
            
            return OrchestrationResult(
                run_id=run_id,
                contract_id=contract_id,
                user_id=user_id,
                query=query,
                success=consolidated["success"],
                confidence=consolidated["confidence"],
                findings=consolidated["findings"],
                recommendations=consolidated["recommendations"],
                execution_time_ms=execution_time,
                agents_used=consolidated["agents_used"],
                error_message=consolidated.get("error_message"),
                # AWS Bedrock AgentCore compatibility
                agent_trace=self._generate_agent_trace(results, consolidated),
                session_id=f"session_{user_id}_{int(datetime.now().timestamp())}"
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"Request processing failed: {e}")
            
            await self._update_processing_run(run_id, "failed", execution_time, str(e))
            
            return OrchestrationResult(
                run_id=run_id,
                contract_id=contract_id,
                user_id=user_id,
                query=query,
                success=False,
                confidence=0.0,
                findings=[{
                    "type": "processing_error",
                    "title": "Processing failed",
                    "severity": "high",
                    "confidence": 1.0,
                    "description": f"System error: {str(e)}"
                }],
                recommendations=["Try again or contact support"],
                execution_time_ms=execution_time,
                agents_used=[],
                error_message=str(e)
            )
    
    def _determine_strategy(
        self, 
        query: Optional[str], 
        document_type: Optional[str], 
        priority: AgentPriority
    ) -> str:
        """Determine optimal execution strategy"""
        
        # Search-only for specific queries
        if query:
            query_lower = query.lower()
            search_indicators = ["find", "search", "where", "show me", "locate"]
            if any(indicator in query_lower for indicator in search_indicators):
                return "search_only"
        
        # Analysis-only for document processing without specific queries
        if not query and priority in [AgentPriority.HIGH, AgentPriority.CRITICAL]:
            return "analysis_only"
        
        # Comprehensive for complex requests
        return "comprehensive"
    
    async def _execute_search_only(self, context: AgentContext) -> List[AgentResult]:
        """Execute search-only strategy with AWS Bedrock AgentCore compatibility"""
        try:
            search_result = await self.agents["document_search_agent"].analyze(context)
            return [search_result]
        except Exception as e:
            self.logger.error(f"Search-only execution failed: {e}")
            return []
    
    async def _execute_analysis_only(self, context: AgentContext) -> List[AgentResult]:
        """Execute analysis-only strategy with AWS Bedrock AgentCore compatibility"""
        try:
            analysis_result = await self.agents["document_analysis_agent"].analyze(context)
            return [analysis_result]
        except Exception as e:
            self.logger.error(f"Analysis-only execution failed: {e}")
            return []
    
    async def _execute_comprehensive(self, context: AgentContext) -> List[AgentResult]:
        """Execute comprehensive strategy with both agents - AWS Bedrock AgentCore compatible"""
        results = []
        
        try:
            # Run all agents in parallel for better performance
            search_task = self.agents["document_search_agent"].analyze(context)
            analysis_task = self.agents["document_analysis_agent"].analyze(context)
            clause_task = self.agents["clause_analysis_agent"].analyze(context)
            risk_task = self.agents["risk_analysis_agent"].analyze(context)
            
            # Wait for all agents with individual error handling
            agent_results = await asyncio.gather(
                search_task, analysis_task, clause_task, risk_task, 
                return_exceptions=True
            )
            
            agent_names = ["document_search_agent", "document_analysis_agent", 
                          "clause_analysis_agent", "risk_analysis_agent"]
            
            # Handle each agent result
            for i, (agent_name, agent_result) in enumerate(zip(agent_names, agent_results)):
                if isinstance(agent_result, Exception):
                    self.logger.error(f"{agent_name} failed: {agent_result}")
                else:
                    results.append(agent_result)
                    self.logger.info(f"✅ {agent_name} completed: {len(agent_result.findings)} findings")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Comprehensive execution failed: {e}")
            return []
    
    def _consolidate_results(
        self, 
        results: List[AgentResult], 
        query: Optional[str]
    ) -> Dict[str, Any]:
        """Consolidate results from multiple agents"""
        
        if not results:
            return {
                "success": False,
                "confidence": 0.0,
                "findings": [{
                    "type": "no_results",
                    "title": "No results available",
                    "severity": "medium",
                    "confidence": 1.0,
                    "description": "No agents produced results"
                }],
                "recommendations": ["Try a different approach or contact support"],
                "agents_used": [],
                "error_message": "No agent results available"
            }
        
        # Collect all findings and recommendations
        all_findings = []
        all_recommendations = []
        agents_used = []
        total_confidence = 0.0
        successful_agents = 0
        
        for result in results:
            agents_used.append(result.agent_name)
            
            if result.status == AgentStatus.COMPLETED:
                all_findings.extend(result.findings)
                all_recommendations.extend(result.recommendations)
                total_confidence += result.confidence
                successful_agents += 1
        
        # Calculate overall metrics
        overall_success = successful_agents > 0
        overall_confidence = total_confidence / max(1, successful_agents)
        
        # Deduplicate and rank findings
        unique_findings = self._deduplicate_findings(all_findings)
        unique_recommendations = self._deduplicate_recommendations(all_recommendations)
        
        # Add query-specific insights if available
        if query and unique_findings:
            query_insight = self._generate_query_insight(query, unique_findings)
            if query_insight:
                unique_findings.insert(0, query_insight)
        
        return {
            "success": overall_success,
            "confidence": overall_confidence,
            "findings": unique_findings[:20],  # Limit findings
            "recommendations": unique_recommendations[:10],  # Limit recommendations
            "agents_used": agents_used
        }
    
    def _deduplicate_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate findings and rank by importance"""
        seen_titles = set()
        unique_findings = []
        
        # Sort by severity and confidence
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
        
        sorted_findings = sorted(
            findings,
            key=lambda x: (
                severity_order.get(x.get("severity", "low"), 1),
                x.get("confidence", 0.0)
            ),
            reverse=True
        )
        
        for finding in sorted_findings:
            title = finding.get("title", "")
            if title not in seen_titles:
                seen_titles.add(title)
                unique_findings.append(finding)
        
        return unique_findings
    
    def _deduplicate_recommendations(self, recommendations: List[str]) -> List[str]:
        """Remove duplicate recommendations while preserving order"""
        seen = set()
        unique_recs = []
        
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recs.append(rec)
        
        return unique_recs
    
    def _generate_query_insight(self, query: str, findings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Generate insight specific to the user's query"""
        try:
            # Count findings by type and severity
            finding_counts = {}
            high_severity_count = 0
            
            for finding in findings:
                finding_type = finding.get("type", "unknown")
                finding_counts[finding_type] = finding_counts.get(finding_type, 0) + 1
                
                if finding.get("severity") in ["critical", "high"]:
                    high_severity_count += 1
            
            # Generate contextual insight
            if high_severity_count > 0:
                insight_text = f"Found {high_severity_count} high-priority items related to your query"
            elif len(findings) > 5:
                insight_text = f"Found {len(findings)} relevant items for your query"
            else:
                insight_text = f"Found {len(findings)} items matching your query"
            
            return {
                "type": "query_insight",
                "title": f"Query Analysis: {query[:50]}...",
                "severity": "info",
                "confidence": 0.9,
                "description": insight_text,
                "query": query,
                "finding_summary": finding_counts
            }
            
        except Exception as e:
            self.logger.error(f"Query insight generation failed: {e}")
            return None
    
    # Database tracking methods
    async def _create_processing_run(self, run_id: str, contract_id: str, user_id: str):
        """Create processing run record"""
        try:
            async for db in get_operational_db():
                run = ProcessingRun(
                    run_id=run_id,
                    contract_id=contract_id,
                    pipeline_version=self.version,
                    trigger="agent_orchestrator",
                    status="running"
                )
                
                db.add(run)
                await db.commit()
        except Exception as e:
            self.logger.error(f"Failed to create processing run: {e}")
    
    async def _update_processing_run(
        self, 
        run_id: str, 
        status: str, 
        execution_time: float,
        error_message: Optional[str] = None
    ):
        """Update processing run record"""
        try:
            async for db in get_operational_db():
                from sqlalchemy import text
                
                await db.execute(
                    text("""
                        UPDATE processing_runs 
                        SET status = :status, 
                            completed_at = NOW(),
                            error_message = :error_message
                        WHERE run_id = :run_id
                    """),
                    {
                        "run_id": run_id,
                        "status": status,
                        "error_message": error_message
                    }
                )
                await db.commit()
        except Exception as e:
            self.logger.error(f"Failed to update processing run: {e}")
    
    # Public interface methods
    async def search_documents(
        self,
        query: str,
        user_id: str,
        contract_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Public interface for document search"""
        try:
            if contract_id:
                result = await self.process_request(
                    contract_id=contract_id,
                    user_id=user_id,
                    query=query,
                    priority=AgentPriority.MEDIUM
                )
            else:
                # Search across all user documents (would need implementation)
                result = OrchestrationResult(
                    run_id="search_all",
                    contract_id="",
                    user_id=user_id,
                    query=query,
                    success=False,
                    confidence=0.0,
                    findings=[{
                        "type": "not_implemented",
                        "title": "Cross-document search not implemented",
                        "severity": "info",
                        "confidence": 1.0,
                        "description": "Please specify a document to search"
                    }],
                    recommendations=["Select a specific document to search"],
                    execution_time_ms=0.0,
                    agents_used=[]
                )
            
            return asdict(result)
            
        except Exception as e:
            self.logger.error(f"Document search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "findings": [],
                "recommendations": []
            }
    
    async def analyze_document(
        self,
        contract_id: str,
        user_id: str,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Public interface for document analysis"""
        try:
            result = await self.process_request(
                contract_id=contract_id,
                user_id=user_id,
                document_type=document_type,
                priority=AgentPriority.HIGH
            )
            
            return asdict(result)
            
        except Exception as e:
            self.logger.error(f"Document analysis failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "findings": [],
                "recommendations": []
            }
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        document_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        document_types: Optional[List[str]] = None,
        industry_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process a user query for chat interface (backward compatibility)
        """
        try:
            if document_id:
                # Process with specific document
                result = await self.process_request(
                    contract_id=document_id,
                    user_id=user_id,
                    query=query,
                    priority=AgentPriority.MEDIUM,
                    timeout_seconds=45
                )
                
                return {
                    "response": self._format_chat_response(result, query),
                    "sources": self._extract_sources_for_chat(result),
                    "confidence": result.confidence,
                    "run_id": result.run_id,
                    "success": result.success
                }
            else:
                # No specific document - return helpful message
                return {
                    "response": "I'd be happy to help! Please specify which document you'd like me to analyze or search through.",
                    "sources": [],
                    "confidence": 1.0,
                    "success": True
                }
                
        except Exception as e:
            self.logger.error(f"Query processing failed: {e}")
            return {
                "response": f"I encountered an error processing your question: {str(e)}. Please try again.",
                "sources": [],
                "confidence": 0.0,
                "success": False,
                "error": str(e)
            }
    
    def _format_chat_response(self, result: OrchestrationResult, query: str) -> str:
        """Format orchestration result for chat interface"""
        if not result.success:
            return f"I couldn't process your request: {result.error_message or 'Unknown error'}"
        
        if not result.findings:
            return "I didn't find any specific information related to your query in this document."
        
        # Format findings into a readable response
        response_parts = []
        
        # Add query-specific intro
        response_parts.append(f"Based on your question about '{query}', here's what I found:")
        
        # Add key findings
        high_priority_findings = [f for f in result.findings if f.get("severity") in ["critical", "high"]]
        if high_priority_findings:
            response_parts.append("\n**Key Points:**")
            for finding in high_priority_findings[:3]:  # Top 3 findings
                title = finding.get("title", "Finding")
                description = finding.get("description", "")
                if description:
                    response_parts.append(f"• {title}: {description[:200]}...")
                else:
                    response_parts.append(f"• {title}")
        
        # Add recommendations if available
        if result.recommendations:
            response_parts.append(f"\n**Recommendations:**")
            for rec in result.recommendations[:3]:  # Top 3 recommendations
                response_parts.append(f"• {rec}")
        
        return "\n".join(response_parts)
    
    def _extract_sources_for_chat(self, result: OrchestrationResult) -> List[Dict[str, Any]]:
        """Extract sources for chat interface"""
        sources = []
        
        for finding in result.findings:
            if finding.get("content"):
                sources.append({
                    "type": finding.get("type", "finding"),
                    "title": finding.get("title", "Source"),
                    "content": finding.get("content", "")[:300],  # Truncate for chat
                    "confidence": finding.get("confidence", 0.5)
                })
        
        return sources[:5]  # Limit to 5 sources
    
    def _generate_agent_trace(self, results: List[AgentResult], consolidated: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AWS Bedrock AgentCore compatible agent trace"""
        try:
            trace = {
                "orchestrator_version": self.version,
                "execution_strategy": "comprehensive" if len(results) > 1 else "single_agent",
                "agent_executions": [],
                "consolidation_summary": {
                    "total_findings": len(consolidated.get("findings", [])),
                    "confidence_score": consolidated.get("confidence", 0.0),
                    "success_rate": len([r for r in results if r.status == AgentStatus.COMPLETED]) / max(1, len(results))
                },
                "bedrock_compatibility": {
                    "framework_version": "docushield_v3",
                    "agent_types": list(self.agents.keys()),
                    "migration_ready": True
                }
            }
            
            for result in results:
                trace["agent_executions"].append({
                    "agent_name": result.agent_name,
                    "agent_version": result.agent_version,
                    "status": result.status.value,
                    "confidence": result.confidence,
                    "execution_time_ms": result.execution_time_ms,
                    "llm_calls": result.llm_calls,
                    "findings_count": len(result.findings),
                    "data_sources": result.data_sources
                })
            
            return trace
            
        except Exception as e:
            self.logger.error(f"Agent trace generation failed: {e}")
            return {"error": "Trace generation failed", "bedrock_compatibility": {"migration_ready": False}}
    
    async def run_comprehensive_analysis(
        self,
        contract_id: str,
        user_id: str,
        query: Optional[str] = None,
        selected_agents: Optional[List[str]] = None,
        timeout_seconds: int = 120
    ) -> OrchestrationResult:
        """
        Run comprehensive analysis (backward compatibility method)
        AWS Bedrock AgentCore compatible
        """
        return await self.process_request(
            contract_id=contract_id,
            user_id=user_id,
            query=query,
            priority=AgentPriority.HIGH,
            timeout_seconds=timeout_seconds
        )
    
    def get_bedrock_compatibility_info(self) -> Dict[str, Any]:
        """Get AWS Bedrock AgentCore compatibility information"""
        return {
            "compatible": True,
            "version": self.version,
            "agent_metadata": self.agent_metadata,
            "supported_operations": [
                "document_search",
                "document_analysis",
                "clause_analysis", 
                "risk_analysis",
                "comprehensive_processing",
                "query_processing"
            ],
            "migration_requirements": {
                "bedrock_agent_runtime": ">=1.0.0",
                "agent_framework": "docushield_v3",
                "model_compatibility": ["claude-3", "gpt-4", "bedrock-titan"]
            },
            "agent_definitions": {
                agent_name: {
                    "type": agent.agent_name,
                    "version": agent.version,
                    "capabilities": ["analysis", "search", "summarization"]
                }
                for agent_name, agent in self.agents.items()
            }
        }

# Global instance - AWS Bedrock AgentCore compatible
document_orchestrator = DocumentOrchestrator()