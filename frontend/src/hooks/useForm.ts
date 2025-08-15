/**
 * Enhanced form hooks with validation and error handling
 */
import { useForm as useReactHookForm, UseFormProps, UseFormReturn, FieldValues } from 'react-hook-form';
import { useCallback, useEffect } from 'react';
import { validateForm, ValidationSchema, formSchemas } from '../utils/formValidation';
import { useToastHelpers } from '../components/common/Toast';
import { log } from '../utils/logger';

interface UseFormOptions<T extends FieldValues> extends UseFormProps<T> {
  schema?: ValidationSchema;
  onSubmitSuccess?: (data: T) => void;
  onSubmitError?: (error: any) => void;
  enableRealTimeValidation?: boolean;
  logFormEvents?: boolean;
}

interface EnhancedFormReturn<T extends FieldValues> extends UseFormReturn<T> {
  isSubmitting: boolean;
  submitWithValidation: (onSubmit: (data: T) => Promise<void> | void) => (data: T) => Promise<void>;
  validateField: (fieldName: keyof T, value: any) => string | null;
  hasErrors: boolean;
  errorCount: number;
}

export function useForm<T extends FieldValues = FieldValues>(
  options: UseFormOptions<T> = {}
): EnhancedFormReturn<T> {
  const {
    schema,
    onSubmitSuccess,
    onSubmitError,
    enableRealTimeValidation = true,
    logFormEvents = false,
    ...reactHookFormOptions
  } = options;

  const { error: showError } = useToastHelpers();
  
  const form = useReactHookForm<T>({
    mode: enableRealTimeValidation ? 'onChange' : 'onSubmit',
    ...reactHookFormOptions,
  });

  const {
    handleSubmit,
    formState: { errors, isSubmitting },
    setError,
    clearErrors,
    watch,
  } = form;

  // Custom validation function
  const validateField = useCallback((fieldName: keyof T, value: any): string | null => {
    if (!schema || !schema[fieldName as string]) return null;
    
    const formData = form.getValues();
    const rule = schema[fieldName as string];
    
    // Use our custom validation
    const error = validateForm({ [fieldName as string]: value, ...formData }, { [fieldName as string]: rule });
    return error.errors[fieldName as string] || null;
  }, [schema, form]);

  // Enhanced submit handler with validation
  const submitWithValidation = useCallback((onSubmit: (data: T) => Promise<void> | void) => {
    return handleSubmit(async (data: T) => {
      try {
        if (logFormEvents) {
          log.user('Form submission started', { formData: data });
        }

        // Custom validation if schema provided
        if (schema) {
          const validation = validateForm(data, schema);
          if (!validation.isValid) {
            // Set form errors
            Object.entries(validation.errors).forEach(([field, message]) => {
              setError(field as any, { type: 'validation', message });
            });
            
            if (logFormEvents) {
              log.warn('Form validation failed', 'FORM', validation.errors);
            }
            
            showError('Validation Error', 'Please check the form and try again');
            return;
          }
        }

        // Clear any existing errors
        clearErrors();

        // Execute the submit function
        await onSubmit(data);
        
        if (logFormEvents) {
          log.user('Form submission successful');
        }
        
        onSubmitSuccess?.(data);
      } catch (error: any) {
        if (logFormEvents) {
          log.error('Form submission failed', 'FORM', error);
        }
        
        // Handle API validation errors
        if (error?.response?.data?.errors) {
          const apiErrors = error.response.data.errors;
          Object.entries(apiErrors).forEach(([field, message]) => {
            setError(field as any, { type: 'server', message: message as string });
          });
        } else {
          showError('Submission Error', error.message || 'An error occurred while submitting the form');
        }
        
        onSubmitError?.(error);
      }
    });
  }, [handleSubmit, schema, setError, clearErrors, showError, onSubmitSuccess, onSubmitError, logFormEvents]);

  // Real-time validation effect
  useEffect(() => {
    if (!enableRealTimeValidation || !schema) return;

    const subscription = watch((value, { name }) => {
      if (name && schema[name]) {
        const error = validateField(name as keyof T, value[name]);
        if (error) {
          setError(name as any, { type: 'validation', message: error });
        } else {
          clearErrors(name as any);
        }
      }
    });

    return () => subscription.unsubscribe();
  }, [watch, schema, enableRealTimeValidation, validateField, setError, clearErrors]);

  const hasErrors = Object.keys(errors).length > 0;
  const errorCount = Object.keys(errors).length;

  return {
    ...form,
    isSubmitting,
    submitWithValidation,
    validateField,
    hasErrors,
    errorCount,
  };
}

// Specialized form hooks for common forms
export function useLoginForm() {
  return useForm({
    schema: formSchemas.login,
    defaultValues: {
      username: '',
      password: '',
      rememberMe: false,
    } as any,
    logFormEvents: true,
  });
}

export function useRegisterForm() {
  return useForm({
    schema: formSchemas.register,
    defaultValues: {
      username: '',
      email: '',
      password: '',
      confirmPassword: '',
      fullName: '',
      acceptTerms: false,
    } as any,
    logFormEvents: true,
  });
}

export function useForgotPasswordForm() {
  return useForm({
    schema: formSchemas.forgotPassword,
    defaultValues: {
      email: '',
    } as any,
  });
}

export function useResetPasswordForm() {
  return useForm({
    schema: formSchemas.resetPassword,
    defaultValues: {
      token: '',
      password: '',
      confirmPassword: '',
    } as any,
  });
}

export function useChangePasswordForm() {
  return useForm({
    schema: formSchemas.changePassword,
    defaultValues: {
      currentPassword: '',
      newPassword: '',
      confirmPassword: '',
    } as any,
  });
}

export function useProfileUpdateForm(initialData?: any) {
  return useForm({
    schema: formSchemas.profileUpdate,
    defaultValues: {
      fullName: '',
      email: '',
      phoneNumber: '',
      bio: '',
      website: '',
      location: '',
      ...initialData,
    } as any,
  });
}

export function useBotCreateForm() {
  return useForm({
    schema: formSchemas.botCreate,
    defaultValues: {
      name: '',
      description: '',
      model: '',
      provider: '',
      systemPrompt: '',
      temperature: 0.7,
      maxTokens: 1000,
      isPublic: false,
    } as any,
    logFormEvents: true,
  });
}

export function useDocumentUploadForm() {
  return useForm({
    schema: formSchemas.documentUpload,
    defaultValues: {
      files: null,
      description: '',
    } as any,
  });
}

export function useApiKeyCreateForm() {
  return useForm({
    schema: formSchemas.apiKeyCreate,
    defaultValues: {
      provider: '',
      apiKey: '',
      name: '',
    } as any,
  });
}

export function useChatMessageForm() {
  return useForm({
    schema: formSchemas.chatMessage,
    defaultValues: {
      message: '',
      sessionId: '',
    } as any,
    enableRealTimeValidation: false, // Don't validate chat messages in real-time
  });
}

export function useCollaboratorInviteForm() {
  return useForm({
    schema: formSchemas.collaboratorInvite,
    defaultValues: {
      email: '',
      role: 'viewer',
      message: '',
    } as any,
  });
}

export function useSearchForm() {
  return useForm({
    schema: formSchemas.search,
    defaultValues: {
      query: '',
      filters: {},
    } as any,
    enableRealTimeValidation: false,
  });
}

export function useContactForm() {
  return useForm({
    schema: formSchemas.contact,
    defaultValues: {
      name: '',
      email: '',
      subject: '',
      message: '',
      category: 'general',
    } as any,
  });
}

// Form state management hook
export function useFormState<T extends FieldValues>(form: UseFormReturn<T>) {
  const { formState, watch } = form;
  const { isDirty, isValid, isSubmitting, errors } = formState;
  
  const values = watch();
  
  return {
    values,
    isDirty,
    isValid,
    isSubmitting,
    hasErrors: Object.keys(errors).length > 0,
    errorCount: Object.keys(errors).length,
    errors,
    canSubmit: isValid && !isSubmitting,
  };
}

// Form persistence hook
export function useFormPersistence<T extends FieldValues>(
  form: UseFormReturn<T>,
  storageKey: string,
  options: {
    excludeFields?: (keyof T)[];
    debounceMs?: number;
  } = {}
) {
  const { excludeFields = [], debounceMs = 1000 } = options;
  const { watch, setValue } = form;

  // Load saved data on mount
  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) {
        const data = JSON.parse(saved);
        Object.entries(data).forEach(([key, value]) => {
          if (!excludeFields.includes(key as keyof T)) {
            setValue(key as any, value as any);
          }
        });
      }
    } catch (error) {
      log.warn('Failed to load form data from storage', 'FORM', { storageKey, error });
    }
  }, [storageKey, setValue, excludeFields]);

  // Save data on changes
  useEffect(() => {
    const subscription = watch((data) => {
      const timeout = setTimeout(() => {
        try {
          const dataToSave = { ...data } as any;
          excludeFields.forEach(field => {
            delete dataToSave[field as string];
          });
          localStorage.setItem(storageKey, JSON.stringify(dataToSave));
        } catch (error) {
          log.warn('Failed to save form data to storage', 'FORM', { storageKey, error });
        }
      }, debounceMs);

      return () => clearTimeout(timeout);
    });

    return () => subscription.unsubscribe();
  }, [watch, storageKey, excludeFields, debounceMs]);

  const clearSavedData = useCallback(() => {
    localStorage.removeItem(storageKey);
  }, [storageKey]);

  return { clearSavedData };
}