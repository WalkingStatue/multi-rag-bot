/**
 * Reusable Input component
 */
import React, { forwardRef } from 'react';

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, helperText, className = '', ...props }, ref) => {
    const inputClasses = [
      'block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 sm:text-sm transition-colors duration-150',
      'bg-white text-neutral-900 placeholder-neutral-500',
      'dark:bg-neutral-800 dark:text-neutral-100 dark:placeholder-neutral-400',
      error
        ? 'border-danger-300 text-danger-700 focus:ring-danger-500 focus:border-danger-500 dark:border-danger-600 dark:text-danger-300 dark:focus:ring-danger-400 dark:focus:border-danger-400'
        : 'border-neutral-300 dark:border-neutral-600 focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400',
      className,
    ].join(' ');

    return (
      <div className="space-y-1">
        {label && (
          <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
            {label}
          </label>
        )}
        <input
          ref={ref}
          className={inputClasses}
          {...props}
        />
        {error && (
          <p className="text-sm text-danger-600">{error}</p>
        )}
        {helperText && !error && (
          <p className="text-sm text-neutral-500 dark:text-neutral-400">{helperText}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';