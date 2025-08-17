/**
 * Unified Main Layout Component
 * 
 * Single layout component that handles all page layouts with consistent styling.
 * Supports different content widths, padding options, and page headers.
 */
import React from 'react';
import { TopNavigation } from '../components/common/TopNavigation';
import { ArrowLeftIcon } from '@heroicons/react/24/outline';

export interface MainLayoutProps {
  children: React.ReactNode;
  className?: string;
  contentClassName?: string;
  
  // Layout options
  fullWidth?: boolean;
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  
  // Page header
  title?: string;
  subtitle?: string;
  actions?: React.ReactNode;
  showBackButton?: boolean;
  onBackClick?: () => void;
  
  // Special layouts
  centered?: boolean;
  noHeader?: boolean;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  children,
  className = '',
  contentClassName = '',
  fullWidth = false,
  maxWidth = '2xl',
  padding = 'md',
  title,
  subtitle,
  actions,
  showBackButton = false,
  onBackClick,
  centered = false,
  noHeader = false,
}) => {
  // Max width classes
  const maxWidthClasses = {
    sm: 'max-w-3xl',
    md: 'max-w-5xl',
    lg: 'max-w-6xl',
    xl: 'max-w-7xl',
    '2xl': 'max-w-screen-2xl',
    full: 'max-w-full',
  };

  // Padding classes
  const paddingClasses = {
    none: 'px-0',
    sm: 'px-4 sm:px-6',
    md: 'px-4 sm:px-6 lg:px-8',
    lg: 'px-6 sm:px-8 lg:px-12',
  };

  // Container classes
  const containerClasses = [
    fullWidth ? 'w-full' : maxWidthClasses[maxWidth],
    fullWidth ? '' : 'mx-auto',
    paddingClasses[padding],
    'py-6',
  ].filter(Boolean).join(' ');

  return (
    <div className={`min-h-dvh bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 ${className}`}>
      {/* Top Navigation */}
      <TopNavigation />
      
      {/* Main Content Area */}
      <main className={contentClassName}>
        <div className={containerClasses}>
          {/* Page Header */}
          {!noHeader && (title || subtitle || actions || showBackButton) && (
            <div className="mb-8">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  {showBackButton && (
                    <button
                      onClick={onBackClick}
                      className="p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all duration-150"
                      aria-label="Go back"
                    >
                      <ArrowLeftIcon className="w-5 h-5" />
                    </button>
                  )}
                  <div>
                    {title && (
                      <h1 className="text-2xl md:text-3xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
                        {title}
                      </h1>
                    )}
                    {subtitle && (
                      <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                        {subtitle}
                      </p>
                    )}
                  </div>
                </div>
                {actions && (
                  <div className="flex items-center space-x-3">
                    {actions}
                  </div>
                )}
              </div>
            </div>
          )}
          
          {/* Page Content */}
          <div className={centered ? 'flex items-center justify-center min-h-[60vh]' : ''}>
            {children}
          </div>
        </div>
      </main>
    </div>
  );
};

export default MainLayout;