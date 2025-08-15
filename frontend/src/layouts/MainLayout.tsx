/**
 * MainLayout component
 * 
 * This layout includes the main navigation and serves as the base for most pages.
 * It supports optional sidebar and different content layouts.
 */
import React, { useState } from 'react';
import { EnhancedNavigation } from '../components/common/EnhancedNavigation';
import BaseLayout from './BaseLayout';

export interface MainLayoutProps {
  children: React.ReactNode;
  className?: string;
  contentClassName?: string;
  hasSidebar?: boolean;
  sidebarContent?: React.ReactNode;
  sidebarWidth?: string;
  fullWidth?: boolean;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  children,
  className = '',
  contentClassName = '',
  hasSidebar = false,
  sidebarContent,
  sidebarWidth = '280px',
  fullWidth = false,
}) => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  return (
    <BaseLayout className={className}>
      {/* Main Navigation */}
      <EnhancedNavigation onToggleSidebar={hasSidebar ? toggleSidebar : undefined} />
      
      {/* Main Content Area */}
      <div className="flex flex-1 pt-16"> {/* pt-16 to account for navbar height */}
        {/* Sidebar */}
        {hasSidebar && (
          <aside 
            className={`fixed top-16 left-0 z-10 h-[calc(100vh-4rem)] bg-white dark:bg-neutral-900 border-r border-neutral-200 dark:border-neutral-800 transition-all duration-300 ${
              isSidebarOpen ? 'translate-x-0' : '-translate-x-full'
            }`}
            style={{ width: sidebarWidth }}
          >
            <div className="h-full overflow-y-auto p-4">
              {sidebarContent}
            </div>
          </aside>
        )}
        
        {/* Main Content */}
        <main 
          className={`flex-1 transition-all duration-300 ${contentClassName}`}
          style={{ 
            marginLeft: hasSidebar && isSidebarOpen ? sidebarWidth : '0',
            width: hasSidebar && isSidebarOpen ? `calc(100% - ${sidebarWidth})` : '100%'
          }}
        >
          <div className={fullWidth ? '' : 'max-w-7xl mx-auto py-6 sm:px-6 lg:px-8'}>
            <div className={fullWidth ? '' : 'px-4 sm:px-0'}>
              {children}
            </div>
          </div>
        </main>
      </div>
    </BaseLayout>
  );
};

export default MainLayout;