/**
 * Main chat window component
 */
import React, { useEffect, useRef } from 'react';
import { useChatStore } from '../../stores/chatStore';
import { chatWebSocketService } from '../../services/chatWebSocketService';
import { useChatSession } from '../../hooks/useChatSession';
import { MessageList } from './MessageList';
import { MessageInput } from './MessageInput';
import { SessionList } from './SessionList';
import { ConnectionStatus } from './ConnectionStatus';
import { TypingIndicator } from './TypingIndicator';
import { ChatDiagnostics } from './ChatDiagnostics';
import { ScrollDebug } from './ScrollDebug';
import { ErrorBoundary, ChatErrorFallback } from '../common/ErrorBoundary';

import { BotResponse } from '../../types/bot';

interface ChatWindowProps {
  bot: BotResponse;
  className?: string;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ bot, className = '' }) => {
  const {
    currentSessionId,
    uiState,
    setCurrentBot,
    setConnectionStatus,
    getCurrentMessages,
    addMessage,
    addTypingUser,
    removeTypingUser
  } = useChatStore();

  const cleanupFunctions = useRef<(() => void)[]>([]);

  // Use the improved session management hook
  const {
    sessions,
    isLoading,
    error,
    selectSession
  } = useChatSession({
    botId: bot.id,
    autoSelectFirst: true,
    preloadMessages: true
  });

  // Set current bot in store
  useEffect(() => {
    setCurrentBot(bot.id);
  }, [bot.id, setCurrentBot]);

  // Set up WebSocket event listeners
  useEffect(() => {
    if (!bot.id) return;

    console.log('ChatWindow: Setting up WebSocket event listeners for bot:', bot.id);

    const unsubscribeChat = chatWebSocketService.onChatMessage((message) => {
      // Handle incoming chat messages
      if (message.bot_id === bot.id) {
        addMessage(message.data.session_id, {
          id: message.data.message_id,
          session_id: message.data.session_id,
          bot_id: message.bot_id,
          user_id: message.data.user_id,
          role: message.data.role,
          content: message.data.content,
          message_metadata: message.data.metadata,
          created_at: message.data.timestamp,
          status: 'sent'
        });
      }
    });

    const unsubscribeTyping = chatWebSocketService.onTypingIndicator((indicator) => {
      if (indicator.bot_id === bot.id) {
        if (indicator.data.is_typing) {
          addTypingUser(indicator.data.username);
        } else {
          removeTypingUser(indicator.data.username);
        }
      }
    });

    const unsubscribeConnection = chatWebSocketService.onConnectionStatus((status) => {
      setConnectionStatus(status);
    });

    // Store cleanup functions
    cleanupFunctions.current = [
      unsubscribeChat,
      unsubscribeTyping,
      unsubscribeConnection
    ];

    return () => {
      // Run cleanup functions
      cleanupFunctions.current.forEach(cleanup => {
        try {
          cleanup();
        } catch (error) {
          console.error('Error during cleanup:', error);
        }
      });
      cleanupFunctions.current = [];
    };
  }, [bot.id, addMessage, addTypingUser, removeTypingUser, setConnectionStatus]);

  const currentMessages = getCurrentMessages();

  if (isLoading) {
    return (
      <div className={`flex items-center justify-center h-96 ${className}`}>
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <span className="text-gray-600">Loading chat...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex items-center justify-center h-96 ${className}`}>
        <div className="text-center text-red-600">
          <div className="mb-4">
            <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <p className="text-lg font-medium">Chat Error</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <ErrorBoundary fallback={<ChatErrorFallback error="Chat failed to load" />}>
      <div className={`flex h-full bg-white rounded-lg shadow-lg overflow-hidden chat-container ${className}`}>
        {/* Session sidebar */}
        <div className="w-1/4 border-r border-gray-200 flex flex-col min-h-0">
          <div className="p-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">
              Chat with {bot.name}
            </h3>
            <div className="mt-2 space-y-2">
              <ConnectionStatus />
              <ChatDiagnostics botId={bot.id} />
              <ScrollDebug />
            </div>
          </div>
          <SessionList bot={bot} sessions={sessions} onSelectSession={selectSession} />
        </div>

        {/* Chat area */}
        <div className="flex-1 flex flex-col min-h-0">
          {currentSessionId ? (
            <ErrorBoundary fallback={<ChatErrorFallback error="Chat messages failed to load" />}>
              <div className="flex-1 flex flex-col min-h-0">
                <MessageList messages={currentMessages} />
                <TypingIndicator users={uiState.typingUsers} />
                <div className="flex-shrink-0">
                  <MessageInput botId={bot.id} sessionId={currentSessionId} />
                </div>
              </div>
            </ErrorBoundary>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <p className="text-lg mb-2">No conversation selected</p>
                <p className="text-sm">Select a conversation or start a new one</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </ErrorBoundary>
  );
};