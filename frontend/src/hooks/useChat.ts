/**
 * Custom hook for chat functionality
 */
import { useEffect, useCallback, useRef } from 'react';
import { useChatStore } from '../stores/chatStore';
import { chatService } from '../services/chatService';
import { chatWebSocketService } from '../services/chatWebSocketService';
import { authService } from '../services/authService';
import { useAuth } from './useAuth';
import { BotResponse } from '../types/bot';
import { ConversationSession, MessageWithStatus } from '../types/chat';

export const useChat = (bot?: BotResponse) => {
  const { user } = useAuth();
  const isInitialized = useRef(false);

  const {
    sessions,
    currentSessionId,
    currentBotId,
    uiState,
    setSessions,
    setCurrentBot,
    setCurrentSession,
    setMessages,
    addMessage,
    updateMessage,
    setLoading,
    setConnectionStatus,
    addTypingUser,
    removeTypingUser,
    getCurrentMessages,
    getCurrentSession
  } = useChatStore();

  // Initialize chat for a bot
  const initializeChat = useCallback(async (botData: BotResponse) => {
    const token = authService.getAccessToken();
    if (!user || !token || isInitialized.current) return;

    try {
      setLoading(true);
      setCurrentBot(botData.id);

      // Load existing sessions
      const botSessions = await chatService.getSessions(botData.id);
      setSessions(botSessions);

      // Connect to WebSocket
      chatWebSocketService.connectToBot(botData.id, token);

      // Set up WebSocket event listeners
      const unsubscribeChat = chatWebSocketService.onChatMessage((message) => {
        if (message.bot_id === botData.id) {
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
        if (indicator.bot_id === botData.id) {
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

      isInitialized.current = true;

      return () => {
        unsubscribeChat();
        unsubscribeTyping();
        unsubscribeConnection();
        chatWebSocketService.disconnect();
        isInitialized.current = false;
      };

    } catch (error) {
      setConnectionStatus({
        status: 'error',
        error: 'Failed to initialize chat'
      });
    } finally {
      setLoading(false);
    }
  }, [user, setLoading, setCurrentBot, setSessions, addMessage, addTypingUser, removeTypingUser, setConnectionStatus]);

  // Create a new session
  const createSession = useCallback(async (botId: string, title?: string): Promise<ConversationSession | null> => {
    try {
      const newSession = await chatService.createBotSession(botId, title);
      const { addSession, setCurrentSession, setMessages } = useChatStore.getState();
      addSession(newSession);
      setCurrentSession(newSession.id);
      setMessages(newSession.id, []);
      return newSession;
    } catch (error) {
      return null;
    }
  }, []);

  // Load session messages
  const loadSessionMessages = useCallback(async (sessionId: string) => {
    try {
      setLoading(true);
      const messages = await chatService.getSessionMessages(sessionId);
      setMessages(sessionId, messages.map(msg => ({ ...msg, status: 'sent' as const })));
    } catch (error) {
      // Failed to load session messages
    } finally {
      setLoading(false);
    }
  }, [setLoading, setMessages]);

  // Send a message
  const sendMessage = useCallback(async (
    botId: string, 
    sessionId: string, 
    content: string
  ): Promise<boolean> => {
    if (!user) return false;

    const tempId = `temp-${Date.now()}`;
    const tempMessage: MessageWithStatus = {
      id: '',
      tempId,
      session_id: sessionId,
      bot_id: botId,
      user_id: user.id,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
      status: 'sending'
    };

    // Add temporary message
    addMessage(sessionId, tempMessage);

    try {
      // Send to backend
      const response = await chatService.sendMessage(botId, {
        message: content,
        session_id: sessionId
      });

      // Update temp message
      updateMessage(sessionId, tempId, {
        id: response.metadata?.user_message_id || tempId,
        status: 'sent',
        tempId: undefined
      });

      // Add assistant response
      const assistantMessage: MessageWithStatus = {
        id: response.metadata?.assistant_message_id || `assistant-${Date.now()}`,
        session_id: response.session_id,
        bot_id: botId,
        user_id: user.id,
        role: 'assistant',
        content: response.message,
        message_metadata: {
          ...response.metadata,
          chunks_used: response.chunks_used,
          processing_time: response.processing_time
        },
        created_at: new Date().toISOString(),
        status: 'sent'
      };

      addMessage(sessionId, assistantMessage);
      return true;

    } catch (error) {
      // Update temp message to show error
      updateMessage(sessionId, tempId, { status: 'error' });
      
      // Add error message
      const errorMessage: MessageWithStatus = {
        id: `error-${Date.now()}`,
        session_id: sessionId,
        bot_id: botId,
        user_id: 'system',
        role: 'system',
        content: 'Failed to send message. Please try again.',
        created_at: new Date().toISOString(),
        status: 'sent'
      };

      addMessage(sessionId, errorMessage);
      return false;
    }
  }, [user, addMessage, updateMessage]);

  // Send typing indicator
  const sendTypingIndicator = useCallback((isTyping: boolean) => {
    chatWebSocketService.sendTypingIndicator(isTyping);
  }, []);

  // Initialize chat when bot changes
  useEffect(() => {
    const token = authService.getAccessToken();
    if (bot && user && token) {
      const cleanup = initializeChat(bot);
      return () => {
        cleanup?.then(cleanupFn => cleanupFn?.());
      };
    }
  }, [bot?.id, user?.id, initializeChat]);

  return {
    // State
    sessions,
    currentSessionId,
    currentBotId,
    uiState,
    currentMessages: getCurrentMessages(),
    currentSession: getCurrentSession(),
    
    // Actions
    createSession,
    loadSessionMessages,
    sendMessage,
    sendTypingIndicator,
    setCurrentSession,
    
    // Utilities
    isConnected: chatWebSocketService.isConnected(),
    isInitialized: isInitialized.current
  };
};