/**
 * Bot management service for API interactions
 */
import { enhancedApiClient } from './enhancedApi';
import {
  BotCreate,
  BotUpdate,
  BotResponse,
  BotWithRole,
  BotTransferRequest,
  BotAnalytics,
  BotDeleteConfirmation,
  BotProviderSettings,
  CollaboratorInvite,
  CollaboratorInviteResponse,
  BulkPermissionUpdate,
  PermissionHistory,
  ActivityLog,
  BotPermission,
} from '../types/bot';

export class BotService {
  /**
   * Create a new bot
   */
  async createBot(botData: BotCreate): Promise<BotResponse> {
    const response = await enhancedApiClient.post('/bots/', botData);
    return response.data;
  }

  /**
   * Get all bots accessible to the current user
   */
  async getUserBots(): Promise<BotWithRole[]> {
    const response = await enhancedApiClient.get('/bots/');
    return response.data;
  }

  /**
   * Get a specific bot by ID
   */
  async getBot(botId: string): Promise<BotResponse> {
    const response = await enhancedApiClient.get(`/bots/${botId}`);
    return response.data;
  }

  /**
   * Update a bot's configuration
   */
  async updateBot(botId: string, updates: BotUpdate): Promise<BotResponse> {
    const response = await enhancedApiClient.put(`/bots/${botId}`, updates);
    return response.data;
  }

  /**
   * Delete a bot (owner only)
   */
  async deleteBot(botId: string): Promise<void> {
    await enhancedApiClient.delete(`/bots/${botId}`);
  }

  /**
   * Transfer bot ownership to another user
   */
  async transferOwnership(botId: string, request: BotTransferRequest): Promise<void> {
    await enhancedApiClient.post(`/bots/${botId}/transfer`, request);
  }

  /**
   * Get bot analytics and usage statistics
   */
  async getBotAnalytics(botId: string): Promise<BotAnalytics> {
    const response = await enhancedApiClient.get(`/bots/${botId}/analytics`);
    return response.data;
  }

  /**
   * Get bot deletion confirmation info (cascade details)
   */
  async getBotDeleteInfo(botId: string): Promise<BotDeleteConfirmation> {
    // This would typically be a separate endpoint, but for now we'll simulate it
    // by getting the bot and analytics data
    const [bot, analytics] = await Promise.all([
      this.getBot(botId),
      this.getBotAnalytics(botId),
    ]);

    return {
      bot_id: botId,
      bot_name: bot.name,
      cascade_info: {
        conversations: analytics.total_conversations,
        messages: analytics.total_messages,
        documents: analytics.total_documents,
        collaborators: analytics.total_collaborators,
      },
    };
  }

  /**
   * Get available provider configurations with dynamic model fetching
   */
  async getProviderSettings(): Promise<BotProviderSettings> {
    const { apiKeyService } = await import('./apiKeyService');
    
    // Get static provider info first
    const staticProviders = await apiKeyService.getSupportedProviders();
    
    // Build provider settings with dynamic model fetching
    const llmProviders: Record<string, any> = {};
    const embeddingProviders: Record<string, any> = {};
    
    for (const [providerKey, providerInfo] of Object.entries(staticProviders.providers)) {
      // Try to get dynamic models, fall back to static if needed
      let models = providerInfo.models;
      let modelsSource = 'static';
      
      try {
        const dynamicModels = await apiKeyService.getProviderModels(providerKey);
        models = dynamicModels.models;
        modelsSource = dynamicModels.source;
      } catch (error: any) {
        // Use static models if dynamic fetch fails
      }
      
      // Convert model strings to model objects
      const modelObjects = models.map(modelId => ({
        id: modelId,
        name: this.formatModelName(modelId),
        max_tokens: this.getModelMaxTokens(modelId)
      }));
      
      // Configure LLM providers
      llmProviders[providerKey] = {
        name: providerKey,
        display_name: this.getProviderDisplayName(providerKey),
        models: modelObjects,
        default_model: models[0] || 'gpt-3.5-turbo',
        supports_embeddings: this.providerSupportsEmbeddings(providerKey),
        models_source: modelsSource
      };
      
      // Configure embedding providers if supported
      if (this.providerSupportsEmbeddings(providerKey)) {
        const embeddingModels = this.getEmbeddingModels(providerKey);
        embeddingProviders[providerKey] = {
          name: providerKey,
          display_name: this.getProviderDisplayName(providerKey),
          models: embeddingModels,
          default_model: embeddingModels[0]?.id || 'text-embedding-3-small',
          supports_embeddings: true
        };
      }
    }
    
    // Add local embedding provider
    embeddingProviders.local = {
      name: 'local',
      display_name: 'Local Models',
      models: [
        { id: 'sentence-transformers/all-MiniLM-L6-v2', name: 'All-MiniLM-L6-v2' },
        { id: 'sentence-transformers/all-mpnet-base-v2', name: 'All-MPNet-Base-v2' },
      ],
      default_model: 'sentence-transformers/all-MiniLM-L6-v2',
      supports_embeddings: true
    };
    
    return {
      llm_providers: llmProviders,
      embedding_providers: embeddingProviders
    };
  }
  
  /**
   * Get dynamic models for a specific provider
   */
  async getProviderModels(provider: string): Promise<string[]> {
    const { apiKeyService } = await import('./apiKeyService');
    
    try {
      const result = await apiKeyService.getProviderModels(provider);
      return result.models;
    } catch (error) {
      // Fall back to static models
      const staticProviders = await apiKeyService.getSupportedProviders();
      return staticProviders.providers[provider]?.models || [];
    }
  }
  
  private formatModelName(modelId: string): string {
    // Convert model IDs to human-readable names
    const nameMap: Record<string, string> = {
      'gpt-4': 'GPT-4',
      'gpt-4-turbo': 'GPT-4 Turbo',
      'gpt-3.5-turbo': 'GPT-3.5 Turbo',
      'claude-3-opus-20240229': 'Claude 3 Opus',
      'claude-3-sonnet-20240229': 'Claude 3 Sonnet',
      'claude-3-haiku-20240307': 'Claude 3 Haiku',
      'gemini-pro': 'Gemini Pro',
      'gemini-1.5-pro': 'Gemini 1.5 Pro',
      'gemini-1.5-flash': 'Gemini 1.5 Flash'
    };
    
    return nameMap[modelId] || modelId.replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  }
  
  private getModelMaxTokens(modelId: string): number {
    // Return max tokens based on model
    if (modelId.includes('gpt-4-turbo') || modelId.includes('gpt-4-0125')) return 128000;
    if (modelId.includes('gpt-4')) return 8192;
    if (modelId.includes('gpt-3.5-turbo-16k')) return 16384;
    if (modelId.includes('gpt-3.5')) return 4096;
    if (modelId.includes('claude')) return 4096;
    if (modelId.includes('gemini')) return 8192;
    return 4096; // Default
  }
  
  private getProviderDisplayName(provider: string): string {
    const displayNames: Record<string, string> = {
      openai: 'OpenAI',
      anthropic: 'Anthropic',
      gemini: 'Google Gemini',
      openrouter: 'OpenRouter'
    };
    return displayNames[provider] || provider;
  }
  
  private providerSupportsEmbeddings(provider: string): boolean {
    return ['openai', 'gemini'].includes(provider);
  }
  
  private getEmbeddingModels(provider: string) {
    const embeddingModels: Record<string, any[]> = {
      openai: [
        { id: 'text-embedding-3-small', name: 'Text Embedding 3 Small' },
        { id: 'text-embedding-3-large', name: 'Text Embedding 3 Large' },
        { id: 'text-embedding-ada-002', name: 'Text Embedding Ada 002' }
      ],
      gemini: [
        { id: 'embedding-001', name: 'Embedding 001' }
      ]
    };
    return embeddingModels[provider] || [];
  }

  // Collaboration methods
  /**
   * Get bot permissions/collaborators
   */
  async getBotPermissions(botId: string): Promise<BotPermission[]> {
    const response = await enhancedApiClient.get(`/bots/${botId}/permissions`);
    return response.data;
  }

  /**
   * Invite a collaborator to a bot
   */
  async inviteCollaborator(
    botId: string,
    invite: CollaboratorInvite
  ): Promise<CollaboratorInviteResponse> {
    const response = await enhancedApiClient.post(`/bots/${botId}/permissions/invite`, invite);
    return response.data;
  }

  /**
   * Update a collaborator's role
   */
  async updateCollaboratorRole(
    botId: string,
    userId: string,
    role: 'admin' | 'editor' | 'viewer'
  ): Promise<BotPermission> {
    const response = await enhancedApiClient.put(`/bots/${botId}/permissions/${userId}`, { role });
    return response.data;
  }

  /**
   * Remove a collaborator from a bot
   */
  async removeCollaborator(botId: string, userId: string): Promise<void> {
    await enhancedApiClient.delete(`/bots/${botId}/permissions/${userId}`);
  }

  /**
   * Bulk update permissions
   */
  async bulkUpdatePermissions(
    botId: string,
    updates: BulkPermissionUpdate
  ): Promise<BotPermission[]> {
    const response = await enhancedApiClient.post(`/bots/${botId}/permissions/bulk`, updates);
    return response.data;
  }

  /**
   * Get permission history for a bot
   */
  async getPermissionHistory(botId: string): Promise<PermissionHistory[]> {
    const response = await enhancedApiClient.get(`/bots/${botId}/permissions/history`);
    return response.data;
  }

  /**
   * Get activity log for a bot
   */
  async getActivityLog(botId: string): Promise<ActivityLog[]> {
    const response = await enhancedApiClient.get(`/bots/${botId}/activity`);
    return response.data;
  }

  // Utility methods
  /**
   * Search for users to invite as collaborators
   */
  async searchUsers(query: string): Promise<Array<{ id: string; username: string; email: string }>> {
    const response = await enhancedApiClient.get(`/users/search?q=${encodeURIComponent(query)}`);
    return response.data;
  }

  /**
   * Validate bot configuration before saving
   */
  validateBotConfig(config: BotCreate | BotUpdate): { valid: boolean; errors: string[] } {
    const errors: string[] = [];

    if ('name' in config && config.name) {
      if (config.name.length < 1 || config.name.length > 255) {
        errors.push('Bot name must be between 1 and 255 characters');
      }
    }

    if ('system_prompt' in config) {
      if (!config.system_prompt || config.system_prompt.trim().length < 1) {
        errors.push('System prompt is required');
      }
    }

    if ('temperature' in config && config.temperature !== undefined) {
      if (config.temperature < 0 || config.temperature > 2) {
        errors.push('Temperature must be between 0 and 2');
      }
    }

    if ('max_tokens' in config && config.max_tokens !== undefined) {
      if (config.max_tokens < 1 || config.max_tokens > 8000) {
        errors.push('Max tokens must be between 1 and 8000');
      }
    }

    if ('top_p' in config && config.top_p !== undefined) {
      if (config.top_p < 0 || config.top_p > 1) {
        errors.push('Top P must be between 0 and 1');
      }
    }

    if ('frequency_penalty' in config && config.frequency_penalty !== undefined) {
      if (config.frequency_penalty < -2 || config.frequency_penalty > 2) {
        errors.push('Frequency penalty must be between -2 and 2');
      }
    }

    if ('presence_penalty' in config && config.presence_penalty !== undefined) {
      if (config.presence_penalty < -2 || config.presence_penalty > 2) {
        errors.push('Presence penalty must be between -2 and 2');
      }
    }

    return {
      valid: errors.length === 0,
      errors,
    };
  }
}

// Export singleton instance
export const botService = new BotService();