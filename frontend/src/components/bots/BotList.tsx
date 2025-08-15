/**
 * Bot list component with filtering and actions
 */
import React, { useState } from 'react';
import { BotWithRole, BotListFilters, BotDeleteConfirmation } from '../../types/bot';
import { botService } from '../../services/botService';

interface BotListProps {
  bots: BotWithRole[];
  isLoading: boolean;
  filters: BotListFilters;
  onFiltersChange: (filters: BotListFilters) => void;
  onCreateBot: () => void;
  onEditBot: (bot: BotWithRole) => void;
  onDeleteBot: (botId: string) => void;
  onTransferOwnership: (bot: BotWithRole) => void;
  onManageCollaboration?: (bot: BotWithRole) => void;
}

export const BotList: React.FC<BotListProps> = ({
  bots,
  isLoading,
  filters,
  onFiltersChange,
  onCreateBot,
  onEditBot,
  onDeleteBot,
  onTransferOwnership,
  onManageCollaboration,
}) => {
  const [deleteConfirmation, setDeleteConfirmation] = useState<string | null>(null);
  const [deleteInfo, setDeleteInfo] = useState<BotDeleteConfirmation | null>(null);
  const [isLoadingDeleteInfo, setIsLoadingDeleteInfo] = useState(false);

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFiltersChange({ ...filters, search: e.target.value });
  };

  const handleRoleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const role = e.target.value as 'owner' | 'admin' | 'editor' | 'viewer' | '';
    onFiltersChange({ ...filters, role: role || undefined });
  };

  const handleProviderFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const provider = e.target.value as 'openai' | 'anthropic' | 'openrouter' | 'gemini' | '';
    onFiltersChange({ ...filters, provider: provider || undefined });
  };

  const handleSortChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const [sort_by, sort_order] = e.target.value.split('-') as [string, 'asc' | 'desc'];
    onFiltersChange({ ...filters, sort_by: sort_by as any, sort_order });
  };

  const handleDeleteClick = async (botId: string) => {
    if (deleteConfirmation === botId && deleteInfo) {
      onDeleteBot(botId);
      setDeleteConfirmation(null);
      setDeleteInfo(null);
    } else {
      // Load delete confirmation info from backend
      setDeleteConfirmation(botId);
      setIsLoadingDeleteInfo(true);
      try {
        const info = await botService.getBotDeleteInfo(botId);
        setDeleteInfo(info);
      } catch (error) {
        console.error('Failed to load delete info:', error);
        // Still allow deletion even if we can't load the info
        setDeleteInfo({
          bot_id: botId,
          bot_name: bots.find(b => b.bot.id === botId)?.bot.name || 'Unknown Bot',
          cascade_info: {
            conversations: 0,
            messages: 0,
            documents: 0,
            collaborators: 0,
          },
        });
      } finally {
        setIsLoadingDeleteInfo(false);
      }
    }
  };

  const handleCancelDelete = () => {
    setDeleteConfirmation(null);
    setDeleteInfo(null);
  };

  const getProviderIcon = (provider: string) => {
    const icons = {
      openai: '🤖',
      anthropic: '🧠',
      gemini: '💎',
      openrouter: '🔀',
    };
    return icons[provider as keyof typeof icons] || '🤖';
  };

  const getProviderName = (provider: string) => {
    const names = {
      openai: 'OpenAI',
      anthropic: 'Anthropic',
      gemini: 'Google Gemini',
      openrouter: 'OpenRouter',
    };
    return names[provider as keyof typeof names] || provider;
  };

  const getRoleBadgeColor = (role: string) => {
    const colors = {
      owner: 'bg-accent-100 text-accent-700',
      admin: 'bg-primary-100 text-primary-700',
      editor: 'bg-success-100 text-success-700',
      viewer: 'bg-neutral-100 text-neutral-700',
    };
    return colors[role as keyof typeof colors] || 'bg-gray-100 text-gray-800';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-4">
        {/* Loading skeleton */}
        {[...Array(3)].map((_, i) => (
          <div key={i} className="bg-white dark:bg-neutral-900 rounded-lg shadow p-6 animate-pulse">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                 <div className="w-12 h-12 bg-neutral-200 dark:bg-neutral-800 rounded-lg"></div>
                <div className="space-y-2">
                  <div className="h-4 bg-neutral-200 dark:bg-neutral-800 rounded w-32"></div>
                  <div className="h-3 bg-neutral-200 dark:bg-neutral-800 rounded w-48"></div>
                </div>
              </div>
              <div className="flex space-x-2">
               <div className="h-8 bg-neutral-200 dark:bg-neutral-800 rounded w-16"></div>
               <div className="h-8 bg-neutral-200 dark:bg-neutral-800 rounded w-16"></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters and Actions */}
      <div className="bg-white dark:bg-neutral-900 rounded-lg shadow p-6">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between space-y-4 lg:space-y-0">
          {/* Search and Filters */}
          <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4">
            {/* Search */}
            <div className="relative">
              <input
                type="text"
                placeholder="Search bots..."
                value={filters.search || ''}
                onChange={handleSearchChange}
               className="pl-10 pr-4 py-2 border border-neutral-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent dark:bg-neutral-900 dark:border-neutral-700"
              />
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <svg className="h-5 w-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </div>
            </div>

            {/* Role Filter */}
            <div className="relative">
            <select
              value={filters.role || ''}
              onChange={handleRoleFilterChange}
              className="appearance-none pr-10 px-3 py-2 border border-neutral-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white text-neutral-700 dark:text-neutral-200 dark:bg-neutral-900 dark:border-neutral-700"
            >
              <option value="">All Roles</option>
              <option value="owner">Owner</option>
              <option value="admin">Admin</option>
              <option value="editor">Editor</option>
              <option value="viewer">Viewer</option>
            </select>
            <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-neutral-500 dark:text-neutral-400">
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 011.08 1.04l-4.25 4.25a.75.75 0 01-1.06 0L5.21 8.27a.75.75 0 01.02-1.06z" clip-rule="evenodd" /></svg>
            </span>
            </div>

            {/* Provider Filter */}
            <div className="relative">
            <select
              value={filters.provider || ''}
              onChange={handleProviderFilterChange}
              className="appearance-none pr-10 px-3 py-2 border border-neutral-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white text-neutral-700 dark:text-neutral-200 dark:bg-neutral-900 dark:border-neutral-700"
            >
              <option value="">All Providers</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="gemini">Google Gemini</option>
              <option value="openrouter">OpenRouter</option>
            </select>
            <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-neutral-500 dark:text-neutral-400">
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 011.08 1.04l-4.25 4.25a.75.75 0 01-1.06 0L5.21 8.27a.75.75 0 01.02-1.06z" clip-rule="evenodd" /></svg>
            </span>
            </div>

            {/* Sort */}
            <div className="relative">
            <select
              value={`${filters.sort_by || 'updated_at'}-${filters.sort_order || 'desc'}`}
              onChange={handleSortChange}
              className="appearance-none pr-10 px-3 py-2 border border-neutral-300 rounded-md focus:ring-2 focus:ring-primary-500 focus:border-transparent bg-white text-neutral-700 dark:text-neutral-200 dark:bg-neutral-900 dark:border-neutral-700"
            >
              <option value="updated_at-desc">Recently Updated</option>
              <option value="updated_at-asc">Oldest Updated</option>
              <option value="created_at-desc">Recently Created</option>
              <option value="created_at-asc">Oldest Created</option>
              <option value="name-asc">Name A-Z</option>
              <option value="name-desc">Name Z-A</option>
            </select>
            <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-neutral-500 dark:text-neutral-400">
              <svg className="h-4 w-4" viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 011.06.02L10 10.94l3.71-3.71a.75.75 0 011.08 1.04l-4.25 4.25a.75.75 0 01-1.06 0L5.21 8.27a.75.75 0 01.02-1.06z" clip-rule="evenodd" /></svg>
            </span>
            </div>
          </div>

          {/* Create Bot Button */}
          <button
            onClick={onCreateBot}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
          >
            <svg className="-ml-1 mr-2 h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            Create Bot
          </button>
        </div>
      </div>

      {/* Bot List */}
      {bots.length === 0 ? (
        <div className="bg-white dark:bg-neutral-900 rounded-lg shadow p-12 text-center">
          <div className="mx-auto h-24 w-24 text-gray-400">
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <h3 className="mt-4 text-lg font-medium text-neutral-900 dark:text-neutral-100">No Bots Found</h3>
          <p className="mt-2 text-neutral-500 dark:text-neutral-400">
            {filters.search || filters.role || filters.provider
              ? 'No bots match your current filters. Try adjusting your search criteria.'
              : 'Get started by creating your first AI assistant.'}
          </p>
          {!filters.search && !filters.role && !filters.provider && (
            <button
              onClick={onCreateBot}
              className="mt-4 inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
            >
              Create Your First Bot
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {bots.map((botWithRole) => (
            <div
              key={botWithRole.bot.id}
              className="bg-white dark:bg-neutral-900 rounded-lg shadow hover:shadow-md transition-shadow duration-200 p-6"
            >
              <div className="flex items-center justify-between">
                {/* Bot Info */}
                <div className="flex items-center space-x-4">
                  {/* Provider Icon */}
                  <div className="flex-shrink-0">
                    <div className="w-12 h-12 bg-neutral-100 dark:bg-neutral-800 rounded-lg flex items-center justify-center text-2xl">
                      {getProviderIcon(botWithRole.bot.llm_provider)}
                    </div>
                  </div>

                  {/* Bot Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <h3 className="text-lg font-medium text-neutral-900 dark:text-neutral-100 truncate">
                        {botWithRole.bot.name}
                      </h3>
                      <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRoleBadgeColor(botWithRole.role)}`}>
                        {botWithRole.role}
                      </span>
                      {botWithRole.bot.is_public && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-warning-100 text-warning-600">
                          Public
                        </span>
                      )}
                    </div>
                    
                    {botWithRole.bot.description && (
                      <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400 truncate">
                        {botWithRole.bot.description}
                      </p>
                    )}
                    
                    <div className="mt-2 flex items-center space-x-4 text-sm text-neutral-500 dark:text-neutral-400">
                      <span>
                        {getProviderName(botWithRole.bot.llm_provider)} • {botWithRole.bot.llm_model}
                      </span>
                      <span>•</span>
                      <span>Updated {formatDate(botWithRole.bot.updated_at)}</span>
                    </div>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center space-x-2">
                  {/* Chat Button - Always visible for users with view permissions */}
                  <a
                    href={`/bots/${botWithRole.bot.id}/chat`}
                    className="inline-flex items-center px-3 py-2 border border-success-300 shadow-sm text-sm leading-4 font-medium rounded-md text-success-700 bg-white hover:bg-success-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-success-600 dark:bg-neutral-900 dark:border-success-800 dark:text-success-300"
                  >
                    <svg className="-ml-0.5 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                    </svg>
                    Chat
                  </a>

                  {/* Documents Button - Visible for users with view permissions */}
                  <a
                    href={`/bots/${botWithRole.bot.id}/documents`}
                    className="inline-flex items-center px-3 py-2 border border-accent-300 shadow-sm text-sm leading-4 font-medium rounded-md text-accent-700 bg-white hover:bg-accent-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-accent-500 dark:bg-neutral-900 dark:border-accent-800 dark:text-accent-300"
                  >
                    <svg className="-ml-0.5 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    Documents
                  </a>

                  {/* Edit Button */}
                  {(botWithRole.role === 'owner' || botWithRole.role === 'admin') && (
                    <button
                      onClick={() => onEditBot(botWithRole)}
                      className="inline-flex items-center px-3 py-2 border border-neutral-300 shadow-sm text-sm leading-4 font-medium rounded-md text-neutral-700 bg-white hover:bg-neutral-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 dark:bg-neutral-900 dark:border-neutral-700 dark:text-neutral-200"
                    >
                      <svg className="-ml-0.5 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                      </svg>
                      Edit
                    </button>
                  )}

                  {/* Manage Collaboration Button */}
                  {botWithRole.bot.allow_collaboration && onManageCollaboration && (
                    <button
                      onClick={() => onManageCollaboration(botWithRole)}
                      className="inline-flex items-center px-3 py-2 border border-primary-300 shadow-sm text-sm leading-4 font-medium rounded-md text-primary-700 bg-white hover:bg-primary-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 dark:bg-neutral-900 dark:border-primary-800 dark:text-primary-300"
                    >
                      <svg className="-ml-0.5 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                      </svg>
                      Collaboration
                    </button>
                  )}

                  {/* Transfer Ownership Button */}
                  {botWithRole.role === 'owner' && (
                    <button
                      onClick={() => onTransferOwnership(botWithRole)}
                      className="inline-flex items-center px-3 py-2 border border-neutral-300 shadow-sm text-sm leading-4 font-medium rounded-md text-neutral-700 bg-white hover:bg-neutral-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 dark:bg-neutral-900 dark:border-neutral-700 dark:text-neutral-200"
                    >
                      <svg className="-ml-0.5 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                      </svg>
                      Transfer
                    </button>
                  )}

                  {/* Delete Button */}
                  {botWithRole.role === 'owner' && (
                    <button
                      onClick={() => handleDeleteClick(botWithRole.bot.id)}
                      className="inline-flex items-center px-3 py-2 border border-danger-300 shadow-sm text-sm leading-4 font-medium rounded-md text-danger-700 bg-white hover:bg-danger-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-danger-500 dark:bg-neutral-900 dark:border-danger-800 dark:text-danger-300"
                    >
                      <svg className="-ml-0.5 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                      Delete
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmation && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <div className="mt-3">
              {/* Modal Header */}
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-medium text-gray-900">Delete Bot</h3>
                <button
                  onClick={handleCancelDelete}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              {/* Modal Content */}
              {isLoadingDeleteInfo ? (
                <div className="animate-pulse space-y-4">
                  <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                  <div className="h-4 bg-gray-200 rounded w-2/3"></div>
                </div>
              ) : deleteInfo ? (
                <div className="space-y-4">
                  <div className="flex items-center space-x-3">
                    <div className="flex-shrink-0">
                      <svg className="h-8 w-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.5 0L4.268 16.5c-.77.833.192 2.5 1.732 2.5z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-sm text-gray-900">
                        Are you sure you want to delete <strong>{deleteInfo.bot_name}</strong>?
                      </p>
                      <p className="text-sm text-red-600 mt-1">
                        This action cannot be undone.
                      </p>
                    </div>
                  </div>

                  {/* Cascade Information */}
                  <div className="bg-red-50 border border-red-200 rounded-md p-4">
                    <h4 className="text-sm font-medium text-red-800 mb-2">
                      The following data will also be deleted:
                    </h4>
                    <ul className="text-sm text-red-700 space-y-1">
                      <li>• {deleteInfo.cascade_info.conversations} conversation sessions</li>
                      <li>• {deleteInfo.cascade_info.messages} messages</li>
                      <li>• {deleteInfo.cascade_info.documents} documents</li>
                      <li>• {deleteInfo.cascade_info.collaborators} collaborator permissions</li>
                    </ul>
                  </div>

                  {/* Action Buttons */}
                  <div className="flex justify-end space-x-3 pt-4">
                    <button
                      onClick={handleCancelDelete}
                      className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
                    >
                      Cancel
                    </button>
                    <button
                      onClick={() => handleDeleteClick(deleteConfirmation)}
                      className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                    >
                      Delete Bot
                    </button>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};