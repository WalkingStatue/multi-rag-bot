/**
 * Router layout component that provides router context for protected routes
 */
import React from 'react';
import { Outlet } from 'react-router-dom';

export const RouterLayout: React.FC = () => {
  return <Outlet />;
};