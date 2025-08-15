# API Documentation

Comprehensive REST API documentation for the Multi-Bot RAG Platform.

## 🔗 Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://api.yourdomain.com`

## 🔐 Authentication

The API uses JWT (JSON Web Token) authentication. Include the token in the Authorization header:

```
Authorization: Bearer <your-jwt-token>
```

### Getting a Token

```http
POST /api/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your-password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe",
    "is_active": true
  }
}
```

## 📚 API Endpoints

### Authentication Endpoints

#### POST /api/auth/register
Register a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure-password",
  "full_name": "John Doe"
}
```

**Response (201):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

#### POST /api/auth/login
Authenticate user and get access token.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "secure-password"
}
```

**Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "email": "user@example.com",
    "full_name": "John Doe"
  }
}
```

#### POST /api/auth/logout
Logout user (invalidate token).

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "message": "Successfully logged out"
}
```

#### POST /api/auth/refresh
Refresh access token.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### User Management

#### GET /api/users/me
Get current user profile.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "settings": {
    "theme": "dark",
    "language": "en",
    "notifications": true
  }
}
```

#### PUT /api/users/me
Update current user profile.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "full_name": "John Smith",
  "settings": {
    "theme": "light",
    "language": "en",
    "notifications": false
  }
}
```

**Response (200):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "full_name": "John Smith",
  "is_active": true,
  "updated_at": "2024-01-15T11:30:00Z",
  "settings": {
    "theme": "light",
    "language": "en",
    "notifications": false
  }
}
```

### Bot Management

#### GET /api/bots
List user's bots with pagination.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `page` (int, optional): Page number (default: 1)
- `size` (int, optional): Items per page (default: 10, max: 100)
- `search` (string, optional): Search by bot name

**Response (200):**
```json
{
  "items": [
    {
      "id": 1,
      "name": "Customer Support Bot",
      "description": "Handles customer inquiries",
      "llm_provider": "openai",
      "llm_model": "gpt-4",
      "system_prompt": "You are a helpful customer support assistant...",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T10:30:00Z",
      "document_count": 5,
      "conversation_count": 23
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10,
  "pages": 1
}
```

#### POST /api/bots
Create a new bot.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "Sales Assistant",
  "description": "Helps with sales inquiries",
  "llm_provider": "anthropic",
  "llm_model": "claude-3-sonnet",
  "system_prompt": "You are a knowledgeable sales assistant...",
  "temperature": 0.7,
  "max_tokens": 1000,
  "is_active": true
}
```

**Response (201):**
```json
{
  "id": 2,
  "name": "Sales Assistant",
  "description": "Helps with sales inquiries",
  "llm_provider": "anthropic",
  "llm_model": "claude-3-sonnet",
  "system_prompt": "You are a knowledgeable sales assistant...",
  "temperature": 0.7,
  "max_tokens": 1000,
  "is_active": true,
  "created_at": "2024-01-15T11:00:00Z",
  "user_id": 1
}
```

#### GET /api/bots/{bot_id}
Get detailed information about a specific bot.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "id": 1,
  "name": "Customer Support Bot",
  "description": "Handles customer inquiries",
  "llm_provider": "openai",
  "llm_model": "gpt-4",
  "system_prompt": "You are a helpful customer support assistant...",
  "temperature": 0.7,
  "max_tokens": 1000,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "user_id": 1,
  "documents": [
    {
      "id": 1,
      "filename": "faq.pdf",
      "size": 1024000,
      "uploaded_at": "2024-01-15T10:35:00Z"
    }
  ],
  "analytics": {
    "total_conversations": 23,
    "total_messages": 156,
    "avg_response_time": 1.2,
    "user_satisfaction": 4.5
  }
}
```

#### PUT /api/bots/{bot_id}
Update an existing bot.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "name": "Updated Bot Name",
  "description": "Updated description",
  "system_prompt": "Updated system prompt...",
  "temperature": 0.8,
  "is_active": false
}
```

**Response (200):**
```json
{
  "id": 1,
  "name": "Updated Bot Name",
  "description": "Updated description",
  "system_prompt": "Updated system prompt...",
  "temperature": 0.8,
  "is_active": false,
  "updated_at": "2024-01-15T12:00:00Z"
}
```

#### DELETE /api/bots/{bot_id}
Delete a bot and all associated data.

**Headers:** `Authorization: Bearer <token>`

**Response (204):** No content

### Document Management

#### POST /api/documents/upload
Upload documents for a specific bot.

**Headers:** 
- `Authorization: Bearer <token>`
- `Content-Type: multipart/form-data`

**Form Data:**
- `file`: Document file (PDF, TXT, DOCX, MD, CSV, JSON)
- `bot_id`: Bot ID to associate the document with

**Response (201):**
```json
{
  "id": 1,
  "filename": "company_handbook.pdf",
  "original_filename": "Company Handbook v2.1.pdf",
  "size": 2048000,
  "content_type": "application/pdf",
  "bot_id": 1,
  "status": "processing",
  "uploaded_at": "2024-01-15T11:00:00Z",
  "processed_at": null,
  "chunk_count": 0,
  "metadata": {
    "pages": 45,
    "language": "en"
  }
}
```

#### GET /api/documents
List documents with filtering and pagination.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `bot_id` (int, optional): Filter by bot ID
- `status` (string, optional): Filter by status (processing, completed, failed)
- `page` (int, optional): Page number (default: 1)
- `size` (int, optional): Items per page (default: 10)

**Response (200):**
```json
{
  "items": [
    {
      "id": 1,
      "filename": "company_handbook.pdf",
      "original_filename": "Company Handbook v2.1.pdf",
      "size": 2048000,
      "content_type": "application/pdf",
      "bot_id": 1,
      "bot_name": "Customer Support Bot",
      "status": "completed",
      "uploaded_at": "2024-01-15T11:00:00Z",
      "processed_at": "2024-01-15T11:05:00Z",
      "chunk_count": 127,
      "metadata": {
        "pages": 45,
        "language": "en"
      }
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10,
  "pages": 1
}
```

#### GET /api/documents/{document_id}
Get detailed information about a specific document.

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "id": 1,
  "filename": "company_handbook.pdf",
  "original_filename": "Company Handbook v2.1.pdf",
  "size": 2048000,
  "content_type": "application/pdf",
  "bot_id": 1,
  "bot_name": "Customer Support Bot",
  "status": "completed",
  "uploaded_at": "2024-01-15T11:00:00Z",
  "processed_at": "2024-01-15T11:05:00Z",
  "chunk_count": 127,
  "metadata": {
    "pages": 45,
    "language": "en",
    "author": "HR Department",
    "created_date": "2024-01-10"
  },
  "processing_log": [
    {
      "timestamp": "2024-01-15T11:00:30Z",
      "message": "Document uploaded successfully"
    },
    {
      "timestamp": "2024-01-15T11:01:00Z",
      "message": "Text extraction completed"
    },
    {
      "timestamp": "2024-01-15T11:03:00Z",
      "message": "Document chunked into 127 segments"
    },
    {
      "timestamp": "2024-01-15T11:05:00Z",
      "message": "Embeddings generated and stored"
    }
  ]
}
```

#### DELETE /api/documents/{document_id}
Delete a document and its associated embeddings.

**Headers:** `Authorization: Bearer <token>`

**Response (204):** No content

#### POST /api/documents/{document_id}/reprocess
Reprocess a document (regenerate chunks and embeddings).

**Headers:** `Authorization: Bearer <token>`

**Response (202):**
```json
{
  "message": "Document reprocessing started",
  "task_id": "reprocess_doc_1_20240115_120000"
}
```

### Conversation Management

#### GET /api/conversations
List conversations with pagination and filtering.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `bot_id` (int, optional): Filter by bot ID
- `page` (int, optional): Page number (default: 1)
- `size` (int, optional): Items per page (default: 10)

**Response (200):**
```json
{
  "items": [
    {
      "id": 1,
      "title": "Product inquiry about pricing",
      "bot_id": 1,
      "bot_name": "Customer Support Bot",
      "message_count": 8,
      "created_at": "2024-01-15T09:00:00Z",
      "updated_at": "2024-01-15T09:15:00Z",
      "last_message": {
        "content": "Thank you for the information!",
        "role": "user",
        "timestamp": "2024-01-15T09:15:00Z"
      }
    }
  ],
  "total": 1,
  "page": 1,
  "size": 10,
  "pages": 1
}
```

#### POST /api/conversations
Start a new conversation.

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "bot_id": 1,
  "title": "New conversation",
  "initial_message": "Hello, I need help with..."
}
```

**Response (201):**
```json
{
  "id": 2,
  "title": "New conversation",
  "bot_id": 1,
  "created_at": "2024-01-15T12:00:00Z",
  "messages": [
    {
      "id": 1,
      "content": "Hello, I need help with...",
      "role": "user",
      "timestamp": "2024-01-15T12:00:00Z"
    }
  ]
}
```

#### GET /api/conversations/{conversation_id}
Get conversation history with all messages.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `page` (int, optional): Page number for messages (default: 1)
- `size` (int, optional): Messages per page (default: 50)

**Response (200):**
```json
{
  "id": 1,
  "title": "Product inquiry about pricing",
  "bot_id": 1,
  "bot_name": "Customer Support Bot",
  "created_at": "2024-01-15T09:00:00Z",
  "updated_at": "2024-01-15T09:15:00Z",
  "messages": {
    "items": [
      {
        "id": 1,
        "content": "Hello, I need information about your pricing plans.",
        "role": "user",
        "timestamp": "2024-01-15T09:00:00Z",
        "metadata": {}
      },
      {
        "id": 2,
        "content": "I'd be happy to help you with pricing information. We offer three main plans...",
        "role": "assistant",
        "timestamp": "2024-01-15T09:00:30Z",
        "metadata": {
          "response_time": 1.2,
          "tokens_used": 156,
          "sources": [
            {
              "document_id": 1,
              "chunk_id": "chunk_45",
              "relevance_score": 0.89
            }
          ]
        }
      }
    ],
    "total": 8,
    "page": 1,
    "size": 50,
    "pages": 1
  }
}
```

#### DELETE /api/conversations/{conversation_id}
Delete a conversation and all its messages.

**Headers:** `Authorization: Bearer <token>`

**Response (204):** No content

### Analytics and Monitoring

#### GET /api/analytics/dashboard
Get dashboard analytics data.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `period` (string, optional): Time period (7d, 30d, 90d, 1y) (default: 30d)
- `bot_id` (int, optional): Filter by specific bot

**Response (200):**
```json
{
  "period": "30d",
  "summary": {
    "total_conversations": 156,
    "total_messages": 1247,
    "active_bots": 3,
    "avg_response_time": 1.4,
    "user_satisfaction": 4.2
  },
  "conversations_over_time": [
    {
      "date": "2024-01-01",
      "count": 12
    },
    {
      "date": "2024-01-02",
      "count": 15
    }
  ],
  "bot_performance": [
    {
      "bot_id": 1,
      "bot_name": "Customer Support Bot",
      "conversations": 89,
      "avg_response_time": 1.2,
      "satisfaction": 4.5
    }
  ],
  "popular_topics": [
    {
      "topic": "pricing",
      "count": 45,
      "percentage": 28.8
    },
    {
      "topic": "features",
      "count": 32,
      "percentage": 20.5
    }
  ]
}
```

#### GET /api/analytics/bots/{bot_id}
Get detailed analytics for a specific bot.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `period` (string, optional): Time period (7d, 30d, 90d, 1y) (default: 30d)

**Response (200):**
```json
{
  "bot_id": 1,
  "bot_name": "Customer Support Bot",
  "period": "30d",
  "metrics": {
    "total_conversations": 89,
    "total_messages": 712,
    "avg_response_time": 1.2,
    "avg_conversation_length": 8.0,
    "user_satisfaction": 4.5,
    "resolution_rate": 0.87
  },
  "usage_over_time": [
    {
      "date": "2024-01-01",
      "conversations": 8,
      "messages": 64,
      "avg_response_time": 1.1
    }
  ],
  "response_time_distribution": {
    "under_1s": 45,
    "1_to_3s": 32,
    "3_to_5s": 8,
    "over_5s": 4
  },
  "document_usage": [
    {
      "document_id": 1,
      "document_name": "company_handbook.pdf",
      "usage_count": 156,
      "avg_relevance": 0.78
    }
  ]
}
```

### System Health and Status

#### GET /health
Health check endpoint (no authentication required).

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T12:00:00Z",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "qdrant": "healthy"
  }
}
```

#### GET /api/system/status
Detailed system status (admin only).

**Headers:** `Authorization: Bearer <admin-token>`

**Response (200):**
```json
{
  "status": "operational",
  "uptime": 86400,
  "version": "1.0.0",
  "environment": "production",
  "services": {
    "database": {
      "status": "healthy",
      "connections": 12,
      "response_time": 0.05
    },
    "redis": {
      "status": "healthy",
      "memory_usage": "45MB",
      "connected_clients": 8
    },
    "qdrant": {
      "status": "healthy",
      "collections": 3,
      "total_vectors": 15420
    }
  },
  "metrics": {
    "requests_per_minute": 45,
    "avg_response_time": 1.2,
    "error_rate": 0.02
  }
}
```

## 🔌 WebSocket API

### Connection

Connect to WebSocket for real-time chat:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws/1?token=your-jwt-token');
```

### Message Format

**Send Message:**
```json
{
  "type": "message",
  "content": "Hello, how can you help me?",
  "conversation_id": 1
}
```

**Receive Message:**
```json
{
  "type": "message",
  "content": "I'd be happy to help! What do you need assistance with?",
  "role": "assistant",
  "timestamp": "2024-01-15T12:00:00Z",
  "message_id": 123,
  "conversation_id": 1,
  "metadata": {
    "response_time": 1.2,
    "tokens_used": 45,
    "sources": [
      {
        "document_id": 1,
        "chunk_id": "chunk_12",
        "relevance_score": 0.85
      }
    ]
  }
}
```

**Typing Indicator:**
```json
{
  "type": "typing",
  "is_typing": true
}
```

**Error Message:**
```json
{
  "type": "error",
  "message": "Failed to process message",
  "code": "PROCESSING_ERROR"
}
```

## 📊 Rate Limiting

API endpoints are rate limited to prevent abuse:

- **Authentication**: 5 requests per minute
- **General API**: 100 requests per hour
- **File Upload**: 10 requests per hour
- **WebSocket**: 60 messages per minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248000
```

## ❌ Error Responses

All error responses follow this format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "email",
      "issue": "Invalid email format"
    }
  },
  "timestamp": "2024-01-15T12:00:00Z",
  "path": "/api/auth/register"
}
```

### Common Error Codes

- `AUTHENTICATION_REQUIRED` (401): Missing or invalid token
- `PERMISSION_DENIED` (403): Insufficient permissions
- `NOT_FOUND` (404): Resource not found
- `VALIDATION_ERROR` (422): Invalid input data
- `RATE_LIMIT_EXCEEDED` (429): Too many requests
- `INTERNAL_ERROR` (500): Server error

## 🔧 SDK and Examples

### Python SDK Example

```python
import requests

class MultiBotClient:
    def __init__(self, base_url, token):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {token}"}
    
    def create_bot(self, name, description, llm_provider="openai"):
        response = requests.post(
            f"{self.base_url}/api/bots",
            json={
                "name": name,
                "description": description,
                "llm_provider": llm_provider,
                "llm_model": "gpt-4"
            },
            headers=self.headers
        )
        return response.json()
    
    def upload_document(self, bot_id, file_path):
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'bot_id': bot_id}
            response = requests.post(
                f"{self.base_url}/api/documents/upload",
                files=files,
                data=data,
                headers=self.headers
            )
        return response.json()

# Usage
client = MultiBotClient("http://localhost:8000", "your-token")
bot = client.create_bot("My Bot", "A helpful assistant")
document = client.upload_document(bot["id"], "document.pdf")
```

### JavaScript/TypeScript SDK Example

```typescript
class MultiBotAPI {
  private baseURL: string;
  private token: string;

  constructor(baseURL: string, token: string) {
    this.baseURL = baseURL;
    this.token = token;
  }

  private async request(endpoint: string, options: RequestInit = {}) {
    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers: {
        'Authorization': `Bearer ${this.token}`,
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.status}`);
    }

    return response.json();
  }

  async createBot(data: CreateBotRequest) {
    return this.request('/api/bots', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getBots(page = 1, size = 10) {
    return this.request(`/api/bots?page=${page}&size=${size}`);
  }

  async startConversation(botId: number, message: string) {
    return this.request('/api/conversations', {
      method: 'POST',
      body: JSON.stringify({
        bot_id: botId,
        initial_message: message,
      }),
    });
  }
}

// Usage
const api = new MultiBotAPI('http://localhost:8000', 'your-token');
const bot = await api.createBot({
  name: 'Customer Support',
  description: 'Handles customer inquiries',
  llm_provider: 'openai',
  llm_model: 'gpt-4'
});
```

## 📖 Interactive Documentation

For interactive API documentation with request/response examples and testing capabilities, visit:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`