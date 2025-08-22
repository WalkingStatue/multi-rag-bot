/**
 * Base API configuration and utilities
 */
import axios, { AxiosInstance, AxiosResponse } from 'axios';

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api';

class APIClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor to handle token refresh and rate limiting
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;

        // Handle 401 Unauthorized - token refresh
        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;

          try {
            const refreshToken = localStorage.getItem('refresh_token');
            if (refreshToken) {
              const response = await this.client.post(`${API_PREFIX}/auth/refresh`, {
                refresh_token: refreshToken,
              });

              const { access_token, refresh_token: newRefreshToken } = response.data;
              localStorage.setItem('access_token', access_token);
              localStorage.setItem('refresh_token', newRefreshToken);

              originalRequest.headers.Authorization = `Bearer ${access_token}`;
              return this.client(originalRequest);
            }
          } catch (refreshError) {
            // Refresh failed, redirect to login
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        // Handle 429 Too Many Requests - rate limiting
        if (error.response?.status === 429) {
          const errorDetail = error.response?.data?.detail || '';
          originalRequest._retryCount = (originalRequest._retryCount || 0) + 1;
          
          // Check if this is an OpenRouter rate limit error
          const isOpenRouterRateLimit = errorDetail.includes('OpenRouter API rate limit exceeded');
          
          // For OpenRouter rate limits, use longer delays and fewer retries
          const maxRetries = isOpenRouterRateLimit ? 1 : 2;
          const baseDelay = isOpenRouterRateLimit ? 10000 : 5000; // 10s for OpenRouter, 5s for others
          
          if (originalRequest._retryCount <= maxRetries) {
            const retryAfter = error.response.headers['retry-after'];
            const delay = retryAfter ? parseInt(retryAfter) * 1000 : baseDelay;
            
            await new Promise(resolve => setTimeout(resolve, delay));
            return this.client(originalRequest);
          } else {
            // Enhance error message for OpenRouter rate limits
            if (isOpenRouterRateLimit) {
              error.isOpenRouterRateLimit = true;
              error.userMessage = 'OpenRouter API rate limit exceeded. Please wait a moment before trying again.';
            }
          }
        }

        return Promise.reject(error);
      }
    );
  }

  private getFullUrl(url: string): string {
    return `${API_PREFIX}${url}`;
  }

  async get<T = any>(url: string, config?: any): Promise<AxiosResponse<T>> {
    return this.client.get<T>(this.getFullUrl(url), config);
  }

  async post<T = any>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>> {
    return this.client.post<T>(this.getFullUrl(url), data, config);
  }

  async put<T = any>(url: string, data?: any, config?: any): Promise<AxiosResponse<T>> {
    return this.client.put<T>(this.getFullUrl(url), data, config);
  }

  async delete<T = any>(url: string, config?: any): Promise<AxiosResponse<T>> {
    return this.client.delete<T>(this.getFullUrl(url), config);
  }
}

// Export singleton instance with deprecation warning
export const apiClient = new APIClient();

// Add deprecation warning in development
if (typeof process !== 'undefined' && process.env?.NODE_ENV === 'development') {
  const originalGet = apiClient.get;
  const originalPost = apiClient.post;
  const originalPut = apiClient.put;
  const originalDelete = apiClient.delete;
  
  const deprecationWarning = (method: string) => {
    console.warn(
      `⚠️  DEPRECATED: apiClient.${method}() is deprecated. ` +
      'Please use enhancedApiClient from "./enhancedApi" instead for better error handling, retry logic, and monitoring.'
    );
  };
  
  apiClient.get = function(...args) {
    deprecationWarning('get');
    return originalGet.apply(this, args);
  };
  
  apiClient.post = function(...args) {
    deprecationWarning('post');
    return originalPost.apply(this, args);
  };
  
  apiClient.put = function(...args) {
    deprecationWarning('put');
    return originalPut.apply(this, args);
  };
  
  apiClient.delete = function(...args) {
    deprecationWarning('delete');
    return originalDelete.apply(this, args);
  };
}
