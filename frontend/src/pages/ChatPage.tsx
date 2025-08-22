/**
 * Chat page component
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChatWindow } from '../components/chat/ChatWindow';
import { ChatSearch } from '../components/chat/ChatSearch';
import { useChatStore } from '../stores/chatStore';
import { botService } from '../services/botService';
import { Button, PageLoading, PageError } from '../components/common';
import { ChatLayout } from '../layouts';
import { BotResponse } from '../types/bot';
import { ConversationSearchResult } from '../types/chat';
import { DocumentTextIcon, UserGroupIcon } from '@heroicons/react/24/outline';
import { log } from '../utils/logger';

export const ChatPage: React.FC = () => {
  const { botId } = useParams<{ botId: string }>();
  const navigate = useNavigate();
  const [bot, setBot] = useState<BotResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { setCurrentSession, setCurrentBot, setHighlightedMessage, clearHighlightedMessage } = useChatStore();

  useEffect(() => {
    const loadBot = async () => {
      if (!botId) {
        setError('Bot ID is required');
        setIsLoading(false);
        return;
      }

      try {
        const botData = await botService.getBot(botId);
        setBot(botData);
        setCurrentBot(botId);
      } catch (err) { log.error('Failed to load bot:', 'ChatPage', { err });
        setError('Failed to load bot. Please check if you have access to this bot.');
      } finally {
        setIsLoading(false);
      }
    };

    loadBot();
  }, [botId, setCurrentBot]);

  // Add body class to prevent page scrolling when chat is active
  useEffect(() => {
    document.body.classList.add('chat-active');
    return () => {
      document.body.classList.remove('chat-active');
    };
  }, []);

  const handleSearchResultSelect = (result: ConversationSearchResult) => {
    // Navigate to the session
    setCurrentSession(result.session_id);
    
    // Highlight and scroll to the specific message
    setHighlightedMessage(result.message_id);
    
    // Clear highlight after a delay
    setTimeout(() => {
      clearHighlightedMessage();
    }, 5000);
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
        <PageLoading message="Loading chat..." />
      </div>
    );
  }

  if (error || !bot) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950">
        <PageError
          title="Unable to Load Chat"
          message={error || 'Bot not found'}
          actionLabel="Back to Dashboard"
          onAction={() => navigate('/dashboard')}
        />
      </div>
    );
  }

  // Quick Actions for the right side of the header
  const quickActions = (
    <div className="flex items-center space-x-2">
      <Button
        variant="outline"
        size="sm"
        onClick={() => navigate(`/bots/${bot.id}/documents`)}
        className="border-accent-300 text-accent-700 hover:bg-accent-50 dark:bg-neutral-900 dark:border-accent-800 dark:text-accent-300"
      >
        <DocumentTextIcon className="-ml-0.5 mr-2 h-4 w-4" />
        Documents
      </Button>
      
      {bot.allow_collaboration && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate(`/bots/${bot.id}/collaboration`)}
          className="border-primary-300 text-primary-700 hover:bg-primary-50 dark:bg-neutral-900 dark:border-primary-800 dark:text-primary-300"
        >
          <UserGroupIcon className="-ml-0.5 mr-2 h-4 w-4" />
          Collaboration
        </Button>
      )}
    </div>
  );

  // Search component for the right side of the header
  const searchComponent = (
    <div className="w-96">
      <ChatSearch 
        botId={bot.id} 
        onResultSelect={handleSearchResultSelect}
      />
    </div>
  );

  // Combine quick actions and search
  const rightContent = (
    <div className="flex items-center space-x-4">
      {quickActions}
      {searchComponent}
    </div>
  );

  return (
    <ChatLayout
      title={bot.name}
      subtitle={bot.description || "Chat with your AI assistant"}
      rightContent={rightContent}
    >
      <ChatWindow bot={bot} className="h-full" />
    </ChatLayout>
  );
};

export default ChatPage;