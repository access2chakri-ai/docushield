"""
DocuShield Agent System
Multi-agent workflow for comprehensive document intelligence using full TiDB schema
"""

from .orchestrator import AgentOrchestrator
from .search_agent import SearchAgent  
from .clause_analyzer_agent import ClauseAnalyzerAgent

# Global orchestrator instance
agent_orchestrator = AgentOrchestrator()

__all__ = [
    'AgentOrchestrator',
    'SearchAgent',
    'ClauseAnalyzerAgent',
    'agent_orchestrator'
]
