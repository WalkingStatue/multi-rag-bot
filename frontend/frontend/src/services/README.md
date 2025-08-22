# WebSocket Services Architecture

This document describes the consolidated WebSocket architecture that replaces the previous standalone WebSocket services.

## Overview

The WebSocket architecture has been consolidated into a **core + adapter pattern** to eliminate code duplication, improve maintainability, and provide consistent connection management across different use cases.

## Architecture Components

### 1. WebSocketCore (`core/WebSocketCore.ts`)
The central WebSocket management class that handles:
- Connection establishment and management
- Automatic reconnection with exponential backoff
- Message queuing and delivery
- Heartbeat/ping-pong for connection health
- Event subscription and notification
- Error handling and logging
- Network state awareness (online/offline, visibility changes)

### 2. Adapters
Specialized service adapters that use the core for specific purposes:

#### ChatWebSocketAdapter (`adapters/ChatWebSocketAdapter.ts`)
- Handles bot-specific chat connections
- Manages chat sessions and synchronization
- Supports typing indicators
- Maps core events to chat-specific event formats
- Provides backward compatibility with the old `chatWebSocketService`

#### NotificationsWebSocketAdapter (`adapters/NotificationsWebSocketAdapter.ts`)
- Manages general application notifications
- Handles bot updates, permission changes, collaboration updates
- Maps core events to notification-specific formats
- Provides backward compatibility with the old `websocketService`

### 3. Unified Service Factory (`WebSocketService.ts`)
- Provides access to all adapters from a single entry point
- Manages initialization of multiple WebSocket connections
- Provides unified status and control methods
- Maintains backward compatibility exports

## Key Features

### Connection Management
- **Debounced connections**: Prevents rapid reconnection attempts
- **Health checks**: Validates backend availability before connecting
- **Smart reconnection**: Exponential backoff with max attempts and network health awareness
- **Connection timeouts**: Configurable connection establishment timeouts

### Message Handling
- **Message queuing**: Messages sent while disconnected are queued and delivered on reconnection
- **Type safety**: Structured message format with timestamps and IDs
- **Event subscription**: Subscribe to specific message types with automatic cleanup

### Error Handling
- **Structured errors**: Consistent error format with context and retry information
- **Global error reporting**: Integration with the application's error handling system
- **Graceful degradation**: Continues operation even with connection issues

### Network Awareness
- **Online/offline detection**: Automatically handles network state changes
- **Page visibility**: Pauses heartbeat when page is hidden to conserve resources
- **Connection health monitoring**: Integration with existing connection health utilities

## Usage

### Basic Usage
```typescript
import { webSocketService } from './services/WebSocketService';

// Initialize notifications connection
await webSocketService.initialize(token);

// Connect to a specific bot chat
await webSocketService.connectToChat(botId, token, sessionId);

// Subscribe to events
const unsubscribe = webSocketService.notifications.onNotification((data) => {
  console.log('New notification:', data);
});

// Clean up
unsubscribe();
webSocketService.disconnect();
```

### Backward Compatibility
The old service interfaces are still available for existing code:

```typescript
// Old websocketService interface (notifications)
import { websocketService } from './services/WebSocketService';
websocketService.connect(token);
websocketService.subscribe('notification', callback);

// Old chatWebSocketService interface  
import { chatWebSocketService } from './services/WebSocketService';
chatWebSocketService.connectToBot(botId, token, sessionId);
chatWebSocketService.onChatMessage(callback);
```

## Configuration

Each adapter can be configured with different parameters:

```typescript
const config = {
  endpoint: '/api/ws/chat',           // WebSocket endpoint
  reconnectInterval: 3000,           // Base reconnection delay (ms)
  maxReconnectAttempts: 10,          // Maximum reconnection attempts
  heartbeatInterval: 30000,          // Ping interval (ms)
  connectionTimeout: 10000,          // Connection timeout (ms)
  enableHeartbeat: true,             // Enable heartbeat/ping
  enableLogging: true,               // Enable debug logging
  enableDebounce: true,              // Enable connection debouncing
  debounceMs: 500,                   // Debounce delay (ms)
};
```

## Migration from Old Services

### Replacing websocketService (notifications)
```typescript
// Old
import { websocketService } from './services/websocketService';

// New
import { webSocketService } from './services/WebSocketService';
// Use webSocketService.notifications or the backward compatibility export
```

### Replacing chatWebSocketService
```typescript
// Old
import { chatWebSocketService } from './services/chatWebSocketService';

// New  
import { webSocketService } from './services/WebSocketService';
// Use webSocketService.chat or the backward compatibility export
```

### Replacing enhancedWebSocketService
The enhanced features are now part of the core WebSocketCore class:
```typescript
// Old
import { enhancedWebSocketService } from './services/enhancedWebSocketService';

// New
import { WebSocketCore } from './services/core/WebSocketCore';
// Or use the adapters for specific use cases
```

## Benefits of Consolidation

1. **Reduced Code Duplication**: Common WebSocket logic is centralized in WebSocketCore
2. **Consistent Behavior**: All WebSocket connections behave consistently 
3. **Better Error Handling**: Unified error handling and logging across all connections
4. **Improved Reliability**: Advanced reconnection logic and network awareness
5. **Easier Testing**: Centralized logic is easier to test and mock
6. **Better Performance**: Optimized connection management and message handling
7. **Maintainability**: Single place to update WebSocket logic
8. **Type Safety**: Consistent typing across all WebSocket interactions

## File Structure

```
src/services/
├── core/
│   └── WebSocketCore.ts          # Core WebSocket management
├── adapters/
│   ├── ChatWebSocketAdapter.ts   # Chat-specific adapter  
│   └── NotificationsWebSocketAdapter.ts  # Notifications adapter
├── WebSocketService.ts           # Unified factory service
├── websocketService.ts           # Legacy notifications service (deprecated)
├── chatWebSocketService.ts       # Legacy chat service (deprecated)
├── enhancedWebSocketService.ts   # Legacy enhanced service (deprecated)
└── README.md                     # This documentation
```

## Testing

The consolidated architecture can be tested by:

1. **Unit Tests**: Test individual adapters and the core separately
2. **Integration Tests**: Test the unified service with real WebSocket connections
3. **Mock Testing**: Use the adapter interfaces to mock WebSocket behavior
4. **Connection Tests**: Test reconnection, error handling, and network state changes

## Future Enhancements

The consolidated architecture makes it easy to add new features:

- **Connection pooling**: Reuse connections across different use cases
- **Message compression**: Add compression for large messages
- **Protocol negotiation**: Support for different WebSocket protocols
- **Load balancing**: Connect to different WebSocket servers
- **Metrics**: Detailed connection and message metrics
- **Caching**: Cache frequently accessed data

## Troubleshooting

If issues arise with WebSocket connections:

1. Check browser developer tools for WebSocket connection errors
2. Enable debug logging by setting `enableLogging: true` in adapter config
3. Check network connectivity and backend health endpoints
4. Verify authentication tokens are valid
5. Check for firewall or proxy issues blocking WebSocket connections
6. Use the connection diagnostics utilities in `utils/websocketDiagnostics.ts`
