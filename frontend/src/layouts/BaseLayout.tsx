/**
 * BaseLayout component
 * 
 * This is the foundation for all layouts in the application.
 * It provides basic structure and common functionality.
 */
import React from 'react';

export interface BaseLayoutProps {
  children: React.ReactNode;
  className?: string;
  id?: string;
}

export const BaseLayout: React.FC<BaseLayoutProps> = ({
  children,
  className = '',
  id,
}) => {
  return (
    <div 
      id={id}
      className={`min-h-screen bg-neutral-50 dark:bg-[var(--bg)] transition-colors duration-200 ${className}`}
    >
      {children}
    </div>
  );
};

export default BaseLayout;