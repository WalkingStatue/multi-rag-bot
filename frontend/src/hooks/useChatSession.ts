/**
 * Custom hook for managing chat sessions with WebSocket integration
 */
import { useEffect, useCallback, useRef } from 'react';
import { useChatStore } from '../stores/chatStore';
import { chatService } from '../services/chatService';
import { chatWebSocketService } from '../services/chatWebSocketService';
import { authService } from '../services/authService';
import { useAuth } from './useAuth';
import { ConversationSession } from '../types/chat';

interface UseChatSessionOptions {
  botId: string;
  autoSelectFirst?: boolean;
  preloadMessages?: boolean;
}

interface UseChatSessionReturn {
  sessions: ConversationSession[];
  currentSession: ConversationSession | null;
  isLoading: boolean;
  error: string | null;
  selectSession: (sessionId: string) => Promise<void>;
  createSession: () => Promise<ConversationSession | null>;
  refreshSessions: () => Promise<void>;
}

export const useChatSession = ({
  botId,
  autoSelectFirst = true,
  preloadMessages = true
}: UseChatSessionOptions): UseChatSessionReturn => {
  const { user } = useAuth();
  const {
    sessions,
    currentSessionId,
    currentBotId,
    uiState,
    lastError,
    setSessions,
    setCurrentSession,
    setMessages,
    setLoading,
    setConnectionStatus,
    addSession,
    getCurrentSession,
    setError,
    clearError
  } = useChatStore();

  const isInitialized = useRef(false);
  const loadingSessionId = useRef<string | null>(null);
  const errorState = useRef<string | null>(null);

  // Initialize sessions for the bot
  const initializeSessions = useCallback(async () => {
    if (!botId || !user) return;

    // Prevent duplicate initialization for the same bot
    if (isInitialized.current && currentBotId === botId) {
      return;
    }

    const token = authService.getAccessToken();
    if (!token) return;

    try {
      setLoading(true);
      errorState.current = null;
      clearError();

      // Load sessions
      const botSessions = await chatService.getSessions(botId);
      setSessions(botSessions);

      // Connect to WebSocket only if not already connected to this bot
      if (!chatWebSocketService.isConnected() || chatWebSocketService.getCurrentBotId() !== botId) {
        try {
          await chatWebSocketService.connectToBot(botId, token);
        } catch (wsError) {
          // Don't fail the entire initialization if WebSocket fails
          // The system will fall back to REST API calls
          setConnectionStatus({
            status: 'error',
            error: 'WebSocket connection failed, using REST API'
          });
        }
      }

      // Auto-select first session if requested and none selected
      if (autoSelectFirst && botSessions.length > 0 && !currentSessionId) {
        await selectSessionInternal(botSessions[0].id, false);
      }

      isInitialized.current = true;

    } catch (error: any) {
      
      // Handle specific error types
      const chatError = error.chatError;
      if (chatError?.type === 'rate_limit') {
        errorState.current = chatError.message;
        setError(chatError.message);
      } else {
        errorState.current = 'Failed to load chat sessions';
        setError('Failed to load chat sessions');
      }
      
      setConnectionStatus({
        status: 'error',
        error: errorState.current || undefined
      });
    } finally {
      setLoading(false);
    }
  }, [botId, user, autoSelectFirst, currentSessionId, currentBotId]);

  // Internal session selection with message loading
  const selectSessionInternal = useCallback(async (sessionId: string, setLoading = true) => {
    if (loadingSessionId.current === sessionId) {
      return;
    }

    loadingSessionId.current = sessionId;

    try {
      if (setLoading) {
        useChatStore.getState().setLoading(true);
      }

      setCurrentSession(sessionId);

      // Sync WebSocket to new session
      chatWebSocketService.syncToSession(sessionId);

      // Load messages if preloading is enabled
      if (preloadMessages) {
        try {
          const messages = await chatService.getSessionMessages(sessionId);
          setMessages(sessionId, messages.map(msg => ({ ...msg, status: 'sent' as const })));
        } catch (messageError) {
          // Don't fail the entire session selection if messages fail to load
          setMessages(sessionId, []);
        }
      }

    } catch (error) {
      errorState.current = 'Failed to load session';
    } finally {
      loadingSessionId.current = null;
      if (setLoading) {
        useChatStore.getState().setLoading(false);
      }
    }
  }, [preloadMessages]);

  // Public session selection method
  const selectSession = useCallback(async (sessionId: string) => {
    await selectSessionInternal(sessionId, true);
  }, [selectSessionInternal]);

  // Create new session
  const createSession = useCallback(async (): Promise<ConversationSession | null> => {
    if (!botId) return null;

    try {
      setLoading(true);
      const newSession = await chatService.createBotSession(botId);
      addSession(newSession);
      await selectSessionInternal(newSession.id, false);
      return newSession;
    } catch (error: any) {
      
      const chatError = error.chatError;
      if (chatError?.type === 'rate_limit') {
        errorState.current = chatError.message;
        setError(chatError.message);
      } else {
        errorState.current = 'Failed to create new session';
        setError('Failed to create new session');
      }
      return null;
    } finally {
      setLoading(false);
    }
  }, [botId, addSession, selectSessionInternal]);

  // Refresh sessions
  const refreshSessions = useCallback(async () => {
    if (!botId) return;

    try {
      const botSessions = await chatService.getSessions(botId);
      setSessions(botSessions);
    } catch (error: any) {
      
      const chatError = error.chatError;
      if (chatError?.type === 'rate_limit') {
        errorState.current = chatError.message;
        setError(chatError.message);
      } else {
        errorState.current = 'Failed to refresh sessions';
        setError('Failed to refresh sessions');
      }
    }
  }, [botId, setSessions]);

  // Initialize when bot changes
  useEffect(() => {
    if (currentBotId !== botId) {
      isInitialized.current = false;
      errorState.current = null;
      loadingSessionId.current = null;
    }

    if (botId && user) {
      initializeSessions();
    }

    return () => {
      // Cleanup when component unmounts or bot changes
      if (currentBotId !== botId) {
        loadingSessionId.current = null;
      }
    };
  }, [botId, user, initializeSessions]);

  // Handle session changes from other sources (e.g., WebSocket updates)
  useEffect(() => {
    if (currentSessionId && currentSessionId !== chatWebSocketService.getCurrentSessionId()) {
      chatWebSocketService.syncToSession(currentSessionId);
    }
  }, [currentSessionId]);

  return {
    sessions: sessions.filter(session => session.bot_id === botId),
    currentSession: getCurrentSession(),
    isLoading: uiState.isLoading,
    error: lastError || errorState.current,
    selectSession,
    createSession,
    refreshSessions
  };
};