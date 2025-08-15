/**
 * Enhanced WebSocket service with error handling and automatic reconnection
 */
import { log } from '../utils/logger';
import { errorHandler, AppError } from '../utils/errorHandler';
import { config } from '../config/environment';

export enum WebSocketState {
  CONNECTING = 'CONNECTING',
  CONNECTED = 'CONNECTED',
  DISCONNECTED = 'DISCONNECTED',
  RECONNECTING = 'RECONNECTING',
  ERROR = 'ERROR',
  CLOSED = 'CLOSED',
}

export interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: number;
  id?: string;
}

export interface WebSocketConfig {
  url: string;
  protocols?: string[];
  reconnectInterval: number;
  maxReconnectAttempts: number;
  heartbeatInterval: number;
  connectionTimeout: number;
  enableHeartbeat: boolean;
  enableLogging: boolean;
}

export interface WebSocketEventHandlers {
  onOpen?: (event: Event) => void;
  onMessage?: (message: WebSocketMessage) => void;
  onError?: (error: AppError) => void;
  onClose?: (event: CloseEvent) => void;
  onStateChange?: (state: WebSocketState) => void;
  onReconnectAttempt?: (attempt: number) => void;
  onReconnectSuccess?: () => void;
  onReconnectFailed?: () => void;
}

class EnhancedWebSocketService {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private state: WebSocketState = WebSocketState.DISCONNECTED;
  private reconnectAttempts = 0;
  private reconnectTimer: number | null = null;
  private heartbeatTimer: number | null = null;
  private connectionTimer: number | null = null;
  private messageQueue: WebSocketMessage[] = [];
  private eventHandlers: WebSocketEventHandlers = {};
  private subscribers: Map<string, Set<(data: any) => void>> = new Map();
  private lastPingTime = 0;
  private isManualClose = false;

  constructor(config: Partial<WebSocketConfig> = {}) {
    this.config = {
      url: config.url || `${config.url || 'ws://localhost:8000'}/ws`,
      protocols: config.protocols,
      reconnectInterval: config.reconnectInterval || 3000,
      maxReconnectAttempts: config.maxReconnectAttempts || 10,
      heartbeatInterval: config.heartbeatInterval || 30000,
      connectionTimeout: config.connectionTimeout || 10000,
      enableHeartbeat: config.enableHeartbeat ?? true,
      enableLogging: config.enableLogging ?? true,
    };

    // Handle page visibility changes
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
    
    // Handle online/offline events
    window.addEventListener('online', this.handleOnline);
    window.addEventListener('offline', this.handleOffline);
  }

  /**
   * Connect to WebSocket server
   */
  connect(handlers: WebSocketEventHandlers = {}): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        this.eventHandlers = { ...this.eventHandlers, ...handlers };
        this.isManualClose = false;
        
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          resolve();
          return;
        }

        this.setState(WebSocketState.CONNECTING);
        this.log('Connecting to WebSocket', { url: this.config.url });

        // Create WebSocket connection
        this.ws = new WebSocket(this.config.url, this.config.protocols);
        
        // Set connection timeout
        this.connectionTimer = setTimeout(() => {
          if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
            this.ws.close();
            const error = this.createError('Connection timeout', 'CONNECTION_TIMEOUT');
            this.handleError(error);
            reject(error);
          }
        }, this.config.connectionTimeout);

        // WebSocket event handlers
        this.ws.onopen = (event) => {
          this.clearConnectionTimer();
          this.setState(WebSocketState.CONNECTED);
          this.reconnectAttempts = 0;
          this.log('WebSocket connected');
          
          // Send queued messages
          this.flushMessageQueue();
          
          // Start heartbeat
          if (this.config.enableHeartbeat) {
            this.startHeartbeat();
          }
          
          this.eventHandlers.onOpen?.(event);
          resolve();
        };

        this.ws.onmessage = (event) => {
          try {
            const message = this.parseMessage(event.data);
            this.handleMessage(message);
          } catch (error) {
            this.log('Failed to parse WebSocket message', { error, data: event.data });
          }
        };

        this.ws.onerror = (event) => {
          this.clearConnectionTimer();
          const error = this.createError('WebSocket error', 'WEBSOCKET_ERROR', event);
          this.handleError(error);
          reject(error);
        };

        this.ws.onclose = (event) => {
          this.clearConnectionTimer();
          this.stopHeartbeat();
          
          const wasConnected = this.state === WebSocketState.CONNECTED;
          this.setState(WebSocketState.DISCONNECTED);
          
          this.log('WebSocket closed', { 
            code: event.code, 
            reason: event.reason, 
            wasClean: event.wasClean 
          });

          this.eventHandlers.onClose?.(event);

          // Attempt reconnection if not manually closed
          if (!this.isManualClose && wasConnected) {
            this.attemptReconnection();
          }
        };

      } catch (error) {
        const appError = this.createError('Failed to create WebSocket connection', 'CONNECTION_FAILED', error);
        this.handleError(appError);
        reject(appError);
      }
    });
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    this.isManualClose = true;
    this.clearReconnectTimer();
    this.stopHeartbeat();
    this.clearConnectionTimer();
    
    if (this.ws) {
      this.ws.close(1000, 'Manual disconnect');
      this.ws = null;
    }
    
    this.setState(WebSocketState.CLOSED);
    this.log('WebSocket manually disconnected');
  }

  /**
   * Send message to WebSocket server
   */
  send(type: string, data: any): boolean {
    const message: WebSocketMessage = {
      type,
      data,
      timestamp: Date.now(),
      id: this.generateMessageId(),
    };

    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(message));
        this.log('Message sent', { type, messageId: message.id });
        return true;
      } catch (error) {
        this.log('Failed to send message', { error, type });
        this.queueMessage(message);
        return false;
      }
    } else {
      this.log('WebSocket not connected, queueing message', { type });
      this.queueMessage(message);
      return false;
    }
  }

  /**
   * Subscribe to specific message types
   */
  subscribe(type: string, handler: (data: any) => void): () => void {
    if (!this.subscribers.has(type)) {
      this.subscribers.set(type, new Set());
    }
    
    this.subscribers.get(type)!.add(handler);
    
    // Return unsubscribe function
    return () => {
      const handlers = this.subscribers.get(type);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.subscribers.delete(type);
        }
      }
    };
  }

  /**
   * Get current connection state
   */
  getState(): WebSocketState {
    return this.state;
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.state === WebSocketState.CONNECTED && this.ws?.readyState === WebSocket.OPEN;
  }

  /**
   * Get connection statistics
   */
  getStats() {
    return {
      state: this.state,
      reconnectAttempts: this.reconnectAttempts,
      queuedMessages: this.messageQueue.length,
      subscribers: Array.from(this.subscribers.keys()),
      lastPingTime: this.lastPingTime,
      isConnected: this.isConnected(),
    };
  }

  // Private methods

  private setState(newState: WebSocketState): void {
    if (this.state !== newState) {
      const oldState = this.state;
      this.state = newState;
      this.log('State changed', { from: oldState, to: newState });
      this.eventHandlers.onStateChange?.(newState);
    }
  }

  private parseMessage(data: string): WebSocketMessage {
    try {
      const parsed = JSON.parse(data);
      return {
        type: parsed.type || 'unknown',
        data: parsed.data || parsed,
        timestamp: parsed.timestamp || Date.now(),
        id: parsed.id,
      };
    } catch {
      // If parsing fails, treat as plain text message
      return {
        type: 'message',
        data: data,
        timestamp: Date.now(),
      };
    }
  }

  private handleMessage(message: WebSocketMessage): void {
    // Handle heartbeat responses
    if (message.type === 'pong') {
      this.lastPingTime = Date.now();
      return;
    }

    // Notify subscribers
    const handlers = this.subscribers.get(message.type);
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(message.data);
        } catch (error) {
          this.log('Error in message handler', { error, type: message.type });
        }
      });
    }

    // Notify global message handler
    this.eventHandlers.onMessage?.(message);
  }

  private handleError(error: AppError): void {
    this.setState(WebSocketState.ERROR);
    this.log('WebSocket error', { error });
    
    // Report error to global error handler
    errorHandler.handleError(error, {
      component: 'WebSocketService',
      action: 'connection',
    });

    this.eventHandlers.onError?.(error);
  }

  private attemptReconnection(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      this.log('Max reconnection attempts reached');
      this.eventHandlers.onReconnectFailed?.();
      return;
    }

    this.setState(WebSocketState.RECONNECTING);
    this.reconnectAttempts++;
    
    this.log('Attempting reconnection', { attempt: this.reconnectAttempts });
    this.eventHandlers.onReconnectAttempt?.(this.reconnectAttempts);

    const delay = Math.min(
      this.config.reconnectInterval * Math.pow(2, this.reconnectAttempts - 1),
      30000 // Max 30 seconds
    );

    this.reconnectTimer = setTimeout(() => {
      this.connect().then(() => {
        this.log('Reconnection successful');
        this.eventHandlers.onReconnectSuccess?.();
      }).catch(() => {
        this.attemptReconnection();
      });
    }, delay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected()) {
        this.send('ping', { timestamp: Date.now() });
      }
    }, this.config.heartbeatInterval);
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private clearConnectionTimer(): void {
    if (this.connectionTimer) {
      clearTimeout(this.connectionTimer);
      this.connectionTimer = null;
    }
  }

  private queueMessage(message: WebSocketMessage): void {
    this.messageQueue.push(message);
    
    // Limit queue size
    if (this.messageQueue.length > 100) {
      this.messageQueue.shift();
    }
  }

  private flushMessageQueue(): void {
    while (this.messageQueue.length > 0 && this.isConnected()) {
      const message = this.messageQueue.shift()!;
      try {
        this.ws!.send(JSON.stringify(message));
        this.log('Queued message sent', { type: message.type });
      } catch (error) {
        this.log('Failed to send queued message', { error, type: message.type });
        // Put message back at the front of the queue
        this.messageQueue.unshift(message);
        break;
      }
    }
  }

  private createError(message: string, code: string, originalError?: any): AppError {
    return {
      type: 'network',
      message,
      code,
      details: originalError,
      retryable: true,
      timestamp: new Date(),
      context: 'WebSocketService',
    };
  }

  private generateMessageId(): string {
    return `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  private handleVisibilityChange = (): void => {
    if (document.hidden) {
      this.log('Page hidden, pausing heartbeat');
      this.stopHeartbeat();
    } else {
      this.log('Page visible, resuming heartbeat');
      if (this.isConnected() && this.config.enableHeartbeat) {
        this.startHeartbeat();
      }
    }
  };

  private handleOnline = (): void => {
    this.log('Network online, attempting reconnection');
    if (!this.isConnected() && !this.isManualClose) {
      this.connect().catch(() => {
        // Reconnection will be handled by the connection failure
      });
    }
  };

  private handleOffline = (): void => {
    this.log('Network offline');
    this.setState(WebSocketState.DISCONNECTED);
  };

  private log(message: string, data?: any): void {
    if (this.config.enableLogging) {
      log.debug(message, 'WebSocket', data);
    }
  }

  // Cleanup
  destroy(): void {
    this.disconnect();
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);
    window.removeEventListener('online', this.handleOnline);
    window.removeEventListener('offline', this.handleOffline);
    this.subscribers.clear();
    this.messageQueue = [];
  }
}

// Create singleton instance
export const enhancedWebSocketService = new EnhancedWebSocketService({
  url: config.wsUrl,
  enableLogging: config.features.enableDebugMode,
});

// Export for use in components
export default enhancedWebSocketService;