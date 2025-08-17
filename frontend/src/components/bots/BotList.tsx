/**
 * Bot list component with filtering and actions
 */
import React, { useState } from 'react';
import { BotWithRole, BotListFilters, BotDeleteConfirmation } from '../../types/bot';
import { botService } from '../../services/botService';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { Modal } from '../common/Modal';
import { MagnifyingGlassIcon, ChevronDownIcon, PlusIcon, ComputerDesktopIcon, ChatBubbleLeftRightIcon, DocumentTextIcon, PencilIcon, UserGroupIcon, ArrowsRightLeftIcon, TrashIcon, XMarkIcon, ExclamationTriangleIcon, EllipsisVerticalIcon, Cog6ToothIcon } from '@heroicons/react/24/outline';

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
  onIntegrations?: (bot: BotWithRole) => void;
  onDocuments?: (bot: BotWithRole) => void;
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
  onIntegrations,
  onDocuments,
}) => {
  const [deleteConfirmation, setDeleteConfirmation] = useState<string | null>(null);
  const [deleteInfo, setDeleteInfo] = useState<BotDeleteConfirmation | null>(null);
  const [isLoadingDeleteInfo, setIsLoadingDeleteInfo] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

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
      <div className="space-y-6">
        {/* Loading skeleton */}
        {[...Array(3)].map((_, i) => (
          <Card key={i} className="animate-pulse">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                 <div className="w-12 h-12 bg-gray-200 dark:bg-gray-800 rounded-lg"></div>
                <div className="space-y-2">
                  <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-32"></div>
                  <div className="h-3 bg-gray-200 dark:bg-gray-800 rounded w-48"></div>
                </div>
              </div>
              <div className="flex space-x-2">
               <div className="h-8 bg-gray-200 dark:bg-gray-800 rounded w-16"></div>
               <div className="h-8 bg-gray-200 dark:bg-gray-800 rounded w-16"></div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Filters and Actions */}
      <Card>
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
               className="h-10 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 pl-10 pr-4 py-2 placeholder:text-gray-400 focus-visible:ring focus-visible:ring-offset-0 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              />
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <MagnifyingGlassIcon className="h-5 w-5 text-gray-400" />
              </div>
            </div>

            {/* Role Filter */}
            <div className="relative">
            <select
              value={filters.role || ''}
              onChange={handleRoleFilterChange}
              className="h-10 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 appearance-none pr-10 px-3 py-2 text-gray-700 dark:text-gray-200 focus-visible:ring focus-visible:ring-offset-0 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">All Roles</option>
              <option value="owner">Owner</option>
              <option value="admin">Admin</option>
              <option value="editor">Editor</option>
              <option value="viewer">Viewer</option>
            </select>
            <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-gray-500 dark:text-gray-400">
              <ChevronDownIcon className="h-4 w-4" />
            </span>
            </div>

            {/* Provider Filter */}
            <div className="relative">
            <select
              value={filters.provider || ''}
              onChange={handleProviderFilterChange}
              className="h-10 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 appearance-none pr-10 px-3 py-2 text-gray-700 dark:text-gray-200 focus-visible:ring focus-visible:ring-offset-0 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="">All Providers</option>
              <option value="openai">OpenAI</option>
              <option value="anthropic">Anthropic</option>
              <option value="gemini">Google Gemini</option>
              <option value="openrouter">OpenRouter</option>
            </select>
            <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-gray-500 dark:text-gray-400">
              <ChevronDownIcon className="h-4 w-4" />
            </span>
            </div>

            {/* Sort */}
            <div className="relative">
            <select
              value={`${filters.sort_by || 'updated_at'}-${filters.sort_order || 'desc'}`}
              onChange={handleSortChange}
              className="h-10 rounded-md border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 appearance-none pr-10 px-3 py-2 text-gray-700 dark:text-gray-200 focus-visible:ring focus-visible:ring-offset-0 focus:ring-2 focus:ring-primary-500 focus:border-transparent"
            >
              <option value="updated_at-desc">Recently Updated</option>
              <option value="updated_at-asc">Oldest Updated</option>
              <option value="created_at-desc">Recently Created</option>
              <option value="created_at-asc">Oldest Created</option>
              <option value="name-asc">Name A-Z</option>
              <option value="name-desc">Name Z-A</option>
            </select>
            <span className="pointer-events-none absolute inset-y-0 right-3 flex items-center text-gray-500 dark:text-gray-400">
              <ChevronDownIcon className="h-4 w-4" />
            </span>
            </div>
          </div>

          {/* Create Bot Button */}
          <Button onClick={onCreateBot}>
            <PlusIcon className="-ml-1 mr-2 h-5 w-5" />
            Create Bot
          </Button>
        </div>
      </Card>

      {/* Bot List */}
      {bots.length === 0 ? (
        <Card padding="lg" className="text-center">
          <div className="mx-auto h-24 w-24 text-gray-400">
            <ComputerDesktopIcon className="h-24 w-24" />
          </div>
          <h3 className="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">No Bots Found</h3>
          <p className="mt-2 text-gray-500 dark:text-gray-400">
            {filters.search || filters.role || filters.provider
              ? 'No bots match your current filters. Try adjusting your search criteria.'
              : 'Get started by creating your first AI assistant.'}
          </p>
          {!filters.search && !filters.role && !filters.provider && (
            <div className="mt-4">
              <Button onClick={onCreateBot}>
                Create Your First Bot
              </Button>
            </div>
          )}
        </Card>
      ) : (
        <div className="space-y-4">
          {bots.map((botWithRole) => (
            <Card
              key={botWithRole.bot.id}
              hover
            >
              <div className="flex items-center justify-between">
                {/* Bot Info */}
                <div className="flex items-center space-x-4">
                  {/* Provider Icon */}
                  <div className="flex-shrink-0">
                    <div className="w-12 h-12 bg-gray-100 dark:bg-gray-800 rounded-lg flex items-center justify-center text-2xl">
                      {getProviderIcon(botWithRole.bot.llm_provider)}
                    </div>
                  </div>

                  {/* Bot Details */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 truncate">
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
                      <p className="mt-1 text-sm text-gray-600 dark:text-gray-400 truncate">
                        {botWithRole.bot.description}
                      </p>
                    )}
                    
                    <div className="mt-2 flex items-center space-x-4 text-sm text-gray-500 dark:text-gray-400">
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
                  {/* Chat Button - Primary action, always visible */}
                  <a href={`/bots/${botWithRole.bot.id}/chat`}>
                    <Button variant="success" size="sm">
                      <ChatBubbleLeftRightIcon className="-ml-0.5 mr-2 h-4 w-4" />
                      Chat
                    </Button>
                  </a>

                  {/* Edit Button - Only show for owners/admins */}
                  {(botWithRole.role === 'owner' || botWithRole.role === 'admin') && (
                    <Button
                      onClick={() => onEditBot(botWithRole)}
                      variant="outline"
                      size="sm"
                    >
                      <PencilIcon className="-ml-0.5 mr-2 h-4 w-4" />
                      Edit
                    </Button>
                  )}

                  {/* More Options Dropdown */}
                  <div className="relative">
                    <Button
                      onClick={() => setOpenDropdown(openDropdown === botWithRole.bot.id ? null : botWithRole.bot.id)}
                      variant="outline"
                      size="sm"
                      className="px-2"
                    >
                      <EllipsisVerticalIcon className="h-4 w-4" />
                    </Button>

                    {/* Dropdown Menu */}
                    {openDropdown === botWithRole.bot.id && (
                      <div className="absolute right-0 mt-2 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
                        <div className="py-1" role="menu">
                          {/* Collaboration & Transfer - Combined option for owners */}
                          {(botWithRole.role === 'owner' && (botWithRole.bot.allow_collaboration || onManageCollaboration)) && (
                            <button
                              onClick={() => {
                                if (onManageCollaboration) {
                                  onManageCollaboration(botWithRole);
                                }
                                setOpenDropdown(null);
                              }}
                              className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                              role="menuitem"
                            >
                              <UserGroupIcon className="mr-3 h-4 w-4" />
                              Manage Collaboration
                            </button>
                          )}
                          
                          {/* Documents */}
                          <button
                            onClick={() => {
                              if (onDocuments) {
                                onDocuments(botWithRole);
                              } else {
                                window.location.href = `/bots/${botWithRole.bot.id}/documents`;
                              }
                              setOpenDropdown(null);
                            }}
                            className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                            role="menuitem"
                          >
                            <DocumentTextIcon className="mr-3 h-4 w-4" />
                            Documents
                          </button>
                          
                          {/* Integrations */}
                          <button
                            onClick={() => {
                              if (onIntegrations) {
                                onIntegrations(botWithRole);
                              }
                              setOpenDropdown(null);
                            }}
                            className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                            role="menuitem"
                          >
                            <Cog6ToothIcon className="mr-3 h-4 w-4" />
                            Integrations
                          </button>
                          
                          {/* Transfer Ownership - For owners only */}
                          {botWithRole.role === 'owner' && (
                            <>
                              <div className="border-t border-gray-100 dark:border-gray-600" />
                              <button
                                onClick={() => {
                                  onTransferOwnership(botWithRole);
                                  setOpenDropdown(null);
                                }}
                                className="flex items-center w-full px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700"
                                role="menuitem"
                              >
                                <ArrowsRightLeftIcon className="mr-3 h-4 w-4" />
                                Transfer Ownership
                              </button>
                            </>
                          )}
                          
                          {/* Delete - For owners only */}
                          {botWithRole.role === 'owner' && (
                            <>
                              <div className="border-t border-gray-100 dark:border-gray-600" />
                              <button
                                onClick={() => {
                                  handleDeleteClick(botWithRole.bot.id);
                                  setOpenDropdown(null);
                                }}
                                className="flex items-center w-full px-4 py-2 text-sm text-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20"
                                role="menuitem"
                              >
                                <TrashIcon className="mr-3 h-4 w-4" />
                                Delete Bot
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!deleteConfirmation}
        onClose={handleCancelDelete}
        title="Delete Bot"
        size="md"
        footer={deleteInfo && !isLoadingDeleteInfo ? (
          <>
            <Button
              onClick={handleCancelDelete}
              variant="outline"
              size="sm"
            >
              Cancel
            </Button>
            <Button
              onClick={() => handleDeleteClick(deleteConfirmation)}
              variant="danger"
              size="sm"
            >
              Delete Bot
            </Button>
          </>
        ) : undefined}
      >

        {/* Modal Content */}
        {isLoadingDeleteInfo ? (
          <div className="animate-pulse space-y-4">
            <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-1/2"></div>
            <div className="h-4 bg-gray-200 dark:bg-gray-800 rounded w-2/3"></div>
          </div>
        ) : deleteInfo ? (
          <>
            <div className="space-y-4">
              <div className="flex items-center space-x-3">
                <div className="flex-shrink-0">
                  <ExclamationTriangleIcon className="h-8 w-8 text-red-400" />
                </div>
                <div>
                  <p className="text-sm text-gray-900 dark:text-gray-100">
                    Are you sure you want to delete <strong>{deleteInfo.bot_name}</strong>?
                  </p>
                  <p className="text-sm text-red-600 dark:text-red-400 mt-1">
                    This action cannot be undone.
                  </p>
                </div>
              </div>

              {/* Cascade Information */}
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
                <h4 className="text-sm font-medium text-red-800 dark:text-red-200 mb-2">
                  The following data will also be deleted:
                </h4>
                <ul className="text-sm text-red-700 dark:text-red-300 space-y-1">
                  <li>• {deleteInfo.cascade_info.conversations} conversation sessions</li>
                  <li>• {deleteInfo.cascade_info.messages} messages</li>
                  <li>• {deleteInfo.cascade_info.documents} documents</li>
                  <li>• {deleteInfo.cascade_info.collaborators} collaborator permissions</li>
                </ul>
              </div>
            </div>
          </>
        ) : null}
      </Modal>
    </div>
  );
};