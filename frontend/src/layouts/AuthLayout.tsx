/**
 * AuthLayout component
 * 
 * This layout is used for authentication pages like login and register.
 * It provides a centered card layout without the main navigation.
 */
import React from 'react';

export interface AuthLayoutProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: React.ReactNode;
  footer?: React.ReactNode;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({
  children,
  className = '',
  title,
  subtitle,
  footer,
}) => {
  return (
    <div className={`min-h-dvh bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 ${className}`}>
      <div className="max-w-md w-full space-y-8">
        {(title || subtitle) && (
          <div className="text-center">
            {title && (
              <h2 className="text-3xl font-extrabold text-gray-900 dark:text-gray-100">
                {title}
              </h2>
            )}
            {subtitle && (
              <div className="mt-2 text-sm text-gray-600 dark:text-gray-400">
                {subtitle}
              </div>
            )}
          </div>
        )}
        
        <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-sm py-8 px-6 sm:px-10">
          {children}
        </div>
        
        {footer && (
          <div className="mt-6 text-center">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
};

export default AuthLayout;