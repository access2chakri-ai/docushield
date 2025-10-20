# DocuShield Demo

> AI-Powered Document Analysis Platform - Demonstration Project

DocuShield is a comprehensive document intelligence platform that showcases modern AI technologies for document processing, analysis, and insights generation. This is a demonstration project built for educational and portfolio purposes.

## 🚀 Features

### Core Capabilities
- **Multi-LLM Integration** - OpenAI, Anthropic, Gemini, and Groq APIs
- **Document Processing** - PDF, DOCX, and text file analysis
- **Semantic Search** - Vector similarity + full-text search with TiDB
- **Risk Analysis** - AI-powered contract risk assessment
- **Real-time Chat** - Interactive document Q&A
- **Analytics Dashboard** - QuickSight integration for insights
- **Multi-tier Architecture** - Bronze, Silver, Gold data layers

### Technology Stack
- **Frontend**: Next.js 14, React, TypeScript, Tailwind CSS
- **Backend**: FastAPI, Python 3.11, SQLAlchemy
- **Database**: TiDB Cloud (MySQL-compatible with vector search)
- **AI/ML**: OpenAI GPT-4, Anthropic Claude, Google Gemini, Groq
- **Cloud**: AWS (S3, App Runner, Amplify, QuickSight, SageMaker)
- **Authentication**: JWT-based auth system

## 📁 Project Structure

```
docushield/
├── frontend/                 # Next.js React application
│   ├── app/                 # App router pages and components
│   ├── utils/               # Utility functions and config
│   └── public/              # Static assets
├── backend/                 # FastAPI Python application
│   ├── app/                 # Main application code
│   │   ├── agents/          # AI agent implementations
│   │   ├── routers/         # API route handlers
│   │   ├── services/        # Business logic services
│   │   ├── core/            # Core utilities and config
│   │   └── models.py        # Database models
│   └── requirements.txt     # Python dependencies
├── scripts/                 # Deployment and utility scripts
└── docs/                    # Additional documentation
```

## 🛠️ Local Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- TiDB Cloud account
- API keys for AI providers (OpenAI, Anthropic, etc.)

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Copy environment template
cp .env.production.example .env
# Edit .env with your API keys and database URL

# Run the backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install

# Copy environment template
cp .env.production.example .env.local
# Edit .env.local with your backend URL

# Run the frontend
npm run dev
```

### Database Setup
1. Create a TiDB Serverless cluster at [TiDB Cloud](https://tidbcloud.com)
2. Get your connection string
3. Update the `DATABASE_URL` in your backend `.env` file
4. The application will automatically create tables on first run

## 🚀 Production Deployment

### Backend Deployment (AWS App Runner)
1. Push your code to GitHub
2. Create an App Runner service
3. Connect to your repository's `backend` folder
4. Use the provided `apprunner.yaml` configuration
5. Set environment variables in App Runner console

### Frontend Deployment (AWS Amplify)
1. Create an Amplify app
2. Connect to your repository's `frontend` folder
3. Use the provided `amplify.yml` configuration
4. Set `NEXT_PUBLIC_API_BASE_URL` to your App Runner URL

### Required Environment Variables

#### Backend
```bash
DATABASE_URL=your-tidb-connection-string
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
GOOGLE_API_KEY=your-google-key
GROQ_API_KEY=your-groq-key
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
S3_BUCKET_NAME=your-s3-bucket
CORS_ORIGINS=https://your-frontend-domain.amplifyapp.com
```

#### Frontend
```bash
NEXT_PUBLIC_API_BASE_URL=https://your-backend-url.apprunner.com
NEXT_PUBLIC_ENVIRONMENT=production
```

## 🔧 Key Components

### AI Agents
- **Document Analyzer** - Comprehensive document analysis
- **Search Agent** - Semantic and keyword search
- **Conversational Agent** - Interactive chat interface
- **Risk Analyzer** - Contract risk assessment
- **Orchestrator** - Coordinates multi-agent workflows

### Data Architecture
- **Bronze Layer** - Raw document storage
- **Silver Layer** - Processed chunks and embeddings
- **Gold Layer** - Analysis results and insights

### API Endpoints
- `/api/documents/` - Document management
- `/api/chat/` - Conversational AI
- `/api/search/` - Document search
- `/api/analytics/` - Dashboard data
- `/api/auth/` - Authentication

## 🎯 Use Cases

### Document Types Supported
- Contracts and agreements
- Legal documents
- Financial reports
- Business proposals
- Technical documentation

### Analysis Capabilities
- Risk assessment and scoring
- Key clause identification
- Compliance checking
- Financial term extraction
- Semantic search across documents

## 🔒 Security & Privacy

### Data Protection
- All documents encrypted in transit and at rest
- JWT-based authentication
- User-specific data isolation
- Secure API key management

### Privacy Features
- Optional content redaction for sensitive data
- Local processing options
- Configurable data retention policies

## 📊 Analytics & Monitoring

### Built-in Analytics
- Document processing metrics
- AI usage statistics
- Risk distribution analysis
- User activity tracking

### QuickSight Integration
- Interactive dashboards
- Real-time data visualization
- Custom report generation
- Embedded analytics

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