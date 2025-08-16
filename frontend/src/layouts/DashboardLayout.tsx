/**
 * Dashboard Layout Component
 * 
 * Alias to MainLayout for backward compatibility.
 * Use MainLayout directly for new components.
 */
import React from 'react';
import { MainLayout, MainLayoutProps } from './MainLayout';

export interface DashboardLayoutProps extends MainLayoutProps {
  noPadding?: boolean;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  children,
  noPadding = false,
  ...props
}) => {
  return (
    <MainLayout {...props}>
      {noPadding ? (
        children
      ) : (
        <div className="rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 shadow-sm p-6 sm:p-8">
          {children}
        </div>
      )}
    </MainLayout>
  );
};

export default DashboardLayout;