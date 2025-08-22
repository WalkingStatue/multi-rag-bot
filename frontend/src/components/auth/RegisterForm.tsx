/**
 * Registration form component
 */
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { useToastHelpers } from '../common/Toast';
import { setAuthToastFunction } from '../../stores/authStore';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { Alert } from '../common/Alert';
import { validateField, authValidationRules, validateConfirmPassword } from '../../utils/validators';

interface RegisterFormProps {
  onSuccess?: () => void;
}

export const RegisterForm: React.FC<RegisterFormProps> = ({ onSuccess }) => {
  const { register, isLoading, error, clearError } = useAuth();
  const { error: showErrorToast } = useToastHelpers();
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    fullName: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  // Set up toast function for auth store
  useEffect(() => {
    setAuthToastFunction(showErrorToast);
  }, [showErrorToast]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Clear field error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
    
    // Don't clear global error automatically - let user dismiss it manually
    // This prevents errors from disappearing too quickly
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};
    
    // Validate username
    const usernameError = validateField(formData.username, authValidationRules.username);
    if (usernameError) {
      newErrors.username = usernameError;
    }

    // Validate email
    const emailError = validateField(formData.email, authValidationRules.email);
    if (emailError) {
      newErrors.email = emailError;
    }

    // Validate password
    const passwordError = validateField(formData.password, authValidationRules.password);
    if (passwordError) {
      newErrors.password = passwordError;
    }

    // Validate confirm password
    const confirmPasswordError = validateConfirmPassword(formData.password, formData.confirmPassword);
    if (confirmPasswordError) {
      newErrors.confirmPassword = confirmPasswordError;
    }

    // Validate full name (optional)
    if (formData.fullName) {
      const fullNameError = validateField(formData.fullName, authValidationRules.fullName);
      if (fullNameError) {
        newErrors.fullName = fullNameError;
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    try {
      await register({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        full_name: formData.fullName || undefined,
      });
      onSuccess?.();
    } catch (error: any) {
      // Error is handled by the auth store
      // The error state will be set in the store and displayed via the Alert component
    }
  };

  return (
    <div className="w-full max-w-md mx-auto">
      {/* Logo/Brand Section */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 mb-6 shadow-lg">
          <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 0 002 2z" />
          </svg>
        </div>
        <h2 className="text-3xl font-bold text-neutral-900 dark:text-neutral-100 mb-2">
          Create your account
        </h2>
        <p className="text-neutral-600 dark:text-neutral-400">
          Join thousands of developers building AI assistants
        </p>
      </div>

      <div className="bg-white dark:bg-neutral-900 p-8 rounded-2xl shadow-xl border border-neutral-200 dark:border-neutral-800">
        {error && (
          <div className="mb-6 animate-in fade-in-50 duration-300">
            <Alert
              type="error"
              message={error}
              onClose={clearError}
            />
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="grid grid-cols-1 gap-5">
            <div className="group">
              <Input
                label="Username"
                name="username"
                type="text"
                autoComplete="username"
                required
                value={formData.username}
                onChange={handleInputChange}
                error={errors.username}
                placeholder="Choose a username"
                helperText="3-50 characters, letters, numbers, underscore and dash only"
                className="transition-all duration-200 group-hover:border-primary-300 dark:group-hover:border-primary-700"
              />
            </div>

            <div className="group">
              <Input
                label="Email"
                name="email"
                type="email"
                autoComplete="email"
                required
                value={formData.email}
                onChange={handleInputChange}
                error={errors.email}
                placeholder="Enter your email address"
                className="transition-all duration-200 group-hover:border-primary-300 dark:group-hover:border-primary-700"
              />
            </div>

            <div className="group">
              <Input
                label="Full Name (Optional)"
                name="fullName"
                type="text"
                autoComplete="name"
                value={formData.fullName}
                onChange={handleInputChange}
                error={errors.fullName}
                placeholder="Enter your full name"
                className="transition-all duration-200 group-hover:border-primary-300 dark:group-hover:border-primary-700"
              />
            </div>

            <div className="group">
              <Input
                label="Password"
                name="password"
                type="password"
                autoComplete="new-password"
                required
                value={formData.password}
                onChange={handleInputChange}
                error={errors.password}
                placeholder="Create a password"
                helperText="At least 8 characters with uppercase, lowercase, and number"
                className="transition-all duration-200 group-hover:border-primary-300 dark:group-hover:border-primary-700"
              />
            </div>

            <div className="group">
              <Input
                label="Confirm Password"
                name="confirmPassword"
                type="password"
                autoComplete="new-password"
                required
                value={formData.confirmPassword}
                onChange={handleInputChange}
                error={errors.confirmPassword}
                placeholder="Confirm your password"
                className="transition-all duration-200 group-hover:border-primary-300 dark:group-hover:border-primary-700"
              />
            </div>
          </div>

          {/* Terms and Privacy */}
          <div className="flex items-start pt-4">
            <div className="flex items-center h-5">
              <input
                id="terms"
                name="terms"
                type="checkbox"
                required
                className="h-4 w-4 rounded border-neutral-300 text-primary-600 focus:ring-primary-500 dark:bg-neutral-800 dark:border-neutral-600 transition-colors duration-200"
              />
            </div>
            <div className="ml-3 text-sm">
              <label htmlFor="terms" className="text-neutral-700 dark:text-neutral-300">
                I agree to the{' '}
                <Link to="/terms" className="font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300 transition-colors duration-200 hover:underline">
                  Terms of Service
                </Link>{' '}
                and{' '}
                <Link to="/privacy" className="font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300 transition-colors duration-200 hover:underline">
                  Privacy Policy
                </Link>
              </label>
            </div>
          </div>

          <Button
            type="submit"
            className="w-full py-3 text-base font-semibold bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white border-0 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 transition-all duration-200 mt-6"
            isLoading={isLoading}
            disabled={isLoading}
          >
            {isLoading ? (
              <div className="flex items-center justify-center">
                <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
                Creating account...
              </div>
            ) : (
              'Create Account'
            )}
          </Button>
        </form>

        {/* Divider */}
        <div className="mt-8 pt-6 border-t border-neutral-200 dark:border-neutral-800">
          <p className="text-center text-sm text-neutral-600 dark:text-neutral-400">
            Already have an account?{' '}
            <Link
              to="/login"
              className="font-semibold text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300 transition-colors duration-200 hover:underline"
            >
              Sign in instead
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};