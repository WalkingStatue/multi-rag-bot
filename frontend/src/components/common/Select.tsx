/**
 * Select component with consistent styling and dark mode support
 */
import React, { SelectHTMLAttributes } from 'react';
import { ChevronDownIcon } from '@heroicons/react/24/outline';

export interface SelectProps extends Omit<SelectHTMLAttributes<HTMLSelectElement>, 'size'> {
  label?: string;
  error?: string;
  helperText?: string;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'outline';
}

export const Select: React.FC<SelectProps> = ({
  label,
  error,
  helperText,
  size = 'md',
  variant = 'default',
  className = '',
  children,
  ...props
}) => {
  const sizeClasses = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-3 py-2 text-sm',
    lg: 'px-4 py-3 text-base'
  };

  const baseClasses = `
    w-full rounded-md border appearance-none pr-10
    bg-white dark:bg-gray-800 
    text-gray-900 dark:text-gray-100
    focus:outline-none focus:ring-2 focus:ring-offset-0
    disabled:opacity-50 disabled:cursor-not-allowed
    transition-colors duration-200
  `;

  const variantClasses = {
    default: `
      border-gray-300 dark:border-gray-600
      focus:ring-primary-500 dark:focus:ring-primary-400 
      focus:border-primary-500 dark:focus:border-primary-400
    `,
    outline: `
      border-gray-300 dark:border-gray-600
      focus:ring-primary-500 dark:focus:ring-primary-400 
      focus:border-primary-500 dark:focus:border-primary-400
    `
  };

  const errorClasses = error ? 'border-danger-600 dark:border-danger-600 focus:ring-danger-600 dark:focus:ring-danger-600' : '';

  const selectClasses = `
    ${baseClasses}
    ${sizeClasses[size]}
    ${variantClasses[variant]}
    ${errorClasses}
    ${className}
  `.trim().replace(/\s+/g, ' ');

  return (
    <div className="w-full">
      {label && (
        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
          {label}
        </label>
      )}
      <div className="relative">
        <select
          className={selectClasses}
          {...props}
        >
          {children}
        </select>
        <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
          <ChevronDownIcon className="h-4 w-4 text-gray-400 dark:text-gray-500" />
        </div>
      </div>
      {error && (
        <p className="mt-1 text-sm text-danger-600 dark:text-danger-600">{error}</p>
      )}
      {helperText && !error && (
        <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">{helperText}</p>
      )}
    </div>
  );
};

export default Select;