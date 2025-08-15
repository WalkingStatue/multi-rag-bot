/**
 * Bot creation and editing form component with backend integration
 */
import React, { useState, useEffect } from 'react';
import { BotFormData, BotResponse, BotProviderSettings } from '../../types/bot';
import { botService } from '../../services/botService';

interface BotFormProps {
  mode: 'create' | 'edit';
  initialData?: BotResponse;
  onSubmit: (data: BotFormData) => Promise<void>;
  onCancel: () => void;
}

export const BotForm: React.FC<BotFormProps> = ({
  mode,
  initialData,
  onSubmit,
  onCancel,
}) => {
  const [formData, setFormData] = useState<BotFormData>({
    name: '',
    description: '',
    llm_provider: 'openai',
    llm_model: 'gpt-3.5-turbo',
    embedding_provider: 'openai',
    embedding_model: 'text-embedding-3-small',
    system_prompt: '',
    temperature: 0.7,
    max_tokens: 1000,
    top_p: 1.0,
    frequency_penalty: 0.0,
    presence_penalty: 0.0,
    is_public: false,
    allow_collaboration: true,
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [providerSettings, setProviderSettings] = useState<BotProviderSettings | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isLoadingProviders, setIsLoadingProviders] = useState(true);

  // Load provider settings on component mount
  useEffect(() => {
    const loadProviderSettings = async () => {
      try {
        setIsLoadingProviders(true);
        const settings = await botService.getProviderSettings();
        setProviderSettings(settings);
      } catch (error) {
        console.error('Failed to load provider settings:', error);
      } finally {
        setIsLoadingProviders(false);
      }
    };

    loadProviderSettings();
  }, []);

  // Initialize form data when editing
  useEffect(() => {
    if (mode === 'edit' && initialData) {
      setFormData({
        name: initialData.name,
        description: initialData.description || '',
        llm_provider: initialData.llm_provider as 'openai' | 'anthropic' | 'openrouter' | 'gemini',
        llm_model: initialData.llm_model,
        embedding_provider: (initialData.embedding_provider as 'openai' | 'gemini' | 'anthropic') || 'openai',
        embedding_model: initialData.embedding_model || 'text-embedding-3-small',
        system_prompt: initialData.system_prompt || '',
        temperature: initialData.temperature || 0.7,
        max_tokens: initialData.max_tokens || 1000,
        top_p: initialData.top_p || 1.0,
        frequency_penalty: initialData.frequency_penalty || 0.0,
        presence_penalty: initialData.presence_penalty || 0.0,
        is_public: initialData.is_public,
        allow_collaboration: initialData.allow_collaboration,
      });
    }
  }, [mode, initialData]);

  // Validate form data in real-time
  useEffect(() => {
    const validation = botService.validateBotConfig(formData);
    setValidationErrors(validation.errors);
  }, [formData]);

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>
  ) => {
    const { name, value, type } = e.target;
    
    if (type === 'checkbox') {
      const checked = (e.target as HTMLInputElement).checked;
      setFormData(prev => ({ ...prev, [name]: checked }));
    } else if (type === 'number') {
      setFormData(prev => ({ ...prev, [name]: parseFloat(value) || 0 }));
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
  };

  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const provider = e.target.value as 'openai' | 'anthropic' | 'gemini' | 'openrouter';
    
    if (!providerSettings) return;
    
    const providerConfig = providerSettings.llm_providers[provider];
    const defaultModel = providerConfig?.default_model || 'gpt-3.5-turbo';

    setFormData(prev => ({
      ...prev,
      llm_provider: provider,
      llm_model: defaultModel,
    }));
  };

  const handleEmbeddingProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const provider = e.target.value as 'openai' | 'gemini' | 'anthropic';
    
    if (!providerSettings) return;
    
    const providerConfig = providerSettings.embedding_providers[provider];
    const defaultModel = providerConfig?.default_model || 'text-embedding-3-small';

    setFormData(prev => ({
      ...prev,
      embedding_provider: provider,
      embedding_model: defaultModel,
    }));
  };

  const getAvailableModels = (provider: string, type: 'llm' | 'embedding' = 'llm') => {
    if (!providerSettings) return [];
    
    const providers = type === 'llm' ? providerSettings.llm_providers : providerSettings.embedding_providers;
    const providerConfig = providers[provider];
    
    return providerConfig?.models?.map(model => ({
      value: model.id,
      label: model.name,
    })) || [];
  };



  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!formData.name.trim() || !formData.system_prompt.trim()) {
      return;
    }

    setIsSubmitting(true);
    try {
      await onSubmit(formData);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-white shadow rounded-lg p-6">
          {/* Basic Information */}
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Basic Information</h3>
              
              <div className="grid grid-cols-1 gap-6">
                {/* Bot Name */}
                <div>
                  <label htmlFor="name" className="block text-sm font-medium text-gray-700">
                    Bot Name *
                  </label>
                  <input
                    type="text"
                    id="name"
                    name="name"
                    required
                    value={formData.name}
                    onChange={handleInputChange}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Enter bot name"
                  />
                </div>

                {/* Description */}
                <div>
                  <label htmlFor="description" className="block text-sm font-medium text-gray-700">
                    Description
                  </label>
                  <textarea
                    id="description"
                    name="description"
                    rows={3}
                    value={formData.description}
                    onChange={handleInputChange}
                    className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Describe what this bot does"
                  />
                </div>

                {/* Public Toggle */}
                <div className="flex items-center">
                  <input
                    id="is_public"
                    name="is_public"
                    type="checkbox"
                    checked={formData.is_public}
                    onChange={handleInputChange}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="is_public" className="ml-2 block text-sm text-gray-900">
                    Make this bot publicly accessible
                  </label>
                </div>
              </div>
            </div>

            {/* Validation Errors */}
            {validationErrors.length > 0 && (
              <div className="bg-red-50 border border-red-200 rounded-md p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800">Please fix the following errors:</h3>
                    <ul className="mt-2 text-sm text-red-700 list-disc list-inside">
                      {validationErrors.map((error, index) => (
                        <li key={index}>{typeof error === 'string' ? error : JSON.stringify(error)}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            )}

            {/* LLM Configuration */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">LLM Configuration</h3>
              
              {isLoadingProviders ? (
                <div className="animate-pulse space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="h-10 bg-gray-200 rounded"></div>
                    <div className="h-10 bg-gray-200 rounded"></div>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Provider */}
                  <div>
                    <label htmlFor="llm_provider" className="block text-sm font-medium text-gray-700">
                      Provider *
                    </label>
                    <select
                      id="llm_provider"
                      name="llm_provider"
                      value={formData.llm_provider}
                      onChange={handleProviderChange}
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      {providerSettings && Object.entries(providerSettings.llm_providers).map(([key, provider]) => (
                        <option key={key} value={key}>{provider.display_name}</option>
                      ))}
                    </select>
                  </div>

                  {/* Model */}
                  <div>
                    <label htmlFor="llm_model" className="block text-sm font-medium text-gray-700">
                      Model *
                    </label>
                    <select
                      id="llm_model"
                      name="llm_model"
                      value={formData.llm_model}
                      onChange={handleInputChange}
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      {getAvailableModels(formData.llm_provider, 'llm').map((model) => (
                        <option key={model.value} value={model.value}>
                          {model.label}
                        </option>
                      ))}
                    </select>
                  </div>

                  {/* Temperature */}
                  <div>
                    <label htmlFor="temperature" className="block text-sm font-medium text-gray-700">
                      Temperature ({formData.temperature})
                    </label>
                    <input
                      type="range"
                      id="temperature"
                      name="temperature"
                      min="0"
                      max="2"
                      step="0.1"
                      value={formData.temperature}
                      onChange={handleInputChange}
                      className="mt-1 block w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>Focused (0)</span>
                      <span>Balanced (1)</span>
                      <span>Creative (2)</span>
                    </div>
                  </div>

                  {/* Max Tokens */}
                  <div>
                    <label htmlFor="max_tokens" className="block text-sm font-medium text-gray-700">
                      Max Tokens
                    </label>
                    <input
                      type="number"
                      id="max_tokens"
                      name="max_tokens"
                      min="1"
                      max="8000"
                      value={formData.max_tokens}
                      onChange={handleInputChange}
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>

                  {/* Top P */}
                  <div>
                    <label htmlFor="top_p" className="block text-sm font-medium text-gray-700">
                      Top P ({formData.top_p})
                    </label>
                    <input
                      type="range"
                      id="top_p"
                      name="top_p"
                      min="0"
                      max="1"
                      step="0.1"
                      value={formData.top_p}
                      onChange={handleInputChange}
                      className="mt-1 block w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>Restrictive (0)</span>
                      <span>Balanced (1)</span>
                    </div>
                  </div>

                  {/* Frequency Penalty */}
                  <div>
                    <label htmlFor="frequency_penalty" className="block text-sm font-medium text-gray-700">
                      Frequency Penalty ({formData.frequency_penalty})
                    </label>
                    <input
                      type="range"
                      id="frequency_penalty"
                      name="frequency_penalty"
                      min="-2"
                      max="2"
                      step="0.1"
                      value={formData.frequency_penalty}
                      onChange={handleInputChange}
                      className="mt-1 block w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>Encourage (-2)</span>
                      <span>Neutral (0)</span>
                      <span>Discourage (2)</span>
                    </div>
                  </div>

                  {/* Presence Penalty */}
                  <div>
                    <label htmlFor="presence_penalty" className="block text-sm font-medium text-gray-700">
                      Presence Penalty ({formData.presence_penalty})
                    </label>
                    <input
                      type="range"
                      id="presence_penalty"
                      name="presence_penalty"
                      min="-2"
                      max="2"
                      step="0.1"
                      value={formData.presence_penalty}
                      onChange={handleInputChange}
                      className="mt-1 block w-full"
                    />
                    <div className="flex justify-between text-xs text-gray-500 mt-1">
                      <span>Encourage (-2)</span>
                      <span>Neutral (0)</span>
                      <span>Discourage (2)</span>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Embedding Configuration */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Embedding Configuration</h3>
              <p className="text-sm text-gray-600 mb-4">
                Configure how documents are processed and embedded for this bot's knowledge base.
              </p>
              
              {isLoadingProviders ? (
                <div className="animate-pulse space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="h-10 bg-gray-200 rounded"></div>
                    <div className="h-10 bg-gray-200 rounded"></div>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Embedding Provider */}
                  <div>
                    <label htmlFor="embedding_provider" className="block text-sm font-medium text-gray-700">
                      Embedding Provider
                    </label>
                    <select
                      id="embedding_provider"
                      name="embedding_provider"
                      value={formData.embedding_provider}
                      onChange={handleEmbeddingProviderChange}
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      {providerSettings && Object.entries(providerSettings.embedding_providers).map(([key, provider]) => (
                        <option key={key} value={key}>{provider.display_name}</option>
                      ))}
                    </select>
                  </div>

                  {/* Embedding Model */}
                  <div>
                    <label htmlFor="embedding_model" className="block text-sm font-medium text-gray-700">
                      Embedding Model
                    </label>
                    <select
                      id="embedding_model"
                      name="embedding_model"
                      value={formData.embedding_model}
                      onChange={handleInputChange}
                      className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      {getAvailableModels(formData.embedding_provider || 'openai', 'embedding').map((model) => (
                        <option key={model.value} value={model.value}>
                          {model.label}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}
            </div>

            {/* Collaboration Settings */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">Collaboration Settings</h3>
              
              <div className="space-y-4">
                {/* Allow Collaboration */}
                <div className="flex items-center">
                  <input
                    id="allow_collaboration"
                    name="allow_collaboration"
                    type="checkbox"
                    checked={formData.allow_collaboration}
                    onChange={handleInputChange}
                    className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                  />
                  <label htmlFor="allow_collaboration" className="ml-2 block text-sm text-gray-900">
                    Allow collaboration on this bot
                  </label>
                </div>
                <p className="text-sm text-gray-500 ml-6">
                  When enabled, you can invite other users to collaborate on this bot with different permission levels.
                </p>
              </div>
            </div>

            {/* System Prompt */}
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-4">System Prompt</h3>
              
              <div>
                <label htmlFor="system_prompt" className="block text-sm font-medium text-gray-700">
                  Instructions for the AI *
                </label>
                <textarea
                  id="system_prompt"
                  name="system_prompt"
                  rows={6}
                  required
                  value={formData.system_prompt}
                  onChange={handleInputChange}
                  className="mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  placeholder="You are a helpful assistant that..."
                />
                <p className="mt-2 text-sm text-gray-500">
                  Define the bot's personality, role, and behavior. This will be sent with every conversation.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Form Actions */}
        <div className="flex justify-end space-x-3">
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting || !formData.name.trim() || !formData.system_prompt.trim()}
            className="px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isSubmitting ? 'Saving...' : mode === 'create' ? 'Create Bot' : 'Update Bot'}
          </button>
        </div>
      </form>
    </div>
  );
};