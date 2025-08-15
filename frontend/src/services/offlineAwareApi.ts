import { enhancedApiClient } from './enhancedApi';
import { offlineQueue } from './offlineQueue';
import { logger } from '../utils/logger';

export interface OfflineAwareRequestOptions {
  priority?: 'low' | 'medium' | 'high';
  enableOfflineQueue?: boolean;
  maxRetries?: number;
  metadata?: Record<string, any>;
  headers?: Record<string, string>;
}

class OfflineAwareApiService {
  private isOnline(): boolean {
    return navigator.onLine;
  }

  private shouldQueueRequest(method: string, options?: OfflineAwareRequestOptions): boolean {
    // Don't queue GET requests by default (they should be cached)
    if (method.toLowerCase() === 'get') {
      return false;
    }

    // Check if offline queueing is explicitly enabled
    return options?.enableOfflineQueue !== false;
  }

  async request<T>(
    url: string,
    options: OfflineAwareRequestOptions & { method?: string; body?: any } = {}
  ): Promise<T> {
    const {
      priority = 'medium',
      enableOfflineQueue = true,
      maxRetries = 3,
      metadata,
      headers = {},
      method = 'GET',
      body,
      ...otherOptions
    } = options;

    // If online, try normal request first
    if (this.isOnline()) {
      try {
        const response = await this.makeApiCall<T>(url, method, body, headers, otherOptions);
        return response.data;
      } catch (error) {
        logger.error(`API request failed: ${method} ${url}: ${error instanceof Error ? error.message : 'Unknown error'}`);
        
        // If request fails and we're now offline, queue it
        if (!this.isOnline() && this.shouldQueueRequest(method, options)) {
          await this.queueRequest(url, { method, body: body ? JSON.stringify(body) : undefined, headers }, {
            priority,
            maxRetries,
            metadata,
          });
          throw new Error('Request queued for when connection is restored');
        }
        
        throw error;
      }
    }

    // If offline, queue the request if applicable
    if (this.shouldQueueRequest(method, options)) {
      await this.queueRequest(url, { method, body: body ? JSON.stringify(body) : undefined, headers }, {
        priority,
        maxRetries,
        metadata,
      });
      throw new Error('You are offline. Request has been queued and will be sent when connection is restored.');
    }

    // For GET requests when offline, try to get from cache via service worker
    if (method.toLowerCase() === 'get') {
      throw new Error('You are offline and this data is not available in cache.');
    }

    throw new Error('You are offline and this action cannot be performed.');
  }

  private async makeApiCall<T>(
    url: string,
    method: string,
    data?: any,
    headers: Record<string, string> = {},
    options: any = {}
  ) {
    const config = {
      ...options,
      headers,
    };

    switch (method.toUpperCase()) {
      case 'GET':
        return enhancedApiClient.get<T>(url, config);
      case 'POST':
        return enhancedApiClient.post<T>(url, data, config);
      case 'PUT':
        return enhancedApiClient.put<T>(url, data, config);
      case 'PATCH':
        return enhancedApiClient.patch<T>(url, data, config);
      case 'DELETE':
        return enhancedApiClient.delete<T>(url, config);
      default:
        throw new Error(`Unsupported HTTP method: ${method}`);
    }
  }

  private async queueRequest(
    url: string,
    options: { method?: string; body?: string; headers?: Record<string, string> },
    queueOptions: {
      priority: 'low' | 'medium' | 'high';
      maxRetries: number;
      metadata?: Record<string, any>;
    }
  ): Promise<string> {
    const requestId = offlineQueue.addRequest(
      url,
      options.method || 'GET',
      options.headers || {},
      options.body,
      queueOptions
    );

    logger.info(`Request queued for offline processing: ${requestId}`);
    return requestId;
  }

  // Convenience methods
  async get<T>(url: string, options?: OfflineAwareRequestOptions): Promise<T> {
    return this.request<T>(url, { ...options, method: 'GET' });
  }

  async post<T>(
    url: string,
    data?: any,
    options?: OfflineAwareRequestOptions
  ): Promise<T> {
    return this.request<T>(url, {
      ...options,
      method: 'POST',
      body: data,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
  }

  async put<T>(
    url: string,
    data?: any,
    options?: OfflineAwareRequestOptions
  ): Promise<T> {
    return this.request<T>(url, {
      ...options,
      method: 'PUT',
      body: data,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
  }

  async patch<T>(
    url: string,
    data?: any,
    options?: OfflineAwareRequestOptions
  ): Promise<T> {
    return this.request<T>(url, {
      ...options,
      method: 'PATCH',
      body: data,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    });
  }

  async delete<T>(url: string, options?: OfflineAwareRequestOptions): Promise<T> {
    return this.request<T>(url, { ...options, method: 'DELETE' });
  }

  // Upload file with offline support
  async uploadFile<T>(
    url: string,
    file: File,
    options?: OfflineAwareRequestOptions & {
      onProgress?: (progress: number) => void;
      additionalData?: Record<string, string>;
    }
  ): Promise<T> {
    const formData = new FormData();
    formData.append('file', file);

    if (options?.additionalData) {
      Object.entries(options.additionalData).forEach(([key, value]) => {
        formData.append(key, value);
      });
    }

    // File uploads should have high priority by default
    return this.request<T>(url, {
      ...options,
      method: 'POST',
      body: formData,
      priority: 'high',
      // Don't set Content-Type header for FormData
      headers: {
        ...options?.headers,
      },
    });
  }

  // Batch operations with offline support
  async batch<T>(
    requests: Array<{
      url: string;
      method?: string;
      data?: any;
      options?: OfflineAwareRequestOptions;
    }>
  ): Promise<T[]> {
    const results: T[] = [];
    const errors: Error[] = [];

    for (const req of requests) {
      try {
        const result = await this.request<T>(req.url, {
          ...req.options,
          method: req.method || 'GET',
          body: req.data,
          headers: {
            'Content-Type': 'application/json',
            ...req.options?.headers,
          },
        });
        results.push(result);
      } catch (error) {
        errors.push(error as Error);
        logger.error(`Batch request failed: ${req.method || 'GET'} ${req.url}: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    }

    if (errors.length > 0 && results.length === 0) {
      throw new Error(`All batch requests failed. ${errors.length} errors occurred.`);
    }

    return results;
  }

  // Get offline queue status
  getOfflineQueueStatus() {
    return {
      queueSize: offlineQueue.getQueueSize(),
      queue: offlineQueue.getQueue(),
      stats: offlineQueue.getStats(),
    };
  }

  // Clear offline queue
  clearOfflineQueue() {
    offlineQueue.clearQueue();
  }

  // Process offline queue manually
  async processOfflineQueue() {
    return offlineQueue.processQueue();
  }

  // Remove specific request from queue
  removeFromQueue(requestId: string): boolean {
    return offlineQueue.removeRequest(requestId);
  }
}

// Export singleton instance
export const offlineAwareApi = new OfflineAwareApiService();

// Export for React Query integration
export const createOfflineAwareQueryFn = <T>(
  url: string,
  options?: OfflineAwareRequestOptions
) => {
  return async (): Promise<T> => {
    return offlineAwareApi.get<T>(url, options);
  };
};

export const createOfflineAwareMutationFn = <TData, TVariables>(
  url: string | ((variables: TVariables) => string),
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE' = 'POST',
  options?: OfflineAwareRequestOptions
) => {
  return async (variables: TVariables): Promise<TData> => {
    const requestUrl = typeof url === 'function' ? url(variables) : url;
    
    switch (method) {
      case 'POST':
        return offlineAwareApi.post<TData>(requestUrl, variables, options);
      case 'PUT':
        return offlineAwareApi.put<TData>(requestUrl, variables, options);
      case 'PATCH':
        return offlineAwareApi.patch<TData>(requestUrl, variables, options);
      case 'DELETE':
        return offlineAwareApi.delete<TData>(requestUrl, options);
      default:
        throw new Error(`Unsupported method: ${method}`);
    }
  };
};

export default offlineAwareApi;