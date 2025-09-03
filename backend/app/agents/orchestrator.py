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
from app.database import get_operational_db
from app.models import ProcessingRun, ProcessingStep

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
