/**
 * Legacy Layout Component
 * 
 * Redirects to the new unified MainLayout for backward compatibility.
 * @deprecated Use MainLayout directly instead.
 */
import React from 'react';
import MainLayout from '../../layouts/MainLayout';

interface LayoutProps {
  children: React.ReactNode;
  className?: string;
  container?: boolean;
}

export const Layout: React.FC<LayoutProps> = ({ 
  children, 
  className = '', 
  container = true 
}) => {
  return (
    <MainLayout 
      className={className}
      fullWidth={!container}
      padding={container ? 'md' : 'none'}
      noHeader={true}
    >
      {children}
    </MainLayout>
  );
};

export default Layout;



