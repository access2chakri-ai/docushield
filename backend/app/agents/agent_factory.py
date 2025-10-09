"""
Production Agent Factory - AWS Bedrock AgentCore Compatible
Centralized agent management with singleton pattern and standardized naming
Enterprise-grade architecture for agent lifecycle management
"""
# Import early_config first to ensure secrets are loaded from AWS Secrets Manager
import early_config

import os
import json
import logging
from typing import Dict, Optional, Type, List, Any
from enum import Enum
from dataclasses import dataclass

from app.services.remote_agent import call_agent
from app.services.agentcore import _invoke_agentcore_sync
from app.core.config import settings

logger = logging.getLogger(__name__)

# Configuration for remote agents
USE_REMOTE = os.getenv("USE_REMOTE_AGENTS", "").lower() == "true"

# Import from base_agent to ensure consistency
from app.agents.base_agent import AgentContext, AgentResult, AgentStatus, AgentPriority

class BaseAgent:
    def __init__(self, agent_name: str, version: str = "1.0.0"):
        self.agent_name = agent_name
        self.version = version
    
    def create_result(
        self, 
        status: AgentStatus = AgentStatus.COMPLETED,
        confidence: float = 0.8,
        findings: List[Dict[str, Any]] = None,
        recommendations: List[str] = None,
        data_sources: List[str] = None,
        execution_time_ms: float = 0.0,
        memory_usage_mb: float = 0.0,
        llm_calls: int = 0,
        error_message: str = None,
        session_id: str = None,
        trace_id: str = None
    ) -> AgentResult:
        """Create standardized agent result - AWS Bedrock AgentCore compatible"""
        return AgentResult(
            agent_name=self.agent_name,
            agent_version=self.version,
            status=status,
            confidence=confidence,
            findings=findings or [],
            recommendations=recommendations or [],
            execution_time_ms=execution_time_ms,
            memory_usage_mb=memory_usage_mb,
            llm_calls=llm_calls,
            data_sources=data_sources or [],
            error_message=error_message,
            session_id=session_id,
            trace_id=trace_id
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
                    error_message=data.get("error_message", "Remote agent failed"),
                    execution_time_ms=data.get("execution_time_ms", 0.0),
                    memory_usage_mb=data.get("memory_usage_mb", 0.0),
                    session_id=getattr(context, "session_id", None),
                    trace_id=getattr(context, "run_id", None)
                )
            
            return self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=data.get("confidence", 0.0),
                findings=data.get("findings", []),
                recommendations=data.get("recommendations", []),
                llm_calls=data.get("llm_calls", 0),
                data_sources=data.get("data_sources", []),
                execution_time_ms=data.get("execution_time_ms", 0.0),
                memory_usage_mb=data.get("memory_usage_mb", 0.0),
                session_id=getattr(context, "session_id", None),
                trace_id=getattr(context, "run_id", None)
            )
            
        except Exception as e:
            logger.error(f"Remote document search agent call failed: {e}")
            return self.create_result(
                status=AgentStatus.FAILED,
                error_message=f"Remote agent error: {str(e)}",
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                session_id=getattr(context, "session_id", None),
                trace_id=getattr(context, "run_id", None)
            )

class RemoteDocumentAnalysisAgent(BaseAgent):
    """Remote wrapper for DocumentAnalysisAgent that calls Dockerized agent via HTTP"""
    
    def __init__(self):
        super().__init__("document_analysis_agent_remote", "3.0.0")
    
    async def _execute_analysis(self, context: AgentContext):
        """Execute analysis by calling remote agent via HTTP"""
        try:
            payload = {
                "inputs": {
                    "contract_id": context.contract_id,
                    "user_id": context.user_id,
                    "query": context.query,
                    "document_type": getattr(context, "document_type", None),
                    "priority": str(getattr(context, "priority", "MEDIUM"))  # Convert to string
                },
                "session_id": getattr(context, "session_id", None),
                "request_id": getattr(context, "run_id", None)
            }
            
            # Call remote agent
            data = await call_agent("document-analysis", payload)
            
            # Map remote JSON back to AgentResult
            status_str = str(data.get("status", "")).upper()
            if status_str == "FAILED":
                return self.create_result(
                    status=AgentStatus.FAILED, 
                    error_message=data.get("error_message", "Remote agent failed"),
                    execution_time_ms=data.get("execution_time_ms", 0.0),
                    memory_usage_mb=data.get("memory_usage_mb", 0.0),
                    session_id=getattr(context, "session_id", None),
                    trace_id=getattr(context, "run_id", None)
                )
            
            return self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=data.get("confidence", 0.0),
                findings=data.get("findings", []),
                recommendations=data.get("recommendations", []),
                llm_calls=data.get("llm_calls", 0),
                data_sources=data.get("data_sources", []),
                execution_time_ms=data.get("execution_time_ms", 0.0),
                memory_usage_mb=data.get("memory_usage_mb", 0.0),
                session_id=getattr(context, "session_id", None),
                trace_id=getattr(context, "run_id", None)
            )
            
        except Exception as e:
            logger.error(f"Remote document analysis agent call failed: {e}")
            return self.create_result(
                status=AgentStatus.FAILED,
                error_message=f"Remote agent error: {str(e)}",
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                session_id=getattr(context, "session_id", None),
                trace_id=getattr(context, "run_id", None)
            )

class RemoteConversationalAgent(BaseAgent):
    """Remote wrapper for ConversationalAgent that calls Dockerized agent via HTTP"""
    
    def __init__(self):
        super().__init__("conversational_agent_remote", "2.0.0")
    
    async def _execute_analysis(self, context: AgentContext):
        """Execute analysis by calling remote conversational agent via HTTP"""
        try:
            # Extract metadata for conversational context
            metadata = getattr(context, "metadata", {})
            
            payload = {
                "inputs": {
                    "query": context.query,
                    "document_id": context.contract_id,
                    "user_id": context.user_id,
                    "document_type": getattr(context, "document_type", "contract"),
                    "chat_mode": metadata.get("chat_mode", "documents"),
                    "search_all_documents": metadata.get("search_all_documents", False),
                    "conversation_history": metadata.get("conversation_history", []),
                    "use_external_data": metadata.get("use_external_data", True),
                    "max_response_length": metadata.get("max_response_length", 1000)
                },
                "session_id": getattr(context, "session_id", None),
                "request_id": getattr(context, "run_id", None)
            }
            
            # Call remote conversational agent
            data = await call_agent("conversational-chat", payload)
            
            # Map remote JSON back to AgentResult
            status_str = str(data.get("status", "")).upper()
            if status_str == "FAILED":
                return self.create_result(
                    status=AgentStatus.FAILED, 
                    error_message=data.get("error_message", "Remote conversational agent failed"),
                    execution_time_ms=data.get("execution_time_ms", 0.0),
                    memory_usage_mb=data.get("memory_usage_mb", 0.0),
                    session_id=getattr(context, "session_id", None),
                    trace_id=getattr(context, "run_id", None)
                )
            
            # Extract conversational-specific data
            response_text = data.get("response", "")
            chat_mode = data.get("chat_mode", "documents")
            document_context = data.get("document_context", False)
            enhanced_with_external = data.get("enhanced_with_external", False)
            
            # Create result with conversational metadata
            result = self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=data.get("confidence", 0.0),
                findings=data.get("findings", []),
                recommendations=data.get("recommendations", []),
                llm_calls=data.get("llm_calls", 0),
                data_sources=data.get("data_sources", []),
                execution_time_ms=data.get("execution_time_ms", 0.0),
                memory_usage_mb=data.get("memory_usage_mb", 0.0),
                session_id=getattr(context, "session_id", None),
                trace_id=getattr(context, "run_id", None)
            )
            
            # Add conversational-specific attributes
            result.response = response_text
            result.chat_mode = chat_mode
            result.document_context = document_context
            result.enhanced_with_external = enhanced_with_external
            result.conversation_metadata = data.get("conversation_metadata", {})
            
            return result
            
        except Exception as e:
            logger.error(f"Remote conversational agent call failed: {e}")
            return self.create_result(
                status=AgentStatus.FAILED,
                error_message=f"Remote conversational agent error: {str(e)}",
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                session_id=getattr(context, "session_id", None),
                trace_id=getattr(context, "run_id", None)
            )

class AgentCoreDocumentSearchAgent(BaseAgent):
    """Wrapper that invokes an AgentCore Runtime agent by ARN."""
    
    def __init__(self):
        super().__init__("document_search_agentcore", "1.0.0")

    async def _execute_analysis(self, context: AgentContext):
        try:
            # Shape the prompt/payload your AgentCore expects.
            # You can pass any JSON your runtime handler understands.
            payload = {
                "query": context.query,
                "contract_id": context.contract_id,
                "user_id": context.user_id,
                "top_k": getattr(context, "top_k", 5),
            }
            # Because boto3 is sync, offload to a thread to avoid blocking the event loop
            import asyncio
            result = await asyncio.to_thread(
                _invoke_agentcore_sync, payload, getattr(context, "session_id", None), "search"
            )

            # Map generic response to your AgentResult
            if isinstance(result, dict) and result.get("error"):
                return self.create_result(
                    status=AgentStatus.FAILED, 
                    error_message=result["error"],
                    execution_time_ms=result.get("execution_time_ms", 0.0),
                    memory_usage_mb=result.get("memory_usage_mb", 0.0),
                    session_id=getattr(context, "session_id", None),
                    trace_id=getattr(context, "run_id", None)
                )

            return self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=float(result.get("confidence", 0.0)),
                findings=result.get("findings", []),
                recommendations=result.get("recommendations", []),
                llm_calls=int(result.get("llm_calls", 0)),
                data_sources=result.get("data_sources", []),
                execution_time_ms=result.get("execution_time_ms", 0.0),
                memory_usage_mb=result.get("memory_usage_mb", 0.0),
                session_id=getattr(context, "session_id", None),
                trace_id=getattr(context, "run_id", None)
            )
        except Exception as e:
            logger.exception("AgentCore invocation failed")
            return self.create_result(
                status=AgentStatus.FAILED, 
                error_message=str(e),
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                session_id=getattr(context, "session_id", None),
                trace_id=getattr(context, "run_id", None)
            )

class AgentCoreDocumentAnalysisAgent(BaseAgent):
    """Wrapper that invokes an AgentCore Runtime agent by ARN for document analysis."""
    
    def __init__(self):
        super().__init__("document_analysis_agentcore", "3.0.0")

    async def _execute_analysis(self, context: AgentContext):
        try:
            # Shape the prompt/payload your AgentCore expects.
            payload = {
                "contract_id": context.contract_id,
                "user_id": context.user_id,
                "query": context.query,
                "document_type": getattr(context, "document_type", None),
                "priority": getattr(context, "priority", "MEDIUM"),
            }
            # Because boto3 is sync, offload to a thread to avoid blocking the event loop
            import asyncio
            result = await asyncio.to_thread(
                _invoke_agentcore_sync, payload, getattr(context, "session_id", None), "analysis"
            )

            # Map generic response to your AgentResult
            if isinstance(result, dict) and result.get("error"):
                return self.create_result(
                    status=AgentStatus.FAILED, 
                    error_message=result["error"],
                    execution_time_ms=result.get("execution_time_ms", 0.0),
                    memory_usage_mb=result.get("memory_usage_mb", 0.0),
                    session_id=getattr(context, "session_id", None),
                    trace_id=getattr(context, "run_id", None)
                )

            return self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=float(result.get("confidence", 0.0)),
                findings=result.get("findings", []),
                recommendations=result.get("recommendations", []),
                llm_calls=int(result.get("llm_calls", 0)),
                data_sources=result.get("data_sources", []),
                execution_time_ms=result.get("execution_time_ms", 0.0),
                memory_usage_mb=result.get("memory_usage_mb", 0.0),
                session_id=getattr(context, "session_id", None),
                trace_id=getattr(context, "run_id", None)
            )
        except Exception as e:
            logger.exception("AgentCore invocation failed")
            return self.create_result(
                status=AgentStatus.FAILED, 
                error_message=str(e),
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                session_id=getattr(context, "session_id", None),
                trace_id=getattr(context, "run_id", None)
            )

class AgentCoreConversationalAgent(BaseAgent):
    """Wrapper that invokes an AgentCore Runtime agent by ARN for conversational chat."""
    
    def __init__(self):
        super().__init__("conversational_agentcore", "2.0.0")

    async def _execute_analysis(self, context: AgentContext):
        try:
            # Extract metadata for conversational context
            metadata = getattr(context, "metadata", {})
            
            # Shape the prompt/payload your AgentCore expects.
            payload = {
                "query": context.query,
                "document_id": context.contract_id,
                "user_id": context.user_id,
                "document_type": getattr(context, "document_type", "contract"),
                "chat_mode": metadata.get("chat_mode", "documents"),
                "search_all_documents": metadata.get("search_all_documents", False),
                "conversation_history": metadata.get("conversation_history", []),
                "use_external_data": metadata.get("use_external_data", True),
                "max_response_length": metadata.get("max_response_length", 1000)
            }
            
            # Because boto3 is sync, offload to a thread to avoid blocking the event loop
            import asyncio
            result = await asyncio.to_thread(
                _invoke_agentcore_sync, payload, getattr(context, "session_id", None), "conversational"
            )

            # Map generic response to your AgentResult
            if isinstance(result, dict) and result.get("error"):
                return self.create_result(
                    status=AgentStatus.FAILED, 
                    error_message=result["error"],
                    execution_time_ms=result.get("execution_time_ms", 0.0),
                    memory_usage_mb=result.get("memory_usage_mb", 0.0),
                    session_id=getattr(context, "session_id", None),
                    trace_id=getattr(context, "run_id", None)
                )

            # Create result with conversational-specific data
            agent_result = self.create_result(
                status=AgentStatus.COMPLETED,
                confidence=float(result.get("confidence", 0.0)),
                findings=result.get("findings", []),
                recommendations=result.get("recommendations", []),
                llm_calls=int(result.get("llm_calls", 0)),
                data_sources=result.get("data_sources", []),
                execution_time_ms=result.get("execution_time_ms", 0.0),
                memory_usage_mb=result.get("memory_usage_mb", 0.0),
                session_id=getattr(context, "session_id", None),
                trace_id=getattr(context, "run_id", None)
            )
            
            # Add conversational-specific attributes
            agent_result.response = result.get("response", "")
            agent_result.chat_mode = result.get("chat_mode", "documents")
            agent_result.document_context = result.get("document_context", False)
            agent_result.enhanced_with_external = result.get("enhanced_with_external", False)
            agent_result.conversation_metadata = result.get("conversation_metadata", {})
            
            return agent_result
            
        except Exception as e:
            logger.exception("AgentCore conversational invocation failed")
            return self.create_result(
                status=AgentStatus.FAILED, 
                error_message=str(e),
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                session_id=getattr(context, "session_id", None),
                trace_id=getattr(context, "run_id", None)
            )

class AgentType(Enum):
    """AWS Bedrock AgentCore compatible agent types"""
    DOCUMENT_ANALYSIS = "document_analysis_agent"
    DOCUMENT_SEARCH = "document_search_agent"
    CLAUSE_ANALYSIS = "clause_analysis_agent"
    RISK_ANALYSIS = "risk_analysis_agent"
    CONVERSATIONAL = "conversational_agent"

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
        
        # Parse remote endpoints to check availability
        remote_endpoints = {}
        try:
            remote_endpoints = json.loads(os.getenv("REMOTE_AGENT_ENDPOINTS", "{}"))
        except json.JSONDecodeError:
            logger.warning("Invalid REMOTE_AGENT_ENDPOINTS JSON, using empty dict")
        
        logger.info(f"🔧 Available Remote Endpoints: {list(remote_endpoints.keys())}")
        
        # Helper function to check if remote endpoint is available
        def has_remote_endpoint(agent_name: str) -> bool:
            return agent_name in remote_endpoints
        
        # Try to initialize each agent individually
        try:
            logger.info(f"🔧 Document Analysis Agent Selection:")
            logger.info(f"   - settings.use_bedrock_agentcore: {settings.use_bedrock_agentcore}")
            logger.info(f"   - USE_REMOTE: {USE_REMOTE}")
            logger.info(f"   - Has 'document-analysis' endpoint: {has_remote_endpoint('document-analysis')}")
            
            if settings.use_bedrock_agentcore:
                doc_agent = AgentCoreDocumentAnalysisAgent()
                logger.info("✅ AgentCore Document Analysis Agent initialized")
            elif USE_REMOTE and has_remote_endpoint('document-analysis'):
                logger.info("🐳 Attempting to create Remote Document Analysis Agent...")
                try:
                    doc_agent = RemoteDocumentAnalysisAgent()
                    logger.info("✅ Remote Document Analysis Agent initialized")
                except Exception as remote_error:
                    logger.error(f"❌ Remote Document Analysis Agent failed: {remote_error}")
                    logger.info("🏠 Falling back to Local Document Analysis Agent...")
                    try:
                        from .document_analyzer import DocumentAnalysisAgent
                        doc_agent = DocumentAnalysisAgent()
                        logger.info("✅ Local Document Analysis Agent initialized (fallback from remote error)")
                    except ImportError as ie:
                        logger.error(f"❌ Local document analysis agent import also failed: {ie}")
                        raise Exception(f"Both remote and local document analysis agents failed")
            else:
                if USE_REMOTE and not has_remote_endpoint('document-analysis'):
                    logger.info("🏠 No remote endpoint for document-analysis, using local agent")
                try:
                    from .document_analyzer import DocumentAnalysisAgent
                    doc_agent = DocumentAnalysisAgent()
                    logger.info("✅ Local Document Analysis Agent initialized")
                except ImportError as ie:
                    logger.error(f"❌ Local document analysis agent import failed: {ie}")
                    if USE_REMOTE:
                        logger.info("🐳 Trying remote as fallback...")
                        doc_agent = RemoteDocumentAnalysisAgent()
                        logger.info("✅ Remote Document Analysis Agent initialized (fallback)")
                    else:
                        raise Exception(f"Document analysis agent initialization failed")
            
            self._agents.update({
                AgentType.DOCUMENT_ANALYSIS.value: doc_agent,
                'document_analyzer': doc_agent,
                'enhanced_analyzer': doc_agent,
                'simple_analyzer': doc_agent,
            })
        except Exception as e:
            logger.error(f"❌ Document Analysis Agent failed: {e}")
        
        try:
            logger.info(f"🔧 Document Search Agent Selection:")
            logger.info(f"   - Has 'document-search' endpoint: {has_remote_endpoint('document-search')}")
            
            if settings.use_bedrock_agentcore:
                search_agent = AgentCoreDocumentSearchAgent()
                logger.info("✅ AgentCore Document Search Agent initialized")
            elif USE_REMOTE and has_remote_endpoint('document-search'):
                search_agent = RemoteDocumentSearchAgent()
                logger.info("✅ Remote Document Search Agent initialized")
            else:
                if USE_REMOTE and not has_remote_endpoint('document-search'):
                    logger.info("🏠 No remote endpoint for document-search, using local agent")
                from .search_agent import DocumentSearchAgent
                search_agent = DocumentSearchAgent()
                logger.info("✅ Local Document Search Agent initialized")
            
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
        
        # Initialize Conversational Agent
        try:
            logger.info(f"🔧 Conversational Agent Selection:")
            logger.info(f"   - settings.use_bedrock_agentcore: {settings.use_bedrock_agentcore}")
            logger.info(f"   - USE_REMOTE: {USE_REMOTE}")
            logger.info(f"   - Has 'conversational-chat' endpoint: {has_remote_endpoint('conversational-chat')}")
            
            if settings.use_bedrock_agentcore:
                conv_agent = AgentCoreConversationalAgent()
                logger.info("✅ AgentCore Conversational Agent initialized")
            elif USE_REMOTE and has_remote_endpoint('conversational-chat'):
                logger.info("🐳 Attempting to create Remote Conversational Agent...")
                try:
                    conv_agent = RemoteConversationalAgent()
                    logger.info("✅ Remote Conversational Agent initialized")
                except Exception as remote_error:
                    logger.error(f"❌ Remote Conversational Agent failed: {remote_error}")
                    logger.info("🏠 Falling back to Local Conversational Agent...")
                    try:
                        from .conversational_agent import ConversationalAgent
                        conv_agent = ConversationalAgent()
                        logger.info("✅ Local Conversational Agent initialized (fallback from remote error)")
                    except ImportError as ie:
                        logger.error(f"❌ Local conversational agent import also failed: {ie}")
                        raise Exception(f"Both remote and local conversational agents failed")
            else:
                if USE_REMOTE and not has_remote_endpoint('conversational-chat'):
                    logger.info("🏠 No remote endpoint for conversational-chat, using local agent")
                try:
                    from .conversational_agent import ConversationalAgent
                    conv_agent = ConversationalAgent()
                    logger.info("✅ Local Conversational Agent initialized")
                except ImportError as ie:
                    logger.error(f"❌ Local conversational agent import failed: {ie}")
                    if USE_REMOTE:
                        logger.info("🐳 Trying remote as fallback...")
                        conv_agent = RemoteConversationalAgent()
                        logger.info("✅ Remote Conversational Agent initialized (fallback)")
                    else:
                        raise Exception(f"Conversational agent initialization failed")
            
            self._agents.update({
                AgentType.CONVERSATIONAL.value: conv_agent,
                'conversational_agent': conv_agent,
                'chat_agent': conv_agent,
            })
        except Exception as e:
            logger.error(f"❌ Conversational Agent failed: {e}")
        
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
            elif agent_type == AgentType.CONVERSATIONAL:
                from .conversational_agent import ConversationalAgent
                return ConversationalAgent()
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
        """Get human-readable description of agent capabilities"""
        descriptions = {
            AgentType.DOCUMENT_ANALYSIS: "Comprehensive document analysis with risk assessment and clause extraction",
            AgentType.DOCUMENT_SEARCH: "Semantic and keyword-based document search with intelligent ranking",
            AgentType.CLAUSE_ANALYSIS: "Specialized clause identification and risk assessment",
            AgentType.RISK_ANALYSIS: "Advanced risk pattern detection and compliance analysis",
            AgentType.CONVERSATIONAL: "Natural language interaction with document context awareness"
        }
        return descriptions.get(agent_type, "Unknown agent type")
    
    # Convenience methods for common agent access patterns
    def get_document_search_agent(self) -> Optional[BaseAgent]:
        """Get the document search agent"""
        return self.get_agent(AgentType.DOCUMENT_SEARCH)
    
    def get_orchestrator(self):
        """Get the document orchestrator for complex workflows"""
        try:
            from .orchestrator import DocumentOrchestrator
            return DocumentOrchestrator()
        except ImportError as e:
            logger.error(f"Failed to import DocumentOrchestrator: {e}")
            return None
    
    # Quick access methods for common operations
    async def quick_analysis(
        self, 
        contract_id: str, 
        user_id: str,
        document_type: Optional[str] = None
    ) -> AgentResult:
        """Quick document analysis using the best available agent"""
        agent = self.get_agent(AgentType.DOCUMENT_ANALYSIS)
        if not agent:
            return AgentResult(
                agent_name="factory",
                agent_version="1.0.0",
                status=AgentStatus.FAILED,
                confidence=0.0,
                findings=[],
                recommendations=[],
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                error_message="No document analysis agent available"
            )
        
        context = AgentContext(
            contract_id=contract_id,
            user_id=user_id,
            document_type=document_type
        )
        return await agent.analyze(context)
    
    async def quick_search(
        self, 
        query: str, 
        contract_id: str, 
        user_id: str
    ) -> AgentResult:
        """Quick document search using the best available agent"""
        agent = self.get_agent(AgentType.DOCUMENT_SEARCH)
        if not agent:
            return AgentResult(
                agent_name="factory",
                agent_version="1.0.0",
                status=AgentStatus.FAILED,
                confidence=0.0,
                findings=[],
                recommendations=[],
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                error_message="No document search agent available"
            )
        
        context = AgentContext(
            contract_id=contract_id,
            user_id=user_id,
            query=query
        )
        return await agent.analyze(context)
    
    async def quick_chat(
        self, 
        query: str, 
        user_id: str,
        document_id: Optional[str] = None,
        chat_mode: str = "documents",
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> AgentResult:
        """Quick conversational interaction using the best available agent"""
        agent = self.get_agent(AgentType.CONVERSATIONAL)
        if not agent:
            return AgentResult(
                agent_name="factory",
                agent_version="1.0.0",
                status=AgentStatus.FAILED,
                confidence=0.0,
                findings=[],
                recommendations=[],
                execution_time_ms=0.0,
                memory_usage_mb=0.0,
                error_message="No conversational agent available"
            )
        
        context = AgentContext(
            contract_id=document_id,
            user_id=user_id,
            query=query,
            metadata={
                "chat_mode": chat_mode,
                "conversation_history": conversation_history or []
            }
        )
        return await agent.analyze(context)

# Global factory instance
agent_factory = AgentFactory()