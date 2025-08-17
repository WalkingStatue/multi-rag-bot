/**
 * Collaboration Management Page
 * Comprehensive page for managing bot collaborators and permissions
 */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { BotWithRole, BotPermission } from '../types/bot';
import { botService } from '../services/botService';
import { permissionService } from '../services/permissionService';
import { CollaborationManagement } from '../components/bots/CollaborationManagement';
import { BulkPermissionManager } from '../components/bots/BulkPermissionManager';
import { NotificationSystem } from '../components/common/NotificationSystem';
import { Button, Container } from '../components/common';
import { useToastHelpers } from '../components/common/Toast';

import { MainLayout } from '../layouts';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';

interface CollaborationPageProps {
  botId?: string;
}

export const CollaborationPage: React.FC<CollaborationPageProps> = ({ botId: propBotId }) => {
  const { botId: urlBotId } = useParams<{ botId: string }>();
  const navigate = useNavigate();
  const { error: showErrorToast } = useToastHelpers();
  
  const botId = propBotId || urlBotId;
  
  const [bot, setBot] = useState<BotWithRole | null>(null);
  const [collaborators, setCollaborators] = useState<BotPermission[]>([]);
  const [currentUserRole, setCurrentUserRole] = useState<'owner' | 'admin' | 'editor' | 'viewer'>('viewer');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'collaborators' | 'bulk-update' | 'activity'>('collaborators');

  useEffect(() => {
    if (botId) {
      loadBotData();
    }
  }, [botId]);

  const loadBotData = async () => {
    if (!botId) return;

    try {
      setLoading(true);
      setError(null);

      // Load bot details and user's role
      const [botData, userRole] = await Promise.all([
        botService.getBot(botId),
        permissionService.getUserBotRole(botId)
      ]);

      // Transform BotResponse to BotWithRole
      const botWithRole: BotWithRole = {
        bot: botData,
        role: (userRole as 'owner' | 'admin' | 'editor' | 'viewer') || 'viewer'
      };

      setBot(botWithRole);
      setCurrentUserRole((userRole as 'owner' | 'admin' | 'editor' | 'viewer') || 'viewer');

      // Load collaborators if user has permission
      if (['owner', 'admin'].includes(userRole || 'viewer')) {
        try {
          const collaboratorsData = await permissionService.getBotPermissions(botId);
          setCollaborators(collaboratorsData);
        } catch (err) {
          console.warn('Could not load collaborators:', err);
        }
      }
    } catch (err: any) {
      console.error('Failed to load bot data:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to load bot data';
      setError(errorMessage);
      showErrorToast('Error Loading Bot', errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handlePermissionUpdate = () => {
    // Reload collaborators after permission changes
    if (['owner', 'admin'].includes(currentUserRole)) {
      loadBotData();
    }
  };

  const handleNotificationClick = (notification: any) => {
    // Handle notification clicks - could navigate to specific sections
    console.log('Notification clicked:', notification);
  };

  const canManageCollaborators = ['owner', 'admin'].includes(currentUserRole);

  // Actions for the header
  const actions = bot && (
    <NotificationSystem
      botId={botId}
      onNotificationClick={handleNotificationClick}
    />
  );

  if (loading) {
    return (
      <ProtectedRoute>
        <MainLayout>
          <Container size="lg" padding="md" centered>
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600 mx-auto"></div>
              <p className="mt-4 text-neutral-600 dark:text-neutral-400">Loading collaboration data...</p>
            </div>
          </Container>
        </MainLayout>
      </ProtectedRoute>
    );
  }

  if (error) {
    return (
      <ProtectedRoute>
        <MainLayout>
          <Container size="lg" padding="md" centered>
            <div className="text-center">
              <div className="mx-auto h-16 w-16 rounded-full bg-red-100 dark:bg-red-900/20 flex items-center justify-center mb-6">
                <svg className="h-8 w-8 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">Error Loading Bot</h1>
              <p className="text-neutral-600 dark:text-neutral-400 mb-8">{error}</p>
              <Button
                onClick={() => navigate('/dashboard')}
                className="bg-neutral-700 hover:bg-neutral-800 text-white"
              >
                Back to Dashboard
              </Button>
            </div>
          </Container>
        </MainLayout>
      </ProtectedRoute>
    );
  }

  if (!bot) {
    return (
      <ProtectedRoute>
        <MainLayout>
          <Container size="lg" padding="md" centered>
            <div className="text-center">
              <div className="mx-auto h-16 w-16 rounded-full bg-red-100 dark:bg-red-900/20 flex items-center justify-center mb-6">
                <svg className="h-8 w-8 text-red-600 dark:text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
              </div>
              <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">Bot Not Found</h1>
              <p className="text-neutral-600 dark:text-neutral-400 mb-8">The requested bot could not be found.</p>
              <Button
                onClick={() => navigate('/dashboard')}
                className="bg-neutral-700 hover:bg-neutral-800 text-white"
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
        title={bot ? `${bot.bot.name} Collaboration` : 'Collaboration Management'}
        subtitle={bot ? `Manage collaborators and permissions for "${bot.bot.name}"` : undefined}
        showBackButton={true}
        onBackClick={() => navigate('/dashboard')}
        actions={actions}
        maxWidth="lg"
      >
        <Container size="lg" padding="md" centered>
          {/* Bot Info Card */}
          <div className="bg-white dark:bg-neutral-900 shadow rounded-lg p-6 mb-8">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">{bot.bot.name}</h2>
                <p className="text-neutral-600 dark:text-neutral-400">{bot.bot.description || 'No description'}</p>
                <div className="mt-2 flex items-center space-x-4 text-sm text-neutral-500 dark:text-neutral-400">
                  <span>Your role: <span className="font-medium text-neutral-900 dark:text-neutral-100">{currentUserRole}</span></span>
                  <span>•</span>
                  <span>Provider: {bot.bot.llm_provider}</span>
                  <span>•</span>
                  <span>Collaboration: {bot.bot.allow_collaboration ? 'Enabled' : 'Disabled'}</span>
                </div>
              </div>
              <div className="text-right">
                <div className="text-sm text-neutral-500 dark:text-neutral-400">Created</div>
                <div className="text-sm font-medium text-neutral-900 dark:text-neutral-100">
                  {new Date(bot.bot.created_at).toLocaleDateString()}
                </div>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="border-b border-neutral-200 dark:border-neutral-800 mb-8">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('collaborators')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'collaborators'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300 dark:text-neutral-400 dark:hover:text-neutral-200 dark:hover:border-neutral-600'
                }`}
              >
                Collaborators
              </button>
              {canManageCollaborators && (
                <button
                  onClick={() => setActiveTab('bulk-update')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm ${
                    activeTab === 'bulk-update'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300 dark:text-neutral-400 dark:hover:text-neutral-200 dark:hover:border-neutral-600'
                  }`}
                >
                  Bulk Update
                </button>
              )}
              <button
                onClick={() => setActiveTab('activity')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'activity'
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-neutral-500 hover:text-neutral-700 hover:border-neutral-300 dark:text-neutral-400 dark:hover:text-neutral-200 dark:hover:border-neutral-600'
                }`}
              >
                Activity Log
              </button>
            </nav>
          </div>

          {/* Content */}
          <div className="mt-6">
            {activeTab === 'collaborators' && (
              <CollaborationManagement
                botId={botId!}
                botName={bot.bot.name}
                currentUserRole={currentUserRole}
                onPermissionUpdate={handlePermissionUpdate}
              />
            )}

            {activeTab === 'bulk-update' && canManageCollaborators && (
              <BulkPermissionManager
                botId={botId!}
                collaborators={collaborators}
                currentUserRole={currentUserRole}
                onUpdateComplete={handlePermissionUpdate}
              />
            )}

            {activeTab === 'activity' && (
              <div className="space-y-6">
                <div className="border-b border-neutral-200 dark:border-neutral-800 pb-4">
                  <h2 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">Activity Log</h2>
                  <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
                    View recent activity and permission changes for this bot
                  </p>
                </div>
                
                <CollaborationManagement
                  botId={botId!}
                  botName={bot.bot.name}
                  currentUserRole={currentUserRole}
                  onPermissionUpdate={handlePermissionUpdate}
                />
              </div>
            )}
          </div>

          {/* Permission Warning */}
          {!canManageCollaborators && (
            <div className="mt-8 bg-warning-100 border border-warning-200 rounded-md p-4">
              <div className="flex">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-warning-600" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-warning-700">
                    Limited Permissions
                  </h3>
                  <div className="mt-2 text-sm text-warning-700">
                    <p>
                      You have {currentUserRole} permissions for this bot. 
                      Only owners and admins can manage collaborators and permissions.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}


        </Container>
      </MainLayout>
    </ProtectedRoute>
  );
};

export default CollaborationPage;