/**
 * Form validation utilities
 */

export interface ValidationRule {
  required?: boolean;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
  custom?: (value: string) => string | null;
}

export interface ValidationRules {
  [key: string]: ValidationRule;
}

export const validateField = (value: string, rule: ValidationRule): string | null => {
  if (rule.required && (!value || value.trim() === '')) {
    return 'This field is required';
  }

  if (value && rule.minLength && value.length < rule.minLength) {
    return `Must be at least ${rule.minLength} characters`;
  }

  if (value && rule.maxLength && value.length > rule.maxLength) {
    return `Must be no more than ${rule.maxLength} characters`;
  }

  if (value && rule.pattern && !rule.pattern.test(value)) {
    return 'Invalid format';
  }

  if (value && rule.custom) {
    return rule.custom(value);
  }

  return null;
};

export const validateForm = (data: Record<string, string>, rules: ValidationRules): Record<string, string> => {
  const errors: Record<string, string> = {};

  Object.keys(rules).forEach((field) => {
    const value = data[field] || '';
    const rule = rules[field];
    const error = validateField(value, rule);
    
    if (error) {
      errors[field] = error;
    }
  });

  return errors;
};

// Common validation rules
export const authValidationRules = {
  username: {
    required: true,
    minLength: 3,
    maxLength: 50,
    pattern: /^[a-zA-Z0-9_-]+$/,
  },
  email: {
    required: true,
    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
  },
  password: {
    required: true,
    minLength: 8,
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
      return null;
    },
  },
  confirmPassword: {
    required: true,
    custom: (value: string, data?: Record<string, string>) => {
      if (data && value !== data.password) {
        return 'Passwords do not match';
      }
      return null;
    },
  },
  fullName: {
    maxLength: 255,
  },
};

export const validateConfirmPassword = (password: string, confirmPassword: string): string | null => {
  if (!confirmPassword) {
    return 'Please confirm your password';
  }
  if (password !== confirmPassword) {
    return 'Passwords do not match';
  }
  return null;
};