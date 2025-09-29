"""
DocuShield Agent System - Using Existing Agents Only
Simple imports for existing agent components
"""

# Core system components
from .agent_factory import agent_factory, AgentType
from .api_interface import agent_api

# Base classes and types
from .base_agent import BaseAgent, AgentContext, AgentResult, AgentStatus, AgentPriority

# Existing agents - import only what exists
from .document_analyzer import DocumentAnalysisAgent
from .search_agent import DocumentSearchAgent
from .clause_analyzer_agent import ClauseAnalysisAgent
from .risk_analyzer_agent import RiskAnalysisAgent

# Try to import orchestrator - if it fails, create a simple fallback
try:
    from .orchestrator import document_orchestrator, DocumentOrchestrator
    # Backward compatibility aliases
    AgentOrchestrator = DocumentOrchestrator
    agent_orchestrator = document_orchestrator
except ImportError:
    # Simple fallback orchestrator
    document_orchestrator = None
    DocumentOrchestrator = None
    AgentOrchestrator = None
    agent_orchestrator = None

__all__ = [
    # Core system
    'agent_factory',
    'agent_api', 
    'AgentType',
    
    # Base classes
    'BaseAgent',
    'AgentContext',
    'AgentResult', 
    'AgentStatus',
    'AgentPriority',
    
    # Existing agents
    'DocumentAnalysisAgent',
    'DocumentSearchAgent',
    'ClauseAnalysisAgent', 
    'RiskAnalysisAgent',
    
    # Orchestrator (if available)
    'document_orchestrator',
    'DocumentOrchestrator',
    'AgentOrchestrator',
    'agent_orchestrator'
]
