/**
 * Enhanced Page Header component
 * 
 * This component extends the original PageHeader with additional features
 * like a back button and more flexible layout options.
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';

export interface EnhancedPageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  className?: string;
  showBackButton?: boolean;
  onBackClick?: () => void;
  backButtonLabel?: string;
}

export const EnhancedPageHeader: React.FC<EnhancedPageHeaderProps> = ({ 
  title, 
  subtitle, 
  actions, 
  className = '',
  showBackButton = false,
  onBackClick,
  backButtonLabel = 'Back'
}) => {
  const navigate = useNavigate();

  const handleBackClick = () => {
    if (onBackClick) {
      onBackClick();
    } else {
      navigate(-1);
    }
  };

  return (
    <div className={`mb-8 ${className}`}>
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-center">
          {showBackButton && (
            <button
              onClick={handleBackClick}
              className="mr-4 p-1 rounded-full text-neutral-500 hover:text-neutral-900 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:text-neutral-100 dark:hover:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-primary-500"
              aria-label={backButtonLabel}
              title={backButtonLabel}
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
          )}
          <div>
            <h2 className="text-3xl font-bold text-neutral-900 dark:text-neutral-100">{title}</h2>
            {subtitle && <p className="text-neutral-600 dark:text-neutral-400 mt-1">{subtitle}</p>}
          </div>
        </div>
        {actions && <div className="flex items-center gap-2">{actions}</div>}
      </div>
    </div>
  );
};

export default EnhancedPageHeader;