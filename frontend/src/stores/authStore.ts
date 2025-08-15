/**
 * Authentication state management using Zustand
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { 
  LoginCredentials, 
  RegisterData, 
  UserProfile,
  AuthState 
} from '../types/auth';
import { authService } from '../services/authService';

interface AuthStore extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => void;
  updateProfile: (profile: Partial<UserProfile>) => Promise<void>;
  requestPasswordReset: (email: string) => Promise<void>;
  resetPassword: (token: string, newPassword: string) => Promise<void>;
  clearError: () => void;
  initializeAuth: () => Promise<void>;
  setLoading: (loading: boolean) => void;
  isInitializing: boolean;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      error: null,
      isInitializing: false,

      setLoading: (loading: boolean) => {
        set({ isLoading: loading });
      },

      clearError: () => {
        set({ error: null });
      },

      login: async (credentials: LoginCredentials) => {
        try {
          set({ isLoading: true, error: null });
          
          const tokens = await authService.login(credentials);
          authService.storeTokens(tokens);
          
          // After successful login, get user profile
          const user = await authService.getCurrentUser();
          
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Login failed';
          set({
            isLoading: false,
            error: errorMessage,
            isAuthenticated: false,
            user: null,
          });
          throw error;
        }
      },

      register: async (data: RegisterData) => {
        try {
          set({ isLoading: true, error: null });
          
          // Step 1: Register the user (returns User object)
          const user = await authService.register(data);
          
          // Step 2: Automatically log them in to get tokens
          const tokens = await authService.login({
            username: data.username,
            password: data.password,
          });
          authService.storeTokens(tokens);
          
          set({
            user,
            isAuthenticated: true,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Registration failed';
          set({
            isLoading: false,
            error: errorMessage,
            isAuthenticated: false,
            user: null,
          });
          throw error;
        }
      },

      logout: () => {
        try {
          authService.logout().catch(() => {
            // Ignore logout API errors, still clear local state
          });
        } finally {
          authService.clearTokens();
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
          });
        }
      },

      updateProfile: async (profile: Partial<UserProfile>) => {
        try {
          set({ isLoading: true, error: null });
          
          const updatedUser = await authService.updateProfile(profile);
          
          set({
            user: updatedUser,
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Profile update failed';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      requestPasswordReset: async (email: string) => {
        try {
          set({ isLoading: true, error: null });
          
          await authService.requestPasswordReset(email);
          
          set({
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Password reset request failed';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      resetPassword: async (token: string, newPassword: string) => {
        try {
          set({ isLoading: true, error: null });
          
          await authService.resetPassword(token, newPassword);
          
          set({
            isLoading: false,
            error: null,
          });
        } catch (error: any) {
          const errorMessage = error.response?.data?.detail || error.response?.data?.message || 'Password reset failed';
          set({
            isLoading: false,
            error: errorMessage,
          });
          throw error;
        }
      },

      initializeAuth: async () => {
        const state = get();
        
        // Prevent multiple simultaneous initialization calls
        if (state.isInitializing) {
          return;
        }
        
        try {
          set({ isInitializing: true });
          
          if (authService.isAuthenticated()) {
            set({ isLoading: true });
            
            const user = await authService.getCurrentUser();
            
            set({
              user,
              isAuthenticated: true,
              isLoading: false,
              error: null,
              isInitializing: false,
            });
          } else {
            // No token, set to unauthenticated state
            set({
              user: null,
              isAuthenticated: false,
              isLoading: false,
              error: null,
              isInitializing: false,
            });
          }
        } catch (error) {
          // Token is invalid, clear it
          authService.clearTokens();
          set({
            user: null,
            isAuthenticated: false,
            isLoading: false,
            error: null,
            isInitializing: false,
          });
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);