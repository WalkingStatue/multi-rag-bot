/**
 * API Key list component for displaying and managing API keys
 */
import React, { useState } from 'react';
import { APIKeyResponse, ProviderInfo } from '../../types/api';

interface APIKeyListProps {
  apiKeys: APIKeyResponse[];
  providers: Record<string, ProviderInfo>;
  onEdit: (provider: string) => void;
  onDelete: (provider: string) => void;
  isLoading?: boolean;
}

export const APIKeyList: React.FC<APIKeyListProps> = ({
  apiKeys,
  providers,
  onEdit,
  onDelete,
  isLoading = false,
}) => {
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const getProviderDisplayName = (provider: string) => {
    const names: Record<string, string> = {
      openai: 'OpenAI',
      anthropic: 'Anthropic',
      openrouter: 'OpenRouter',
      gemini: 'Google Gemini',
    };
    return names[provider] || provider;
  };

  const getProviderIcon = (provider: string) => {
    const icons: Record<string, string> = {
      openai: '🤖',
      anthropic: '🧠',
      openrouter: '🔀',
      gemini: '💎',
    };
    return icons[provider] || '🔑';
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

  const handleDelete = (provider: string) => {
    if (deleteConfirm === provider) {
      onDelete(provider);
      setDeleteConfirm(null);
    } else {
      setDeleteConfirm(provider);
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-md p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-neutral-200 dark:bg-neutral-800 rounded w-1/4 mb-4"></div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-neutral-200 dark:bg-neutral-800 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (apiKeys.length === 0) {
    return (
      <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Your API Keys</h3>
        <div className="text-center py-8">
          <div className="text-4xl mb-4">🔑</div>
          <h4 className="text-lg font-medium text-neutral-900 dark:text-neutral-100 mb-2">No API Keys</h4>
          <p className="text-neutral-600 dark:text-neutral-400 mb-4">
            Add your first API key to start using the platform with your preferred LLM provider.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">Your API Keys</h3>
      
      <div className="space-y-4">
        {apiKeys.map((apiKey) => (
          <div
            key={apiKey.id}
            className="border border-neutral-200 dark:border-neutral-800 rounded-lg p-4 hover:shadow-sm transition-shadow"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className="text-2xl">{getProviderIcon(apiKey.provider)}</div>
                <div>
                  <h4 className="font-medium text-neutral-900 dark:text-neutral-100">
                    {getProviderDisplayName(apiKey.provider)}
                  </h4>
                  <div className="flex items-center space-x-4 text-sm text-neutral-500 dark:text-neutral-400">
                    <span>Added {formatDate(apiKey.created_at)}</span>
                    {apiKey.updated_at !== apiKey.created_at && (
                      <span>Updated {formatDate(apiKey.updated_at)}</span>
                    )}
                    <span
                      className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                        apiKey.is_active
                          ? 'bg-success-100 text-success-700'
                          : 'bg-danger-100 text-danger-700'
                      }`}
                    >
                      {apiKey.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <button
                  onClick={() => onEdit(apiKey.provider)}
                  className="px-3 py-1 text-sm font-medium text-primary-600 hover:text-primary-800 hover:bg-primary-50 rounded"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(apiKey.provider)}
                  className={`px-3 py-1 text-sm font-medium rounded ${
                    deleteConfirm === apiKey.provider
                      ? 'text-white bg-danger-600 hover:bg-danger-700'
                      : 'text-danger-600 hover:text-danger-800 hover:bg-danger-50'
                  }`}
                >
                  {deleteConfirm === apiKey.provider ? 'Confirm Delete' : 'Delete'}
                </button>
                {deleteConfirm === apiKey.provider && (
                  <button
                    onClick={() => setDeleteConfirm(null)}
                    className="px-3 py-1 text-sm font-medium text-neutral-600 hover:text-neutral-800 hover:bg-neutral-50 dark:text-neutral-300 dark:hover:text-neutral-100 dark:hover:bg-neutral-800 rounded"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>

            {/* Available Models */}
            {providers[apiKey.provider] && (
              <div className="mt-3 pt-3 border-t border-neutral-100 dark:border-neutral-800">
                <div className="text-sm text-neutral-600 dark:text-neutral-400 mb-2">Available Models:</div>
                <div className="flex flex-wrap gap-1">
                  {providers[apiKey.provider].models.slice(0, 5).map((model) => (
                    <span
                      key={model}
                      className="inline-block px-2 py-1 text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 rounded"
                    >
                      {model}
                    </span>
                  ))}
                  {providers[apiKey.provider].models.length > 5 && (
                    <span className="inline-block px-2 py-1 text-xs bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 rounded">
                      +{providers[apiKey.provider].models.length - 5} more
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};