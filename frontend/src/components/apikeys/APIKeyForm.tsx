/**
 * API Key form component for adding/editing API keys
 */
import React, { useState } from 'react';
import { APIKeyCreate, ProviderInfo } from '../../types/api';

interface APIKeyFormProps {
  onSubmit: (data: APIKeyCreate) => Promise<void>;
  onCancel: () => void;
  providers: Record<string, ProviderInfo>;
  initialProvider?: string;
  isLoading?: boolean;
}

export const APIKeyForm: React.FC<APIKeyFormProps> = ({
  onSubmit,
  onCancel,
  providers,
  initialProvider,
  isLoading = false,
}) => {
  const [formData, setFormData] = useState<APIKeyCreate>({
    provider: initialProvider || '',
    api_key: '',
  });
  const [validationStatus, setValidationStatus] = useState<{
    isValidating: boolean;
    isValid: boolean | null;
    message: string;
  }>({
    isValidating: false,
    isValid: null,
    message: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.provider || !formData.api_key.trim()) {
      return;
    }
    await onSubmit(formData);
  };

  const handleProviderChange = (provider: string) => {
    setFormData({ ...formData, provider });
    setValidationStatus({ isValidating: false, isValid: null, message: '' });
  };

  const handleAPIKeyChange = (apiKey: string) => {
    setFormData({ ...formData, api_key: apiKey });
    setValidationStatus({ isValidating: false, isValid: null, message: '' });
  };

  const validateAPIKey = async () => {
    if (!formData.provider || !formData.api_key.trim()) {
      return;
    }

    setValidationStatus({ isValidating: true, isValid: null, message: '' });

    try {
      const { apiKeyService } = await import('../../services/apiKeyService');
      
      // Try LLM validation first
      let result;
      try {
        result = await apiKeyService.validateAPIKey(formData.provider, formData.api_key);
      } catch (llmError) {
        // If LLM validation fails, try embedding validation
        try {
          result = await apiKeyService.validateEmbeddingAPIKey(formData.provider, formData.api_key);
        } catch (embeddingError) {
          throw new Error('Failed to validate API key for both LLM and embedding services');
        }
      }
      
      setValidationStatus({
        isValidating: false,
        isValid: result.valid,
        message: result.message,
      });

      // If validation is successful, try to fetch dynamic models
      if (result.valid) {
        try {
          // Try to fetch both LLM and embedding models
          const [llmModels, embeddingModels] = await Promise.allSettled([
            apiKeyService.getProviderModels(formData.provider),
            apiKeyService.getEmbeddingProviderModels(formData.provider)
          ]);
          
          if (llmModels.status === 'fulfilled') {
            console.log(`Fetched ${llmModels.value.models.length} LLM models from ${formData.provider} API:`, llmModels.value.models);
          }
          
          if (embeddingModels.status === 'fulfilled') {
            console.log(`Fetched ${embeddingModels.value.models.length} embedding models from ${formData.provider} API:`, embeddingModels.value.models);
          }
        } catch (error) {
          console.warn('Failed to fetch dynamic models after validation:', error);
        }
      }
    } catch (error) {
      setValidationStatus({
        isValidating: false,
        isValid: false,
        message: 'Failed to validate API key',
      });
    }
  };

  const getProviderDisplayName = (provider: string) => {
    const names: Record<string, string> = {
      openai: 'OpenAI',
      anthropic: 'Anthropic',
      openrouter: 'OpenRouter',
      gemini: 'Google Gemini',
    };
    return names[provider] || provider;
  };

  const getAPIKeyPlaceholder = (provider: string) => {
    const placeholders: Record<string, string> = {
      openai: 'sk-...',
      anthropic: 'sk-ant-...',
      openrouter: 'sk-or-...',
      gemini: 'AIza...',
    };
    return placeholders[provider] || 'Enter your API key';
  };

  return (
    <div className="bg-white dark:bg-neutral-900 rounded-lg shadow-md p-6">
      <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 mb-4">
        {initialProvider ? 'Update API Key' : 'Add API Key'}
      </h3>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Provider Selection */}
        <div>
          <label htmlFor="provider" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
            Provider
          </label>
          <select
            id="provider"
            value={formData.provider}
            onChange={(e) => handleProviderChange(e.target.value)}
            disabled={!!initialProvider}
            className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-700 dark:bg-neutral-900 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 disabled:bg-neutral-100 dark:disabled:bg-neutral-800"
            required
          >
            <option value="">Select a provider</option>
            {Object.entries(providers).map(([key]) => (
              <option key={key} value={key}>
                {getProviderDisplayName(key)}
              </option>
            ))}
          </select>
        </div>

        {/* API Key Input */}
        <div>
          <label htmlFor="api_key" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
            API Key
          </label>
          <div className="relative">
            <input
              type="password"
              id="api_key"
              value={formData.api_key}
              onChange={(e) => handleAPIKeyChange(e.target.value)}
              placeholder={getAPIKeyPlaceholder(formData.provider)}
              className="w-full px-3 py-2 border border-neutral-300 dark:border-neutral-700 dark:bg-neutral-900 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              required
            />
            {formData.provider && formData.api_key && (
              <button
                type="button"
                onClick={validateAPIKey}
                disabled={validationStatus.isValidating}
                className="absolute right-2 top-1/2 transform -translate-y-1/2 px-3 py-1 text-xs bg-primary-600 text-white rounded hover:bg-primary-700 disabled:opacity-50"
              >
                {validationStatus.isValidating ? 'Validating...' : 'Validate'}
              </button>
            )}
          </div>

          {/* Validation Status */}
          {validationStatus.message && (
            <div
              className={`mt-2 text-sm ${
                validationStatus.isValid
                  ? 'text-success-600'
                  : validationStatus.isValid === false
                  ? 'text-danger-600'
                  : 'text-neutral-600 dark:text-neutral-400'
              }`}
            >
              {validationStatus.message}
            </div>
          )}
        </div>

        {/* Available Models */}
        {formData.provider && providers[formData.provider] && (
          <div>
            <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Available Models
            </label>
            <div className="bg-neutral-50 dark:bg-neutral-800 rounded-md p-3">
              <div className="flex flex-wrap gap-2">
                {providers[formData.provider].models.map((model) => (
                  <span
                    key={model}
                    className="inline-block px-2 py-1 text-xs bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-300 rounded"
                  >
                    {model}
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Form Actions */}
        <div className="flex justify-end space-x-3 pt-4">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-neutral-700 bg-white dark:bg-neutral-900 border border-neutral-300 dark:border-neutral-700 rounded-md hover:bg-neutral-50 dark:hover:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isLoading || !formData.provider || !formData.api_key.trim()}
            className="px-4 py-2 text-sm font-medium text-white bg-primary-600 border border-transparent rounded-md hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? 'Saving...' : initialProvider ? 'Update' : 'Add'} API Key
          </button>
        </div>
      </form>
    </div>
  );
};