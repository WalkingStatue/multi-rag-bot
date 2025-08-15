import { useEffect, useRef, useCallback } from 'react';
import { performanceMonitor } from '../utils/performance';
import { logger } from '../utils/logger';

/**
 * Hook for tracking component render performance
 */
export function useRenderPerformance(componentName: string) {
  const renderStartTime = useRef<number>(0);
  const renderCount = useRef<number>(0);

  useEffect(() => {
    renderStartTime.current = performance.now();
    renderCount.current += 1;
  });

  useEffect(() => {
    const renderTime = performance.now() - renderStartTime.current;
    
    performanceMonitor.recordMetric({
      name: 'component_render_time',
      value: renderTime,
      unit: 'ms',
      timestamp: Date.now(),
      tags: {
        component: componentName,
        render_count: renderCount.current.toString(),
      },
      context: 'component_performance',
    });

    // Warn about slow renders
    if (renderTime > 16) { // 60fps threshold
      logger.warn(`Slow render detected in ${componentName}: ${renderTime.toFixed(2)}ms`);
    }
  });

  return {
    renderCount: renderCount.current,
  };
}

/**
 * Hook for tracking API call performance
 */
export function useApiPerformance() {
  const trackApiCall = useCallback((
    endpoint: string,
    method: string,
    startTime: number,
    endTime: number,
    success: boolean,
    statusCode?: number
  ) => {
    const duration = endTime - startTime;
    
    performanceMonitor.recordMetric({
      name: 'api_call_duration',
      value: duration,
      unit: 'ms',
      timestamp: Date.now(),
      tags: {
        endpoint,
        method,
        success: success.toString(),
        status_code: statusCode?.toString() || 'unknown',
      },
      context: 'api_performance',
    });

    // Track slow API calls
    if (duration > 3000) {
      logger.warn(`Slow API call: ${method} ${endpoint} took ${duration}ms`);
    }
  }, []);

  return { trackApiCall };
}

/**
 * Hook for tracking user interactions
 */
export function useInteractionPerformance() {
  const trackInteraction = useCallback((
    interactionType: string,
    elementId?: string,
    duration?: number
  ) => {
    performanceMonitor.recordMetric({
      name: 'user_interaction',
      value: duration || 0,
      unit: 'ms',
      timestamp: Date.now(),
      tags: {
        interaction_type: interactionType,
        element_id: elementId || 'unknown',
      },
      context: 'user_interaction',
    });
  }, []);

  const trackClick = useCallback((elementId: string) => {
    trackInteraction('click', elementId);
  }, [trackInteraction]);

  const trackFormSubmit = useCallback((formId: string, duration: number) => {
    trackInteraction('form_submit', formId, duration);
  }, [trackInteraction]);

  return {
    trackInteraction,
    trackClick,
    trackFormSubmit,
  };
}

/**
 * Hook for tracking page load performance
 */
export function usePagePerformance(pageName: string) {
  const pageLoadStart = useRef<number>(0);

  useEffect(() => {
    pageLoadStart.current = performance.now();

    return () => {
      const pageLoadTime = performance.now() - pageLoadStart.current;
      
      performanceMonitor.recordMetric({
        name: 'page_load_time',
        value: pageLoadTime,
        unit: 'ms',
        timestamp: Date.now(),
        tags: {
          page: pageName,
        },
        context: 'page_performance',
      });
    };
  }, [pageName]);

  const trackPageInteraction = useCallback((interactionType: string) => {
    const timeOnPage = performance.now() - pageLoadStart.current;
    
    performanceMonitor.recordMetric({
      name: 'time_to_interaction',
      value: timeOnPage,
      unit: 'ms',
      timestamp: Date.now(),
      tags: {
        page: pageName,
        interaction_type: interactionType,
      },
      context: 'page_performance',
    });
  }, [pageName]);

  return { trackPageInteraction };
}

/**
 * Hook for tracking bundle size and loading performance
 */
export function useBundlePerformance() {
  useEffect(() => {
    // Track initial bundle load time
    if (window.performance && window.performance.timing) {
      const timing = window.performance.timing;
      const loadTime = timing.loadEventEnd - timing.navigationStart;
      const domContentLoadedTime = timing.domContentLoadedEventEnd - timing.navigationStart;
      
      performanceMonitor.recordMetric({
        name: 'bundle_load_time',
        value: loadTime,
        unit: 'ms',
        timestamp: Date.now(),
        tags: {
          dom_content_loaded: domContentLoadedTime.toString(),
        },
        context: 'bundle_performance',
      });
    }

    // Track resource loading
    if (window.performance && window.performance.getEntriesByType) {
      const resources = window.performance.getEntriesByType('resource') as PerformanceResourceTiming[];
      
      resources.forEach((resource) => {
        if (resource.name.includes('.js') || resource.name.includes('.css')) {
          performanceMonitor.recordMetric({
            name: 'resource_load_time',
            value: resource.responseEnd - resource.startTime,
            unit: 'ms',
            timestamp: Date.now(),
            tags: {
              resource_name: resource.name.split('/').pop() || 'unknown',
              resource_type: resource.name.includes('.js') ? 'javascript' : 'css',
              transfer_size: resource.transferSize?.toString() || '0',
            },
            context: 'resource_performance',
          });
        }
      });
    }
  }, []);
}

/**
 * Hook for tracking memory usage over time
 */
export function useMemoryTracking(intervalMs: number = 30000) {
  useEffect(() => {
    const trackMemory = () => {
      if ('memory' in performance) {
        const memory = (performance as any).memory;
        if (memory && memory.usedJSHeapSize) {
          performanceMonitor.recordMetric({
            name: 'memory_usage_tracking',
            value: memory.usedJSHeapSize,
            unit: 'bytes',
            timestamp: Date.now(),
            tags: {
              total_heap: memory.totalJSHeapSize?.toString() || '0',
              heap_limit: memory.jsHeapSizeLimit?.toString() || '0',
            },
            context: 'memory_tracking',
          });
        }
      }
    };

    // Track immediately
    trackMemory();

    // Set up interval tracking
    const interval = setInterval(trackMemory, intervalMs);

    return () => clearInterval(interval);
  }, [intervalMs]);
}

/**
 * Hook for tracking error performance impact
 */
export function useErrorPerformance() {
  const trackError = useCallback((
    errorType: string,
    errorMessage: string,
    recoveryTime?: number
  ) => {
    performanceMonitor.recordMetric({
      name: 'error_impact',
      value: recoveryTime || 0,
      unit: 'ms',
      timestamp: Date.now(),
      tags: {
        error_type: errorType,
        error_message: errorMessage.substring(0, 100), // Limit message length
        has_recovery_time: (recoveryTime !== undefined).toString(),
      },
      context: 'error_performance',
    });
  }, []);

  return { trackError };
}