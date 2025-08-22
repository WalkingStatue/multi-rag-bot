import React, { useEffect, useState } from 'react';
import { performanceMonitor } from '../../utils/performance';
import { useBundlePerformance, useMemoryTracking } from '../../hooks/usePerformance';
import { logger } from '../../utils/logger';
import { getEnvVar } from '../../config/environment';

interface PerformanceOptimizerProps {
  children: React.ReactNode;
  enableMemoryTracking?: boolean;
  memoryTrackingInterval?: number;
  enablePerformanceWarnings?: boolean;
}

/**
 * Performance optimizer component that wraps the app and provides
 * performance monitoring, optimization, and warnings
 */
export const PerformanceOptimizer: React.FC<PerformanceOptimizerProps> = ({
  children,
  enableMemoryTracking = true,
  memoryTrackingInterval = 30000,
  enablePerformanceWarnings = true,
}) => {
  const [isLowPerformanceDevice, setIsLowPerformanceDevice] = useState(false);
  
  // Initialize bundle performance tracking
  useBundlePerformance();
  
  // Initialize memory tracking if enabled
  if (enableMemoryTracking) {
    useMemoryTracking(memoryTrackingInterval);
  }

  useEffect(() => {
    // Detect low-performance devices
    detectDevicePerformance();

    // Set up performance warnings
    if (enablePerformanceWarnings) {
      setupPerformanceWarnings();
    }
  }, [enablePerformanceWarnings]);

  const detectDevicePerformance = () => {
    // Check hardware concurrency (CPU cores)
    const cores = navigator.hardwareConcurrency || 1;
    
    // Check memory (if available)
    const memory = (navigator as any).deviceMemory;
    
    // Check connection (if available)
    const connection = (navigator as any).connection;
    const effectiveType = connection?.effectiveType;
    
    // Determine if this is a low-performance device
    const isLowPerf = cores <= 2 || 
                     (memory && memory <= 2) || 
                     effectiveType === 'slow-2g' || 
                     effectiveType === '2g';
    
    setIsLowPerformanceDevice(isLowPerf);
    
    if (isLowPerf) {
      logger.info('Low-performance device detected, enabling optimizations');
      
      // Record device performance metrics
      performanceMonitor.recordMetric({
        name: 'device_performance',
        value: cores,
        unit: 'count',
        timestamp: Date.now(),
        tags: {
          memory: memory?.toString() || 'unknown',
          connection_type: effectiveType || 'unknown',
          is_low_performance: 'true',
        },
        context: 'device_detection',
      });
    }
  };

  const setupPerformanceWarnings = () => {
    // Monitor long tasks
    if ('PerformanceObserver' in window) {
      try {
        const longTaskObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            if (entry.duration > 50) { // Tasks longer than 50ms
              logger.warn(`Long task detected: ${entry.duration.toFixed(2)}ms`);
              
              performanceMonitor.recordMetric({
                name: 'long_task',
                value: entry.duration,
                unit: 'ms',
                timestamp: Date.now(),
                tags: {
                  task_name: entry.name || 'unknown',
                },
                context: 'performance_warning',
              });
            }
          }
        });
        
        longTaskObserver.observe({ entryTypes: ['longtask'] });
      } catch (error) {
        logger.warn('Long task observer not supported');
      }
    }

    // Monitor layout shifts
    if ('PerformanceObserver' in window) {
      try {
        const layoutShiftObserver = new PerformanceObserver((list) => {
          for (const entry of list.getEntries()) {
            const layoutShiftEntry = entry as any;
            if (layoutShiftEntry.value > 0.1) { // Significant layout shift
              logger.warn(`Layout shift detected: ${layoutShiftEntry.value.toFixed(4)}`);
              
              performanceMonitor.recordMetric({
                name: 'layout_shift',
                value: layoutShiftEntry.value,
                unit: 'score',
                timestamp: Date.now(),
                context: 'performance_warning',
              });
            }
          }
        });
        
        layoutShiftObserver.observe({ entryTypes: ['layout-shift'] });
      } catch (error) {
        logger.warn('Layout shift observer not supported');
      }
    }
  };

  // Apply performance optimizations for low-performance devices
  const optimizationStyles: React.CSSProperties = isLowPerformanceDevice ? {
    // Reduce animations and transitions
    '--animation-duration': '0.1s',
    '--transition-duration': '0.1s',
    // Reduce shadows and effects
    '--box-shadow': 'none',
    '--backdrop-filter': 'none',
  } as React.CSSProperties : {};

  return (
    <div 
      className={`performance-optimizer ${isLowPerformanceDevice ? 'low-performance' : ''}`}
      style={optimizationStyles}
    >
      {children}
      {isLowPerformanceDevice && (
        <div className="performance-notice" style={{
          position: 'fixed',
          bottom: '10px',
          right: '10px',
          background: 'rgba(255, 193, 7, 0.9)',
          color: '#000',
          padding: '8px 12px',
          borderRadius: '4px',
          fontSize: '12px',
          zIndex: 9999,
          display: 'none', // Hidden by default, can be shown via CSS or state
        }}>
          Performance optimizations enabled
        </div>
      )}
    </div>
  );
};

/**
 * Higher-order component for performance monitoring
 */
export function withPerformanceMonitoring<P extends object>(
  WrappedComponent: React.ComponentType<P>,
  componentName?: string
) {
  const displayName = componentName || WrappedComponent.displayName || WrappedComponent.name || 'Component';
  
  const PerformanceMonitoredComponent: React.FC<P> = (props) => {
    const renderStart = React.useRef<number>(0);
    
    // Track render start
    renderStart.current = performance.now();
    
    React.useEffect(() => {
      // Track render completion
      const renderTime = performance.now() - renderStart.current;
      
      performanceMonitor.recordMetric({
        name: 'component_render_time',
        value: renderTime,
        unit: 'ms',
        timestamp: Date.now(),
        tags: {
          component: displayName,
        },
        context: 'component_performance',
      });
      
      if (renderTime > 16) {
        logger.warn(`Slow render in ${displayName}: ${renderTime.toFixed(2)}ms`);
      }
    });
    
    return <WrappedComponent {...props} />;
  };
  
  PerformanceMonitoredComponent.displayName = `withPerformanceMonitoring(${displayName})`;
  
  return PerformanceMonitoredComponent;
}

/**
 * Performance metrics display component (for development)
 */
export const PerformanceMetrics: React.FC = () => {
  const [metrics, setMetrics] = useState<any[]>([]);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Only show in development
    if (getEnvVar.MODE() !== 'development') {
      return;
    }

    const interval = setInterval(() => {
      const recentMetrics = performanceMonitor.getMetrics().slice(-10);
      setMetrics(recentMetrics);
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  if (getEnvVar.MODE() !== 'development' || !isVisible) {
    return (
      <button
        onClick={() => setIsVisible(true)}
        style={{
          position: 'fixed',
          bottom: '10px',
          left: '10px',
          background: '#007bff',
          color: 'white',
          border: 'none',
          padding: '8px 12px',
          borderRadius: '4px',
          fontSize: '12px',
          cursor: 'pointer',
          zIndex: 9999,
        }}
      >
        Show Performance
      </button>
    );
  }

  return (
    <div style={{
      position: 'fixed',
      bottom: '10px',
      left: '10px',
      background: 'rgba(0, 0, 0, 0.9)',
      color: 'white',
      padding: '10px',
      borderRadius: '4px',
      fontSize: '11px',
      maxWidth: '300px',
      maxHeight: '200px',
      overflow: 'auto',
      zIndex: 9999,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '5px' }}>
        <strong>Performance Metrics</strong>
        <button
          onClick={() => setIsVisible(false)}
          style={{
            background: 'none',
            border: 'none',
            color: 'white',
            cursor: 'pointer',
            padding: '0',
          }}
        >
          ×
        </button>
      </div>
      {metrics.map((metric, index) => (
        <div key={index} style={{ marginBottom: '2px' }}>
          <strong>{metric.name}:</strong> {metric.value.toFixed(2)}{metric.unit}
          {metric.tags && (
            <div style={{ fontSize: '10px', opacity: 0.7 }}>
              {Object.entries(metric.tags).map(([key, value]) => (
                <span key={key}> {key}: {String(value)}</span>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  );
};