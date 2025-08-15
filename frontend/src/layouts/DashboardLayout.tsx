/**
 * DashboardLayout component
 * 
 * This layout extends the MainLayout with specific dashboard features.
 * It includes a sidebar with navigation and content area with header.
 */
import React, { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';
import MainLayout from './MainLayout';
import { EnhancedPageHeader } from '../components/common/EnhancedPageHeader';

export interface DashboardLayoutProps {
  children: React.ReactNode;
  className?: string;
  title: string;
  subtitle?: string;
  actions?: React.ReactNode;
  showBackButton?: boolean;
  onBackClick?: () => void;
}

export const DashboardLayout: React.FC<DashboardLayoutProps> = ({
  children,
  className = '',
  title,
  subtitle,
  actions,
  showBackButton = false,
  onBackClick,
}) => {
  const location = useLocation();
  const [activeSection, setActiveSection] = useState('');

  // Update active section based on URL
  useEffect(() => {
    const path = location.pathname;
    const search = new URLSearchParams(location.search);
    const view = search.get('view');
    
    if (path === '/dashboard') {
      if (view === 'bots') {
        setActiveSection('bots');
      } else if (view === 'api-keys') {
        setActiveSection('api-keys');
      } else {
        setActiveSection('dashboard');
      }
    } else if (path.includes('/bots')) {
      setActiveSection('bots');
    } else if (path.includes('/profile')) {
      setActiveSection('profile');
    }
  }, [location]);

  // Sidebar navigation items
  const sidebarNavItems = [
    {
      name: 'Dashboard',
      href: '/dashboard',
      icon: (
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      ),
      section: 'dashboard',
    },
    {
      name: 'Bots',
      href: '/dashboard?view=bots',
      icon: (
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      ),
      section: 'bots',
    },
    {
      name: 'API Keys',
      href: '/dashboard?view=api-keys',
      icon: (
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
        </svg>
      ),
      section: 'api-keys',
    },
    {
      name: 'Profile',
      href: '/profile',
      icon: (
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      ),
      section: 'profile',
    },
  ];

  // Render sidebar content
  const renderSidebarContent = () => (
    <div className="space-y-6">
      <div className="space-y-1">
        {sidebarNavItems.map((item) => (
          <Link
            key={item.name}
            to={item.href}
            className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
              activeSection === item.section
                ? 'text-primary-700 dark:text-primary-300 bg-primary-50 dark:bg-primary-950/40'
                : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50 dark:text-neutral-300 dark:hover:text-neutral-100 dark:hover:bg-neutral-800/50'
            }`}
          >
            <span className="mr-3">{item.icon}</span>
            {item.name}
          </Link>
        ))}
      </div>
    </div>
  );

  return (
    <MainLayout 
      className={className}
      hasSidebar={true}
      sidebarContent={renderSidebarContent()}
    >
      <div className="py-6">
        <EnhancedPageHeader
          title={title}
          subtitle={subtitle}
          actions={actions}
          showBackButton={showBackButton}
          onBackClick={onBackClick}
        />
        <div className="mt-6">
          {children}
        </div>
      </div>
    </MainLayout>
  );
};

export default DashboardLayout;