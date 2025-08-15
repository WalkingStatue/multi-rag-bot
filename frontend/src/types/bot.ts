/**
 * Bot-related TypeScript types for frontend
 */

export interface BotBase {
  name: string;
  description?: string;
  system_prompt: string;
}

export interface BotCreate extends BotBase {
  llm_provider: 'openai' | 'anthropic' | 'openrouter' | 'gemini';
  llm_model: string;
  embedding_provider?: 'openai' | 'gemini' | 'anthropic';
  embedding_model?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  is_public?: boolean;
  allow_collaboration?: boolean;
}

export interface BotUpdate {
  name?: string;
  description?: string;
  system_prompt?: string;
  llm_provider?: 'openai' | 'anthropic' | 'openrouter' | 'gemini';
  llm_model?: string;
  embedding_provider?: 'openai' | 'gemini' | 'anthropic';
  embedding_model?: string;
  temperature?: number;
  max_tokens?: number;
  top_p?: number;
  frequency_penalty?: number;
  presence_penalty?: number;
  is_public?: boolean;
  allow_collaboration?: boolean;
}

export interface BotResponse extends BotBase {
  id: string;
  owner_id: string;
  llm_provider: string;
  llm_model: string;
  embedding_provider?: string;
  embedding_model?: string;
  temperature: number;
  max_tokens: number;
  top_p: number;
  frequency_penalty: number;
  presence_penalty: number;
  is_public: boolean;
  allow_collaboration: boolean;
  created_at: string;
  updated_at: string;
}

export interface BotWithRole {
  bot: BotResponse;
  role: 'owner' | 'admin' | 'editor' | 'viewer';
  granted_at?: string;
}

export interface BotTransferRequest {
  new_owner_id: string;
}

export interface BotAnalytics {
  total_conversations: number;
  total_messages: number;
  total_documents: number;
  total_collaborators: number;
  last_activity: string;
  usage_by_day: Array<{
    date: string;
    conversations: number;
    messages: number;
  }>;
  top_collaborators: Array<{
    user_id: string;
    username: string;
    message_count: number;
  }>;
}

// Permission-related types
export interface BotPermission {
  id: string;
  bot_id: string;
  user_id: string;
  username?: string;
  email?: string;
  role: 'owner' | 'admin' | 'editor' | 'viewer';
  granted_by?: string;
  granted_at: string;
}

export interface CollaboratorInvite {
  identifier: string; // email or username
  role: 'admin' | 'editor' | 'viewer';
  message?: string;
}

export interface CollaboratorInviteResponse {
  success: boolean;
  message: string;
  user_id?: string;
  permission?: BotPermission;
}

export interface BulkPermissionUpdate {
  user_permissions: Array<{
    user_id: string;
    role: 'admin' | 'editor' | 'viewer';
  }>;
}

export interface BulkUpdateResponse {
  successful: BotPermission[];
  failed: Array<{
    user_id: string;
    error: string;
  }>;
}

export interface PermissionHistory {
  id: string;
  bot_id: string;
  user_id: string;
  username: string;
  action: 'granted' | 'updated' | 'revoked';
  old_role?: string;
  new_role?: string;
  granted_by?: string;
  granted_by_username?: string;
  created_at: string;
}

export interface ActivityLog {
  id: string;
  bot_id: string;
  user_id?: string;
  username?: string;
  action: string;
  details?: Record<string, any>;
  created_at: string;
}

// UI-specific types
export interface BotFormData extends BotCreate {}

export interface BotListFilters {
  search?: string;
  role?: 'owner' | 'admin' | 'editor' | 'viewer';
  provider?: 'openai' | 'anthropic' | 'openrouter' | 'gemini';
  is_public?: boolean;
  sort_by?: 'name' | 'created_at' | 'updated_at' | 'last_activity';
  sort_order?: 'asc' | 'desc';
}

export interface BotDeleteConfirmation {
  bot_id: string;
  bot_name: string;
  cascade_info: {
    conversations: number;
    messages: number;
    documents: number;
    collaborators: number;
  };
}

// Provider configuration types
export interface ProviderModel {
  id: string;
  name: string;
  description?: string;
  max_tokens?: number;
  supports_functions?: boolean;
}

export interface ProviderConfig {
  name: string;
  display_name: string;
  models: ProviderModel[];
  default_model: string;
  supports_embeddings: boolean;
  embedding_models?: ProviderModel[];
  default_embedding_model?: string;
}

export interface BotProviderSettings {
  llm_providers: Record<string, ProviderConfig>;
  embedding_providers: Record<string, ProviderConfig>;
}