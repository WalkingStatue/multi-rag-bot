/**
 * Custom hook for authentication
 */
import { useEffect } from 'react';
import { useAuthStore } from '../stores/authStore';

export const useAuth = () => {
  const {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    updateProfile,
    requestPasswordReset,
    resetPassword,
    clearError,
    initializeAuth,
    isInitializing,
  } = useAuthStore();

  // Initialize authentication on mount only once
  useEffect(() => {
    if (!isInitializing && !isAuthenticated && !user) {
      initializeAuth();
    }
  }, []); // Empty dependency array to run only once

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout,
    updateProfile,
    requestPasswordReset,
    resetPassword,
    clearError,
  };
};