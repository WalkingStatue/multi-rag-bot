/**
 * Dashboard page component
 */
import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { BotManagement } from '../components/bots/BotManagement';
import { APIKeyManagement } from '../components/apikeys/APIKeyManagement';
import { botService } from '../services/botService';
import { Button, Card, Grid, Panel, Container } from '../components/common';
import { DashboardLayout } from '../layouts';
import { BotWithRole } from '../types/bot';

export const DashboardPage: React.FC = () => {
  const { /* user */ } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [bots, setBots] = useState<BotWithRole[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [stats, setStats] = useState({
    totalBots: 0,
    ownedBots: 0,
    sharedBots: 0,
    recentActivity: 0
  });

  // Get current view from URL parameters
  const currentView = searchParams.get('view') || 'dashboard';
  
  // Get page title and subtitle based on current view
  const getPageHeader = () => {
    switch (currentView) {
      case 'bots':
        return {
          title: 'Bot Management',
          subtitle: 'Create, edit and manage your bots',
        };
      case 'api-keys':
        return {
          title: 'API Key Management',
          subtitle: 'Manage your API keys for different LLM providers',
        };
      default:
        return {
          title: 'Dashboard',
          subtitle: 'Welcome to your Multi-Bot RAG Platform dashboard!',
        };
    }
  };

  // Dashboard actions
  const dashboardActions = (
    <Button
      variant="outline"
      size="sm"
      onClick={() => loadDashboardData()}
      isLoading={isLoading}
    >
      Refresh
    </Button>
  );

  useEffect(() => {
    if (currentView === 'dashboard') {
      loadDashboardData();
    }
  }, [currentView]);

  const loadDashboardData = async () => {
    try {
      setIsLoading(true);
      const userBots = await botService.getUserBots();
      setBots(userBots);
      
      // Calculate stats
      const ownedBots = userBots.filter(bot => bot.role === 'owner').length;
      const sharedBots = userBots.filter(bot => bot.role !== 'owner').length;
      
      setStats({
        totalBots: userBots.length,
        ownedBots,
        sharedBots,
        recentActivity: userBots.filter(bot => {
          const lastUpdated = new Date(bot.bot.updated_at);
          const weekAgo = new Date();
          weekAgo.setDate(weekAgo.getDate() - 7);
          return lastUpdated > weekAgo;
        }).length
      });
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateBot = () => {
    navigate('/dashboard?view=bots&action=create');
  };

  const handleManageBots = () => {
    navigate('/dashboard?view=bots');
  };

  const handleManageAPIKeys = () => {
    navigate('/dashboard?view=api-keys');
  };

  const handleManageProfile = () => {
    navigate('/profile');
  };

  const getRoleBadgeColor = (role: string) => {
    switch (role) {
      case 'owner': return 'bg-green-100 text-green-800';
      case 'admin': return 'bg-blue-100 text-blue-800';
      case 'editor': return 'bg-yellow-100 text-yellow-800';
      case 'viewer': return 'bg-gray-100 text-gray-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getProviderIcon = (provider: string) => {
    const icons = {
      openai: '🤖',
      anthropic: '🧠',
      gemini: '💎',
      openrouter: '🔀',
    };
    return icons[provider as keyof typeof icons] || '🤖';
  };

  const renderContent = () => {
    switch (currentView) {
      case 'bots':
        return <BotManagement />;
      case 'api-keys':
        return <APIKeyManagement />;
      default:
        return renderDashboardContent();
    }
  };

  const renderDashboardContent = () => (
    <Container>
      {/* Stats Cards */}
      <Grid cols={1} mdCols={2} lgCols={4} gap="medium" className="mb-8">
        <Card
          title="Total Bots"
          variant="default"
          padding="medium"
        >
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 rounded-full bg-primary-100 dark:bg-primary-900/30">
              <svg className="h-6 w-6 text-primary-600 dark:text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <div className="ml-5">
              <div className="text-3xl font-semibold text-neutral-900 dark:text-neutral-100">
                {isLoading ? '...' : stats.totalBots}
              </div>
            </div>
          </div>
        </Card>
        
        <Card
          title="Owned Bots"
          variant="default"
          padding="medium"
        >
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 rounded-full bg-success-100 dark:bg-success-900/30">
              <svg className="h-6 w-6 text-success-600 dark:text-success-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
              </svg>
            </div>
            <div className="ml-5">
              <div className="text-3xl font-semibold text-neutral-900 dark:text-neutral-100">
                {isLoading ? '...' : stats.ownedBots}
              </div>
            </div>
          </div>
        </Card>
        
        <Card
          title="Shared Bots"
          variant="default"
          padding="medium"
        >
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 rounded-full bg-accent-100 dark:bg-accent-900/30">
              <svg className="h-6 w-6 text-accent-600 dark:text-accent-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <div className="ml-5">
              <div className="text-3xl font-semibold text-neutral-900 dark:text-neutral-100">
                {isLoading ? '...' : stats.sharedBots}
              </div>
            </div>
          </div>
        </Card>
        
        <Card
          title="Recent Activity"
          variant="default"
          padding="medium"
        >
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 rounded-full bg-warning-100 dark:bg-warning-900/30">
              <svg className="h-6 w-6 text-warning-600 dark:text-warning-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div className="ml-5">
              <div className="text-3xl font-semibold text-neutral-900 dark:text-neutral-100">
                {isLoading ? '...' : stats.recentActivity}
              </div>
            </div>
          </div>
        </Card>
      </Grid>
      
      {/* Quick Actions */}
      <Panel
        title="Quick Actions"
        variant="default"
        padding="medium"
        className="mb-8"
      >
        <Grid cols={1} mdCols={2} lgCols={4} gap="medium">
          <Card
            variant="outline"
            padding="medium"
            hover={true}
            onClick={handleCreateBot}
          >
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-8 w-8 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              </div>
              <div className="ml-4">
                <h4 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Create New Bot</h4>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">Build a new AI assistant</p>
              </div>
            </div>
          </Card>
          
          <Card
            variant="outline"
            padding="medium"
            hover={true}
            onClick={handleManageBots}
          >
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-8 w-8 text-success-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="ml-4">
                <h4 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Manage Bots</h4>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">View and edit your bots</p>
              </div>
            </div>
          </Card>
          
          <Card
            variant="outline"
            padding="medium"
            hover={true}
            onClick={handleManageAPIKeys}
          >
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-8 w-8 text-accent-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
              </div>
              <div className="ml-4">
                <h4 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">API Keys</h4>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">Manage provider keys</p>
              </div>
            </div>
          </Card>
          
          <Card
            variant="outline"
            padding="medium"
            hover={true}
            onClick={handleManageProfile}
          >
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <svg className="h-8 w-8 text-primary-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <div className="ml-4">
                <h4 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">Profile</h4>
                <p className="text-sm text-neutral-500 dark:text-neutral-400">Update your settings</p>
              </div>
            </div>
          </Card>
        </Grid>
      </Panel>
      
      {/* Recent Bots */}
      <Panel
        title="Recent Bots"
        variant="default"
        padding="medium"
        headerActions={
          <Button
            variant="outline"
            size="sm"
            onClick={handleManageBots}
          >
            View all
          </Button>
        }
      >
        {isLoading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600 mx-auto"></div>
            <p className="mt-2 text-neutral-600 dark:text-neutral-400">Loading bots...</p>
          </div>
        ) : bots.length === 0 ? (
          <div className="text-center py-8">
            <svg className="mx-auto h-12 w-12 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <h3 className="mt-2 text-sm font-medium text-neutral-900 dark:text-neutral-100">No bots yet</h3>
            <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
              Get started by creating your first AI assistant.
            </p>
            <div className="mt-6">
              <Button
                onClick={handleCreateBot}
                className="bg-primary-600 hover:bg-primary-700 text-white"
              >
                Create Your First Bot
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {bots.slice(0, 5).map((botWithRole) => (
              <Card
                key={botWithRole.bot.id}
                variant="outline"
                padding="medium"
                hover={true}
                onClick={() => navigate('/dashboard?view=bots&action=edit&id=' + botWithRole.bot.id)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <div className="flex-shrink-0">
                      <span className="text-2xl">{getProviderIcon(botWithRole.bot.llm_provider)}</span>
                    </div>
                    <div className="ml-4">
                      <h4 className="text-sm font-medium text-neutral-900 dark:text-neutral-100">{botWithRole.bot.name}</h4>
                      <p className="text-sm text-neutral-500 dark:text-neutral-400">{botWithRole.bot.description || 'No description'}</p>
                      <div className="flex items-center mt-1 space-x-2">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRoleBadgeColor(botWithRole.role)}`}>
                          {botWithRole.role}
                        </span>
                        <span className="text-xs text-neutral-400">
                          {new Date(botWithRole.bot.updated_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/bots/${botWithRole.bot.id}/chat`);
                      }}
                      className="border-success-300 text-success-700 hover:bg-success-50 dark:bg-neutral-900 dark:border-success-800 dark:text-success-300"
                    >
                      Chat
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/bots/${botWithRole.bot.id}/documents`);
                      }}
                      className="border-accent-300 text-accent-700 hover:bg-accent-50 dark:bg-neutral-900 dark:border-accent-800 dark:text-accent-300"
                    >
                      Documents
                    </Button>
                    {botWithRole.bot.allow_collaboration && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/bots/${botWithRole.bot.id}/collaboration`);
                        }}
                        className="border-primary-300 text-primary-700 hover:bg-primary-50 dark:bg-neutral-900 dark:border-primary-800 dark:text-primary-300"
                      >
                        Collaboration
                      </Button>
                    )}
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate('/dashboard?view=bots&action=edit&id=' + botWithRole.bot.id);
                      }}
                      className="border-neutral-300 text-neutral-700 hover:bg-neutral-50 dark:bg-neutral-900 dark:border-neutral-700 dark:text-neutral-200"
                    >
                      Edit
                    </Button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </Panel>
    </Container>
  );

  return (
    <ProtectedRoute>
      <DashboardLayout
        title={getPageHeader().title}
        subtitle={getPageHeader().subtitle}
        actions={currentView === 'dashboard' ? dashboardActions : undefined}
      >
        {renderContent()}
      </DashboardLayout>
    </ProtectedRoute>
  );
};