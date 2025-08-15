/**
 * Notification System Component
 * Displays real-time notifications from WebSocket events
 */
import React, { useState, useEffect, useCallback } from 'react';
import { websocketService } from '../../services/websocketService';
import { Notification, NotificationSettings } from '../../types/notifications';
import { Button } from './Button';

interface NotificationSystemProps {
  botId?: string;
  onNotificationClick?: (notification: NotificationItem) => void;
}

interface NotificationItem {
  id: string;
  type: 'permission_granted' | 'permission_updated' | 'permission_revoked' | 'bot_updated' | 'bot_deleted' | 'ownership_transferred';
  title: string;
  message: string;
  created_at: string;
  read: boolean;
  timestamp: Date;
  data?: any;
}

export const NotificationSystem: React.FC<NotificationSystemProps> = ({
  botId,
  onNotificationClick
}) => {
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isOpen, setIsOpen] = useState(false);
  const [settings /*, setSettings*/] = useState<NotificationSettings>({
    email_notifications: true,
    push_notifications: true,
    permission_changes: true,
    bot_updates: true,
    collaboration_invites: true,
  });

  // Setup WebSocket listeners
  useEffect(() => {
    // Subscribe to notification events
    const unsubscribeNotification = websocketService.subscribe('notification', (data: Notification) => {
      handleNewNotification(data);
    });

    // Subscribe to permission updates
    const unsubscribePermission = websocketService.subscribe('permission_update', (data: any) => {
      if (settings.permission_changes) {
        handlePermissionUpdate(data);
      }
    });

    // Subscribe to bot updates
    const unsubscribeBotUpdate = websocketService.subscribe('bot_update', (data: any) => {
      if (settings.bot_updates) {
        handleBotUpdate(data);
      }
    });

    // Subscribe to collaboration updates
    const unsubscribeCollaboration = websocketService.subscribe('collaboration_update', (data: any) => {
      if (settings.collaboration_invites) {
        handleCollaborationUpdate(data);
      }
    });

    return () => {
      unsubscribeNotification();
      unsubscribePermission();
      unsubscribeBotUpdate();
      unsubscribeCollaboration();
    };
  }, [settings]);

  // Update unread count when notifications change
  useEffect(() => {
    const unread = notifications.filter(n => !n.read).length;
    setUnreadCount(unread);
  }, [notifications]);

  const handleNewNotification = useCallback((notification: Notification) => {
    const newNotification: NotificationItem = {
      ...notification,
      id: `notification-${Date.now()}-${Math.random()}`,
      timestamp: new Date(),
      read: false,
    };

    setNotifications(prev => [newNotification, ...prev.slice(0, 49)]); // Keep max 50 notifications
  }, []);

  const handlePermissionUpdate = useCallback((data: any) => {
    if (botId && data.bot_id !== botId) return;

    const notification: NotificationItem = {
      id: `permission-${Date.now()}`,
      type: 'permission_updated',
      title: 'Permission Updated',
      message: `${data.username} is now ${data.new_role} for ${data.bot_name}`,
      created_at: new Date().toISOString(),
      read: false,
      timestamp: new Date(),
      data: {
        bot_id: data.bot_id,
        bot_name: data.bot_name,
        user_id: data.user_id,
        username: data.username,
        old_role: data.old_role,
        new_role: data.new_role,
        granted_by: data.granted_by,
        granted_by_username: data.granted_by_username,
      },
    };

    setNotifications(prev => [notification, ...prev.slice(0, 49)]);
  }, [botId]);

  const handleBotUpdate = useCallback((data: any) => {
    if (botId && data.bot_id !== botId) return;

    const notification: NotificationItem = {
      id: `bot-${Date.now()}`,
      type: 'bot_updated',
      title: 'Bot Updated',
      message: `${data.bot_name} has been updated by ${data.updated_by_username}`,
      created_at: new Date().toISOString(),
      read: false,
      timestamp: new Date(),
      data: {
        bot_id: data.bot_id,
        bot_name: data.bot_name,
        updated_by: data.updated_by,
        updated_by_username: data.updated_by_username,
        changes: data.changes,
      },
    };

    setNotifications(prev => [notification, ...prev.slice(0, 49)]);
  }, [botId]);

  const handleCollaborationUpdate = useCallback((data: any) => {
    if (botId && data.bot_id !== botId) return;

    const notification: NotificationItem = {
      id: `collab-${Date.now()}`,
      type: 'permission_granted',
      title: 'Collaboration Invite',
      message: data.message || 'You have been invited to collaborate on a bot',
      created_at: new Date().toISOString(),
      read: false,
      timestamp: new Date(),
      data: {
        bot_id: data.bot_id,
        bot_name: data.bot_name,
        user_id: data.user_id,
        username: data.username,
        new_role: data.role,
        granted_by: data.granted_by,
        granted_by_username: data.granted_by_username,
      },
    };

    setNotifications(prev => [notification, ...prev.slice(0, 49)]);
  }, [botId]);

  const markAsRead = (notificationId: string) => {
    setNotifications(prev => 
      prev.map(n => n.id === notificationId ? { ...n, read: true } : n)
    );
  };

  const markAllAsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, read: true })));
  };

  const clearNotification = (notificationId: string) => {
    setNotifications(prev => prev.filter(n => n.id !== notificationId));
  };

  const clearAllNotifications = () => {
    setNotifications([]);
  };

  const handleNotificationClick = (notification: NotificationItem) => {
    if (!notification.read) {
      markAsRead(notification.id);
    }
    onNotificationClick?.(notification);
  };

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'permission_granted':
      case 'permission_updated':
        return (
          <svg className="h-5 w-5 text-blue-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
          </svg>
        );
      case 'bot_updated':
        return (
          <svg className="h-5 w-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z" clipRule="evenodd" />
          </svg>
        );
      case 'bot_deleted':
        return (
          <svg className="h-5 w-5 text-red-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
        );
      default:
        return (
          <svg className="h-5 w-5 text-gray-500" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
          </svg>
        );
    }
  };

  const formatTimeAgo = (timestamp: Date) => {
    const now = new Date();
    const diffInSeconds = Math.floor((now.getTime() - timestamp.getTime()) / 1000);

    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    return `${Math.floor(diffInSeconds / 86400)}d ago`;
  };

  return (
    <div className="relative">
      {/* Notification Bell */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 text-gray-600 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-md"
      >
        <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5 5v-5zM10.5 3.75a6 6 0 00-6 6v3.75l-2.25 2.25V19.5h12.75V15l-2.25-2.25V9.75a6 6 0 00-6-6z" />
        </svg>
        
        {/* Unread Badge */}
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Notification Panel */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 z-50">
          <div className="py-2">
            {/* Header */}
            <div className="px-4 py-2 border-b border-gray-200 flex justify-between items-center">
              <h3 className="text-sm font-medium text-gray-900">Notifications</h3>
              <div className="flex space-x-2">
                {unreadCount > 0 && (
                  <Button
                    onClick={markAllAsRead}
                    className="text-xs bg-blue-600 hover:bg-blue-700 text-white px-2 py-1"
                  >
                    Mark all read
                  </Button>
                )}
                {notifications.length > 0 && (
                  <Button
                    onClick={clearAllNotifications}
                    className="text-xs bg-gray-600 hover:bg-gray-700 text-white px-2 py-1"
                  >
                    Clear all
                  </Button>
                )}
              </div>
            </div>

            {/* Notification List */}
            <div className="max-h-96 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="px-4 py-8 text-center text-gray-500">
                  <svg className="mx-auto h-8 w-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-5 5v-5zM10.5 3.75a6 6 0 00-6 6v3.75l-2.25 2.25V19.5h12.75V15l-2.25-2.25V9.75a6 6 0 00-6-6z" />
                  </svg>
                  <p className="mt-2 text-sm">No notifications</p>
                </div>
              ) : (
                <ul className="divide-y divide-gray-200">
                  {notifications.map((notification) => (
                    <li
                      key={notification.id}
                      className={`px-4 py-3 hover:bg-gray-50 cursor-pointer ${
                        !notification.read ? 'bg-blue-50' : ''
                      }`}
                      onClick={() => handleNotificationClick(notification)}
                    >
                      <div className="flex items-start">
                        <div className="flex-shrink-0 mt-0.5">
                          {getNotificationIcon(notification.type)}
                        </div>
                        <div className="ml-3 flex-1 min-w-0">
                          <div className="flex justify-between items-start">
                            <p className="text-sm font-medium text-gray-900">
                              {notification.title}
                            </p>
                            <div className="flex items-center space-x-2">
                              <span className="text-xs text-gray-500">
                                {formatTimeAgo(notification.timestamp)}
                              </span>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  clearNotification(notification.id);
                                }}
                                className="text-gray-400 hover:text-gray-600"
                              >
                                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                              </button>
                            </div>
                          </div>
                          <p className="text-sm text-gray-600 mt-1">
                            {notification.message}
                          </p>
                          {!notification.read && (
                            <div className="mt-2">
                              <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                                New
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}; 