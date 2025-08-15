# Multi-Bot RAG Platform

A comprehensive full-stack multi-bot assistant platform with advanced document-based knowledge retrieval (RAG) capabilities, real-time chat, and enterprise-grade features.

## 🚀 Features

- **🤖 Multi-LLM Support**: OpenAI GPT, Anthropic Claude, Google Gemini
- **📄 Advanced RAG**: Document upload, processing, and intelligent retrieval
- **👥 Role-Based Access**: Complete user management and permissions
- **⚡ Real-Time Chat**: WebSocket-powered instant messaging
- **🔒 Data Isolation**: Complete separation between bot instances
- **📊 Analytics**: Performance monitoring and usage analytics
- **🔍 OCR Support**: Extract text from images and PDFs
- **🎯 Adaptive Retrieval**: Smart threshold management for optimal results
- **💾 Caching**: Redis-powered response and embedding caching
- **🔄 Migration System**: Alembic-based database versioning

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React + TS    │    │   FastAPI       │    │   PostgreSQL    │
│   Frontend      │◄──►│   Backend       │◄──►│   Database      │
│   (Port 3000)   │    │   (Port 8000)   │    │   (Port 5432)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐    ┌─────────────────┐
         │              │     Redis       │    │     Qdrant      │
         └──────────────►│   Cache Store   │    │  Vector Store   │
                        │   (Port 6379)   │    │   (Port 6333)   │
                        └─────────────────┘    └─────────────────┘
```

## 🛠️ Technology Stack

### Frontend
- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **React Query** for state management
- **WebSocket** for real-time communication

### Backend
- **FastAPI** with Python 3.11+
- **SQLAlchemy** ORM with Alembic migrations
- **Pydantic** for data validation
- **JWT** authentication
- **WebSocket** support

### Infrastructure
- **PostgreSQL** for primary data storage
- **Redis** for caching and session management
- **Qdrant** for vector embeddings storage
- **Docker** with Docker Compose
- **Nginx** for production deployment

## 🚀 Quick Start

### Prerequisites
- **Docker Desktop** (recommended) or Docker + Docker Compose
- **Git**
- **Node.js 18+** (for local development)
- **Python 3.11+** (for local development)

### Option 1: Docker Setup (Recommended)

1. **Clone the repository**
   ```bash
   git clone <your-repository-url>
   cd multi-bot-rag-platform
   ```

2. **Start the application**
   ```bash
   # Windows PowerShell
   .\run.ps1 run
   
   # Windows Command Prompt
   run.bat run
   
   # Linux/Mac
   make run
   ```

3. **Run database migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

4. **Access the application**
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:8000
   - **API Documentation**: http://localhost:8000/docs
   - **Qdrant Dashboard**: http://localhost:6333/dashboard

### Option 2: Local Development Setup

1. **Backend Setup**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Frontend Setup**
   ```bash
   cd frontend
   npm install
   ```

3. **Start Services**
   ```bash
   # Start databases only
   docker-compose up postgres redis qdrant -d
   
   # Start backend
   cd backend && uvicorn main:app --reload
   
   # Start frontend (new terminal)
   cd frontend && npm run dev
   ```

## ⚙️ Configuration

### Environment Variables

Copy and customize the environment file:
```bash
cp config/.env.example config/.env
```

Key configuration options:

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/multi_bot_rag

# Security (CHANGE IN PRODUCTION!)
SECRET_KEY=your-very-long-secret-key-change-this-in-production

# API Keys (add your own)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# File Upload
MAX_FILE_SIZE=10485760  # 10MB
UPLOAD_DIR=/app/uploads

# Frontend
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

### LLM Provider Setup

1. **OpenAI**: Get API key from https://platform.openai.com/
2. **Anthropic**: Get API key from https://console.anthropic.com/
3. **Google**: Get API key from https://makersuite.google.com/

## 📁 Project Structure

```
multi-bot-rag-platform/
├── backend/                    # FastAPI Python backend
│   ├── src/
│   │   ├── api/               # API route handlers
│   │   ├── core/              # Core configuration and database
│   │   ├── models/            # SQLAlchemy database models
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── services/          # Business logic services
│   │   └── utils/             # Utility functions
│   ├── alembic/               # Database migrations
│   ├── uploads/               # File upload storage
│   ├── requirements.txt       # Python dependencies
│   └── Dockerfile
├── frontend/                   # React TypeScript frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/             # Page components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── services/          # API service functions
│   │   ├── types/             # TypeScript type definitions
│   │   └── utils/             # Utility functions
│   ├── package.json
│   └── Dockerfile
├── config/                     # Configuration files
│   ├── docker/                # Docker-specific configs
│   ├── nginx/                 # Nginx configurations
│   └── .env                   # Environment variables
├── docs/                       # Documentation
│   ├── API.md                 # API documentation
│   ├── DEPLOYMENT.md          # Deployment guide
│   └── DEVELOPMENT.md         # Development guide
├── docker-compose.yml          # Docker services definition
├── Makefile                   # Build automation (Linux/Mac)
├── run.ps1                    # PowerShell runner script
├── run.bat                    # Batch runner script
└── README.md                  # This file
```

## 🔧 Available Commands

### Docker Commands
```bash
# Start all services
.\run.ps1 run          # PowerShell
run.bat run            # Command Prompt
make run               # Linux/Mac

# Stop all services
.\run.ps1 stop
run.bat stop
make stop

# View logs
.\run.ps1 logs
run.bat logs
make logs

# Clean up (removes containers and volumes)
.\run.ps1 clean
run.bat clean
make clean

# Install dependencies
.\run.ps1 install
run.bat install
make install
```

### Database Commands
```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision --autogenerate -m "Description"

# Check current migration
docker-compose exec backend alembic current

# Migration history
docker-compose exec backend alembic history
```

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test

# E2E tests
npm run test:e2e
```

## 📚 API Documentation

- **Interactive Docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key API Endpoints

- `POST /api/auth/login` - User authentication
- `GET /api/bots` - List user's bots
- `POST /api/bots` - Create new bot
- `POST /api/documents/upload` - Upload documents
- `POST /api/conversations` - Start conversation
- `WebSocket /api/ws/{bot_id}` - Real-time chat

## 🚀 Deployment

### Production Deployment

1. **Update environment variables**
   ```bash
   # Set production values
   NODE_ENV=production
   SECRET_KEY=<strong-production-key>
   DATABASE_URL=<production-db-url>
   ```

2. **Build and deploy**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Run migrations**
   ```bash
   docker-compose exec backend alembic upgrade head
   ```

See [DEPLOYMENT.md](docs/DEPLOYMENT.md) for detailed deployment instructions.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Run tests: `make test`
5. Commit changes: `git commit -m 'Add amazing feature'`
6. Push to branch: `git push origin feature/amazing-feature`
7. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Open an issue on GitHub
- **Discussions**: Use GitHub Discussions for questions

## 🙏 Acknowledgments

- FastAPI for the excellent Python web framework
- React team for the amazing frontend library
- Qdrant for vector database capabilities
- All contributors who help improve this project

---

**Made with ❤️ for the developer community**