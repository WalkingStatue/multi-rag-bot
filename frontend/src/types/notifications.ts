/**
 * Notification and WebSocket types
 */

export interface NotificationBase {
  id: string;
  type: 'permission_granted' | 'permission_updated' | 'permission_revoked' | 'bot_updated' | 'bot_deleted' | 'ownership_transferred';
  title: string;
  message: string;
  created_at: string;
  read: boolean;
}

export interface PermissionNotification extends NotificationBase {
  type: 'permission_granted' | 'permission_updated' | 'permission_revoked';
  data: {
    bot_id: string;
    bot_name: string;
    user_id: string;
    username: string;
    old_role?: string;
    new_role?: string;
    granted_by: string;
    granted_by_username: string;
  };
}

export interface BotUpdateNotification extends NotificationBase {
  type: 'bot_updated' | 'bot_deleted' | 'ownership_transferred';
  data: {
    bot_id: string;
    bot_name: string;
    updated_by: string;
    updated_by_username: string;
    changes?: Record<string, any>;
  };
}

export type Notification = PermissionNotification | BotUpdateNotification;

export interface WebSocketMessage {
  type: 'notification' | 'permission_update' | 'bot_update';
  data: any;
}

export interface NotificationSettings {
  email_notifications: boolean;
  push_notifications: boolean;
  permission_changes: boolean;
  bot_updates: boolean;
  collaboration_invites: boolean;
}