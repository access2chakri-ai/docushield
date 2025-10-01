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

def _invoke_agentcore_sync(payload: Dict[str, Any], session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Calls AgentCore Runtime (streaming or JSON). Returns dict payload.
    """
    if not settings.agentcore_runtime_arn:
        raise RuntimeError("AGENTCORE_RUNTIME_ARN not configured")

    # Payload must be bytes
    body = json.dumps(payload).encode("utf-8")
    sid = session_id or f"{settings.agentcore_session_prefix}-{uuid.uuid4()}"

    resp = _agentcore.invoke_agent_runtime(
        agentRuntimeArn=settings.agentcore_runtime_arn,
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