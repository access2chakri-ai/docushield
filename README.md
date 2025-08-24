# DocuShield

A document intelligence platform built with FastAPI, featuring hybrid search, LLM integration, and multi-modal document processing.

## Features

- **Document Ingestion**: Support for TXT, CSV, and PDF files
- **Hybrid Search**: Vector similarity + keyword matching
- **Multiple Modes**: Q&A, Summary, and Dashboard generation
- **LLM Integration**: Pluggable LLM providers (OpenAI, Anthropic, Groq)
- **Audit Logging**: Track all interactions for compliance
- **TiDB Ready**: Designed for TiDB Cloud with vector support

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

3. **Run the application**:
   ```bash
   uvicorn src.app.main:app --reload --port 8000
   ```

4. **Open your browser** to `http://localhost:8000`

## Project Structure

```
src/app/
├── __init__.py          # Package initialization
├── main.py             # FastAPI application and endpoints
├── settings.py         # Environment configuration
├── db.py              # Database models and connection
├── models.py           # Utility functions
├── schemas.py          # Pydantic models
├── ingest.py           # Document processing
├── llm/
│   ├── __init__.py
│   └── factory.py      # LLM provider abstraction
├── retrieval/
│   ├── __init__.py
│   └── hybrid.py       # Hybrid search implementation
└── agents/
    ├── __init__.py
    ├── planner.py      # Query planning
    ├── retriever.py    # Document retrieval
    ├── action.py       # Action execution
    └── audit.py        # Interaction logging
```

## API Endpoints

- `GET /` - Web interface
- `POST /ingest` - Upload and process documents
- `POST /query` - Query documents (Q&A, Summary, Dashboard)
- `GET /healthz` - Health check
- `GET /readyz` - Readiness check

## Development

This is a hackathon base project with mock LLM implementations. To integrate real LLMs:

1. Update `src/app/llm/factory.py` with actual API calls
2. Replace mock embeddings with real vector models
3. Enhance hybrid search with TiDB VECTOR operations
4. Add proper error handling and validation

## License

See [LICENSE](LICENSE) file for details.
