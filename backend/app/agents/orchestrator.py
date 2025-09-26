"""
Agent Orchestrator - Coordinates multiple specialized agents
Manages workflow, data flow, and result synthesis across all agents
"""
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from .base_agent import BaseAgent, AgentContext, AgentResult
from .search_agent import SearchAgent
from .clause_analyzer_agent import ClauseAnalyzerAgent
from .simple_analyzer_agent import SimpleAnalyzerAgent
from .enhanced_analyzer_agent import EnhancedAnalyzerAgent
from app.database import get_operational_db
from app.models import ProcessingRun, ProcessingStep
from sqlalchemy import text

logger = logging.getLogger(__name__)

@dataclass
class OrchestrationResult:
    """Complete orchestration result"""
    run_id: str
    contract_id: str
    user_id: str
    query: Optional[str]
    overall_success: bool
    overall_confidence: float
    agent_results: List[AgentResult]
    consolidated_findings: List[Dict[str, Any]]
    consolidated_recommendations: List[str]
    execution_time_ms: float
    total_llm_calls: int
    workflow_version: str

class AgentOrchestrator:
    """
    Orchestrates multiple specialized agents for comprehensive document analysis
    Manages the complete workflow and ensures all TiDB tables are utilized
    """
    
    def __init__(self):
        # Initialize all agents
        self.agents = {
            "search": SearchAgent(),
            "clause_analyzer": ClauseAnalyzerAgent(),
            "simple_analyzer": SimpleAnalyzerAgent(),
            "enhanced_analyzer": EnhancedAnalyzerAgent(),
            # Additional agents can be added here
        }
        
        self.workflow_version = "3.0.0"
        self.logger = logging.getLogger("orchestrator")
    
    async def run_comprehensive_analysis(
        self, 
        contract_id: str, 
        user_id: str,
        query: Optional[str] = None,
        selected_agents: List[str] = None,
        timeout_seconds: int = 120
    ) -> OrchestrationResult:
        """
        Run comprehensive analysis using multiple agents with timeout
        """
        start_time = datetime.now()
        
        # Add overall timeout to prevent hanging
        import asyncio
        try:
            return await asyncio.wait_for(
                self._run_comprehensive_analysis_impl(contract_id, user_id, query, selected_agents),
                timeout=timeout_seconds
            )
        except asyncio.TimeoutError:
            self.logger.error(f"Analysis timeout after {timeout_seconds}s for contract {contract_id}")
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Return timeout error result
            return OrchestrationResult(
                run_id=f"timeout_{contract_id}",
                contract_id=contract_id,
                user_id=user_id,
                query=query,
                overall_success=False,
                overall_confidence=0.0,
                agent_results=[],
                consolidated_findings=[{
                    "type": "timeout_error",
                    "title": "Analysis timeout",
                    "description": f"Analysis timed out after {timeout_seconds} seconds",
                    "severity": "high",
                    "confidence": 1.0,
                    "source_agent": "orchestrator"
                }],
                consolidated_recommendations=["Manual analysis required due to system timeout"],
                execution_time_ms=execution_time,
                total_llm_calls=0,
                workflow_version=self.workflow_version
            )
    
    async def _run_comprehensive_analysis_impl(
        self, 
        contract_id: str, 
        user_id: str,
        query: Optional[str] = None,
        selected_agents: List[str] = None
    ) -> OrchestrationResult:
        """
        Internal implementation of comprehensive analysis
        """
        start_time = datetime.now()
        
        # Create processing run record
        self.logger.info(f"Creating processing run for contract {contract_id}")
        run_id = await self.create_processing_run(contract_id, user_id, query)
        self.logger.info(f"Created processing run {run_id}")
        
        try:
            # Determine which agents to run
            agents_to_run = selected_agents or list(self.agents.keys())
            self.logger.info(f"Running agents: {agents_to_run}")
            
            # Create shared context
            context = AgentContext(
                contract_id=contract_id,
                user_id=user_id,
                query=query,
                metadata={"run_id": run_id, "workflow_version": self.workflow_version}
            )
            self.logger.info(f"Created context for contract {contract_id}")
            
            # Execute agents in optimal order
            self.logger.info(f"Starting agent workflow execution for contract {contract_id}")
            agent_results = await self.execute_agent_workflow(context, agents_to_run)
            self.logger.info(f"Agent workflow completed, got {len(agent_results)} results")
            
            # Consolidate results
            self.logger.info(f"Consolidating results for contract {contract_id}")
            consolidated_findings = self.consolidate_findings(agent_results)
            consolidated_recommendations = self.consolidate_recommendations(agent_results)
            self.logger.info(f"Consolidated {len(consolidated_findings)} findings and {len(consolidated_recommendations)} recommendations")
            
            # Calculate overall metrics
            overall_success = all(result.success for result in agent_results)
            overall_confidence = sum(result.confidence for result in agent_results) / len(agent_results) if agent_results else 0.0
            total_llm_calls = sum(result.llm_calls for result in agent_results)
            
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Update processing run
            await self.update_processing_run(run_id, "completed", execution_time)
            
            # Create orchestration result
            result = OrchestrationResult(
                run_id=run_id,
                contract_id=contract_id,
                user_id=user_id,
                query=query,
                overall_success=overall_success,
                overall_confidence=overall_confidence,
                agent_results=agent_results,
                consolidated_findings=consolidated_findings,
                consolidated_recommendations=consolidated_recommendations,
                execution_time_ms=execution_time,
                total_llm_calls=total_llm_calls,
                workflow_version=self.workflow_version
            )
            
            self.logger.info(f"Comprehensive analysis completed for {contract_id} in {execution_time:.2f}ms")
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"Orchestration failed for {contract_id}: {e}")
            
            # Update processing run with error
            await self.update_processing_run(run_id, "failed", execution_time, str(e))
            
            # Return error result
            return OrchestrationResult(
                run_id=run_id,
                contract_id=contract_id,
                user_id=user_id,
                query=query,
                overall_success=False,
                overall_confidence=0.0,
                agent_results=[],
                consolidated_findings=[{"error": f"Orchestration failed: {str(e)}"}],
                consolidated_recommendations=["Manual analysis required due to system error"],
                execution_time_ms=execution_time,
                total_llm_calls=0,
                workflow_version=self.workflow_version
            )
    
    async def execute_agent_workflow(
        self, 
        context: AgentContext, 
        agent_names: List[str]
    ) -> List[AgentResult]:
        """
        Execute agents in optimal order with dependency management
        """
        agent_results = []
        
        try:
            # Phase 1: Independent agents (can run in parallel)
            independent_agents = []
            
            if "search" in agent_names:
                independent_agents.append(("search", self.agents["search"]))
            if "clause_analyzer" in agent_names:
                independent_agents.append(("clause_analyzer", self.agents["clause_analyzer"]))
            if "enhanced_analyzer" in agent_names:
                independent_agents.append(("enhanced_analyzer", self.agents["enhanced_analyzer"]))
            
            # Run independent agents in parallel
            if independent_agents:
                tasks = []
                for agent_name, agent in independent_agents:
                    task = self.run_agent_with_tracking(agent_name, agent, context)
                    tasks.append(task)
                
                parallel_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for result in parallel_results:
                    if isinstance(result, Exception):
                        self.logger.error(f"Agent execution failed: {result}")
                        # Create error result
                        error_result = AgentResult(
                            agent_name="unknown",
                            success=False,
                            confidence=0.0,
                            findings=[],
                            recommendations=[],
                            data_used={},
                            execution_time_ms=0.0,
                            llm_calls=0,
                            error_message=str(result)
                        )
                        agent_results.append(error_result)
                    else:
                        agent_results.append(result)
            
            # Phase 2: Dependent agents (run after independent agents complete)
            # Update context with results from previous phase
            context.previous_results = {
                result.agent_name: asdict(result) for result in agent_results if result.success
            }
            
            # Additional dependent agents would go here
            # For now, we have independent agents only
            
            return agent_results
            
        except Exception as e:
            self.logger.error(f"Agent workflow execution failed: {e}")
            return []
    
    async def run_agent_with_tracking(
        self, 
        agent_name: str, 
        agent: BaseAgent, 
        context: AgentContext
    ) -> AgentResult:
        """
        Run individual agent with tracking and error handling
        """
        start_time = datetime.now()
        
        try:
            # Create processing step record
            step_id = await self.create_processing_step(
                context.metadata["run_id"], 
                agent_name, 
                "running"
            )
            
            # Execute agent
            result = await agent.analyze(context)
            
            # Update step record
            await self.update_processing_step(
                step_id, 
                "completed" if result.success else "failed",
                result.execution_time_ms,
                result.error_message
            )
            
            return result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            self.logger.error(f"Agent {agent_name} execution failed: {e}")
            
            # Update step record with error
            if 'step_id' in locals():
                await self.update_processing_step(step_id, "failed", execution_time, str(e))
            
            # Return error result
            return AgentResult(
                agent_name=agent_name,
                success=False,
                confidence=0.0,
                findings=[],
                recommendations=[f"{agent_name} analysis failed: {str(e)}"],
                data_used={},
                execution_time_ms=execution_time,
                llm_calls=0,
                error_message=str(e)
            )
    
    def consolidate_findings(self, agent_results: List[AgentResult]) -> List[Dict[str, Any]]:
        """
        Consolidate findings from all agents, removing duplicates and ranking by importance
        """
        all_findings = []
        
        for result in agent_results:
            if result.success:
                for finding in result.findings:
                    # Add agent source to finding
                    finding_with_source = {
                        **finding,
                        "source_agent": result.agent_name,
                        "agent_confidence": result.confidence
                    }
                    all_findings.append(finding_with_source)
        
        # Sort by severity and confidence
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
        
        sorted_findings = sorted(
            all_findings,
            key=lambda x: (
                severity_order.get(x.get("severity", "low"), 1),
                x.get("confidence", 0.0)
            ),
            reverse=True
        )
        
        return sorted_findings
    
    def consolidate_recommendations(self, agent_results: List[AgentResult]) -> List[str]:
        """
        Consolidate recommendations from all agents, removing duplicates
        """
        all_recommendations = []
        
        for result in agent_results:
            if result.success:
                for rec in result.recommendations:
                    # Add agent prefix for clarity
                    prefixed_rec = f"[{result.agent_name}] {rec}"
                    all_recommendations.append(prefixed_rec)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in all_recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)
        
        return unique_recommendations[:15]  # Limit to 15 recommendations
    
    # =============================================================================
    # DATABASE TRACKING METHODS
    # =============================================================================
    
    async def create_processing_run(
        self, 
        contract_id: str, 
        user_id: str, 
        query: Optional[str] = None
    ) -> str:
        """Create processing run record"""
        async for db in get_operational_db():
            run = ProcessingRun(
                contract_id=contract_id,
                pipeline_version=self.workflow_version,
                trigger="orchestrator",
                status="running"
            )
            
            db.add(run)
            await db.commit()
            await db.refresh(run)
            
            return run.run_id
    
    async def update_processing_run(
        self, 
        run_id: str, 
        status: str, 
        execution_time: float,
        error_message: Optional[str] = None
    ):
        """Update processing run record"""
        async for db in get_operational_db():
            result = await db.execute(
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
    
    async def create_processing_step(
        self, 
        run_id: str, 
        step_name: str, 
        status: str
    ) -> str:
        """Create processing step record"""
        async for db in get_operational_db():
            step = ProcessingStep(
                run_id=run_id,
                step_name=step_name,
                step_order=1,  # Could be calculated based on workflow
                status=status,
                started_at=datetime.utcnow()
            )
            
            db.add(step)
            await db.commit()
            await db.refresh(step)
            
            return step.step_id
    
    async def update_processing_step(
        self, 
        step_id: str, 
        status: str, 
        execution_time: float,
        error_message: Optional[str] = None
    ):
        """Update processing step record"""
        async for db in get_operational_db():
            await db.execute(
                text("""
                    UPDATE processing_steps 
                    SET status = :status,
                        completed_at = NOW(),
                        error_message = :error_message
                    WHERE step_id = :step_id
                """),
                {
                    "step_id": step_id,
                    "status": status,
                    "error_message": error_message
                }
            )
            await db.commit()
    
    # =============================================================================
    # QUERY PROCESSING FOR CHAT
    # =============================================================================
    
    async def process_query(
        self,
        query: str,
        user_id: str,
        document_id: Optional[str] = None,
        conversation_history: List[Dict[str, Any]] = None,
        document_types: Optional[List[str]] = None,
        industry_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Process a user query for chat interface with intelligent routing and enhanced context
        """
        try:
            self.logger.info(f"Processing query: {query[:100]}... for user {user_id}, document: {document_id}")
            
            # Import query processor
            from .query_processor import query_processor
            
            # Analyze the query to understand intent and requirements
            user_context = {
                "user_id": user_id, 
                "document_id": document_id,
                "document_types": document_types,
                "industry_types": industry_types
            }
            query_analysis = await query_processor.analyze_query(query, user_context)
            
            self.logger.info(f"Query analysis: type={query_analysis.query_type.value}, intent={query_analysis.intent.value}, confidence={query_analysis.confidence}")
            
            # Route based on query analysis
            if query_analysis.query_type.value == "help":
                return await self._handle_help_query(query, query_analysis)
            elif query_analysis.query_type.value == "general_info" and not document_id:
                return await self._handle_general_info_query(query, query_analysis, user_id)
            elif query_analysis.requires_document and not document_id:
                # Need document but none provided - find best match
                document_id = await self._find_best_document(query, user_id, query_analysis)
                if not document_id:
                    return await self._handle_no_document_available(query, user_id)
            
            # If document_id is provided or found, run targeted analysis with enhanced context
            if document_id:
                # First, verify document exists and get basic info
                async for db in get_operational_db():
                    from sqlalchemy import select
                    from app.models import BronzeContract
                    
                    result = await db.execute(
                        select(BronzeContract)
                        .where(BronzeContract.contract_id == document_id)
                        .where(BronzeContract.owner_user_id == user_id)
                    )
                    contract = result.scalar_one_or_none()
                    
                    if not contract:
                        return {
                            "response": f"I couldn't find the specified document. Please make sure you have access to it and try again.",
                            "sources": [],
                            "confidence": 0.0,
                            "error": "Document not found"
                        }
                
                # Run comprehensive analysis with better context
                result = await self.run_comprehensive_analysis(
                    contract_id=document_id,
                    user_id=user_id,
                    query=query,
                    selected_agents=query_analysis.suggested_agents
                )
                
                # Generate enhanced response with document context
                response_text = self._generate_intelligent_response(result, query, query_analysis)
                
                # Add document context to the response
                if contract:
                    context_prefix = f"**Analyzing: {contract.filename}**\n\n"
                    response_text = context_prefix + response_text
                
                # Convert orchestration result to chat response format
                return {
                    "response": response_text,
                    "sources": self._extract_sources(result),
                    "confidence": result.overall_confidence,
                    "run_id": result.run_id,
                    "document_context": {
                        "document_id": document_id,
                        "filename": contract.filename,
                        "status": contract.status
                    },
                    "query_analysis": {
                        "type": query_analysis.query_type.value,
                        "intent": query_analysis.intent.value,
                        "confidence": query_analysis.confidence
                    },
                    "agent_results": [asdict(r) for r in result.agent_results]
                }
            else:
                # No specific document - search across user's documents
                return await self._process_general_query(query, user_id, conversation_history, query_analysis)
                
        except Exception as e:
            self.logger.error(f"Query processing failed: {e}")
            return {
                "response": f"I encountered an error processing your question: {str(e)}. Please try again or rephrase your question.",
                "sources": [],
                "confidence": 0.0,
                "error": str(e)
            }
    
    async def _handle_help_query(self, query: str, query_analysis) -> Dict[str, Any]:
        """Handle help and guidance queries"""
        help_response = """
🤖 **DocuShield AI Assistant Help**

I can help you with:

📋 **Document Analysis:**
• "Summarize this contract" - Get key points and overview
• "What are the high-risk clauses?" - Identify problematic terms
• "Find liability clauses" - Search for specific clause types

⚖️ **Risk Assessment:**
• "Is this contract safe to sign?" - Get risk evaluation
• "What should I worry about?" - Highlight concerns
• "Rate the risk level" - Overall risk scoring

🔍 **Specific Questions:**
• "What does clause 5 say about termination?" - Explain specific terms
• "How much notice is required?" - Find specific details
• "Who pays for damages?" - Understand obligations

📊 **Document Stats:**
• "How many pages is this?" - Basic document info
• "When was this created?" - Metadata questions

💡 **Recommendations:**
• "Should I sign this?" - Get advice
• "What changes should I request?" - Negotiation points

**Tips:**
• Be specific about what you want to know
• Reference specific documents when possible
• Ask follow-up questions for more details
        """
        
        return {
            "response": help_response,
            "sources": [],
            "confidence": 1.0,
            "query_type": "help"
        }
    
    async def _handle_general_info_query(self, query: str, query_analysis, user_id: str) -> Dict[str, Any]:
        """Handle general information queries"""
        # Get user's document count for context
        async for db in get_operational_db():
            from sqlalchemy import select, func
            from app.models import BronzeContract
            
            result = await db.execute(
                select(func.count(BronzeContract.contract_id))
                .where(BronzeContract.owner_user_id == user_id)
            )
            doc_count = result.scalar() or 0
            
            processed_result = await db.execute(
                select(func.count(BronzeContract.contract_id))
                .where(BronzeContract.owner_user_id == user_id)
                .where(BronzeContract.status == "completed")
            )
            processed_count = processed_result.scalar() or 0
            
        response = f"""
📊 **Your DocuShield Account Overview**

📁 **Documents:** {doc_count} total documents uploaded
✅ **Processed:** {processed_count} documents analyzed
⏳ **Pending:** {doc_count - processed_count} awaiting analysis

💡 **What I can help you with:**
• Ask questions about your processed documents
• Get risk assessments and summaries
• Find specific clauses or terms
• Compare different contracts
• Get recommendations for contract decisions

**Try asking:**
• "What are the risks in my latest contract?"
• "Summarize my recent agreement"
• "Find all liability clauses"
• "Should I be concerned about anything?"

Need help with a specific document? Upload it first, then ask me questions about it!
        """
        
        return {
            "response": response,
            "sources": [],
            "confidence": 0.9,
            "query_type": "general_info"
        }
    
    async def _find_best_document(self, query: str, user_id: str, query_analysis) -> Optional[str]:
        """Find the most relevant document for the query"""
        try:
            async for db in get_operational_db():
                from sqlalchemy import select
                from app.models import BronzeContract
                
                # Get user's most recent processed document as fallback
                result = await db.execute(
                    select(BronzeContract)
                    .where(BronzeContract.owner_user_id == user_id)
                    .where(BronzeContract.status == "completed")
                    .order_by(BronzeContract.created_at.desc())
                    .limit(1)
                )
                recent_contract = result.scalar_one_or_none()
                
                if recent_contract:
                    return recent_contract.contract_id
                
        except Exception as e:
            self.logger.error(f"Error finding best document: {e}")
        
        return None
    
    async def _handle_no_document_available(self, query: str, user_id: str) -> Dict[str, Any]:
        """Handle case where no documents are available"""
        return {
            "response": """
📭 **No Documents Available**

I'd love to help answer your question, but I don't see any processed documents in your account yet.

**To get started:**
1. 📤 Upload a document (contract, agreement, policy, etc.)
2. ⏳ Wait for processing to complete
3. 🤖 Ask me questions about it!

**Example questions you can ask after uploading:**
• "What are the key terms in this contract?"
• "Are there any high-risk clauses?"
• "Summarize this agreement"
• "What should I be careful about?"

Upload your first document and I'll be ready to help analyze it! 🚀
            """,
            "sources": [],
            "confidence": 1.0,
            "query_type": "no_documents"
        }
    
    def _generate_intelligent_response(self, result: OrchestrationResult, original_query: str, query_analysis) -> str:
        """Generate intelligent response based on query analysis"""
        try:
            # Use query analysis to format response appropriately
            if query_analysis.response_format == "numbered_list":
                return self._generate_list_response(result, original_query, query_analysis)
            elif query_analysis.response_format == "count_with_details":
                return self._generate_count_response(result, original_query, query_analysis)
            elif query_analysis.response_format == "structured_summary":
                return self._generate_summary_response(result, original_query, query_analysis)
            elif query_analysis.response_format == "risk_assessment":
                return self._generate_risk_response(result, original_query, query_analysis)
            else:
                return self._generate_conversational_response(result, original_query, query_analysis)
        except Exception as e:
            self.logger.error(f"Intelligent response generation failed: {e}")
            # Fallback to original method
            return self._generate_chat_response(result, original_query)
    
    def _generate_list_response(self, result: OrchestrationResult, query: str, analysis) -> str:
        """Generate a numbered list response"""
        response_parts = []
        
        if "high-risk" in query.lower() or "risk" in query.lower():
            high_risk_findings = [f for f in result.consolidated_findings if f.get('severity') in ['critical', 'high']]
            
            if high_risk_findings:
                response_parts.append(f"🚨 **Found {len(high_risk_findings)} High-Risk Items:**\n")
                for i, finding in enumerate(high_risk_findings, 1):
                    title = finding.get('title', 'Risk Item')
                    desc = finding.get('description', 'Requires attention')
                    severity = finding.get('severity', 'high')
                    emoji = "🚨" if severity == "critical" else "⚠️"
                    response_parts.append(f"{i}. {emoji} **{title}:** {desc}")
            else:
                response_parts.append("✅ **No High-Risk Items Found**\nThis document appears to have acceptable risk levels.")
        
        elif "clause" in query.lower():
            all_findings = result.consolidated_findings
            if all_findings:
                response_parts.append(f"📋 **Found {len(all_findings)} Relevant Clauses:**\n")
                for i, finding in enumerate(all_findings[:15], 1):  # Limit to 15
                    title = finding.get('title', 'Clause')
                    desc = finding.get('description', 'See details')
                    response_parts.append(f"{i}. **{title}:** {desc}")
            else:
                response_parts.append("📋 **No Specific Clauses Found**\nTry asking about specific clause types like 'liability' or 'termination'.")
        
        # Add summary info
        response_parts.append(f"\n📊 **Analysis:** {result.execution_time_ms:.0f}ms • {result.overall_confidence:.0%} confidence")
        
        return "\n".join(response_parts)
    
    def _generate_count_response(self, result: OrchestrationResult, query: str, analysis) -> str:
        """Generate a count-focused response"""
        response_parts = []
        
        # Count different types of findings
        high_risk_count = len([f for f in result.consolidated_findings if f.get('severity') in ['critical', 'high']])
        medium_risk_count = len([f for f in result.consolidated_findings if f.get('severity') == 'medium'])
        low_risk_count = len([f for f in result.consolidated_findings if f.get('severity') == 'low'])
        total_findings = len(result.consolidated_findings)
        
        response_parts.append("📊 **Document Analysis Count:**")
        response_parts.append(f"• **Total Findings:** {total_findings}")
        response_parts.append(f"• **High Risk:** {high_risk_count} items")
        response_parts.append(f"• **Medium Risk:** {medium_risk_count} items")
        response_parts.append(f"• **Low Risk:** {low_risk_count} items")
        
        if high_risk_count > 0:
            response_parts.append(f"\n⚠️ **{high_risk_count} High-Risk Items Need Attention:**")
            high_risk_findings = [f for f in result.consolidated_findings if f.get('severity') in ['critical', 'high']]
            for i, finding in enumerate(high_risk_findings[:5], 1):  # Show top 5
                title = finding.get('title', 'Risk Item')
                response_parts.append(f"{i}. {title}")
        
        return "\n".join(response_parts)
    
    def _generate_summary_response(self, result: OrchestrationResult, query: str, analysis) -> str:
        """Generate a structured summary response"""
        # Use the existing summary logic but with enhanced structure
        return self._generate_chat_response(result, query)
    
    def _generate_risk_response(self, result: OrchestrationResult, query: str, analysis) -> str:
        """Generate a risk assessment response"""
        response_parts = []
        
        # Risk overview
        high_risk_count = len([f for f in result.consolidated_findings if f.get('severity') in ['critical', 'high']])
        medium_risk_count = len([f for f in result.consolidated_findings if f.get('severity') == 'medium'])
        
        if high_risk_count > 0:
            response_parts.append("🚨 **HIGH RISK DOCUMENT**")
            response_parts.append(f"Found {high_risk_count} critical/high-risk issues requiring immediate attention.")
        elif medium_risk_count > 0:
            response_parts.append("⚠️ **MODERATE RISK DOCUMENT**")
            response_parts.append(f"Found {medium_risk_count} medium-risk items that should be reviewed.")
        else:
            response_parts.append("✅ **LOW RISK DOCUMENT**")
            response_parts.append("No significant risk factors identified.")
        
        # Show specific risks
        if high_risk_count > 0:
            response_parts.append("\n**🔍 Critical Issues:**")
            high_risk_findings = [f for f in result.consolidated_findings if f.get('severity') in ['critical', 'high']]
            for i, finding in enumerate(high_risk_findings[:5], 1):
                title = finding.get('title', 'Risk Item')
                desc = finding.get('description', 'Requires review')
                response_parts.append(f"{i}. **{title}:** {desc}")
        
        # Recommendations
        if result.consolidated_recommendations:
            response_parts.append("\n💡 **Recommendations:**")
            for rec in result.consolidated_recommendations[:3]:
                clean_rec = rec.replace('[search_agent]', '').replace('[clause_analyzer]', '').replace('[simple_analyzer]', '').strip()
                if clean_rec:
                    response_parts.append(f"• {clean_rec}")
        
        return "\n".join(response_parts)
    
    def _generate_conversational_response(self, result: OrchestrationResult, query: str, analysis) -> str:
        """Generate a conversational response"""
        # Use enhanced chat response logic
        return self._generate_chat_response(result, query)
    
    async def _process_general_query(
        self,
        query: str,
        user_id: str,
        conversation_history: List[Dict[str, Any]] = None,
        query_analysis = None
    ) -> Dict[str, Any]:
        """Process a general query across user's documents"""
        try:
            # Get user's recent documents
            async for db in get_operational_db():
                from sqlalchemy import select
                from app.models import BronzeContract
                
                result = await db.execute(
                    select(BronzeContract)
                    .where(BronzeContract.owner_user_id == user_id)
                    .where(BronzeContract.status == "completed")
                    .order_by(BronzeContract.created_at.desc())
                    .limit(5)
                )
                recent_contracts = result.scalars().all()
                
                if not recent_contracts:
                    return {
                        "response": "I don't see any processed documents in your account yet. Please upload and process some documents first, then I'll be able to answer questions about them.",
                        "sources": [],
                        "confidence": 0.0
                    }
                
                # For now, run analysis on the most recent document
                # In a full implementation, this would do semantic search across all documents
                most_recent = recent_contracts[0]
                
                result = await self.run_comprehensive_analysis(
                    contract_id=most_recent.contract_id,
                    user_id=user_id,
                    query=query
                )
                
                response = f"Based on your most recent document '{most_recent.filename}', here's what I found:\n\n"
                response += self._generate_chat_response(result, query)
                
                if len(recent_contracts) > 1:
                    response += f"\n\nNote: I analyzed your most recent document. You have {len(recent_contracts)} processed documents total. For more comprehensive analysis, please specify a particular document."
                
                return {
                    "response": response,
                    "sources": self._extract_sources(result),
                    "confidence": result.overall_confidence * 0.8,  # Reduce confidence for general queries
                    "run_id": result.run_id,
                    "analyzed_document": most_recent.filename
                }
                
        except Exception as e:
            self.logger.error(f"General query processing failed: {e}")
            return {
                "response": "I encountered an error while searching your documents. Please try again or be more specific about which document you'd like me to analyze.",
                "sources": [],
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _generate_chat_response(self, result: OrchestrationResult, original_query: str) -> str:
        """Generate a natural language response from orchestration results"""
        try:
            if not result.overall_success:
                return f"I had trouble analyzing the document. {result.consolidated_findings[0].get('description', 'Please try again.')}"
            
            response_parts = []
            
            # Check if this is a summary request
            is_summary_request = any(word in original_query.lower() for word in ['summarize', 'summary', 'key findings', 'overview', 'main points'])
            
            # Add main findings
            if result.consolidated_findings:
                if is_summary_request:
                    # For summary requests, show all relevant findings, not just high-priority
                    relevant_findings = [
                        f for f in result.consolidated_findings 
                        if f.get('severity') in ['high', 'critical', 'medium'] or f.get('type') in ['document_stats', 'clause_analysis']
                    ]
                    
                    if relevant_findings:
                        response_parts.append("🔍 **Document Summary:**")
                        
                        # Count findings by severity
                        high_risk = len([f for f in relevant_findings if f.get('severity') == 'high'])
                        critical_risk = len([f for f in relevant_findings if f.get('severity') == 'critical'])
                        medium_risk = len([f for f in relevant_findings if f.get('severity') == 'medium'])
                        low_risk = len([f for f in relevant_findings if f.get('severity') == 'low'])
                        
                        # Document overview
                        doc_stats = [f for f in relevant_findings if f.get('type') == 'document_stats']
                        if doc_stats:
                            stats = doc_stats[0]
                            word_count = stats.get('word_count', 'unknown')
                            response_parts.append(f"📄 **Document Overview:** {word_count} words analyzed")
                        
                        # Risk summary
                        if critical_risk > 0 or high_risk > 0:
                            total_high_risk = critical_risk + high_risk
                            response_parts.append(f"🚨 **High Risk Issues:** {total_high_risk} critical/high-risk clauses identified requiring immediate legal review")
                        
                        if medium_risk > 0:
                            response_parts.append(f"⚡ **Medium Risk Items:** {medium_risk} clauses need review for potential negotiation points")
                        
                        if low_risk > 0:
                            response_parts.append(f"✅ **Low Risk Items:** {low_risk} standard clauses with minimal concerns")
                        
                        # Show specific high-risk findings
                        high_risk_findings = [f for f in relevant_findings if f.get('severity') in ['critical', 'high']]
                        if high_risk_findings:
                            response_parts.append("\n**🔍 Key Risk Areas:**")
                            for i, finding in enumerate(high_risk_findings[:10], 1):  # Show up to 10
                                title = finding.get('title', 'Risk identified')
                                desc = finding.get('description', 'See detailed analysis')
                                severity = finding.get('severity', 'unknown')
                                emoji = {"critical": "🚨", "high": "⚠️"}.get(severity, "•")
                                response_parts.append(f"{i}. {emoji} **{title}:** {desc}")
                            
                            if len(high_risk_findings) > 10:
                                response_parts.append(f"... and {len(high_risk_findings) - 10} more risk items")
                        
                        # Overall assessment
                        if critical_risk > 0:
                            response_parts.append("\n🔴 **Overall Assessment:** HIGH RISK - Immediate legal consultation recommended before signing")
                        elif high_risk > 0:
                            response_parts.append("\n🟡 **Overall Assessment:** MEDIUM RISK - Review and negotiate key terms before proceeding")
                        elif medium_risk > 0:
                            response_parts.append("\n🟢 **Overall Assessment:** LOW-MEDIUM RISK - Standard contract with some negotiable terms")
                        else:
                            response_parts.append("\n✅ **Overall Assessment:** LOW RISK - Standard contract terms with minimal concerns")
                else:
                    # For non-summary requests, show relevant findings based on query
                    relevant_findings_for_query = []
                    query_lower = original_query.lower()
                    
                    # If asking about specific types or counts, show more findings
                    if any(word in query_lower for word in ['high-risk', 'high risk', 'clauses', 'what are', 'list', 'show']):
                        relevant_findings_for_query = [
                            f for f in result.consolidated_findings 
                            if f.get('severity') in ['high', 'critical', 'medium']
                        ]
                    else:
                        relevant_findings_for_query = [
                            f for f in result.consolidated_findings 
                            if f.get('severity') in ['high', 'critical']
                        ]
                    
                    if relevant_findings_for_query:
                        # Count high-risk items
                        high_risk_count = len([f for f in relevant_findings_for_query if f.get('severity') in ['high', 'critical']])
                        
                        if high_risk_count > 0:
                            response_parts.append(f"🚨 **HIGH RISK DOCUMENT**")
                            response_parts.append(f"Found {high_risk_count} critical/high-risk issues requiring immediate attention.")
                            response_parts.append("\n**🔍 Critical Issues:**")
                            
                            high_risk_items = [f for f in relevant_findings_for_query if f.get('severity') in ['high', 'critical']]
                            for i, finding in enumerate(high_risk_items[:10], 1):  # Show up to 10 items
                                title = finding.get('title', 'Risk identified')
                                desc = finding.get('description', 'See detailed analysis')
                                severity = finding.get('severity', 'unknown')
                                severity_emoji = {"critical": "🚨", "high": "⚠️"}.get(severity, '•')
                                
                                # Add more specific details if available
                                clause_type = finding.get('clause_type', '')
                                match_count = finding.get('match_count', 0)
                                matches = finding.get('matches', [])
                                
                                detail_parts = [desc]
                                if clause_type:
                                    detail_parts.append(f"Type: {clause_type}")
                                if match_count > 0:
                                    detail_parts.append(f"Found {match_count} instances")
                                if matches:
                                    detail_parts.append(f"Terms: {', '.join(matches[:3])}")
                                
                                full_desc = ' - '.join(detail_parts)
                                response_parts.append(f"{i}. {severity_emoji} **{title}:** {full_desc}")
                        
                        # Also show medium risk if query asks for comprehensive list
                        if 'clauses' in query_lower or 'list' in query_lower or 'show' in query_lower:
                            medium_risk_items = [f for f in relevant_findings_for_query if f.get('severity') == 'medium']
                            if medium_risk_items:
                                response_parts.append(f"\n**⚡ Medium-Risk Items ({len(medium_risk_items)} found):**")
                                for i, finding in enumerate(medium_risk_items[:10], 1):  # Show up to 10 medium risk
                                    title = finding.get('title', 'Issue identified')
                                    desc = finding.get('description', 'Requires review')
                                    response_parts.append(f"{i}. ⚡ **{title}:** {desc}")
                    else:
                        response_parts.append("✅ No high-risk clauses found in this document.")
            
            # Add recommendations
            if result.consolidated_recommendations:
                response_parts.append("\n💡 **Recommendations:**")
                for rec in result.consolidated_recommendations[:3]:  # Limit to top 3
                    clean_rec = rec.replace('[search_agent]', '').replace('[clause_analyzer]', '').replace('[simple_analyzer]', '').strip()
                    if clean_rec and not clean_rec.startswith('[') and not clean_rec.endswith(']'):
                        response_parts.append(f"• {clean_rec}")
            
            # Add summary for cases where no significant findings
            if not response_parts:
                if is_summary_request:
                    response_parts.append("📋 **Document Summary:**")
                    response_parts.append("✅ Document appears to be standard with no critical risk factors identified")
                    response_parts.append("✅ Basic analysis completed successfully")
                    response_parts.append("✅ No high-risk clauses requiring immediate attention")
                else:
                    # Check what the user was asking about
                    query_lower = original_query.lower()
                    if any(word in query_lower for word in ['high-risk', 'high risk', 'risk', 'clauses']):
                        response_parts.append("✅ **No High-Risk Clauses Found**")
                        response_parts.append("The document analysis didn't identify any clauses that require immediate attention. This suggests the document has standard, acceptable terms.")
                    else:
                        response_parts.append("I've analyzed the document and found it to be in good shape with no significant concerns or issues identified.")
            
            # Add execution info
            response_parts.append(f"\n📊 **Analysis Summary:** Processed in {result.execution_time_ms:.0f}ms using {len(result.agent_results)} specialized agents with {result.overall_confidence:.1%} confidence.")
            
            return "\n".join(response_parts)
            
        except Exception as e:
            self.logger.error(f"Response generation failed: {e}")
            return f"I analyzed the document but encountered an issue generating the response. The analysis found {len(result.consolidated_findings)} findings and {len(result.consolidated_recommendations)} recommendations."
    
    def _extract_sources(self, result: OrchestrationResult) -> List[Dict[str, Any]]:
        """Extract source information from orchestration results"""
        sources = []
        
        for agent_result in result.agent_results:
            if agent_result.success and agent_result.data_used:
                source = {
                    "agent": agent_result.agent_name,
                    "confidence": agent_result.confidence,
                    "data_points": len(agent_result.data_used),
                    "execution_time": agent_result.execution_time_ms
                }
                sources.append(source)
        
        return sources

    # =============================================================================
    # UTILITY METHODS
    # =============================================================================
    
    def get_available_agents(self) -> List[str]:
        """Get list of available agent names"""
        return list(self.agents.keys())
    
    def get_agent_info(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available agents"""
        info = {}
        for name, agent in self.agents.items():
            info[name] = {
                "name": agent.agent_name,
                "description": agent.__doc__ or "No description available",
                "capabilities": getattr(agent, "capabilities", [])
            }
        return info
    
    async def get_processing_history(self, contract_id: str) -> List[Dict[str, Any]]:
        """Get processing history for a contract"""
        async for db in get_operational_db():
            result = await db.execute(
                text("""
                    SELECT pr.*, ps.step_name, ps.status as step_status, ps.execution_time_ms
                    FROM processing_runs pr
                    LEFT JOIN processing_steps ps ON pr.run_id = ps.run_id
                    WHERE pr.contract_id = :contract_id
                    ORDER BY pr.started_at DESC, ps.step_order ASC
                """),
                {"contract_id": contract_id}
            )
            
            runs = []
            current_run = None
            
            for row in result:
                if not current_run or current_run["run_id"] != row.run_id:
                    if current_run:
                        runs.append(current_run)
                    
                    current_run = {
                        "run_id": row.run_id,
                        "pipeline_version": row.pipeline_version,
                        "trigger": row.trigger,
                        "status": row.status,
                        "started_at": row.started_at.isoformat() if row.started_at else None,
                        "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                        "steps": []
                    }
                
                if row.step_name:
                    current_run["steps"].append({
                        "step_name": row.step_name,
                        "status": row.step_status,
                        "execution_time_ms": row.execution_time_ms
                    })
            
            if current_run:
                runs.append(current_run)
            
            return runs
