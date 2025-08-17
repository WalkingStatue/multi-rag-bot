/**
 * Document management page for the application
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import DocumentManagement from '../components/documents/DocumentManagement';
import { botService } from '../services/botService';
import { Button, Container, PageLoading, PageError } from '../components/common';
import { MainLayout } from '../layouts';
import { BotResponse } from '../types/bot';
import { ArrowLeftIcon, ChatBubbleLeftRightIcon, UserGroupIcon } from '@heroicons/react/24/outline';

const DocumentManagementPage: React.FC = () => {
  const { botId } = useParams<{ botId: string }>();
  const navigate = useNavigate();
  const [bot, setBot] = useState<BotResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
      } catch (err) {
        console.error('Failed to load bot:', err);
        setError('Failed to load bot. Please check if you have access to this bot.');
      } finally {
        setIsLoading(false);
      }
    };

    loadBot();
  }, [botId]);

  // Actions for the header
  const actions = bot && (
    <div className="flex items-center space-x-2">
      <Button
        variant="outline"
        size="sm"
        onClick={() => navigate(`/bots/${bot.id}/chat`)}
        className="border-success-300 text-success-700 hover:bg-success-50 dark:bg-neutral-900 dark:border-success-800 dark:text-success-300"
      >
        <ChatBubbleLeftRightIcon className="-ml-0.5 mr-2 h-4 w-4" />
        Chat
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

  if (!botId) {
    return (
      <ProtectedRoute>
        <MainLayout>
          <PageError
            title="Bot ID Required"
            message="Bot ID is required to manage documents."
            actionLabel="Back to Dashboard"
            onAction={() => navigate('/dashboard')}
          />
        </MainLayout>
      </ProtectedRoute>
    );
  }

  if (isLoading) {
    return (
      <ProtectedRoute>
        <MainLayout>
          <PageLoading message="Loading documents..." />
        </MainLayout>
      </ProtectedRoute>
    );
  }

  if (error || !bot) {
    return (
      <ProtectedRoute>
        <MainLayout>
          <PageError
            title="Unable to Load Documents"
            message={error || 'Bot not found'}
            actionLabel="Back to Dashboard"
            onAction={() => navigate('/dashboard')}
          />
        </MainLayout>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <MainLayout
        title={bot ? `${bot.name} Documents` : 'Documents'}
        subtitle={bot?.description}
        showBackButton={true}
        onBackClick={() => navigate('/dashboard')}
        actions={actions}
        maxWidth="lg"
      >
        <DocumentManagement botId={botId} />
      </MainLayout>
    </ProtectedRoute>
  );
};

export default DocumentManagementPage;
