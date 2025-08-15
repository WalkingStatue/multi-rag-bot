import React from 'react';
import { useNetworkStatus } from '../../hooks/useNetworkStatus';

interface OfflineIndicatorProps {
  className?: string;
  showWhenOnline?: boolean;
  position?: 'top' | 'bottom';
  variant?: 'banner' | 'toast' | 'badge';
}

export const OfflineIndicator: React.FC<OfflineIndicatorProps> = ({
  className = '',
  showWhenOnline = false,
  position = 'top',
  variant = 'banner',
}) => {
  const { isOnline, isSlowConnection, networkStatus, retryConnection } = useNetworkStatus();

  // Don't show anything if online and showWhenOnline is false
  if (isOnline && !showWhenOnline) {
    return null;
  }

  const getStatusMessage = () => {
    if (!isOnline) {
      return 'You are currently offline. Some features may not be available.';
    }
    if (isSlowConnection) {
      return `Slow connection detected (${networkStatus.effectiveType}). Some features may be limited.`;
    }
    return 'You are back online!';
  };

  const getStatusColor = () => {
    if (!isOnline) return 'bg-red-500';
    if (isSlowConnection) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  const getTextColor = () => {
    if (!isOnline) return 'text-red-700';
    if (isSlowConnection) return 'text-yellow-700';
    return 'text-green-700';
  };

  const getBorderColor = () => {
    if (!isOnline) return 'border-red-200';
    if (isSlowConnection) return 'border-yellow-200';
    return 'border-green-200';
  };

  const getBackgroundColor = () => {
    if (!isOnline) return 'bg-red-50';
    if (isSlowConnection) return 'bg-yellow-50';
    return 'bg-green-50';
  };

  const baseClasses = `
    flex items-center justify-between px-4 py-2 text-sm font-medium
    transition-all duration-300 ease-in-out
  `;

  const variantClasses = {
    banner: `
      w-full border-l-4 ${getBorderColor()} ${getBackgroundColor()} ${getTextColor()}
      ${position === 'top' ? 'border-t border-r border-b' : 'border-b border-r border-t'}
    `,
    toast: `
      max-w-md mx-auto rounded-lg shadow-lg ${getBackgroundColor()} ${getTextColor()}
      border ${getBorderColor()}
    `,
    badge: `
      inline-flex rounded-full px-3 py-1 ${getStatusColor()} text-white text-xs
    `,
  };

  const positionClasses = {
    top: 'fixed top-0 left-0 right-0 z-50',
    bottom: 'fixed bottom-0 left-0 right-0 z-50',
  };

  if (variant === 'badge') {
    return (
      <div className={`${variantClasses.badge} ${className}`}>
        <div className="flex items-center space-x-2">
          <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-white' : 'bg-red-200'}`} />
          <span>{isOnline ? 'Online' : 'Offline'}</span>
        </div>
      </div>
    );
  }

  return (
    <div
      className={`
        ${baseClasses}
        ${variantClasses[variant]}
        ${variant === 'banner' ? positionClasses[position] : ''}
        ${className}
      `}
      role="alert"
      aria-live="polite"
    >
      <div className="flex items-center space-x-3">
        {/* Status indicator */}
        <div className="flex items-center space-x-2">
          <div
            className={`
              w-3 h-3 rounded-full
              ${isOnline ? (isSlowConnection ? 'bg-yellow-400' : 'bg-green-400') : 'bg-red-400'}
              ${!isOnline ? 'animate-pulse' : ''}
            `}
          />
          <span>{getStatusMessage()}</span>
        </div>

        {/* Connection details for slow connections */}
        {isOnline && isSlowConnection && (
          <div className="text-xs opacity-75">
            {networkStatus.downlink > 0 && (
              <span>Speed: {networkStatus.downlink.toFixed(1)} Mbps</span>
            )}
            {networkStatus.rtt > 0 && (
              <span className="ml-2">Latency: {networkStatus.rtt}ms</span>
            )}
          </div>
        )}
      </div>

      {/* Action buttons */}
      <div className="flex items-center space-x-2">
        {!isOnline && (
          <button
            onClick={retryConnection}
            className={`
              px-3 py-1 text-xs font-medium rounded
              ${getTextColor()} hover:bg-opacity-20 hover:bg-current
              transition-colors duration-200
            `}
            aria-label="Retry connection"
          >
            Retry
          </button>
        )}

        {/* Dismiss button for toast variant */}
        {variant === 'toast' && isOnline && (
          <button
            className={`
              p-1 rounded hover:bg-opacity-20 hover:bg-current
              ${getTextColor()} transition-colors duration-200
            `}
            aria-label="Dismiss notification"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
                clipRule="evenodd"
              />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
};

// Connection status badge for use in headers/navigation
export const ConnectionStatusBadge: React.FC<{ className?: string }> = ({ className }) => {
  return (
    <OfflineIndicator
      variant="badge"
      showWhenOnline={true}
      className={className}
    />
  );
};

// Floating offline notification
export const OfflineNotification: React.FC = () => {
  const { isOffline } = useNetworkStatus();

  if (!isOffline) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50">
      <OfflineIndicator variant="toast" />
    </div>
  );
};

export default OfflineIndicator;