# 🛡️ DocuShield - Digital Twin Document Intelligence

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688.svg)](https://fastapi.tiangolo.com/)
[![TiDB](https://img.shields.io/badge/TiDB-Cloud-FF6B35)](https://tidbcloud.com/)

> **Enterprise-grade AI-powered document intelligence platform that transforms how businesses analyze, understand, and manage contracts and legal documents.**

DocuShield is a production-ready document intelligence platform that leverages advanced AI technologies to provide comprehensive document processing, risk analysis, and business insights. Built with modern cloud-native architecture and enterprise security standards.

## 🎯 Overview

DocuShield empowers small and medium-sized businesses to:
- **Analyze contracts in seconds** instead of hours
- **Identify risks and compliance issues** automatically
- **Chat with documents** using natural language
- **Generate actionable insights** from complex legal text
- **Make informed decisions** without extensive legal expertise

## ✨ Key Features

### 🤖 AI-Powered Analysis
- **Multi-Agent Architecture** - Specialized AI agents for search, analysis, risk assessment, and conversation
- **Advanced NLP** - Semantic understanding of legal and business documents
- **Risk Detection** - Automated identification of liability, penalties, and compliance gaps
- **Intelligent Summarization** - Key insights extraction in plain language

### 🔍 Smart Search & Discovery
- **Semantic Search** - Vector-based similarity search with legal context understanding
- **Hybrid Search** - Combined keyword and semantic search for comprehensive results
- **Multi-Document Search** - Cross-document analysis and comparison
- **Contextual Highlighting** - Intelligent highlighting of relevant sections

### 💬 Interactive Experience
- **Document Chat** - Natural language Q&A with uploaded documents
- **Real-time Processing** - Live document analysis with progress tracking
- **Intuitive Dashboard** - Clean, modern interface for document management
- **Mobile Responsive** - Full functionality across all devices

### 🏗️ Enterprise Architecture
- **Scalable Infrastructure** - AWS cloud-native deployment
- **Multi-Layer Data Architecture** - Bronze, Silver, Gold data processing layers
- **Privacy-Safe Processing** - PII detection and redaction capabilities
- **High Availability** - Distributed architecture with automatic failover

## 🏗️ Technology Stack

### Frontend
| Technology | Version | Purpose |
|------------|---------|---------|
| ![Next.js](https://img.shields.io/badge/Next.js-14-black) | 14.x | React framework with SSR/SSG |
| ![React](https://img.shields.io/badge/React-18-61DAFB) | 18.x | Component-based UI library |
| ![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6) | 5.x | Type-safe development |
| ![Tailwind CSS](https://img.shields.io/badge/Tailwind-3-38B2AC) | 3.x | Utility-first CSS framework |

### Backend
| Technology | Version | Purpose |
|------------|---------|---------|
| ![Python](https://img.shields.io/badge/Python-3.11+-3776AB) | 3.11+ | Core backend language |
| ![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-009688) | 0.104+ | High-performance web framework |
| ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-red) | 2.0+ | Python SQL toolkit and ORM |
| ![Pydantic](https://img.shields.io/badge/Pydantic-2.0-E92063) | 2.0+ | Data validation and serialization |

### AI & Machine Learning
| Provider | Models | Purpose |
|----------|--------|---------|
| ![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4-412991) | GPT-4, GPT-3.5 | Text analysis and generation |
| ![Anthropic](https://img.shields.io/badge/Anthropic-Claude-8B5A3C) | Claude 3 | Advanced reasoning |
| ![AWS Bedrock](https://img.shields.io/badge/AWS-Bedrock-FF9900) | Multiple | Model orchestration |
| ![Google](https://img.shields.io/badge/Google-Gemini-4285F4) | Gemini Pro | Multimodal AI |

### Cloud Infrastructure
| Service | Purpose |
|---------|---------|
| ![AWS](https://img.shields.io/badge/AWS-Cloud-FF9900) | Primary cloud provider |
| ![TiDB](https://img.shields.io/badge/TiDB-Cloud-FF6B35) | Distributed SQL database |
| ![S3](https://img.shields.io/badge/AWS-S3-569A31) | Document storage |
| ![QuickSight](https://img.shields.io/badge/AWS-QuickSight-FF9900) | Business intelligence |

## 📁 Project Architecture

```
docushield/
├── 🎨 frontend/                    # Next.js React Application
│   ├── app/                       # App Router (Next.js 14)
│   │   ├── components/            # Reusable UI components
│   │   ├── contexts/              # React context providers
│   │   ├── (pages)/               # Route pages
│   │   └── api/                   # API route handlers
│   ├── utils/                     # Utility functions
│   └── public/                    # Static assets
│
├── ⚙️ backend/                     # FastAPI Python Application
│   ├── app/                       # Core application
│   │   ├── 🤖 agents/             # AI Agent System
│   │   │   ├── orchestrator.py    # Multi-agent coordinator
│   │   │   ├── search_agent.py    # Document search specialist
│   │   │   ├── document_analyzer.py # Content analysis agent
│   │   │   ├── risk_analyzer_agent.py # Risk assessment agent
│   │   │   └── conversational_agent.py # Chat interface agent
│   │   │
│   │   ├── 🛣️ routers/             # API Endpoints
│   │   │   ├── documents.py       # Document management
│   │   │   ├── chat.py            # Conversational AI
│   │   │   ├── search.py          # Search functionality
│   │   │   ├── analytics.py       # Dashboard data
│   │   │   └── auth.py            # Authentication
│   │   │
│   │   ├── 🔧 services/           # Business Logic
│   │   │   ├── llm_factory.py     # Multi-LLM integration
│   │   │   ├── privacy_safe_llm.py # Privacy protection
│   │   │   ├── document_processor.py # Document pipeline
│   │   │   ├── mcp_integration.py # External data sources
│   │   │   └── data_export.py     # Analytics export
│   │   │
│   │   ├── 🏛️ core/               # Core Infrastructure
│   │   │   ├── config.py          # Configuration management
│   │   │   ├── security.py        # Security utilities
│   │   │   ├── auth.py            # Authentication logic
│   │   │   └── dependencies.py    # Dependency injection
│   │   │
│   │   ├── 📊 models.py           # Database Models
│   │   ├── 🗄️ database.py         # Database connections
│   │   └── 📋 schemas/            # API schemas
│   │
│   ├── runtime_http/              # Agent Runtime Services
│   ├── runtime_handlers/          # Background processors
│   └── requirements.txt           # Python dependencies
│
├── 📊 sagemaker_files/            # ML Notebooks & ETL
├── 🎨 diagrams/                   # Architecture diagrams
├── 📚 docs/                       # Documentation
└── 🚀 scripts/                    # Deployment scripts
```

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Installation |
|-------------|---------|--------------|
| ![Python](https://img.shields.io/badge/Python-3.11+-3776AB) | 3.11+ | [Download Python](https://python.org/downloads/) |
| ![Node.js](https://img.shields.io/badge/Node.js-18+-339933) | 18+ | [Download Node.js](https://nodejs.org/) |
| ![Git](https://img.shields.io/badge/Git-Latest-F05032) | Latest | [Download Git](https://git-scm.com/) |

### API Keys Required

| Provider | Purpose | Get API Key |
|----------|---------|-------------|
| OpenAI | GPT models | [OpenAI Platform](https://platform.openai.com/) |
| Anthropic | Claude models | [Anthropic Console](https://console.anthropic.com/) |
| TiDB Cloud | Database | [TiDB Cloud](https://tidbcloud.com/) |
| AWS | Cloud services | [AWS Console](https://aws.amazon.com/) |

### 1️⃣ Clone Repository

```bash
git clone https://github.com/your-username/docushield.git
cd docushield
```

### 2️⃣ Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Setup environment variables
cp .env.example .env
# Edit .env with your API keys and configuration

# Start the backend server
python main.py
```

### 3️⃣ Frontend Setup

```bash
# Navigate to frontend directory (new terminal)
cd frontend

# Install dependencies
npm install

# Setup environment variables
cp .env.example .env.local
# Edit .env.local with your backend URL

# Start the development server
npm run dev
```

### 4️⃣ Database Configuration

1. **Create TiDB Cluster**
   ```bash
   # Visit https://tidbcloud.com/
   # Create a new Serverless cluster
   # Copy the connection string
   ```

2. **Update Environment Variables**
   ```bash
   # In backend/.env
   DATABASE_URL=mysql+pymysql://username:password@gateway01.region.prod.aws.tidbcloud.com:4000/database_name?ssl_ca=/etc/ssl/certs/ca-certificates.crt&ssl_verify_cert=true&ssl_verify_identity=true
   ```

3. **Initialize Database**
   ```bash
   # Tables are created automatically on first run
   # Check logs for successful database connection
   ```

### 5️⃣ Verify Installation

| Service | URL | Status Check |
|---------|-----|--------------|
| Backend API | http://localhost:8000 | Visit `/docs` for Swagger UI |
| Frontend App | http://localhost:3000 | Should show DocuShield homepage |
| Health Check | http://localhost:8000/health | Should return `{"status": "healthy"}` |

## 🌐 Production Deployment

### Deployment Architecture

```mermaid
graph TB
    A[GitHub Repository] --> B[AWS Amplify]
    A --> C[AWS App Runner]
    B --> D[Frontend Application]
    C --> E[Backend API]
    E --> F[TiDB Cloud]
    E --> G[AWS S3]
    E --> H[AWS Bedrock]
    D --> I[Users]
    E --> J[AWS QuickSight]
```

### 1️⃣ Backend Deployment (AWS App Runner)

```bash
# 1. Prepare your repository
git add .
git commit -m "Production deployment"
git push origin main

# 2. Create App Runner service via AWS Console
# - Service name: docushield-backend
# - Source: GitHub repository
# - Build settings: Automatic
# - Configuration file: apprunner.yaml
```

**App Runner Configuration (`apprunner.yaml`)**:
```yaml
version: 1.0
runtime: python3
build:
  commands:
    build:
      - pip install -r requirements.txt
run:
  runtime-version: 3.11
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000
  network:
    port: 8000
    env: PORT
  env:
    - name: PORT
      value: "8000"
```

### 2️⃣ Frontend Deployment (AWS Amplify)

```bash
# 1. Create Amplify app via AWS Console
# - App name: docushield-frontend
# - Repository: GitHub
# - Branch: main
# - Build settings: amplify.yml
```

**Amplify Configuration (`amplify.yml`)**:
```yaml
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: .next
    files:
      - '**/*'
  cache:
    paths:
      - node_modules/**/*
```

### 3️⃣ Environment Variables Configuration

#### Backend Environment Variables (App Runner)
| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | TiDB connection string | `mysql+pymysql://user:pass@host:4000/db` |
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `ANTHROPIC_API_KEY` | Anthropic API key | `sk-ant-...` |
| `AWS_ACCESS_KEY_ID` | AWS access key | `AKIA...` |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | `...` |
| `S3_BUCKET_NAME` | S3 bucket for documents | `docushield-documents` |
| `CORS_ORIGINS` | Allowed frontend origins | `https://main.d1234.amplifyapp.com` |

#### Frontend Environment Variables (Amplify)
| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_BASE_URL` | Backend API URL | `https://abc123.us-east-1.awsapprunner.com` |
| `NEXT_PUBLIC_ENVIRONMENT` | Environment name | `production` |

### 4️⃣ Database Migration

```bash
# Production database setup is automatic
# Tables are created on first backend startup
# Monitor logs for successful migration
```

### 5️⃣ SSL & Custom Domain (Optional)

```bash
# App Runner provides HTTPS by default
# Amplify provides HTTPS by default
# Configure custom domains in respective consoles
```

### 6️⃣ Monitoring & Logging

| Service | Monitoring | Logs |
|---------|------------|------|
| App Runner | CloudWatch Metrics | CloudWatch Logs |
| Amplify | Build logs | Access logs |
| TiDB Cloud | Built-in monitoring | Query logs |

### 🔧 Deployment Checklist

- [ ] Repository pushed to GitHub
- [ ] App Runner service created and deployed
- [ ] Amplify app created and deployed
- [ ] Environment variables configured
- [ ] Database connection verified
- [ ] Health checks passing
- [ ] Frontend connecting to backend
- [ ] SSL certificates active
- [ ] Monitoring configured

## 🧠 AI Agent System

DocuShield employs a sophisticated multi-agent architecture where specialized AI agents work together to provide comprehensive document intelligence.

### Agent Architecture

```mermaid
graph TD
    A[User Request] --> B[AI Orchestrator]
    B --> C[Document Search Agent]
    B --> D[Document Analysis Agent]
    B --> E[Risk Analysis Agent]
    B --> F[Conversational Agent]
    C --> G[Result Consolidation]
    D --> G
    E --> G
    F --> G
    G --> H[Unified Response]
```

### 🤖 Specialized Agents

| Agent | Purpose | Capabilities |
|-------|---------|--------------|
| **🎼 Orchestrator** | Coordinates multi-agent workflows | Strategy selection, result consolidation, performance optimization |
| **🔍 Search Agent** | Document search and retrieval | Semantic search, keyword matching, multi-document queries |
| **📊 Analysis Agent** | Content analysis and extraction | Structure detection, entity extraction, summarization |
| **⚠️ Risk Agent** | Risk assessment and compliance | Liability detection, penalty analysis, compliance gaps |
| **💬 Chat Agent** | Natural language interaction | Document Q&A, contextual responses, conversation management |

### 🏗️ Data Architecture Layers

| Layer | Purpose | Data Types | Processing |
|-------|---------|------------|-----------|
| **🥉 Bronze** | Raw data ingestion | Original documents, metadata | OCR, text extraction, validation |
| **🥈 Silver** | Processed data | Chunks, embeddings, clauses | NLP processing, vector generation |
| **🥇 Gold** | Business insights | Analysis results, scores | Risk assessment, recommendations |

### 📡 API Endpoints

#### Document Management
```http
POST   /api/documents/upload          # Upload new document
GET    /api/documents/                # List user documents
GET    /api/documents/{id}            # Get document details
DELETE /api/documents/{id}            # Delete document
POST   /api/documents/{id}/analyze    # Trigger analysis
```

#### AI Interaction
```http
POST   /api/chat/ask                  # Ask question about document
POST   /api/search/                   # Search across documents
GET    /api/search/suggestions        # Get search suggestions
POST   /api/agents/analyze            # Multi-agent analysis
```

#### Analytics & Insights
```http
GET    /api/analytics/dashboard       # Dashboard data
GET    /api/analytics/risk-analysis   # Risk metrics
GET    /api/analytics/usage-stats     # Usage statistics
POST   /api/analytics/export          # Export data
```

#### Authentication & User Management
```http
POST   /api/auth/register             # User registration
POST   /api/auth/login                # User login
POST   /api/auth/refresh              # Refresh token
GET    /api/auth/profile              # User profile
```

## 📋 Supported Document Types

| Category | Document Types | Analysis Features |
|----------|----------------|-------------------|
| **📄 Legal** | Contracts, NDAs, Terms of Service, Privacy Policies | Risk assessment, clause extraction, compliance checking |
| **💼 Business** | Proposals, Agreements, MOUs, Partnership docs | Key terms identification, financial analysis |
| **💰 Financial** | Invoices, Purchase Orders, Financial Reports | Payment terms, monetary extraction, audit trails |
| **🏢 Corporate** | Employment contracts, Vendor agreements, Leases | Obligation tracking, renewal management |
| **📊 Technical** | Specifications, Requirements, Documentation | Structure analysis, content summarization |

## 🎯 Key Use Cases

### For Small Businesses
- **Contract Review**: Quickly understand vendor agreements and identify risks
- **Compliance Monitoring**: Ensure documents meet regulatory requirements  
- **Cost Management**: Track payment terms and renewal dates
- **Legal Triage**: Determine when legal counsel is needed

### For Legal Teams
- **Document Analysis**: Automated first-pass review of contracts
- **Risk Identification**: Highlight problematic clauses and terms
- **Precedent Research**: Find similar clauses across document library
- **Client Communication**: Generate plain-language summaries

### For Business Operations
- **Vendor Management**: Analyze supplier contracts and terms
- **Renewal Tracking**: Monitor contract expiration dates
- **Financial Planning**: Extract and track financial obligations
- **Process Automation**: Streamline document workflows

## 🔐 Security & Privacy

### 🛡️ Data Protection Standards

| Security Layer | Implementation | Compliance |
|----------------|----------------|------------|
| **Encryption** | AES-256 at rest, TLS 1.3 in transit | SOC 2, ISO 27001 |
| **Authentication** | JWT tokens, MFA support | OWASP standards |
| **Authorization** | Role-based access control (RBAC) | Principle of least privilege |
| **Data Isolation** | User-specific data segregation | Multi-tenant security |

### 🔒 Privacy Features

- **PII Detection**: Automatic identification and redaction of sensitive data
- **Data Residency**: Configurable data storage locations
- **Retention Policies**: Automated data lifecycle management
- **Audit Logging**: Comprehensive activity tracking
- **GDPR Compliance**: Right to deletion and data portability

### 🚨 Security Monitoring

```mermaid
graph LR
    A[User Activity] --> B[Security Monitoring]
    B --> C[Threat Detection]
    B --> D[Audit Logging]
    B --> E[Compliance Reporting]
    C --> F[Automated Response]
    D --> G[Security Analytics]
```

## 📊 Analytics & Business Intelligence

### 📈 Built-in Analytics Dashboard

| Metric Category | Key Metrics | Business Value |
|-----------------|-------------|----------------|
| **Document Processing** | Upload volume, processing time, success rate | Operational efficiency |
| **Risk Analysis** | Risk distribution, high-risk documents, trends | Risk management |
| **User Engagement** | Active users, feature usage, session duration | Product optimization |
| **AI Performance** | Model accuracy, response time, cost per query | Technical optimization |

### 🎯 QuickSight Integration

- **Real-time Dashboards**: Live data visualization with automatic refresh
- **Custom Reports**: Tailored analytics for specific business needs  
- **Embedded Analytics**: White-label dashboard integration
- **Data Export**: CSV, Excel, PDF report generation
- **Scheduled Reports**: Automated delivery of key metrics

### 📊 Sample Analytics Views

```sql
-- Risk Analysis Query Example
SELECT 
    document_type,
    AVG(risk_score) as avg_risk,
    COUNT(*) as document_count,
    SUM(CASE WHEN risk_score > 0.7 THEN 1 ELSE 0 END) as high_risk_count
FROM gold_contract_scores 
WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
GROUP BY document_type
ORDER BY avg_risk DESC;
```

## 🧪 Testing

### Backend Testing
```bash
cd backend
pytest tests/
```

### Frontend Testing
```bash
cd frontend
npm test
```

## 📈 Performance

### Optimization Features
- Async document processing
- Intelligent caching
- Connection pooling
- Vector search optimization
- Multi-provider load balancing

### Scalability
- Horizontal scaling with App Runner
- TiDB auto-scaling
- S3 unlimited storage
- CDN integration with Amplify

## 🤝 Contributing

This is a demonstration project, but contributions are welcome:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is for demonstration and educational purposes. See individual component licenses for specific terms.

## 🆘 Support

For questions about this demonstration project:
- Check the deployment guide in `DEPLOYMENT.md`
- Review the API documentation
- Examine the code examples in `/examples`

## 🎓 Educational Purpose

This project demonstrates:
- Modern full-stack development practices
- AI/ML integration patterns
- Cloud-native architecture
- Document processing workflows
- Real-time analytics implementation
- Production deployment strategies

## 🔗 Related Technologies

- [TiDB Cloud](https://tidbcloud.com) - Serverless MySQL with vector search
- [OpenAI API](https://openai.com/api/) - GPT models for analysis
- [Anthropic Claude](https://anthropic.com) - Advanced reasoning capabilities
- [AWS Services](https://aws.amazon.com) - Cloud infrastructure
- [Next.js](https://nextjs.org) - React framework
- [FastAPI](https://fastapi.tiangolo.com) - Python web framework

---

**Note**: This is a demonstration project showcasing AI document processing capabilities. It is not intended for production use with sensitive or confidential documents without proper security review and implementation of additional safeguards.
