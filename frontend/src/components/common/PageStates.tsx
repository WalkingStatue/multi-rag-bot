/**
 * Standardized page state components for loading, error, and empty states
 */
import React from 'react';
import { ExclamationTriangleIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import { Button } from './Button';
import { LoadingSpinner } from './LoadingSpinner';

export interface PageLoadingProps {
  message?: string;
  className?: string;
}

export const PageLoading: React.FC<PageLoadingProps> = ({ 
  message = 'Loading...', 
  className = '' 
}) => {
  return (
    <div className={`flex items-center justify-center min-h-[400px] ${className}`}>
      <div className="text-center">
        <LoadingSpinner size="lg" className="mx-auto mb-4" />
        <p className="text-neutral-600 dark:text-neutral-400">{message}</p>
      </div>
    </div>
  );
};

export interface PageErrorProps {
  title?: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const PageError: React.FC<PageErrorProps> = ({
  title = 'Something went wrong',
  message = 'An unexpected error occurred. Please try again.',
  actionLabel = 'Try again',
  onAction,
  className = ''
}) => {
  return (
    <div className={`flex items-center justify-center min-h-[400px] ${className}`}>
      <div className="text-center max-w-md">
        <div className="w-16 h-16 mx-auto mb-4 bg-danger-100 dark:bg-danger-900/30 rounded-full flex items-center justify-center">
          <ExclamationTriangleIcon className="w-8 h-8 text-danger-600 dark:text-danger-400" />
        </div>
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
          {title}
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400 mb-6">
          {message}
        </p>
        {onAction && (
          <Button onClick={onAction} variant="primary">
            <ArrowPathIcon className="w-4 h-4 mr-2" />
            {actionLabel}
          </Button>
        )}
      </div>
    </div>
  );
};

export interface PageEmptyProps {
  title?: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
  className?: string;
}

export const PageEmpty: React.FC<PageEmptyProps> = ({
  title = 'No data found',
  message = 'There is no data to display at the moment.',
  actionLabel,
  onAction,
  icon,
  className = ''
}) => {
  return (
    <div className={`flex items-center justify-center min-h-[400px] ${className}`}>
      <div className="text-center max-w-md">
        {icon && (
          <div className="w-16 h-16 mx-auto mb-4 text-neutral-400 dark:text-neutral-500">
            {icon}
          </div>
        )}
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
          {title}
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400 mb-6">
          {message}
        </p>
        {onAction && actionLabel && (
          <Button onClick={onAction} variant="primary">
            {actionLabel}
          </Button>
        )}
      </div>
    </div>
  );
};

export interface PageNotFoundProps {
  title?: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
  className?: string;
}

export const PageNotFound: React.FC<PageNotFoundProps> = ({
  title = 'Page not found',
  message = 'The page you are looking for does not exist.',
  actionLabel = 'Go back',
  onAction,
  className = ''
}) => {
  return (
    <div className={`flex items-center justify-center min-h-[400px] ${className}`}>
      <div className="text-center max-w-md">
        <div className="text-6xl font-bold text-neutral-300 dark:text-neutral-600 mb-4">
          404
        </div>
        <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">
          {title}
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400 mb-6">
          {message}
        </p>
        {onAction && (
          <Button onClick={onAction} variant="primary">
            {actionLabel}
          </Button>
        )}
      </div>
    </div>
  );
};