/**
 * Error boundary component to catch and display errors gracefully
 */
import React, { Component, ErrorInfo, ReactNode } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error boundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div className="min-h-screen flex items-center justify-center bg-neutral-50 dark:bg-[var(--bg)]">
          <div className="max-w-md w-full bg-white dark:bg-neutral-900 shadow-lg rounded-lg p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg
                  className="h-8 w-8 text-red-400"
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
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-neutral-800 dark:text-neutral-100">
                  Something went wrong
                </h3>
                <div className="mt-2 text-sm text-neutral-500 dark:text-neutral-400">
                  <p>
                    An unexpected error occurred. Please refresh the page and try again.
                  </p>
                  {this.state.error && (
                    <details className="mt-2">
                       <summary className="cursor-pointer text-xs text-neutral-400">
                        Error details
                      </summary>
                       <pre className="mt-1 text-xs text-neutral-400 whitespace-pre-wrap">
                        {this.state.error.message}
                      </pre>
                    </details>
                  )}
                </div>
              </div>
            </div>
            <div className="mt-4">
              <button
                onClick={() => window.location.reload()}
                className="w-full bg-primary-600 text-white px-4 py-2 rounded-md text-sm font-medium hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
              >
                Refresh Page
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

// Simple error fallback component
export const ChatErrorFallback: React.FC<{ error?: string; onRetry?: () => void }> = ({
  error,
  onRetry
}) => (
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
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
        />
      </svg>
      <h3 className="mt-2 text-sm font-medium text-neutral-900 dark:text-neutral-100">Chat Error</h3>
      <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
        {error || 'Unable to load chat. Please try again.'}
      </p>
      {onRetry && (
        <div className="mt-4">
          <button
            onClick={onRetry}
            className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            Try Again
          </button>
        </div>
      )}
    </div>
  </div>
);