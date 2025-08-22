/**
 * Enhanced error boundaries for different application sections
 */
import React, { Component, ErrorInfo, ReactNode } from 'react';
import { logErrorBoundary, log } from '../../utils/logger';
import { ErrorDisplay, FullPageError } from './ErrorDisplay';
import { Button } from './Button';
import { getEnvVar } from '../../config/environment';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  level?: 'page' | 'section' | 'component';
  context?: string;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  showReload?: boolean;
  showGoHome?: boolean;
}

interface State {
  hasError: boolean;
  error?: Error;
  errorInfo?: ErrorInfo;
  errorId: string;
}

export class EnhancedErrorBoundary extends Component<Props, State> {
  private retryCount = 0;
  private maxRetries = 3;

  constructor(props: Props) {
    super(props);
    this.state = { 
      hasError: false,
      errorId: this.generateErrorId()
    };
  }

  private generateErrorId(): string {
    return `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { 
      hasError: true, 
      error,
      errorId: `error-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    // Log the error
    logErrorBoundary(error, errorInfo);
    
    // Store error info in state
    this.setState({ errorInfo });
    
    // Call custom error handler if provided
    this.props.onError?.(error, errorInfo);
    
    // Send error to monitoring service in production
    if (getEnvVar.PROD()) {
      this.sendErrorToMonitoring(error, errorInfo);
    }
  }

  private sendErrorToMonitoring(error: Error, errorInfo: ErrorInfo) {
    // In a real app, you'd send this to your monitoring service
    // Example: Sentry, LogRocket, etc.
    try {
      fetch('/api/errors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          errorId: this.state.errorId,
          message: error.message,
          stack: error.stack,
          componentStack: errorInfo.componentStack,
          context: this.props.context,
          level: this.props.level,
          timestamp: new Date().toISOString(),
          url: window.location.href,
          userAgent: navigator.userAgent,
        }),
      }).catch(() => {
        // Ignore monitoring errors
      });
    } catch {
      // Ignore monitoring errors
    }
  }

  private handleRetry = () => {
    if (this.retryCount < this.maxRetries) {
      this.retryCount++;
      this.setState({ 
        hasError: false, 
        error: undefined, 
        errorInfo: undefined,
        errorId: this.generateErrorId()
      });
    }
  };

  private handleReload = () => {
    window.location.reload();
  };

  private handleGoHome = () => {
    window.location.href = '/dashboard';
  };

  render() {
    if (this.state.hasError && this.state.error) {
      // Custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      const canRetry = this.retryCount < this.maxRetries;
      const error = this.state.error;
      const context = this.props.context || 'Application';

      // Full page error for page-level boundaries
      if (this.props.level === 'page') {
        return (
          <FullPageError
            error={`${context} Error: ${error.message}`}
            onRetry={canRetry ? this.handleRetry : undefined}
            onGoHome={this.props.showGoHome ? this.handleGoHome : undefined}
          />
        );
      }

      // Section or component level error
      return (
        <div className="p-4 border border-red-200 rounded-lg bg-red-50 dark:bg-red-900/20 dark:border-red-800">
          <ErrorDisplay
            error={`${context} Error: ${error.message}`}
            onRetry={canRetry ? this.handleRetry : undefined}
            showDetails={getEnvVar.DEV()}
            className="border-0 bg-transparent shadow-none p-0"
          />
          
          {/* Additional actions */}
          <div className="mt-4 flex flex-wrap gap-2">
            {this.props.showReload && (
              <Button
                onClick={this.handleReload}
                size="sm"
                variant="secondary"
              >
                Reload Page
              </Button>
            )}
            
            {getEnvVar.DEV() && (
              <Button
                onClick={() => log.info('Error Details', 'EnhancedErrorBoundary', { 
                  error: this.state.error, 
                  errorInfo: this.state.errorInfo 
                })}
                size="sm"
                variant="secondary"
              >
                Log Details
              </Button>
            )}
          </div>
          
          {/* Error ID for support */}
          <div className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
            Error ID: {this.state.errorId}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Specialized error boundaries for different sections

/**
 * Page-level error boundary
 */
export const PageErrorBoundary: React.FC<{
  children: ReactNode;
  pageName?: string;
}> = ({ children, pageName = 'Page' }) => (
  <EnhancedErrorBoundary
    level="page"
    context={pageName}
    showGoHome
    showReload
  >
    {children}
  </EnhancedErrorBoundary>
);

/**
 * Chat-specific error boundary
 */
export const ChatErrorBoundary: React.FC<{
  children: ReactNode;
  onError?: () => void;
}> = ({ children, onError }) => (
  <EnhancedErrorBoundary
    level="section"
    context="Chat"
    onError={onError ? (error) => onError() : undefined}
    fallback={
      <div className="flex items-center justify-center h-64 bg-neutral-50 dark:bg-neutral-900 rounded-lg">
        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 text-neutral-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-neutral-900 dark:text-neutral-100">
            Chat Unavailable
          </h3>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            There was an error loading the chat. Please try refreshing the page.
          </p>
          <div className="mt-4">
            <Button onClick={() => window.location.reload()} size="sm">
              Refresh Page
            </Button>
          </div>
        </div>
      </div>
    }
  >
    {children}
  </EnhancedErrorBoundary>
);

/**
 * Document management error boundary
 */
export const DocumentErrorBoundary: React.FC<{
  children: ReactNode;
}> = ({ children }) => (
  <EnhancedErrorBoundary
    level="section"
    context="Document Management"
    fallback={
      <div className="p-6 text-center bg-neutral-50 dark:bg-neutral-900 rounded-lg">
        <svg
          className="mx-auto h-12 w-12 text-neutral-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-neutral-900 dark:text-neutral-100">
          Document Management Error
        </h3>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Unable to load document management features.
        </p>
      </div>
    }
  >
    {children}
  </EnhancedErrorBoundary>
);

/**
 * Form error boundary
 */
export const FormErrorBoundary: React.FC<{
  children: ReactNode;
  formName?: string;
}> = ({ children, formName = 'Form' }) => (
  <EnhancedErrorBoundary
    level="component"
    context={formName}
    fallback={
      <div className="p-4 border border-red-200 rounded-lg bg-red-50 dark:bg-red-900/20 dark:border-red-800">
        <div className="flex">
          <svg
            className="h-5 w-5 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
            />
          </svg>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800 dark:text-red-200">
              {formName} Error
            </h3>
            <p className="mt-1 text-sm text-red-700 dark:text-red-300">
              There was an error with the form. Please refresh the page and try again.
            </p>
          </div>
        </div>
      </div>
    }
  >
    {children}
  </EnhancedErrorBoundary>
);

/**
 * API data error boundary
 */
export const DataErrorBoundary: React.FC<{
  children: ReactNode;
  dataType?: string;
}> = ({ children, dataType = 'Data' }) => (
  <EnhancedErrorBoundary
    level="component"
    context={`${dataType} Loading`}
    fallback={
      <div className="p-4 text-center">
        <svg
          className="mx-auto h-8 w-8 text-neutral-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-neutral-900 dark:text-neutral-100">
          {dataType} Unavailable
        </h3>
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          Unable to load {dataType.toLowerCase()}. Please try again.
        </p>
      </div>
    }
  >
    {children}
  </EnhancedErrorBoundary>
);

// Hook for programmatic error reporting
export const useErrorReporting = () => {
  const reportError = (error: Error, context?: string, additionalData?: any) => {
    logErrorBoundary(error, { componentStack: context || 'Manual Report' });
    
    // Send to monitoring service
    if (getEnvVar.PROD()) {
      fetch('/api/errors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          errorId: `manual-${Date.now()}`,
          message: error.message,
          stack: error.stack,
          context,
          additionalData,
          timestamp: new Date().toISOString(),
          url: window.location.href,
        }),
      }).catch(() => {
        // Ignore monitoring errors
      });
    }
  };

  return { reportError };
};