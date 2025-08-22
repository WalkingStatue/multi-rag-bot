/**
 * Comprehensive error handling utilities
 */
import { log } from './logger';

export interface AppError {
  type: 'network' | 'api' | 'validation' | 'auth' | 'rate_limit' | 'unknown';
  message: string;
  code?: string;
  statusCode?: number;
  details?: any;
  retryable?: boolean;
  retryAfter?: number;
  timestamp: Date;
  context?: string;
}

export interface ErrorContext {
  component?: string;
  action?: string;
  userId?: string;
  sessionId?: string;
  metadata?: Record<string, any>;
}

/**
 * Parse API error response into structured AppError
 */
export function parseApiError(error: any, context?: ErrorContext): AppError {
  const response = error.response;
  const status = response?.status;
  const data = response?.data;
  const detail = data?.detail || data?.message || error.message || 'Unknown error occurred';

  let errorType: AppError['type'] = 'unknown';
  let retryable = false;
  let retryAfter: number | undefined;

  // Determine error type based on status code and content
  if (status === 401 || detail.includes('authentication') || detail.includes('unauthorized')) {
    errorType = 'auth';
    retryable = false;
  } else if (status === 429 || detail.includes('rate limit')) {
    errorType = 'rate_limit';
    retryable = true;
    retryAfter = response?.headers['retry-after'] ? parseInt(response.headers['retry-after']) : 30;
  } else if (status === 400 || status === 422) {
    errorType = 'validation';
    retryable = false;
  } else if (status >= 500) {
    errorType = 'api';
    retryable = true;
    retryAfter = 10;
  } else if (!response || error.code === 'NETWORK_ERROR' || error.code === 'ECONNABORTED') {
    errorType = 'network';
    retryable = true;
    retryAfter = 5;
  }

  const result: AppError = {
    type: errorType,
    message: detail,
    retryable,
    timestamp: new Date(),
  };

  if (data?.code || error.code) {
    result.code = data?.code || error.code;
  }

  if (status) {
    result.statusCode = status;
  }

  if (data) {
    result.details = data;
  }

  if (retryAfter !== undefined) {
    result.retryAfter = retryAfter;
  }

  const contextValue = context?.component || context?.action;
  if (contextValue) {
    result.context = contextValue;
  }

  return result;
}

/**
 * Format error message for user display
 */
export function formatErrorMessage(error: AppError): string {
  switch (error.type) {
    case 'network':
      return 'Network connection error. Please check your internet connection and try again.';
    case 'auth':
      return 'Authentication failed. Please log in again.';
    case 'rate_limit':
      return `Rate limit exceeded. Please wait ${error.retryAfter || 30} seconds before trying again.`;
    case 'validation':
      return error.message || 'Invalid input. Please check your data and try again.';
    case 'api':
      return 'Server error. Please try again in a moment.';
    default:
      return error.message || 'An unexpected error occurred. Please try again.';
  }
}

/**
 * Check if error should trigger logout
 */
export function shouldLogout(error: AppError): boolean {
  return error.type === 'auth' && error.statusCode === 401;
}

/**
 * Get retry delay for retryable errors
 */
export function getRetryDelay(error: AppError, attempt: number = 1): number {
  if (!error.retryable) return 0;
  
  const baseDelay = error.retryAfter || 5;
  // Exponential backoff with jitter
  return Math.min(baseDelay * Math.pow(2, attempt - 1) + Math.random() * 1000, 30000);
}

/**
 * Log error for debugging and monitoring
 */
export function logError(error: AppError, context?: ErrorContext): void {
  const logData = {
    ...error,
    context,
    userAgent: navigator.userAgent,
    url: window.location.href,
    timestamp: error.timestamp.toISOString()
  };

  // Log using the logger system
  log.error('Application Error', 'ErrorHandler', logData);

  // In production, you might want to send to monitoring service
  // Example: sendToMonitoringService(logData);
}

/**
 * Create error from validation failures
 */
export function createValidationError(
  message: string,
  details?: Record<string, string[]>
): AppError {
  return {
    type: 'validation',
    message,
    details,
    retryable: false,
    timestamp: new Date()
  };
}

/**
 * Create network error
 */
export function createNetworkError(message?: string): AppError {
  return {
    type: 'network',
    message: message || 'Network connection failed',
    retryable: true,
    retryAfter: 5,
    timestamp: new Date()
  };
}

/**
 * Error handler hook for React components
 */
export class ErrorHandler {
  private static instance: ErrorHandler;
  private errorListeners: ((error: AppError) => void)[] = [];

  static getInstance(): ErrorHandler {
    if (!ErrorHandler.instance) {
      ErrorHandler.instance = new ErrorHandler();
    }
    return ErrorHandler.instance;
  }

  addErrorListener(listener: (error: AppError) => void): () => void {
    this.errorListeners.push(listener);
    return () => {
      const index = this.errorListeners.indexOf(listener);
      if (index > -1) {
        this.errorListeners.splice(index, 1);
      }
    };
  }

  handleError(error: any, context?: ErrorContext): AppError {
    const appError = error instanceof Error ? parseApiError(error, context) : error;
    
    // Log the error
    logError(appError, context);
    
    // Notify listeners
    this.errorListeners.forEach(listener => {
      try {
        listener(appError);
      } catch (e) {
        log.error('Error in error listener', 'ErrorHandler', e);
      }
    });

    return appError;
  }
}

export const errorHandler = ErrorHandler.getInstance();