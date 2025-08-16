/**
 * Enhanced Profile Page
 * 
 * User profile management with consistent styling and improved UX.
 */
import React from 'react';
import { UserProfile } from '../components/auth/UserProfile';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { MainLayout } from '../layouts';

export const ProfilePage: React.FC = () => {
  return (
    <ProtectedRoute>
      <MainLayout
        title="Profile Settings"
        subtitle="Manage your account settings and preferences"
        maxWidth="lg"
        padding="md"
        showBackButton={true}
      >
        <UserProfile />
      </MainLayout>
    </ProtectedRoute>
  );
};