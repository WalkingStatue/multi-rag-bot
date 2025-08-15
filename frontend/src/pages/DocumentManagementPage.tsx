/**
 * Document management page for the application
 */

import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import DocumentManagement from '../components/documents/DocumentManagement';
import { botService } from '../services/botService';
import { Button, Container } from '../components/common';
import { MainLayout } from '../layouts';
import { BotResponse } from '../types/bot';

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

  // Header content with back button and bot info
  const headerContent = bot && (
    <div className="flex items-center space-x-4">
      <button
        onClick={() => navigate('/dashboard')}
        className="text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
        </svg>
      </button>
      <div>
        <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">{bot.name} - Documents</h1>
        <p className="text-sm text-neutral-500 dark:text-neutral-400">{bot.description}</p>
      </div>
    </div>
  );

  // Quick Actions
  const quickActions = bot && (
    <div className="flex items-center space-x-2">
      <Button
        variant="outline"
        size="sm"
        onClick={() => navigate(`/bots/${bot.id}/chat`)}
        className="border-success-300 text-success-700 hover:bg-success-50 dark:bg-neutral-900 dark:border-success-800 dark:text-success-300"
      >
        <svg className="-ml-0.5 mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        Chat
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

  if (!botId) {
    return (
      <ProtectedRoute>
        <MainLayout>
          <Container size="lg" padding="md" centered>
            <div className="text-center py-12">
              <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">Bot ID Required</h2>
              <p className="text-neutral-600 dark:text-neutral-400 mb-4">Bot ID is required to manage documents.</p>
              <Button
                onClick={() => navigate('/dashboard')}
                className="bg-primary-600 text-white hover:bg-primary-700"
              >
                Back to Dashboard
              </Button>
            </div>
          </Container>
        </MainLayout>
      </ProtectedRoute>
    );
  }

  if (isLoading) {
    return (
      <ProtectedRoute>
        <MainLayout>
          <Container size="lg" padding="md" centered>
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto mb-4"></div>
              <p className="text-neutral-600 dark:text-neutral-400">Loading documents...</p>
            </div>
          </Container>
        </MainLayout>
      </ProtectedRoute>
    );
  }

  if (error || !bot) {
    return (
      <ProtectedRoute>
        <MainLayout>
          <Container size="lg" padding="md" centered>
            <div className="text-center py-12">
              <div className="w-16 h-16 mx-auto mb-4 bg-red-100 rounded-full flex items-center justify-center">
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100 mb-2">Unable to Load Documents</h2>
              <p className="text-neutral-600 dark:text-neutral-400 mb-4">{error}</p>
              <Button
                onClick={() => navigate('/dashboard')}
                className="bg-primary-600 text-white hover:bg-primary-700"
              >
                Back to Dashboard
              </Button>
            </div>
          </Container>
        </MainLayout>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
      <MainLayout
        hasSidebar={false}
      >
        <div className="bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 px-6 py-4">
          <div className="flex items-center justify-between">
            {headerContent}
            {quickActions}
          </div>
        </div>

        <Container size="lg" padding="md" centered>
          <div className="py-6">
            <DocumentManagement botId={botId} />
          </div>
        </Container>
      </MainLayout>
    </ProtectedRoute>
  );
};

export default DocumentManagementPage;
