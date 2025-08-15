/**
 * Simple WebSocket connection test utility
 */

export function testWebSocketConnection(botId: string, token: string): Promise<{success: boolean, message: string, details?: any}> {
  return new Promise((resolve) => {
    const wsUrl = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8000';
    const chatUrl = `${wsUrl}/api/ws/chat/${botId}?token=${encodeURIComponent(token)}`;
    

    
    let socket: WebSocket;
    let resolved = false;
    
    const timeout = setTimeout(() => {
      if (!resolved) {
        resolved = true;
        if (socket) {
          socket.close();
        }
        resolve({
          success: false,
          message: 'Connection timeout after 15 seconds',
          details: { timeout: true }
        });
      }
    }, 15000);

    try {
      socket = new WebSocket(chatUrl);
      
      socket.onopen = (event) => {
        if (!resolved) {
          resolved = true;
          clearTimeout(timeout);
          socket.close();
          resolve({
            success: true,
            message: 'WebSocket connection successful',
            details: { event }
          });
        }
      };

      socket.onerror = (error) => {
        if (!resolved) {
          resolved = true;
          clearTimeout(timeout);
          resolve({
            success: false,
            message: 'WebSocket connection error',
            details: { error }
          });
        }
      };

      socket.onclose = (event) => {
        if (!resolved) {
          resolved = true;
          clearTimeout(timeout);
          resolve({
            success: false,
            message: `WebSocket closed immediately: ${event.code} - ${event.reason || 'No reason provided'}`,
            details: { 
              code: event.code, 
              reason: event.reason,
              wasClean: event.wasClean
            }
          });
        }
      };

      socket.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data);
          if (message.type === 'connection_established') {
            // Connection established
          }
        } catch (e) {
          // Non-JSON message received
        }
      };

    } catch (error: any) {
      if (!resolved) {
        resolved = true;
        clearTimeout(timeout);
        resolve({
          success: false,
          message: `Failed to create WebSocket: ${error.message}`,
          details: { error }
        });
      }
    }
  });
}

// Export a simple test function that can be called from console
(window as any).testWebSocket = testWebSocketConnection;