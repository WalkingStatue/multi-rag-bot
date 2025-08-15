import { useState, useEffect, useCallback } from 'react';
import { logger } from '../utils/logger';

export interface NetworkStatus {
  isOnline: boolean;
  isSlowConnection: boolean;
  connectionType: string;
  effectiveType: string;
  downlink: number;
  rtt: number;
  saveData: boolean;
}

export interface UseNetworkStatusReturn {
  networkStatus: NetworkStatus;
  isOnline: boolean;
  isOffline: boolean;
  isSlowConnection: boolean;
  checkConnection: () => Promise<boolean>;
  retryConnection: () => void;
}

// Extended Navigator interface for connection API
interface NavigatorWithConnection extends Navigator {
  connection?: {
    effectiveType: string;
    type: string;
    downlink: number;
    rtt: number;
    saveData: boolean;
    addEventListener: (event: string, handler: () => void) => void;
    removeEventListener: (event: string, handler: () => void) => void;
  };
}

const getConnectionInfo = (): Partial<NetworkStatus> => {
  const nav = navigator as NavigatorWithConnection;
  const connection = nav.connection;

  if (!connection) {
    return {
      connectionType: 'unknown',
      effectiveType: 'unknown',
      downlink: 0,
      rtt: 0,
      saveData: false,
    };
  }

  return {
    connectionType: connection.type || 'unknown',
    effectiveType: connection.effectiveType || 'unknown',
    downlink: connection.downlink || 0,
    rtt: connection.rtt || 0,
    saveData: connection.saveData || false,
  };
};

const isSlowConnection = (effectiveType: string, downlink: number): boolean => {
  return effectiveType === 'slow-2g' || effectiveType === '2g' || downlink < 0.5;
};

const checkOnlineStatus = async (): Promise<boolean> => {
  if (!navigator.onLine) {
    return false;
  }

  try {
    // Try to fetch a small resource to verify actual connectivity
    const response = await fetch('/favicon.ico', {
      method: 'HEAD',
      cache: 'no-cache',
      signal: AbortSignal.timeout(5000),
    });
    return response.ok;
  } catch {
    // If fetch fails, fall back to navigator.onLine
    return navigator.onLine;
  }
};

export const useNetworkStatus = (): UseNetworkStatusReturn => {
  const [networkStatus, setNetworkStatus] = useState<NetworkStatus>(() => {
    const connectionInfo = getConnectionInfo();
    return {
      isOnline: navigator.onLine,
      isSlowConnection: isSlowConnection(
        connectionInfo.effectiveType || 'unknown',
        connectionInfo.downlink || 0
      ),
      ...connectionInfo,
    } as NetworkStatus;
  });

  const updateNetworkStatus = useCallback(() => {
    const connectionInfo = getConnectionInfo();
    const newStatus: NetworkStatus = {
      isOnline: navigator.onLine,
      isSlowConnection: isSlowConnection(
        connectionInfo.effectiveType || 'unknown',
        connectionInfo.downlink || 0
      ),
      ...connectionInfo,
    } as NetworkStatus;

    setNetworkStatus(prevStatus => {
      // Only update if status actually changed
      if (
        prevStatus.isOnline !== newStatus.isOnline ||
        prevStatus.isSlowConnection !== newStatus.isSlowConnection ||
        prevStatus.effectiveType !== newStatus.effectiveType
      ) {
        logger.info(`Network status changed: ${prevStatus.isOnline ? 'online' : 'offline'} -> ${newStatus.isOnline ? 'online' : 'offline'}, connection: ${newStatus.effectiveType}`);
        return newStatus;
      }
      return prevStatus;
    });
  }, []);

  const checkConnection = useCallback(async (): Promise<boolean> => {
    try {
      const isOnline = await checkOnlineStatus();
      setNetworkStatus(prev => ({
        ...prev,
        isOnline,
      }));
      return isOnline;
    } catch (error) {
      logger.error(`Failed to check connection status: ${error instanceof Error ? error.message : 'Unknown error'}`);
      return false;
    }
  }, []);

  const retryConnection = useCallback(() => {
    logger.info('Retrying connection check');
    checkConnection();
  }, [checkConnection]);

  useEffect(() => {
    const handleOnline = () => {
      logger.info('Network came online');
      updateNetworkStatus();
      checkConnection();
    };

    const handleOffline = () => {
      logger.warn('Network went offline');
      updateNetworkStatus();
    };

    const handleConnectionChange = () => {
      logger.info('Network connection changed');
      updateNetworkStatus();
    };

    // Add event listeners
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Add connection change listener if available
    const nav = navigator as NavigatorWithConnection;
    if (nav.connection) {
      nav.connection.addEventListener('change', handleConnectionChange);
    }

    // Initial connection check
    checkConnection();

    // Cleanup
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      
      if (nav.connection) {
        nav.connection.removeEventListener('change', handleConnectionChange);
      }
    };
  }, [updateNetworkStatus, checkConnection]);

  return {
    networkStatus,
    isOnline: networkStatus.isOnline,
    isOffline: !networkStatus.isOnline,
    isSlowConnection: networkStatus.isSlowConnection,
    checkConnection,
    retryConnection,
  };
};

export default useNetworkStatus;