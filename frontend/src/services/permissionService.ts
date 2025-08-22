/**
 * Permission management service for collaboration features
 */
import { enhancedApiClient } from './enhancedApi';
import {
  BotPermission,
  CollaboratorInvite,
  CollaboratorInviteResponse,
  BulkPermissionUpdate,
  PermissionHistory,
  ActivityLog,
} from '../types/bot';

export class PermissionService {
  /**
   * Get all permissions for a bot
   */
  async getBotPermissions(botId: string): Promise<BotPermission[]> {
    try {
      const response = await enhancedApiClient.get(`/bots/${botId}/permissions`);
      return response.data;
    } catch (error: any) {
      throw error;
    }
  }

  /**
   * Invite a collaborator to a bot
   */
  async inviteCollaborator(
    botId: string,
    invite: CollaboratorInvite
  ): Promise<CollaboratorInviteResponse> {
    const response = await enhancedApiClient.post(`/bots/${botId}/permissions/invite`, invite);
    return response.data;
  }

  /**
   * Update a collaborator's role
   */
  async updateCollaboratorRole(
    botId: string,
    userId: string,
    role: 'admin' | 'editor' | 'viewer'
  ): Promise<BotPermission> {
    const response = await enhancedApiClient.put(`/bots/${botId}/permissions/${userId}`, { role });
    return response.data;
  }

  /**
   * Remove a collaborator from a bot
   */
  async removeCollaborator(botId: string, userId: string): Promise<void> {
    await enhancedApiClient.delete(`/bots/${botId}/permissions/${userId}`);
  }

  /**
   * Bulk update permissions for multiple users
   */
  async bulkUpdatePermissions(
    botId: string,
    updates: BulkPermissionUpdate
  ): Promise<BotPermission[]> {
    const response = await enhancedApiClient.post(`/bots/${botId}/permissions/bulk`, updates);
    return response.data;
  }

  /**
   * Get permission history for a bot
   */
  async getPermissionHistory(botId: string): Promise<PermissionHistory[]> {
    const response = await enhancedApiClient.get(`/bots/${botId}/permissions/history`);
    return response.data;
  }

  /**
   * Get activity log for a bot
   */
  async getActivityLog(botId: string): Promise<ActivityLog[]> {
    const response = await enhancedApiClient.get(`/bots/${botId}/activity`);
    const data = response.data as any;
    if (Array.isArray(data)) {
      return data as ActivityLog[];
    }
    if (Array.isArray(data?.activity_logs)) {
      return data.activity_logs as ActivityLog[];
    }
    if (Array.isArray(data?.logs)) {
      return data.logs as ActivityLog[];
    }
    return [];
  }

  /**
   * Search for users to invite as collaborators
   */
  async searchUsers(query: string): Promise<Array<{ id: string; username: string; email: string; full_name?: string }>> {
    const response = await enhancedApiClient.get(`/users/search?q=${encodeURIComponent(query)}`);
    return response.data;
  }

  /**
   * Get user's current role for a bot
   */
  async getUserBotRole(botId: string): Promise<string | null> {
    try {
      const response = await enhancedApiClient.get(`/bots/${botId}/permissions/my-role`);
      return response.data.role;
    } catch (error: any) {
      return null;
    }
  }

  /**
   * Check if user has specific permission for a bot
   */
  async checkPermission(
    botId: string,
    requiredRole: 'owner' | 'admin' | 'editor' | 'viewer'
  ): Promise<boolean> {
    try {
      const userRole = await this.getUserBotRole(botId);
      if (!userRole) return false;

      const roleHierarchy = ['viewer', 'editor', 'admin', 'owner'];
      const userRoleIndex = roleHierarchy.indexOf(userRole);
      const requiredRoleIndex = roleHierarchy.indexOf(requiredRole);

      return userRoleIndex >= requiredRoleIndex;
    } catch (error) {
      return false;
    }
  }

  /**
   * Validate permission update request
   */
  validatePermissionUpdate(
    currentUserRole: string,
    targetRole: string,
    isOwner: boolean
  ): { valid: boolean; error?: string } {
    // Only owners can grant admin role
    if (targetRole === 'admin' && !isOwner) {
      return { valid: false, error: 'Only bot owners can grant admin permissions' };
    }

    // Only owners and admins can grant editor role
    if (targetRole === 'editor' && !['owner', 'admin'].includes(currentUserRole)) {
      return { valid: false, error: 'Only owners and admins can grant editor permissions' };
    }

    // Only owners and admins can grant viewer role
    if (targetRole === 'viewer' && !['owner', 'admin'].includes(currentUserRole)) {
      return { valid: false, error: 'Only owners and admins can grant viewer permissions' };
    }

    // Cannot grant owner role through this method
    if (targetRole === 'owner') {
      return { valid: false, error: 'Ownership must be transferred through the transfer ownership feature' };
    }

    return { valid: true };
  }

  /**
   * Format role display name
   */
  formatRoleName(role: string): string {
    const roleNames: Record<string, string> = {
      owner: 'Owner',
      admin: 'Administrator',
      editor: 'Editor',
      viewer: 'Viewer',
    };
    return roleNames[role] || role;
  }

  /**
   * Get role description
   */
  getRoleDescription(role: string): string {
    const descriptions: Record<string, string> = {
      owner: 'Full control over the bot, including deletion and ownership transfer',
      admin: 'Can manage collaborators, edit bot settings, and upload documents',
      editor: 'Can edit bot settings, upload documents, and chat with the bot',
      viewer: 'Can only view and chat with the bot',
    };
    return descriptions[role] || 'Unknown role';
  }

  /**
   * Get role permissions
   */
  getRolePermissions(role: string): string[] {
    const permissions: Record<string, string[]> = {
      owner: [
        'Delete bot',
        'Transfer ownership',
        'Manage all collaborators',
        'Edit bot settings',
        'Upload documents',
        'Chat with bot',
        'View analytics',
      ],
      admin: [
        'Manage collaborators',
        'Edit bot settings',
        'Upload documents',
        'Chat with bot',
        'View analytics',
      ],
      editor: [
        'Edit bot settings',
        'Upload documents',
        'Chat with bot',
      ],
      viewer: [
        'Chat with bot',
        'View bot information',
      ],
    };
    return permissions[role] || [];
  }
}

// Export singleton instance
export const permissionService = new PermissionService();