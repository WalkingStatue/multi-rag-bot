/**
 * Enhanced protected route component with loading states and permissions
 */
import React, { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useEnhancedAuth, usePermissions } from '../../hooks/useEnhancedAuth';
import { LoadingOverlay, LoadingSpinner } from '../common/LoadingSpinner';
import { ErrorDisplay } from '../common/ErrorDisplay';
import { log } from '../../utils/logger';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requireAuth?: boolean;
  requiredPermissions?: string[];
  fallbackPath?: string;
  loadingComponent?: React.ReactNode;
  unauthorizedComponent?: React.ReactNode;
  showLoadingOverlay?: boolean;
  minLoadingTime?: number; // Minimum loading time in ms to prevent flashing
}

export const EnhancedProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requireAuth = true,
  requiredPermissions = [],
  fallbackPath = '/login',
  loadingComponent,
  unauthorizedComponent,
  showLoadingOverlay = true,
  minLoadingTime = 500,
}) => {
  const { isAuthenticated, isLoading, isReady, user, error } = useEnhancedAuth();
  const permissions = usePermissions();
  const location = useLocation();
  const [showMinLoading, setShowMinLoading] = useState(true);

  // Ensure minimum loading time to prevent flashing
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowMinLoading(false);
    }, minLoadingTime);

    return () => clearTimeout(timer);
  }, [minLoadingTime]);

  // Log route access attempts
  useEffect(() => {
    if (isReady) {
      log.user('Route access attempt', {
        path: location.pathname,
        requireAuth,
        isAuthenticated,
        userId: user?.id,
        requiredPermissions,
      });
    }
  }, [location.pathname, requireAuth, isAuthenticated, user?.id, requiredPermissions, isReady]);

  // Show loading state
  if (isLoading || !isReady || showMinLoading) {
    if (loadingComponent) {
      return <>{loadingComponent}</>;
    }

    if (showLoadingOverlay) {
      return <LoadingOverlay message="Loading..." />;
    }

    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="xl" />
      </div>
    );
  }

  // Handle authentication errors
  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <ErrorDisplay
          error={error}
          onRetry={() => window.location.reload()}
          showDetails={import.meta.env.DEV}
        />
      </div>
    );
  }

  // Check authentication requirement
  if (requireAuth && !isAuthenticated) {
    log.user('Unauthorized route access redirected', {
      path: location.pathname,
      redirectTo: fallbackPath,
    });

    return (
      <Navigate
        to={fallbackPath}
        state={{ from: location }}
        replace
      />
    );
  }

  // Redirect authenticated users away from auth pages
  if (!requireAuth && isAuthenticated) {
    const from = location.state?.from?.pathname || '/dashboard';
    log.user('Authenticated user redirected from auth page', {
      path: location.pathname,
      redirectTo: from,
    });

    return <Navigate to={from} replace />;
  }

  // Check permissions if required
  if (requiredPermissions.length > 0 && isAuthenticated) {
    const hasRequiredPermissions = requiredPermissions.every(permission => {
      // Add your permission checking logic here
      // This is a simplified example
      switch (permission) {
        case 'admin':
          return (user as any)?.role === 'admin';
        case 'editor':
          return ['admin', 'editor'].includes((user as any)?.role || '');
        case 'viewer':
          return ['admin', 'editor', 'viewer'].includes((user as any)?.role || '');
        default:
          return true;
      }
    });

    if (!hasRequiredPermissions) {
      log.user('Insufficient permissions for route', {
        path: location.pathname,
        userRole: (user as any)?.role,
        requiredPermissions,
      });

      if (unauthorizedComponent) {
        return <>{unauthorizedComponent}</>;
      }

      return (
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center">
            <div className="mx-auto h-12 w-12 text-red-400">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
                />
              </svg>
            </div>
            <h3 className="mt-2 text-sm font-medium text-neutral-900 dark:text-neutral-100">
              Access Denied
            </h3>
            <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
              You don't have permission to access this page.
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
      );
    }
  }

  return <>{children}</>;
};

/**
 * Route wrapper with role-based access control
 */
interface RoleProtectedRouteProps extends ProtectedRouteProps {
  allowedRoles: string[];
}

export const RoleProtectedRoute: React.FC<RoleProtectedRouteProps> = ({
  allowedRoles,
  ...props
}) => {
  return (
    <EnhancedProtectedRoute
      {...props}
      requiredPermissions={allowedRoles}
    />
  );
};

/**
 * Admin-only route wrapper
 */
export const AdminRoute: React.FC<Omit<ProtectedRouteProps, 'requiredPermissions'>> = (props) => {
  return (
    <EnhancedProtectedRoute
      {...props}
      requiredPermissions={['admin']}
    />
  );
};

/**
 * Public route that redirects authenticated users
 */
export const PublicRoute: React.FC<ProtectedRouteProps> = (props) => {
  return (
    <EnhancedProtectedRoute
      {...props}
      requireAuth={false}
    />
  );
};

/**
 * Route with custom loading state
 */
interface LoadingRouteProps extends ProtectedRouteProps {
  isLoading: boolean;
  loadingMessage?: string;
}

export const LoadingRoute: React.FC<LoadingRouteProps> = ({
  isLoading,
  loadingMessage = 'Loading...',
  children,
  ...props
}) => {
  if (isLoading) {
    return <LoadingOverlay message={loadingMessage} />;
  }

  return (
    <EnhancedProtectedRoute {...props}>
      {children}
    </EnhancedProtectedRoute>
  );
};

/**
 * Route with data fetching and loading state
 */
interface DataRouteProps extends ProtectedRouteProps {
  data: any;
  isLoading: boolean;
  error?: any;
  onRetry?: () => void;
  emptyState?: React.ReactNode;
}

export const DataRoute: React.FC<DataRouteProps> = ({
  data,
  isLoading,
  error,
  onRetry,
  emptyState,
  children,
  ...props
}) => {
  return (
    <EnhancedProtectedRoute {...props}>
      {isLoading ? (
        <LoadingOverlay message="Loading data..." />
      ) : error ? (
        <div className="min-h-screen flex items-center justify-center">
          <ErrorDisplay
            error={error}
            onRetry={onRetry}
            showDetails={import.meta.env.DEV}
          />
        </div>
      ) : !data && emptyState ? (
        emptyState
      ) : (
        children
      )}
    </EnhancedProtectedRoute>
  );
};

/**
 * Conditional route wrapper
 */
interface ConditionalRouteProps extends ProtectedRouteProps {
  condition: boolean;
  fallback?: React.ReactNode;
}

export const ConditionalRoute: React.FC<ConditionalRouteProps> = ({
  condition,
  fallback,
  children,
  ...props
}) => {
  return (
    <EnhancedProtectedRoute {...props}>
      {condition ? children : fallback}
    </EnhancedProtectedRoute>
  );
};

/**
 * Route with feature flag protection
 */
interface FeatureRouteProps extends ProtectedRouteProps {
  featureFlag: string;
  featureEnabled: boolean;
}

export const FeatureRoute: React.FC<FeatureRouteProps> = ({
  featureFlag,
  featureEnabled,
  children,
  ...props
}) => {
  if (!featureEnabled) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="mx-auto h-12 w-12 text-neutral-400">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>
          <h3 className="mt-2 text-sm font-medium text-neutral-900 dark:text-neutral-100">
            Feature Not Available
          </h3>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            This feature is currently disabled.
          </p>
        </div>
      </div>
    );
  }

  return (
    <EnhancedProtectedRoute {...props}>
      {children}
    </EnhancedProtectedRoute>
  );
};