/**
 * Registration page component
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Link } from 'react-router-dom';
import { RegisterForm } from '../components/auth/RegisterForm';
import { ProtectedRoute } from '../components/auth/ProtectedRoute';
import { AuthLayout } from '../layouts';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();

  const handleRegisterSuccess = () => {
    navigate('/dashboard', { replace: true });
  };

  // Footer content with login link
  const footerContent = (
    <p className="text-sm text-neutral-600 dark:text-neutral-400">
      Already have an account?{' '}
      <Link
        to="/login"
        className="font-medium text-primary-600 hover:text-primary-500"
      >
        Sign in
      </Link>
    </p>
  );

  return (
    <ProtectedRoute requireAuth={false}>
      <AuthLayout
        title="Create your account"
        subtitle="Fill in your details to get started with our platform."
        footer={footerContent}
      >
        <RegisterForm onSuccess={handleRegisterSuccess} />
      </AuthLayout>
    </ProtectedRoute>
  );
};