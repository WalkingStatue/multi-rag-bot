/**
 * WebSocket diagnostics and troubleshooting utilities
 */

interface DiagnosticResult {
  test: string;
  status: 'pass' | 'fail' | 'warning';
  message: string;
  details?: any;
}

interface WebSocketDiagnostics {
  timestamp: string;
  botId: string;
  results: DiagnosticResult[];
  summary: {
    passed: number;
    failed: number;
    warnings: number;
  };
}

export const runWebSocketDiagnostics = async (
  botId: string, 
  token: string
): Promise<WebSocketDiagnostics> => {
  const results: DiagnosticResult[] = [];
  const timestamp = new Date().toISOString();



  // Test 1: Network connectivity
  try {
    const apiUrl = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';
    const response = await fetch(`${apiUrl}/health`, {
      method: 'GET',
      signal: AbortSignal.timeout(5000)
    });

    if (response.ok) {
      results.push({
        test: 'Backend Connectivity',
        status: 'pass',
        message: 'Backend is reachable',
        details: { status: response.status, url: apiUrl }
      });
    } else {
      results.push({
        test: 'Backend Connectivity',
        status: 'fail',
        message: `Backend returned ${response.status}`,
        details: { status: response.status, url: apiUrl }
      });
    }
  } catch (error) {
    results.push({
      test: 'Backend Connectivity',
      status: 'fail',
      message: 'Cannot reach backend',
      details: { error: error instanceof Error ? error.message : 'Unknown error' }
    });
  }

  // Test 2: WebSocket URL construction
  try {
    const wsUrl = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8000';
    const chatUrl = `${wsUrl}/api/ws/chat/${botId}?token=${encodeURIComponent(token)}`;
    
    // Validate URL format
    const url = new URL(chatUrl);
    
    results.push({
      test: 'WebSocket URL',
      status: 'pass',
      message: 'WebSocket URL is valid',
      details: { 
        protocol: url.protocol,
        host: url.host,
        pathname: url.pathname,
        hasToken: url.searchParams.has('token')
      }
    });
  } catch (error) {
    results.push({
      test: 'WebSocket URL',
      status: 'fail',
      message: 'Invalid WebSocket URL',
      details: { error: error instanceof Error ? error.message : 'Unknown error' }
    });
  }

  // Test 3: Token validation
  try {
    if (!token) {
      results.push({
        test: 'Authentication Token',
        status: 'fail',
        message: 'No authentication token provided'
      });
    } else {
      // Basic token format check (JWT should have 3 parts)
      const tokenParts = token.split('.');
      if (tokenParts.length === 3) {
        results.push({
          test: 'Authentication Token',
          status: 'pass',
          message: 'Token format appears valid',
          details: { parts: tokenParts.length }
        });
      } else {
        results.push({
          test: 'Authentication Token',
          status: 'warning',
          message: 'Token format may be invalid',
          details: { parts: tokenParts.length }
        });
      }
    }
  } catch (error) {
    results.push({
      test: 'Authentication Token',
      status: 'fail',
      message: 'Token validation failed',
      details: { error: error instanceof Error ? error.message : 'Unknown error' }
    });
  }

  // Test 4: Bot access validation
  try {
    const apiUrl = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';
    const response = await fetch(`${apiUrl}/api/bots/${botId}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      signal: AbortSignal.timeout(5000)
    });

    if (response.ok) {
      results.push({
        test: 'Bot Access',
        status: 'pass',
        message: 'User has access to bot',
        details: { botId, status: response.status }
      });
    } else if (response.status === 401) {
      results.push({
        test: 'Bot Access',
        status: 'fail',
        message: 'Authentication failed',
        details: { botId, status: response.status }
      });
    } else if (response.status === 403) {
      results.push({
        test: 'Bot Access',
        status: 'fail',
        message: 'Access denied to bot',
        details: { botId, status: response.status }
      });
    } else if (response.status === 404) {
      results.push({
        test: 'Bot Access',
        status: 'fail',
        message: 'Bot not found',
        details: { botId, status: response.status }
      });
    } else {
      results.push({
        test: 'Bot Access',
        status: 'fail',
        message: `Unexpected response: ${response.status}`,
        details: { botId, status: response.status }
      });
    }
  } catch (error) {
    results.push({
      test: 'Bot Access',
      status: 'fail',
      message: 'Failed to verify bot access',
      details: { error: error instanceof Error ? error.message : 'Unknown error' }
    });
  }

  // Test 5: WebSocket connection attempt
  try {
    const wsUrl = (import.meta as any).env?.VITE_WS_URL || 'ws://localhost:8000';
    const chatUrl = `${wsUrl}/api/ws/chat/${botId}?token=${encodeURIComponent(token)}`;
    
    const testSocket = new WebSocket(chatUrl);
    
    const connectionResult = await new Promise<DiagnosticResult>((resolve) => {
      const timeout = setTimeout(() => {
        testSocket.close();
        resolve({
          test: 'WebSocket Connection',
          status: 'fail',
          message: 'Connection timeout (10s)',
          details: { url: chatUrl.replace(token, '[TOKEN]') }
        });
      }, 10000);

      testSocket.onopen = () => {
        clearTimeout(timeout);
        testSocket.close(1000, 'Diagnostic test complete');
        resolve({
          test: 'WebSocket Connection',
          status: 'pass',
          message: 'WebSocket connection successful',
          details: { url: chatUrl.replace(token, '[TOKEN]') }
        });
      };

      testSocket.onerror = () => {
        clearTimeout(timeout);
        resolve({
          test: 'WebSocket Connection',
          status: 'fail',
          message: 'WebSocket connection failed',
          details: { 
            url: chatUrl.replace(token, '[TOKEN]'),
            error: 'Connection error'
          }
        });
      };

      testSocket.onclose = (event) => {
        clearTimeout(timeout);
        if (event.code !== 1000) {
          resolve({
            test: 'WebSocket Connection',
            status: 'fail',
            message: `WebSocket closed unexpectedly: ${event.code}`,
            details: { 
              url: chatUrl.replace(token, '[TOKEN]'),
              code: event.code,
              reason: event.reason
            }
          });
        }
      };
    });

    results.push(connectionResult);
  } catch (error) {
    results.push({
      test: 'WebSocket Connection',
      status: 'fail',
      message: 'Failed to create WebSocket',
      details: { error: error instanceof Error ? error.message : 'Unknown error' }
    });
  }

  // Calculate summary
  const summary = {
    passed: results.filter(r => r.status === 'pass').length,
    failed: results.filter(r => r.status === 'fail').length,
    warnings: results.filter(r => r.status === 'warning').length
  };

  const diagnostics: WebSocketDiagnostics = {
    timestamp,
    botId,
    results,
    summary
  };

  // Diagnostics completed

  return diagnostics;
};

export const formatDiagnosticsReport = (diagnostics: WebSocketDiagnostics): string => {
  const { timestamp, botId, results, summary } = diagnostics;
  
  let report = `WebSocket Diagnostics Report\n`;
  report += `Timestamp: ${timestamp}\n`;
  report += `Bot ID: ${botId}\n`;
  report += `Summary: ${summary.passed} passed, ${summary.failed} failed, ${summary.warnings} warnings\n\n`;
  
  results.forEach((result, index) => {
    const status = result.status.toUpperCase();
    report += `${index + 1}. ${result.test}: [${status}] ${result.message}\n`;
    if (result.details) {
      report += `   Details: ${JSON.stringify(result.details, null, 2)}\n`;
    }
    report += '\n';
  });
  
  return report;
};