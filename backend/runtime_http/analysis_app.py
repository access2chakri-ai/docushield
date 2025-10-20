"""
AgentCore Compatible Runtime HTTP Service for Document Analysis
Follows AWS Bedrock AgentCore service contract
"""
from fastapi import FastAPI, Request

app = FastAPI(title="DocuShield Document Analysis Agent Runtime", version="3.0.0")

@app.get("/ping")
async def ping():
    """AgentCore health check endpoint"""
    return {"status": "healthy", "agent": "document-analysis", "version": "3.0.0"}

@app.post("/invocations")
async def invocations(req: Request):
    """AgentCore invocation endpoint"""
    # Lazy import to avoid circular dependency
    from runtime_handlers.document_analysis import handler
    
    event = await req.json()
    return await handler(event, context=None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)