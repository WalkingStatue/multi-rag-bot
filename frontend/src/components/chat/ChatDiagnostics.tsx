/**
 * Chat diagnostics component for debugging chat system issues
 */
import React, { useState } from 'react';
import { chatWebSocketService } from '../../services/chatWebSocketService';
import { useChatStore } from '../../stores/chatStore';

interface ChatDiagnosticsProps {
  botId: string;
  className?: string;
}

export const ChatDiagnostics: React.FC<ChatDiagnosticsProps> = ({
  botId,
  className = ''
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [diagnostics, setDiagnostics] = useState<any>(null);
  const [isRunning, setIsRunning] = useState(false);
  
  const { uiState, sessions, currentSessionId } = useChatStore();

  const runDiagnostics = async () => {
    setIsRunning(true);
    try {
      const token = localStorage.getItem('access_token');
      const results = {
        timestamp: new Date().toISOString(),
        environment: {
          apiUrl: (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000',
          wsUrl: (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8000',
          userAgent: navigator.userAgent,
          online: navigator.onLine
        },
        authentication: {
          hasToken: !!token,
          tokenLength: token?.length || 0
        },
        websocket: {
          isConnected: chatWebSocketService.isConnected(),
          currentBotId: chatWebSocketService.getCurrentBotId(),
          currentSessionId: chatWebSocketService.getCurrentSessionId(),
          readyState: chatWebSocketService.isConnected() ? 'OPEN' : 'CLOSED'
        },
        chatStore: {
          sessionsCount: sessions.length,
          currentSessionId,
          isLoading: uiState.isLoading,
          connectionStatus: uiState.connectionStatus,
          messagesCount: Object.keys(useChatStore.getState().messages).length
        },
        backend: {
          healthCheck: null as any,
          wsEndpoint: null as any
        }
      };

      // Test backend health
      try {
        const healthResponse = await fetch(`${results.environment.apiUrl}/health`);
        results.backend.healthCheck = {
          status: healthResponse.status,
          ok: healthResponse.ok,
          statusText: healthResponse.statusText
        };
      } catch (error: any) {
        results.backend.healthCheck = {
          error: error.message,
          type: error.name
        };
      }

      // Test WebSocket endpoint
      try {
        const wsUrl = `${results.environment.wsUrl}/api/ws/chat/${botId}?token=${encodeURIComponent(token || '')}`;
        const testWs = new WebSocket(wsUrl);
        
        await new Promise((resolve, reject) => {
          const timeout = setTimeout(() => {
            testWs.close();
            reject(new Error('WebSocket connection timeout'));
          }, 5000);

          testWs.onopen = () => {
            clearTimeout(timeout);
            results.backend.wsEndpoint = {
              status: 'success',
              readyState: testWs.readyState
            };
            testWs.close();
            resolve(true);
          };

          testWs.onerror = (error) => {
            clearTimeout(timeout);
            results.backend.wsEndpoint = {
              status: 'error',
              error: 'WebSocket connection failed'
            };
            reject(error);
          };
        });
      } catch (error: any) {
        results.backend.wsEndpoint = {
          status: 'error',
          error: error.message,
          type: error.name
        };
      }

      setDiagnostics(results);
    } catch (error) {
      console.error('Diagnostics failed:', error);
      setDiagnostics({
        error: 'Failed to run diagnostics',
        details: error
      });
    } finally {
      setIsRunning(false);
    }
  };

  const copyToClipboard = () => {
    if (diagnostics) {
      navigator.clipboard.writeText(JSON.stringify(diagnostics, null, 2));
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className={`text-xs text-gray-500 hover:text-gray-700 underline ${className}`}
      >
        Chat Diagnostics
      </button>
    );
  }

  return (
    <div className={`fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 ${className}`}>
      <div className="bg-white rounded-lg p-6 max-w-4xl max-h-[80vh] overflow-auto">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Chat System Diagnostics</h3>
          <button
            onClick={() => setIsOpen(false)}
            className="text-gray-500 hover:text-gray-700"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="space-y-4">
          <div className="flex space-x-2">
            <button
              onClick={runDiagnostics}
              disabled={isRunning}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {isRunning ? 'Running...' : 'Run Diagnostics'}
            </button>
            
            {diagnostics && (
              <button
                onClick={copyToClipboard}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
              >
                Copy Results
              </button>
            )}
          </div>

          {diagnostics && (
            <div className="bg-gray-100 p-4 rounded-lg">
              <pre className="text-xs overflow-auto max-h-96">
                {JSON.stringify(diagnostics, null, 2)}
              </pre>
            </div>
          )}

          {diagnostics && (
            <div className="space-y-2 text-sm">
              <h4 className="font-semibold">Quick Analysis:</h4>
              <ul className="space-y-1">
                <li className={`flex items-center space-x-2 ${diagnostics.authentication?.hasToken ? 'text-green-600' : 'text-red-600'}`}>
                  <span>{diagnostics.authentication?.hasToken ? '✓' : '✗'}</span>
                  <span>Authentication Token</span>
                </li>
                <li className={`flex items-center space-x-2 ${diagnostics.backend?.healthCheck?.ok ? 'text-green-600' : 'text-red-600'}`}>
                  <span>{diagnostics.backend?.healthCheck?.ok ? '✓' : '✗'}</span>
                  <span>Backend Health</span>
                </li>
                <li className={`flex items-center space-x-2 ${diagnostics.backend?.wsEndpoint?.status === 'success' ? 'text-green-600' : 'text-red-600'}`}>
                  <span>{diagnostics.backend?.wsEndpoint?.status === 'success' ? '✓' : '✗'}</span>
                  <span>WebSocket Endpoint</span>
                </li>
                <li className={`flex items-center space-x-2 ${diagnostics.websocket?.isConnected ? 'text-green-600' : 'text-yellow-600'}`}>
                  <span>{diagnostics.websocket?.isConnected ? '✓' : '⚠'}</span>
                  <span>WebSocket Connection</span>
                </li>
                <li className={`flex items-center space-x-2 ${diagnostics.chatStore?.sessionsCount > 0 ? 'text-green-600' : 'text-yellow-600'}`}>
                  <span>{diagnostics.chatStore?.sessionsCount > 0 ? '✓' : '⚠'}</span>
                  <span>Chat Sessions ({diagnostics.chatStore?.sessionsCount || 0})</span>
                </li>
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};