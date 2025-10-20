# Import early_config first so your AWS creds get loaded from Secrets Manager if needed
import early_config

import os
import json
import uuid
import logging
import boto3
from typing import Optional, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# One boto3 client (thread-safe for most operations)
_agentcore = boto3.client("bedrock-agentcore", region_name=settings.aws_default_region)

def _invoke_agentcore_sync(payload: Dict[str, Any], session_id: Optional[str] = None, agent_type: str = "search") -> Dict[str, Any]:
    """
    Calls AgentCore Runtime (streaming or JSON). Returns dict payload.
    
    Args:
        payload: The payload to send to the agent
        session_id: Optional session ID
        agent_type: Type of agent ("search", "analysis", or "conversational")
    """
    # Get the appropriate ARN based on agent type
    if agent_type == "analysis":
        runtime_arn = getattr(settings, 'agentcore_runtime_arn_analysis', None) or settings.agentcore_runtime_arn
    elif agent_type == "conversational":
        runtime_arn = getattr(settings, 'agentcore_runtime_arn_conversational', None) or settings.agentcore_runtime_arn
    else:
        runtime_arn = getattr(settings, 'agentcore_runtime_arn_search', None) or settings.agentcore_runtime_arn
    
    if not runtime_arn:
        raise RuntimeError(f"AGENTCORE_RUNTIME_ARN for {agent_type} not configured")

    # Payload must be bytes
    body = json.dumps(payload).encode("utf-8")
    sid = session_id or f"{settings.agentcore_session_prefix}-{uuid.uuid4()}"

    resp = _agentcore.invoke_agent_runtime(
        agentRuntimeArn=runtime_arn,
        runtimeSessionId=sid,
        payload=body,
    )
    ctype = resp.get("contentType", "")

    # Streaming Server-Sent Events
    if "text/event-stream" in ctype:
        chunks = []
        for line in resp["response"].iter_lines(chunk_size=1024):
            if not line:
                continue
            line = line.decode("utf-8")
            if line.startswith("data: "):
                data = line[6:]
                chunks.append(data)
        # Your agent can emit JSON lines; join & parse best-effort
        try:
            # If the final event is a full JSON, prefer that
            return json.loads(chunks[-1])
        except Exception:
            return {"events": chunks}

    # Non-streaming JSON
    if ctype == "application/json":
        parts = []
        for part in resp.get("response", []):
            parts.append(part.decode("utf-8"))
        return json.loads("".join(parts)) if parts else {}

    # Fallback raw
    return {"raw": {"contentType": ctype}}

# =============================================================================
# 🧠 AGENTCORE MEMORY INTEGRATION
# =============================================================================

class AgentCoreMemoryService:
    """Service for integrating with AgentCore Memory for user personalization"""
    
    def __init__(self):
        self.memory_client = None
        self.memory_id = None
        self._initialize_memory()
    
    def _initialize_memory(self):
        """Initialize AgentCore Memory client and resources"""
        try:
            # For now, we'll use a simple in-memory approach
            # In production, this would connect to actual AgentCore Memory
            logger.info("AgentCore Memory service initialized (mock mode)")
        except Exception as e:
            logger.warning(f"AgentCore Memory initialization failed: {e}")
    
    def store_user_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """Store user preferences in AgentCore Memory"""
        try:
            # Mock implementation - in production this would use AgentCore Memory API
            logger.info(f"Storing preferences for user {user_id}: {preferences}")
            
            # Here you would call AgentCore Memory to store:
            # - Document type preferences
            # - Risk level focus areas
            # - Time range preferences
            # - Dashboard interaction patterns
            
            return True
        except Exception as e:
            logger.error(f"Failed to store user preferences: {e}")
            return False
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """Retrieve user preferences from AgentCore Memory"""
        try:
            # Mock implementation - in production this would query AgentCore Memory
            logger.info(f"Retrieving preferences for user {user_id}")
            
            # Here you would call AgentCore Memory to retrieve:
            # - Learned user patterns
            # - Preference recommendations
            # - Behavioral insights
            
            return {
                "learned_patterns": {},
                "recommendations": [],
                "confidence_score": 0.0
            }
        except Exception as e:
            logger.error(f"Failed to get user preferences: {e}")
            return {}
    
    def track_user_activity(self, user_id: str, activity: Dict[str, Any]) -> bool:
        """Track user activity for learning preferences"""
        try:
            # Mock implementation - in production this would send to AgentCore Memory
            logger.info(f"Tracking activity for user {user_id}: {activity}")
            
            # Here you would send activity data to AgentCore Memory:
            # - Dashboard views and interactions
            # - Filter usage patterns
            # - Time spent on different sections
            # - Document types analyzed
            
            return True
        except Exception as e:
            logger.error(f"Failed to track user activity: {e}")
            return False
    
    def get_personalized_recommendations(self, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Get personalized recommendations based on user patterns"""
        try:
            # Mock implementation - in production this would use AgentCore Memory insights
            logger.info(f"Getting recommendations for user {user_id}")
            
            # Here you would get AI-powered recommendations:
            # - Suggested dashboard views
            # - Documents that need attention
            # - Optimal filter combinations
            # - Productivity insights
            
            return {
                "dashboard_suggestions": [
                    "Focus on high-risk contracts from last 7 days",
                    "Review pending document analysis"
                ],
                "filter_suggestions": {
                    "document_types": ["contract", "invoice"],
                    "risk_levels": ["high", "critical"],
                    "time_range": "30d"
                },
                "insights": [
                    "You typically analyze contracts on Monday mornings",
                    "Your focus areas are financial and legal risks"
                ]
            }
        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return {}

# Global instance
agentcore_memory = AgentCoreMemoryService()