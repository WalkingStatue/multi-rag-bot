/**
 * Reset password page component
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { ResetPasswordForm } from '../components/auth/ResetPasswordForm';
import { PublicRoute } from '../components/routing/EnhancedProtectedRoute';
import { AuthLayout } from '../layouts';

export const ResetPasswordPage: React.FC = () => {
  // Footer content with login link
  const footerContent = (
    <p className="text-sm text-neutral-600 dark:text-neutral-400">
      Remember your password?{' '}
      <Link
        to="/login"
        className="font-medium text-primary-600 hover:text-primary-500"
      >
        Back to login
      </Link>
    </p>
  );

  return (
    <PublicRoute>
      <AuthLayout
        title="Create new password"
        subtitle="Enter your new password below to reset your account."
        footer={footerContent}
      >
        <ResetPasswordForm />
      </AuthLayout>
    </PublicRoute>
  );
};