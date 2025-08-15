import React from 'react';
import { logger } from '../utils/logger';

export interface QueuedRequest {
  id: string;
  url: string;
  method: string;
  headers: Record<string, string>;
  body?: string;
  timestamp: number;
  retryCount: number;
  maxRetries: number;
  priority: 'low' | 'medium' | 'high';
  metadata?: Record<string, any>;
}

export interface OfflineQueueOptions {
  maxQueueSize: number;
  maxRetries: number;
  retryDelay: number;
  storageKey: string;
  enablePersistence: boolean;
}

export class OfflineQueue {
  private queue: QueuedRequest[] = [];
  private isProcessing = false;
  private options: OfflineQueueOptions;
  private listeners: Set<(queue: QueuedRequest[]) => void> = new Set();

  constructor(options: Partial<OfflineQueueOptions> = {}) {
    this.options = {
      maxQueueSize: 100,
      maxRetries: 3,
      retryDelay: 1000,
      storageKey: 'offline_queue',
      enablePersistence: true,
      ...options,
    };

    this.loadFromStorage();
    this.setupNetworkListeners();
  }

  private setupNetworkListeners(): void {
    window.addEventListener('online', () => {
      logger.info('Network came online, processing offline queue');
      this.processQueue();
    });

    window.addEventListener('offline', () => {
      logger.info('Network went offline, requests will be queued');
    });
  }

  private loadFromStorage(): void {
    if (!this.options.enablePersistence) return;

    try {
      const stored = localStorage.getItem(this.options.storageKey);
      if (stored) {
        this.queue = JSON.parse(stored);
        logger.info(`Loaded ${this.queue.length} requests from offline queue`);
      }
    } catch (error) {
      logger.error(`Failed to load offline queue from storage: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private saveToStorage(): void {
    if (!this.options.enablePersistence) return;

    try {
      localStorage.setItem(this.options.storageKey, JSON.stringify(this.queue));
    } catch (error) {
      logger.error(`Failed to save offline queue to storage: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private notifyListeners(): void {
    this.listeners.forEach(listener => {
      try {
        listener([...this.queue]);
      } catch (error) {
        logger.error(`Error in queue listener: ${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    });
  }

  public addRequest(
    url: string,
    method: string,
    headers: Record<string, string> = {},
    body?: string,
    options: {
      priority?: 'low' | 'medium' | 'high';
      maxRetries?: number;
      metadata?: Record<string, any>;
    } = {}
  ): string {
    // Check queue size limit
    if (this.queue.length >= this.options.maxQueueSize) {
      // Remove oldest low priority request to make room
      const oldestLowPriority = this.queue.findIndex(req => req.priority === 'low');
      if (oldestLowPriority !== -1) {
        this.queue.splice(oldestLowPriority, 1);
        logger.warn('Removed oldest low priority request due to queue size limit');
      } else {
        throw new Error('Offline queue is full');
      }
    }

    const request: QueuedRequest = {
      id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      url,
      method: method.toUpperCase(),
      headers,
      timestamp: Date.now(),
      retryCount: 0,
      maxRetries: options.maxRetries ?? this.options.maxRetries,
      priority: options.priority ?? 'medium',
    };

    if (body) {
      request.body = body;
    }

    if (options.metadata) {
      request.metadata = options.metadata;
    }

    // Insert based on priority
    const insertIndex = this.findInsertIndex(request.priority);
    this.queue.splice(insertIndex, 0, request);

    this.saveToStorage();
    this.notifyListeners();

    logger.info(`Added request to offline queue: ${method} ${url} (priority: ${request.priority})`);
    return request.id;
  }

  private findInsertIndex(priority: 'low' | 'medium' | 'high'): number {
    const priorityOrder: Record<'low' | 'medium' | 'high', number> = { high: 3, medium: 2, low: 1 };
    const requestPriority = priorityOrder[priority];

    for (let i = 0; i < this.queue.length; i++) {
      const queueItem = this.queue[i];
      if (queueItem && queueItem.priority) {
        const currentPriority = priorityOrder[queueItem.priority];
        if (currentPriority && currentPriority < requestPriority) {
          return i;
        }
      }
    }
    return this.queue.length;
  }

  public removeRequest(id: string): boolean {
    const index = this.queue.findIndex(req => req.id === id);
    if (index !== -1) {
      this.queue.splice(index, 1);
      this.saveToStorage();
      this.notifyListeners();
      logger.info(`Removed request from offline queue: ${id}`);
      return true;
    }
    return false;
  }

  public clearQueue(): void {
    this.queue = [];
    this.saveToStorage();
    this.notifyListeners();
    logger.info('Cleared offline queue');
  }

  public getQueue(): QueuedRequest[] {
    return [...this.queue];
  }

  public getQueueSize(): number {
    return this.queue.length;
  }

  public subscribe(listener: (queue: QueuedRequest[]) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  public async processQueue(): Promise<void> {
    if (this.isProcessing || !navigator.onLine) {
      return;
    }

    this.isProcessing = true;
    logger.info(`Processing offline queue with ${this.queue.length} requests`);

    const processedRequests: string[] = [];
    const failedRequests: string[] = [];

    for (const request of [...this.queue]) {
      try {
        const success = await this.executeRequest(request);
        if (success) {
          processedRequests.push(request.id);
          this.removeRequest(request.id);
        } else {
          request.retryCount++;
          if (request.retryCount >= request.maxRetries) {
            failedRequests.push(request.id);
            this.removeRequest(request.id);
            logger.error(`Request failed after ${request.maxRetries} retries: ${request.method} ${request.url}`);
          } else {
            logger.warn(`Request failed, will retry (${request.retryCount}/${request.maxRetries}): ${request.method} ${request.url}`);
          }
        }

        // Add delay between requests to avoid overwhelming the server
        if (this.queue.length > 0) {
          await new Promise(resolve => setTimeout(resolve, this.options.retryDelay));
        }
      } catch (error) {
        logger.error(`Error processing queued request: ${error instanceof Error ? error.message : 'Unknown error'}`);
        request.retryCount++;
        if (request.retryCount >= request.maxRetries) {
          failedRequests.push(request.id);
          this.removeRequest(request.id);
        }
      }
    }

    this.isProcessing = false;

    if (processedRequests.length > 0 || failedRequests.length > 0) {
      logger.info(`Queue processing complete. Processed: ${processedRequests.length}, Failed: ${failedRequests.length}`);
    }
  }

  private async executeRequest(request: QueuedRequest): Promise<boolean> {
    try {
      const fetchOptions: RequestInit = {
        method: request.method,
        headers: request.headers,
      };

      if (request.body) {
        fetchOptions.body = request.body;
      }

      const response = await fetch(request.url, fetchOptions);

      if (response.ok) {
        logger.info(`Successfully executed queued request: ${request.method} ${request.url}`);
        return true;
      } else {
        logger.warn(`Queued request failed with status ${response.status}: ${request.method} ${request.url}`);
        return false;
      }
    } catch (error) {
      logger.error(`Failed to execute queued request: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return false;
    }
  }

  public getStats(): {
    totalRequests: number;
    byPriority: Record<string, number>;
    oldestRequest?: number;
    averageAge: number;
  } {
    const now = Date.now();
    const byPriority = this.queue.reduce((acc, req) => {
      acc[req.priority] = (acc[req.priority] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const ages = this.queue.map(req => now - req.timestamp);
    const averageAge = ages.length > 0 ? ages.reduce((sum, age) => sum + age, 0) / ages.length : 0;
    const oldestRequest = ages.length > 0 ? Math.max(...ages) : undefined;

    const result: {
      totalRequests: number;
      byPriority: Record<string, number>;
      averageAge: number;
      oldestRequest?: number;
    } = {
      totalRequests: this.queue.length,
      byPriority,
      averageAge,
    };

    if (oldestRequest !== undefined) {
      result.oldestRequest = oldestRequest;
    }

    return result;
  }
}

// Global offline queue instance
export const offlineQueue = new OfflineQueue();

// Hook for React components
export const useOfflineQueue = () => {
  const [queue, setQueue] = React.useState<QueuedRequest[]>(offlineQueue.getQueue());

  React.useEffect(() => {
    const unsubscribe = offlineQueue.subscribe(setQueue);
    return unsubscribe;
  }, []);

  return {
    queue,
    queueSize: queue.length,
    addRequest: offlineQueue.addRequest.bind(offlineQueue),
    removeRequest: offlineQueue.removeRequest.bind(offlineQueue),
    clearQueue: offlineQueue.clearQueue.bind(offlineQueue),
    processQueue: offlineQueue.processQueue.bind(offlineQueue),
    stats: offlineQueue.getStats(),
  };
};