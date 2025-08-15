/**
 * Error-related type definitions
 */

export interface AppError {
  type: ErrorType;
  message: string;
  statusCode?: number;
  code?: string;
  details?: Record<string, any>;
  timestamp: string;
  retryable: boolean;
  retryAfter?: number;
  context?: ErrorContext;
}

export enum ErrorType {
  NETWORK = 'network',
  VALIDATION = 'validation',
  AUTHENTICATION = 'authentication',
  AUTHORIZATION = 'authorization',
  NOT_FOUND = 'not_found',
  RATE_LIMIT = 'rate_limit',
  SERVER = 'server',
  CLIENT = 'client',
  UNKNOWN = 'unknown',
}

export interface ErrorContext {
  component?: string;
  action?: string;
  userId?: string;
  requestId?: string;
  url?: string;
  method?: string;
}

export interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
  errorInfo?: React.ErrorInfo;
}

export interface ErrorDisplayProps {
  error: AppError | Error | string;
  onRetry?: () => void;
  showDetails?: boolean;
  className?: string;
}