/**
 * Enhanced authentication hook with better error handling and loading states
 */
import { useCallback, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useToastHelpers } from '../components/common/Toast';
import { errorHandler } from '../utils/errorHandler';
import { LoginCredentials, RegisterData } from '../types/auth';

export const useEnhancedAuth = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { success, error: showError } = useToastHelpers();
  
  const {
    user,
    isAuthenticated,
    isLoading,
    error,
    login: authLogin,
    register: authRegister,
    logout: authLogout,
    updateProfile,
    requestPasswordReset,
    resetPassword,
    clearError,
    initializeAuth,
    isInitializing,
  } = useAuthStore();

  // Enhanced login with better error handling
  const login = useCallback(async (credentials: LoginCredentials) => {
    try {
      clearError();
      await authLogin(credentials);
      
      // Navigate to intended destination or dashboard
      const from = location.state?.from?.pathname || '/dashboard';
      navigate(from, { replace: true });
      
      success('Welcome back!', `Logged in as ${credentials.username}`);
    } catch (err: any) {
      const appError = errorHandler.handleError(err, {
        component: 'useEnhancedAuth',
        action: 'login'
      });
      
      // Show specific error messages
      if (appError.type === 'auth') {
        showError('Login Failed', 'Invalid username or password');
      } else if (appError.type === 'network') {
        showError('Connection Error', 'Please check your internet connection');
      } else {
        showError('Login Failed', appError.message);
      }
      
      throw err;
    }
  }, [authLogin, navigate, location, success, showError, clearError]);

  // Enhanced register with better error handling
  const register = useCallback(async (data: RegisterData) => {
    try {
      clearError();
      await authRegister(data);
      
      navigate('/dashboard', { replace: true });
      success('Account Created!', `Welcome to the platform, ${data.username}!`);
    } catch (err: any) {
      const appError = errorHandler.handleError(err, {
        component: 'useEnhancedAuth',
        action: 'register'
      });
      
      // Show specific error messages
      if (appError.statusCode === 409) {
        showError('Registration Failed', 'Username or email already exists');
      } else if (appError.type === 'validation') {
        showError('Registration Failed', 'Please check your input and try again');
      } else if (appError.type === 'network') {
        showError('Connection Error', 'Please check your internet connection');
      } else {
        showError('Registration Failed', appError.message);
      }
      
      throw err;
    }
  }, [authRegister, navigate, success, showError, clearError]);

  // Enhanced logout with confirmation
  const logout = useCallback(async (showConfirmation = true) => {
    try {
      authLogout();
      navigate('/login', { replace: true });
      
      if (showConfirmation) {
        success('Logged Out', 'You have been successfully logged out');
      }
    } catch (err: any) {
      // Even if logout fails on server, clear local state
      navigate('/login', { replace: true });
      showError('Logout Warning', 'Logged out locally, but server logout may have failed');
    }
  }, [authLogout, navigate, success, showError]);

  // Enhanced profile update
  const updateUserProfile = useCallback(async (profileData: any) => {
    try {
      clearError();
      await updateProfile(profileData);
      success('Profile Updated', 'Your profile has been updated successfully');
    } catch (err: any) {
      const appError = errorHandler.handleError(err, {
        component: 'useEnhancedAuth',
        action: 'updateProfile'
      });
      
      showError('Profile Update Failed', appError.message);
      throw err;
    }
  }, [updateProfile, success, showError, clearError]);

  // Enhanced password reset request
  const requestPasswordResetWithFeedback = useCallback(async (email: string) => {
    try {
      clearError();
      await requestPasswordReset(email);
      success('Reset Email Sent', 'Please check your email for password reset instructions');
    } catch (err: any) {
      const appError = errorHandler.handleError(err, {
        component: 'useEnhancedAuth',
        action: 'requestPasswordReset'
      });
      
      if (appError.statusCode === 404) {
        showError('Email Not Found', 'No account found with this email address');
      } else {
        showError('Reset Request Failed', appError.message);
      }
      
      throw err;
    }
  }, [requestPasswordReset, success, showError, clearError]);

  // Enhanced password reset
  const resetPasswordWithFeedback = useCallback(async (token: string, newPassword: string) => {
    try {
      clearError();
      await resetPassword(token, newPassword);
      navigate('/login', { replace: true });
      success('Password Reset', 'Your password has been reset successfully. Please log in with your new password.');
    } catch (err: any) {
      const appError = errorHandler.handleError(err, {
        component: 'useEnhancedAuth',
        action: 'resetPassword'
      });
      
      if (appError.statusCode === 400) {
        showError('Invalid Reset Token', 'The reset token is invalid or has expired');
      } else {
        showError('Password Reset Failed', appError.message);
      }
      
      throw err;
    }
  }, [resetPassword, navigate, success, showError, clearError]);

  // Auto-logout on token expiration
  useEffect(() => {
    const handleTokenExpiration = () => {
      if (isAuthenticated) {
        logout(false);
        showError('Session Expired', 'Your session has expired. Please log in again.');
      }
    };

    // Listen for auth errors globally
    const unsubscribe = errorHandler.addErrorListener((appError) => {
      if (appError.type === 'auth' && appError.statusCode === 401) {
        handleTokenExpiration();
      }
    });

    return unsubscribe;
  }, [isAuthenticated, logout, showError]);

  // Initialize auth on mount
  useEffect(() => {
    if (!isInitializing && !isAuthenticated && !user) {
      initializeAuth();
    }
  }, [initializeAuth, isInitializing, isAuthenticated, user]);

  return {
    // State
    user,
    isAuthenticated,
    isLoading,
    isInitializing,
    error,
    
    // Actions
    login,
    register,
    logout,
    updateProfile: updateUserProfile,
    requestPasswordReset: requestPasswordResetWithFeedback,
    resetPassword: resetPasswordWithFeedback,
    clearError,
    
    // Utilities
    isReady: !isInitializing,
    hasError: !!error,
  };
};

// Hook for checking specific permissions
export const usePermissions = () => {
  const { user, isAuthenticated } = useEnhancedAuth();
  
  return {
    canCreateBot: isAuthenticated,
    canEditBot: (botOwnerId?: string) => isAuthenticated && (!botOwnerId || user?.id === botOwnerId),
    canDeleteBot: (botOwnerId?: string) => isAuthenticated && (!botOwnerId || user?.id === botOwnerId),
    canManageDocuments: (botOwnerId?: string) => isAuthenticated && (!botOwnerId || user?.id === botOwnerId),
    canChat: isAuthenticated,
    isOwner: (ownerId?: string) => isAuthenticated && user?.id === ownerId,
  };
};

// Hook for auth-related navigation guards
export const useAuthGuard = () => {
  const { isAuthenticated, isInitializing } = useEnhancedAuth();
  const navigate = useNavigate();
  const location = useLocation();
  
  const requireAuth = useCallback(() => {
    if (!isInitializing && !isAuthenticated) {
      navigate('/login', { 
        state: { from: location },
        replace: true 
      });
      return false;
    }
    return true;
  }, [isAuthenticated, isInitializing, navigate, location]);
  
  const requireGuest = useCallback(() => {
    if (!isInitializing && isAuthenticated) {
      const from = location.state?.from?.pathname || '/dashboard';
      navigate(from, { replace: true });
      return false;
    }
    return true;
  }, [isAuthenticated, isInitializing, navigate, location]);
  
  return {
    requireAuth,
    requireGuest,
    isReady: !isInitializing,
  };
};