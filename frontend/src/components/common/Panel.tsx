/**
 * Panel component
 * 
 * A panel component for creating sections with headers.
 */
import React from 'react';

export interface PanelProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  headerActions?: React.ReactNode;
  footer?: React.ReactNode;
  variant?: 'default' | 'outline' | 'filled';
  padding?: 'none' | 'small' | 'medium' | 'large';
  collapsible?: boolean;
  defaultCollapsed?: boolean;
}

export const Panel: React.FC<PanelProps> = ({
  children,
  className = '',
  title,
  subtitle,
  headerActions,
  footer,
  variant = 'default',
  padding = 'medium',
  collapsible = false,
  defaultCollapsed = false,
}) => {
  const [isCollapsed, setIsCollapsed] = React.useState(defaultCollapsed);

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
  
  // Combine classes
  const panelClasses = [
    baseClasses,
    variantClasses[variant],
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

  const toggleCollapse = () => {
    if (collapsible) {
      setIsCollapsed(!isCollapsed);
    }
  };

  return (
    <div className={panelClasses}>
      {/* Panel Header */}
      {(title || subtitle || headerActions) && (
        <div 
          className={`${headerPadding} ${padding !== 'none' ? 'pb-3' : ''} border-b border-neutral-200 dark:border-neutral-800 ${collapsible ? 'cursor-pointer' : ''}`}
          onClick={toggleCollapse}
        >
          <div className="flex justify-between items-start">
            <div className="flex items-center">
              {collapsible && (
                <button 
                  className="mr-2 text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:hover:text-neutral-300"
                  aria-label={isCollapsed ? 'Expand' : 'Collapse'}
                >
                  <svg 
                    className={`h-5 w-5 transition-transform duration-200 ${isCollapsed ? 'rotate-180' : ''}`} 
                    fill="none" 
                    viewBox="0 0 24 24" 
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              )}
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
            </div>
            {headerActions && (
              <div className="ml-4">
                {headerActions}
              </div>
            )}
          </div>
        </div>
      )}
      
      {/* Panel Content */}
      {!isCollapsed && (
        <div className={contentClasses}>
          {children}
        </div>
      )}
      
      {/* Panel Footer */}
      {!isCollapsed && footer && (
        <div className={`border-t border-neutral-200 dark:border-neutral-800 ${footerPadding} ${padding !== 'none' ? 'mt-3' : ''}`}>
          {footer}
        </div>
      )}
    </div>
  );
};

export default Panel;