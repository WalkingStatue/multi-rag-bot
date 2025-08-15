/**
 * Card component
 * 
 * A versatile card component with various style options.
 */
import React from 'react';

export interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  footer?: React.ReactNode;
  headerActions?: React.ReactNode;
  variant?: 'default' | 'outline' | 'filled';
  padding?: 'none' | 'small' | 'medium' | 'large';
  hover?: boolean;
  onClick?: () => void;
}

export const Card: React.FC<CardProps> = ({
  children,
  className = '',
  title,
  subtitle,
  footer,
  headerActions,
  variant = 'default',
  padding = 'medium',
  hover = false,
  onClick,
}) => {
  // Base classes
  const baseClasses = 'rounded-lg transition-all duration-200';
  
  // Variant classes
  const variantClasses = {
    default: 'bg-white dark:bg-neutral-900 shadow',
    outline: 'bg-white dark:bg-neutral-900 border border-neutral-200 dark:border-neutral-800',
    filled: 'bg-neutral-50 dark:bg-neutral-800',
  };
  
  // Padding classes
  const paddingClasses = {
    none: '',
    small: 'p-3',
    medium: 'p-5',
    large: 'p-6',
  };
  
  // Hover classes
  const hoverClasses = hover 
    ? 'hover:shadow-md hover:border-neutral-300 dark:hover:border-neutral-700 cursor-pointer' 
    : '';
  
  // Combine classes
  const cardClasses = [
    baseClasses,
    variantClasses[variant],
    onClick || hover ? hoverClasses : '',
    className,
  ].filter(Boolean).join(' ');
  
  // Header and content padding
  const headerPadding = padding !== 'none' ? paddingClasses[padding] : 'p-5';
  const contentPadding = padding !== 'none' ? paddingClasses[padding] : 'px-5 py-3';
  const footerPadding = padding !== 'none' ? paddingClasses[padding] : 'p-5';
  
  // If content has padding but header exists, adjust top padding
  const contentClasses = (title || subtitle) && padding !== 'none' 
    ? contentPadding.replace('pt-5', 'pt-0').replace('py-3', 'py-3 pt-0') 
    : contentPadding;

  return (
    <div 
      className={cardClasses}
      onClick={onClick}
    >
      {/* Card Header */}
      {(title || subtitle || headerActions) && (
        <div className={`${headerPadding} ${padding !== 'none' ? 'pb-3' : ''}`}>
          <div className="flex justify-between items-start">
            <div>
              {title && (
                <h3 className="text-lg font-medium text-neutral-900 dark:text-neutral-100">
                  {title}
                </h3>
              )}
              {subtitle && (
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                  {subtitle}
                </p>
              )}
            </div>
            {headerActions && (
              <div className="ml-4">
                {headerActions}
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Card Content */}
      <div className={contentClasses}>
        {children}
      </div>
      
      {/* Card Footer */}
      {footer && (
        <div className={`border-t border-neutral-200 dark:border-neutral-800 ${footerPadding} ${padding !== 'none' ? 'mt-3' : ''}`}>
          {footer}
        </div>
      )}
    </div>
  );
};

export default Card;