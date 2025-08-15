/**
 * Enhanced Navigation component with sidebar toggle support
 */
import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Button } from './Button';
import { NotificationSystem } from './NotificationSystem';
import { useTheme } from '../../hooks/useTheme';

interface EnhancedNavigationProps {
  className?: string;
  onToggleSidebar?: () => void;
}

export const EnhancedNavigation: React.FC<EnhancedNavigationProps> = ({ 
  className = '',
  onToggleSidebar
}) => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { isDark, toggleTheme } = useTheme();

  const handleLogout = () => {
    logout();
  };

  const isActive = (href: string) => {
    const currentPath = location.pathname;
    const currentSearch = new URLSearchParams(location.search);
    try {
      const url = new URL(href, window.location.origin);
      const itemPath = url.pathname;
      const itemSearch = new URLSearchParams(url.search);

      // Path must match for active
      if (itemPath !== currentPath) return false;

      // If item has search params, all must match
      let hasParams = false;
      for (const [key, value] of itemSearch.entries()) {
        hasParams = true;
        if (currentSearch.get(key) !== value) return false;
      }

      // If item has no params and we're on /dashboard with a view param, do not mark as Dashboard
      if (!hasParams && currentPath === '/dashboard' && currentSearch.get('view')) {
        return false;
      }

      return true;
    } catch {
      // Fallback: simple equality
      return currentPath === href || currentPath.startsWith(href + '/');
    }
  };

  const navigationItems = [
    {
      name: 'Dashboard',
      href: '/dashboard',
      icon: (
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z" />
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 5a2 2 0 012-2h4a2 2 0 012 2v6H8V5z" />
        </svg>
      ),
    },
    {
      name: 'Bots',
      href: '/dashboard?view=bots',
      icon: (
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
      ),
    },
    {
      name: 'API Keys',
      href: '/dashboard?view=api-keys',
      icon: (
        <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
        </svg>
      ),
    },
  ];

  return (
    <nav className={`fixed top-0 left-0 right-0 z-20 bg-white/80 dark:bg-neutral-900/70 backdrop-blur supports-[backdrop-filter]:bg-white/60 shadow transition-colors duration-200 ${className}`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo and Brand */}
          <div className="flex items-center">
            {/* Sidebar Toggle Button (if onToggleSidebar is provided) */}
            {onToggleSidebar && (
              <button
                onClick={onToggleSidebar}
                className="mr-2 p-2 rounded-md text-neutral-500 hover:text-neutral-900 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:text-neutral-100 dark:hover:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500"
                aria-label="Toggle sidebar"
              >
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              </button>
            )}
            
            <Link to="/dashboard" className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-8 w-8 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="ml-3">
                <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
                  Multi-Bot RAG Platform
                </h1>
              </div>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden md:flex md:items-center md:space-x-6">
            {/* Navigation Links */}
            <div className="flex items-center space-x-1">
              {navigationItems.map((item) => (
                <Link
                  key={item.name}
                  to={item.href}
                   className={`flex items-center px-3 py-2 rounded-md text-sm font-medium transition-colors ${
                    isActive(item.href)
                      ? 'text-primary-700 dark:text-primary-300 bg-primary-50 dark:bg-primary-950/40'
                      : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50 dark:text-neutral-300 dark:hover:text-neutral-100 dark:hover:bg-neutral-800/50'
                  }`}
                >
                  <span className="mr-2">{item.icon}</span>
                  {item.name}
                </Link>
              ))}
            </div>

            {/* Divider */}
            <div className="h-6 w-px bg-neutral-200 dark:bg-neutral-700"></div>

            {/* User Menu and Notifications */}
            <div className="flex items-center space-x-4">
              {/* Notifications */}
              <NotificationSystem />
              
              {/* User Info */}
              <div className="flex items-center space-x-3">
                <div className="text-right">
                  <div className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                    {user?.full_name || user?.username}
                  </div>
                  <div className="text-xs text-neutral-500 dark:text-neutral-400">
                    {user?.email}
                  </div>
                </div>
                
                {/* User Avatar */}
                <Link to="/profile" className="flex-shrink-0">
                  {user?.avatar_url ? (
                    <img
                      src={user.avatar_url}
                      alt={user?.full_name || user?.username || 'User'}
                      className="h-8 w-8 rounded-full object-cover ring-2 ring-transparent hover:ring-primary-500"
                    />
                  ) : (
                    <div className="h-8 w-8 rounded-full bg-primary-600 flex items-center justify-center hover:ring-2 hover:ring-primary-500">
                      <span className="text-sm font-medium text-white">
                        {(user?.full_name || user?.username || 'U').charAt(0).toUpperCase()}
                      </span>
                    </div>
                  )}
                </Link>

                {/* Theme toggle */}
                <button
                  onClick={toggleTheme}
                  className="rounded-md p-2 text-neutral-600 hover:text-neutral-900 hover:bg-neutral-100 focus:outline-none focus:ring-2 focus:ring-primary-500 dark:text-neutral-300 dark:hover:text-neutral-100 dark:hover:bg-neutral-800"
                  aria-label="Toggle theme"
                  title="Toggle theme"
                >
                  {isDark ? (
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20"><path d="M17.293 13.293A8 8 0 016.707 2.707 8.001 8.001 0 1017.293 13.293z"/></svg>
                  ) : (
                    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-4 7a1 1 0 011-1h0a1 1 0 110 2h0a1 1 0 01-1-1zM4.222 4.222a1 1 0 011.415 0l.707.707a1 1 0 01-1.414 1.415l-.708-.708a1 1 0 010-1.414zM16.97 16.97a1 1 0 01-1.415 0l-.707-.707a1 1 0 011.414-1.415l.708.708a1 1 0 010 1.414zM2 11a1 1 0 100-2h-1a1 1 0 100 2h1zm18 0a1 1 0 100-2h-1a1 1 0 100 2h1zM4.222 15.778a1 1 0 010-1.415l.708-.707a1 1 0 111.414 1.414l-.707.708a1 1 0 01-1.415 0zM15.778 4.222a1 1 0 00-1.415 0l-.707.708a1 1 0 101.414 1.414l.708-.707a1 1 0 000-1.415z" clipRule="evenodd"/></svg>
                  )}
                </button>

                {/* Logout Button */}
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleLogout}
                >
                  Sign out
                </Button>
              </div>
            </div>
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center space-x-4">
            {/* Notifications for mobile */}
            <NotificationSystem />
            
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="inline-flex items-center justify-center p-2 rounded-md text-neutral-400 hover:text-neutral-500 hover:bg-neutral-100 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-primary-500 dark:text-neutral-300 dark:hover:text-neutral-100 dark:hover:bg-neutral-800"
            >
              <span className="sr-only">Open main menu</span>
              {isMobileMenuOpen ? (
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden">
          <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3 bg-white dark:bg-neutral-900 border-t border-neutral-200 dark:border-neutral-800">
            {navigationItems.map((item) => (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center px-3 py-2 rounded-md text-base font-medium transition-colors ${
                  isActive(item.href)
                    ? 'bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300'
                    : 'text-neutral-600 hover:text-neutral-900 hover:bg-neutral-50 dark:text-neutral-300 dark:hover:text-neutral-100 dark:hover:bg-neutral-800/50'
                }`}
                onClick={() => setIsMobileMenuOpen(false)}
              >
                <span className="mr-3">{item.icon}</span>
                {item.name}
              </Link>
            ))}
            
            {/* Mobile user info */}
            <div className="px-3 py-3 border-t border-neutral-200 dark:border-neutral-800">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="h-8 w-8 rounded-full bg-primary-600 flex items-center justify-center">
                    <span className="text-sm font-medium text-white">
                      {(user?.full_name || user?.username || 'U').charAt(0).toUpperCase()}
                    </span>
                  </div>
                </div>
                <div className="ml-3">
                  <div className="text-base font-medium text-neutral-800 dark:text-neutral-100">
                    {user?.full_name || user?.username}
                  </div>
                  <div className="text-sm text-neutral-500 dark:text-neutral-400">
                    {user?.email}
                  </div>
                </div>
              </div>
              <div className="mt-3">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handleLogout}
                  className="w-full"
                >
                  Sign out
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </nav>
  );
};

export default EnhancedNavigation;