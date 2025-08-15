/**
 * Custom hook for sending chat messages with error handling
 */
import { useCallback } from 'react';
import { useChatStore } from '../stores/chatStore';
import { chatService } from '../services/chatService';
import { MessageWithStatus, ChatError } from '../types/chat';
// Generate a simple UUID-like string
const generateId = () => {
  return crypto.randomUUID ? crypto.randomUUID() : 
    'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
};

interface UseChatMessageOptions {
  botId: string;
  sessionId: string;
}

interface UseChatMessageReturn {
  sendMessage: (content: string) => Promise<void>;
  isLoading: boolean;
  error: string | null;
  clearError: () => void;
}

export const useChatMessage = ({
  botId,
  sessionId
}: UseChatMessageOptions): UseChatMessageReturn => {
  const {
    addMessage,
    updateMessage,
    uiState,
    setLoading,
    setError,
    clearError,
    lastError
  } = useChatStore();

  const sendMessage = useCallback(async (content: string) => {
    if (!content.trim() || !sessionId) return;

    const tempId = generateId();
    const timestamp = new Date().toISOString();

    // Add user message immediately
    const userMessage: MessageWithStatus = {
      id: tempId,
      tempId,
      session_id: sessionId,
      bot_id: botId,
      user_id: 'current-user', // This should come from auth context
      role: 'user',
      content: content.trim(),
      created_at: timestamp,
      status: 'sending'
    };

    addMessage(sessionId, userMessage);
    setLoading(true);
    clearError();

    try {
      // Send message to backend
      const response = await chatService.sendMessage(botId, {
        message: content.trim(),
        session_id: sessionId
      });

      // Update user message status to sent
      updateMessage(sessionId, tempId, { status: 'sent' });

      // Add assistant response
      const assistantMessage: MessageWithStatus = {
        id: generateId(),
        session_id: sessionId,
        bot_id: botId,
        user_id: 'assistant',
        role: 'assistant',
        content: response.message,
        message_metadata: {
          chunks_used: response.chunks_used,
          processing_time: response.processing_time,
          ...response.metadata
        },
        created_at: new Date().toISOString(),
        status: 'sent'
      };

      addMessage(sessionId, assistantMessage);

    } catch (error: any) {
      // Parse the error
      const chatError: ChatError = error.chatError || {
        type: 'unknown',
        message: 'Failed to send message',
        retryable: true
      };

      // Update user message with error
      updateMessage(sessionId, tempId, { 
        status: 'error',
        error: chatError
      });

      // Set global error for UI display
      setError(chatError.message);

      // For rate limit errors, provide additional context
      if (chatError.type === 'rate_limit') {
        const retryMessage = chatError.retryAfter 
          ? ` Please wait ${chatError.retryAfter} seconds before trying again.`
          : ' Please wait a moment before trying again.';
        
        setError(chatError.message + retryMessage);
      }

    } finally {
      setLoading(false);
    }
  }, [botId, sessionId, addMessage, updateMessage, setLoading, setError, clearError]);

  return {
    sendMessage,
    isLoading: uiState.isLoading,
    error: lastError,
    clearError
  };
};