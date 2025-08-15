/**
 * Notification service for managing user notifications
 */
import { apiClient } from './api';
import type { Notification, NotificationSettings } from '../types/notifications';

export class NotificationService {
  /**
   * Get all notifications for the current user
   */
  async getNotifications(limit = 50, offset = 0): Promise<{
    notifications: Notification[];
    total: number;
    unread_count: number;
  }> {
    const response = await apiClient.get(`/notifications?limit=${limit}&offset=${offset}`);
    return response.data;
  }

  /**
   * Get unread notification count
   */
  async getUnreadCount(): Promise<number> {
    const response = await apiClient.get('/notifications/unread-count');
    return response.data.count;
  }

  /**
   * Mark a notification as read
   */
  async markAsRead(notificationId: string): Promise<void> {
    await apiClient.put(`/notifications/${notificationId}/read`);
  }

  /**
   * Mark all notifications as read
   */
  async markAllAsRead(): Promise<void> {
    await apiClient.put('/notifications/mark-all-read');
  }

  /**
   * Delete a notification
   */
  async deleteNotification(notificationId: string): Promise<void> {
    await apiClient.delete(`/notifications/${notificationId}`);
  }

  /**
   * Clear all notifications
   */
  async clearAllNotifications(): Promise<void> {
    await apiClient.delete('/notifications');
  }

  /**
   * Get notification settings
   */
  async getNotificationSettings(): Promise<NotificationSettings> {
    const response = await apiClient.get('/notifications/settings');
    return response.data;
  }

  /**
   * Update notification settings
   */
  async updateNotificationSettings(settings: Partial<NotificationSettings>): Promise<NotificationSettings> {
    const response = await apiClient.put('/notifications/settings', settings);
    return response.data;
  }

  /**
   * Create a local notification (for testing or offline scenarios)
   */
  createLocalNotification(
    type: Notification['type'],
    title: string,
    message: string,
    data?: any
  ): Notification {
    return {
      id: `local-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
      type,
      title,
      message,
      created_at: new Date().toISOString(),
      read: false,
      data: data || {},
    } as Notification;
  }

  /**
   * Format notification for display
   */
  formatNotification(notification: Notification): {
    icon: string;
    color: string;
    timeAgo: string;
  } {
    const now = new Date();
    const createdAt = new Date(notification.created_at);
    const diffMs = now.getTime() - createdAt.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    let timeAgo: string;
    if (diffMins < 1) {
      timeAgo = 'Just now';
    } else if (diffMins < 60) {
      timeAgo = `${diffMins}m ago`;
    } else if (diffHours < 24) {
      timeAgo = `${diffHours}h ago`;
    } else if (diffDays < 7) {
      timeAgo = `${diffDays}d ago`;
    } else {
      timeAgo = createdAt.toLocaleDateString();
    }

    const typeConfig: Record<string, { icon: string; color: string }> = {
      permission_granted: { icon: '👥', color: 'text-green-600' },
      permission_updated: { icon: '🔄', color: 'text-blue-600' },
      permission_revoked: { icon: '❌', color: 'text-red-600' },
      bot_updated: { icon: '🤖', color: 'text-blue-600' },
      bot_deleted: { icon: '🗑️', color: 'text-red-600' },
      ownership_transferred: { icon: '👑', color: 'text-purple-600' },
    };

    const config = typeConfig[notification.type] || { icon: '📢', color: 'text-gray-600' };

    return {
      icon: config.icon,
      color: config.color,
      timeAgo,
    };
  }

  /**
   * Group notifications by date
   */
  groupNotificationsByDate(notifications: Notification[]): Record<string, Notification[]> {
    const groups: Record<string, Notification[]> = {};
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    notifications.forEach(notification => {
      const createdAt = new Date(notification.created_at);
      let groupKey: string;

      if (this.isSameDay(createdAt, today)) {
        groupKey = 'Today';
      } else if (this.isSameDay(createdAt, yesterday)) {
        groupKey = 'Yesterday';
      } else if (createdAt.getTime() > today.getTime() - 7 * 24 * 60 * 60 * 1000) {
        groupKey = 'This week';
      } else {
        groupKey = createdAt.toLocaleDateString('en-US', { 
          month: 'long', 
          day: 'numeric',
          year: createdAt.getFullYear() !== today.getFullYear() ? 'numeric' : undefined 
        });
      }

      if (!groups[groupKey]) {
        groups[groupKey] = [];
      }
      groups[groupKey].push(notification);
    });

    return groups;
  }

  /**
   * Check if two dates are the same day
   */
  private isSameDay(date1: Date, date2: Date): boolean {
    return (
      date1.getFullYear() === date2.getFullYear() &&
      date1.getMonth() === date2.getMonth() &&
      date1.getDate() === date2.getDate()
    );
  }

  /**
   * Request browser notification permission
   */
  async requestNotificationPermission(): Promise<NotificationPermission> {
    if (!('Notification' in window)) {
      throw new Error('This browser does not support notifications');
    }

    if (Notification.permission === 'granted') {
      return 'granted';
    }

    if (Notification.permission !== 'denied') {
      const permission = await Notification.requestPermission();
      return permission;
    }

    return Notification.permission;
  }

  /**
   * Show browser notification
   */
  showBrowserNotification(title: string, options?: NotificationOptions): void {
    if (Notification.permission === 'granted') {
      new Notification(title, {
        icon: '/favicon.ico',
        badge: '/favicon.ico',
        ...options,
      });
    }
  }
}

// Export singleton instance
export const notificationService = new NotificationService();