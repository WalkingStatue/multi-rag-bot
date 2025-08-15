/**
 * Connection recovery utilities for handling WebSocket failures
 */
import { chatWebSocketService } from '../services/chatWebSocketService';
import { authService } from '../services/authService';
import { connectionHealthMonitor } from './connectionHealth';
import { runWebSocketDiagnostics } from './websocketDiagnostics';

export interface RecoveryOptions {
  maxAttempts?: number;
  baseDelay?: number;
  maxDelay?: number;
  backoffMultiplier?: number;
  runDiagnostics?: boolean;
}

export interface RecoveryResult {
  success: boolean;
  attempts: number;
  error?: string;
  diagnostics?: any;
}

export class ConnectionRecoveryManager {
  private isRecovering = false;
  private recoveryPromise: Promise<RecoveryResult> | null = null;

  /**
   * Attempt to recover WebSocket connection with exponential backoff
   */
  async recoverConnection(
    botId: string,
    sessionId?: string,
    options: RecoveryOptions = {}
  ): Promise<RecoveryResult> {
    // Return existing recovery promise if already recovering
    if (this.recoveryPromise) {
      return this.recoveryPromise;
    }

    const {
      maxAttempts = 5,
      baseDelay = 1000,
      maxDelay = 30000,
      backoffMultiplier = 2,
      runDiagnostics = true
    } = options;

    this.recoveryPromise = this.performRecovery(
      botId,
      sessionId,
      maxAttempts,
      baseDelay,
      maxDelay,
      backoffMultiplier,
      runDiagnostics
    );

    const result = await this.recoveryPromise;
    this.recoveryPromise = null;
    return result;
  }

  private async performRecovery(
    botId: string,
    sessionId: string | undefined,
    maxAttempts: number,
    baseDelay: number,
    maxDelay: number,
    backoffMultiplier: number,
    runDiagnostics: boolean
  ): Promise<RecoveryResult> {
    this.isRecovering = true;
    let attempts = 0;
    let lastError: string | undefined;
    let diagnostics: any;



    try {
      const token = authService.getAccessToken();
      if (!token) {
        return {
          success: false,
          attempts: 0,
          error: 'No authentication token available'
        };
      }

      // Run diagnostics if requested
      if (runDiagnostics && attempts === 0) {
        try {
          diagnostics = await runWebSocketDiagnostics(botId, token);
        } catch (diagError) {
          // Failed to run diagnostics
        }
      }

      while (attempts < maxAttempts) {
        attempts++;

        try {
          // Check network health before attempting
          if (!connectionHealthMonitor.isHealthy()) {
            await this.delay(Math.min(baseDelay * Math.pow(backoffMultiplier, attempts), maxDelay));
            continue;
          }

          // Disconnect any existing connection
          chatWebSocketService.disconnect();

          // Wait a moment before reconnecting
          await this.delay(500);

          // Attempt to reconnect
          await chatWebSocketService.connectToBot(botId, token, sessionId);

          // Verify connection is actually open
          if (chatWebSocketService.isConnected()) {
            return {
              success: true,
              attempts,
              diagnostics
            };
          } else {
            throw new Error('Connection not established after connect call');
          }

        } catch (error) {
          lastError = error instanceof Error ? error.message : 'Unknown error';

          if (attempts < maxAttempts) {
            const delay = Math.min(baseDelay * Math.pow(backoffMultiplier, attempts), maxDelay);
            await this.delay(delay);
          }
        }
      }

      return {
        success: false,
        attempts,
        error: lastError || 'All recovery attempts failed',
        diagnostics
      };

    } finally {
      this.isRecovering = false;
    }
  }

  /**
   * Check if recovery is currently in progress
   */
  isRecoveringConnection(): boolean {
    return this.isRecovering;
  }

  /**
   * Cancel ongoing recovery attempt
   */
  cancelRecovery(): void {
    if (this.recoveryPromise) {
      this.isRecovering = false;
      this.recoveryPromise = null;
    }
  }

  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Export singleton instance
export const connectionRecoveryManager = new ConnectionRecoveryManager();

/**
 * Quick recovery function for common use cases
 */
export const quickRecover = async (
  botId: string,
  sessionId?: string
): Promise<boolean> => {
  const result = await connectionRecoveryManager.recoverConnection(botId, sessionId, {
    maxAttempts: 3,
    baseDelay: 1000,
    runDiagnostics: false
  });
  
  return result.success;
};

/**
 * Full recovery with diagnostics for troubleshooting
 */
export const fullRecover = async (
  botId: string,
  sessionId?: string
): Promise<RecoveryResult> => {
  return connectionRecoveryManager.recoverConnection(botId, sessionId, {
    maxAttempts: 5,
    baseDelay: 2000,
    runDiagnostics: true
  });
};