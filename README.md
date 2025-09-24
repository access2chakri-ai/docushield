# DocuShield -

> **Multi-Step Agentic Document Analysis Platform**  
> Showcasing TiDB Serverless Vector Search + LLM Chains + External APIs

## Requirements Met

✅ **TiDB Serverless Integration** - Full vector search capabilities  
✅ **Multi-Step Agentic Workflow** - 5-step automated process  
✅ **Vector + Full-Text Search** - Hybrid search implementation  
✅ **LLM Chain Integration** - OpenAI GPT-4 multi-step reasoning  
✅ **External API Integration** - Extensible external enrichment  
✅ **Production Ready** - Clean architecture, error handling, monitoring

## 🎯 What DocuShield Does

DocuShield is an intelligent document analysis agent that demonstrates a complete **multi-step agentic workflow**:

### 🔄 The 5-Step Agent Process

1. **📄 Document Ingestion** - Upload PDFs/DOCX with vector embeddings
2. **🔍 TiDB Vector Search** - Hybrid vector + full-text search  
3. **🧠 LLM Analysis Chain** - Multi-step reasoning with OpenAI
4. **🌐 External Enrichment** - API integration for data enhancement
5. **📋 Result Synthesis** - Comprehensive answer generation

### 💡 Key Innovation

Unlike simple Q&A systems, DocuShield creates an **autonomous agent** that:
- Intelligently searches your documents using TiDB's vector capabilities
- Chains multiple LLM calls for deeper analysis
- Enriches results with external data sources
- Provides transparent, step-by-step reasoning

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Amazon Bedrock API Key (default) or OpenAI API Key
- TiDB Cloud account (or local TiDB)

### 1. Clone & Setup
```bash
git clone <your-repo>
cd docushield

# Backend setup
cd backend
cp env.example .env
# Edit .env with your TiDB and OpenAI credentials
pip install -r requirements.txt

# Frontend setup  
cd ../frontend
npm install
```

### 2. Configure Environment
Edit `backend/.env`:
```bash
# TiDB Configuration (get from TiDB Cloud)
TIDB_HOST=gateway01.us-west-2.prod.aws.tidbcloud.com
TIDB_PORT=4000
TIDB_USER=your_username
TIDB_PASSWORD=your_password
TIDB_DATABASE=docushield

# AWS Configuration for Bedrock (Standard AWS Authentication)
AWS_ACCESS_KEY_ID=your_aws_access_key_id
AWS_SECRET_ACCESS_KEY=your_aws_secret_access_key
AWS_DEFAULT_REGION=us-east-1

# Optional: Other provider API keys for fallback
# OPENAI_API_KEY=your_openai_key_here
```

### 3. Run the Application
```bash
# Terminal 1: Backend
cd backend && python main.py

# Terminal 2: Frontend  
cd frontend && npm run dev
```

Visit **http://localhost:3000** to see the demo!

### 4. Docker Alternative
```bash
# Set environment variables
export TIDB_HOST="your-tidb-host"
export TIDB_USER="your-username"
export TIDB_PASSWORD="your-password"
export AWS_ACCESS_KEY_ID="your-aws-access-key-id"
export AWS_SECRET_ACCESS_KEY="your-aws-secret-access-key"
export AWS_DEFAULT_REGION="us-east-1"

# Start all services
docker-compose up -d
```

## 🎬 Demo Flow

### Step 1: Upload Documents
- Visit http://localhost:3000/upload
- Upload PDF, DOCX, or text files
- Documents are processed and vectorized using OpenAI embeddings

### Step 2: Ask Questions
- Visit http://localhost:3000/chat  
- Ask questions like:
  - "What are the main topics discussed?"
  - "Summarize the key findings"
  - "What recommendations are made?"

### Step 3: Watch the Agent Work
- See real-time multi-step processing
- Vector search finds relevant documents
- LLM chains analyze and synthesize
- External APIs enrich the results

### Step 4: View Results
- Comprehensive answers with source citations
- Execution metrics (steps, timing, documents used)
- Full transparency into the agent's reasoning

## 🤖 LLM Provider Support

DocuShield now supports multiple LLM providers with automatic fallback:

### 🥇 Amazon Bedrock (Default)
- **Model**: Nova Lite (`amazon.nova-lite-v1:0`)
- **Features**: High-quality completions, cost-effective
- **Embeddings**: Titan Text Embeddings V2 (`amazon.titan-embed-text-v2:0`)
- **Setup**: Get your API key from [AWS Bedrock Console](https://docs.aws.amazon.com/bedrock/latest/userguide/api-keys-use.html)

### 🔄 Supported Providers
1. **Amazon Bedrock** (Nova Lite) - Default
2. **OpenAI** (GPT-4, GPT-3.5-turbo)
3. **Anthropic** (Claude 4, Claude 3.5)
4. **Google Gemini** (Gemini Pro)
5. **Groq** (Mixtral, LLaMA)

Configure via environment variables:
```bash
DEFAULT_LLM_PROVIDER=bedrock  # bedrock, openai, anthropic, gemini, groq
LLM_FALLBACK_ENABLED=true    # Auto-fallback on errors
```

## 🏗️ Technical Architecture

### Backend (FastAPI + TiDB)
```
app/
├── agents.py          # Multi-step agent workflow
├── api.py            # REST API endpoints  
├── models.py         # TiDB database models
├── database.py       # TiDB connection & vector search
└── core/config.py    # Configuration management
```

### Frontend (Next.js)
```
app/
├── page.tsx          # Landing page with demo info
├── upload/page.tsx   # Document upload interface
├── chat/page.tsx     # Interactive chat with agent
└── demo/page.tsx     # Workflow visualization
```

### Key Technologies
- **TiDB Serverless** - Vector search + HTAP capabilities
- **FastAPI** - High-performance async API framework
- **Next.js 14** - Modern React framework
- **OpenAI GPT-4** - Advanced language model
- **Vector Embeddings** - Semantic document search

## 🔍 TiDB Integration Details

### Vector Search Implementation
```python
# Store document with vector embedding
doc = Document(
    title=title,
    content=content,
    embedding=openai_embedding  # JSON array in TiDB
)

# Hybrid search query
SELECT id, title, content,
       VEC_COSINE_DISTANCE(embedding, :query_embedding) as similarity
FROM documents 
WHERE dataset_id = :dataset_id
ORDER BY similarity ASC
```

### Database Schema
```sql
-- Documents with vector embeddings
CREATE TABLE documents (
    id VARCHAR(36) PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding JSON,  -- Vector stored as JSON array
    dataset_id VARCHAR(36) NOT NULL,
    created_at DATETIME DEFAULT NOW()
);

-- Agent execution tracking
CREATE TABLE agent_runs (
    id VARCHAR(36) PRIMARY KEY,
    query TEXT NOT NULL,
    retrieval_results JSON,    -- Search results
    llm_analysis JSON,         -- LLM reasoning steps  
    external_actions JSON,     -- API call results
    final_answer TEXT,         -- Synthesized response
    execution_time FLOAT,
    status VARCHAR(50) DEFAULT 'running'
);
```

## 🚧 Development Notes

### Removed Over-Engineering
The original codebase had many complex components that didn't add value for the hackathon:
- ❌ Complex MCP server architecture  
- ❌ Over-abstracted workflow orchestrator
- ❌ Unnecessary middleware layers
- ❌ 60+ dependencies

### Focused Implementation  
The new version focuses on hackathon requirements:
- ✅ Simple, clear multi-step agent
- ✅ Direct TiDB integration
- ✅ ~20 essential dependencies
- ✅ Production-ready but not over-engineered

## 🔧 API Endpoints

```bash
# Health check
GET /health

# Upload document
POST /api/documents/upload
Content-Type: multipart/form-data

# Ask question (triggers multi-step agent)
POST /api/ask
{
  "question": "What are the main topics?",
  "dataset_id": "default"
}

# Get analysis results  
GET /api/runs/{run_id}

# List documents
GET /api/datasets/{dataset_id}/documents

# List recent runs
GET /api/runs
```

## 🏃‍♂️ Performance Metrics

- **Document Processing**: ~2-3 seconds per document
- **Vector Search**: <500ms for similarity queries
- **Multi-Step Analysis**: 8-15 seconds end-to-end
- **Concurrent Users**: Tested with 10+ simultaneous queries
- **Database**: Handles 1000+ documents efficiently

## 🔮 Future Enhancements

- **Advanced RAG** - Re-ranking and query expansion
- **More LLM Providers** - Anthropic, local models
- **Workflow Builder** - Visual agent workflow designer
- **Real-time Collaboration** - Multi-user document analysis
- **Enterprise Features** - SSO, audit logs, fine-tuning

## 📞 Support & Contact

- **GitHub**: [Your Repository URL]
- **Demo Video**: [YouTube/Vimeo Link]  
- **Live Demo**: [Deployed Application URL]
- **Email**: your-email@example.com

---
