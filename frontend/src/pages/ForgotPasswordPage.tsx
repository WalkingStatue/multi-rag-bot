/**
 * Forgot password page component
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { ForgotPasswordForm } from '../components/auth/ForgotPasswordForm';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { AuthLayout } from '../layouts';

export const ForgotPasswordPage: React.FC = () => {
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
    <ProtectedRoute requireAuth={false}>
      <AuthLayout
        title="Reset your password"
        subtitle="Enter your email address and we'll send you a link to reset your password."
        footer={footerContent}
      >
        <ForgotPasswordForm />
      </AuthLayout>
    </ProtectedRoute>
  );
};