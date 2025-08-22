/**
 * API Documentation Page
 * Comprehensive documentation for all available API endpoints
 */
import React, { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

interface EndpointProps {
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
  path: string;
  description: string;
  parameters?: { name: string; type: string; required: boolean; description: string }[];
  requestBody?: string;
  responseExample?: string;
  authRequired?: boolean;
}

const Endpoint: React.FC<EndpointProps> = ({
  method,
  path,
  description,
  parameters = [],
  requestBody,
  responseExample,
  authRequired = true
}) => {
  const [showDetails, setShowDetails] = useState(false);

  const methodColors = {
    GET: 'bg-green-500',
    POST: 'bg-blue-500',
    PUT: 'bg-yellow-500',
    PATCH: 'bg-purple-500',
    DELETE: 'bg-red-500'
  };

  return (
    <div className="border border-gray-200 rounded-lg mb-4">
      <div
        className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
        onClick={() => setShowDetails(!showDetails)}
      >
        <div className="flex items-center gap-4">
          <span className={`px-3 py-1 rounded text-white text-sm font-medium ${methodColors[method]}`}>
            {method}
          </span>
          <code className="text-lg font-mono text-gray-800">{path}</code>
          {authRequired && (
            <span className="px-2 py-1 bg-orange-100 text-orange-800 text-xs rounded">
              Auth Required
            </span>
          )}
        </div>
        <p className="text-gray-600 mt-2">{description}</p>
      </div>

      {showDetails && (
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          {parameters.length > 0 && (
            <div className="mb-4">
              <h4 className="font-semibold text-gray-800 mb-2">Parameters</h4>
              <div className="overflow-x-auto">
                <table className="min-w-full bg-white rounded border">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="px-4 py-2 text-left text-sm font-semibold">Name</th>
                      <th className="px-4 py-2 text-left text-sm font-semibold">Type</th>
                      <th className="px-4 py-2 text-left text-sm font-semibold">Required</th>
                      <th className="px-4 py-2 text-left text-sm font-semibold">Description</th>
                    </tr>
                  </thead>
                  <tbody>
                    {parameters.map((param, index) => (
                      <tr key={index} className="border-t">
                        <td className="px-4 py-2 font-mono text-sm">{param.name}</td>
                        <td className="px-4 py-2 text-sm">{param.type}</td>
                        <td className="px-4 py-2 text-sm">
                          {param.required ? (
                            <span className="text-red-600">Yes</span>
                          ) : (
                            <span className="text-gray-500">No</span>
                          )}
                        </td>
                        <td className="px-4 py-2 text-sm">{param.description}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {requestBody && (
            <div className="mb-4">
              <h4 className="font-semibold text-gray-800 mb-2">Request Body</h4>
              <SyntaxHighlighter language="json" style={oneDark} className="text-sm rounded">
                {requestBody}
              </SyntaxHighlighter>
            </div>
          )}

          {responseExample && (
            <div className="mb-4">
              <h4 className="font-semibold text-gray-800 mb-2">Response Example</h4>
              <SyntaxHighlighter language="json" style={oneDark} className="text-sm rounded">
                {responseExample}
              </SyntaxHighlighter>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const ApiDocsPage: React.FC = () => {
  const [activeSection, setActiveSection] = useState('auth');

  const sections = [
    { id: 'auth', name: 'Authentication' },
    { id: 'users', name: 'Users' },
    { id: 'bots', name: 'Bots' },
    { id: 'documents', name: 'Documents' },
    { id: 'conversations', name: 'Conversations' },
    { id: 'api-keys', name: 'API Keys' },
    { id: 'websockets', name: 'WebSockets' },
  ];

  const authEndpoints = [
    {
      method: 'POST' as const,
      path: '/api/auth/login',
      description: 'Authenticate user with email and password',
      parameters: [],
      requestBody: JSON.stringify({
        email: 'user@example.com',
        password: 'password123'
      }, null, 2),
      responseExample: JSON.stringify({
        access_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        refresh_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        token_type: 'bearer',
        expires_in: 3600
      }, null, 2),
      authRequired: false
    },
    {
      method: 'POST' as const,
      path: '/api/auth/register',
      description: 'Register a new user account',
      parameters: [],
      requestBody: JSON.stringify({
        email: 'newuser@example.com',
        password: 'password123',
        username: 'newuser'
      }, null, 2),
      responseExample: JSON.stringify({
        id: '12345',
        email: 'newuser@example.com',
        username: 'newuser',
        created_at: '2024-01-01T00:00:00Z'
      }, null, 2),
      authRequired: false
    },
    {
      method: 'POST' as const,
      path: '/api/auth/refresh',
      description: 'Refresh access token using refresh token',
      parameters: [],
      requestBody: JSON.stringify({
        refresh_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
      }, null, 2),
      responseExample: JSON.stringify({
        access_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        refresh_token: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',
        token_type: 'bearer',
        expires_in: 3600
      }, null, 2),
      authRequired: false
    },
    {
      method: 'POST' as const,
      path: '/api/auth/logout',
      description: 'Logout user and invalidate tokens',
      parameters: [],
      responseExample: JSON.stringify({
        message: 'Successfully logged out'
      }, null, 2)
    }
  ];

  const userEndpoints = [
    {
      method: 'GET' as const,
      path: '/api/users/profile',
      description: 'Get current user profile information',
      responseExample: JSON.stringify({
        id: '12345',
        email: 'user@example.com',
        username: 'user',
        created_at: '2024-01-01T00:00:00Z',
        last_login: '2024-01-15T12:00:00Z'
      }, null, 2)
    },
    {
      method: 'PUT' as const,
      path: '/api/users/profile',
      description: 'Update current user profile',
      requestBody: JSON.stringify({
        username: 'newusername',
        email: 'newemail@example.com'
      }, null, 2),
      responseExample: JSON.stringify({
        id: '12345',
        email: 'newemail@example.com',
        username: 'newusername',
        updated_at: '2024-01-15T12:00:00Z'
      }, null, 2)
    }
  ];

  const botEndpoints = [
    {
      method: 'GET' as const,
      path: '/api/bots',
      description: 'Get all bots accessible to the current user',
      responseExample: JSON.stringify([
        {
          id: 'bot123',
          name: 'My AI Assistant',
          description: 'A helpful AI assistant',
          model: 'gpt-4',
          role: 'owner',
          created_at: '2024-01-01T00:00:00Z'
        }
      ], null, 2)
    },
    {
      method: 'POST' as const,
      path: '/api/bots',
      description: 'Create a new bot',
      requestBody: JSON.stringify({
        name: 'My New Bot',
        description: 'A description of my bot',
        system_prompt: 'You are a helpful assistant',
        model: 'gpt-4',
        temperature: 0.7,
        max_tokens: 2000
      }, null, 2),
      responseExample: JSON.stringify({
        id: 'bot456',
        name: 'My New Bot',
        description: 'A description of my bot',
        system_prompt: 'You are a helpful assistant',
        model: 'gpt-4',
        temperature: 0.7,
        max_tokens: 2000,
        created_at: '2024-01-15T12:00:00Z'
      }, null, 2)
    },
    {
      method: 'GET' as const,
      path: '/api/bots/{bot_id}',
      description: 'Get a specific bot by ID',
      parameters: [
        { name: 'bot_id', type: 'string', required: true, description: 'The unique identifier of the bot' }
      ],
      responseExample: JSON.stringify({
        id: 'bot123',
        name: 'My AI Assistant',
        description: 'A helpful AI assistant',
        system_prompt: 'You are a helpful assistant',
        model: 'gpt-4',
        temperature: 0.7,
        created_at: '2024-01-01T00:00:00Z'
      }, null, 2)
    },
    {
      method: 'PUT' as const,
      path: '/api/bots/{bot_id}',
      description: 'Update a bot configuration',
      parameters: [
        { name: 'bot_id', type: 'string', required: true, description: 'The unique identifier of the bot' }
      ],
      requestBody: JSON.stringify({
        name: 'Updated Bot Name',
        system_prompt: 'Updated system prompt',
        temperature: 0.8
      }, null, 2)
    },
    {
      method: 'DELETE' as const,
      path: '/api/bots/{bot_id}',
      description: 'Delete a bot (owner only)',
      parameters: [
        { name: 'bot_id', type: 'string', required: true, description: 'The unique identifier of the bot' }
      ]
    }
  ];

  const documentEndpoints = [
    {
      method: 'GET' as const,
      path: '/api/bots/{bot_id}/documents',
      description: 'Get all documents for a bot',
      parameters: [
        { name: 'bot_id', type: 'string', required: true, description: 'The unique identifier of the bot' }
      ],
      responseExample: JSON.stringify([
        {
          id: 'doc123',
          filename: 'document.pdf',
          size: 1024000,
          status: 'processed',
          uploaded_at: '2024-01-01T00:00:00Z'
        }
      ], null, 2)
    },
    {
      method: 'POST' as const,
      path: '/api/bots/{bot_id}/documents/upload',
      description: 'Upload a new document to a bot',
      parameters: [
        { name: 'bot_id', type: 'string', required: true, description: 'The unique identifier of the bot' }
      ],
      requestBody: 'FormData with file field',
      responseExample: JSON.stringify({
        id: 'doc456',
        filename: 'new-document.pdf',
        size: 2048000,
        status: 'processing',
        uploaded_at: '2024-01-15T12:00:00Z'
      }, null, 2)
    },
    {
      method: 'DELETE' as const,
      path: '/api/bots/{bot_id}/documents/{document_id}',
      description: 'Delete a document from a bot',
      parameters: [
        { name: 'bot_id', type: 'string', required: true, description: 'The unique identifier of the bot' },
        { name: 'document_id', type: 'string', required: true, description: 'The unique identifier of the document' }
      ]
    }
  ];

  const conversationEndpoints = [
    {
      method: 'GET' as const,
      path: '/api/conversations/sessions',
      description: 'Get all conversation sessions',
      parameters: [
        { name: 'bot_id', type: 'string', required: false, description: 'Filter by bot ID' }
      ],
      responseExample: JSON.stringify([
        {
          id: 'session123',
          bot_id: 'bot123',
          title: 'Conversation about AI',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T01:00:00Z'
        }
      ], null, 2)
    },
    {
      method: 'POST' as const,
      path: '/api/conversations/bots/{bot_id}/chat',
      description: 'Send a message to a bot',
      parameters: [
        { name: 'bot_id', type: 'string', required: true, description: 'The unique identifier of the bot' }
      ],
      requestBody: JSON.stringify({
        message: 'Hello, how are you?',
        session_id: 'session123'
      }, null, 2),
      responseExample: JSON.stringify({
        session_id: 'session123',
        message_id: 'msg456',
        response: 'Hello! I\'m doing well, thank you for asking.',
        timestamp: '2024-01-15T12:00:00Z'
      }, null, 2)
    }
  ];

  const apiKeyEndpoints = [
    {
      method: 'GET' as const,
      path: '/api/api-keys',
      description: 'Get all API keys for current user',
      responseExample: JSON.stringify([
        {
          id: 'key123',
          provider: 'openai',
          name: 'My OpenAI Key',
          created_at: '2024-01-01T00:00:00Z',
          last_used: '2024-01-15T12:00:00Z'
        }
      ], null, 2)
    },
    {
      method: 'POST' as const,
      path: '/api/api-keys',
      description: 'Add a new API key',
      requestBody: JSON.stringify({
        provider: 'openai',
        name: 'My OpenAI Key',
        key: 'sk-...'
      }, null, 2),
      responseExample: JSON.stringify({
        id: 'key456',
        provider: 'openai',
        name: 'My OpenAI Key',
        created_at: '2024-01-15T12:00:00Z'
      }, null, 2)
    },
    {
      method: 'DELETE' as const,
      path: '/api/api-keys/{key_id}',
      description: 'Delete an API key',
      parameters: [
        { name: 'key_id', type: 'string', required: true, description: 'The unique identifier of the API key' }
      ]
    }
  ];

  const renderEndpoints = () => {
    switch (activeSection) {
      case 'auth':
        return authEndpoints.map((endpoint, index) => <Endpoint key={index} {...endpoint} />);
      case 'users':
        return userEndpoints.map((endpoint, index) => <Endpoint key={index} {...endpoint} />);
      case 'bots':
        return botEndpoints.map((endpoint, index) => <Endpoint key={index} {...endpoint} />);
      case 'documents':
        return documentEndpoints.map((endpoint, index) => <Endpoint key={index} {...endpoint} />);
      case 'conversations':
        return conversationEndpoints.map((endpoint, index) => <Endpoint key={index} {...endpoint} />);
      case 'api-keys':
        return apiKeyEndpoints.map((endpoint, index) => <Endpoint key={index} {...endpoint} />);
      case 'websockets':
        return (
          <div className="space-y-4">
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-blue-900 mb-2">WebSocket Connections</h3>
              <p className="text-blue-800 mb-4">
                Real-time communication is handled through WebSocket connections. Authentication is done via token query parameter.
              </p>
              
              <div className="space-y-4">
                <div>
                  <h4 className="font-semibold text-blue-900">Chat WebSocket</h4>
                  <code className="bg-white px-2 py-1 rounded text-sm">
                    ws://localhost:8000/api/ws/chat/{'{bot_id}'}?token={'{your_token}'}
                  </code>
                  <p className="text-sm text-blue-700 mt-1">
                    Connect to real-time chat with a specific bot. Supports bidirectional messaging and typing indicators.
                  </p>
                </div>
                
                <div>
                  <h4 className="font-semibold text-blue-900">Notifications WebSocket</h4>
                  <code className="bg-white px-2 py-1 rounded text-sm">
                    ws://localhost:8000/api/ws/notifications?token={'{your_token}'}
                  </code>
                  <p className="text-sm text-blue-700 mt-1">
                    Receive real-time notifications about bot updates, permissions changes, and system events.
                  </p>
                </div>
              </div>
            </div>
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">API Documentation</h1>
          <p className="text-gray-600">
            Comprehensive documentation for the Multi-RAG Bot Platform API. 
            All API endpoints require authentication unless otherwise specified.
          </p>
        </div>

        <div className="flex gap-8">
          {/* Sidebar */}
          <div className="w-64 flex-shrink-0">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
              <h3 className="font-semibold text-gray-900 mb-4">API Sections</h3>
              <nav className="space-y-2">
                {sections.map((section) => (
                  <button
                    key={section.id}
                    onClick={() => setActiveSection(section.id)}
                    className={`w-full text-left px-3 py-2 rounded transition-colors ${
                      activeSection === section.id
                        ? 'bg-blue-100 text-blue-700 font-medium'
                        : 'text-gray-600 hover:bg-gray-50'
                    }`}
                  >
                    {section.name}
                  </button>
                ))}
              </nav>
            </div>

            {/* Authentication Info */}
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 mt-4">
              <h3 className="font-semibold text-gray-900 mb-2">Authentication</h3>
              <p className="text-sm text-gray-600 mb-2">
                Most endpoints require a Bearer token in the Authorization header:
              </p>
              <code className="block bg-gray-100 p-2 rounded text-xs">
                Authorization: Bearer your_access_token
              </code>
            </div>
          </div>

          {/* Main Content */}
          <div className="flex-1">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              <div className="p-6 border-b border-gray-200">
                <h2 className="text-2xl font-semibold text-gray-900">
                  {sections.find(s => s.id === activeSection)?.name} API
                </h2>
              </div>
              <div className="p-6">
                {renderEndpoints()}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ApiDocsPage;
