/**
 * API response types and interfaces
 */

export interface APIResponse<T = any> {
  data?: T;
  message?: string;
  error?: string;
}

export interface APIKeyResponse {
  id: string;
  provider: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface APIKeyCreate {
  provider: string;
  api_key: string;
}

export interface APIKeyUpdate {
  api_key: string;
  is_active?: boolean;
}

export interface APIKeyValidationResponse {
  valid: boolean;
  provider: string;
  message: string;
}

export interface ProviderInfo {
  name: string;
  models: string[];
}

export interface ProvidersResponse {
  providers: Record<string, ProviderInfo>;
  total: number;
}

export interface UserResponse {
  id: string;
  username: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AuthToken {
  access_token: string;
  refresh_token: string;
  token_type: string;
}