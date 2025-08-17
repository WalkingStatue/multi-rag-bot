/**
 * Chat state management using Zustand
 */
import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import {
  ConversationSession,

  MessageWithStatus,
  ChatUIState,
  ConversationSearchResult,
  ConnectionStatus
} from '../types/chat';

interface ChatStore {
  // State
  sessions: ConversationSession[];
  messages: Record<string, MessageWithStatus[]>; // sessionId -> messages
  currentSessionId: string | null;
  currentBotId: string | null;
  uiState: ChatUIState;
  lastError: string | null;
  highlightedMessageId: string | null;

  // Actions
  setSessions: (sessions: ConversationSession[]) => void;
  addSession: (session: ConversationSession) => void;
  updateSession: (sessionId: string, updates: Partial<ConversationSession>) => void;
  removeSession: (sessionId: string) => void;
  
  setMessages: (sessionId: string, messages: MessageWithStatus[]) => void;
  addMessage: (sessionId: string, message: MessageWithStatus) => void;
  updateMessage: (sessionId: string, messageId: string, updates: Partial<MessageWithStatus>) => void;
  removeMessage: (sessionId: string, messageId: string) => void;
  
  setCurrentSession: (sessionId: string | null) => void;
  setCurrentBot: (botId: string | null) => void;
  
  setLoading: (loading: boolean) => void;
  setTyping: (typing: boolean) => void;
  setTypingUsers: (users: string[]) => void;
  addTypingUser: (user: string) => void;
  removeTypingUser: (user: string) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  setSearchQuery: (query: string) => void;
  setSearchResults: (results: ConversationSearchResult[]) => void;
  setError: (error: string | null) => void;
  clearError: () => void;
  setHighlightedMessage: (messageId: string | null) => void;
  clearHighlightedMessage: () => void;
  
  // Computed
  getCurrentSession: () => ConversationSession | null;
  getCurrentMessages: () => MessageWithStatus[];
  getSessionMessages: (sessionId: string) => MessageWithStatus[];
}

export const useChatStore = create<ChatStore>()(
  devtools(
    (set, get) => ({
      // Initial state
      sessions: [],
      messages: {},
      currentSessionId: null,
      currentBotId: null,
      lastError: null,
      highlightedMessageId: null,
      uiState: {
        isLoading: false,
        isTyping: false,
        typingUsers: [],
        connectionStatus: { status: 'disconnected' },
        searchQuery: '',
        searchResults: []
      },

      // Session actions
      setSessions: (sessions) => set({ sessions }),
      
      addSession: (session) => set((state) => ({
        sessions: [session, ...state.sessions]
      })),
      
      updateSession: (sessionId, updates) => set((state) => ({
        sessions: state.sessions.map(session =>
          session.id === sessionId ? { ...session, ...updates } : session
        )
      })),
      
      removeSession: (sessionId) => set((state) => {
        const newMessages = { ...state.messages };
        delete newMessages[sessionId];
        
        return {
          sessions: state.sessions.filter(session => session.id !== sessionId),
          messages: newMessages,
          currentSessionId: state.currentSessionId === sessionId ? null : state.currentSessionId
        };
      }),

      // Message actions
      setMessages: (sessionId, messages) => set((state) => ({
        messages: { ...state.messages, [sessionId]: messages }
      })),
      
      addMessage: (sessionId, message) => set((state) => {
        const sessionMessages = state.messages[sessionId] || [];
        
        // Check if message already exists to prevent duplicates
        const messageExists = sessionMessages.some(msg => {
          // Check by ID first
          if (msg.id && message.id && msg.id === message.id) {
            return true;
          }
          // Check by tempId
          if (msg.tempId && message.tempId && msg.tempId === message.tempId) {
            return true;
          }
          // Check by content and timestamp for messages without IDs (fallback)
          if (!msg.id && !message.id && !msg.tempId && !message.tempId) {
            return msg.content === message.content && 
                   Math.abs(new Date(msg.created_at).getTime() - new Date(message.created_at).getTime()) < 1000;
          }
          return false;
        });
        
        if (messageExists) {
          return state; // Return unchanged state
        }
        
        return {
          messages: {
            ...state.messages,
            [sessionId]: [...sessionMessages, message]
          }
        };
      }),
      
      updateMessage: (sessionId, messageId, updates) => set((state) => {
        const sessionMessages = state.messages[sessionId] || [];
        return {
          messages: {
            ...state.messages,
            [sessionId]: sessionMessages.map(msg =>
              (msg.id === messageId || msg.tempId === messageId) 
                ? { ...msg, ...updates } 
                : msg
            )
          }
        };
      }),
      
      removeMessage: (sessionId, messageId) => set((state) => {
        const sessionMessages = state.messages[sessionId] || [];
        return {
          messages: {
            ...state.messages,
            [sessionId]: sessionMessages.filter(msg => 
              msg.id !== messageId && msg.tempId !== messageId
            )
          }
        };
      }),

      // Current state actions
      setCurrentSession: (sessionId) => set({ currentSessionId: sessionId }),
      setCurrentBot: (botId) => set({ currentBotId: botId }),

      // UI state actions
      setLoading: (loading) => set((state) => ({
        uiState: { ...state.uiState, isLoading: loading }
      })),
      
      setTyping: (typing) => set((state) => ({
        uiState: { ...state.uiState, isTyping: typing }
      })),
      
      setTypingUsers: (users) => set((state) => ({
        uiState: { ...state.uiState, typingUsers: users }
      })),
      
      addTypingUser: (user) => set((state) => ({
        uiState: {
          ...state.uiState,
          typingUsers: state.uiState.typingUsers.includes(user)
            ? state.uiState.typingUsers
            : [...state.uiState.typingUsers, user]
        }
      })),
      
      removeTypingUser: (user) => set((state) => ({
        uiState: {
          ...state.uiState,
          typingUsers: state.uiState.typingUsers.filter(u => u !== user)
        }
      })),
      
      setConnectionStatus: (status) => set((state) => ({
        uiState: { ...state.uiState, connectionStatus: status }
      })),
      
      setSearchQuery: (query) => set((state) => ({
        uiState: { ...state.uiState, searchQuery: query }
      })),
      
      setSearchResults: (results) => set((state) => ({
        uiState: { ...state.uiState, searchResults: results }
      })),

      setError: (error) => set({ lastError: error }),
      clearError: () => set({ lastError: null }),
      
      setHighlightedMessage: (messageId) => set({ highlightedMessageId: messageId }),
      clearHighlightedMessage: () => set({ highlightedMessageId: null }),

      // Computed getters
      getCurrentSession: () => {
        const { sessions, currentSessionId } = get();
        return sessions.find(session => session.id === currentSessionId) || null;
      },
      
      getCurrentMessages: () => {
        const { messages, currentSessionId } = get();
        return currentSessionId ? messages[currentSessionId] || [] : [];
      },
      
      getSessionMessages: (sessionId) => {
        const { messages } = get();
        return messages[sessionId] || [];
      }
    }),
    { name: 'chat-store' }
  )
);