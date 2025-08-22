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
    <div className={`min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-neutral-950 dark:via-neutral-900 dark:to-purple-950/20 text-neutral-900 dark:text-neutral-100 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8 ${className}`}>
      <div className="w-full max-w-md mx-auto">
        {/* Background decorations */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-40 -right-40 w-80 h-80 rounded-full bg-blue-100 dark:bg-blue-900/20 opacity-50 blur-3xl"></div>
          <div className="absolute -bottom-40 -left-40 w-80 h-80 rounded-full bg-purple-100 dark:bg-purple-900/20 opacity-50 blur-3xl"></div>
        </div>
        
        <div className="relative">
          {(title || subtitle) && (
            <div className="text-center mb-8">
              {title && (
                <h2 className="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">
                  {title}
                </h2>
              )}
              {subtitle && (
                <div className="text-neutral-600 dark:text-neutral-400">
                  {subtitle}
                </div>
              )}
            </div>
          )}
          
          {children}
          
          {footer && (
            <div className="mt-8 text-center">
              {footer}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default AuthLayout;