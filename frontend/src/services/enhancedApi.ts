/**
 * Enhanced API client with comprehensive error handling and retry logic
 */
import axios, { AxiosInstance, AxiosResponse, AxiosRequestConfig } from 'axios';
import { parseApiError, errorHandler, AppError } from '../utils/errorHandler';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const API_PREFIX = '/api';

interface RetryConfig {
  maxRetries: number;
  retryDelay: number;
  retryCondition?: (error: any) => boolean;
}

interface RequestConfig extends AxiosRequestConfig {
  retry?: Partial<RetryConfig>;
  skipErrorHandling?: boolean;
  context?: string;
}

class EnhancedAPIClient {
  private client: AxiosInstance;
  private defaultRetryConfig: RetryConfig = {
    maxRetries: 3,
    retryDelay: 1000,
    retryCondition: (error) => {
      const status = error.response?.status;
      return !status || status >= 500 || status === 429;
    }
  };

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors() {
    // Request interceptor
    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        
        // Add request timestamp for monitoring
        (config as any).metadata = { startTime: Date.now() };
        
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.client.interceptors.response.use(
      (response) => {
        // Log successful requests in development
        if (import.meta.env.DEV) {
          const duration = Date.now() - (response.config as any).metadata?.startTime;
          console.log(`✅ ${response.config.method?.toUpperCase()} ${response.config.url} - ${duration}ms`);
        }
        return response;
      },
      async (error) => {
        const originalRequest = error.config;
        
        // Parse the error
        const appError = parseApiError(error, { 
          component: originalRequest.context,
          action: `${originalRequest.method?.toUpperCase()} ${originalRequest.url}`
        });

        // Handle token refresh for 401 errors
        if (appError.statusCode === 401 && !originalRequest._retry) {
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
            // Refresh failed, clear tokens and redirect
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.href = '/login';
            return Promise.reject(refreshError);
          }
        }

        // Handle retries for retryable errors
        if (appError.retryable && !originalRequest.skipErrorHandling) {
          const retryConfig = { ...this.defaultRetryConfig, ...originalRequest.retry };
          const retryCount = originalRequest._retryCount || 0;
          
          if (retryCount < retryConfig.maxRetries && retryConfig.retryCondition?.(error)) {
            originalRequest._retryCount = retryCount + 1;
            
            const delay = appError.retryAfter 
              ? appError.retryAfter * 1000 
              : retryConfig.retryDelay * Math.pow(2, retryCount);
            
            await new Promise(resolve => setTimeout(resolve, delay));
            return this.client(originalRequest);
          }
        }

        // Log error and notify error handler
        if (!originalRequest.skipErrorHandling) {
          errorHandler.handleError(appError, {
            component: originalRequest.context,
            action: `${originalRequest.method?.toUpperCase()} ${originalRequest.url}`
          });
        }

        return Promise.reject(error);
      }
    );
  }

  private getFullUrl(url: string): string {
    return `${API_PREFIX}${url}`;
  }

  async get<T = any>(url: string, config?: RequestConfig): Promise<AxiosResponse<T>> {
    return this.client.get<T>(this.getFullUrl(url), config);
  }

  async post<T = any>(url: string, data?: any, config?: RequestConfig): Promise<AxiosResponse<T>> {
    return this.client.post<T>(this.getFullUrl(url), data, config);
  }

  async put<T = any>(url: string, data?: any, config?: RequestConfig): Promise<AxiosResponse<T>> {
    return this.client.put<T>(this.getFullUrl(url), data, config);
  }

  async patch<T = any>(url: string, data?: any, config?: RequestConfig): Promise<AxiosResponse<T>> {
    return this.client.patch<T>(this.getFullUrl(url), data, config);
  }

  async delete<T = any>(url: string, config?: RequestConfig): Promise<AxiosResponse<T>> {
    return this.client.delete<T>(this.getFullUrl(url), config);
  }

  /**
   * Upload file with progress tracking
   */
  async uploadFile<T = any>(
    url: string, 
    file: File, 
    onProgress?: (progress: number) => void,
    config?: RequestConfig
  ): Promise<AxiosResponse<T>> {
    const formData = new FormData();
    formData.append('file', file);

    return this.client.post<T>(this.getFullUrl(url), formData, {
      ...config,
      headers: {
        'Content-Type': 'multipart/form-data',
        ...config?.headers,
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(progress);
        }
      },
    });
  }

  /**
   * Download file with proper handling
   */
  async downloadFile(
    url: string, 
    filename?: string,
    config?: RequestConfig
  ): Promise<void> {
    const response = await this.client.get(this.getFullUrl(url), {
      ...config,
      responseType: 'blob',
    });

    const blob = new Blob([response.data]);
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = filename || 'download';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(downloadUrl);
  }

  /**
   * Health check endpoint
   */
  async healthCheck(): Promise<boolean> {
    try {
      await this.client.get('/health', {
        timeout: 5000
      } as any);
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Cancel all pending requests
   */
  cancelAllRequests(): void {
    // This would require implementing a request tracking system
    // For now, we'll just create a new axios instance
    this.client = axios.create(this.client.defaults);
    this.setupInterceptors();
  }
}

// Create and export singleton instance
export const enhancedApiClient = new EnhancedAPIClient();

// Export the original client for backward compatibility
export { apiClient } from './api';

// Export types
export type { RequestConfig, RetryConfig };