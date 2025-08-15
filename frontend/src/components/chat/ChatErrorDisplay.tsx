/**
 * Component for displaying chat errors with appropriate styling and actions
 */
import React from 'react';
import { ChatError } from '../../types/chat';

interface ChatErrorDisplayProps {
  error: string | ChatError | null;
  onRetry?: () => void;
  onDismiss?: () => void;
  className?: string;
}

export const ChatErrorDisplay: React.FC<ChatErrorDisplayProps> = ({
  error,
  onRetry,
  onDismiss,
  className = ''
}) => {
  if (!error) return null;

  // Handle both string and ChatError types
  const errorMessage = typeof error === 'string' ? error : error.message;
  const errorType = typeof error === 'string' ? 'unknown' : error.type;
  const isRetryable = typeof error === 'string' ? true : error.retryable;
  const retryAfter = typeof error === 'string' ? undefined : error.retryAfter;

  const getErrorIcon = () => {
    switch (errorType) {
      case 'rate_limit':
        return (
          <svg className="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 18.5c-.77.833.192 2.5 1.732 2.5z" />
          </svg>
        );
      case 'api_error':
        return (
          <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
      case 'network_error':
        return (
          <svg className="w-5 h-5 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.141 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
          </svg>
        );
      default:
        return (
          <svg className="w-5 h-5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        );
    }
  };

  const getErrorBgColor = () => {
    switch (errorType) {
      case 'rate_limit':
        return 'bg-yellow-50 border-yellow-200';
      case 'api_error':
        return 'bg-red-50 border-red-200';
      case 'network_error':
        return 'bg-orange-50 border-orange-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className={`rounded-lg border p-4 ${getErrorBgColor()} ${className}`}>
      <div className="flex items-start">
        <div className="flex-shrink-0">
          {getErrorIcon()}
        </div>
        <div className="ml-3 flex-1">
          <p className="text-sm font-medium text-gray-900">
            {errorMessage}
          </p>
          {retryAfter && (
            <p className="mt-1 text-xs text-gray-600">
              Please wait {retryAfter} seconds before trying again.
            </p>
          )}
        </div>
        <div className="ml-4 flex-shrink-0 flex space-x-2">
          {isRetryable && onRetry && (
            <button
              type="button"
              onClick={onRetry}
              className="text-sm font-medium text-blue-600 hover:text-blue-500 focus:outline-none focus:underline"
            >
              Retry
            </button>
          )}
          {onDismiss && (
            <button
              type="button"
              onClick={onDismiss}
              className="text-sm font-medium text-gray-600 hover:text-gray-500 focus:outline-none focus:underline"
            >
              Dismiss
            </button>
          )}
        </div>
      </div>
    </div>
  );
};