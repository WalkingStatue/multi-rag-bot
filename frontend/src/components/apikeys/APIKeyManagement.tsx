/**
 * Main API Key management component
 */
import React, { useState, useEffect } from 'react';
import { APIKeyForm } from './APIKeyForm';
import { APIKeyList } from './APIKeyList';
import { apiKeyService } from '../../services/apiKeyService';
import {
  APIKeyResponse,
  APIKeyCreate,
  APIKeyUpdate,
  ProviderInfo,
} from '../../types/api';

type ViewMode = 'list' | 'add' | 'edit';

export const APIKeyManagement: React.FC = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [apiKeys, setApiKeys] = useState<APIKeyResponse[]>([]);
  const [providers, setProviders] = useState<Record<string, ProviderInfo>>({});
  const [editingProvider, setEditingProvider] = useState<string | null>(null);
  const [loading, setLoading] = useState({
    list: true,
    providers: true,
    action: false,
  });
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading({ list: true, providers: true, action: false });
      setError(null);

      const [apiKeysData, llmProvidersData, embeddingProvidersData] = await Promise.all([
        apiKeyService.getAPIKeys(),
        apiKeyService.getSupportedProviders(),
        apiKeyService.getSupportedEmbeddingProviders(),
      ]);

      setApiKeys(apiKeysData);
      
      // Combine LLM and embedding providers
      const combinedProviders = {
        ...llmProvidersData.providers,
        ...embeddingProvidersData.providers
      };
      
      setProviders(combinedProviders);
    } catch (err) {
      setError('Failed to load API keys and providers');
      console.error('Error loading data:', err);
    } finally {
      setLoading({ list: false, providers: false, action: false });
    }
  };

  const handleAddAPIKey = async (data: APIKeyCreate) => {
    try {
      setLoading({ ...loading, action: true });
      setError(null);

      const newAPIKey = await apiKeyService.addAPIKey(data);
      
      // Update the list
      setApiKeys((prev) => {
        const filtered = prev.filter((key) => key.provider !== data.provider);
        return [...filtered, newAPIKey];
      });

      setSuccess(`API key for ${data.provider} added successfully`);
      setViewMode('list');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to add API key');
    } finally {
      setLoading({ ...loading, action: false });
    }
  };

  const handleUpdateAPIKey = async (data: APIKeyCreate) => {
    if (!editingProvider) return;

    try {
      setLoading({ ...loading, action: true });
      setError(null);

      const updateData: APIKeyUpdate = {
        api_key: data.api_key,
        is_active: true,
      };

      const updatedAPIKey = await apiKeyService.updateAPIKey(editingProvider, updateData);
      
      // Update the list
      setApiKeys((prev) =>
        prev.map((key) =>
          key.provider === editingProvider ? updatedAPIKey : key
        )
      );

      setSuccess(`API key for ${editingProvider} updated successfully`);
      setViewMode('list');
      setEditingProvider(null);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update API key');
    } finally {
      setLoading({ ...loading, action: false });
    }
  };

  const handleDeleteAPIKey = async (provider: string) => {
    try {
      setLoading({ ...loading, action: true });
      setError(null);

      await apiKeyService.deleteAPIKey(provider);
      
      // Update the list
      setApiKeys((prev) => prev.filter((key) => key.provider !== provider));

      setSuccess(`API key for ${provider} deleted successfully`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete API key');
    } finally {
      setLoading({ ...loading, action: false });
    }
  };

  const handleEditAPIKey = (provider: string) => {
    setEditingProvider(provider);
    setViewMode('edit');
  };

  const handleCancel = () => {
    setViewMode('list');
    setEditingProvider(null);
    setError(null);
    setSuccess(null);
  };

  const getAvailableProviders = () => {
    const existingProviders = new Set(apiKeys.map((key) => key.provider));
    return Object.fromEntries(
      Object.entries(providers).filter(([key]) => !existingProviders.has(key))
    );
  };

  // Clear messages after 5 seconds
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => setSuccess(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => setError(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [error]);

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">API Key Management</h1>
          <p className="text-neutral-600 dark:text-neutral-400 mt-1">
            Manage your API keys for different LLM providers
          </p>
        </div>

        {viewMode === 'list' && (
          <button
            onClick={() => setViewMode('add')}
            disabled={Object.keys(getAvailableProviders()).length === 0}
            className="px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Add API Key
          </button>
        )}
      </div>

      {/* Messages */}
      {error && (
        <div className="bg-danger-100 border border-danger-200 rounded-md p-4">
          <div className="flex">
            <div className="text-red-400">⚠️</div>
            <div className="ml-3">
              <p className="text-sm text-danger-700">{error}</p>
            </div>
          </div>
        </div>
      )}

      {success && (
        <div className="bg-success-100 border border-success-200 rounded-md p-4">
          <div className="flex">
            <div className="text-green-400">✅</div>
            <div className="ml-3">
              <p className="text-sm text-success-700">{success}</p>
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      {viewMode === 'list' && (
        <APIKeyList
          apiKeys={apiKeys}
          providers={providers}
          onEdit={handleEditAPIKey}
          onDelete={handleDeleteAPIKey}
          isLoading={loading.list}
        />
      )}

      {viewMode === 'add' && (
        <APIKeyForm
          onSubmit={handleAddAPIKey}
          onCancel={handleCancel}
          providers={getAvailableProviders()}
          isLoading={loading.action}
        />
      )}

      {viewMode === 'edit' && editingProvider && (
        <APIKeyForm
          onSubmit={handleUpdateAPIKey}
          onCancel={handleCancel}
          providers={providers}
          initialProvider={editingProvider}
          isLoading={loading.action}
        />
      )}

      {/* Loading overlay */}
      {loading.action && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white dark:bg-neutral-900 rounded-lg p-6 flex items-center space-x-3">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600"></div>
            <span className="text-neutral-900 dark:text-neutral-100">Processing...</span>
          </div>
        </div>
      )}
    </div>
  );
};