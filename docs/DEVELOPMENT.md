# Development Guide

This guide covers local development setup, coding standards, and contribution guidelines for the Multi-Bot RAG Platform.

## 🛠️ Local Development Setup

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Docker Desktop**
- **Git**

### Backend Development

1. **Create virtual environment**
   ```bash
   cd backend
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Start database services**
   ```bash
   docker-compose up postgres redis qdrant -d
   ```

4. **Run migrations**
   ```bash
   alembic upgrade head
   ```

5. **Start development server**
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Frontend Development

1. **Install dependencies**
   ```bash
   cd frontend
   npm install
   ```

2. **Start development server**
   ```bash
   npm run dev
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000

## 📁 Project Structure Deep Dive

### Backend Structure

```
backend/
├── src/
│   ├── api/                    # API route handlers
│   │   ├── auth.py            # Authentication endpoints
│   │   ├── bots.py            # Bot management
│   │   ├── conversations.py   # Chat endpoints
│   │   ├── documents.py       # Document upload/management
│   │   └── websocket.py       # WebSocket handlers
│   ├── core/                   # Core application logic
│   │   ├── config.py          # Configuration management
│   │   ├── database.py        # Database connection
│   │   ├── dependencies.py    # FastAPI dependencies
│   │   └── security.py        # Authentication logic
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py            # User model
│   │   ├── bot.py             # Bot model
│   │   ├── conversation.py    # Conversation model
│   │   └── document.py        # Document model
│   ├── schemas/                # Pydantic schemas
│   │   ├── user.py            # User schemas
│   │   ├── bot.py             # Bot schemas
│   │   └── conversation.py    # Conversation schemas
│   ├── services/               # Business logic
│   │   ├── auth_service.py    # Authentication service
│   │   ├── bot_service.py     # Bot management service
│   │   ├── chat_service.py    # Chat processing service
│   │   ├── document_service.py # Document processing
│   │   ├── embedding_service.py # Embedding generation
│   │   ├── llm_service.py     # LLM integration
│   │   └── vector_store.py    # Vector database operations
│   └── utils/                  # Utility functions
│       ├── encryption.py      # Encryption utilities
│       └── text_processing.py # Text processing utilities
├── alembic/                    # Database migrations
├── uploads/                    # File upload storage
├── requirements.txt            # Python dependencies
└── Dockerfile                 # Docker configuration
```

### Frontend Structure

```
frontend/
├── src/
│   ├── components/             # Reusable components
│   │   ├── ui/                # Basic UI components
│   │   ├── chat/              # Chat-related components
│   │   ├── bot/               # Bot management components
│   │   └── document/          # Document components
│   ├── pages/                  # Page components
│   │   ├── Login.tsx          # Login page
│   │   ├── Dashboard.tsx      # Main dashboard
│   │   ├── BotManagement.tsx  # Bot management
│   │   └── Chat.tsx           # Chat interface
│   ├── hooks/                  # Custom React hooks
│   │   ├── useAuth.ts         # Authentication hook
│   │   ├── useWebSocket.ts    # WebSocket hook
│   │   └── useChat.ts         # Chat functionality hook
│   ├── services/               # API service functions
│   │   ├── api.ts             # Base API configuration
│   │   ├── auth.ts            # Authentication API
│   │   ├── bots.ts            # Bot management API
│   │   └── chat.ts            # Chat API
│   ├── types/                  # TypeScript type definitions
│   │   ├── auth.ts            # Authentication types
│   │   ├── bot.ts             # Bot types
│   │   └── chat.ts            # Chat types
│   ├── utils/                  # Utility functions
│   │   ├── constants.ts       # Application constants
│   │   ├── helpers.ts         # Helper functions
│   │   └── validation.ts      # Form validation
│   ├── styles/                 # Global styles
│   └── App.tsx                # Main application component
├── public/                     # Static assets
├── package.json               # Node.js dependencies
└── Dockerfile                # Docker configuration
```

## 🎯 Coding Standards

### Python (Backend)

- **Code Style**: Follow PEP 8
- **Formatting**: Use Black with line length 100
- **Import Sorting**: Use isort
- **Type Hints**: Use type hints for all functions
- **Docstrings**: Use Google-style docstrings

```python
def process_document(
    document_id: int, 
    user_id: int
) -> DocumentProcessingResult:
    """Process a document for RAG indexing.
    
    Args:
        document_id: The ID of the document to process
        user_id: The ID of the user who owns the document
        
    Returns:
        DocumentProcessingResult containing processing status and metadata
        
    Raises:
        DocumentNotFoundError: If document doesn't exist
        PermissionError: If user doesn't have access to document
    """
    # Implementation here
    pass
```

### TypeScript (Frontend)

- **Code Style**: Use ESLint with TypeScript rules
- **Formatting**: Use Prettier
- **Naming**: Use camelCase for variables, PascalCase for components
- **Types**: Define explicit types for all props and state

```typescript
interface ChatMessageProps {
  message: ChatMessage;
  isOwn: boolean;
  onEdit?: (messageId: string, newContent: string) => void;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ 
  message, 
  isOwn, 
  onEdit 
}) => {
  // Component implementation
};
```

## 🧪 Testing

### Backend Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src

# Run specific test file
pytest tests/test_auth.py

# Run with verbose output
pytest -v
```

### Frontend Testing

```bash
# Run unit tests
npm test

# Run with coverage
npm run test:coverage

# Run E2E tests
npm run test:e2e
```

## 🔄 Database Migrations

### Creating Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new table"

# Create empty migration
alembic revision -m "Custom migration"
```

### Running Migrations

```bash
# Upgrade to latest
alembic upgrade head

# Upgrade to specific revision
alembic upgrade abc123

# Downgrade one revision
alembic downgrade -1

# Show current revision
alembic current

# Show migration history
alembic history
```

## 🐛 Debugging

### Backend Debugging

1. **Enable debug mode**
   ```python
   # In config/.env
   DEBUG=true
   LOG_LEVEL=DEBUG
   ```

2. **Use debugger**
   ```python
   import pdb; pdb.set_trace()
   ```

3. **Check logs**
   ```bash
   docker-compose logs backend
   ```

### Frontend Debugging

1. **Browser DevTools**: Use React Developer Tools
2. **Console Logging**: Use `console.log()` for debugging
3. **Network Tab**: Monitor API calls

## 🚀 Performance Optimization

### Backend Optimization

- **Database Queries**: Use SQLAlchemy query optimization
- **Caching**: Implement Redis caching for expensive operations
- **Async Operations**: Use async/await for I/O operations
- **Connection Pooling**: Configure database connection pooling

### Frontend Optimization

- **Code Splitting**: Use React.lazy() for route-based splitting
- **Memoization**: Use React.memo() and useMemo() appropriately
- **Bundle Analysis**: Use `npm run build:analyze`
- **Image Optimization**: Optimize images and use appropriate formats

## 🔒 Security Best Practices

### Backend Security

- **Input Validation**: Validate all inputs using Pydantic
- **SQL Injection**: Use SQLAlchemy ORM, avoid raw SQL
- **Authentication**: Use JWT tokens with proper expiration
- **CORS**: Configure CORS properly for production
- **Rate Limiting**: Implement rate limiting for API endpoints

### Frontend Security

- **XSS Prevention**: Sanitize user inputs
- **CSRF Protection**: Use CSRF tokens for state-changing operations
- **Secure Storage**: Store sensitive data securely
- **HTTPS**: Always use HTTPS in production

## 📊 Monitoring and Logging

### Logging Configuration

```python
# Backend logging
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)
```

### Monitoring Metrics

- **Response Times**: Monitor API response times
- **Error Rates**: Track error rates and types
- **Resource Usage**: Monitor CPU, memory, and disk usage
- **User Activity**: Track user engagement metrics

## 🤝 Contributing Workflow

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes** following coding standards
4. **Write tests** for new functionality
5. **Run tests**: `make test`
6. **Commit changes**: `git commit -m 'Add amazing feature'`
7. **Push to branch**: `git push origin feature/amazing-feature`
8. **Create Pull Request**

## 📝 Documentation

- **API Documentation**: Update OpenAPI schemas
- **Code Comments**: Add meaningful comments
- **README Updates**: Update README for new features
- **Changelog**: Update CHANGELOG.md for releases

## 🆘 Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check if PostgreSQL is running
   - Verify DATABASE_URL in .env
   - Check network connectivity

2. **Migration Issues**
   - Ensure database is accessible
   - Check for conflicting migrations
   - Verify model imports in alembic/env.py

3. **Frontend Build Issues**
   - Clear node_modules and reinstall
   - Check for TypeScript errors
   - Verify environment variables

4. **Docker Issues**
   - Check Docker Desktop is running
   - Verify docker-compose.yml syntax
   - Check for port conflicts

### Getting Help

- **Documentation**: Check the docs/ directory
- **Issues**: Search existing GitHub issues
- **Discussions**: Use GitHub Discussions for questions
- **Logs**: Always check application logs first