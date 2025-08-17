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
    <div className="max-w-md mx-auto">
      <div className="bg-white dark:bg-neutral-900 py-8 px-6 shadow rounded-lg sm:px-10 transition-colors duration-200">
        <div className="mb-6">
          <h2 className="text-center text-3xl font-extrabold text-neutral-900 dark:text-neutral-100">
            Create your account
          </h2>
          <p className="mt-2 text-center text-sm text-neutral-600 dark:text-neutral-400">
            Or{' '}
            <Link
              to="/login"
              className="font-medium text-primary-600 hover:text-primary-500 dark:text-primary-400 dark:hover:text-primary-300 transition-colors duration-150"
            >
              sign in to your existing account
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
        
        <form onSubmit={handleSubmit} className="space-y-6">
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
          />

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
          />

          <Input
            label="Full Name (Optional)"
            name="fullName"
            type="text"
            autoComplete="name"
            value={formData.fullName}
            onChange={handleInputChange}
            error={errors.fullName}
            placeholder="Enter your full name"
          />

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
          />

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
          />

          <Button
            type="submit"
            className="w-full"
            isLoading={isLoading}
            disabled={isLoading}
          >
            {isLoading ? 'Creating account...' : 'Create account'}
          </Button>
        </form>
      </div>
    </div>
  );
};