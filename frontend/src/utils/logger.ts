/**
 * Comprehensive logging system with different levels and contexts
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3,
  FATAL = 4,
}

export interface LogEntry {
  timestamp: Date;
  level: LogLevel;
  message: string;
  context?: string;
  data?: any;
  userId?: string;
  sessionId?: string;
  url?: string;
  userAgent?: string;
  stack?: string;
}

export interface LoggerConfig {
  level: LogLevel;
  enableConsole: boolean;
  enableRemote: boolean;
  enableStorage: boolean;
  maxStorageEntries: number;
  remoteEndpoint?: string;
  contextFilters: string[];
  enableStackTrace: boolean;
}

class Logger {
  private static instance: Logger;
  private config: LoggerConfig;
  private logBuffer: LogEntry[] = [];
  private sessionId: string;

  private constructor() {
    this.sessionId = this.generateSessionId();
    this.config = {
      level: import.meta.env.DEV ? LogLevel.DEBUG : LogLevel.INFO,
      enableConsole: true,
      enableRemote: import.meta.env.PROD,
      enableStorage: true,
      maxStorageEntries: 1000,
      remoteEndpoint: import.meta.env.VITE_LOG_ENDPOINT,
      contextFilters: [],
      enableStackTrace: import.meta.env.DEV,
    };

    // Load stored logs on initialization
    this.loadStoredLogs();
    
    // Set up periodic remote log sending
    if (this.config.enableRemote && this.config.remoteEndpoint) {
      setInterval(() => this.sendLogsToRemote(), 30000); // Every 30 seconds
    }

    // Handle page unload to send remaining logs
    window.addEventListener('beforeunload', () => {
      this.sendLogsToRemote();
    });
  }

  static getInstance(): Logger {
    if (!Logger.instance) {
      Logger.instance = new Logger();
    }
    return Logger.instance;
  }

  private generateSessionId(): string {
    return `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  private shouldLog(level: LogLevel, context?: string): boolean {
    if (level < this.config.level) {
      return false;
    }

    if (context && this.config.contextFilters.length > 0) {
      return this.config.contextFilters.some(filter => 
        context.toLowerCase().includes(filter.toLowerCase())
      );
    }

    return true;
  }

  private createLogEntry(
    level: LogLevel,
    message: string,
    context?: string,
    data?: any
  ): LogEntry {
    const entry: LogEntry = {
      timestamp: new Date(),
      level,
      message,
      context,
      data,
      userId: this.getCurrentUserId(),
      sessionId: this.sessionId,
      url: window.location.href,
      userAgent: navigator.userAgent,
    };

    // Add stack trace for errors and warnings
    if (this.config.enableStackTrace && level >= LogLevel.WARN) {
      entry.stack = new Error().stack;
    }

    return entry;
  }

  private getCurrentUserId(): string | undefined {
    try {
      // Try to get user ID from auth store or localStorage
      const authData = localStorage.getItem('auth-storage');
      if (authData) {
        const parsed = JSON.parse(authData);
        return parsed.state?.user?.id;
      }
    } catch {
      // Ignore errors
    }
    return undefined;
  }

  private formatConsoleMessage(entry: LogEntry): string {
    const timestamp = entry.timestamp.toISOString();
    const context = entry.context ? `[${entry.context}]` : '';
    return `${timestamp} ${context} ${entry.message}`;
  }

  private logToConsole(entry: LogEntry): void {
    if (!this.config.enableConsole) return;

    const message = this.formatConsoleMessage(entry);
    const data = entry.data ? [entry.data] : [];

    switch (entry.level) {
      case LogLevel.DEBUG:
        console.debug(message, ...data);
        break;
      case LogLevel.INFO:
        console.info(message, ...data);
        break;
      case LogLevel.WARN:
        console.warn(message, ...data);
        break;
      case LogLevel.ERROR:
      case LogLevel.FATAL:
        console.error(message, ...data);
        if (entry.stack) {
          console.error('Stack trace:', entry.stack);
        }
        break;
    }
  }

  private storeLog(entry: LogEntry): void {
    if (!this.config.enableStorage) return;

    this.logBuffer.push(entry);

    // Limit buffer size
    if (this.logBuffer.length > this.config.maxStorageEntries) {
      this.logBuffer = this.logBuffer.slice(-this.config.maxStorageEntries);
    }

    // Store in localStorage (with size limit)
    try {
      const logsToStore = this.logBuffer.slice(-100); // Store last 100 logs
      localStorage.setItem('app-logs', JSON.stringify(logsToStore));
    } catch (error) {
      // Storage quota exceeded, clear old logs
      localStorage.removeItem('app-logs');
    }
  }

  private loadStoredLogs(): void {
    try {
      const stored = localStorage.getItem('app-logs');
      if (stored) {
        const logs = JSON.parse(stored);
        this.logBuffer = logs.map((log: any) => ({
          ...log,
          timestamp: new Date(log.timestamp),
        }));
      }
    } catch {
      // Ignore errors loading stored logs
    }
  }

  private async sendLogsToRemote(): Promise<void> {
    if (!this.config.enableRemote || !this.config.remoteEndpoint || this.logBuffer.length === 0) {
      return;
    }

    const logsToSend = [...this.logBuffer];
    this.logBuffer = [];

    try {
      await fetch(this.config.remoteEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          logs: logsToSend,
          sessionId: this.sessionId,
        }),
      });
    } catch (error) {
      // If remote logging fails, put logs back in buffer
      this.logBuffer = [...logsToSend, ...this.logBuffer];
      console.warn('Failed to send logs to remote endpoint:', error);
    }
  }

  // Public logging methods
  debug(message: string, context?: string, data?: any): void {
    this.log(LogLevel.DEBUG, message, context, data);
  }

  info(message: string, context?: string, data?: any): void {
    this.log(LogLevel.INFO, message, context, data);
  }

  warn(message: string, context?: string, data?: any): void {
    this.log(LogLevel.WARN, message, context, data);
  }

  error(message: string, context?: string, data?: any): void {
    this.log(LogLevel.ERROR, message, context, data);
  }

  fatal(message: string, context?: string, data?: any): void {
    this.log(LogLevel.FATAL, message, context, data);
  }

  private log(level: LogLevel, message: string, context?: string, data?: any): void {
    if (!this.shouldLog(level, context)) {
      return;
    }

    const entry = this.createLogEntry(level, message, context, data);
    
    this.logToConsole(entry);
    this.storeLog(entry);
  }

  // Utility methods
  logApiRequest(method: string, url: string, data?: any): void {
    this.debug(`API Request: ${method} ${url}`, 'API', data);
  }

  logApiResponse(method: string, url: string, status: number, data?: any): void {
    const level = status >= 400 ? LogLevel.ERROR : LogLevel.DEBUG;
    this.log(level, `API Response: ${method} ${url} - ${status}`, 'API', data);
  }

  logUserAction(action: string, data?: any): void {
    this.info(`User Action: ${action}`, 'USER', data);
  }

  logPerformance(operation: string, duration: number, data?: any): void {
    this.info(`Performance: ${operation} took ${duration}ms`, 'PERFORMANCE', data);
  }

  logError(error: Error, context?: string, data?: any): void {
    this.error(error.message, context, {
      ...data,
      name: error.name,
      stack: error.stack,
    });
  }

  // Configuration methods
  setLevel(level: LogLevel): void {
    this.config.level = level;
  }

  setContextFilters(filters: string[]): void {
    this.config.contextFilters = filters;
  }

  enableRemoteLogging(endpoint: string): void {
    this.config.enableRemote = true;
    this.config.remoteEndpoint = endpoint;
  }

  disableRemoteLogging(): void {
    this.config.enableRemote = false;
  }

  // Export methods
  exportLogs(): LogEntry[] {
    return [...this.logBuffer];
  }

  exportLogsAsJson(): string {
    return JSON.stringify(this.logBuffer, null, 2);
  }

  exportLogsAsCsv(): string {
    const headers = ['timestamp', 'level', 'message', 'context', 'userId', 'url'];
    const rows = this.logBuffer.map(entry => [
      entry.timestamp.toISOString(),
      LogLevel[entry.level],
      entry.message,
      entry.context || '',
      entry.userId || '',
      entry.url || '',
    ]);

    return [headers, ...rows].map(row => row.join(',')).join('\n');
  }

  // Clear methods
  clearLogs(): void {
    this.logBuffer = [];
    localStorage.removeItem('app-logs');
  }

  clearStoredLogs(): void {
    localStorage.removeItem('app-logs');
  }
}

// Create and export singleton instance
export const logger = Logger.getInstance();

// Convenience functions
export const log = {
  debug: (message: string, context?: string, data?: any) => logger.debug(message, context, data),
  info: (message: string, context?: string, data?: any) => logger.info(message, context, data),
  warn: (message: string, context?: string, data?: any) => logger.warn(message, context, data),
  error: (message: string, context?: string, data?: any) => logger.error(message, context, data),
  fatal: (message: string, context?: string, data?: any) => logger.fatal(message, context, data),
  
  // Specialized logging
  api: {
    request: (method: string, url: string, data?: any) => logger.logApiRequest(method, url, data),
    response: (method: string, url: string, status: number, data?: any) => 
      logger.logApiResponse(method, url, status, data),
  },
  
  user: (action: string, data?: any) => logger.logUserAction(action, data),
  performance: (operation: string, duration: number, data?: any) => 
    logger.logPerformance(operation, duration, data),
  exception: (error: Error, context?: string, data?: any) => logger.logError(error, context, data),
};

// React hook for using logger
export const useLogger = () => {
  return {
    logger,
    log,
    exportLogs: () => logger.exportLogs(),
    clearLogs: () => logger.clearLogs(),
  };
};

// Performance timing utility
export const withPerformanceLogging = <T extends (...args: any[]) => any>(
  fn: T,
  operationName: string,
  context?: string
): T => {
  return ((...args: any[]) => {
    const start = performance.now();
    const result = fn(...args);
    
    if (result instanceof Promise) {
      return result.finally(() => {
        const duration = performance.now() - start;
        logger.logPerformance(operationName, duration, { context });
      });
    } else {
      const duration = performance.now() - start;
      logger.logPerformance(operationName, duration, { context });
      return result;
    }
  }) as T;
};

// Error boundary logging
export const logErrorBoundary = (error: Error, errorInfo: any) => {
  logger.fatal('React Error Boundary', 'REACT', {
    error: {
      name: error.name,
      message: error.message,
      stack: error.stack,
    },
    errorInfo,
  });
};