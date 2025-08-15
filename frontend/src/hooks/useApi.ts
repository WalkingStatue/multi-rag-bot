/**
 * Custom hooks for API data fetching with React Query
 */
import { useQuery, useMutation, useQueryClient, UseQueryOptions, UseMutationOptions } from '@tanstack/react-query';
import { enhancedApiClient } from '../services/enhancedApi';
import { useToastHelpers } from '../components/common/Toast';
import { AppError } from '../utils/errorHandler';

// Query key factory for consistent cache keys
export const queryKeys = {
  // Auth
  currentUser: ['auth', 'currentUser'] as const,
  
  // Bots
  bots: ['bots'] as const,
  bot: (id: string) => ['bots', id] as const,
  botModels: ['bots', 'models'] as const,
  
  // Documents
  documents: (botId?: string) => ['documents', botId] as const,
  document: (id: string) => ['documents', id] as const,
  
  // Conversations
  conversations: (botId?: string) => ['conversations', botId] as const,
  conversation: (id: string) => ['conversations', id] as const,
  conversationMessages: (id: string) => ['conversations', id, 'messages'] as const,
  
  // API Keys
  apiKeys: ['apiKeys'] as const,
  
  // Analytics
  analytics: (botId?: string) => ['analytics', botId] as const,
};

// Generic API hook
export function useApiQuery<T = any>(
  queryKey: readonly unknown[],
  url: string,
  options?: Omit<UseQueryOptions<T>, 'queryKey' | 'queryFn'>
) {
  return useQuery({
    queryKey,
    queryFn: async () => {
      const response = await enhancedApiClient.get<T>(url, {
        context: `useApiQuery-${queryKey.join('-')}`
      });
      return response.data;
    },
    ...options,
  });
}

// Generic mutation hook
export function useApiMutation<TData = any, TVariables = any>(
  mutationFn: (variables: TVariables) => Promise<TData>,
  options?: UseMutationOptions<TData, Error, TVariables>
) {
  const { error: showError } = useToastHelpers();
  
  return useMutation({
    mutationFn,
    onSuccess: (data, variables, context) => {
      options?.onSuccess?.(data, variables, context);
    },
    onError: (error: any, variables, context) => {
      // Handle specific error types
      if (error?.chatError) {
        const chatError = error.chatError as AppError;
        if (chatError.type !== 'rate_limit') { // Rate limit errors are handled globally
          showError(`Error: ${chatError.message}`);
        }
      } else {
        showError('An unexpected error occurred');
      }
      options?.onError?.(error, variables, context);
    },
    ...options,
  });
}

// Auth hooks
export function useCurrentUser() {
  return useApiQuery(
    queryKeys.currentUser,
    '/users/profile',
    {
      staleTime: 10 * 60 * 1000, // 10 minutes
      retry: false, // Don't retry auth failures
    }
  );
}

// Bot hooks
export function useBots() {
  return useApiQuery(
    queryKeys.bots,
    '/bots',
    {
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
}

export function useBot(botId: string) {
  return useApiQuery(
    queryKeys.bot(botId),
    `/bots/${botId}`,
    {
      enabled: !!botId,
      staleTime: 5 * 60 * 1000,
    }
  );
}

export function useCreateBot() {
  const queryClient = useQueryClient();
  const { success } = useToastHelpers();
  
  return useApiMutation(
    async (botData: any) => {
      const response = await enhancedApiClient.post('/bots', botData, {
        context: 'createBot'
      });
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: queryKeys.bots });
        success('Bot created successfully');
      },
    }
  );
}

export function useUpdateBot(botId: string) {
  const queryClient = useQueryClient();
  const { success } = useToastHelpers();
  
  return useApiMutation(
    async (botData: any) => {
      const response = await enhancedApiClient.put(`/bots/${botId}`, botData, {
        context: 'updateBot'
      });
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: queryKeys.bot(botId) });
        queryClient.invalidateQueries({ queryKey: queryKeys.bots });
        success('Bot updated successfully');
      },
    }
  );
}

export function useDeleteBot() {
  const queryClient = useQueryClient();
  const { success } = useToastHelpers();
  
  return useApiMutation(
    async (botId: string) => {
      await enhancedApiClient.delete(`/bots/${botId}`, {
        context: 'deleteBot'
      });
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: queryKeys.bots });
        success('Bot deleted successfully');
      },
    }
  );
}

// Document hooks
export function useDocuments(botId?: string) {
  return useApiQuery(
    queryKeys.documents(botId),
    botId ? `/bots/${botId}/documents` : '/documents',
    {
      enabled: !!botId,
      staleTime: 2 * 60 * 1000, // 2 minutes
    }
  );
}

export function useUploadDocument(botId: string) {
  const queryClient = useQueryClient();
  const { success } = useToastHelpers();
  
  return useApiMutation(
    async ({ file, onProgress }: { file: File; onProgress?: (progress: number) => void }) => {
      const response = await enhancedApiClient.uploadFile(
        `/bots/${botId}/documents/upload`,
        file,
        onProgress,
        { context: 'uploadDocument' }
      );
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: queryKeys.documents(botId) });
        success('Document uploaded successfully');
      },
    }
  );
}

export function useDeleteDocument(botId: string) {
  const queryClient = useQueryClient();
  const { success } = useToastHelpers();
  
  return useApiMutation(
    async (documentId: string) => {
      await enhancedApiClient.delete(`/bots/${botId}/documents/${documentId}`, {
        context: 'deleteDocument'
      });
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: queryKeys.documents(botId) });
        success('Document deleted successfully');
      },
    }
  );
}

// Conversation hooks
export function useConversations(botId?: string) {
  return useApiQuery(
    queryKeys.conversations(botId),
    botId ? `/conversations/sessions?bot_id=${botId}` : '/conversations/sessions',
    {
      staleTime: 1 * 60 * 1000, // 1 minute
    }
  );
}

export function useConversationMessages(conversationId: string) {
  return useApiQuery(
    queryKeys.conversationMessages(conversationId),
    `/conversations/sessions/${conversationId}/messages`,
    {
      enabled: !!conversationId,
      staleTime: 30 * 1000, // 30 seconds
    }
  );
}

export function useSendMessage(botId: string) {
  const queryClient = useQueryClient();
  
  return useApiMutation(
    async (messageData: any) => {
      const response = await enhancedApiClient.post(`/conversations/bots/${botId}/chat`, messageData, {
        context: 'sendMessage'
      });
      return response.data;
    },
    {
      onSuccess: (data, variables) => {
        // Invalidate conversation messages if session_id is provided
        if (variables.session_id) {
          queryClient.invalidateQueries({ 
            queryKey: queryKeys.conversationMessages(variables.session_id) 
          });
        }
        // Invalidate conversations list
        queryClient.invalidateQueries({ queryKey: queryKeys.conversations(botId) });
      },
    }
  );
}

// API Key hooks
export function useApiKeys() {
  return useApiQuery(
    queryKeys.apiKeys,
    '/api-keys',
    {
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
}

export function useCreateApiKey() {
  const queryClient = useQueryClient();
  const { success } = useToastHelpers();
  
  return useApiMutation(
    async (apiKeyData: any) => {
      const response = await enhancedApiClient.post('/api-keys', apiKeyData, {
        context: 'createApiKey'
      });
      return response.data;
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys });
        success('API key added successfully');
      },
    }
  );
}

export function useDeleteApiKey() {
  const queryClient = useQueryClient();
  const { success } = useToastHelpers();
  
  return useApiMutation(
    async (apiKeyId: string) => {
      await enhancedApiClient.delete(`/api-keys/${apiKeyId}`, {
        context: 'deleteApiKey'
      });
    },
    {
      onSuccess: () => {
        queryClient.invalidateQueries({ queryKey: queryKeys.apiKeys });
        success('API key deleted successfully');
      },
    }
  );
}

// Analytics hooks
export function useAnalytics(botId?: string) {
  return useApiQuery(
    queryKeys.analytics(botId),
    botId ? `/analytics?bot_id=${botId}` : '/analytics',
    {
      staleTime: 5 * 60 * 1000, // 5 minutes
    }
  );
}

// Utility hooks
export function useInvalidateQueries() {
  const queryClient = useQueryClient();
  
  return {
    invalidateBots: () => queryClient.invalidateQueries({ queryKey: queryKeys.bots }),
    invalidateBot: (botId: string) => queryClient.invalidateQueries({ queryKey: queryKeys.bot(botId) }),
    invalidateDocuments: (botId?: string) => queryClient.invalidateQueries({ queryKey: queryKeys.documents(botId) }),
    invalidateConversations: (botId?: string) => queryClient.invalidateQueries({ queryKey: queryKeys.conversations(botId) }),
    invalidateAll: () => queryClient.invalidateQueries(),
  };
}