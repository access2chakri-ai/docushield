"""
Remote Agent HTTP Client
Handles communication with Dockerized agents via HTTP
"""
# Import early_config first to ensure secrets are loaded from AWS Secrets Manager
import early_config

import os
import json
import httpx
import logging

logger = logging.getLogger(__name__)

# Configuration from environment variables
ENDPOINTS = json.loads(os.getenv("REMOTE_AGENT_ENDPOINTS", "{}"))
TIMEOUT = float(os.getenv("REMOTE_AGENT_TIMEOUT", "45"))

async def call_agent(name: str, payload: dict) -> dict:
    """
    Call a remote agent via HTTP
    
    Args:
        name: Agent name (e.g., "document-search")
        payload: Request payload to send to the agent
        
    Returns:
        dict: Response from the remote agent
        
    Raises:
        httpx.HTTPError: If the HTTP request fails
        KeyError: If the agent endpoint is not configured
    """
    if name not in ENDPOINTS:
        raise KeyError(f"No endpoint configured for agent '{name}'. Available: {list(ENDPOINTS.keys())}")
    
    url = ENDPOINTS[name]
    headers = {"content-type": "application/json"}
    
    logger.info(f"Calling remote agent '{name}' at {url}")
    
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            r = await client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            result = r.json()
            logger.info(f"Remote agent '{name}' responded successfully")
            return result
    except httpx.TimeoutException:
        logger.error(f"Timeout calling remote agent '{name}' after {TIMEOUT}s")
        raise
    except httpx.HTTPError as e:
        logger.error(f"HTTP error calling remote agent '{name}': {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling remote agent '{name}': {e}")
        raise