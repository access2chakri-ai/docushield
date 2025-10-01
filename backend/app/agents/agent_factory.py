"""
Production Agent Factory - AWS Bedrock AgentCore Compatible
Centralized agent management with singleton pattern and standardized naming
Enterprise-grade architecture for agent lifecycle management
"""
# Import early_config first to ensure secrets are loaded from AWS Secrets Manager
import early_config

import os
import logging
from typing import Dict, Optional, Type, List, Any
from enum import Enum
from dataclasses import dataclass

from app.services.remote_agent import call_agent

logger = logging.getLogger(__name__)

# Configuration for remote agents
USE_REMOTE = os.getenv("USE_REMOTE_AGENTS", "").lower() == "true"

# Minimal base classes for remote agent wrapper
class AgentStatus:
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class AgentPriority:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

@dataclass
class AgentContext:
    contract_id: str
    user_id: str
    query: Optional[str] = None
    run_id: Optional[str] = None
    session_id: Optional[str] = None

@dataclass
class AgentResult:
    status: str
    confidence: float
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    llm_calls: int = 0
    data_sources: List[str] = None
    error_message: Optional[str] = None

class BaseAgent:
    def __init__(self, agent_name: str, version: str = "1.0.0"):
        self.agent_name = agent_name
        self.version = version
    
    def create_result(self, status=AgentStatus.COMPLETED, confidence=0.8, findings=None, 
                     recommendations=None, llm_calls=0, data_sources=None, error_message=None):
        return AgentResult(
            status=status,
            confidence=confidence,
            findings=findings or [],
            recommendations=recommendations or [],
            llm_calls=llm_calls,
            data_sources=data_sources or [],
            error_message=error_message
        )
    
    async def analyze(self, context):
        return await self._execute_analysis(context)
    
    async def _execute_analysis(self, context):
        raise NotImplementedError

class RemoteDocumentSearchAgent(BaseAgent):
    """Remote wrapper for DocumentSearchAgent that calls Dockerized agent via HTTP"""
    
    def __init__(self):
        super().__init__("document_search_agent_remote", "2.0.0")
    
    async def _execute_analysis(self, context: AgentContext):
        """Execute analysis by calling remote agent via HTTP"""
        try:
            payload = {
                "inputs": {
                    "query": context.query,
                    "contract_id": context.contract_id,
                    "user_id": context.user_id,
                    "top_k": getattr(context, "top_k", 5)
                },
                "session_id": getattr(context, "session_id", None),
                "request_id": getattr(context, "run_id", None)
            }
            
            # Call remote agent
            data = await call_agent("document-search", payload)
            
            # Map remote JSON back to AgentResult
            status_str = str(data.get("status", "")).upper()
            if status_str == "FAILED":
                return self.create_result(
                    status=AgentStatus.FAILED, 
                    error_message=data.get("error_message", "Remote agent failed")
                )
            
            return self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=data.get("confidence", 0.0),
                findings=data.get("findings", []),
                recommendations=data.get("recommendations", []),
                llm_calls=data.get("llm_calls", 0),
                data_sources=data.get("data_sources", [])
            )
            
        except Exception as e:
            logger.error(f"Remote agent call failed: {e}")
            return self.create_result(
                status=AgentStatus.FAILED,
                error_message=f"Remote agent error: {str(e)}"
            )

class AgentType(Enum):
    """AWS Bedrock AgentCore compatible agent types"""
    DOCUMENT_ANALYSIS = "document_analysis_agent"
    DOCUMENT_SEARCH = "document_search_agent"
    CLAUSE_ANALYSIS = "clause_analysis_agent"
    RISK_ANALYSIS = "risk_analysis_agent"

class AgentFactory:
    """
    Singleton factory for managing agent instances - AWS Bedrock AgentCore Compatible
    Provides standardized agent lifecycle management with enterprise-grade reliability
    """
    
    _instance = None
    _agents: Dict[str, BaseAgent] = {}
    _agent_metadata: Dict[str, Dict[str, Any]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentFactory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._initialize_agents()
            self._initialized = True
    
    def _initialize_agents(self):
        """Initialize existing agents only"""
        self._agents = {}
        logger.info(f"🔧 Agent Factory: USE_REMOTE_AGENTS = {USE_REMOTE}")
        
        # Try to initialize each agent individually
        try:
            from .document_analyzer import DocumentAnalysisAgent
            doc_agent = DocumentAnalysisAgent()
            self._agents.update({
                AgentType.DOCUMENT_ANALYSIS.value: doc_agent,
                'document_analyzer': doc_agent,
                'enhanced_analyzer': doc_agent,
                'simple_analyzer': doc_agent,
            })
            logger.info("✅ Document Analysis Agent initialized")
        except Exception as e:
            logger.error(f"❌ Document Analysis Agent failed: {e}")
        
        try:
            if USE_REMOTE:
                search_agent = RemoteDocumentSearchAgent()
                logger.info("✅ Remote Document Search Agent initialized")
                self._agents.update({
                    AgentType.DOCUMENT_SEARCH.value: search_agent,
                    'search_agent': search_agent,
                })
            else:
                try:
                    from .search_agent import DocumentSearchAgent
                    search_agent = DocumentSearchAgent()
                    logger.info("✅ Local Document Search Agent initialized")
                    self._agents.update({
                        AgentType.DOCUMENT_SEARCH.value: search_agent,
                        'search_agent': search_agent,
                    })
                except ImportError as ie:
                    logger.warning(f"Local search agent import failed: {ie}, falling back to remote")
                    search_agent = RemoteDocumentSearchAgent()
                    logger.info("✅ Remote Document Search Agent initialized (fallback)")
                    self._agents.update({
                        AgentType.DOCUMENT_SEARCH.value: search_agent,
                        'search_agent': search_agent,
                    })
        except Exception as e:
            logger.error(f"❌ Document Search Agent failed: {e}")
        
        try:
            from .clause_analyzer_agent import ClauseAnalysisAgent
            clause_agent = ClauseAnalysisAgent()
            self._agents.update({
                AgentType.CLAUSE_ANALYSIS.value: clause_agent,
                'clause_analyzer': clause_agent,
            })
            logger.info("✅ Clause Analysis Agent initialized")
        except Exception as e:
            logger.error(f"❌ Clause Analysis Agent failed: {e}")
        
        try:
            from .risk_analyzer_agent import RiskAnalysisAgent
            risk_agent = RiskAnalysisAgent()
            self._agents.update({
                AgentType.RISK_ANALYSIS.value: risk_agent,
                'risk_analyzer': risk_agent,
            })
            logger.info("✅ Risk Analysis Agent initialized")
        except Exception as e:
            logger.error(f"❌ Risk Analysis Agent failed: {e}")
        
        # Store metadata for each agent
        for agent_name, agent in self._agents.items():
            self._agent_metadata[agent_name] = {
                'name': agent.agent_name,
                'version': agent.version,
                'type': type(agent).__name__,
                'bedrock_compatible': getattr(agent, 'bedrock_metadata', {}).get('bedrock_compatible', False),
                'capabilities': getattr(agent, 'bedrock_metadata', {}).get('capabilities', []),
                'supported_models': getattr(agent, 'bedrock_metadata', {}).get('supported_models', [])
            }
        
        logger.info(f"Initialized {len(set(self._agents.values()))} unique agents with {len(self._agents)} aliases")
    
    def get_agent(self, agent_identifier) -> Optional[BaseAgent]:
        """Get agent instance by name or type enum with fallback logic"""
        # Handle AgentType enum
        if isinstance(agent_identifier, AgentType):
            return self._agents.get(agent_identifier.value)
        
        # Handle string name
        agent_name = str(agent_identifier)
        
        # Try exact match first
        agent = self._agents.get(agent_name)
        if agent:
            return agent
        
        # Try enum value match
        try:
            agent_type = AgentType(agent_name)
            return self._agents.get(agent_type.value)
        except ValueError:
            pass
        
        # Try fuzzy matching for common variations
        name_lower = agent_name.lower()
        for key, agent in self._agents.items():
            if name_lower in key.lower() or key.lower() in name_lower:
                logger.info(f"Fuzzy matched '{agent_name}' to '{key}'")
                return agent
        
        logger.warning(f"Agent '{agent_name}' not found. Available: {list(self._agents.keys())}")
        return None
    
    def _create_agent(self, agent_type: AgentType) -> Optional[BaseAgent]:
        """Create new agent instance (for future dynamic creation)"""
        try:
            if agent_type == AgentType.DOCUMENT_ANALYSIS:
                from .document_analyzer import DocumentAnalysisAgent
                return DocumentAnalysisAgent()
            elif agent_type == AgentType.DOCUMENT_SEARCH:
                from .search_agent import DocumentSearchAgent
                return DocumentSearchAgent()
            elif agent_type == AgentType.CLAUSE_ANALYSIS:
                from .clause_analyzer_agent import ClauseAnalysisAgent
                return ClauseAnalysisAgent()
            elif agent_type == AgentType.RISK_ANALYSIS:
                from .risk_analyzer_agent import RiskAnalysisAgent
                return RiskAnalysisAgent()
            else:
                logger.error(f"Unknown agent type: {agent_type}")
                return None
        except ImportError as e:
            logger.error(f"Failed to create agent {agent_type}: {e}")
            return None
    
    def get_all_agents(self) -> Dict[str, BaseAgent]:
        """Get all available agents"""
        return self._agents.copy()
    
    def get_agent_info(self, agent_type: Optional[AgentType] = None) -> Dict[str, Any]:
        """Get information about all agents or specific agent type"""
        if agent_type is None:
            return self._agent_metadata.copy()
        return self._agent_metadata.get(agent_type.value, {})
    
    def is_agent_available(self, agent_name: str) -> bool:
        """Check if agent is available"""
        return agent_name in self._agents
    
    def get_available_agent_names(self) -> List[str]:
        """Get list of available agent names"""
        return list(self._agents.keys())
    
    def list_available_agents(self) -> List[Dict[str, Any]]:
        """List all available agents with metadata"""
        agents = []
        unique_agents = set()
        
        for name, agent in self._agents.items():
            agent_id = f"{agent.agent_name}_{agent.version}"
            if agent_id not in unique_agents:
                unique_agents.add(agent_id)
                agents.append({
                    'name': agent.agent_name,
                    'version': agent.version,
                    'type': type(agent).__name__,
                    'aliases': [k for k, v in self._agents.items() if v == agent],
                    'bedrock_compatible': getattr(agent, 'bedrock_metadata', {}).get('bedrock_compatible', False),
                    'capabilities': getattr(agent, 'bedrock_metadata', {}).get('capabilities', [])
                })
        
        return agents
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on all agents"""
        health_status = {
            'total_agents': len(set(self._agents.values())),
            'total_aliases': len(self._agents),
            'healthy_agents': 0,
            'failed_agents': 0,
            'agent_status': {}
        }
        
        unique_agents = set(self._agents.values())
        for agent in unique_agents:
            try:
                # Simple health check - verify agent has required attributes
                if hasattr(agent, 'agent_name') and hasattr(agent, 'version'):
                    health_status['healthy_agents'] += 1
                    health_status['agent_status'][agent.agent_name] = 'healthy'
                else:
                    health_status['failed_agents'] += 1
                    health_status['agent_status'][agent.agent_name] = 'unhealthy'
            except Exception as e:
                health_status['failed_agents'] += 1
                health_status['agent_status'][agent.agent_name] = f'error: {str(e)}'
        
        return health_status
    
    def reset_agents(self):
        """Reset and reinitialize all agents"""
        self._agents.clear()
        self._agent_metadata.clear()
        self._initialize_agents()
        logger.info("Agent factory reset and reinitialized")
    
    def _get_agent_description(self, agent_type: AgentType) -> str:
        """Get human-readable description of agent"""
        descriptions = {
            AgentType.DOCUMENT_ANALYSIS: "Comprehensive document analysis including content extraction, risk assessment, and insights generation",
            AgentType.DOCUMENT_SEARCH: "Semantic and keyword-based document search with intelligent result ranking",
            AgentType.CLAUSE_ANALYSIS: "Specialized analysis of contract clauses, terms, and legal provisions",
            AgentType.RISK_ANALYSIS: "Risk assessment and compliance analysis for documents and contracts"
        }
        return descriptions.get(agent_type, "General document processing agent")
    
    # Orchestrator integration methods
    async def quick_analysis(
        self, 
        contract_id: str, 
        user_id: str,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Quick analysis using document analysis agent"""
        try:
            agent = self.get_agent(AgentType.DOCUMENT_ANALYSIS)
            if not agent:
                return {"success": False, "error": "Document analysis agent not available"}
            
            from .base_agent import AgentContext, AgentPriority
            context = AgentContext(
                contract_id=contract_id,
                user_id=user_id,
                document_type=document_type,
                priority=AgentPriority.MEDIUM,
                timeout_seconds=30
            )
            
            result = await agent.analyze(context)
            
            return {
                "success": result.success,
                "confidence": result.confidence,
                "findings": result.findings,
                "recommendations": result.recommendations,
                "execution_time_ms": result.execution_time_ms
            }
            
        except Exception as e:
            logger.error(f"Quick analysis failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def quick_search(
        self, 
        query: str, 
        contract_id: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """Quick search using document search agent"""
        try:
            agent = self.get_agent(AgentType.DOCUMENT_SEARCH)
            if not agent:
                return {"success": False, "error": "Document search agent not available"}
            
            from .base_agent import AgentContext, AgentPriority
            context = AgentContext(
                contract_id=contract_id,
                user_id=user_id,
                query=query,
                priority=AgentPriority.MEDIUM,
                timeout_seconds=30
            )
            
            result = await agent.analyze(context)
            
            return {
                "success": result.success,
                "confidence": result.confidence,
                "findings": result.findings,
                "recommendations": result.recommendations,
                "execution_time_ms": result.execution_time_ms
            }
            
        except Exception as e:
            logger.error(f"Quick search failed: {e}")
            return {"success": False, "error": str(e)}
    
    def get_document_search_agent(self):
        """Get document search agent (local or remote based on configuration)"""
        return self.get_agent(AgentType.DOCUMENT_SEARCH)
    
    def get_orchestrator(self):
        """Get the document orchestrator instance"""
        from .orchestrator import document_orchestrator
        return document_orchestrator

# Global singleton instance
agent_factory = AgentFactory()