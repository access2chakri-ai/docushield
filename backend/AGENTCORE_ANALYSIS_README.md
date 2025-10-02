# AgentCore Integration for DocuShield Document Analysis

This document explains how to use AWS Bedrock AgentCore with DocuShield's document analysis functionality.

## Overview

The Document Analysis agent has been migrated to a separate microservice architecture, providing:
- Scalable agent runtime execution
- Managed infrastructure via AWS Bedrock AgentCore
- Containerized deployment with Docker
- Independent scaling and deployment
- Streaming and JSON response support
- Session management

## Architecture

The Document Analysis agent now supports three deployment modes:

1. **AgentCore** (Production) - Uses AWS Bedrock AgentCore
2. **Remote HTTP** (Development) - Uses containerized agents via HTTP
3. **Local** (Development) - Uses local Python agents

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# AgentCore Configuration for Document Analysis
USE_BEDROCK_AGENTCORE=true
AGENTCORE_RUNTIME_ARN_ANALYSIS=arn:aws:bedrock-agentcore:us-east-1:192933326034:runtime/docushield_analysis_agent-XXXXX
AGENTCORE_RUNTIME_ARN_SEARCH=arn:aws:bedrock-agentcore:us-east-1:192933326034:runtime/docushield_search_agent-WYjV5lBM6W
AGENTCORE_SESSION_PREFIX=docushield
AGENTCORE_TIMEOUT=90

# Remote Agent Configuration (for development)
USE_REMOTE_AGENTS=true
REMOTE_AGENT_ENDPOINTS={"document-search": "http://localhost:8080/invocations", "document-analysis": "http://localhost:8081/invocations"}
REMOTE_AGENT_TIMEOUT=90

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

## Docker Deployment

### Build and Run Document Analysis Agent

```bash
# Build the document analysis agent container
cd docushield/backend
docker build -f Dockerfile.agent.analysis -t docushield-agent-analysis .

# Run the container
docker run -p 8081:8081 \
  -e TIDB_OPERATIONAL_HOST=your_tidb_host \
  -e TIDB_OPERATIONAL_USER=your_tidb_user \
  -e TIDB_OPERATIONAL_PASSWORD=your_tidb_password \
  -e AWS_ACCESS_KEY_ID=your_aws_key \
  -e AWS_SECRET_ACCESS_KEY=your_aws_secret \
  docushield-agent-analysis
```

### Docker Compose

Use the provided docker-compose.yml to run all services:

```bash
cd docushield
docker-compose up -d
```

This will start:
- `agent-analysis` on port 8081
- `agent-search` on port 8080
- `backend` on port 8000
- `frontend` on port 3000
- `tidb` on port 4000

## Testing

### 1. Basic HTTP Connectivity Test

Test the containerized agent directly:

```bash
curl -X POST http://localhost:8081/invocations \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": "test-contract-123",
    "user_id": "test-user",
    "document_type": "contract",
    "priority": "MEDIUM"
  }'
```

### 2. Health Check

```bash
curl http://localhost:8081/ping
```

Expected response:
```json
{
  "status": "healthy",
  "agent": "document-analysis",
  "version": "3.0.0"
}
```

### 3. Full Integration Test

Test through the main DocuShield API:

```bash
curl -X POST http://localhost:8000/api/v1/documents/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "contract_id": "your-contract-id",
    "analysis_type": "comprehensive"
  }'
```

## Payload Format

### Input Payload

The Document Analysis agent expects this payload structure:

```json
{
  "inputs": {
    "contract_id": "contract-123",
    "user_id": "user-456",
    "query": "What are the key risks?",
    "document_type": "contract",
    "priority": "HIGH"
  },
  "session_id": "optional-session-id",
  "request_id": "optional-request-id"
}
```

### Output Format

```json
{
  "status": "COMPLETED",
  "confidence": 0.85,
  "findings": [
    {
      "type": "risk_pattern",
      "title": "Unlimited liability exposure",
      "severity": "critical",
      "confidence": 0.9,
      "description": "Found unlimited liability clause",
      "context": "...contract text..."
    }
  ],
  "recommendations": [
    "🚨 1 critical issue(s) require immediate attention",
    "Seek legal counsel before proceeding"
  ],
  "llm_calls": 3,
  "data_sources": ["bronze_contract", "bronze_contract_text_raw"],
  "execution_time_ms": 1250.5,
  "memory_usage_mb": 45.2,
  "agent_name": "document_analysis_agent",
  "agent_version": "3.0.0"
}
```

## Analysis Features

The Document Analysis agent provides:

### 1. Multi-Strategy Analysis
- **Comprehensive**: Full AI + pattern analysis for complex documents
- **Fast**: Pattern-based analysis for simple queries
- **Fallback**: Basic analysis when other methods fail

### 2. Document Type Support
- **Contracts**: Focus on obligations, termination, liability, payment terms
- **Invoices**: Analyze amounts, due dates, payment terms, line items
- **Policies**: Review requirements, procedures, compliance
- **General**: Key points, requirements, deadlines, responsibilities

### 3. Risk Pattern Detection
- Unlimited liability exposure
- Immediate termination clauses
- Auto-renewal terms
- Exclusive IP licenses
- Indemnification clauses
- Overdue payments
- Policy violations

### 4. AI-Powered Analysis
- Intelligent document understanding
- Context-aware risk assessment
- Actionable recommendations
- Confidence scoring

## Troubleshooting

### Common Issues

1. **"Contract ID is required"**
   - Ensure `contract_id` is provided in the payload
   - Verify the contract exists in the database

2. **"Agent not found" in factory**
   - Check agent factory initialization logs
   - Verify environment variables are set correctly

3. **Docker container fails to start**
   - Check port 8081 is available
   - Verify database connection settings
   - Check AWS credentials if using Bedrock

4. **AgentCore invocation fails**
   - Verify `AGENTCORE_RUNTIME_ARN_ANALYSIS` is correct
   - Check AWS credentials and permissions
   - Ensure the AgentCore runtime is deployed

### Debug Steps

1. Check container health:
   ```bash
   docker ps
   curl http://localhost:8081/ping
   ```

2. View container logs:
   ```bash
   docker logs docushield-agent-analysis-1
   ```

3. Test agent factory:
   ```bash
   cd docushield/backend
   python -c "from app.agents.agent_factory import agent_factory; print(agent_factory.get_available_agent_names())"
   ```

## Production Deployment

### AWS Bedrock AgentCore

1. **Deploy the runtime**: Package and deploy the agent as an AgentCore runtime
2. **Update ARN**: Set `AGENTCORE_RUNTIME_ARN_ANALYSIS` to your deployed runtime ARN
3. **Configure IAM**: Ensure proper permissions for bedrock-agentcore
4. **Enable monitoring**: Set up CloudWatch logging and metrics

### Security Best Practices

1. **Use IAM roles** instead of access keys in production
2. **Enable VPC endpoints** for secure AWS communication
3. **Implement proper logging** and monitoring
4. **Use secrets management** for sensitive configuration

### Scaling

1. **Horizontal scaling**: Deploy multiple agent containers behind a load balancer
2. **Vertical scaling**: Adjust container resources based on workload
3. **Auto-scaling**: Use container orchestration for dynamic scaling
4. **Caching**: Implement result caching for frequently analyzed documents

## Migration Notes

The Document Analysis agent has been successfully migrated from a monolithic architecture to a microservice architecture:

- ✅ **Runtime handler** created (`runtime_handlers/document_analysis.py`)
- ✅ **Docker container** configured (`Dockerfile.agent.analysis`)
- ✅ **HTTP service** implemented (`runtime_http/analysis_app.py`)
- ✅ **Remote agent wrapper** added to agent factory
- ✅ **AgentCore integration** implemented
- ✅ **Docker Compose** configuration updated
- ✅ **Environment configuration** updated
- ✅ **Multi-ARN support** added for different agent types

The migration maintains full backward compatibility while enabling independent scaling and deployment of the Document Analysis functionality.