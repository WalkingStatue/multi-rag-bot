/**
 * Bot Integrations Page
 * 
 * Shows API documentation and integration examples for a specific bot
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { MainLayout } from '../layouts';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { botService } from '../services/botService';
import { BotWithRole } from '../types/bot';
import { 
  ArrowLeftIcon, 
  DocumentDuplicateIcon, 
  CodeBracketIcon,
  CommandLineIcon,
  LinkIcon,
  KeyIcon,
  ExclamationTriangleIcon,
  CheckIcon
} from '@heroicons/react/24/outline';

export const BotIntegrationsPage: React.FC = () => {
  const { botId } = useParams<{ botId: string }>();
  const navigate = useNavigate();
  const [bot, setBot] = useState<BotWithRole | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copiedSection, setCopiedSection] = useState<string | null>(null);

  useEffect(() => {
    if (botId) {
      loadBot();
    }
  }, [botId]);

  const loadBot = async () => {
    if (!botId) return;
    
    try {
      setIsLoading(true);
      const userBots = await botService.getUserBots();
      const foundBot = userBots.find(b => b.bot.id === botId);
      
      if (!foundBot) {
        setError('Bot not found or you do not have access to it.');
        return;
      }
      
      setBot(foundBot);
    } catch (err) {
      console.error('Failed to load bot:', err);
      setError('Failed to load bot information.');
    } finally {
      setIsLoading(false);
    }
  };

  const copyToClipboard = async (text: string, section: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedSection(section);
      setTimeout(() => setCopiedSection(null), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const generateApiKey = () => {
    // In a real implementation, this would call an API to generate a bot-specific API key
    return 'mb_' + Math.random().toString(36).substring(2) + '_' + botId?.substring(0, 8);
  };

  const baseUrl = window.location.origin;
  const apiBaseUrl = baseUrl.replace(':5173', ':8000'); // Adjust for dev environment
  const embedUrl = `${baseUrl}/bots/${botId}/chat?embed=1`;
  const iframeSnippet = `<iframe src=\"${embedUrl}\" width=\"100%\" height=\"600\" style=\"border: 1px solid #e5e7eb; border-radius: 8px;\" allow=\"clipboard-read; clipboard-write\"></iframe>`;

  if (isLoading) {
    return (
      <ProtectedRoute>
        <MainLayout
          title="Bot Integrations"
          subtitle="Loading..."
          showBackButton
          onBackClick={() => navigate('/bots')}
        >
          <div className="flex justify-center items-center h-64">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600"></div>
          </div>
        </MainLayout>
      </ProtectedRoute>
    );
  }

  if (error || !bot) {
    return (
      <ProtectedRoute>
        <MainLayout
          title="Bot Integrations"
          subtitle="Error loading bot"
          showBackButton
          onBackClick={() => navigate('/bots')}
        >
          <Card padding="lg" className="text-center">
            <ExclamationTriangleIcon className="mx-auto h-12 w-12 text-red-400" />
            <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">
              {error || 'Bot not found'}
            </h3>
            <p className="mt-2 text-gray-500 dark:text-gray-400">
              Please check the bot ID and try again.
            </p>
            <Button
              onClick={() => navigate('/bots')}
              className="mt-4"
            >
              Back to Bots
            </Button>
          </Card>
        </MainLayout>
      </ProtectedRoute>
    );
  }

  const curlExample = `curl -X POST "${apiBaseUrl}/api/v1/bots/${botId}/chat" \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -d '{
    "message": "Hello, how can you help me?",
    "conversation_id": "optional-conversation-id"
  }'`;

  const pythonExample = `import requests

# Bot configuration
BOT_ID = "${botId}"
API_KEY = "YOUR_API_KEY"
BASE_URL = "${apiBaseUrl}/api/v1"

# Send a message to the bot
def chat_with_bot(message, conversation_id=None):
    url = f"{BASE_URL}/bots/{BOT_ID}/chat"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    payload = {"message": message}
    if conversation_id:
        payload["conversation_id"] = conversation_id
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Example usage
result = chat_with_bot("What can you help me with?")
print(result)`;

  const javascriptExample = `const BOT_ID = '${botId}';
const API_KEY = 'YOUR_API_KEY';
const BASE_URL = '${apiBaseUrl}/api/v1';

// Function to send message to bot
async function chatWithBot(message, conversationId = null) {
  const response = await fetch(\`\${BASE_URL}/bots/\${BOT_ID}/chat\`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': \`Bearer \${API_KEY}\`
    },
    body: JSON.stringify({
      message: message,
      ...(conversationId && { conversation_id: conversationId })
    })
  });
  
  return await response.json();
}

// Example usage
chatWithBot('Hello, how can you help me?')
  .then(result => console.log(result))
  .catch(error => console.error('Error:', error));`;

  const endpoints = [
    {
      method: 'POST',
      endpoint: `/api/v1/bots/${botId}/chat`,
      description: 'Send a message to the bot and receive a response',
      parameters: [
        { name: 'message', type: 'string', required: true, description: 'The message to send to the bot' },
        { name: 'conversation_id', type: 'string', required: false, description: 'Optional conversation ID for context' }
      ]
    },
    {
      method: 'GET',
      endpoint: `/api/v1/bots/${botId}/conversations`,
      description: 'Get list of conversations with this bot',
      parameters: [
        { name: 'limit', type: 'number', required: false, description: 'Maximum number of conversations to return (default: 50)' },
        { name: 'offset', type: 'number', required: false, description: 'Number of conversations to skip (default: 0)' }
      ]
    },
    {
      method: 'GET',
      endpoint: `/api/v1/bots/${botId}/conversations/{conversation_id}`,
      description: 'Get messages from a specific conversation',
      parameters: [
        { name: 'conversation_id', type: 'string', required: true, description: 'The conversation ID' }
      ]
    },
    {
      method: 'GET',
      endpoint: `/api/v1/bots/${botId}`,
      description: 'Get bot information and configuration',
      parameters: []
    }
  ];

  return (
    <ProtectedRoute>
      <MainLayout
        title={`${bot.bot.name} - Integrations`}
        subtitle="API documentation and integration examples"
        showBackButton
        onBackClick={() => navigate('/bots')}
      >
        <div className="space-y-8">
          {/* Bot Information */}
          <Card title="Bot Information" padding="md">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <h4 className="font-medium text-gray-900 dark:text-gray-100">Bot Name</h4>
                <p className="text-gray-600 dark:text-gray-400">{bot.bot.name}</p>
              </div>
              <div>
                <h4 className="font-medium text-gray-900 dark:text-gray-100">Bot ID</h4>
                <p className="text-gray-600 dark:text-gray-400 font-mono text-sm">{bot.bot.id}</p>
              </div>
              <div>
                <h4 className="font-medium text-gray-900 dark:text-gray-100">Provider</h4>
                <p className="text-gray-600 dark:text-gray-400">{bot.bot.llm_provider}</p>
              </div>
              <div>
                <h4 className="font-medium text-gray-900 dark:text-gray-100">Model</h4>
                <p className="text-gray-600 dark:text-gray-400">{bot.bot.llm_model}</p>
              </div>
            </div>
          </Card>

          {/* API Authentication */}
          <Card title="Authentication" padding="md">
            <div className="space-y-4">
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-4">
                <div className="flex">
                  <KeyIcon className="h-5 w-5 text-yellow-400 mt-0.5" />
                  <div className="ml-3">
                    <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                      API Key Required
                    </h4>
                    <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                      You'll need an API key to authenticate requests. Contact your administrator to obtain one.
                    </p>
                  </div>
                </div>
              </div>
              
              <div>
                <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Authorization Header</h4>
                <div className="relative">
                  <code className="block bg-gray-100 dark:bg-gray-800 p-3 rounded text-sm font-mono">
                    Authorization: Bearer YOUR_API_KEY
                  </code>
                  <button
                    onClick={() => copyToClipboard('Authorization: Bearer YOUR_API_KEY', 'auth-header')}
                    className="absolute top-2 right-2 p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  >
                    {copiedSection === 'auth-header' ? (
                      <CheckIcon className="h-4 w-4 text-green-500" />
                    ) : (
                      <DocumentDuplicateIcon className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </Card>

          {/* Integration Options */}
          <Card title="Integration Options" padding="md">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Iframe Embed */}
              <div className="border rounded-lg p-4 bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-gray-900 dark:text-gray-100">Embed as Iframe</h4>
                  <a href={embedUrl} target="_blank" rel="noreferrer" className="text-sm text-primary-600 hover:underline">Open</a>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  Drop this snippet into any website to embed the chat widget.
                </p>
                <div className="relative">
                  <pre className="bg-gray-900 dark:bg-gray-800 text-gray-100 p-4 rounded-lg overflow-x-auto text-xs">
                    <code>{iframeSnippet}</code>
                  </pre>
                  <button
                    onClick={() => copyToClipboard(iframeSnippet, 'iframe')}
                    className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-300"
                  >
                    {copiedSection === 'iframe' ? (
                      <CheckIcon className="h-4 w-4 text-green-400" />
                    ) : (
                      <DocumentDuplicateIcon className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* API Access */}
              <div className="border rounded-lg p-4 bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-gray-900 dark:text-gray-100">Use the API</h4>
                  <a href={`${apiBaseUrl}/docs`} target="_blank" rel="noreferrer" className="text-sm text-primary-600 hover:underline">API Docs</a>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                  Call our REST endpoints directly from your server or frontend.
                </p>
                <ul className="list-disc list-inside text-sm text-gray-600 dark:text-gray-400 space-y-1">
                  <li>Authentication via Bearer token</li>
                  <li>Endpoints scoped to your Bot ID</li>
                  <li>Streaming via WebSocket supported</li>
                </ul>
              </div>
            </div>
          </Card>

          {/* API Endpoints */}
          <Card title="Available Endpoints" padding="md">
            <div className="space-y-6">
              {endpoints.map((endpoint, index) => (
                <div key={index} className="border-b border-gray-200 dark:border-gray-700 last:border-b-0 pb-6 last:pb-0">
                  <div className="flex items-center space-x-2 mb-2">
                    <span className={`px-2 py-1 text-xs font-mono font-semibold rounded ${
                      endpoint.method === 'GET' 
                        ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                        : 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                    }`}>
                      {endpoint.method}
                    </span>
                    <code className="text-sm font-mono text-gray-700 dark:text-gray-300">
                      {endpoint.endpoint}
                    </code>
                  </div>
                  <p className="text-gray-600 dark:text-gray-400 mb-3">{endpoint.description}</p>
                  
                  {endpoint.parameters.length > 0 && (
                    <div>
                      <h5 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Parameters</h5>
                      <div className="overflow-x-auto">
                        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                          <thead>
                            <tr>
                              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Name
                              </th>
                              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Type
                              </th>
                              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Required
                              </th>
                              <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                                Description
                              </th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                            {endpoint.parameters.map((param, paramIndex) => (
                              <tr key={paramIndex}>
                                <td className="px-3 py-2 text-sm font-mono text-gray-900 dark:text-gray-100">
                                  {param.name}
                                </td>
                                <td className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400">
                                  {param.type}
                                </td>
                                <td className="px-3 py-2 text-sm">
                                  <span className={`px-2 py-1 text-xs rounded ${
                                    param.required 
                                      ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                      : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
                                  }`}>
                                    {param.required ? 'Required' : 'Optional'}
                                  </span>
                                </td>
                                <td className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400">
                                  {param.description}
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>

          {/* Code Examples */}
          <Card title="Code Examples" padding="md">
            <div className="space-y-6">
              {/* cURL Example */}
              <div>
                <div className="flex items-center space-x-2 mb-3">
                  <CommandLineIcon className="h-5 w-5 text-gray-500" />
                  <h4 className="font-medium text-gray-900 dark:text-gray-100">cURL</h4>
                </div>
                <div className="relative">
                  <pre className="bg-gray-900 dark:bg-gray-800 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
                    <code>{curlExample}</code>
                  </pre>
                  <button
                    onClick={() => copyToClipboard(curlExample, 'curl')}
                    className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-300"
                  >
                    {copiedSection === 'curl' ? (
                      <CheckIcon className="h-4 w-4 text-green-400" />
                    ) : (
                      <DocumentDuplicateIcon className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* Python Example */}
              <div>
                <div className="flex items-center space-x-2 mb-3">
                  <CodeBracketIcon className="h-5 w-5 text-gray-500" />
                  <h4 className="font-medium text-gray-900 dark:text-gray-100">Python</h4>
                </div>
                <div className="relative">
                  <pre className="bg-gray-900 dark:bg-gray-800 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
                    <code>{pythonExample}</code>
                  </pre>
                  <button
                    onClick={() => copyToClipboard(pythonExample, 'python')}
                    className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-300"
                  >
                    {copiedSection === 'python' ? (
                      <CheckIcon className="h-4 w-4 text-green-400" />
                    ) : (
                      <DocumentDuplicateIcon className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>

              {/* JavaScript Example */}
              <div>
                <div className="flex items-center space-x-2 mb-3">
                  <CodeBracketIcon className="h-5 w-5 text-gray-500" />
                  <h4 className="font-medium text-gray-900 dark:text-gray-100">JavaScript</h4>
                </div>
                <div className="relative">
                  <pre className="bg-gray-900 dark:bg-gray-800 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
                    <code>{javascriptExample}</code>
                  </pre>
                  <button
                    onClick={() => copyToClipboard(javascriptExample, 'javascript')}
                    className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-300"
                  >
                    {copiedSection === 'javascript' ? (
                      <CheckIcon className="h-4 w-4 text-green-400" />
                    ) : (
                      <DocumentDuplicateIcon className="h-4 w-4" />
                    )}
                  </button>
                </div>
              </div>
            </div>
          </Card>

          {/* Response Format */}
          <Card title="Response Format" padding="md">
            <div className="space-y-4">
              <p className="text-gray-600 dark:text-gray-400">
                All API responses follow this format:
              </p>
              <div className="relative">
                <pre className="bg-gray-900 dark:bg-gray-800 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm">
                  <code>{`{
  "success": true,
  "data": {
    "message": "Bot response message here",
    "conversation_id": "conv_123456789",
    "message_id": "msg_987654321",
    "timestamp": "2024-08-16T16:12:03Z",
    "model_used": "${bot.bot.llm_model}",
    "tokens_used": {
      "prompt": 45,
      "completion": 32,
      "total": 77
    }
  },
  "error": null
}`}</code>
                </pre>
                <button
                  onClick={() => copyToClipboard(`{
  "success": true,
  "data": {
    "message": "Bot response message here",
    "conversation_id": "conv_123456789",
    "message_id": "msg_987654321",
    "timestamp": "2024-08-16T16:12:03Z",
    "model_used": "${bot.bot.llm_model}",
    "tokens_used": {
      "prompt": 45,
      "completion": 32,
      "total": 77
    }
  },
  "error": null
}`, 'response-format')}
                  className="absolute top-2 right-2 p-2 text-gray-400 hover:text-gray-300"
                >
                  {copiedSection === 'response-format' ? (
                    <CheckIcon className="h-4 w-4 text-green-400" />
                  ) : (
                    <DocumentDuplicateIcon className="h-4 w-4" />
                  )}
                </button>
              </div>
            </div>
          </Card>

          {/* Rate Limits & Guidelines */}
          <Card title="Guidelines & Limitations" padding="md">
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Rate Limits</h4>
                  <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                    <li>• 100 requests per minute per API key</li>
                    <li>• 1000 requests per hour per API key</li>
                    <li>• Rate limits reset every hour</li>
                  </ul>
                </div>
                <div>
                  <h4 className="font-medium text-gray-900 dark:text-gray-100 mb-2">Best Practices</h4>
                  <ul className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                    <li>• Include conversation_id for context</li>
                    <li>• Handle rate limit responses (429)</li>
                    <li>• Implement retry logic with backoff</li>
                    <li>• Keep messages under 4000 characters</li>
                  </ul>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
};
