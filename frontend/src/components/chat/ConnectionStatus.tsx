/**
 * Connection status indicator for chat WebSocket
 */
import React, { useState, useEffect } from 'react';
import { chatWebSocketService } from '../../services/chatWebSocketService';
import { runWebSocketDiagnostics } from '../../utils/websocketDiagnostics';

interface ConnectionStatusProps {
  className?: string;
}

export const ConnectionStatus: React.FC<ConnectionStatusProps> = ({
  className = ''
}) => {
  const [status, setStatus] = useState<'connected' | 'disconnected' | 'error' | 'reconnecting' | 'failed'>('disconnected');
  const [message, setMessage] = useState<string>('');

  useEffect(() => {
    const unsubscribe = chatWebSocketService.onConnectionStatus((statusData) => {
      switch (statusData.status) {
        case 'connected':
          setStatus('connected');
          setMessage('Connected');
          break;
        case 'disconnected':
          setStatus('disconnected');
          setMessage('Disconnected');
          break;
        case 'error':
          setStatus('error');
          const errorMsg = statusData.error || 'Connection error';
          if (errorMsg.includes('REST API')) {
            setMessage('Using REST API (WebSocket unavailable)');
          } else {
            setMessage(errorMsg);
          }
          break;
        case 'failed':
          setStatus('error');
          setMessage(statusData.message || 'Connection failed');
          break;
        default:
          setStatus('reconnecting');
          setMessage('Reconnecting...');
      }
    });

    // Check initial connection status
    if (chatWebSocketService.isConnected()) {
      setStatus('connected');
      setMessage('Connected');
    }

    return unsubscribe;
  }, []);

  if (status === 'connected') {
    return null; // Don't show anything when connected
  }

  const getStatusColor = () => {
    switch (status) {
      case 'disconnected':
        return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'error':
      case 'failed':
        return 'text-red-600 bg-red-50 border-red-200';
      case 'reconnecting':
        return 'text-blue-600 bg-blue-50 border-blue-200';
      default:
        return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getStatusIcon = () => {
    switch (status) {
      case 'disconnected':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        );
      case 'error':
      case 'failed':
        return (
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
          </svg>
        );
      case 'reconnecting':
        return (
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <div className={`flex items-center space-x-2 px-3 py-2 border rounded-lg text-sm ${getStatusColor()} ${className}`}>
      {getStatusIcon()}
      <span>{message}</span>
      {status === 'error' && (
        <div className="ml-2 space-x-2">
          <button
            onClick={async () => {
              const botId = chatWebSocketService.getCurrentBotId();
              const sessionId = chatWebSocketService.getCurrentSessionId();
              const token = localStorage.getItem('access_token');
              if (botId && token) {
                await chatWebSocketService.connectToBot(botId, token, sessionId || undefined);
              }
            }}
            className="text-xs underline hover:no-underline"
          >
            Retry
          </button>
          <button
            onClick={async () => {
              const botId = chatWebSocketService.getCurrentBotId();
              const token = localStorage.getItem('access_token');
              if (botId && token) {
                await runWebSocketDiagnostics(botId, token);
              }
            }}
            className="text-xs underline hover:no-underline"
          >
            Diagnose
          </button>
        </div>
      )}
    </div>
  );
};