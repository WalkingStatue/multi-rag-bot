# Multi-RAG Bot Platform API Documentation

Comprehensive API documentation for the Multi-RAG Bot Platform. This API allows you to manage bots, documents, conversations, and user accounts programmatically.

## Base URL

```
http://localhost:8000
```

## Authentication

Most API endpoints require authentication using Bearer tokens. Include your access token in the Authorization header:

```
Authorization: Bearer your_access_token
```

### Obtaining Tokens

Use the `/api/auth/login` endpoint to obtain access and refresh tokens:

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "your@email.com",
    "password": "your_password"
  }'
```

## Rate Limiting

The API implements rate limiting to ensure fair usage:
- **Standard endpoints**: 100 requests per minute per user
- **Chat endpoints**: 20 requests per minute per user
- **File upload endpoints**: 10 requests per minute per user

When rate limits are exceeded, the API returns a `429 Too Many Requests` status code with a `Retry-After` header.

## Error Handling

The API uses conventional HTTP response codes and returns JSON-formatted error responses:

```json
{
  "detail": "Error description",
  "code": "ERROR_CODE",
  "type": "error_type"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request (validation errors)
- `401` - Unauthorized (invalid/missing authentication)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error

---

## Authentication API

### Login

**POST** `/api/auth/login`

Authenticate a user with email and password.

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Register

**POST** `/api/auth/register`

Register a new user account.

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "password": "password123",
  "username": "newuser"
}
```

**Response:**
```json
{
  "id": "12345",
  "email": "newuser@example.com",
  "username": "newuser",
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Refresh Token

**POST** `/api/auth/refresh`

Refresh an access token using a refresh token.

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Logout

**POST** `/api/auth/logout` 🔒

Logout and invalidate the current session.

**Response:**
```json
{
  "message": "Successfully logged out"
}
```

---

## Users API

### Get Profile

**GET** `/api/users/profile` 🔒

Get the current user's profile information.

**Response:**
```json
{
  "id": "12345",
  "email": "user@example.com",
  "username": "user",
  "created_at": "2024-01-01T00:00:00Z",
  "last_login": "2024-01-15T12:00:00Z"
}
```

### Update Profile

**PUT** `/api/users/profile` 🔒

Update the current user's profile information.

**Request Body:**
```json
{
  "username": "newusername",
  "email": "newemail@example.com"
}
```

**Response:**
```json
{
  "id": "12345",
  "email": "newemail@example.com",
  "username": "newusername",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

---

## Bots API

### List Bots

**GET** `/api/bots` 🔒

Get all bots accessible to the current user.

**Response:**
```json
[
  {
    "id": "bot123",
    "name": "My AI Assistant",
    "description": "A helpful AI assistant",
    "model": "gpt-4",
    "role": "owner",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

### Create Bot

**POST** `/api/bots` 🔒

Create a new bot.

**Request Body:**
```json
{
  "name": "My New Bot",
  "description": "A description of my bot",
  "system_prompt": "You are a helpful assistant",
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 2000,
  "top_p": 1.0,
  "frequency_penalty": 0.0,
  "presence_penalty": 0.0
}
```

**Response:**
```json
{
  "id": "bot456",
  "name": "My New Bot",
  "description": "A description of my bot",
  "system_prompt": "You are a helpful assistant",
  "model": "gpt-4",
  "temperature": 0.7,
  "max_tokens": 2000,
  "created_at": "2024-01-15T12:00:00Z"
}
```

### Get Bot

**GET** `/api/bots/{bot_id}` 🔒

Get a specific bot by ID.

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot

**Response:**
```json
{
  "id": "bot123",
  "name": "My AI Assistant",
  "description": "A helpful AI assistant",
  "system_prompt": "You are a helpful assistant",
  "model": "gpt-4",
  "temperature": 0.7,
  "created_at": "2024-01-01T00:00:00Z"
}
```

### Update Bot

**PUT** `/api/bots/{bot_id}` 🔒

Update a bot's configuration. Only owners and editors can update bots.

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot

**Request Body:**
```json
{
  "name": "Updated Bot Name",
  "system_prompt": "Updated system prompt",
  "temperature": 0.8,
  "max_tokens": 3000
}
```

### Delete Bot

**DELETE** `/api/bots/{bot_id}` 🔒

Delete a bot. Only owners can delete bots.

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot

### Bot Analytics

**GET** `/api/bots/{bot_id}/analytics` 🔒

Get usage analytics for a bot.

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot

**Response:**
```json
{
  "total_conversations": 45,
  "total_messages": 892,
  "total_documents": 12,
  "total_collaborators": 3,
  "usage_last_30_days": {
    "conversations": 23,
    "messages": 456
  }
}
```

### Bot Permissions

**GET** `/api/bots/{bot_id}/permissions` 🔒

Get all permissions/collaborators for a bot.

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot

**Response:**
```json
[
  {
    "user_id": "user123",
    "username": "collaborator1",
    "email": "collab@example.com",
    "role": "editor",
    "granted_at": "2024-01-01T00:00:00Z"
  }
]
```

### Invite Collaborator

**POST** `/api/bots/{bot_id}/permissions/invite` 🔒

Invite a user to collaborate on a bot.

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot

**Request Body:**
```json
{
  "email": "newcollab@example.com",
  "role": "viewer"
}
```

### Update Collaborator Role

**PUT** `/api/bots/{bot_id}/permissions/{user_id}` 🔒

Update a collaborator's role.

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot
- `user_id` (string, required): The unique identifier of the user

**Request Body:**
```json
{
  "role": "editor"
}
```

### Remove Collaborator

**DELETE** `/api/bots/{bot_id}/permissions/{user_id}` 🔒

Remove a collaborator from a bot.

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot
- `user_id` (string, required): The unique identifier of the user

---

## Documents API

### List Documents

**GET** `/api/bots/{bot_id}/documents` 🔒

Get all documents for a bot.

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot

**Response:**
```json
[
  {
    "id": "doc123",
    "filename": "document.pdf",
    "size": 1024000,
    "status": "processed",
    "uploaded_at": "2024-01-01T00:00:00Z",
    "processed_at": "2024-01-01T00:05:00Z"
  }
]
```

### Upload Document

**POST** `/api/bots/{bot_id}/documents/upload` 🔒

Upload a new document to a bot's knowledge base.

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot

**Request Body:**
- `file` (file, required): The document file to upload
- Content-Type: `multipart/form-data`

**Supported file types:**
- PDF (`.pdf`)
- Microsoft Word (`.doc`, `.docx`)
- Text files (`.txt`)
- Markdown (`.md`)
- CSV (`.csv`)

**Response:**
```json
{
  "id": "doc456",
  "filename": "new-document.pdf",
  "size": 2048000,
  "status": "processing",
  "uploaded_at": "2024-01-15T12:00:00Z"
}
```

### Get Document

**GET** `/api/bots/{bot_id}/documents/{document_id}` 🔒

Get information about a specific document.

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot
- `document_id` (string, required): The unique identifier of the document

### Delete Document

**DELETE** `/api/bots/{bot_id}/documents/{document_id}` 🔒

Delete a document from a bot's knowledge base.

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot
- `document_id` (string, required): The unique identifier of the document

### Document Processing Status

**GET** `/api/bots/{bot_id}/documents/{document_id}/status` 🔒

Get the processing status of a document.

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot
- `document_id` (string, required): The unique identifier of the document

**Response:**
```json
{
  "status": "processing",
  "progress": 75,
  "stage": "embedding_generation",
  "estimated_completion": "2024-01-15T12:05:00Z"
}
```

---

## Conversations API

### List Conversations

**GET** `/api/conversations/sessions` 🔒

Get all conversation sessions for the current user.

**Query Parameters:**
- `bot_id` (string, optional): Filter conversations by bot ID
- `limit` (integer, optional): Maximum number of sessions to return (default: 50)
- `offset` (integer, optional): Number of sessions to skip for pagination (default: 0)

**Response:**
```json
[
  {
    "id": "session123",
    "bot_id": "bot123",
    "title": "Conversation about AI",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T01:00:00Z",
    "message_count": 12
  }
]
```

### Get Conversation Messages

**GET** `/api/conversations/sessions/{session_id}/messages` 🔒

Get all messages in a conversation session.

**Parameters:**
- `session_id` (string, required): The unique identifier of the session

**Response:**
```json
[
  {
    "id": "msg123",
    "session_id": "session123",
    "role": "user",
    "content": "Hello, how are you?",
    "timestamp": "2024-01-01T00:00:00Z"
  },
  {
    "id": "msg124",
    "session_id": "session123",
    "role": "assistant",
    "content": "Hello! I'm doing well, thank you for asking.",
    "timestamp": "2024-01-01T00:00:30Z"
  }
]
```

### Send Message

**POST** `/api/conversations/bots/{bot_id}/chat` 🔒

Send a message to a bot and receive a response.

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot

**Request Body:**
```json
{
  "message": "Hello, how are you?",
  "session_id": "session123",
  "stream": false
}
```

**Response:**
```json
{
  "session_id": "session123",
  "message_id": "msg456",
  "response": "Hello! I'm doing well, thank you for asking.",
  "timestamp": "2024-01-15T12:00:00Z"
}
```

### Stream Response

**POST** `/api/conversations/bots/{bot_id}/chat` 🔒

Send a message and receive a streamed response.

**Request Body:**
```json
{
  "message": "Tell me a story",
  "session_id": "session123",
  "stream": true
}
```

**Response:** Server-Sent Events (SSE) stream
```
data: {"type": "start", "session_id": "session123", "message_id": "msg789"}

data: {"type": "content", "content": "Once upon"}

data: {"type": "content", "content": " a time"}

data: {"type": "end", "message_id": "msg789", "timestamp": "2024-01-15T12:00:00Z"}
```

---

## API Keys API

### List API Keys

**GET** `/api/api-keys` 🔒

Get all API keys for the current user.

**Response:**
```json
[
  {
    "id": "key123",
    "provider": "openai",
    "name": "My OpenAI Key",
    "created_at": "2024-01-01T00:00:00Z",
    "last_used": "2024-01-15T12:00:00Z"
  }
]
```

### Add API Key

**POST** `/api/api-keys` 🔒

Add a new API key for a provider.

**Request Body:**
```json
{
  "provider": "openai",
  "name": "My OpenAI Key",
  "key": "sk-..."
}
```

**Response:**
```json
{
  "id": "key456",
  "provider": "openai",
  "name": "My OpenAI Key",
  "created_at": "2024-01-15T12:00:00Z"
}
```

### Delete API Key

**DELETE** `/api/api-keys/{key_id}` 🔒

Delete an API key.

**Parameters:**
- `key_id` (string, required): The unique identifier of the API key

### Get Supported Providers

**GET** `/api/api-keys/providers` 🔒

Get a list of supported AI providers and their available models.

**Response:**
```json
{
  "providers": {
    "openai": {
      "name": "OpenAI",
      "models": ["gpt-4", "gpt-3.5-turbo"],
      "supports_embeddings": true
    },
    "anthropic": {
      "name": "Anthropic",
      "models": ["claude-3-opus", "claude-3-sonnet"],
      "supports_embeddings": false
    }
  }
}
```

---

## Bot API Keys API

### List Bot API Keys

**GET** `/api/bots/{bot_id}/api-keys` 🔒

Get all API keys for a bot (owner only).

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot

**Response:**
```json
[
  {
    "id": "bot_key123",
    "name": "Production API Key",
    "key": "sk-bot-...",
    "permissions": ["read", "chat"],
    "created_at": "2024-01-01T00:00:00Z",
    "last_used": "2024-01-15T12:00:00Z"
  }
]
```

### Create Bot API Key

**POST** `/api/bots/{bot_id}/api-keys` 🔒

Create a new API key for a bot (owner only).

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot

**Request Body:**
```json
{
  "name": "Development API Key",
  "permissions": ["read", "chat"],
  "expires_at": "2024-12-31T23:59:59Z"
}
```

### Update Bot API Key

**PUT** `/api/bots/{bot_id}/api-keys/{key_id}` 🔒

Update a bot API key (owner only).

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot
- `key_id` (string, required): The unique identifier of the API key

### Delete Bot API Key

**DELETE** `/api/bots/{bot_id}/api-keys/{key_id}` 🔒

Delete a bot API key (owner only).

**Parameters:**
- `bot_id` (string, required): The unique identifier of the bot
- `key_id` (string, required): The unique identifier of the API key

---

## WebSocket API

The platform provides real-time communication through WebSocket connections. Authentication is performed using tokens in the connection URL.

### Chat WebSocket

**WebSocket** `ws://localhost:8000/api/ws/chat/{bot_id}?token={access_token}`

Connect to real-time chat with a specific bot.

**Connection Example:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws/chat/bot123?token=your_access_token');
```

**Supported Message Types:**

#### Outgoing Messages (Client → Server)
```json
{
  "type": "message",
  "data": {
    "content": "Hello bot!",
    "session_id": "session123"
  }
}
```

```json
{
  "type": "typing",
  "data": {
    "is_typing": true
  }
}
```

#### Incoming Messages (Server → Client)
```json
{
  "type": "chat_response",
  "data": {
    "message_id": "msg456",
    "content": "Hello! How can I help you?",
    "session_id": "session123",
    "timestamp": "2024-01-15T12:00:00Z"
  }
}
```

```json
{
  "type": "typing_indicator",
  "data": {
    "is_typing": true,
    "user_id": "bot"
  }
}
```

### Notifications WebSocket

**WebSocket** `ws://localhost:8000/api/ws/notifications?token={access_token}`

Receive real-time notifications about system events.

**Connection Example:**
```javascript
const ws = new WebSocket('ws://localhost:8000/api/ws/notifications?token=your_access_token');
```

**Notification Types:**
```json
{
  "type": "bot_update",
  "data": {
    "bot_id": "bot123",
    "action": "updated",
    "changes": ["name", "system_prompt"]
  }
}
```

```json
{
  "type": "permission_change",
  "data": {
    "bot_id": "bot123",
    "user_id": "user456",
    "old_role": "viewer",
    "new_role": "editor"
  }
}
```

```json
{
  "type": "document_update",
  "data": {
    "bot_id": "bot123",
    "document_id": "doc789",
    "status": "processed"
  }
}
```

---

## SDKs and Libraries

### Python SDK

```python
from multi_rag_bot import Client

# Initialize client
client = Client(base_url="http://localhost:8000", token="your_access_token")

# List bots
bots = client.bots.list()

# Send a message
response = client.conversations.send_message(
    bot_id="bot123",
    message="Hello!",
    session_id="session123"
)
```

### JavaScript/Node.js SDK

```javascript
import { MultiRagBotClient } from '@multi-rag-bot/client';

const client = new MultiRagBotClient({
  baseUrl: 'http://localhost:8000',
  token: 'your_access_token'
});

// List bots
const bots = await client.bots.list();

// Send a message
const response = await client.conversations.sendMessage({
  botId: 'bot123',
  message: 'Hello!',
  sessionId: 'session123'
});
```

---

## Webhooks

Configure webhooks to receive notifications about events in your bots.

### Webhook Configuration

**POST** `/api/webhooks` 🔒

Create a new webhook endpoint.

**Request Body:**
```json
{
  "url": "https://your-app.com/webhook",
  "events": ["bot.updated", "conversation.new", "document.processed"],
  "secret": "your_webhook_secret"
}
```

### Webhook Events

Webhooks are sent as POST requests with the following structure:

```json
{
  "event": "bot.updated",
  "data": {
    "bot_id": "bot123",
    "changes": ["name", "system_prompt"],
    "updated_by": "user456"
  },
  "timestamp": "2024-01-15T12:00:00Z",
  "signature": "sha256=..."
}
```

### Signature Verification

Verify webhook signatures using HMAC SHA-256:

```python
import hmac
import hashlib

def verify_webhook_signature(payload, signature, secret):
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f"sha256={expected_signature}" == signature
```

---

## Usage Examples

### Create a Bot with Documents

```bash
# 1. Create a bot
curl -X POST http://localhost:8000/api/bots \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Knowledge Assistant",
    "description": "A bot trained on company documents",
    "system_prompt": "You are a helpful assistant with access to company knowledge.",
    "model": "gpt-4"
  }'

# 2. Upload documents
curl -X POST http://localhost:8000/api/bots/bot123/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@company-handbook.pdf"

# 3. Start a conversation
curl -X POST http://localhost:8000/api/conversations/bots/bot123/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is our vacation policy?",
    "session_id": "session123"
  }'
```

### Real-time Chat Integration

```javascript
class BotChat {
  constructor(botId, token) {
    this.ws = new WebSocket(`ws://localhost:8000/api/ws/chat/${botId}?token=${token}`);
    this.setupEventHandlers();
  }
  
  setupEventHandlers() {
    this.ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'chat_response') {
        this.displayMessage(message.data.content);
      }
    };
  }
  
  sendMessage(content, sessionId) {
    this.ws.send(JSON.stringify({
      type: 'message',
      data: { content, session_id: sessionId }
    }));
  }
}
```

---

## Changelog

### v1.2.0 (2024-01-15)
- Added Bot API Keys for programmatic access
- Enhanced WebSocket message types
- Added document processing status endpoint
- Improved error handling and rate limiting

### v1.1.0 (2024-01-01)
- Added collaboration features (bot permissions)
- WebSocket support for real-time chat
- Document upload and processing
- Conversation session management

### v1.0.0 (2023-12-01)
- Initial API release
- Basic bot management
- User authentication
- API key management

---

## Support

For API support and questions:
- Email: api-support@multi-rag-bot.com
- Documentation: https://docs.multi-rag-bot.com
- GitHub Issues: https://github.com/multi-rag-bot/issues

---

🔒 = Requires authentication
