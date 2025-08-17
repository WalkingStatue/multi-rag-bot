/**
 * Main App component with routing and global providers
 */

import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from './components/common/ErrorBoundary';
import { useEffect } from 'react';

// Import pages
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { ForgotPasswordPage } from './pages/ForgotPasswordPage';
import { ResetPasswordPage } from './pages/ResetPasswordPage';
import { DashboardPage } from './pages/DashboardPage';
import { ProfilePage } from './pages/ProfilePage';
import { CollaborationPage } from './pages/CollaborationPage';
import DocumentManagementPage from './pages/DocumentManagementPage';
import { ChatPage } from './pages/ChatPage';
import { BotIntegrationsPage } from './pages/BotIntegrationsPage';

// Create a client for React Query
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors except 429
        if (error?.response?.status >= 400 && error?.response?.status < 500 && error?.response?.status !== 429) {
          return false;
        }
        return failureCount < 3;
      },
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
    },
    mutations: {
      retry: (failureCount, error: any) => {
        // Don't retry mutations on client errors
        if (error?.response?.status >= 400 && error?.response?.status < 500) {
          return false;
        }
        return failureCount < 2;
      },
    },
  },
});

function App() {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Router>
          <div className="App">
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
              <Route path="/forgot-password" element={<ForgotPasswordPage />} />
              <Route path="/reset-password" element={<ResetPasswordPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/profile" element={<ProfilePage />} />
              <Route path="/bots" element={<DashboardPage />} />
              <Route path="/bots/:botId/chat" element={<ChatPage />} />
              <Route path="/bots/:botId/documents" element={<DocumentManagementPage />} />
              <Route path="/bots/:botId/collaboration" element={<CollaborationPage />} />
              <Route path="/bots/:botId/integrations" element={<BotIntegrationsPage />} />
              <Route path="/" element={<DashboardPage />} />
              <Route path="*" element={
                <div className="min-h-screen bg-neutral-50 dark:bg-neutral-900 flex items-center justify-center px-4">
                  <div className="text-center max-w-md mx-auto">
                    <div className="mx-auto h-16 w-16 rounded-full bg-neutral-100 dark:bg-neutral-800 flex items-center justify-center mb-6">
                      <svg className="h-8 w-8 text-neutral-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                    </div>
                    <h1 className="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">Page Not Found</h1>
                    <p className="text-neutral-600 dark:text-neutral-400 mb-8">
                      The page you're looking for doesn't exist or has been moved.
                    </p>
                    <div className="space-y-3">
                      <button
                        onClick={() => window.history.back()}
                        className="inline-flex items-center justify-center px-6 py-3 border border-transparent text-sm font-medium rounded-lg text-white bg-primary-600 hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-all duration-150 w-full sm:w-auto"
                      >
                        Go Back
                      </button>
                      <button
                        onClick={() => window.location.href = '/dashboard'}
                        className="inline-flex items-center justify-center px-6 py-3 border border-neutral-300 dark:border-neutral-600 text-sm font-medium rounded-lg text-neutral-700 dark:text-neutral-200 bg-white dark:bg-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 transition-all duration-150 w-full sm:w-auto ml-0 sm:ml-3"
                      >
                        Go to Dashboard
                      </button>
                    </div>
                  </div>
                </div>
              } />
            </Routes>
          </div>
        </Router>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;