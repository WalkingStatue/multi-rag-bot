/**
 * AuthLayout component
 * 
 * This layout is used for authentication pages like login and register.
 * It provides a centered card layout without the main navigation.
 */
import React from 'react';
import BaseLayout from './BaseLayout';

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
    <BaseLayout className={`flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 ${className}`}>
      <div className="max-w-md w-full space-y-8">
        {(title || subtitle) && (
          <div className="text-center">
            {title && (
              <h2 className="text-3xl font-extrabold text-neutral-900 dark:text-neutral-100">
                {title}
              </h2>
            )}
            {subtitle && (
              <div className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                {subtitle}
              </div>
            )}
          </div>
        )}
        
        <div className="bg-white dark:bg-neutral-900 py-8 px-6 shadow rounded-lg sm:px-10">
          {children}
        </div>
        
        {footer && (
          <div className="mt-6 text-center">
            {footer}
          </div>
        )}
      </div>
    </BaseLayout>
  );
};

export default AuthLayout;