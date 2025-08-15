/**
 * Collaboration Management Component
 * Provides comprehensive UI for managing bot collaborators and permissions
 */
import React, { useState, useEffect, useCallback } from 'react';
import { 
  BotPermission, 
  CollaboratorInviteResponse,
  ActivityLog
} from '../../types/bot';
import { permissionService } from '../../services/permissionService';
import { websocketService } from '../../services/websocketService';
import { CollaboratorInviteModal } from './CollaboratorInvite';
import { Alert } from '../common/Alert';
import { Button } from '../common/Button';

interface CollaborationManagementProps {
  botId: string;
  botName: string;
  currentUserRole: 'owner' | 'admin' | 'editor' | 'viewer';
  onPermissionUpdate?: () => void;
}

interface ViewMode {
  type: 'collaborators' | 'activity' | 'bulk-update';
}

export const CollaborationManagement: React.FC<CollaborationManagementProps> = ({
  botId,
  botName,
  currentUserRole,
  onPermissionUpdate
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>({ type: 'collaborators' });
  const [collaborators, setCollaborators] = useState<BotPermission[]>([]);
  // const [permissionHistory, setPermissionHistory] = useState<PermissionHistory[]>([]);
  const [activityLogs, setActivityLogs] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState({
    collaborators: true,
    history: false,
    activity: false,
    action: false
  });
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [showInviteModal, setShowInviteModal] = useState(false);
  // const [selectedCollaborator, setSelectedCollaborator] = useState<BotPermission | null>(null);

  // Check if user has admin permissions
  const canManageCollaborators = ['owner', 'admin'].includes(currentUserRole);
  const isOwner = currentUserRole === 'owner';

  // Load collaborators on component mount
  useEffect(() => {
    if (canManageCollaborators) {
      loadCollaborators();
    }
  }, [botId, canManageCollaborators]);

  // Setup WebSocket listeners for real-time updates
  useEffect(() => {
    // Subscribe to permission updates
    const unsubscribePermission = websocketService.subscribe('permission_update', (data) => {
      if (data.bot_id === botId) {
        handlePermissionUpdate(data);
      }
    });

    // Subscribe to collaboration updates
    const unsubscribeCollaboration = websocketService.subscribe('collaboration_update', (data) => {
      if (data.bot_id === botId) {
        handleCollaborationUpdate(data);
      }
    });

    // Subscribe to activity updates
    const unsubscribeActivity = websocketService.subscribe('activity_update', (data) => {
      if (data.bot_id === botId) {
        handleActivityUpdate(data);
      }
    });

    return () => {
      unsubscribePermission();
      unsubscribeCollaboration();
      unsubscribeActivity();
    };
  }, [botId]);

  // Auto-hide messages
  useEffect(() => {
    if (success || error) {
      const timer = setTimeout(() => {
        setSuccess(null);
        setError(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [success, error]);

  const loadCollaborators = async () => {
    try {
      setLoading(prev => ({ ...prev, collaborators: true }));
      setError(null);
      const data = await permissionService.getBotPermissions(botId);
      setCollaborators(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load collaborators');
      console.error('Error loading collaborators:', err);
    } finally {
      setLoading(prev => ({ ...prev, collaborators: false }));
    }
  };

  // const loadPermissionHistory = async () => {
  //   try {
  //     setLoading(prev => ({ ...prev, history: true }));
  //     setError(null);
  //     const data = await permissionService.getPermissionHistory(botId);
  //     setPermissionHistory(data);
  //   } catch (err: any) {
  //     setError(err.response?.data?.detail || 'Failed to load permission history');
  //     console.error('Error loading permission history:', err);
  //   } finally {
  //     setLoading(prev => ({ ...prev, history: false }));
  //   }
  // };

  const loadActivityLogs = async () => {
    try {
      setLoading(prev => ({ ...prev, activity: true }));
      setError(null);
      const data = await permissionService.getActivityLog(botId);
      setActivityLogs(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load activity logs');
      console.error('Error loading activity logs:', err);
    } finally {
      setLoading(prev => ({ ...prev, activity: false }));
    }
  };

  const handleInviteSuccess = (response: CollaboratorInviteResponse) => {
    if (response.success) {
      setSuccess(response.message);
      loadCollaborators(); // Reload the list
      onPermissionUpdate?.();
    } else {
      setError(response.message);
    }
    setShowInviteModal(false);
  };

  const handleUpdateRole = async (userId: string, newRole: 'admin' | 'editor' | 'viewer') => {
    try {
      setLoading(prev => ({ ...prev, action: true }));
      setError(null);

      // Validate permission update
      const validation = permissionService.validatePermissionUpdate(
        currentUserRole,
        newRole,
        isOwner
      );

      if (!validation.valid) {
        setError(validation.error || 'Invalid permission update');
        return;
      }

      await permissionService.updateCollaboratorRole(botId, userId, newRole);
      setSuccess(`Role updated successfully to ${permissionService.formatRoleName(newRole)}`);
      loadCollaborators(); // Reload the list
      onPermissionUpdate?.();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update role');
      console.error('Error updating role:', err);
    } finally {
      setLoading(prev => ({ ...prev, action: false }));
    }
  };

  const handleRemoveCollaborator = async (userId: string, username: string) => {
    if (!window.confirm(`Are you sure you want to remove ${username} from this bot?`)) {
      return;
    }

    try {
      setLoading(prev => ({ ...prev, action: true }));
      setError(null);
      await permissionService.removeCollaborator(botId, userId);
      setSuccess(`${username} removed from bot successfully`);
      loadCollaborators(); // Reload the list
      onPermissionUpdate?.();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to remove collaborator');
      console.error('Error removing collaborator:', err);
    } finally {
      setLoading(prev => ({ ...prev, action: false }));
    }
  };

  // const handleBulkUpdate = async (updates: BulkPermissionUpdate) => {
  //   try {
  //     setLoading(prev => ({ ...prev, action: true }));
  //     setError(null);
  //     const results = await permissionService.bulkUpdatePermissions(botId, updates) as BulkUpdateResponse;
  //     setSuccess(`Bulk update completed: ${results.successful?.length || 0} successful, ${results.failed?.length || 0} failed`);
  //     loadCollaborators(); // Reload the list
  //     onPermissionUpdate?.();
  //   } catch (err: any) {
  //     setError(err.response?.data?.detail || 'Failed to perform bulk update');
  //     console.error('Error performing bulk update:', err);
  //   } finally {
  //     setLoading(prev => ({ ...prev, action: false }));
  //   }
  // };

  // WebSocket event handlers
  const handlePermissionUpdate = useCallback((data: any) => {
    setSuccess(`Permission updated: ${data.username} is now ${permissionService.formatRoleName(data.new_role)}`);
    loadCollaborators();
  }, []);

  const handleCollaborationUpdate = useCallback((data: any) => {
    setSuccess(`Collaboration update: ${data.message}`);
    loadCollaborators();
  }, []);

  const handleActivityUpdate = useCallback((_data: any) => {
    if (viewMode.type === 'activity') {
      loadActivityLogs();
    }
  }, [viewMode.type]);

  const renderCollaboratorsList = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-gray-900">Collaborators</h3>
        {canManageCollaborators && (
          <Button
            onClick={() => setShowInviteModal(true)}
            disabled={loading.action}
            className="bg-blue-600 hover:bg-blue-700 text-white"
          >
            Invite Collaborator
          </Button>
        )}
      </div>

      {loading.collaborators ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading collaborators...</p>
        </div>
      ) : collaborators.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No collaborators found for this bot.</p>
          {canManageCollaborators && (
            <p className="mt-2">Click "Invite Collaborator" to add team members.</p>
          )}
        </div>
      ) : (
        <div className="bg-white shadow overflow-hidden sm:rounded-md">
          <ul className="divide-y divide-gray-200">
            {collaborators.map((collaborator) => (
              <li key={collaborator.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <div className="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                        <span className="text-sm font-medium text-gray-700">
                          {collaborator.username?.charAt(0).toUpperCase() || 'U'}
                        </span>
                      </div>
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-gray-900">
                        {collaborator.username}
                      </div>
                      <div className="text-sm text-gray-500">
                        {collaborator.email}
                      </div>
                      <div className="text-xs text-gray-400">
                        Added {new Date(collaborator.granted_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <div className="text-right">
                      <div className="text-sm font-medium text-gray-900">
                        {permissionService.formatRoleName(collaborator.role)}
                      </div>
                      {canManageCollaborators && collaborator.role !== 'owner' && (
                        <div className="text-xs text-gray-500">
                          {permissionService.getRoleDescription(collaborator.role)}
                        </div>
                      )}
                    </div>
                    {canManageCollaborators && collaborator.role !== 'owner' && (
                      <div className="flex space-x-2">
                        <select
                          value={collaborator.role}
                          onChange={(e) => handleUpdateRole(collaborator.user_id, e.target.value as any)}
                          disabled={loading.action}
                          className="text-sm border border-gray-300 rounded px-2 py-1"
                        >
                          <option value="viewer">Viewer</option>
                          <option value="editor">Editor</option>
                          {isOwner && <option value="admin">Admin</option>}
                        </select>
                        <Button
                          onClick={() => handleRemoveCollaborator(collaborator.user_id, collaborator.username || 'User')}
                          disabled={loading.action}
                          className="bg-red-600 hover:bg-red-700 text-white text-sm px-3 py-1"
                        >
                          Remove
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );

  // const renderPermissionHistory = () => (
  //   <div className="space-y-4">
  //     <div className="flex justify-between items-center">
  //       <h3 className="text-lg font-medium text-gray-900">Permission History</h3>
  //       <Button
  //         onClick={loadPermissionHistory}
  //         disabled={loading.history}
  //         className="bg-gray-600 hover:bg-gray-700 text-white"
  //       >
  //         Refresh
  //       </Button>
  //     </div>
  //
  //     {loading.history ? (
  //       <div className="text-center py-8">
  //         <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
  //         <p className="mt-2 text-gray-600">Loading history...</p>
  //       </div>
  //     ) : permissionHistory.length === 0 ? (
  //       <div className="text-center py-8 text-gray-500">
  //         <p>No permission history found.</p>
  //       </div>
  //     ) : (
  //       <div className="bg-white shadow overflow-hidden sm:rounded-md">
  //         <ul className="divide-y divide-gray-200">
  //           {permissionHistory.map((history) => (
  //             <li key={history.id} className="px-6 py-4">
  //               <div className="flex items-center justify-between">
  //                 <div>
  //                   <div className="text-sm font-medium text-gray-900">
  //                     {history.username}
  //                   </div>
  //                   <div className="text-sm text-gray-500">
  //                     {history.action === 'granted' && `Granted ${permissionService.formatRoleName(history.new_role || '')} role`}
  //                     {history.action === 'updated' && `Updated from ${permissionService.formatRoleName(history.old_role || '')} to ${permissionService.formatRoleName(history.new_role || '')}`}
  //                     {history.action === 'revoked' && `Permission revoked`}
  //                   </div>
  //                   <div className="text-xs text-gray-400">
  //                     by {history.granted_by_username} on {new Date(history.created_at).toLocaleString()}
  //                   </div>
  //                 </div>
  //               </div>
  //             </li>
  //           ))}
  //         </ul>
  //       </div>
  //     )}
  //   </div>
  // );

  const renderActivityLogs = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-gray-900">Activity Log</h3>
        <Button
          onClick={loadActivityLogs}
          disabled={loading.activity}
          className="bg-gray-600 hover:bg-gray-700 text-white"
        >
          Refresh
        </Button>
      </div>

      {loading.activity ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-gray-600">Loading activity logs...</p>
        </div>
      ) : activityLogs.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p>No activity logs found.</p>
        </div>
      ) : (
        <div className="bg-white shadow overflow-hidden sm:rounded-md">
          <ul className="divide-y divide-gray-200">
            {activityLogs.map((log) => (
              <li key={log.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-gray-900">
                      {log.action}
                    </div>
                    <div className="text-sm text-gray-500">
                      {log.username && `by ${log.username}`}
                    </div>
                    <div className="text-xs text-gray-400">
                      {new Date(log.created_at).toLocaleString()}
                    </div>
                    {log.details && (
                      <div className="text-xs text-gray-600 mt-1">
                        {JSON.stringify(log.details, null, 2)}
                      </div>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );

  const renderBulkUpdate = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-gray-900">Bulk Permission Update</h3>
      </div>
      
      <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800">
              Bulk Update Feature
            </h3>
            <div className="mt-2 text-sm text-yellow-700">
              <p>
                This feature allows you to update permissions for multiple users at once.
                Use this feature carefully as it will affect multiple collaborators simultaneously.
              </p>
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white shadow rounded-lg p-6">
        <p className="text-gray-600 mb-4">
          Bulk update functionality will be implemented in a future update.
          For now, please use the individual permission management above.
        </p>
      </div>
    </div>
  );

  const renderContent = () => {
    switch (viewMode.type) {
      case 'collaborators':
        return renderCollaboratorsList();
      case 'activity':
        return renderActivityLogs();
      case 'bulk-update':
        return renderBulkUpdate();
      default:
        return renderCollaboratorsList();
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-2xl font-bold text-gray-900">Collaboration Management</h2>
        <p className="mt-1 text-sm text-gray-600">
          Manage collaborators and permissions for "{botName}"
        </p>
      </div>

      {/* Alerts */}
      {error && <Alert type="error" message={error} />}
      {success && <Alert type="success" message={success} />}

      {/* Navigation Tabs */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setViewMode({ type: 'collaborators' })}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              viewMode.type === 'collaborators'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Collaborators
          </button>
          <button
            onClick={() => {
              setViewMode({ type: 'activity' });
              loadActivityLogs();
            }}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              viewMode.type === 'activity'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Activity Log
          </button>
          {canManageCollaborators && (
            <button
              onClick={() => setViewMode({ type: 'bulk-update' })}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                viewMode.type === 'bulk-update'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              Bulk Update
            </button>
          )}
        </nav>
      </div>

      {/* Content */}
      <div className="mt-6">
        {renderContent()}
      </div>

      {/* Invite Modal */}
      {showInviteModal && (
        <CollaboratorInviteModal
          botId={botId}
          isOpen={showInviteModal}
          onClose={() => setShowInviteModal(false)}
          onInviteSuccess={handleInviteSuccess}
        />
      )}
    </div>
  );
}; 