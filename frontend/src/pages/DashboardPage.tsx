/**
 * Enhanced Dashboard Page
 * 
 * Unified dashboard with consistent styling and improved UX.
 */
import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { BotManagement } from '../components/bots/BotManagement';
import { APIKeyManagement } from '../components/apikeys/APIKeyManagement';
import { botService } from '../services/botService';
import { Button, Card, Grid, Panel } from '../components/common';
import { MainLayout } from '../layouts';
import { BotWithRole } from '../types/bot';
import { log } from '../utils/logger';

export const DashboardPage: React.FC = () => {
  const location = useLocation();
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
  const currentView = (location.pathname === '/bots') ? 'bots' : (searchParams.get('view') || 'dashboard');
  const currentAction = searchParams.get('action');
  
  // Get page title and subtitle based on current view
  const getPageHeader = () => {
    switch (currentView) {
      case 'bots':
        // Handle sub-actions for bot management
        if (currentAction === 'create') {
          return {
            title: 'Create New Bot',
            subtitle: 'Build a new AI assistant with custom settings',
          };
        } else if (currentAction === 'edit') {
          return {
            title: 'Edit Bot',
            subtitle: 'Modify your bot configuration and settings',
          };
        }
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
    } catch (error) { log.error('Failed to load dashboard data:', 'DashboardPage', { error });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateBot = () => {
    navigate('/bots?action=create');
  };

  const handleManageBots = () => {
    navigate('/bots');
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
    <div className="space-y-8">
      {/* Stats Cards */}
      <Grid cols={1} mdCols={2} lgCols={4} gap="md" className="mb-8">
        <Card variant="default" padding="md" className="group">
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 rounded-xl bg-primary-100 dark:bg-primary-900/30 group-hover:bg-primary-200 dark:group-hover:bg-primary-900/50 transition-colors duration-200">
              <svg className="h-6 w-6 text-primary-600 dark:text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <div className="ml-4">
              <div className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
                {isLoading ? '...' : stats.totalBots}
              </div>
              <div className="text-sm font-medium text-neutral-600 dark:text-neutral-400">
                Total Bots
              </div>
            </div>
          </div>
        </Card>
        
        <Card variant="default" padding="md" className="group">
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 rounded-xl bg-success-100 dark:bg-success-900/30 group-hover:bg-success-200 dark:group-hover:bg-success-900/50 transition-colors duration-200">
              <svg className="h-6 w-6 text-success-600 dark:text-success-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <div className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
                {isLoading ? '...' : stats.ownedBots}
              </div>
              <div className="text-sm font-medium text-neutral-600 dark:text-neutral-400">
                Owned Bots
              </div>
            </div>
          </div>
        </Card>
        
        <Card variant="default" padding="md" className="group">
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 rounded-xl bg-accent-100 dark:bg-accent-900/30 group-hover:bg-accent-200 dark:group-hover:bg-accent-900/50 transition-colors duration-200">
              <svg className="h-6 w-6 text-accent-600 dark:text-accent-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            </div>
            <div className="ml-4">
              <div className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
                {isLoading ? '...' : stats.sharedBots}
              </div>
              <div className="text-sm font-medium text-neutral-600 dark:text-neutral-400">
                Shared Bots
              </div>
            </div>
          </div>
        </Card>
        
        <Card variant="default" padding="md" className="group">
          <div className="flex items-center">
            <div className="flex-shrink-0 p-3 rounded-xl bg-warning-100 dark:bg-warning-900/30 group-hover:bg-warning-200 dark:group-hover:bg-warning-900/50 transition-colors duration-200">
              <svg className="h-6 w-6 text-warning-600 dark:text-warning-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
            </div>
            <div className="ml-4">
              <div className="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
                {isLoading ? '...' : stats.recentActivity}
              </div>
              <div className="text-sm font-medium text-neutral-600 dark:text-neutral-400">
                Recent Activity
              </div>
            </div>
          </div>
        </Card>
      </Grid>
      
      {/* Quick Actions */}
      <Card
        title="Quick Actions"
        subtitle="Get started with common tasks"
        variant="default"
        padding="md"
        className="mb-8"
      >
        <Grid cols={1} mdCols={2} lgCols={4} gap="md">
          <Card
            variant="outline"
            padding="md"
            hover={true}
            interactive={true}
            onClick={handleCreateBot}
            className="group"
          >
            <div className="flex items-center">
              <div className="flex-shrink-0 p-2 rounded-lg bg-primary-50 dark:bg-primary-900/20 group-hover:bg-primary-100 dark:group-hover:bg-primary-900/40 transition-colors duration-200">
                <svg className="h-6 w-6 text-primary-600 dark:text-primary-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
              </div>
              <div className="ml-3">
                <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Create Bot</h4>
                <p className="text-xs text-neutral-600 dark:text-neutral-400">Build a new AI assistant</p>
              </div>
            </div>
          </Card>
          
          <Card
            variant="outline"
            padding="md"
            hover={true}
            interactive={true}
            onClick={handleManageBots}
            className="group"
          >
            <div className="flex items-center">
              <div className="flex-shrink-0 p-2 rounded-lg bg-success-50 dark:bg-success-900/20 group-hover:bg-success-100 dark:group-hover:bg-success-900/40 transition-colors duration-200">
                <svg className="h-6 w-6 text-success-600 dark:text-success-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
              </div>
              <div className="ml-3">
                <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Manage Bots</h4>
                <p className="text-xs text-neutral-600 dark:text-neutral-400">View and edit bots</p>
              </div>
            </div>
          </Card>
          
          <Card
            variant="outline"
            padding="md"
            hover={true}
            interactive={true}
            onClick={handleManageAPIKeys}
            className="group"
          >
            <div className="flex items-center">
              <div className="flex-shrink-0 p-2 rounded-lg bg-accent-50 dark:bg-accent-900/20 group-hover:bg-accent-100 dark:group-hover:bg-accent-900/40 transition-colors duration-200">
                <svg className="h-6 w-6 text-accent-600 dark:text-accent-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                </svg>
              </div>
              <div className="ml-3">
                <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">API Keys</h4>
                <p className="text-xs text-neutral-600 dark:text-neutral-400">Manage provider keys</p>
              </div>
            </div>
          </Card>
          
          <Card
            variant="outline"
            padding="md"
            hover={true}
            interactive={true}
            onClick={handleManageProfile}
            className="group"
          >
            <div className="flex items-center">
              <div className="flex-shrink-0 p-2 rounded-lg bg-neutral-100 dark:bg-neutral-800 group-hover:bg-neutral-200 dark:group-hover:bg-neutral-700 transition-colors duration-200">
                <svg className="h-6 w-6 text-neutral-600 dark:text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <div className="ml-3">
                <h4 className="text-sm font-semibold text-neutral-900 dark:text-neutral-100">Profile</h4>
                <p className="text-xs text-neutral-600 dark:text-neutral-400">Update settings</p>
              </div>
            </div>
          </Card>
        </Grid>
      </Card>
      
      {/* Recent Bots */}
      <Card
        title="Recent Bots"
        subtitle="Your recently updated AI assistants"
        variant="default"
        padding="md"
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
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-10 w-10 border-2 border-primary-600 border-t-transparent mx-auto"></div>
            <p className="mt-4 text-neutral-600 dark:text-neutral-400">Loading bots...</p>
          </div>
        ) : bots.length === 0 ? (
          <div className="text-center py-12">
            <div className="mx-auto h-16 w-16 rounded-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center mb-4">
              <svg className="h-8 w-8 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">No bots yet</h3>
            <p className="mt-2 text-neutral-600 dark:text-neutral-400 max-w-sm mx-auto">
              Get started by creating your first AI assistant to begin building intelligent conversations.
            </p>
            <div className="mt-6">
              <Button
                onClick={handleCreateBot}
                size="lg"
              >
                Create Your First Bot
              </Button>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {bots.slice(0, 5).map((botWithRole) => (
              <Card
                key={botWithRole.bot.id}
                variant="outline"
                padding="md"
                hover={true}
                interactive={true}
                onClick={() => navigate('/bots?action=edit&id=' + botWithRole.bot.id)}
                className="group"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center min-w-0 flex-1">
                    <div className="flex-shrink-0 text-2xl mr-4">
                      {getProviderIcon(botWithRole.bot.llm_provider)}
                    </div>
                    <div className="min-w-0 flex-1">
                      <h4 className="text-base font-semibold text-neutral-900 dark:text-neutral-100 truncate">
                        {botWithRole.bot.name}
                      </h4>
                      <p className="text-sm text-neutral-600 dark:text-neutral-400 truncate">
                        {botWithRole.bot.description || 'No description'}
                      </p>
                      <div className="flex items-center mt-2 space-x-3">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getRoleBadgeColor(botWithRole.role)}`}>
                          {botWithRole.role}
                        </span>
                        <span className="text-xs text-neutral-500 dark:text-neutral-400">
                          Updated {new Date(botWithRole.bot.updated_at).toLocaleDateString()}
                        </span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2 ml-4">
                    <Button
                      variant="success"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        navigate(`/bots/${botWithRole.bot.id}/chat`);
                      }}
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
                      >
                        Share
                      </Button>
                    )}
                  </div>
                </div>
              </Card>
            ))}
          </div>
        )}
      </Card>
    </div>
  );

  return (
    <ProtectedRoute>
      <MainLayout
        title={getPageHeader().title}
        subtitle={getPageHeader().subtitle}
        actions={currentView === 'dashboard' ? dashboardActions : undefined}
        maxWidth="xl"
        padding="md"
      >
        {renderContent()}
      </MainLayout>
    </ProtectedRoute>
  );
};