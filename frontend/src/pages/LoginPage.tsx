/**
 * Login page component
 */
import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Link } from 'react-router-dom';
import { LoginForm } from '../components/auth/LoginForm';
import { PublicRoute } from '../components/routing/EnhancedProtectedRoute';
import { AuthLayout } from '../layouts';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLoginSuccess = () => {
    const from = location.state?.from?.pathname || '/dashboard';
    navigate(from, { replace: true });
  };

  // Footer content with registration link
  const footerContent = (
    <p className="text-sm text-neutral-600 dark:text-neutral-400">
      Don't have an account?{' '}
      <Link
        to="/register"
        className="font-medium text-primary-600 hover:text-primary-500"
      >
        Sign up
      </Link>
    </p>
  );

  return (
    <PublicRoute>
      <AuthLayout
        title="Sign in to your account"
        subtitle="Welcome back! Please enter your credentials to access your account."
        footer={footerContent}
      >
        <LoginForm onSuccess={handleLoginSuccess} />
      </AuthLayout>
    </PublicRoute>
  );
};