/**
 * Bot ownership transfer modal component
 */
import React, { useState, useEffect } from 'react';
import { BotWithRole, BotTransferRequest } from '../../types/bot';
import { botService } from '../../services/botService';
import { Button } from '../common/Button';
import { log } from '../../utils/logger';

interface BotTransferModalProps {
  bot: BotWithRole;
  isOpen: boolean;
  onClose: () => void;
  onTransfer: (botId: string, request: BotTransferRequest) => Promise<void>;
}

interface UserSearchResult {
  id: string;
  username: string;
  email: string;
}

export const BotTransferModal: React.FC<BotTransferModalProps> = ({
  bot,
  isOpen,
  onClose,
  onTransfer,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<UserSearchResult[]>([]);
  const [selectedUser, setSelectedUser] = useState<UserSearchResult | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isTransferring, setIsTransferring] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Reset state when modal opens/closes
  useEffect(() => {
    if (isOpen) {
      setSearchQuery('');
      setSearchResults([]);
      setSelectedUser(null);
      setSearchError(null);
    }
  }, [isOpen]);

  // Search for users with debouncing
  useEffect(() => {
    if (!searchQuery.trim() || searchQuery.length < 2) {
      setSearchResults([]);
      return;
    }

    const searchTimeout = setTimeout(async () => {
      try {
        setIsSearching(true);
        setSearchError(null);
        const results = await botService.searchUsers(searchQuery);
        setSearchResults(results);
      } catch (error) { log.error('Failed to search users:', 'BotTransferModal', { error });
        setSearchError('Failed to search users. Please try again.');
        setSearchResults([]);
      } finally {
        setIsSearching(false);
      }
    }, 300);

    return () => clearTimeout(searchTimeout);
  }, [searchQuery]);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value);
    setSelectedUser(null);
  };

  const handleUserSelect = (user: UserSearchResult) => {
    setSelectedUser(user);
    setSearchQuery(user.username);
    setSearchResults([]);
  };

  const handleTransfer = async () => {
    if (!selectedUser) return;

    try {
      setIsTransferring(true);
      await onTransfer(bot.bot.id, { new_owner_id: selectedUser.id });
      onClose();
    } catch (error) { log.error('Failed to transfer ownership:', 'BotTransferModal', { error });
      setSearchError('Failed to transfer ownership. Please try again.');
    } finally {
      setIsTransferring(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 overflow-y-auto h-full w-full z-40">
      <div className="relative top-20 mx-auto p-5 border border-gray-200 dark:border-gray-800 w-96 shadow-xl rounded-xl bg-white dark:bg-gray-900">
        <div className="mt-3">
          {/* Modal Header */}
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100">Transfer Bot Ownership</h3>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300"
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Modal Content */}
          <div className="space-y-4">
            {/* Bot Info */}
            <div className="bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-800 rounded-md p-4">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <svg className="h-8 w-8 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">{bot.bot.name}</h4>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {bot.bot.description || 'No description'}
                  </p>
                </div>
              </div>
            </div>

            {/* Warning */}
            <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-md p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                    Important: This action cannot be undone
                  </h3>
                  <div className="mt-2 text-sm text-yellow-700 dark:text-yellow-300">
                    <p>
                      Once you transfer ownership, you will lose all owner privileges for this bot. 
                      The new owner will have full control and can remove your access entirely.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* User Search */}
            <div>
              <label htmlFor="user-search" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Search for new owner
              </label>
              <div className="relative">
                <input
                  id="user-search"
                  type="text"
                  placeholder="Enter username or email..."
                  value={searchQuery}
                  onChange={handleSearchChange}
                  className="h-10 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 w-full pl-10 pr-4 py-2 placeholder:text-gray-400 focus-visible:ring focus-visible:ring-offset-0 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                {isSearching && (
                  <div className="absolute inset-y-0 right-0 pr-3 flex items-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                  </div>
                )}
              </div>

              {/* Search Results */}
              {searchResults.length > 0 && (
                <div className="mt-2 max-h-40 overflow-y-auto border border-gray-300 dark:border-gray-700 rounded-md bg-white dark:bg-gray-900 shadow-sm">
                  {searchResults.map((user) => (
                    <button
                      key={user.id}
                      onClick={() => handleUserSelect(user)}
                      className="w-full px-4 py-2 text-left hover:bg-gray-50 dark:hover:bg-gray-800/50 focus:bg-gray-50 dark:focus:bg-gray-800/50 focus:outline-none border-b border-gray-100 dark:border-gray-800 last:border-b-0"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="flex-shrink-0">
                          <div className="w-8 h-8 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center">
                            <span className="text-sm font-medium text-gray-600 dark:text-gray-300">
                              {user.username.charAt(0).toUpperCase()}
                            </span>
                          </div>
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                            {user.username}
                          </p>
                          <p className="text-sm text-gray-500 dark:text-gray-400 truncate">
                            {user.email}
                          </p>
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              )}

              {/* Selected User */}
              {selectedUser && (
                <div className="mt-2 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-md">
                  <div className="flex items-center space-x-3">
                    <div className="flex-shrink-0">
                      <div className="w-8 h-8 bg-blue-200 dark:bg-blue-700 rounded-full flex items-center justify-center">
                        <span className="text-sm font-medium text-blue-800 dark:text-blue-200">
                          {selectedUser.username.charAt(0).toUpperCase()}
                        </span>
                      </div>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-blue-900 dark:text-blue-100">
                        {selectedUser.username}
                      </p>
                      <p className="text-sm text-blue-700 dark:text-blue-300">
                        {selectedUser.email}
                      </p>
                    </div>
                    <button
                      onClick={() => {
                        setSelectedUser(null);
                        setSearchQuery('');
                      }}
                      className="text-blue-400 hover:text-blue-600 dark:text-blue-300 dark:hover:text-blue-200"
                    >
                      <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </div>
              )}

              {/* Search Error */}
              {searchError && (
                <div className="mt-2 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md">
                  <p className="text-sm text-red-600 dark:text-red-400">{searchError}</p>
                </div>
              )}

              {/* No Results */}
              {searchQuery.length >= 2 && !isSearching && searchResults.length === 0 && !searchError && (
                <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900/40 border border-gray-200 dark:border-gray-800 rounded-md">
                  <p className="text-sm text-gray-600 dark:text-gray-400">No users found matching "{searchQuery}"</p>
                </div>
              )}
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end space-x-3 pt-4">
              <Button
                onClick={onClose}
                disabled={isTransferring}
                variant="outline"
                size="sm"
              >
                Cancel
              </Button>
              <Button
                onClick={handleTransfer}
                disabled={!selectedUser || isTransferring}
                size="sm"
              >
                {isTransferring ? 'Transferring...' : 'Transfer Ownership'}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};