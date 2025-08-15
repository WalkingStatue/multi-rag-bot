/**
 * Profile page component
 */
import React from 'react';
import { UserProfile } from '../components/auth/UserProfile';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { MainLayout } from '../layouts';
import { Container } from '../components/common';

export const ProfilePage: React.FC = () => {
  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="bg-white dark:bg-neutral-900 border-b border-neutral-200 dark:border-neutral-800 px-6 py-4 mb-6">
          <h1 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">Profile</h1>
          <p className="text-sm text-neutral-500 dark:text-neutral-400">Manage your account settings and preferences</p>
        </div>
        <Container size="md" padding="md" centered>
          <UserProfile />
        </Container>
      </MainLayout>
    </ProtectedRoute>
  );
};