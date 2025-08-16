/**
 * Chat Layout Component
 * 
 * Specialized full-screen layout for chat interfaces.
 * Uses the canonical layout pattern with chat-specific header.
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { TopNavigation } from '../components/common/TopNavigation';

export interface ChatLayoutProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
  subtitle?: string;
  rightContent?: React.ReactNode;
  onBackClick?: () => void;
}

export const ChatLayout: React.FC<ChatLayoutProps> = ({
  children,
  className = '',
  title,
  subtitle,
  rightContent,
  onBackClick,
}) => {
  const navigate = useNavigate();

  const handleBackClick = () => {
    if (onBackClick) {
      onBackClick();
    } else {
      navigate('/dashboard');
    }
  };

  return (
    <div className={`min-h-dvh bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 h-screen flex flex-col ${className}`}>
      {/* Top Navigation */}
      <TopNavigation />
      
      {/* Chat Header */}
      <div className="bg-white/95 dark:bg-gray-900/95 backdrop-blur-sm border-b border-gray-200/50 dark:border-gray-800/50 px-4 sm:px-6 py-4 flex-shrink-0">
        <div className="mx-auto max-w-screen-2xl">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4 min-w-0 flex-1">
              <button
                onClick={handleBackClick}
                className="p-2 rounded-lg text-gray-500 hover:text-gray-700 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-gray-800/50 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-all duration-150 flex-shrink-0"
                aria-label="Go back"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                </svg>
              </button>
              <div className="min-w-0 flex-1">
                <h1 className="text-lg sm:text-xl font-semibold text-gray-900 dark:text-gray-100 truncate">
                  {title}
                </h1>
                {subtitle && (
                  <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                    {subtitle}
                  </p>
                )}
              </div>
            </div>
            
            {/* Right content area (search, actions, etc.) */}
            {rightContent && (
              <div className="flex items-center space-x-3 flex-shrink-0 ml-4">
                {rightContent}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Chat content area */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {children}
      </div>
    </div>
  );
};

export default ChatLayout;