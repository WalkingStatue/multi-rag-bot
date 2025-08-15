/**
 * Container component
 * 
 * A container component for consistent content width and padding.
 */
import React from 'react';

export interface ContainerProps {
  children: React.ReactNode;
  className?: string;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  padding?: 'none' | 'sm' | 'md' | 'lg';
  centered?: boolean;
}

export const Container: React.FC<ContainerProps> = ({
  children,
  className = '',
  size = 'lg',
  padding = 'md',
  centered = true,
}) => {
  // Size classes
  const sizeClasses = {
    sm: 'max-w-3xl',
    md: 'max-w-5xl',
    lg: 'max-w-7xl',
    xl: 'max-w-screen-2xl',
    full: 'max-w-full',
  };
  
  // Padding classes
  const paddingClasses = {
    none: 'px-0',
    sm: 'px-4 sm:px-6',
    md: 'px-4 sm:px-6 lg:px-8',
    lg: 'px-6 sm:px-8 lg:px-12',
  };
  
  // Combine classes
  const containerClasses = [
    sizeClasses[size],
    paddingClasses[padding],
    centered ? 'mx-auto' : '',
    className,
  ].filter(Boolean).join(' ');
  
  return (
    <div className={containerClasses}>
      {children}
    </div>
  );
};

export default Container;