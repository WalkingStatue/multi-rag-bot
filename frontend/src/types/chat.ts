/**
 * Chat and conversation-related TypeScript types for frontend
 */

export interface ConversationSession {
  id: string;
  bot_id: string;
  user_id: string;
  title?: string;
  is_shared: boolean;
  created_at: string;
  updated_at: string;
}

export interface ConversationSessionCreate {
  bot_id: string;
  title?: string;
}

export interface Message {
  id: string;
  session_id: string;
  bot_id: string;
  user_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  message_metadata?: Record<string, any>;
  created_at: string;
}

export interface MessageCreate {
  session_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  message_metadata?: Record<string, any>;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
}

export interface ChatResponse {
  message: string;
  session_id: string;
  chunks_used: string[];
  processing_time: number;
  metadata?: Record<string, any>;
}

export interface ConversationSearchResult {
  session_id: string;
  bot_id: string;
  bot_name: string;
  title?: string;
  message_content: string;
  message_role: string;
  created_at: string;
  relevance_score?: number;
}

export interface ConversationExport {
  sessions: ConversationSession[];
  messages: Message[];
  export_date: string;
  format: string;
}

export interface ConversationAnalytics {
  total_sessions: number;
  total_messages: number;
  average_session_length: number;
  most_active_bots: Array<{
    bot_id: string;
    bot_name: string;
    message_count: number;
  }>;
  activity_by_day: Array<{
    date: string;
    sessions: number;
    messages: number;
  }>;
}
// WebSocket message types
export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp?: string;
}

export interface ChatMessage extends WebSocketMessage {
  type: 'chat_message';
  bot_id: string;
  data: {
    message_id: string;
    session_id: string;
    user_id: string;
    username: string;
    content: string;
    role: 'user' | 'assistant';
    timestamp: string;
    metadata?: Record<string, any>;
  };
}

export interface TypingIndicator extends WebSocketMessage {
  type: 'typing_indicator';
  bot_id: string;
  data: {
    user_id: string;
    username: string;
    is_typing: boolean;
  };
}

export interface ConnectionStatus {
  status: 'connected' | 'disconnected' | 'error' | 'failed';
  reason?: string;
  error?: string;
  message?: string;
}

// UI state types
export interface ChatUIState {
  isLoading: boolean;
  isTyping: boolean;
  typingUsers: string[];
  connectionStatus: ConnectionStatus;
  selectedSessionId?: string;
  searchQuery: string;
  searchResults: ConversationSearchResult[];
}

export interface MessageWithStatus extends Message {
  status?: 'sending' | 'sent' | 'error';
  tempId?: string;
  error?: ChatError;
}

export interface ChatError {
  type: 'rate_limit' | 'api_error' | 'network_error' | 'validation_error' | 'unknown';
  message: string;
  provider?: string;
  retryable?: boolean;
  retryAfter?: number; // seconds
}