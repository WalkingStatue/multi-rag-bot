import React from 'react';
import { Navigation } from './Navigation';

interface LayoutProps {
  children: React.ReactNode;
  className?: string;
  container?: boolean;
}

export const Layout: React.FC<LayoutProps> = ({ children, className = '', container = true }) => {
  return (
    <div className={`min-h-screen bg-neutral-50 dark:bg-[var(--bg)] transition-colors duration-200 ${className}`}>
      <Navigation />
      <main className={container ? 'max-w-7xl mx-auto py-6 sm:px-6 lg:px-8' : ''}>
        <div className={container ? 'px-4 sm:px-0' : ''}>{children}</div>
      </main>
    </div>
  );
};

export default Layout;



