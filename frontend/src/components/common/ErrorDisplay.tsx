/**
 * Error display components for different error scenarios
 */
import React from 'react';
import { AppError, formatErrorMessage } from '../../utils/errorHandler';
import { Button } from './Button';

interface ErrorDisplayProps {
  error: AppError | string;
  onRetry?: () => void;
  onDismiss?: () => void;
  className?: string;
  showDetails?: boolean;
}

/**
 * Generic error display component
 */
export const ErrorDisplay: React.FC<ErrorDisplayProps> = ({
  error,
  onRetry,
  onDismiss,
  className = '',
  showDetails = false
}) => {
  const errorObj = typeof error === 'string' 
    ? { type: 'unknown' as const, message: error, timestamp: new Date(), retryable: false }
    : error;

  const message = typeof error === 'string' ? error : formatErrorMessage(errorObj);

  const getErrorIcon = () => {
    switch (errorObj.type) {
      case 'network':
        return (
          <svg className="h-8 w-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        );
      case 'auth':
        return (
          <svg className="h-8 w-8 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
        );
      case 'rate_limit':
        return (
          <svg className="h-8 w-8 text-orange-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      default:
        return (
          <svg className="h-8 w-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        );
    }
  };

  return (
    <div className={`bg-white dark:bg-neutral-900 shadow-lg rounded-lg p-6 ${className}`}>
      <div className="flex items-start">
        <div className="flex-shrink-0">
          {getErrorIcon()}
        </div>
        <div className="ml-3 flex-1">
          <h3 className="text-sm font-medium text-neutral-800 dark:text-neutral-100">
            {errorObj.type === 'network' ? 'Connection Error' :
             errorObj.type === 'auth' ? 'Authentication Error' :
             errorObj.type === 'rate_limit' ? 'Rate Limit Exceeded' :
             errorObj.type === 'validation' ? 'Validation Error' :
             'Something went wrong'}
          </h3>
          <div className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
            <p>{message}</p>
            
            {showDetails && errorObj.details && (
              <details className="mt-2">
                <summary className="cursor-pointer text-xs text-neutral-400 hover:text-neutral-600">
                  Technical details
                </summary>
                <pre className="mt-1 text-xs text-neutral-400 whitespace-pre-wrap bg-neutral-50 dark:bg-neutral-800 p-2 rounded">
                  {JSON.stringify(errorObj.details, null, 2)}
                </pre>
              </details>
            )}
          </div>
          
          <div className="mt-4 flex space-x-3">
            {onRetry && errorObj.retryable && (
              <Button
                onClick={onRetry}
                size="sm"
                variant="primary"
              >
                Try Again
              </Button>
            )}
            {onDismiss && (
              <Button
                onClick={onDismiss}
                size="sm"
                variant="secondary"
              >
                Dismiss
              </Button>
            )}
          </div>
        </div>
        
        {onDismiss && (
          <div className="ml-4 flex-shrink-0">
            <button
              onClick={onDismiss}
              className="bg-white dark:bg-neutral-900 rounded-md inline-flex text-neutral-400 hover:text-neutral-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              <span className="sr-only">Close</span>
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Inline error display for forms and smaller components
 */
export const InlineError: React.FC<{
  error: AppError | string;
  className?: string;
}> = ({ error, className = '' }) => {
  const message = typeof error === 'string' ? error : formatErrorMessage(error);
  
  return (
    <div className={`flex items-center space-x-2 text-red-600 dark:text-red-400 ${className}`}>
      <svg className="h-4 w-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
      </svg>
      <span className="text-sm">{message}</span>
    </div>
  );
};

/**
 * Full page error display
 */
export const FullPageError: React.FC<{
  error: AppError | string;
  onRetry?: () => void;
  onGoHome?: () => void;
}> = ({ error, onRetry, onGoHome }) => {
  const errorObj = typeof error === 'string' 
    ? { type: 'unknown' as const, message: error, timestamp: new Date(), retryable: false }
    : error;

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-50 dark:bg-neutral-900 px-4">
      <div className="max-w-md w-full">
        <ErrorDisplay
          error={errorObj}
          onRetry={onRetry}
          showDetails={import.meta.env.DEV}
          className="text-center"
        />
        
        {onGoHome && (
          <div className="mt-6 text-center">
            <Button
              onClick={onGoHome}
              variant="secondary"
              className="w-full"
            >
              Go to Dashboard
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

/**
 * Network error specific component
 */
export const NetworkError: React.FC<{
  onRetry?: () => void;
  className?: string;
}> = ({ onRetry, className = '' }) => {
  return (
    <div className={`text-center py-8 ${className}`}>
      <svg className="mx-auto h-12 w-12 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
      </svg>
      <h3 className="mt-2 text-sm font-medium text-neutral-900 dark:text-neutral-100">
        Connection Lost
      </h3>
      <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
        Please check your internet connection and try again.
      </p>
      {onRetry && (
        <div className="mt-4">
          <Button onClick={onRetry} size="sm">
            Retry Connection
          </Button>
        </div>
      )}
    </div>
  );
};

/**
 * Empty state component (not exactly an error, but related)
 */
export const EmptyState: React.FC<{
  title: string;
  description?: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  icon?: React.ReactNode;
  className?: string;
}> = ({ title, description, action, icon, className = '' }) => {
  const defaultIcon = (
    <svg className="mx-auto h-12 w-12 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
    </svg>
  );

  return (
    <div className={`text-center py-12 ${className}`}>
      {icon || defaultIcon}
      <h3 className="mt-2 text-sm font-medium text-neutral-900 dark:text-neutral-100">
        {title}
      </h3>
      {description && (
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
          {description}
        </p>
      )}
      {action && (
        <div className="mt-6">
          <Button onClick={action.onClick}>
            {action.label}
          </Button>
        </div>
      )}
    </div>
  );
};