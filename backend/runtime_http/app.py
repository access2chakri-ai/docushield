"""
HTTP wrapper for runtime handlers
Provides HTTP interface for local agent testing and remote agent communication
"""
from fastapi import FastAPI, Request
from runtime_handlers.document_search import handler  # your existing handler

app = FastAPI(title="DocuShield Agent Runtime HTTP", version="1.0.0")

@app.post("/invoke")
async def invoke(req: Request):
    """HTTP endpoint that wraps the existing runtime handler"""
    event = await req.json()
    return await handler(event, context=None)

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "service": "agent-runtime-http"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)