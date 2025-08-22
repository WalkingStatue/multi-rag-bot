/**
 * Notifications WebSocket adapter using the core WebSocket service
 * This replaces the standalone websocketService for notifications
 */
import { WebSocketCore, WebSocketState } from '../core/WebSocketCore';
import { config } from '../../config/environment';

export interface NotificationData {
  id?: string;
  type: string;
  title: string;
  message: string;
  timestamp: string;
  read?: boolean;
  data?: any;
}

export interface BotUpdateData {
  bot_id: string;
  action: 'created' | 'updated' | 'deleted';
  data: any;
}

export interface PermissionUpdateData {
  user_id: string;
  bot_id: string;
  permission_level: string;
  action: 'granted' | 'revoked' | 'updated';
}

export interface CollaborationUpdateData {
  document_id: string;
  user_id: string;
  action: 'joined' | 'left' | 'updated';
  data?: any;
}

export class NotificationsWebSocketAdapter {
  private core: WebSocketCore;

  constructor() {
    this.core = new WebSocketCore({
      endpoint: '/api/ws/notifications',
      enableLogging: config.features.enableDebugMode,
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      heartbeatInterval: 30000,
      connectionTimeout: 10000,
      enableHeartbeat: true,
      enableDebounce: false, // Don't debounce notifications
    });
  }

  /**
   * Connect to notifications WebSocket
   */
  async connect(token: string): Promise<void> {
    try {
      await this.core.connect(token);
    } catch (error) {
      throw error;
    }
  }

  /**
   * Disconnect from notifications WebSocket
   */
  disconnect(): void {
    this.core.disconnect();
  }

  /**
   * Subscribe to notifications
   */
  onNotification(callback: (data: NotificationData) => void): () => void {
    return this.core.subscribe('notification', callback);
  }

  /**
   * Subscribe to bot updates
   */
  onBotUpdate(callback: (data: BotUpdateData) => void): () => void {
    return this.core.subscribe('bot_update', callback);
  }

  /**
   * Subscribe to permission changes
   */
  onPermissionUpdate(callback: (data: PermissionUpdateData) => void): () => void {
    return this.core.subscribe('permission_update', callback);
  }

  /**
   * Subscribe to collaboration updates (document changes)
   */
  onCollaborationUpdate(callback: (data: CollaborationUpdateData) => void): () => void {
    return this.core.subscribe('collaboration_update', callback);
  }

  /**
   * Subscribe to connection status changes
   */
  onConnectionStatus(callback: (data: { status: string; error?: string; code?: number; reason?: string }) => void): () => void {
    return this.core.subscribe('connection', (data) => {
      // Map WebSocket core connection events to notification connection status format
      const state = this.core.getState();
      let status: string;
      
      switch (state) {
        case WebSocketState.CONNECTED:
          status = 'connected';
          break;
        case WebSocketState.CONNECTING:
          status = 'connecting';
          break;
        case WebSocketState.RECONNECTING:
          status = 'reconnecting';
          break;
        case WebSocketState.ERROR:
          status = 'error';
          break;
        case WebSocketState.DISCONNECTED:
        case WebSocketState.CLOSED:
        default:
          status = 'disconnected';
          break;
      }
      
      callback({
        status,
        error: data.error,
        code: data.code,
        reason: data.reason
      });
    });
  }

  /**
   * Subscribe to any event type (generic subscription)
   */
  subscribe(eventType: string, callback: (data: any) => void): () => void {
    return this.core.subscribe(eventType, callback);
  }

  /**
   * Send a message through WebSocket (if needed for notifications)
   */
  send(data: any): boolean {
    return this.core.send('message', data);
  }

  /**
   * Check if connected
   */
  isConnected(): boolean {
    return this.core.isConnected();
  }

  /**
   * Get connection state
   */
  getState(): WebSocketState {
    return this.core.getState();
  }

  /**
   * Get connection statistics
   */
  getStats() {
    return this.core.getStats();
  }

  /**
   * Cleanup resources
   */
  destroy(): void {
    this.core.destroy();
  }
}

// Export singleton instance
export const notificationsWebSocketAdapter = new NotificationsWebSocketAdapter();
