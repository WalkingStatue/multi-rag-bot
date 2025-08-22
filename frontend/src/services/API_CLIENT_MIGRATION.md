# API Client Migration Guide

This document describes the migration from `apiClient` to `enhancedApiClient` for improved API handling.

## Migration Summary

All service files have been updated to use `enhancedApiClient` instead of the legacy `apiClient`. This provides:

- **Enhanced Error Handling**: Structured error parsing and context-aware error reporting
- **Automatic Retry Logic**: Configurable retry for failed requests with exponential backoff
- **Request Context Tracking**: Better logging and debugging with request context
- **Comprehensive Logging**: Request timing and success/failure logging in development
- **Advanced Features**: File upload with progress, file download helpers, health checks

## Files Updated

The following service files have been migrated:

- ✅ `src/services/authService.ts`
- ✅ `src/services/notificationService.ts` 
- ✅ `src/services/chatService.ts`
- ✅ `src/services/botService.ts`
- ✅ `src/services/permissionService.ts`
- ✅ `src/services/apiKeyService.ts`
- ✅ `src/services/documentService.ts`
- ✅ `src/hooks/useApi.ts` (was already using enhancedApiClient)
- ✅ `src/services/offlineAwareApi.ts` (was already using enhancedApiClient)

## Breaking Changes

### Import Statements
```typescript
// Old
import { apiClient } from './api';

// New
import { enhancedApiClient } from './enhancedApi';
```

### Method Calls
```typescript
// Old
const response = await apiClient.get('/endpoint');

// New  
const response = await enhancedApiClient.get('/endpoint');
```

### Enhanced Context Support
The new client supports request context for better error tracking:

```typescript
// Basic usage (same as before)
const response = await enhancedApiClient.get('/users');

// With context for better error tracking
const response = await enhancedApiClient.get('/users', {
  context: 'UserService.getUsers'
});
```

### Retry Configuration
You can now configure retry behavior per request:

```typescript
const response = await enhancedApiClient.post('/data', payload, {
  retry: {
    maxRetries: 5,
    retryDelay: 2000,
    retryCondition: (error) => error.response?.status >= 500
  }
});
```

### Error Handling Opt-out
You can skip enhanced error handling if needed:

```typescript
const response = await enhancedApiClient.get('/data', {
  skipErrorHandling: true
});
```

## New Features Available

### File Upload with Progress
```typescript
await enhancedApiClient.uploadFile(
  '/upload',
  file,
  (progress) => console.log(`Upload progress: ${progress}%`),
  { context: 'FileUpload' }
);
```

### File Download
```typescript
await enhancedApiClient.downloadFile('/download/file.pdf', 'document.pdf');
```

### Health Check
```typescript
const isHealthy = await enhancedApiClient.healthCheck();
```

### Request Cancellation
```typescript
enhancedApiClient.cancelAllRequests();
```

## Configuration Options

The enhanced client supports these configuration options:

```typescript
interface RequestConfig {
  retry?: {
    maxRetries: number;
    retryDelay: number;
    retryCondition?: (error: any) => boolean;
  };
  skipErrorHandling?: boolean;
  context?: string;
  timeout?: number;
  headers?: Record<string, string>;
}
```

## Error Handling Improvements

### Before (apiClient)
```typescript
try {
  const response = await apiClient.get('/data');
  return response.data;
} catch (error) {
  console.error('Request failed:', error);
  throw error;
}
```

### After (enhancedApiClient)
```typescript
// Error handling is automatic, but you can still catch specific errors
try {
  const response = await enhancedApiClient.get('/data', {
    context: 'DataService.getData'
  });
  return response.data;
} catch (error) {
  // Error is already logged and processed by enhanced error handler
  // Just handle business logic here
  throw error;
}
```

## Backward Compatibility

The old `apiClient` is still available but deprecated. In development mode, it will show deprecation warnings. The enhanced API client maintains the same interface, so no code changes are required beyond the import statement.

## Environment Integration

The enhanced client uses the typed environment helpers:

```typescript
// Automatically uses typed environment configuration
import { enhancedApiClient } from './enhancedApi';
// Gets VITE_API_URL from getEnvVar.get('VITE_API_URL')
```

## Logging Integration

The enhanced client integrates with the utils/logger system:

```typescript
// In development, you'll see logs like:
// ✅ GET /api/users - 234ms [enhancedApi]
// ❌ POST /api/data failed: 500 Internal Server Error [enhancedApi]
```

## Migration Checklist

- [x] Update all service imports to use `enhancedApiClient`
- [x] Update all method calls to use `enhancedApiClient`
- [x] Add context parameters to important API calls
- [x] Test retry behavior with failing requests
- [x] Verify error handling and logging work correctly
- [x] Add deprecation warnings to old `apiClient`
- [ ] Remove old `apiClient` in future cleanup (after thorough testing)

## Future Improvements

With the enhanced API client in place, future improvements can include:

- **Request/Response Interceptors**: Custom processing for specific endpoints
- **Caching Integration**: Automatic response caching for GET requests
- **Request Deduplication**: Prevent duplicate simultaneous requests
- **Performance Monitoring**: Track request timing and success rates
- **Circuit Breaker**: Temporarily stop requests to failing endpoints

## Testing the Migration

To test the migration:

1. **Development Mode**: Check browser console for any deprecation warnings
2. **Network Failures**: Test that retry logic works by simulating network issues
3. **Error Scenarios**: Verify enhanced error handling shows helpful messages
4. **File Operations**: Test file upload/download functionality
5. **Authentication**: Ensure token refresh still works correctly

## Support

For questions or issues with the migration:

1. Check the enhanced error logs in browser dev tools
2. Review the `enhancedApiClient` implementation in `src/services/enhancedApi.ts`
3. Test with the legacy `apiClient` temporarily if needed for comparison
4. Check network requests in browser dev tools for detailed timing and headers
