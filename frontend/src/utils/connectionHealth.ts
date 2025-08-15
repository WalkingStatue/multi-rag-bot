/**
 * Connection health monitoring utilities
 */

export interface ConnectionHealthStatus {
  isOnline: boolean;
  lastCheck: number;
  consecutiveFailures: number;
}

export class ConnectionHealthMonitor {
  private status: ConnectionHealthStatus = {
    isOnline: navigator.onLine,
    lastCheck: Date.now(),
    consecutiveFailures: 0
  };
  
  private listeners: Set<(status: ConnectionHealthStatus) => void> = new Set();
  private checkInterval: number | null = null;
  private readonly CHECK_INTERVAL = 30000; // 30 seconds
  private readonly MAX_FAILURES = 3;

  constructor() {
    // Listen to browser online/offline events
    window.addEventListener('online', this.handleOnline);
    window.addEventListener('offline', this.handleOffline);
    
    this.startHealthCheck();
  }

  private handleOnline = () => {
    this.updateStatus({
      isOnline: true,
      consecutiveFailures: 0,
      lastCheck: Date.now()
    });
  };

  private handleOffline = () => {
    this.updateStatus({
      isOnline: false,
      lastCheck: Date.now()
    });
  };

  private updateStatus(updates: Partial<ConnectionHealthStatus>) {
    this.status = { ...this.status, ...updates };
    this.notifyListeners();
  }

  private notifyListeners() {
    this.listeners.forEach(listener => {
      try {
        listener(this.status);
      } catch (error) {
        // Error in connection health listener
      }
    });
  }

  private startHealthCheck() {
    if (this.checkInterval) return;

    this.checkInterval = setInterval(async () => {
      try {
        // Simple connectivity check using the API base URL
        const apiUrl = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';
        const response = await fetch(`${apiUrl}/health`, {
          method: 'GET',
          cache: 'no-cache',
          signal: AbortSignal.timeout(5000)
        });

        if (response.ok) {
          this.updateStatus({
            isOnline: true,
            consecutiveFailures: 0,
            lastCheck: Date.now()
          });
        } else {
          throw new Error(`Health check failed: ${response.status}`);
        }
      } catch (error) {
        const failures = this.status.consecutiveFailures + 1;
        this.updateStatus({
          isOnline: failures < this.MAX_FAILURES,
          consecutiveFailures: failures,
          lastCheck: Date.now()
        });
      }
    }, this.CHECK_INTERVAL);
  }

  public subscribe(listener: (status: ConnectionHealthStatus) => void): () => void {
    this.listeners.add(listener);
    
    // Immediately notify with current status
    listener(this.status);
    
    return () => {
      this.listeners.delete(listener);
    };
  }

  public getStatus(): ConnectionHealthStatus {
    return { ...this.status };
  }

  public isHealthy(): boolean {
    return this.status.isOnline && this.status.consecutiveFailures < this.MAX_FAILURES;
  }

  public destroy() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
    }
    
    window.removeEventListener('online', this.handleOnline);
    window.removeEventListener('offline', this.handleOffline);
    this.listeners.clear();
  }
}

// Export singleton instance
export const connectionHealthMonitor = new ConnectionHealthMonitor();