/**
 * Main bot management component with backend integration
 */
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { BotList } from './BotList';
import { BotForm } from './BotForm';
import { BotTransferModal } from './BotTransferModal';
import { BotWithRole, BotFormData, BotListFilters, BotTransferRequest } from '../../types/bot';
import { botService } from '../../services/botService';
import { log } from '../../utils/logger';

type ViewMode = 'list' | 'create' | 'edit';

interface Message {
  type: 'success' | 'error';
  text: string;
}

export const BotManagement: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [bots, setBots] = useState<BotWithRole[]>([]);
  const [editingBot, setEditingBot] = useState<BotWithRole | null>(null);
  const [transferBot, setTransferBot] = useState<BotWithRole | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [message, setMessage] = useState<Message | null>(null);
  const [filters, setFilters] = useState<BotListFilters>({});
  
  // Derive view mode from URL parameters
  const action = searchParams.get('action');
  const botId = searchParams.get('id');
  const viewMode: ViewMode = action === 'create' ? 'create' : action === 'edit' ? 'edit' : 'list';

  // Load bots on component mount
  useEffect(() => {
    loadBots();
  }, []);

  // Load specific bot for editing when URL changes
  useEffect(() => {
    if (viewMode === 'edit' && botId && bots.length > 0) {
      const botToEdit = bots.find(b => b.bot.id === botId);
      if (botToEdit) {
        setEditingBot(botToEdit);
      }
    } else if (viewMode !== 'edit') {
      setEditingBot(null);
    }
  }, [viewMode, botId, bots]);

  // Auto-hide messages after 5 seconds
  useEffect(() => {
    if (message) {
      const timer = setTimeout(() => {
        setMessage(null);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [message]);

  const loadBots = async () => {
    try {
      setIsLoading(true);
      const userBots = await botService.getUserBots();
      setBots(userBots);
    } catch (error: any) { log.error('Failed to load bots:', 'BotManagement', { error });
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to load bots',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateBot = () => {
    navigate('/bots?action=create');
  };

  const handleEditBot = (bot: BotWithRole) => {
    navigate(`/bots?action=edit&id=${bot.bot.id}`);
  };

  const handleDeleteBot = async (botId: string) => {
    try {
      await botService.deleteBot(botId);
      setMessage({
        type: 'success',
        text: 'Bot deleted successfully',
      });
      await loadBots(); // Reload the list
    } catch (error: any) { log.error('Failed to delete bot:', 'BotManagement', { error });
      setMessage({
        type: 'error',
        text: error.response?.data?.detail || 'Failed to delete bot',
      });
    }
  };

  const handleFormSubmit = async (data: BotFormData) => {
    try {
      if (viewMode === 'create') {
        await botService.createBot(data);
        setMessage({
          type: 'success',
          text: 'Bot created successfully',
        });
      } else if (viewMode === 'edit' && editingBot) {
        await botService.updateBot(editingBot.bot.id, data);
        setMessage({
          type: 'success',
          text: 'Bot updated successfully',
        });
      }

      navigate('/bots');
      setEditingBot(null);
      await loadBots(); // Reload the list
    } catch (error: any) { log.error('Failed to save bot:', 'BotManagement', { error });
      
      // Handle validation errors (422)
      let errorMessage = `Failed to ${viewMode === 'create' ? 'create' : 'update'} bot`;
      
      if (error.response?.status === 422 && error.response?.data?.detail) {
        const detail = error.response.data.detail;
        if (Array.isArray(detail)) {
          // Handle Pydantic validation errors
          const validationErrors = detail.map((err: any) => {
            if (typeof err === 'object' && err.msg) {
              return `${err.loc?.join(' → ') || 'Field'}: ${err.msg}`;
            }
            return String(err);
          });
          errorMessage = validationErrors.join('; ');
        } else if (typeof detail === 'string') {
          errorMessage = detail;
        }
      } else if (error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      setMessage({
        type: 'error',
        text: errorMessage,
      });
    }
  };

  const handleFormCancel = () => {
    navigate('/bots');
    setEditingBot(null);
  };

  const handleTransferOwnership = (bot: BotWithRole) => {
    setTransferBot(bot);
  };

  const handleTransferSubmit = async (botId: string, request: BotTransferRequest) => {
    try {
      await botService.transferOwnership(botId, request);
      setMessage({
        type: 'success',
        text: 'Bot ownership transferred successfully',
      });
      setTransferBot(null);
      await loadBots(); // Reload the list
    } catch (error: any) { log.error('Failed to transfer ownership:', 'BotManagement', { error });
      throw error; // Re-throw to let the modal handle the error display
    }
  };

  const handleTransferCancel = () => {
    setTransferBot(null);
  };

  const handleFiltersChange = (newFilters: BotListFilters) => {
    setFilters(newFilters);
  };

  const handleManageCollaboration = (bot: BotWithRole) => {
    navigate(`/bots/${bot.bot.id}/collaboration`);
  };

  const filteredBots = React.useMemo(() => {
    let filtered = [...bots];

    // Apply search filter
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      filtered = filtered.filter(
        (botWithRole) =>
          botWithRole.bot.name.toLowerCase().includes(searchLower) ||
          botWithRole.bot.description?.toLowerCase().includes(searchLower)
      );
    }

    // Apply role filter
    if (filters.role) {
      filtered = filtered.filter((botWithRole) => botWithRole.role === filters.role);
    }

    // Apply provider filter
    if (filters.provider) {
      filtered = filtered.filter((botWithRole) => botWithRole.bot.llm_provider === filters.provider);
    }

    // Apply public filter
    if (filters.is_public !== undefined) {
      filtered = filtered.filter((botWithRole) => botWithRole.bot.is_public === filters.is_public);
    }

    // Apply sorting
    const sortBy = filters.sort_by || 'updated_at';
    const sortOrder = filters.sort_order || 'desc';
    
    filtered.sort((a, b) => {
      let aValue: any;
      let bValue: any;

      switch (sortBy) {
        case 'name':
          aValue = a.bot.name.toLowerCase();
          bValue = b.bot.name.toLowerCase();
          break;
        case 'created_at':
          aValue = new Date(a.bot.created_at);
          bValue = new Date(b.bot.created_at);
          break;
        case 'updated_at':
          aValue = new Date(a.bot.updated_at);
          bValue = new Date(b.bot.updated_at);
          break;
        default:
          aValue = new Date(a.bot.updated_at);
          bValue = new Date(b.bot.updated_at);
      }

      if (aValue < bValue) return sortOrder === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortOrder === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [bots, filters]);

  return (
    <div className="space-y-6">

      {/* Message Display */}
      {message && (
        <div
          className={`mb-6 p-4 rounded-md ${
            message.type === 'success'
              ? 'bg-green-50 border border-green-200 text-green-800'
              : 'bg-red-50 border border-red-200 text-red-800'
          }`}
        >
          <div className="flex">
            <div className="flex-shrink-0">
              {message.type === 'success' ? (
                <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              ) : (
                <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>
            <div className="ml-3">
              <p className="text-sm font-medium">{message.text}</p>
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      {viewMode === 'list' ? (
        <BotList
          bots={filteredBots}
          isLoading={isLoading}
          filters={filters}
          onFiltersChange={handleFiltersChange}
          onCreateBot={handleCreateBot}
          onEditBot={handleEditBot}
          onDeleteBot={handleDeleteBot}
          onTransferOwnership={handleTransferOwnership}
          onManageCollaboration={handleManageCollaboration}
          onIntegrations={(bot) => navigate(`/bots/${bot.bot.id}/integrations`)}
        />
      ) : (
        <BotForm
          mode={viewMode}
          initialData={editingBot?.bot}
          onSubmit={handleFormSubmit}
          onCancel={handleFormCancel}
        />
      )}

      {/* Transfer Ownership Modal */}
      {transferBot && (
        <BotTransferModal
          bot={transferBot}
          isOpen={!!transferBot}
          onClose={handleTransferCancel}
          onTransfer={handleTransferSubmit}
        />
      )}
    </div>
  );
};