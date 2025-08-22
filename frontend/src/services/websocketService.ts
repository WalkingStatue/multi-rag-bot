/**
 * Unified WebSocket service factory
 * This provides access to different WebSocket adapters from a single entry point
 */
import { chatWebSocketAdapter } from './adapters/ChatWebSocketAdapter';
import { notificationsWebSocketAdapter } from './adapters/NotificationsWebSocketAdapter';
import { WebSocketState } from './core/WebSocketCore';

/**
 * Unified WebSocket Service
 * Provides access to all WebSocket functionality through adapters
 */
export class WebSocketService {
  // Expose adapters as public properties
  public readonly chat = chatWebSocketAdapter;
  public readonly notifications = notificationsWebSocketAdapter;

  /**
   * Initialize all WebSocket connections with authentication token
   */
  async initialize(token: string): Promise<void> {
    try {
      // Connect to notifications WebSocket
      await this.notifications.connect(token);
      
      // Note: Chat WebSocket is connected on-demand when needed for a specific bot
      // This is handled in ChatWebSocketAdapter.connectToBot()
      
    } catch (error) {
      throw new Error(`Failed to initialize WebSocket services: ${error}`);
    }
  }

  /**
   * Connect to chat WebSocket for a specific bot
   */
  async connectToChat(botId: string, token: string, sessionId?: string): Promise<void> {
    return this.chat.connectToBot(botId, token, sessionId);
  }

  /**
   * Disconnect all WebSocket connections
   */
  disconnect(): void {
    this.chat.disconnect();
    this.notifications.disconnect();
  }

  /**
   * Clean disconnect that clears all listeners
   */
  cleanDisconnect(): void {
    this.chat.cleanDisconnect();
    this.notifications.disconnect();
  }

  /**
   * Check if any WebSocket connections are active
   */
  isConnected(): boolean {
    return this.chat.isConnected() || this.notifications.isConnected();
  }

  /**
   * Get overall connection status
   */
  getStatus() {
    return {
      chat: {
        connected: this.chat.isConnected(),
        state: this.chat.getState(),
        botId: this.chat.getCurrentBotId(),
        sessionId: this.chat.getCurrentSessionId(),
        stats: this.chat.getStats(),
      },
      notifications: {
        connected: this.notifications.isConnected(),
        state: this.notifications.getState(),
        stats: this.notifications.getStats(),
      },
    };
  }

  /**
   * Cleanup all resources
   */
  destroy(): void {
    this.chat.destroy();
    this.notifications.destroy();
  }
}

// Export singleton instance
export const webSocketService = new WebSocketService();

// Export types and utilities
export { WebSocketState } from './core/WebSocketCore';
export type { 
  NotificationData, 
  BotUpdateData, 
  PermissionUpdateData, 
  CollaborationUpdateData 
} from './adapters/NotificationsWebSocketAdapter';

// Backward compatibility exports - these maintain the same interface as the old services
export const websocketService = {
  connect: (token: string) => webSocketService.notifications.connect(token),
  disconnect: () => webSocketService.notifications.disconnect(),
  subscribe: (eventType: string, callback: (data: any) => void) => 
    webSocketService.notifications.subscribe(eventType, callback),
  send: (data: any) => webSocketService.notifications.send(data),
  isConnected: () => webSocketService.notifications.isConnected(),
};

export const chatWebSocketService = {
  connectToBot: (botId: string, token: string, sessionId?: string) => 
    webSocketService.chat.connectToBot(botId, token, sessionId),
  syncToSession: (sessionId: string) => webSocketService.chat.syncToSession(sessionId),
  disconnect: () => webSocketService.chat.disconnect(),
  cleanDisconnect: () => webSocketService.chat.cleanDisconnect(),
  onChatMessage: (callback: any) => webSocketService.chat.onChatMessage(callback),
  onTypingIndicator: (callback: any) => webSocketService.chat.onTypingIndicator(callback),
  onConnectionStatus: (callback: any) => webSocketService.chat.onConnectionStatus(callback),
  sendTypingIndicator: (isTyping: boolean) => webSocketService.chat.sendTypingIndicator(isTyping),
  isConnected: () => webSocketService.chat.isConnected(),
  getCurrentBotId: () => webSocketService.chat.getCurrentBotId(),
  getCurrentSessionId: () => webSocketService.chat.getCurrentSessionId(),
};
