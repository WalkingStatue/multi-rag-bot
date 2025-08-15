/**
 * WebSocket service for real-time updates
 */


export class WebSocketService {
  private socket: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private listeners: Map<string, Set<(data: any) => void>> = new Map();
  private token: string | null = null;
  private pingInterval: number | null = null;

  /**
   * Connect to WebSocket server
   */
  connect(token: string): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    this.token = token;
    const wsUrl = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8000';
    const notificationsUrl = `${wsUrl}/api/ws/notifications?token=${encodeURIComponent(token)}`;
    
    this.socket = new WebSocket(notificationsUrl);
    this.setupEventHandlers();
  }

  /**
   * Disconnect from WebSocket server
   */
  disconnect(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
    
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.listeners.clear();
    this.reconnectAttempts = 0;
    this.token = null;
  }

  /**
   * Subscribe to specific event types
   */
  subscribe(eventType: string, callback: (data: any) => void): () => void {
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
   * Send a message through WebSocket
   */
  send(data: any): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data));
    }
  }

  /**
   * Check if WebSocket is connected
   */
  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN || false;
  }

  /**
   * Setup event handlers for WebSocket
   */
  private setupEventHandlers(): void {
    if (!this.socket) return;

    this.socket.onopen = () => {
      this.reconnectAttempts = 0;
      this.notifyListeners('connection', { status: 'connected' });
      this.startPingInterval();
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
      
      // Don't reconnect if it was a clean close or authentication error
      if (event.code !== 1000 && event.code !== 4001) {
        this.handleReconnect();
      }
    };

    this.socket.onerror = () => {
      this.notifyListeners('connection', { status: 'error', error: 'Connection error' });
    };

    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        // Error parsing WebSocket message
      }
    };
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(message: any): void {
    const { type, data } = message;

    switch (type) {
      case 'connection_established':
        break;
      
      case 'notification':
        this.notifyListeners('notification', data);
        break;
      
      case 'permission_change':
        this.notifyListeners('permission_update', data);
        break;
      
      case 'bot_update':
        this.notifyListeners('bot_update', data);
        break;
      
      case 'document_update':
        this.notifyListeners('collaboration_update', data);
        break;
      
      case 'chat_response':
        // Handle chat responses from the bot
        this.notifyListeners('chat_message', data);
        break;
      
      case 'chat_message':
        // Handle chat messages (user messages from other collaborators)
        this.notifyListeners('chat_message', data);
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
   * Start ping interval for connection health
   */
  private startPingInterval(): void {
    this.pingInterval = setInterval(() => {
      if (this.isConnected()) {
        this.send({
          type: 'ping',
          timestamp: new Date().toISOString()
        });
      }
    }, 30000); // Ping every 30 seconds
  }

  /**
   * Handle reconnection logic
   */
  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts || !this.token) {
      this.notifyListeners('connection', { 
        status: 'failed', 
        message: 'Failed to reconnect after maximum attempts' 
      });
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    
    setTimeout(() => {
      if (this.token) {
        this.connect(this.token);
      }
    }, delay);
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
          // Error in WebSocket listener
        }
      });
    }
  }
}

// Export singleton instance
export const websocketService = new WebSocketService();