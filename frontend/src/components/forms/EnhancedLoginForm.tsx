/**
 * Enhanced login form using React Hook Form with validation
 */
import React from 'react';
import { Link } from 'react-router-dom';
import { useLoginForm } from '../../hooks/useForm';
import { useEnhancedAuth } from '../../hooks/useEnhancedAuth';
import { FormField, CheckboxField } from './FormField';
import { Button } from '../common/Button';
import { Alert } from '../common/Alert';
import { FormErrorBoundary } from '../common/EnhancedErrorBoundary';
import { LoginFormData } from '../../utils/formValidation';
import { getEnvVar } from '../../config/environment';

interface EnhancedLoginFormProps {
  onSuccess?: () => void;
  className?: string;
}

export const EnhancedLoginForm: React.FC<EnhancedLoginFormProps> = ({
  onSuccess,
  className = '',
}) => {
  const { login, isLoading, error, clearError } = useEnhancedAuth();
  const form = useLoginForm();
  
  const {
    control,
    submitWithValidation,
    formState: { errors },
    hasErrors,
  } = form;

  const handleSubmit = submitWithValidation(async (data: LoginFormData) => {
    await login({
      username: data.username,
      password: data.password,
    });
    onSuccess?.();
  });

  return (
    <FormErrorBoundary formName="Login Form">
      <div className={`max-w-md mx-auto ${className}`}>
        <div className="bg-white dark:bg-neutral-900 py-8 px-6 shadow rounded-lg sm:px-10">
          <div className="mb-6">
            <h2 className="text-center text-3xl font-extrabold text-neutral-900 dark:text-neutral-100">
              Sign in to your account
            </h2>
            <p className="mt-2 text-center text-sm text-neutral-600 dark:text-neutral-400">
              Or{' '}
              <Link
                to="/register"
                className="font-medium text-primary-600 hover:text-primary-500"
              >
                create a new account
              </Link>
            </p>
          </div>

          {error && (
            <Alert
              type="error"
              message={error}
              onClose={clearError}
              className="mb-6"
            />
          )}

          <form onSubmit={handleSubmit} className="space-y-6" noValidate>
            <FormField
              name="username"
              control={control}
              label="Username"
              type="text"
              placeholder="Enter your username"
              autoComplete="username"
              required
            />

            <FormField
              name="password"
              control={control}
              label="Password"
              type="password"
              placeholder="Enter your password"
              autoComplete="current-password"
              required
            />

            <CheckboxField
              name="rememberMe"
              control={control}
              label=""
              checkboxLabel="Remember me"
            />

            <div className="flex items-center justify-between">
              <div className="text-sm">
                <Link
                  to="/forgot-password"
                  className="font-medium text-primary-600 hover:text-primary-500"
                >
                  Forgot your password?
                </Link>
              </div>
            </div>

            <Button
              type="submit"
              className="w-full"
              isLoading={isLoading}
              disabled={isLoading || hasErrors}
            >
              {isLoading ? 'Signing in...' : 'Sign in'}
            </Button>

            {/* Development helper */}
            {getEnvVar.DEV() && hasErrors && (
              <div className="mt-4 p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-md">
                <h4 className="text-sm font-medium text-yellow-800 dark:text-yellow-200">
                  Form Validation Errors:
                </h4>
                <ul className="mt-1 text-xs text-yellow-700 dark:text-yellow-300">
                  {Object.entries(errors).map(([field, error]) => (
                    <li key={field}>
                      {field}: {(error as any)?.message || 'Invalid input'}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </form>
        </div>
      </div>
    </FormErrorBoundary>
  );
};