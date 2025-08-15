/**
 * Bulk Permission Management Component
 * Allows updating permissions for multiple users at once
 */
import React, { useState, useEffect } from 'react';
import { BotPermission, BulkPermissionUpdate } from '../../types/bot';
import { permissionService } from '../../services/permissionService';
import { Button } from '../common/Button';
import { Alert } from '../common/Alert';

interface BulkPermissionManagerProps {
  botId: string;
  collaborators: BotPermission[];
  currentUserRole: 'owner' | 'admin' | 'editor' | 'viewer';
  onUpdateComplete?: () => void;
}

interface BulkUpdateItem {
  user_id: string;
  username: string;
  current_role: string;
  new_role: 'admin' | 'editor' | 'viewer';
  selected: boolean;
}

interface BulkUpdateResult {
  successful: BotPermission[];
  failed: Array<{
    user_id: string;
    error: string;
  }>;
  total: number;
}

export const BulkPermissionManager: React.FC<BulkPermissionManagerProps> = ({
  botId,
  collaborators,
  currentUserRole,
  onUpdateComplete
}) => {
  const [bulkItems, setBulkItems] = useState<BulkUpdateItem[]>([]);
  const [selectedRole, setSelectedRole] = useState<'admin' | 'editor' | 'viewer'>('viewer');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [results, setResults] = useState<BulkUpdateResult | null>(null);
  const [showResults, setShowResults] = useState(false);

  // Check permissions
  const canManageCollaborators = ['owner', 'admin'].includes(currentUserRole);
  const isOwner = currentUserRole === 'owner';

  // Initialize bulk items from collaborators
  useEffect(() => {
    const items: BulkUpdateItem[] = collaborators
      .filter(collaborator => collaborator.role !== 'owner') // Can't modify owner
      .map(collaborator => ({
        user_id: collaborator.user_id,
        username: collaborator.username || 'Unknown User',
        current_role: collaborator.role,
        new_role: collaborator.role as 'admin' | 'editor' | 'viewer',
        selected: false
      }));
    setBulkItems(items);
  }, [collaborators]);

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

  const handleSelectAll = (selected: boolean) => {
    setBulkItems(prev => prev.map(item => ({
      ...item,
      selected: selected && item.current_role !== 'owner'
    })));
  };

  const handleSelectItem = (userId: string, selected: boolean) => {
    setBulkItems(prev => prev.map(item => 
      item.user_id === userId ? { ...item, selected } : item
    ));
  };

  const handleRoleChange = (userId: string, newRole: 'admin' | 'editor' | 'viewer') => {
    setBulkItems(prev => prev.map(item => 
      item.user_id === userId ? { ...item, new_role: newRole } : item
    ));
  };

  const handleBulkRoleChange = () => {
    setBulkItems(prev => prev.map(item => ({
      ...item,
      new_role: selectedRole
    })));
  };

  const handleBulkUpdate = async () => {
    const selectedItems = bulkItems.filter(item => item.selected);
    
    if (selectedItems.length === 0) {
      setError('Please select at least one user to update');
      return;
    }

    // Validate permissions
    for (const item of selectedItems) {
      const validation = permissionService.validatePermissionUpdate(
        currentUserRole,
        item.new_role,
        isOwner
      );

      if (!validation.valid) {
        setError(`Cannot update ${item.username}: ${validation.error}`);
        return;
      }
    }

    try {
      setLoading(true);
      setError(null);
      setResults(null);
      setShowResults(false);

      const updates: BulkPermissionUpdate = {
        user_permissions: selectedItems.map(item => ({
          user_id: item.user_id,
          role: item.new_role
        }))
      };

      const response = await permissionService.bulkUpdatePermissions(botId, updates);
      
      // The API returns successful updates as BotPermission[], so we transform it
      const result: BulkUpdateResult = {
        successful: response || [],
        failed: [], // API doesn't return failed items currently, but we keep the structure
        total: response?.length || 0
      };
      
      setResults(result);
      setShowResults(true);
      setSuccess(`Bulk update completed: ${result.successful.length} successful, ${result.failed.length} failed`);
      onUpdateComplete?.();
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to perform bulk update');
      console.error('Error performing bulk update:', err);
    } finally {
      setLoading(false);
    }
  };

  const getSelectedCount = () => bulkItems.filter(item => item.selected).length;

  const getRoleOptions = (currentRole: string) => {
    const options = ['viewer', 'editor'];
    if (isOwner) {
      options.push('admin');
    }
    return options.filter(role => role !== currentRole);
  };

  const renderBulkControls = () => (
    <div className="bg-gray-50 border border-gray-200 rounded-md p-4 mb-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">Bulk Actions</h3>
        <div className="text-sm text-gray-500">
          {getSelectedCount()} of {bulkItems.length} selected
        </div>
      </div>

      <div className="flex items-center space-x-4">
        <div className="flex items-center">
          <input
            type="checkbox"
            checked={getSelectedCount() === bulkItems.length && bulkItems.length > 0}
            onChange={(e) => handleSelectAll(e.target.checked)}
            className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
          />
          <label className="ml-2 text-sm text-gray-700">Select All</label>
        </div>

        <div className="flex items-center space-x-2">
          <label className="text-sm text-gray-700">Set all selected to:</label>
          <select
            value={selectedRole}
            onChange={(e) => setSelectedRole(e.target.value as 'admin' | 'editor' | 'viewer')}
            className="text-sm border border-gray-300 rounded px-2 py-1"
          >
            <option value="viewer">Viewer</option>
            <option value="editor">Editor</option>
            {isOwner && <option value="admin">Admin</option>}
          </select>
          <Button
            onClick={handleBulkRoleChange}
            disabled={getSelectedCount() === 0}
            className="bg-gray-600 hover:bg-gray-700 text-white text-sm px-3 py-1"
          >
            Apply
          </Button>
        </div>

        <Button
          onClick={handleBulkUpdate}
          disabled={getSelectedCount() === 0 || loading}
          className="bg-blue-600 hover:bg-blue-700 text-white"
        >
          {loading ? 'Updating...' : 'Update Selected'}
        </Button>
      </div>
    </div>
  );

  const renderCollaboratorsList = () => (
    <div className="bg-white shadow overflow-hidden sm:rounded-md">
      <ul className="divide-y divide-gray-200">
        {bulkItems.map((item) => (
          <li key={item.user_id} className="px-6 py-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <input
                  type="checkbox"
                  checked={item.selected}
                  onChange={(e) => handleSelectItem(item.user_id, e.target.checked)}
                  disabled={item.current_role === 'owner'}
                  className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <div className="ml-4">
                  <div className="text-sm font-medium text-gray-900">
                    {item.username}
                  </div>
                  <div className="text-sm text-gray-500">
                    Current: {permissionService.formatRoleName(item.current_role)}
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-3">
                <select
                  value={item.new_role}
                  onChange={(e) => handleRoleChange(item.user_id, e.target.value as any)}
                  disabled={item.current_role === 'owner' || loading}
                  className="text-sm border border-gray-300 rounded px-2 py-1"
                >
                  {getRoleOptions(item.current_role).map(role => (
                    <option key={role} value={role}>
                      {permissionService.formatRoleName(role)}
                    </option>
                  ))}
                </select>
                {item.current_role === 'owner' && (
                  <span className="text-xs text-gray-400">Owner (cannot modify)</span>
                )}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );

  const renderResults = () => {
    if (!results || !showResults) return null;

    return (
      <div className="mt-6">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Update Results</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Successful Updates */}
          <div className="bg-green-50 border border-green-200 rounded-md p-4">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h4 className="text-sm font-medium text-green-800">
                  Successful Updates ({results.successful.length})
                </h4>
                <div className="mt-2 text-sm text-green-700">
                  {results.successful.length > 0 ? (
                    <ul className="list-disc list-inside space-y-1">
                      {results.successful.map((item, index) => (
                        <li key={index}>
                          User {item.user_id}: {permissionService.formatRoleName(item.role)}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>No successful updates</p>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Failed Updates */}
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <h4 className="text-sm font-medium text-red-800">
                  Failed Updates ({results.failed.length})
                </h4>
                <div className="mt-2 text-sm text-red-700">
                  {results.failed.length > 0 ? (
                    <ul className="list-disc list-inside space-y-1">
                      {results.failed.map((item, index) => (
                        <li key={index}>
                          User {item.user_id}: {item.error}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p>No failed updates</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-4 flex justify-end">
          <Button
            onClick={() => setShowResults(false)}
            className="bg-gray-600 hover:bg-gray-700 text-white"
          >
            Close Results
          </Button>
        </div>
      </div>
    );
  };

  if (!canManageCollaborators) {
    return (
      <div className="text-center py-8">
        <div className="text-gray-500">
          <svg className="mx-auto h-12 w-12 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">Access Denied</h3>
          <p className="mt-1 text-sm text-gray-500">
            You need admin or owner permissions to manage collaborators.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-2xl font-bold text-gray-900">Bulk Permission Management</h2>
        <p className="mt-1 text-sm text-gray-600">
          Update permissions for multiple collaborators at once
        </p>
      </div>

      {/* Alerts */}
      {error && <Alert type="error" message={error} />}
      {success && <Alert type="success" message={success} />}

      {/* Warning */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-yellow-800">
              Bulk Update Warning
            </h3>
            <div className="mt-2 text-sm text-yellow-700">
              <p>
                This action will update permissions for multiple users simultaneously.
                Please review your selections carefully before proceeding.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Bulk Controls */}
      {renderBulkControls()}

      {/* Collaborators List */}
      {renderCollaboratorsList()}

      {/* Results */}
      {renderResults()}
    </div>
  );
}; 