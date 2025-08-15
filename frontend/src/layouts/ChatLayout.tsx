/**
 * ChatLayout component
 * 
 * This layout is used for the chat interface.
 * It provides a full-screen layout with a specialized header.
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import BaseLayout from './BaseLayout';

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
    <BaseLayout className={`h-screen flex flex-col ${className}`}>
      {/* Header */}
      <div className="bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={handleBackClick}
              className="text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>
            <div>
              <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">{title}</h1>
              {subtitle && <p className="text-sm text-neutral-500 dark:text-neutral-400">{subtitle}</p>}
            </div>
          </div>
          
          {/* Right content area (search, actions, etc.) */}
          {rightContent && (
            <div className="flex items-center space-x-4">
              {rightContent}
            </div>
          )}
        </div>
      </div>

      {/* Chat content area */}
      <div className="flex-1 min-h-0 overflow-hidden">
        {children}
      </div>
    </BaseLayout>
  );
};

export default ChatLayout;