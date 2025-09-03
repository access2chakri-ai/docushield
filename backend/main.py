"""
DocuShield - TiDB Hackathon Demo
Modular multi-step agentic document analysis
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",  # Changed to use the new modular main.py
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )