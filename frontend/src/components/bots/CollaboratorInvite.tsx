/**
 * Collaborator invitation component
 */
import React, { useState, useEffect } from 'react';
import { CollaboratorInvite, CollaboratorInviteResponse } from '../../types/bot';
import { permissionService } from '../../services/permissionService';
import { Button } from '../common/Button';
import { Input } from '../common/Input';

interface CollaboratorInviteProps {
  botId: string;
  isOpen: boolean;
  onClose: () => void;
  onInviteSuccess: (response: CollaboratorInviteResponse) => void;
}

interface UserSearchResult {
  id: string;
  username: string;
  email: string;
  full_name?: string;
}

export const CollaboratorInviteModal: React.FC<CollaboratorInviteProps> = ({
  botId,
  isOpen,
  onClose,
  onInviteSuccess,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<UserSearchResult[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserSearchResult | null>(null);
  const [selectedRole, setSelectedRole] = useState<'admin' | 'editor' | 'viewer'>('viewer');
  const [inviteMessage, setInviteMessage] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [isInviting, setIsInviting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchTimeout, setSearchTimeout] = useState<number | null>(null);

  // Clear state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setSearchQuery('');
      setSearchResults([]);
      setSelectedUser(null);
      setSelectedRole('viewer');
      setInviteMessage('');
      setError(null);
    }
  }, [isOpen]);

  // Debounced search
  useEffect(() => {
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }

    if (searchQuery.trim().length >= 2) {
      const timeout = setTimeout(() => {
        performSearch(searchQuery.trim());
      }, 300);
      setSearchTimeout(timeout);
    } else {
      setSearchResults([]);
    }

    return () => {
      if (searchTimeout) {
        clearTimeout(searchTimeout);
      }
    };
  }, [searchQuery]);

  const performSearch = async (query: string) => {
    try {
      setIsSearching(true);
      setError(null);
      const results = await permissionService.searchUsers(query);
      setSearchResults(results);
    } catch (error: any) {
      console.error('Failed to search users:', error);
      setError('Failed to search users. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleUserSelect = (user: UserSearchResult) => {
    setSelectedUser(user);
    setSearchQuery(user.username);
    setSearchResults([]);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!selectedUser) {
      setError('Please select a user to invite');
      return;
    }

    try {
      setIsInviting(true);
      setError(null);

      const inviteData: CollaboratorInvite = {
        identifier: selectedUser.username, // Use username as identifier
        role: selectedRole,
        message: inviteMessage.trim() || undefined,
      };

      const response = await permissionService.inviteCollaborator(botId, inviteData);
      onInviteSuccess(response);
    } catch (error: any) {
      console.error('Failed to invite collaborator:', error);
      setError(error.response?.data?.detail || 'Failed to invite collaborator. Please try again.');
    } finally {
      setIsInviting(false);
    }
  };

  const handleClose = () => {
    if (!isInviting) {
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <div className="mt-3">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-medium text-gray-900">Invite Collaborator</h3>
            <button
              onClick={handleClose}
              disabled={isInviting}
              className="text-gray-400 hover:text-gray-600"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Error Display */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-md p-3">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            {/* User Search */}
            <div>
              <label htmlFor="user-search" className="block text-sm font-medium text-gray-700 mb-2">
                Search User
              </label>
              <div className="relative">
                <Input
                  id="user-search"
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by username or email..."
                  disabled={isInviting}
                  className="w-full"
                />
                {isSearching && (
                  <div className="absolute right-3 top-1/2 transform -translate-y-1/2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                  </div>
                )}
              </div>

              {/* Search Results */}
              {searchResults.length > 0 && (
                <div className="mt-2 border border-gray-200 rounded-md max-h-40 overflow-y-auto">
                  {searchResults.map((user) => (
                    <button
                      key={user.id}
                      type="button"
                      onClick={() => handleUserSelect(user)}
                      className="w-full text-left px-3 py-2 hover:bg-gray-50 border-b border-gray-100 last:border-b-0"
                    >
                      <div className="font-medium text-gray-900">{user.username}</div>
                      <div className="text-sm text-gray-500">{user.email}</div>
                      {user.full_name && (
                        <div className="text-xs text-gray-400">{user.full_name}</div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Selected User Display */}
            {selectedUser && (
              <div className="bg-blue-50 border border-blue-200 rounded-md p-3">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className="h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center">
                      <span className="text-sm font-medium text-white">
                        {selectedUser.username.charAt(0).toUpperCase()}
                      </span>
                    </div>
                  </div>
                  <div className="ml-3">
                    <div className="text-sm font-medium text-blue-900">
                      {selectedUser.username}
                    </div>
                    <div className="text-sm text-blue-700">{selectedUser.email}</div>
                  </div>
                </div>
              </div>
            )}

            {/* Role Selection */}
            <div>
              <label htmlFor="role-select" className="block text-sm font-medium text-gray-700 mb-2">
                Role
              </label>
              <select
                id="role-select"
                value={selectedRole}
                onChange={(e) => setSelectedRole(e.target.value as 'admin' | 'editor' | 'viewer')}
                disabled={isInviting}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                <option value="viewer">Viewer</option>
                <option value="editor">Editor</option>
                <option value="admin">Admin</option>
              </select>
              <p className="mt-1 text-xs text-gray-500">
                {permissionService.getRoleDescription(selectedRole)}
              </p>
            </div>

            {/* Optional Message */}
            <div>
              <label htmlFor="invite-message" className="block text-sm font-medium text-gray-700 mb-2">
                Message (Optional)
              </label>
              <textarea
                id="invite-message"
                value={inviteMessage}
                onChange={(e) => setInviteMessage(e.target.value)}
                placeholder="Add a personal message to the invitation..."
                disabled={isInviting}
                rows={3}
                className="w-full border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end space-x-3 pt-4">
              <Button
                type="button"
                onClick={handleClose}
                disabled={isInviting}
                className="bg-gray-300 hover:bg-gray-400 text-gray-700"
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={!selectedUser || isInviting}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                {isInviting ? 'Inviting...' : 'Send Invitation'}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};