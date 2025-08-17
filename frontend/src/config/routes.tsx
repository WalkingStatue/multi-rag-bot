/**
 * Route configuration with enhanced protection and loading states
 */
import React from 'react';
import { RouteObject } from 'react-router-dom';
import { EnhancedProtectedRoute, PublicRoute, AdminRoute, DataRoute } from '../components/routing/EnhancedProtectedRoute';
import { PageErrorBoundary } from '../components/common/EnhancedErrorBoundary';
import { RouterLayout } from '../components/routing/RouterLayout';

// Import pages directly (can be converted to lazy loading later)
import { LoginPage } from '../pages/LoginPage';
import { RegisterPage } from '../pages/RegisterPage';
import { ForgotPasswordPage } from '../pages/ForgotPasswordPage';
import { ResetPasswordPage } from '../pages/ResetPasswordPage';
import { DashboardPage } from '../pages/DashboardPage';
import { ProfilePage } from '../pages/ProfilePage';
import { CollaborationPage } from '../pages/CollaborationPage';
import DocumentManagementPage from '../pages/DocumentManagementPage';
import { ChatPage } from '../pages/ChatPage';
import { BotIntegrationsPage } from '../pages/BotIntegrationsPage';

// Route wrapper with error boundary and suspense
const RouteWrapper: React.FC<{
  children: React.ReactNode;
  pageName: string;
}> = ({ children, pageName }) => (
  <PageErrorBoundary pageName={pageName}>
    {children}
  </PageErrorBoundary>
);

// Protected route wrapper that works within router context
const ProtectedRouteWrapper: React.FC<{
  children: React.ReactNode;
  pageName: string;
  requireAuth?: boolean;
  requiredPermissions?: string[];
  fallbackPath?: string;
}> = ({ children, pageName, requireAuth = true, requiredPermissions = [], fallbackPath = '/login' }) => (
  <RouteWrapper pageName={pageName}>
    <EnhancedProtectedRoute
      requireAuth={requireAuth}
      requiredPermissions={requiredPermissions}
      fallbackPath={fallbackPath}
    >
      {children}
    </EnhancedProtectedRoute>
  </RouteWrapper>
);

// Public route wrapper that works within router context
const PublicRouteWrapper: React.FC<{
  children: React.ReactNode;
  pageName: string;
}> = ({ children, pageName }) => (
  <RouteWrapper pageName={pageName}>
    <PublicRoute>
      {children}
    </PublicRoute>
  </RouteWrapper>
);

// Admin route wrapper that works within router context
const AdminRouteWrapper: React.FC<{
  children: React.ReactNode;
  pageName: string;
}> = ({ children, pageName }) => (
  <RouteWrapper pageName={pageName}>
    <AdminRoute>
      {children}
    </AdminRoute>
  </RouteWrapper>
);

// Route configuration
export const routeConfig: RouteObject[] = [
  {
    path: '/',
    element: <RouterLayout />,
    children: [
      // Public routes (redirect authenticated users)
      {
        path: 'login',
        element: (
          <PublicRouteWrapper pageName="Login">
            <LoginPage />
          </PublicRouteWrapper>
        ),
      },
      {
        path: 'register',
        element: (
          <PublicRouteWrapper pageName="Register">
            <RegisterPage />
          </PublicRouteWrapper>
        ),
      },
      {
        path: 'forgot-password',
        element: (
          <PublicRouteWrapper pageName="Forgot Password">
            <ForgotPasswordPage />
          </PublicRouteWrapper>
        ),
      },
      {
        path: 'reset-password',
        element: (
          <PublicRouteWrapper pageName="Reset Password">
            <ResetPasswordPage />
          </PublicRouteWrapper>
        ),
      },

      // Protected routes
      {
        path: 'dashboard',
        element: (
          <ProtectedRouteWrapper pageName="Dashboard">
            <DashboardPage />
          </ProtectedRouteWrapper>
        ),
      },
      {
        path: 'bots',
        element: (
          <ProtectedRouteWrapper pageName="Bots">
            <DashboardPage />
          </ProtectedRouteWrapper>
        ),
      },
      {
        path: 'profile',
        element: (
          <ProtectedRouteWrapper pageName="Profile">
            <ProfilePage />
          </ProtectedRouteWrapper>
        ),
      },

      // Bot-specific routes
      {
        path: 'bots/:botId/chat',
        element: (
          <ProtectedRouteWrapper pageName="Chat">
            <ChatPage />
          </ProtectedRouteWrapper>
        ),
      },
      {
        path: 'bots/:botId/documents',
        element: (
          <ProtectedRouteWrapper pageName="Document Management">
            <DocumentManagementPage />
          </ProtectedRouteWrapper>
        ),
      },
      {
        path: 'bots/:botId/collaboration',
        element: (
          <ProtectedRouteWrapper pageName="Collaboration">
            <CollaborationPage />
          </ProtectedRouteWrapper>
        ),
      },
      {
        path: 'bots/:botId/integrations',
        element: (
          <ProtectedRouteWrapper pageName="Integrations">
            <BotIntegrationsPage />
          </ProtectedRouteWrapper>
        ),
      },

      // Admin routes
      {
        path: 'admin',
        element: (
          <AdminRouteWrapper pageName="Admin Dashboard">
            <div className="p-8">
              <h1 className="text-2xl font-bold">Admin Dashboard</h1>
              <p>This is an admin-only area.</p>
            </div>
          </AdminRouteWrapper>
        ),
      },

      // Default redirect
      {
        index: true,
        element: (
          <ProtectedRouteWrapper pageName="Home" fallbackPath="/login">
            <div />
          </ProtectedRouteWrapper>
        ),
      },

      // Catch-all route
      {
        path: '*',
        element: (
          <RouteWrapper pageName="Not Found">
            <div className="min-h-screen flex items-center justify-center">
              <div className="text-center">
                <div className="mx-auto h-12 w-12 text-neutral-400">
                  <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                    />
                  </svg>
                </div>
                <h3 className="mt-2 text-sm font-medium text-neutral-900 dark:text-neutral-100">
                  Page Not Found
                </h3>
                <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
                  The page you're looking for doesn't exist.
                </p>
                <div className="mt-6">
                  <button
                    onClick={() => window.history.back()}
                    className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-primary-600 hover:bg-primary-700"
                  >
                    Go Back
                  </button>
                </div>
              </div>
            </div>
          </RouteWrapper>
        ),
      },
    ],
  },
];

// Route metadata for navigation and breadcrumbs
export const routeMetadata: Record<string, {
  title: string;
  description: string;
  requireAuth: boolean;
  requiredRole?: string;
}> = {
  '/login': {
    title: 'Sign In',
    description: 'Sign in to your account',
    requireAuth: false,
  },
  '/register': {
    title: 'Sign Up',
    description: 'Create a new account',
    requireAuth: false,
  },
  '/forgot-password': {
    title: 'Forgot Password',
    description: 'Reset your password',
    requireAuth: false,
  },
  '/reset-password': {
    title: 'Reset Password',
    description: 'Set a new password',
    requireAuth: false,
  },
  '/dashboard': {
    title: 'Dashboard',
    description: 'Your bot management dashboard',
    requireAuth: true,
  },
  '/bots': {
    title: 'Bots',
    description: 'Create, edit and manage your bots',
    requireAuth: true,
  },
  '/profile': {
    title: 'Profile',
    description: 'Manage your account settings',
    requireAuth: true,
  },
  '/bots/:botId/chat': {
    title: 'Chat',
    description: 'Chat with your bot',
    requireAuth: true,
  },
  '/bots/:botId/documents': {
    title: 'Documents',
    description: 'Manage bot documents',
    requireAuth: true,
  },
  '/bots/:botId/collaboration': {
    title: 'Collaboration',
    description: 'Manage bot collaborators',
    requireAuth: true,
  },
  '/bots/:botId/integrations': {
    title: 'Integrations',
    description: 'Embed your bot or use the API',
    requireAuth: true,
  },
  '/admin': {
    title: 'Admin Dashboard',
    description: 'Administrative controls',
    requireAuth: true,
    requiredRole: 'admin',
  },
};

// Navigation items for authenticated users
export const navigationItems = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: 'home',
    current: false,
  },
  {
    name: 'Profile',
    href: '/profile',
    icon: 'user',
    current: false,
  },
];

// Utility functions
export const getRouteMetadata = (pathname: string) => {
  // Try exact match first
  if (routeMetadata[pathname]) {
    return routeMetadata[pathname];
  }

  // Try pattern matching for dynamic routes
  for (const [pattern, metadata] of Object.entries(routeMetadata)) {
    if (pattern.includes(':')) {
      const regex = new RegExp('^' + pattern.replace(/:[^/]+/g, '[^/]+') + '$');
      if (regex.test(pathname)) {
        return metadata;
      }
    }
  }

  return null;
};

export const isProtectedRoute = (pathname: string): boolean => {
  const metadata = getRouteMetadata(pathname);
  return metadata?.requireAuth ?? true; // Default to protected
};

export const getRequiredRole = (pathname: string): string | null => {
  const metadata = getRouteMetadata(pathname);
  return metadata?.requiredRole ?? null;
};