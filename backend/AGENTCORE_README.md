# AgentCore Integration for DocuShield

This document explains how to use AWS Bedrock AgentCore with DocuShield's document search functionality.

## Overview

AgentCore allows you to deploy your document search logic as a managed AWS service, providing:
- Scalable agent runtime execution
- Managed infrastructure
- Streaming and JSON response support
- Session management

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# AgentCore Configuration
USE_BEDROCK_AGENTCORE=true
AGENTCORE_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-1:192933326034:runtime/docushield_search_agent-WYjV5lBM6W
AGENTCORE_SESSION_PREFIX=docushield
AGENTCORE_TIMEOUT=90

# AWS Configuration (required for AgentCore)
AWS_DEFAULT_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key_here
AWS_SECRET_ACCESS_KEY=your_aws_secret_key_here
```

### Agent Selection Logic

The system automatically selects the appropriate agent based on configuration:

1. **AgentCore** (if `USE_BEDROCK_AGENTCORE=true`) - Uses AWS Bedrock AgentCore
2. **Remote HTTP** (if `USE_REMOTE_AGENTS=true`) - Uses containerized agents via HTTP
3. **Local** (default) - Uses local Python agents

## Testing

### 1. Basic AgentCore Connectivity Test

Test your AgentCore connection directly:

```bash
cd docushield/backend
python test_agentcore.py
```

This will:
- Verify your AWS credentials
- Test the AgentCore runtime ARN
- Send a simple ping payload
- Handle streaming/JSON responses

### 2. Full Integration Test

Test the complete DocuShield integration:

```bash
cd docushield/backend
python test_agentcore_integration.py
```

This will:
- Check agent factory configuration
- Test document search agent selection
- Execute a full analysis workflow
- Verify response mapping

## Architecture

### AgentCore Service (`app/services/agentcore.py`)

```python
# Synchronous boto3 call wrapped for async usage
result = await asyncio.to_thread(
    _invoke_agentcore_sync, payload, session_id
)
```

### AgentCore Agent (`app/agents/agent_factory.py`)

```python
class AgentCoreDocumentSearchAgent(BaseAgent):
    async def _execute_analysis(self, context: AgentContext):
        # Shape payload for your AgentCore runtime
        payload = {
            "query": context.query,
            "contract_id": context.contract_id,
            "user_id": context.user_id,
            "top_k": getattr(context, "top_k", 5),
        }
        
        # Call AgentCore asynchronously
        result = await asyncio.to_thread(
            _invoke_agentcore_sync, payload, context.session_id
        )
        
        # Map response to AgentResult
        return self.create_result(...)
```

## Response Handling

AgentCore supports two response types:

### 1. Streaming (text/event-stream)
```
data: {"partial": "result"}
data: {"final": "complete result"}
```

### 2. JSON (application/json)
```json
{
  "confidence": 0.85,
  "findings": [...],
  "recommendations": [...],
  "llm_calls": 3
}
```

## Payload Format

Your AgentCore runtime should expect this payload structure:

```json
{
  "query": "What are the key terms?",
  "contract_id": "contract-123",
  "user_id": "user-456",
  "top_k": 5
}
```

## Troubleshooting

### Common Issues

1. **"AGENTCORE_RUNTIME_ARN not configured"**
   - Ensure `AGENTCORE_RUNTIME_ARN` is set in your `.env` file
   - Verify the ARN format is correct

2. **AWS Credentials Error**
   - Check `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`
   - Ensure your AWS credentials have bedrock-agentcore permissions
   - Verify `AWS_DEFAULT_REGION` matches your AgentCore region

3. **"Agent not found" in factory**
   - Ensure `USE_BEDROCK_AGENTCORE=true` is set
   - Check that the agent factory initialization completed successfully

4. **Timeout Issues**
   - Increase `AGENTCORE_TIMEOUT` value
   - Check your AgentCore runtime performance

### Debug Steps

1. Run the basic connectivity test first:
   ```bash
   python test_agentcore.py
   ```

2. Check agent factory health:
   ```bash
   python test_agentcore_integration.py
   ```

3. Enable debug logging in your application:
   ```bash
   DEBUG=true
   ```

## Production Deployment

For production use:

1. **Security**: Use IAM roles instead of access keys
2. **Monitoring**: Enable CloudWatch logging for your AgentCore runtime
3. **Scaling**: Configure appropriate timeout and retry settings
4. **Fallback**: Keep `USE_REMOTE_AGENTS` as a backup option

## Local Development

For local development, you can switch between modes:

```bash
# Use AgentCore (requires AWS setup)
USE_BEDROCK_AGENTCORE=true

# Use HTTP agents (requires Docker)
USE_BEDROCK_AGENTCORE=false
USE_REMOTE_AGENTS=true

# Use local agents (no external dependencies)
USE_BEDROCK_AGENTCORE=false
USE_REMOTE_AGENTS=false
```