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
import { useToastHelpers } from '../common/Toast';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { log } from '../../utils/logger';

interface CollaborationManagementProps {
  botId: string;
  botName: string;
  currentUserRole: 'owner' | 'admin' | 'editor' | 'viewer';
  onPermissionUpdate?: () => void;
  // Optional: when provided, the component renders the specified view and hides internal navigation when hideChrome is true
  view?: 'collaborators' | 'activity' | 'bulk-update';
  hideChrome?: boolean;
}

interface ViewMode {
  type: 'collaborators' | 'activity' | 'bulk-update';
}

export const CollaborationManagement: React.FC<CollaborationManagementProps> = ({
  botId,
  botName,
  currentUserRole,
  onPermissionUpdate,
  view,
  hideChrome
}) => {
  const { error: showErrorToast, success: showSuccessToast } = useToastHelpers();
  const [viewMode, setViewMode] = useState<ViewMode>({ type: 'collaborators' });
  const effectiveView: 'collaborators' | 'activity' | 'bulk-update' = (view || viewMode.type);
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

  // If externally controlled to activity view, ensure logs are loaded
  useEffect(() => {
    if (effectiveView === 'activity') {
      loadActivityLogs();
    }
  }, [effectiveView]);

  const loadCollaborators = async () => {
    try {
      setLoading(prev => ({ ...prev, collaborators: true }));
      setError(null);
      const data = await permissionService.getBotPermissions(botId);
      setCollaborators(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load collaborators'); log.error('Error loading collaborators:', 'CollaborationManagement', { err });
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
  // log.error('Error loading permission history:', 'CollaborationManagement', { err });
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
      setError(err.response?.data?.detail || 'Failed to load activity logs'); log.error('Error loading activity logs:', 'CollaborationManagement', { err });
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
        const errorMessage = validation.error || 'Invalid permission update';
        setError(errorMessage);
        showErrorToast('Permission Update Error', errorMessage);
        return;
      }

      await permissionService.updateCollaboratorRole(botId, userId, newRole);
      const successMessage = `Role updated successfully to ${permissionService.formatRoleName(newRole)}`;
      setSuccess(successMessage);
      showSuccessToast('Role Updated', successMessage);
      loadCollaborators(); // Reload the list
      onPermissionUpdate?.();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to update role';
      setError(errorMessage);
      showErrorToast('Role Update Error', errorMessage); log.error('Error updating role:', 'CollaborationManagement', { err });
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
      const successMessage = `${username} removed from bot successfully`;
      setSuccess(successMessage);
      showSuccessToast('Collaborator Removed', successMessage);
      loadCollaborators(); // Reload the list
      onPermissionUpdate?.();
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || 'Failed to remove collaborator';
      setError(errorMessage);
      showErrorToast('Remove Collaborator Error', errorMessage); log.error('Error removing collaborator:', 'CollaborationManagement', { err });
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
  // log.error('Error performing bulk update:', 'CollaborationManagement', { err });
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
    if ((view || viewMode.type) === 'activity') {
      loadActivityLogs();
    }
  }, [view, viewMode.type]);

  const renderCollaboratorsList = () => (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">Collaborators</h3>
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
          <p className="mt-2 text-gray-600 dark:text-gray-400">Loading collaborators...</p>
        </div>
      ) : collaborators.length === 0 ? (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <p>No collaborators found for this bot.</p>
          {canManageCollaborators && (
            <p className="mt-2">Click "Invite Collaborator" to add team members.</p>
          )}
        </div>
      ) : (
        <Card padding="none">
          <ul className="divide-y divide-gray-200 dark:divide-gray-800">
            {collaborators.map((collaborator) => (
              <li key={collaborator.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <div className="h-10 w-10 rounded-full bg-gray-300 dark:bg-gray-700 flex items-center justify-center">
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                          {collaborator.username?.charAt(0).toUpperCase() || 'U'}
                        </span>
                      </div>
                    </div>
                    <div className="ml-4">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {collaborator.username}
                      </div>
                      <div className="text-sm text-gray-500 dark:text-gray-400">
                        {collaborator.email}
                      </div>
                      <div className="text-xs text-gray-400 dark:text-gray-500">
                        Added {new Date(collaborator.granted_at).toLocaleDateString()}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3">
                    <div className="text-right">
                      <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                        {permissionService.formatRoleName(collaborator.role)}
                      </div>
                      {canManageCollaborators && collaborator.role !== 'owner' && (
                        <div className="text-xs text-gray-500 dark:text-gray-400">
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
                          className="text-sm border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 rounded px-2 py-1"
                        >
                          <option value="viewer">Viewer</option>
                          <option value="editor">Editor</option>
                          {isOwner && <option value="admin">Admin</option>}
                        </select>
                        <Button
                          onClick={() => handleRemoveCollaborator(collaborator.user_id, collaborator.username || 'User')}
                          disabled={loading.action}
                          variant="danger"
                          size="sm"
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
        </Card>
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
        <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">Activity Log</h3>
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
          <p className="mt-2 text-gray-600 dark:text-gray-400">Loading activity logs...</p>
        </div>
      ) : !Array.isArray(activityLogs) || activityLogs.length === 0 ? (
        <div className="text-center py-8 text-gray-500 dark:text-gray-400">
          <p>No activity logs found.</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-neutral-900 shadow overflow-hidden sm:rounded-md">
          <ul className="divide-y divide-gray-200 dark:divide-neutral-800">
            {activityLogs.map((log) => (
              <li key={log.id} className="px-6 py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-sm font-medium text-gray-900 dark:text-gray-100">
                      {log.action}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      {log.username && `by ${log.username}`}
                    </div>
                    <div className="text-xs text-gray-400 dark:text-gray-500">
                      {new Date(log.created_at).toLocaleString()}
                    </div>
                    {log.details && (
                      <div className="text-xs text-gray-600 dark:text-gray-400 mt-1">
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
    switch (effectiveView) {
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
      {!hideChrome && (
        <div className="border-b border-gray-200 pb-4">
          <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Collaboration Management</h2>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
            Manage collaborators and permissions for "{botName}"
          </p>
        </div>
      )}

      {/* Status Messages */}
      {error && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700 dark:text-red-300">{error}</p>
            </div>
          </div>
        </div>
      )}
      {success && (
        <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-md">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-green-700 dark:text-green-300">{success}</p>
            </div>
          </div>
        </div>
      )}

      {/* Navigation Tabs */}
      {!hideChrome && (
        <div className="border-b border-gray-200 dark:border-gray-800">
          <nav className="-mb-px flex space-x-8">
            <button
              onClick={() => setViewMode({ type: 'collaborators' })}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                effectiveView === 'collaborators'
                  ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
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
                effectiveView === 'activity'
                  ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
              }`}
            >
              Activity Log
            </button>
            {canManageCollaborators && (
              <button
                onClick={() => setViewMode({ type: 'bulk-update' })}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  effectiveView === 'bulk-update'
                    ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600'
                }`}
              >
                Bulk Update
              </button>
            )}
          </nav>
        </div>
      )}

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