/**
 * Enhanced Page Layout Component
 * 
 * Provides consistent page structure with standardized loading, error, and content states.
 * Combines layout management with state handling for better developer experience.
 */
import React from 'react';
import { MainLayout, MainLayoutProps } from '../../layouts/MainLayout';
import { PageLoading, PageError, PageEmpty } from './PageStates';

export interface PageLayoutProps extends Omit<MainLayoutProps, 'children'> {
  children?: React.ReactNode;
  
  // State management
  isLoading?: boolean;
  error?: string | null;
  isEmpty?: boolean;
  
  // Loading state
  loadingMessage?: string;
  
  // Error state
  errorTitle?: string;
  errorMessage?: string;
  errorActionLabel?: string;
  onErrorAction?: () => void;
  
  // Empty state
  emptyTitle?: string;
  emptyMessage?: string;
  emptyActionLabel?: string;
  onEmptyAction?: () => void;
  emptyIcon?: React.ReactNode;
  
  // Layout behavior
  showStatesInLayout?: boolean; // Whether to wrap states in MainLayout
}

export const PageLayout: React.FC<PageLayoutProps> = ({
  children,
  isLoading = false,
  error = null,
  isEmpty = false,
  loadingMessage = 'Loading...',
  errorTitle = 'Something went wrong',
  errorMessage,
  errorActionLabel = 'Try again',
  onErrorAction,
  emptyTitle = 'No data found',
  emptyMessage = 'There is no data to display at the moment.',
  emptyActionLabel,
  onEmptyAction,
  emptyIcon,
  showStatesInLayout = true,
  ...layoutProps
}) => {
  // Determine what to render
  const renderContent = () => {
    if (isLoading) {
      return <PageLoading message={loadingMessage} />;
    }
    
    if (error) {
      return (
        <PageError
          title={errorTitle}
          message={errorMessage || error}
          actionLabel={errorActionLabel}
          onAction={onErrorAction}
        />
      );
    }
    
    if (isEmpty) {
      return (
        <PageEmpty
          title={emptyTitle}
          message={emptyMessage}
          actionLabel={emptyActionLabel}
          onAction={onEmptyAction}
          icon={emptyIcon}
        />
      );
    }
    
    return children;
  };

  const content = renderContent();

  // If we're showing a state and showStatesInLayout is false, render without MainLayout wrapper
  if (!showStatesInLayout && (isLoading || error || isEmpty)) {
    return <>{content}</>;
  }

  // Otherwise, wrap in MainLayout
  return (
    <MainLayout {...layoutProps}>
      {content}
    </MainLayout>
  );
};

export default PageLayout;