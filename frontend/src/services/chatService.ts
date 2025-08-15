/**
 * Chat service for handling chat operations with backend API
 */
import { apiClient } from './api';
import {
  ConversationSession,
  ConversationSessionCreate,
  Message,
  MessageCreate,
  ChatRequest,
  ChatResponse,
  ConversationSearchResult,
  ConversationAnalytics,
  ConversationExport,
  ChatError
} from '../types/chat';

/**
 * Parse API error into a structured ChatError
 */
function parseApiError(error: any): ChatError {
  const response = error.response;
  const status = response?.status;
  const data = response?.data;
  const detail = data?.detail || error.message || 'Unknown error occurred';

  // Handle rate limit errors
  if (status === 429 || detail.includes('rate limit')) {
    const isOpenRouter = detail.includes('OpenRouter');
    return {
      type: 'rate_limit',
      message: isOpenRouter 
        ? 'OpenRouter API rate limit exceeded. Please wait before sending another message.'
        : 'Rate limit exceeded. Please wait before trying again.',
      provider: isOpenRouter ? 'openrouter' : undefined,
      retryable: true,
      retryAfter: isOpenRouter ? 30 : 10 // OpenRouter typically needs longer waits
    };
  }

  // Handle API key errors
  if (status === 401 || detail.includes('API key') || detail.includes('authentication')) {
    return {
      type: 'api_error',
      message: 'API authentication failed. Please check your API keys in bot settings.',
      retryable: false
    };
  }

  // Handle validation errors
  if (status === 400 || status === 422) {
    return {
      type: 'validation_error',
      message: detail.includes('validation') ? detail : 'Invalid request. Please check your input.',
      retryable: false
    };
  }

  // Handle network errors
  if (!response || error.code === 'NETWORK_ERROR' || error.code === 'ECONNABORTED') {
    return {
      type: 'network_error',
      message: 'Network error. Please check your connection and try again.',
      retryable: true,
      retryAfter: 5
    };
  }

  // Handle server errors
  if (status >= 500) {
    return {
      type: 'api_error',
      message: 'Server error. Please try again in a moment.',
      retryable: true,
      retryAfter: 10
    };
  }

  // Default unknown error
  return {
    type: 'unknown',
    message: detail || 'An unexpected error occurred. Please try again.',
    retryable: true,
    retryAfter: 5
  };
}

export class ChatService {
  /**
   * Create a new conversation session
   */
  async createSession(sessionData: ConversationSessionCreate): Promise<ConversationSession> {
    const response = await apiClient.post('/conversations/sessions', sessionData);
    return response.data;
  }

  /**
   * Create a session for a specific bot
   */
  async createBotSession(botId: string, title?: string): Promise<ConversationSession> {
    const response = await apiClient.post(`/conversations/bots/${botId}/sessions`, {
      title: title || 'New Conversation'
    });
    return response.data;
  }

  /**
   * Get list of conversation sessions
   */
  async getSessions(
    botId?: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<ConversationSession[]> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString()
    });
    
    if (botId) {
      params.append('bot_id', botId);
    }

    const response = await apiClient.get(`/conversations/sessions?${params}`);
    return response.data;
  }

  /**
   * Get a specific conversation session
   */
  async getSession(sessionId: string): Promise<ConversationSession> {
    const response = await apiClient.get(`/conversations/sessions/${sessionId}`);
    return response.data;
  }

  /**
   * Update a conversation session
   */
  async updateSession(
    sessionId: string,
    title?: string,
    isShared?: boolean
  ): Promise<ConversationSession> {
    const updateData: any = {};
    if (title !== undefined) updateData.title = title;
    if (isShared !== undefined) updateData.is_shared = isShared;

    const response = await apiClient.put(`/conversations/sessions/${sessionId}`, updateData);
    return response.data;
  }

  /**
   * Delete a conversation session
   */
  async deleteSession(sessionId: string): Promise<void> {
    await apiClient.delete(`/conversations/sessions/${sessionId}`);
  } 
 /**
   * Send a chat message to a bot
   */
  async sendMessage(botId: string, chatRequest: ChatRequest): Promise<ChatResponse> {
    try {
      const response = await apiClient.post(`/conversations/bots/${botId}/chat`, chatRequest);
      return response.data;
    } catch (error) {
      const chatError = parseApiError(error);
      // Attach the parsed error to the original error for upstream handling
      (error as any).chatError = chatError;
      throw error;
    }
  }

  /**
   * Add a message to a session
   */
  async addMessage(messageData: MessageCreate): Promise<Message> {
    const response = await apiClient.post('/conversations/messages', messageData);
    return response.data;
  }

  /**
   * Get messages from a session
   */
  async getSessionMessages(
    sessionId: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<Message[]> {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString()
    });

    const response = await apiClient.get(`/conversations/sessions/${sessionId}/messages?${params}`);
    return response.data;
  }

  /**
   * Search conversations
   */
  async searchConversations(
    query: string,
    botId?: string,
    limit: number = 50,
    offset: number = 0
  ): Promise<{ query: string; results: ConversationSearchResult[]; total: number }> {
    const params = new URLSearchParams({
      q: query,
      limit: limit.toString(),
      offset: offset.toString()
    });

    if (botId) {
      params.append('bot_id', botId);
    }

    const response = await apiClient.get(`/conversations/search?${params}`);
    return response.data;
  }

  /**
   * Export conversations
   */
  async exportConversations(
    botId?: string,
    sessionId?: string,
    format: string = 'json'
  ): Promise<ConversationExport> {
    const params = new URLSearchParams({
      format_type: format
    });

    if (botId) params.append('bot_id', botId);
    if (sessionId) params.append('session_id', sessionId);

    const response = await apiClient.get(`/conversations/export?${params}`);
    return response.data;
  }

  /**
   * Get conversation analytics
   */
  async getAnalytics(botId?: string): Promise<ConversationAnalytics> {
    const params = botId ? `?bot_id=${botId}` : '';
    const response = await apiClient.get(`/conversations/analytics${params}`);
    return response.data;
  }

  /**
   * Get available models for all providers
   */
  async getAvailableModels(): Promise<Record<string, string[]>> {
    const response = await apiClient.get('/bots/models/available');
    return response.data;
  }

  /**
   * Get available models for a specific provider
   */
  async getProviderModels(provider: string): Promise<string[]> {
    const response = await apiClient.get(`/bots/models/${provider}`);
    return response.data;
  }

  /**
   * Get supported providers
   */
  async getSupportedProviders(): Promise<string[]> {
    const response = await apiClient.get('/bots/providers');
    return response.data;
  }

  /**
   * Get available embedding models for all providers
   */
  async getAvailableEmbeddingModels(): Promise<Record<string, string[]>> {
    const response = await apiClient.get('/bots/embeddings/available');
    return response.data;
  }

  /**
   * Get available embedding models for a specific provider
   */
  async getProviderEmbeddingModels(provider: string): Promise<string[]> {
    const response = await apiClient.get(`/bots/embeddings/${provider}`);
    return response.data;
  }

  /**
   * Get supported embedding providers
   */
  async getSupportedEmbeddingProviders(): Promise<string[]> {
    const response = await apiClient.get('/bots/embeddings/providers');
    return response.data;
  }
}

// Export singleton instance
export const chatService = new ChatService();