/**
 * API Key management service
 */
import { enhancedApiClient } from './enhancedApi';
import {
  APIKeyResponse,
  APIKeyCreate,
  APIKeyUpdate,
  APIKeyValidationResponse,
  ProvidersResponse,
} from '../types/api';

export class APIKeyService {
  /**
   * Get all API keys for the current user
   */
  async getAPIKeys(): Promise<APIKeyResponse[]> {
    const response = await enhancedApiClient.get<APIKeyResponse[]>('/users/api-keys');
    return response.data;
  }

  /**
   * Add or update an API key for a provider
   */
  async addAPIKey(apiKeyData: APIKeyCreate): Promise<APIKeyResponse> {
    const response = await enhancedApiClient.post<APIKeyResponse>('/users/api-keys', apiKeyData);
    return response.data;
  }

  /**
   * Update an existing API key for a provider
   */
  async updateAPIKey(provider: string, apiKeyData: APIKeyUpdate): Promise<APIKeyResponse> {
    const response = await enhancedApiClient.put<APIKeyResponse>(
      `/users/api-keys/${provider}`,
      apiKeyData
    );
    return response.data;
  }

  /**
   * Delete an API key for a provider
   */
  async deleteAPIKey(provider: string): Promise<void> {
    await enhancedApiClient.delete(`/users/api-keys/${provider}`);
  }

  /**
   * Validate an API key for a provider
   */
  async validateAPIKey(provider: string, apiKey: string): Promise<APIKeyValidationResponse> {
    const response = await enhancedApiClient.post<APIKeyValidationResponse>(
      `/users/api-keys/${provider}/validate`,
      { provider, api_key: apiKey }
    );
    return response.data;
  }

  /**
   * Get supported providers and their available models (static)
   */
  async getSupportedProviders(): Promise<ProvidersResponse> {
    const response = await enhancedApiClient.get<ProvidersResponse>('/users/api-keys/providers');
    return response.data;
  }

  /**
   * Get available models for a specific provider using user's API key
   */
  async getProviderModels(provider: string): Promise<{
    provider: string;
    models: string[];
    total: number;
    source: 'api' | 'static';
  }> {
    const response = await enhancedApiClient.get(`/users/api-keys/providers/${provider}/models`);
    return response.data;
  }

  /**
   * Get supported embedding providers and their available models (static)
   */
  async getSupportedEmbeddingProviders(): Promise<{
    providers: Record<string, { name: string; models: string[]; requires_api_key: boolean }>;
    total: number;
  }> {
    const response = await enhancedApiClient.get('/users/embedding-providers');
    return response.data;
  }

  /**
   * Get available embedding models for a specific provider using user's API key
   */
  async getEmbeddingProviderModels(provider: string): Promise<{
    provider: string;
    models: string[];
    total: number;
    source: 'api' | 'static';
  }> {
    const response = await enhancedApiClient.get(`/users/embedding-providers/${provider}/models`);
    return response.data;
  }

  /**
   * Validate an API key for an embedding provider
   */
  async validateEmbeddingAPIKey(provider: string, apiKey: string): Promise<{
    valid: boolean;
    provider: string;
    message: string;
  }> {
    const response = await enhancedApiClient.post(`/users/embedding-providers/${provider}/validate`, {
      provider,
      api_key: apiKey
    });
    return response.data;
  }
}

export const apiKeyService = new APIKeyService();