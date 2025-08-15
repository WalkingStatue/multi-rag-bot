/**
 * Chat page component
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChatWindow } from '../components/chat/ChatWindow';
import { ChatSearch } from '../components/chat/ChatSearch';
import { useChatStore } from '../stores/chatStore';
import { botService } from '../services/botService';
import { Button } from '../components/common';
import { ChatLayout } from '../layouts';
import { BotResponse } from '../types/bot';
import { ConversationSearchResult } from '../types/chat';

export const ChatPage: React.FC = () => {
  const { botId } = useParams<{ botId: string }>();
  const navigate = useNavigate();
  const [bot, setBot] = useState<BotResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { setCurrentSession, setCurrentBot } = useChatStore();

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
      } catch (err) {
        console.error('Failed to load bot:', err);
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
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading chat...</p>
        </div>
      </div>
    );
  }

  if (error || !bot) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
            <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Unable to Load Chat</h2>
          <p className="text-gray-600 mb-4">{error}</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700"
          >
            Back to Dashboard
          </button>
        </div>
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
        <svg className="-ml-0.5 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        Documents
      </Button>
      
      {bot.allow_collaboration && (
        <Button
          variant="outline"
          size="sm"
          onClick={() => navigate(`/bots/${bot.id}/collaboration`)}
          className="border-primary-300 text-primary-700 hover:bg-primary-50 dark:bg-neutral-900 dark:border-primary-800 dark:text-primary-300"
        >
          <svg className="-ml-0.5 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
          </svg>
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