/**
 * Form validation utilities without external dependencies
 */

export interface ValidationRule {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
  min?: number;
  max?: number;
  custom?: (value: any, formData?: any) => string | null;
}

export interface ValidationSchema {
  [key: string]: ValidationRule;
}

export interface ValidationResult {
  isValid: boolean;
  errors: Record<string, string>;
}

// Common validation patterns
export const patterns = {
  email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  username: /^[a-zA-Z0-9_-]+$/,
  strongPassword: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/,
  url: /^https?:\/\/.+/,
  phoneNumber: /^\+?[\d\s\-\(\)]+$/,
};

// Validation functions
export const validateField = (value: any, rule: ValidationRule, formData?: any): string | null => {
  // Required validation
  if (rule.required && (value === undefined || value === null || value === '')) {
    return 'This field is required';
  }

  // Skip other validations if field is empty and not required
  if (!rule.required && (value === undefined || value === null || value === '')) {
    return null;
  }

  // String validations
  if (typeof value === 'string') {
    if (rule.minLength && value.length < rule.minLength) {
      return `Must be at least ${rule.minLength} characters`;
    }

    if (rule.maxLength && value.length > rule.maxLength) {
      return `Must be no more than ${rule.maxLength} characters`;
    }

    if (rule.pattern && !rule.pattern.test(value)) {
      return 'Invalid format';
    }
  }

  // Number validations
  if (typeof value === 'number') {
    if (rule.min !== undefined && value < rule.min) {
      return `Must be at least ${rule.min}`;
    }

    if (rule.max !== undefined && value > rule.max) {
      return `Must be no more than ${rule.max}`;
    }
  }

  // Custom validation
  if (rule.custom) {
    return rule.custom(value, formData);
  }

  return null;
};

export const validateForm = (data: Record<string, any>, schema: ValidationSchema): ValidationResult => {
  const errors: Record<string, string> = {};
  let isValid = true;

  Object.keys(schema).forEach((field) => {
    const value = data[field];
    const rule = schema[field];
    const error = validateField(value, rule, data);
    
    if (error) {
      errors[field] = error;
      isValid = false;
    }
  });

  return { isValid, errors };
};

// Common validation rules
export const commonRules = {
  email: {
    required: true,
    pattern: patterns.email,
    maxLength: 255,
  },

  username: {
    required: true,
    minLength: 3,
    maxLength: 50,
    pattern: patterns.username,
  },

  password: {
    required: true,
    minLength: 8,
    maxLength: 128,
  },

  strongPassword: {
    required: true,
    minLength: 8,
    maxLength: 128,
    custom: (value: string) => {
      if (!/(?=.*[a-z])/.test(value)) {
        return 'Password must contain at least one lowercase letter';
      }
      if (!/(?=.*[A-Z])/.test(value)) {
        return 'Password must contain at least one uppercase letter';
      }
      if (!/(?=.*\d)/.test(value)) {
        return 'Password must contain at least one number';
      }
      if (!/(?=.*[@$!%*?&])/.test(value)) {
        return 'Password must contain at least one special character';
      }
      return null;
    },
  },

  confirmPassword: (passwordField: string = 'password') => ({
    required: true,
    custom: (value: string, formData: any) => {
      if (value !== formData?.[passwordField]) {
        return 'Passwords do not match';
      }
      return null;
    },
  }),

  fullName: {
    maxLength: 255,
  },

  url: {
    pattern: patterns.url,
  },

  phoneNumber: {
    pattern: patterns.phoneNumber,
  },

  required: (fieldName: string) => ({
    required: true,
    custom: (value: any) => {
      if (!value || (typeof value === 'string' && value.trim() === '')) {
        return `${fieldName} is required`;
      }
      return null;
    },
  }),
};

// Predefined form schemas
export const formSchemas = {
  login: {
    username: commonRules.username,
    password: commonRules.password,
  },

  register: {
    username: commonRules.username,
    email: commonRules.email,
    password: commonRules.strongPassword,
    confirmPassword: commonRules.confirmPassword(),
    fullName: commonRules.fullName,
    acceptTerms: {
      required: true,
      custom: (value: boolean) => {
        if (!value) {
          return 'You must accept the terms and conditions';
        }
        return null;
      },
    },
  },

  forgotPassword: {
    email: commonRules.email,
  },

  resetPassword: {
    token: commonRules.required('Reset token'),
    password: commonRules.strongPassword,
    confirmPassword: commonRules.confirmPassword(),
  },

  changePassword: {
    currentPassword: commonRules.password,
    newPassword: commonRules.strongPassword,
    confirmPassword: commonRules.confirmPassword('newPassword'),
  },

  profileUpdate: {
    fullName: commonRules.fullName,
    email: commonRules.email,
    phoneNumber: commonRules.phoneNumber,
    bio: { maxLength: 500 },
    website: commonRules.url,
    location: { maxLength: 100 },
  },

  botCreate: {
    name: {
      required: true,
      minLength: 3,
      maxLength: 100,
    },
    description: { maxLength: 500 },
    model: commonRules.required('Model'),
    provider: commonRules.required('Provider'),
    systemPrompt: { maxLength: 2000 },
    temperature: { min: 0, max: 2 },
    maxTokens: { min: 1, max: 4000 },
  },

  documentUpload: {
    files: {
      required: true,
      custom: (files: FileList | File[]) => {
        if (!files || files.length === 0) {
          return 'Please select at least one file';
        }

        const maxSize = 10 * 1024 * 1024; // 10MB
        const allowedTypes = [
          'application/pdf',
          'text/plain',
          'application/msword',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        ];

        for (let i = 0; i < files.length; i++) {
          const file = files[i];
          if (file.size > maxSize) {
            return `File "${file.name}" is too large. Maximum size is 10MB`;
          }
          if (!allowedTypes.includes(file.type)) {
            return `File "${file.name}" is not supported. Only PDF, TXT, DOC, and DOCX files are allowed`;
          }
        }

        return null;
      },
    },
    description: { maxLength: 500 },
  },

  apiKeyCreate: {
    provider: commonRules.required('Provider'),
    apiKey: {
      required: true,
      minLength: 10,
      maxLength: 500,
    },
    name: { maxLength: 100 },
  },

  chatMessage: {
    message: {
      required: true,
      minLength: 1,
      maxLength: 4000,
    },
  },

  collaboratorInvite: {
    email: commonRules.email,
    role: {
      required: true,
      custom: (value: string) => {
        const validRoles = ['viewer', 'editor', 'admin'];
        if (!validRoles.includes(value)) {
          return 'Please select a valid role';
        }
        return null;
      },
    },
    message: { maxLength: 500 },
  },

  search: {
    query: {
      required: true,
      minLength: 2,
      maxLength: 200,
    },
  },

  contact: {
    name: {
      required: true,
      maxLength: 100,
    },
    email: commonRules.email,
    subject: {
      required: true,
      maxLength: 200,
    },
    message: {
      required: true,
      minLength: 10,
      maxLength: 2000,
    },
    category: {
      required: true,
      custom: (value: string) => {
        const validCategories = ['general', 'technical', 'billing', 'feature-request'];
        if (!validCategories.includes(value)) {
          return 'Please select a category';
        }
        return null;
      },
    },
  },
};

// Type definitions for form data
export interface LoginFormData {
  username: string;
  password: string;
  rememberMe?: boolean;
}

export interface RegisterFormData {
  username: string;
  email: string;
  password: string;
  confirmPassword: string;
  fullName?: string;
  acceptTerms: boolean;
}

export interface ForgotPasswordFormData {
  email: string;
}

export interface ResetPasswordFormData {
  token: string;
  password: string;
  confirmPassword: string;
}

export interface ChangePasswordFormData {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

export interface ProfileUpdateFormData {
  fullName?: string;
  email: string;
  phoneNumber?: string;
  bio?: string;
  website?: string;
  location?: string;
}

export interface BotCreateFormData {
  name: string;
  description?: string;
  model: string;
  provider: string;
  systemPrompt?: string;
  temperature?: number;
  maxTokens?: number;
  isPublic?: boolean;
}

export interface DocumentUploadFormData {
  files: FileList | File[];
  description?: string;
}

export interface ApiKeyCreateFormData {
  provider: string;
  apiKey: string;
  name?: string;
}

export interface ChatMessageFormData {
  message: string;
  sessionId?: string;
}

export interface CollaboratorInviteFormData {
  email: string;
  role: 'viewer' | 'editor' | 'admin';
  message?: string;
}

export interface SearchFormData {
  query: string;
  filters?: {
    dateFrom?: Date;
    dateTo?: Date;
    type?: string;
    botId?: string;
  };
}

export interface ContactFormData {
  name: string;
  email: string;
  subject: string;
  message: string;
  category: 'general' | 'technical' | 'billing' | 'feature-request';
}

// Utility functions
export const createPasswordMatchValidator = (passwordField: string) => {
  return (confirmPassword: string, formData: any) => {
    if (confirmPassword !== formData[passwordField]) {
      return 'Passwords do not match';
    }
    return null;
  };
};

export const createUniqueValidator = (existingValues: string[], fieldName: string) => {
  return (value: string) => {
    if (existingValues.includes(value.toLowerCase())) {
      return `${fieldName} already exists`;
    }
    return null;
  };
};

export const createAsyncValidator = (validatorFn: (value: string) => Promise<boolean>, errorMessage: string) => {
  return async (value: string) => {
    try {
      const isValid = await validatorFn(value);
      return isValid ? null : errorMessage;
    } catch {
      return 'Validation failed';
    }
  };
};

// Real-time validation helper
export const createRealTimeValidator = (schema: ValidationSchema) => {
  return (fieldName: string, value: any, formData?: any) => {
    const rule = schema[fieldName];
    if (!rule) return null;
    return validateField(value, rule, formData);
  };
};