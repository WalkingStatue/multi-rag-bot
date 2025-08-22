/**
 * Bot creation and editing form component with backend integration
 */
import React, { useState, useEffect } from 'react';
import { BotFormData, BotResponse, BotProviderSettings } from '../../types/bot';
import { botService } from '../../services/botService';
import { log } from '../../utils/logger';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { InlineError } from '../common/ErrorDisplay';

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
        log.error('Failed to load provider settings', 'BotForm', error);
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
    <div className="max-w-4xl mx-auto">
      <form onSubmit={handleSubmit} className="space-y-8">
        <div className="bg-white dark:bg-neutral-900 shadow-lg rounded-2xl border border-neutral-200 dark:border-neutral-800 overflow-hidden">
          <div className="p-8 space-y-8">
            {/* Basic Information */}
            <div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-6 pb-2 border-b border-neutral-200 dark:border-neutral-700">
                Basic Information
              </h3>
              
              <div className="grid grid-cols-1 gap-6">
                {/* Bot Name */}
                <div className="group">
                  <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                    Bot Name <span className="text-red-500">*</span>
                  </label>
                  <input
                    name="name"
                    type="text"
                    required
                    value={formData.name}
                    onChange={handleInputChange}
                    placeholder="Enter a descriptive name for your bot"
                    className="block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 sm:text-sm transition-all duration-200 bg-white text-neutral-900 placeholder-neutral-500 dark:bg-neutral-800 dark:text-neutral-100 dark:placeholder-neutral-400 border-neutral-300 dark:border-neutral-600 focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400 group-hover:border-primary-300 dark:group-hover:border-primary-700"
                  />
                  <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                    Choose a clear, descriptive name for your bot
                  </p>
                </div>

                {/* Description */}
                <div className="group">
                  <label htmlFor="description" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                    Description
                  </label>
                  <textarea
                    id="description"
                    name="description"
                    rows={3}
                    value={formData.description}
                    onChange={handleInputChange}
                    className="block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 sm:text-sm transition-all duration-200 bg-white text-neutral-900 placeholder-neutral-500 dark:bg-neutral-800 dark:text-neutral-100 dark:placeholder-neutral-400 border-neutral-300 dark:border-neutral-600 focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400 group-hover:border-primary-300 dark:group-hover:border-primary-700 resize-y"
                    placeholder="Describe what this bot does and how it should behave"
                  />
                  <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                    Help users understand the bot's purpose and capabilities
                  </p>
                </div>

                {/* Settings Row */}
                <div className="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg p-4 space-y-4">
                  <h4 className="text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-3">Access & Collaboration</h4>
                  
                  <div className="space-y-3">
                    {/* Public Toggle */}
                    <div className="flex items-start">
                      <input
                        id="is_public"
                        name="is_public"
                        type="checkbox"
                        checked={formData.is_public}
                        onChange={handleInputChange}
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-neutral-300 dark:border-neutral-600 rounded dark:bg-neutral-800 mt-0.5 transition-colors duration-200"
                      />
                      <div className="ml-3">
                        <label htmlFor="is_public" className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                          Public Bot
                        </label>
                        <p className="text-xs text-neutral-500 dark:text-neutral-400">
                          Allow anyone to discover and use this bot
                        </p>
                      </div>
                    </div>

                    {/* Collaboration Toggle */}
                    <div className="flex items-start">
                      <input
                        id="allow_collaboration"
                        name="allow_collaboration"
                        type="checkbox"
                        checked={formData.allow_collaboration}
                        onChange={handleInputChange}
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-neutral-300 dark:border-neutral-600 rounded dark:bg-neutral-800 mt-0.5 transition-colors duration-200"
                      />
                      <div className="ml-3">
                        <label htmlFor="allow_collaboration" className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                          Allow Collaboration
                        </label>
                        <p className="text-xs text-neutral-500 dark:text-neutral-400">
                          Let other users help improve this bot
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Validation Errors */}
            {validationErrors.length > 0 && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
                <div className="flex">
                  <div className="flex-shrink-0">
                    <svg className="h-5 w-5 text-red-400 dark:text-red-300" viewBox="0 0 20 20" fill="currentColor">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                    </svg>
                  </div>
                  <div className="ml-3">
                    <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Please fix the following errors:</h3>
                    <ul className="mt-2 text-sm text-red-700 dark:text-red-300 list-disc list-inside">
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
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-6 pb-2 border-b border-neutral-200 dark:border-neutral-700">
                Language Model Configuration
              </h3>
              <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-6">
                Configure the AI model that will power your bot's responses and reasoning.
              </p>
              
              {isLoadingProviders ? (
                <div className="animate-pulse space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="h-12 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
                    <div className="h-12 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="h-16 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
                    <div className="h-12 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
                  </div>
                </div>
              ) : (
                <div className="space-y-6">
                  {/* Provider and Model Row */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Provider */}
                    <div className="group">
                      <label htmlFor="llm_provider" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                        Provider <span className="text-red-500">*</span>
                      </label>
                      <select
                        id="llm_provider"
                        name="llm_provider"
                        value={formData.llm_provider}
                        onChange={handleProviderChange}
                        className="block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 sm:text-sm transition-all duration-200 bg-white text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100 border-neutral-300 dark:border-neutral-600 focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400 group-hover:border-primary-300 dark:group-hover:border-primary-700"
                      >
                        {providerSettings && Object.entries(providerSettings.llm_providers).map(([key, provider]) => (
                          <option key={key} value={key}>{provider.display_name}</option>
                        ))}
                      </select>
                      <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                        Choose your preferred AI provider
                      </p>
                    </div>

                    {/* Model */}
                    <div className="group">
                      <label htmlFor="llm_model" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                        Model <span className="text-red-500">*</span>
                      </label>
                      <select
                        id="llm_model"
                        name="llm_model"
                        value={formData.llm_model}
                        onChange={handleInputChange}
                        className="block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 sm:text-sm transition-all duration-200 bg-white text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100 border-neutral-300 dark:border-neutral-600 focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400 group-hover:border-primary-300 dark:group-hover:border-primary-700"
                      >
                        {getAvailableModels(formData.llm_provider, 'llm').map((model) => (
                          <option key={model.value} value={model.value}>
                            {model.label}
                          </option>
                        ))}
                      </select>
                      <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                        Select the specific model variant
                      </p>
                    </div>
                  </div>

                  {/* Advanced Parameters */}
                  <div className="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg p-6">
                    <h4 className="text-sm font-medium text-neutral-900 dark:text-neutral-100 mb-4 flex items-center">
                      <svg className="w-4 h-4 mr-2 text-neutral-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 100 4m0-4v2m0-6V4" />
                      </svg>
                      Advanced Parameters
                    </h4>
                    <p className="text-xs text-neutral-600 dark:text-neutral-400 mb-4">
                      Fine-tune the model's behavior and response characteristics
                    </p>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      {/* Temperature */}
                      <div className="group">
                        <label htmlFor="temperature" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                          Temperature: {formData.temperature}
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
                          className="block w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer dark:bg-neutral-700 range-slider transition-all duration-200 group-hover:bg-primary-100 dark:group-hover:bg-primary-900/20"
                        />
                        <div className="flex justify-between text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                          <span>Focused (0)</span>
                          <span>Balanced (1)</span>
                          <span>Creative (2)</span>
                        </div>
                        <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                          Controls randomness in responses
                        </p>
                      </div>

                      {/* Max Tokens */}
                      <div className="group">
                        <label htmlFor="max_tokens" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
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
                          className="block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 sm:text-sm transition-all duration-200 bg-white text-neutral-900 placeholder-neutral-500 dark:bg-neutral-800 dark:text-neutral-100 dark:placeholder-neutral-400 border-neutral-300 dark:border-neutral-600 focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400 group-hover:border-primary-300 dark:group-hover:border-primary-700"
                        />
                        <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                          Maximum response length
                        </p>
                      </div>

                      {/* Top P */}
                      <div className="group">
                        <label htmlFor="top_p" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                          Top P: {formData.top_p}
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
                          className="block w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer dark:bg-neutral-700 range-slider transition-all duration-200 group-hover:bg-primary-100 dark:group-hover:bg-primary-900/20"
                        />
                        <div className="flex justify-between text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                          <span>Restrictive (0)</span>
                          <span>Balanced (1)</span>
                        </div>
                        <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                          Controls vocabulary diversity
                        </p>
                      </div>

                      {/* Frequency Penalty */}
                      <div className="group">
                        <label htmlFor="frequency_penalty" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                          Frequency Penalty: {formData.frequency_penalty}
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
                          className="block w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer dark:bg-neutral-700 range-slider transition-all duration-200 group-hover:bg-primary-100 dark:group-hover:bg-primary-900/20"
                        />
                        <div className="flex justify-between text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                          <span>Encourage (-2)</span>
                          <span>Neutral (0)</span>
                          <span>Discourage (2)</span>
                        </div>
                        <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                          Reduces word repetition
                        </p>
                      </div>

                      {/* Presence Penalty */}
                      <div className="group">
                        <label htmlFor="presence_penalty" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                          Presence Penalty: {formData.presence_penalty}
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
                          className="block w-full h-2 bg-neutral-200 rounded-lg appearance-none cursor-pointer dark:bg-neutral-700 range-slider transition-all duration-200 group-hover:bg-primary-100 dark:group-hover:bg-primary-900/20"
                        />
                        <div className="flex justify-between text-xs text-neutral-500 dark:text-neutral-400 mt-1">
                          <span>Encourage (-2)</span>
                          <span>Neutral (0)</span>
                          <span>Discourage (2)</span>
                        </div>
                        <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                          Encourages topic diversity
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Embedding Configuration */}
            <div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-6 pb-2 border-b border-neutral-200 dark:border-neutral-700">
                Document Embedding Configuration
              </h3>
              <p className="text-sm text-neutral-600 dark:text-neutral-400 mb-6">
                Configure how documents are processed and embedded for this bot's knowledge base.
              </p>
              
              {isLoadingProviders ? (
                <div className="animate-pulse space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="h-12 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
                    <div className="h-12 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  {/* Embedding Provider */}
                  <div className="group">
                    <label htmlFor="embedding_provider" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                      Embedding Provider
                    </label>
                    <select
                      id="embedding_provider"
                      name="embedding_provider"
                      value={formData.embedding_provider}
                      onChange={handleEmbeddingProviderChange}
                      className="block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 sm:text-sm transition-all duration-200 bg-white text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100 border-neutral-300 dark:border-neutral-600 focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400 group-hover:border-primary-300 dark:group-hover:border-primary-700"
                    >
                      {providerSettings && Object.entries(providerSettings.embedding_providers).map(([key, provider]) => (
                        <option key={key} value={key}>{provider.display_name}</option>
                      ))}
                    </select>
                    <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                      Provider for document processing
                    </p>
                  </div>

                  {/* Embedding Model */}
                  <div className="group">
                    <label htmlFor="embedding_model" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                      Embedding Model
                    </label>
                    <select
                      id="embedding_model"
                      name="embedding_model"
                      value={formData.embedding_model}
                      onChange={handleInputChange}
                      className="block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 sm:text-sm transition-all duration-200 bg-white text-neutral-900 dark:bg-neutral-800 dark:text-neutral-100 border-neutral-300 dark:border-neutral-600 focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400 group-hover:border-primary-300 dark:group-hover:border-primary-700"
                    >
                      {getAvailableModels(formData.embedding_provider || 'openai', 'embedding').map((model) => (
                        <option key={model.value} value={model.value}>
                          {model.label}
                        </option>
                      ))}
                    </select>
                    <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">
                      Model for text vectorization
                    </p>
                  </div>
                </div>
              )}
            </div>

            {/* System Prompt */}
            <div>
              <h3 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-6 pb-2 border-b border-neutral-200 dark:border-neutral-700">
                AI Instructions & Behavior
              </h3>
              
              <div className="group">
                <label htmlFor="system_prompt" className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                  System Prompt <span className="text-red-500">*</span>
                </label>
                <textarea
                  id="system_prompt"
                  name="system_prompt"
                  rows={6}
                  required
                  value={formData.system_prompt}
                  onChange={handleInputChange}
                  className="block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-0 sm:text-sm transition-all duration-200 bg-white text-neutral-900 placeholder-neutral-500 dark:bg-neutral-800 dark:text-neutral-100 dark:placeholder-neutral-400 border-neutral-300 dark:border-neutral-600 focus:ring-primary-500 focus:border-primary-500 dark:focus:ring-primary-400 dark:focus:border-primary-400 group-hover:border-primary-300 dark:group-hover:border-primary-700 resize-y"
                  placeholder="You are a helpful assistant that specializes in..."
                />
                <p className="mt-2 text-sm text-neutral-600 dark:text-neutral-400">
                  Define the bot's personality, expertise, and behavior patterns. This instruction will guide all of the bot's responses.
                </p>
                <div className="mt-2 text-xs text-neutral-500 dark:text-neutral-400">
                  💡 <strong>Pro tip:</strong> Be specific about the bot's role, tone, and any special knowledge or constraints.
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Form Actions */}
        <div className="bg-white dark:bg-neutral-900 rounded-2xl border border-neutral-200 dark:border-neutral-800 p-6">
          <div className="flex flex-col sm:flex-row gap-3 sm:justify-end">
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              className="sm:order-1"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={isSubmitting || !formData.name.trim() || !formData.system_prompt.trim()}
              isLoading={isSubmitting}
              className="sm:order-2"
            >
              {isSubmitting ? 'Saving...' : mode === 'create' ? 'Create Bot' : 'Update Bot'}
            </Button>
          </div>
          
          {/* Form Status */}
          <div className="mt-4 text-center">
            <p className="text-xs text-neutral-500 dark:text-neutral-400">
              {mode === 'create' ? 'Creating' : 'Updating'} your bot configuration
            </p>
            {(formData.name.trim() && formData.system_prompt.trim()) && (
              <div className="mt-2 flex items-center justify-center text-xs text-green-600 dark:text-green-400">
                <svg className="w-3 h-3 mr-1" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                Ready to submit
              </div>
            )}
          </div>
        </div>
      </form>
    </div>
  );
};