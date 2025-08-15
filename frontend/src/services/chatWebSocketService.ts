/**
 * WebSocket service specifically for chat functionality
 */
import { ChatMessage, TypingIndicator, ConnectionStatus } from '../types/chat';
import { connectionHealthMonitor } from '../utils/connectionHealth';

export class ChatWebSocketService {
  private socket: WebSocket | null = null;
  private currentBotId: string | null = null;
  private currentSessionId: string | null = null;
  private typingTimeout: number | null = null;
  private pingInterval: number | null = null;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private token: string | null = null;
  private connectionTimeout: number | null = null;
  private lastConnectionAttempt = 0;
  private connectionDebounceMs = 500; // Reduced debounce time
  private isConnecting = false;
  private connectionPromise: Promise<void> | null = null;
  private sessionSyncQueue: Array<{ sessionId: string; callback: () => void }> = [];

  /**
   * Connect to chat WebSocket for a specific bot
   */
  async connectToBot(botId: string, token: string, sessionId?: string): Promise<void> {
    // Return existing connection promise if already connecting
    if (this.connectionPromise && this.isConnecting) {
      return this.connectionPromise;
    }

    // If already connected to the same bot, just sync session
    if (this.socket?.readyState === WebSocket.OPEN && this.currentBotId === botId) {
      if (sessionId && sessionId !== this.currentSessionId) {
        this.syncToSession(sessionId);
      }
      return Promise.resolve();
    }

    // Debounce connection attempts
    const now = Date.now();
    if (now - this.lastConnectionAttempt < this.connectionDebounceMs && this.currentBotId === botId) {
      return Promise.resolve();
    }
    this.lastConnectionAttempt = now;

    this.connectionPromise = this.performConnection(botId, token, sessionId);
    return this.connectionPromise;
  }

  /**
   * Perform the actual WebSocket connection
   */
  private async performConnection(botId: string, token: string, sessionId?: string): Promise<void> {
    return new Promise<void>(async (resolve, reject) => {
      this.isConnecting = true;

      try {
        // Disconnect existing connection if any
        this.disconnect();

        this.currentBotId = botId;
        this.currentSessionId = sessionId || null;
        this.token = token;
        
        const wsUrl = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8000';
        const chatUrl = `${wsUrl}/api/ws/chat/${botId}?token=${encodeURIComponent(token)}`;
        

        
        // Check if backend is reachable before attempting WebSocket connection
        await this.checkBackendHealth();
        
        this.socket = new WebSocket(chatUrl);
        this.setupEventHandlers(resolve, reject);
        
        // Set connection timeout
        this.connectionTimeout = setTimeout(() => {
          if (this.socket && this.socket.readyState === WebSocket.CONNECTING) {
            this.socket.close();
            this.notifyListeners('connection', { status: 'error', error: 'Connection timeout' });
            reject(new Error('Connection timeout'));
          }
        }, 10000); // 10 second timeout
        
      } catch (error) {
        this.notifyListeners('connection', { status: 'error', error: 'Failed to create connection' });
        reject(error);
      } finally {
        this.isConnecting = false;
        this.connectionPromise = null;
      }
    });
  }

  /**
   * Check backend health before attempting WebSocket connection
   */
  private async checkBackendHealth(): Promise<void> {
    try {
      const apiUrl = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';
      const healthResponse = await fetch(`${apiUrl}/health`, {
        method: 'GET',
        signal: AbortSignal.timeout(5000)
      });
      
      if (!healthResponse.ok) {
        throw new Error(`Backend not available: ${healthResponse.status}`);
      }
    } catch (error) {
      // Backend health check failed, attempting WebSocket connection anyway
    }
  }

  /**
   * Sync WebSocket to a specific session
   */
  syncToSession(sessionId: string): void {
    this.currentSessionId = sessionId;
    
    // If connected, send session sync message
    if (this.isConnected()) {
      this.send({
        type: 'session_sync',
        data: { session_id: sessionId }
      });
    } else {
      // Queue session sync for when connection is established
      this.sessionSyncQueue.push({
        sessionId,
        callback: () => {
          this.send({
            type: 'session_sync',
            data: { session_id: sessionId }
          });
        }
      });
    }
  }

  /**
   * Disconnect from current bot chat
   */
  disconnect(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    
    if (this.typingTimeout) {
      clearTimeout(this.typingTimeout);
      this.typingTimeout = null;
    }
    
    if (this.connectionTimeout) {
      clearTimeout(this.connectionTimeout);
      this.connectionTimeout = null;
    }
    
    if (this.socket) {
      this.socket.close(1000, 'Client disconnect');
      this.socket = null;
    }
    
    // Clear state but preserve listeners for reconnection
    this.currentBotId = null;
    this.currentSessionId = null;
    this.reconnectAttempts = 0;
    this.token = null;
    this.isConnecting = false;
    this.connectionPromise = null;
    this.sessionSyncQueue = [];
    this.lastConnectionAttempt = 0; // Reset debounce
  }

  /**
   * Clean disconnect that also clears listeners
   */
  cleanDisconnect(): void {
    this.disconnect();
    this.listeners.clear();
  }

  /**
   * Subscribe to chat messages
   */
  onChatMessage(callback: (message: ChatMessage) => void): () => void {
    return this.subscribe('chat_message', callback);
  }

  /**
   * Subscribe to typing indicators
   */
  onTypingIndicator(callback: (indicator: TypingIndicator) => void): () => void {
    return this.subscribe('typing_indicator', callback);
  }

  /**
   * Subscribe to connection status changes
   */
  onConnectionStatus(callback: (status: ConnectionStatus) => void): () => void {
    return this.subscribe('connection', callback);
  }

  /**
   * Subscribe to specific event types
   */
  private subscribe(eventType: string, callback: (data: any) => void): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    
    this.listeners.get(eventType)!.add(callback);

    // Return unsubscribe function
    return () => {
      const eventListeners = this.listeners.get(eventType);
      if (eventListeners) {
        eventListeners.delete(callback);
        if (eventListeners.size === 0) {
          this.listeners.delete(eventType);
        }
      }
    };
  }

  /**
   * Send typing indicator
   */
  sendTypingIndicator(isTyping: boolean): void {
    if (!this.currentBotId || !this.isConnected()) return;

    this.send({
      type: 'typing',
      data: { is_typing: isTyping }
    });

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
   * Send a message through WebSocket
   */
  private send(data: any): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    }
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN || false;
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
   * Setup event handlers for WebSocket
   */
  private setupEventHandlers(resolve?: () => void, reject?: (error: Error) => void): void {
    if (!this.socket) return;

    this.socket.onopen = () => {
      // Clear connection timeout
      if (this.connectionTimeout) {
        clearTimeout(this.connectionTimeout);
        this.connectionTimeout = null;
      }
      
      this.reconnectAttempts = 0;
      this.notifyListeners('connection', { status: 'connected' });
      
      // Process queued session syncs
      this.processSessionSyncQueue();
      
      // Start ping with delay to let connection stabilize
      this.startPingInterval();
      
      // Resolve the connection promise
      if (resolve) {
        resolve();
      }
    };

    this.socket.onclose = (event) => {
      this.notifyListeners('connection', { 
        status: 'disconnected', 
        code: event.code, 
        reason: event.reason 
      });
      
      if (this.pingInterval) {
        clearInterval(this.pingInterval);
        this.pingInterval = null;
      }
      
      // Handle different close codes appropriately
      if (event.code === 1000) {
        // Normal closure - don't reconnect
      } else if (event.code === 4001 || event.code === 4003) {
        // Authentication errors - don't reconnect
        this.notifyListeners('connection', { 
          status: 'error', 
          error: 'Authentication failed' 
        });
      } else if (event.code === 1006) {
        // Abnormal closure - could be network or server issue
        setTimeout(() => {
          if (this.token && this.currentBotId && this.reconnectAttempts < this.maxReconnectAttempts) {
            this.handleReconnect();
          }
        }, 2000); // Wait 2 seconds before reconnecting
      } else {
        // Other errors - attempt reconnection
        this.handleReconnect();
      }
    };

    this.socket.onerror = () => {
      this.notifyListeners('connection', { status: 'error', error: 'Connection error' });
      
      // Reject the connection promise
      if (reject) {
        reject(new Error('WebSocket connection error'));
      }
    };

    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        // Error parsing chat WebSocket message
      }
    };
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(message: any): void {
    const { type } = message;

    switch (type) {
      case 'connection_established':
        break;
      
      case 'chat_message':
        this.notifyListeners('chat_message', message);
        break;
      
      case 'chat_response':
        // Handle bot responses - treat them as chat messages
        this.notifyListeners('chat_message', message);
        break;
      
      case 'typing_indicator':
        this.notifyListeners('typing_indicator', message);
        break;
      
      case 'pong':
        // Handle pong response for ping/pong health check
        break;
      
      case 'error':
        break;
      
      default:
    }
  }

  /**
   * Notify all listeners for a specific event type
   */
  private notifyListeners(eventType: string, data: any): void {
    const eventListeners = this.listeners.get(eventType);
    if (eventListeners) {
      eventListeners.forEach(callback => {
        try {
          callback(data);
        } catch (error) {
          // Error in chat WebSocket listener
        }
      });
    }
  }

  /**
   * Handle reconnection logic
   */
  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts || !this.token || !this.currentBotId) {
      this.notifyListeners('connection', { 
        status: 'failed', 
        message: 'Failed to reconnect after maximum attempts' 
      });
      return;
    }

    // Check network health before attempting reconnection
    if (!connectionHealthMonitor.isHealthy()) {
      setTimeout(() => this.handleReconnect(), 10000);
      return;
    }

    this.reconnectAttempts++;
    // Increase delay more aggressively to avoid rate limiting
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000);
    
    setTimeout(async () => {
      if (this.token && this.currentBotId && connectionHealthMonitor.isHealthy()) {
        try {
          await this.connectToBot(this.currentBotId, this.token, this.currentSessionId || undefined);
        } catch (error) {
          // Continue with normal reconnection logic
          if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.handleReconnect();
          }
        }
      }
    }, delay);
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
   * Start ping interval for connection health
   */
  private startPingInterval(): void {
    // Wait a bit before starting ping to let connection stabilize
    setTimeout(() => {
      this.pingInterval = setInterval(() => {
        if (this.isConnected()) {
          this.send({
            type: 'ping',
            timestamp: new Date().toISOString()
          });
        }
      }, 30000); // Ping every 30 seconds
    }, 5000); // Wait 5 seconds before starting ping
  }
}

// Export singleton instance
export const chatWebSocketService = new ChatWebSocketService();