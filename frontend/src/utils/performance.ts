/**
 * Performance monitoring and optimization utilities
 */

import { logger } from './logger';

// Performance metrics interface
export interface PerformanceMetric {
  name: string;
  value: number;
  unit: 'ms' | 'bytes' | 'count' | 'score';
  timestamp: number;
  tags?: Record<string, string>;
  context?: string;
}

// Web Vitals metrics
export interface WebVitalsMetric {
  name: 'CLS' | 'FID' | 'FCP' | 'LCP' | 'TTFB';
  value: number;
  rating: 'good' | 'needs-improvement' | 'poor';
  delta: number;
  id: string;
  navigationType: string;
}

// Performance observer for custom metrics
class PerformanceMonitor {
  private metrics: PerformanceMetric[] = [];
  private observers: PerformanceObserver[] = [];
  private isEnabled: boolean;

  constructor() {
    this.isEnabled = import.meta.env.VITE_ENABLE_PERFORMANCE_MONITORING !== 'false';
    
    if (this.isEnabled && typeof window !== 'undefined') {
      this.initializeObservers();
      this.setupWebVitals();
    }
  }

  private initializeObservers(): void {
    try {
      // Navigation timing
      if ('PerformanceObserver' in window) {
        const navObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.entryType === 'navigation') {
              this.recordNavigationMetrics(entry as PerformanceNavigationTiming);
            }
          }
        });
        navObserver.observe({ entryTypes: ['navigation'] });
        this.observers.push(navObserver);

        // Resource timing
        const resourceObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.entryType === 'resource') {
              this.recordResourceMetric(entry as PerformanceResourceTiming);
            }
          }
        });
        resourceObserver.observe({ entryTypes: ['resource'] });
        this.observers.push(resourceObserver);

        // Long tasks
        const longTaskObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.entryType === 'longtask') {
              this.recordLongTask(entry);
            }
          }
        });
        longTaskObserver.observe({ entryTypes: ['longtask'] });
        this.observers.push(longTaskObserver);

        // Layout shifts
        const layoutShiftObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.entryType === 'layout-shift' && !(entry as any).hadRecentInput) {
              this.recordLayoutShift(entry);
            }
          }
        });
        layoutShiftObserver.observe({ entryTypes: ['layout-shift'] });
        this.observers.push(layoutShiftObserver);
      }
    } catch (error) {
      logger.warn(`Failed to initialize performance observers: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  private recordNavigationMetrics(entry: PerformanceNavigationTiming): void {
    const metrics: PerformanceMetric[] = [
      {
        name: 'dns_lookup',
        value: entry.domainLookupEnd - entry.domainLookupStart,
        unit: 'ms',
        timestamp: Date.now(),
        context: 'navigation',
      },
      {
        name: 'tcp_connection',
        value: entry.connectEnd - entry.connectStart,
        unit: 'ms',
        timestamp: Date.now(),
        context: 'navigation',
      },
      {
        name: 'request_response',
        value: entry.responseEnd - entry.requestStart,
        unit: 'ms',
        timestamp: Date.now(),
        context: 'navigation',
      },
      {
        name: 'dom_content_loaded',
        value: entry.domContentLoadedEventEnd - entry.domContentLoadedEventStart,
        unit: 'ms',
        timestamp: Date.now(),
        context: 'navigation',
      },
      {
        name: 'load_complete',
        value: entry.loadEventEnd - entry.loadEventStart,
        unit: 'ms',
        timestamp: Date.now(),
        context: 'navigation',
      },
    ];

    metrics.forEach(metric => this.recordMetric(metric));
  }

  private recordResourceMetric(entry: PerformanceResourceTiming): void {
    // Only track significant resources
    if (entry.transferSize > 10000 || entry.duration > 100) {
      const resourceType = this.getResourceType(entry.name);
      
      this.recordMetric({
        name: 'resource_load_time',
        value: entry.duration,
        unit: 'ms',
        timestamp: Date.now(),
        tags: {
          resource_type: resourceType,
          resource_size: entry.transferSize.toString(),
        },
        context: 'resource',
      });
    }
  }

  private recordLongTask(entry: PerformanceEntry): void {
    this.recordMetric({
      name: 'long_task',
      value: entry.duration,
      unit: 'ms',
      timestamp: Date.now(),
      context: 'performance',
    });

    // Log warning for very long tasks
    if (entry.duration > 100) {
      logger.warn(`Long task detected: ${entry.duration}ms`);
    }
  }

  private recordLayoutShift(entry: PerformanceEntry): void {
    this.recordMetric({
      name: 'layout_shift',
      value: (entry as any).value,
      unit: 'score',
      timestamp: Date.now(),
      context: 'performance',
    });
  }

  private getResourceType(url: string): string {
    if (url.includes('.js')) return 'javascript';
    if (url.includes('.css')) return 'stylesheet';
    if (url.match(/\.(png|jpg|jpeg|gif|svg|webp)$/)) return 'image';
    if (url.match(/\.(woff|woff2|ttf|eot)$/)) return 'font';
    if (url.includes('/api/')) return 'api';
    return 'other';
  }

  private setupWebVitals(): void {
    // Try to import web-vitals dynamically to avoid bundle bloat
    try {
      // For now, we'll implement basic web vitals tracking without the library
      this.setupBasicWebVitals();
    } catch (error) {
      logger.info('Web Vitals tracking not available');
    }
  }

  private setupBasicWebVitals(): void {
    // Basic FCP tracking
    if ('PerformanceObserver' in window) {
      try {
        const paintObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.name === 'first-contentful-paint') {
              this.recordMetric({
                name: 'fcp',
                value: entry.startTime,
                unit: 'ms',
                timestamp: Date.now(),
                context: 'web_vitals',
              });
            }
          }
        });
        paintObserver.observe({ entryTypes: ['paint'] });
        this.observers.push(paintObserver);
      } catch (error) {
        logger.warn('Failed to setup paint observer');
      }
    }
  }

  private onWebVital(metric: WebVitalsMetric): void {
    this.recordMetric({
      name: metric.name.toLowerCase(),
      value: metric.value,
      unit: metric.name === 'CLS' ? 'score' : 'ms',
      timestamp: Date.now(),
      tags: {
        rating: metric.rating,
        navigation_type: metric.navigationType,
      },
      context: 'web_vitals',
    });

    // Log poor web vitals
    if (metric.rating === 'poor') {
      logger.warn(`Poor ${metric.name}: ${metric.value}${metric.name === 'CLS' ? '' : 'ms'}`);
    }
  }

  public recordMetric(metric: PerformanceMetric): void {
    if (!this.isEnabled) return;

    this.metrics.push(metric);
    
    // Log significant performance issues
    if (metric.unit === 'ms' && metric.value > 1000) {
      logger.warn(`Slow ${metric.name}: ${metric.value}ms`);
    }

    // Send to analytics service (implement based on your needs)
    this.sendToAnalytics(metric);
  }

  private sendToAnalytics(metric: PerformanceMetric): void {
    // Implement your analytics service integration here
    // Example: Google Analytics, DataDog, New Relic, etc.
    if (import.meta.env.DEV) {
      console.log('Performance Metric:', metric);
    }
  }

  public getMetrics(): PerformanceMetric[] {
    return [...this.metrics];
  }

  public getMetricsByName(name: string): PerformanceMetric[] {
    return this.metrics.filter(metric => metric.name === name);
  }

  public getAverageMetric(name: string): number {
    const metrics = this.getMetricsByName(name);
    if (metrics.length === 0) return 0;
    
    const sum = metrics.reduce((acc, metric) => acc + metric.value, 0);
    return sum / metrics.length;
  }

  public clearMetrics(): void {
    this.metrics = [];
  }

  public destroy(): void {
    this.observers.forEach(observer => observer.disconnect());
    this.observers = [];
    this.clearMetrics();
  }
}

// Singleton instance
export const performanceMonitor = new PerformanceMonitor();

// Utility functions
export const measureFunction = <T extends (...args: any[]) => any>(
  fn: T,
  name: string
): T => {
  return ((...args: any[]) => {
    const start = performance.now();
    const result = fn(...args);
    const duration = performance.now() - start;
    
    performanceMonitor.recordMetric({
      name: `function_${name}`,
      value: duration,
      unit: 'ms',
      timestamp: Date.now(),
      context: 'function_timing',
    });

    return result;
  }) as T;
};

export const measureAsyncFunction = <T extends (...args: any[]) => Promise<any>>(
  fn: T,
  name: string
): T => {
  return (async (...args: any[]) => {
    const start = performance.now();
    try {
      const result = await fn(...args);
      const duration = performance.now() - start;
      
      performanceMonitor.recordMetric({
        name: `async_function_${name}`,
        value: duration,
        unit: 'ms',
        timestamp: Date.now(),
        context: 'async_function_timing',
      });

      return result;
    } catch (error) {
      const duration = performance.now() - start;
      
      performanceMonitor.recordMetric({
        name: `async_function_${name}_error`,
        value: duration,
        unit: 'ms',
        timestamp: Date.now(),
        context: 'async_function_timing',
      });

      throw error;
    }
  }) as T;
};

// Memory monitoring
export const getMemoryUsage = (): Record<string, number> | null => {
  if ('memory' in performance) {
    const memory = (performance as any).memory;
    return {
      usedJSHeapSize: memory.usedJSHeapSize,
      totalJSHeapSize: memory.totalJSHeapSize,
      jsHeapSizeLimit: memory.jsHeapSizeLimit,
    };
  }
  return null;
};

export const monitorMemoryUsage = (intervalMs: number = 30000): (() => void) => {
  const interval = setInterval(() => {
    const memory = getMemoryUsage();
    if (memory) {
      if (memory.usedJSHeapSize && memory.totalJSHeapSize && memory.jsHeapSizeLimit) {
        performanceMonitor.recordMetric({
          name: 'memory_usage',
          value: memory.usedJSHeapSize,
          unit: 'bytes',
          timestamp: Date.now(),
          tags: {
            total_heap: memory.totalJSHeapSize.toString(),
            heap_limit: memory.jsHeapSizeLimit.toString(),
          },
          context: 'memory',
        });

        // Warn if memory usage is high
        const usagePercent = (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100;
        if (usagePercent > 80) {
          logger.warn(`High memory usage: ${usagePercent.toFixed(1)}%`);
        }
      }
    }
  }, intervalMs);

  return () => clearInterval(interval);
};

// Bundle size monitoring
export const getBundleSize = async (): Promise<number> => {
  try {
    const response = await fetch('/stats.json');
    const stats = await response.json();
    return stats.assets.reduce((total: number, asset: any) => total + asset.size, 0);
  } catch {
    return 0;
  }
};

// Performance budget checker
export interface PerformanceBudget {
  metric: string;
  threshold: number;
  unit: string;
}

export const checkPerformanceBudget = (
  budgets: PerformanceBudget[]
): { passed: boolean; violations: string[] } => {
  const violations: string[] = [];

  budgets.forEach(budget => {
    const average = performanceMonitor.getAverageMetric(budget.metric);
    if (average > budget.threshold) {
      violations.push(
        `${budget.metric} (${average.toFixed(2)}${budget.unit}) exceeds budget (${budget.threshold}${budget.unit})`
      );
    }
  });

  return {
    passed: violations.length === 0,
    violations,
  };
};

// Default performance budgets
export const DEFAULT_PERFORMANCE_BUDGETS: PerformanceBudget[] = [
  { metric: 'fcp', threshold: 1800, unit: 'ms' },
  { metric: 'lcp', threshold: 2500, unit: 'ms' },
  { metric: 'fid', threshold: 100, unit: 'ms' },
  { metric: 'cls', threshold: 0.1, unit: 'score' },
  { metric: 'ttfb', threshold: 800, unit: 'ms' },
];

export default {
  performanceMonitor,
  measureFunction,
  measureAsyncFunction,
  getMemoryUsage,
  monitorMemoryUsage,
  getBundleSize,
  checkPerformanceBudget,
  DEFAULT_PERFORMANCE_BUDGETS,
};