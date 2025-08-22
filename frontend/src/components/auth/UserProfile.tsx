/**
 * User profile management component
 */
import React, { useState, useEffect } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../common/Button';
import { Input } from '../common/Input';
import { Alert } from '../common/Alert';
import { validateField, authValidationRules } from '../../utils/validators';
import { log } from '../../utils/logger';

export const UserProfile: React.FC = () => {
  const { user, updateProfile, isLoading, error, clearError } = useAuth();
  
  // Debug logging
  log.debug('UserProfile render', 'UserProfile', { user, isLoading, error, hasUser: !!user });
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    fullName: '',
    avatarUrl: '',
  });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [successMessage, setSuccessMessage] = useState('');

  // Initialize form data when user data is available
  useEffect(() => {
    if (user) {
      setFormData({
        username: user.username,
        email: user.email,
        fullName: user.full_name || '',
        avatarUrl: user.avatar_url || '',
      });
    }
  }, [user]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
    
    // Clear field error when user starts typing
    if (errors[name]) {
      setErrors(prev => ({ ...prev, [name]: '' }));
    }
    
    // Clear messages
    if (error) {
      clearError();
    }
    if (successMessage) {
      setSuccessMessage('');
    }
  };

  const handleAvatarUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, avatarUrl: e.target.value }));
    if (errors['avatar']) setErrors(prev => ({ ...prev, avatar: '' }));
    if (error) clearError();
    if (successMessage) setSuccessMessage('');
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
      await updateProfile({
        username: formData.username,
        email: formData.email,
        full_name: formData.fullName || undefined,
        avatar_url: formData.avatarUrl || undefined,
      });
      setSuccessMessage('Profile updated successfully!');
    } catch (error) {
      // Error is handled by the auth store
    }
  };

  const hasChanges = user && (
    formData.username !== user.username ||
    formData.email !== user.email ||
    formData.fullName !== (user.full_name || '') ||
    (formData.avatarUrl || '') !== (user.avatar_url || '')
  );

  if (!user) {
    return (
      <div className="max-w-2xl mx-auto">
        <div className="bg-white shadow rounded-lg p-6">
          <div className="animate-pulse">
            <div className="h-4 bg-gray-200 rounded w-1/4 mb-4"></div>
            <div className="space-y-3">
              <div className="h-4 bg-gray-200 rounded"></div>
              <div className="h-4 bg-gray-200 rounded w-5/6"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white dark:bg-neutral-900 shadow rounded-lg">
        <div className="px-6 py-4 border-b border-neutral-200 dark:border-neutral-800">
          <h2 className="text-lg font-medium text-neutral-900 dark:text-neutral-100">Profile Settings</h2>
          <p className="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
            Update your personal information and account settings.
          </p>
        </div>

        <div className="px-6 py-6">
          {error && (
            <Alert
              type="error"
              message={error}
              onClose={clearError}
              className="mb-6"
            />
          )}

          {successMessage && (
            <Alert
              type="success"
              message={successMessage}
              onClose={() => setSuccessMessage('')}
              className="mb-6"
            />
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Avatar controls: preview + URL or upload */}
            <div className="flex items-center gap-4">
              <div className="h-16 w-16 rounded-full bg-primary-600 text-white flex items-center justify-center overflow-hidden">
                {formData.avatarUrl ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={formData.avatarUrl} alt="avatar" className="h-full w-full object-cover" />
                ) : (
                  <span className="text-xl font-semibold">
                    {(user.full_name || user.username || 'U').charAt(0).toUpperCase()}
                  </span>
                )}
              </div>
              <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">Avatar URL</label>
                  <input
                    type="url"
                    placeholder="https://..."
                    value={formData.avatarUrl}
                    onChange={handleAvatarUrlChange}
                    className="mt-1 w-full px-3 py-2 border border-neutral-300 dark:border-neutral-700 rounded-md bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">Or upload</label>
                  <input
                    type="file"
                    accept="image/*"
                    onChange={async (e) => {
                      const file = e.target.files?.[0];
                      if (!file) return;
                      try {
                        const form = new FormData();
                        form.append('file', file);
                        const token = localStorage.getItem('access_token');
                        const base = getEnvVar.get('VITE_API_URL', '') || '';
                        const url = `${base.replace(/\/$/, '')}/api/users/avatar`;
                        const res = await fetch(url, {
                          method: 'POST',
                          body: form,
                          headers: token ? { Authorization: `Bearer ${token}` } : undefined,
                          credentials: 'include',
                        });
                        if (!res.ok) throw new Error('Upload failed');
                        const updated = await res.json();
                        setFormData((prev) => ({ ...prev, avatarUrl: updated.avatar_url || '' }));
                        // Soft refresh auth user in store so header avatar updates immediately
                        try {
                          const { authService } = await import('../../services/authService');
                          const me = await authService.getCurrentUser();
                          const { useAuthStore } = await import('../../stores/authStore');
                          useAuthStore.getState().setLoading(false);
                          useAuthStore.setState({ user: me });
                        } catch {}
                        setSuccessMessage('Avatar updated');
                      } catch (err) {
                        setErrors((prev) => ({ ...prev, avatar: 'Upload failed. Try a smaller PNG/JPG.' }));
                      }
                    }}
                    className="mt-1 block w-full text-sm text-neutral-700 dark:text-neutral-200 file:mr-4 file:py-2 file:px-3 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100 dark:file:bg-primary-900/30 dark:file:text-primary-300"
                  />
                  <p className="mt-1 text-xs text-neutral-500 dark:text-neutral-400">PNG/JPG/WEBP up to 2MB.</p>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              <Input
                label="Username"
                name="username"
                type="text"
                autoComplete="username"
                required
                value={formData.username}
                onChange={handleInputChange}
                error={errors.username}
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
              />
            </div>

            <Input
              label="Full Name"
              name="fullName"
              type="text"
              autoComplete="name"
              value={formData.fullName}
              onChange={handleInputChange}
              error={errors.fullName}
              placeholder="Enter your full name (optional)"
            />

            <div className="bg-neutral-50 dark:bg-neutral-800 px-4 py-3 rounded-md">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-neutral-400" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <p className="text-sm text-neutral-700 dark:text-neutral-300">
                    <strong>Account created:</strong> {new Date(user.created_at).toLocaleDateString()}
                  </p>
                  <p className="text-sm text-neutral-700 dark:text-neutral-300">
                    <strong>Last updated:</strong> {new Date(user.updated_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-3">
              <Button
                type="button"
                variant="secondary"
                onClick={() => {
                  setFormData({
                    username: user.username,
                    email: user.email,
                    fullName: user.full_name || '',
                    avatarUrl: user.avatar_url || '',
                  });
                  setErrors({});
                  setSuccessMessage('');
                  clearError();
                }}
                disabled={!hasChanges}
              >
                Reset
              </Button>
              <Button
                type="submit"
                isLoading={isLoading}
                disabled={isLoading || !hasChanges}
              >
                {isLoading ? 'Saving...' : 'Save Changes'}
              </Button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};