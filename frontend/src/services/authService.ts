/**
 * Authentication service for API calls
 */
import { enhancedApiClient } from './enhancedApi';
import { 
  AuthToken, 
  LoginCredentials, 
  RegisterData, 
  User, 
  UserProfile
} from '../types/auth';

export class AuthService {
  /**
   * Login user with credentials
   */
  async login(credentials: LoginCredentials): Promise<AuthToken> {
    const response = await enhancedApiClient.post<AuthToken>('/auth/login', credentials, {
      context: 'AuthService.login'
    });
    return response.data;
  }

  /**
   * Register new user
   */
  async register(data: RegisterData): Promise<User> {
    const response = await enhancedApiClient.post<User>('/auth/register', data);
    return response.data;
  }

  /**
   * Logout user
   */
  async logout(): Promise<void> {
    await enhancedApiClient.post('/auth/logout');
  }

  /**
   * Refresh authentication token
   */
  async refreshToken(refreshToken: string): Promise<AuthToken> {
    const response = await enhancedApiClient.post<AuthToken>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  }

  /**
   * Get current user profile
   */
  async getCurrentUser(): Promise<User> {
    const response = await enhancedApiClient.get<User>('/users/profile');
    return response.data;
  }

  /**
   * Update user profile
   */
  async updateProfile(profile: Partial<UserProfile>): Promise<User> {
    const response = await enhancedApiClient.put<User>('/users/profile', profile);
    return response.data;
  }

  /**
   * Request password reset
   */
  async requestPasswordReset(email: string): Promise<void> {
    await enhancedApiClient.post('/auth/forgot-password', { email });
  }

  /**
   * Reset password with token
   */
  async resetPassword(token: string, newPassword: string): Promise<void> {
    await enhancedApiClient.post('/auth/reset-password', {
      token,
      new_password: newPassword,
    });
  }

  /**
   * Verify if user is authenticated
   */
  isAuthenticated(): boolean {
    const token = localStorage.getItem('access_token');
    return !!token;
  }

  /**
   * Get stored access token
   */
  getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  /**
   * Get stored refresh token
   */
  getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  }

  /**
   * Store authentication tokens
   */
  storeTokens(tokens: AuthToken): void {
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
  }

  /**
   * Clear stored tokens
   */
  clearTokens(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }
}

export const authService = new AuthService();