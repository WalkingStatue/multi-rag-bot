/**
 * Chat WebSocket adapter using the core WebSocket service
 * This replaces the standalone chatWebSocketService
 */
import { WebSocketCore, WebSocketState } from '../core/WebSocketCore';
import { ChatMessage, TypingIndicator, ConnectionStatus } from '../../types/chat';
import { config } from '../../config/environment';

export class ChatWebSocketAdapter {
  private core: WebSocketCore | null = null;
  private currentBotId: string | null = null;
  private currentSessionId: string | null = null;
  private typingTimeout: number | null = null;
  private sessionSyncQueue: Array<{ sessionId: string; callback: () => void }> = [];
  private coreConfig = {
    enableLogging: config.features.enableDebugMode,
    reconnectInterval: 2000,
    maxReconnectAttempts: 5,
    heartbeatInterval: 30000,
    connectionTimeout: 10000,
    enableHeartbeat: true,
    enableDebounce: true,
    debounceMs: 500,
  };

  constructor() {
    // Core will be created on-demand when connecting to a bot
  }

  /**
   * Setup core WebSocket event handlers
   */
  private setupCoreHandlers(): void {
    if (!this.core) return;
    
    this.core.subscribe('connection_established', () => {
      // Process queued session syncs when connection is established
      this.processSessionSyncQueue();
    });
  }

  /**
   * Connect to chat WebSocket for a specific bot
   */
  async connectToBot(botId: string, token: string, sessionId?: string): Promise<void> {
    // If already connected to the same bot, just sync session
    if (this.core && this.core.isConnected() && this.currentBotId === botId) {
      if (sessionId && sessionId !== this.currentSessionId) {
        this.syncToSession(sessionId);
      }
      return Promise.resolve();
    }

    try {
      // Disconnect existing core if we're switching bots
      if (this.core && this.currentBotId !== botId) {
        this.core.destroy();
        this.core = null;
      }

      this.currentBotId = botId;
      this.currentSessionId = sessionId || null;

      // Create a new core instance with the bot-specific endpoint
      if (!this.core) {
        this.core = new WebSocketCore({
          endpoint: `/api/ws/chat/${botId}`,
          ...this.coreConfig
        });
        this.setupCoreHandlers();
      }

      await this.core.connect(token, sessionId ? { session_id: sessionId } : {});
      
    } catch (error) {
      this.currentBotId = null;
      this.currentSessionId = null;
      throw error;
    }
  }

  /**
   * Sync WebSocket to a specific session
   */
  syncToSession(sessionId: string): void {
    this.currentSessionId = sessionId;
    
    // If connected, send session sync message
    if (this.core && this.core.isConnected()) {
      this.core.send('session_sync', { session_id: sessionId });
    } else {
      // Queue session sync for when connection is established
      this.sessionSyncQueue.push({
        sessionId,
        callback: () => {
          if (this.core) {
            this.core.send('session_sync', { session_id: sessionId });
          }
        }
      });
    }
  }

  /**
   * Disconnect from current bot chat
   */
  disconnect(): void {
    if (this.typingTimeout) {
      clearTimeout(this.typingTimeout);
      this.typingTimeout = null;
    }

    if (this.core) {
      this.core.disconnect();
    }
    
    // Clear state
    this.currentBotId = null;
    this.currentSessionId = null;
    this.sessionSyncQueue = [];
  }

  /**
   * Clean disconnect that also clears listeners
   */
  cleanDisconnect(): void {
    this.disconnect();
    // Note: We don't clear core subscribers as they might be used by other components
  }

  /**
   * Subscribe to chat messages
   */
  onChatMessage(callback: (message: ChatMessage) => void): () => void {
    if (!this.core) {
      return () => {}; // Return no-op unsubscriber if no core
    }
    return this.core.subscribe('chat_message', callback);
  }

  /**
   * Subscribe to chat responses (bot messages)
   */
  onChatResponse(callback: (message: ChatMessage) => void): () => void {
    if (!this.core) {
      return () => {}; // Return no-op unsubscriber if no core
    }
    return this.core.subscribe('chat_response', callback);
  }

  /**
   * Subscribe to typing indicators
   */
  onTypingIndicator(callback: (indicator: TypingIndicator) => void): () => void {
    if (!this.core) {
      return () => {}; // Return no-op unsubscriber if no core
    }
    return this.core.subscribe('typing_indicator', callback);
  }

  /**
   * Subscribe to connection status changes
   */
  onConnectionStatus(callback: (status: ConnectionStatus) => void): () => void {
    if (!this.core) {
      return () => {}; // Return no-op unsubscriber if no core
    }
    return this.core.subscribe('connection', (data) => {
      // Map WebSocket core connection events to chat connection status format
      let status: ConnectionStatus;
      
      if (!this.core) return; // Safety check
      
      const state = this.core.getState();
      switch (state) {
        case WebSocketState.CONNECTED:
          status = { status: 'connected' };
          break;
        case WebSocketState.CONNECTING:
          status = { status: 'connecting' };
          break;
        case WebSocketState.RECONNECTING:
          status = { status: 'reconnecting' };
          break;
        case WebSocketState.ERROR:
          status = { status: 'error', error: data.error || 'Connection error' };
          break;
        case WebSocketState.DISCONNECTED:
        case WebSocketState.CLOSED:
        default:
          status = { 
            status: 'disconnected', 
            code: data.code, 
            reason: data.reason 
          };
          break;
      }
      
      callback(status);
    });
  }

  /**
   * Send typing indicator
   */
  sendTypingIndicator(isTyping: boolean): void {
    if (!this.currentBotId || !this.core || !this.core.isConnected()) return;

    this.core.send('typing', { is_typing: isTyping });

    // Auto-stop typing after 3 seconds
    if (isTyping) {
      if (this.typingTimeout) {
        clearTimeout(this.typingTimeout);
      }
      
      this.typingTimeout = setTimeout(() => {
        this.sendTypingIndicator(false);
      }, 3000);
    } else if (this.typingTimeout) {
      clearTimeout(this.typingTimeout);
      this.typingTimeout = null;
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.core ? this.core.isConnected() : false;
  }

  /**
   * Get current bot ID
   */
  getCurrentBotId(): string | null {
    return this.currentBotId;
  }

  /**
   * Get current session ID
   */
  getCurrentSessionId(): string | null {
    return this.currentSessionId;
  }

  /**
   * Get connection state
   */
  getState(): WebSocketState {
    return this.core ? this.core.getState() : WebSocketState.DISCONNECTED;
  }

  /**
   * Get connection statistics
   */
  getStats() {
    const coreStats = this.core ? this.core.getStats() : {
      state: WebSocketState.DISCONNECTED,
      reconnectAttempts: 0,
      queuedMessages: 0,
      subscribers: [],
      lastPingTime: 0,
      isConnected: false,
      endpoint: 'none'
    };
    
    return {
      ...coreStats,
      botId: this.currentBotId,
      sessionId: this.currentSessionId,
      queuedSyncs: this.sessionSyncQueue.length,
    };
  }

  /**
   * Process queued session sync operations
   */
  private processSessionSyncQueue(): void {
    while (this.sessionSyncQueue.length > 0) {
      const syncOp = this.sessionSyncQueue.shift();
      if (syncOp) {
        syncOp.callback();
      }
    }
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    this.disconnect();
    if (this.core) {
      this.core.destroy();
    }
  }
}

// Export singleton instance
export const chatWebSocketAdapter = new ChatWebSocketAdapter();
