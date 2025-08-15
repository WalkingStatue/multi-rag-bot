/**
 * Validation schemas and utilities for React Hook Form
 */
import { z } from 'zod';

// Common validation patterns
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const usernameRegex = /^[a-zA-Z0-9_-]+$/;
const strongPasswordRegex = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]/;

// Common field validations
export const commonValidations = {
  email: z
    .string()
    .min(1, 'Email is required')
    .email('Please enter a valid email address')
    .max(255, 'Email must be less than 255 characters'),

  username: z
    .string()
    .min(1, 'Username is required')
    .min(3, 'Username must be at least 3 characters')
    .max(50, 'Username must be less than 50 characters')
    .regex(usernameRegex, 'Username can only contain letters, numbers, underscores, and hyphens'),

  password: z
    .string()
    .min(1, 'Password is required')
    .min(8, 'Password must be at least 8 characters')
    .max(128, 'Password must be less than 128 characters'),

  strongPassword: z
    .string()
    .min(1, 'Password is required')
    .min(8, 'Password must be at least 8 characters')
    .max(128, 'Password must be less than 128 characters')
    .regex(/(?=.*[a-z])/, 'Password must contain at least one lowercase letter')
    .regex(/(?=.*[A-Z])/, 'Password must contain at least one uppercase letter')
    .regex(/(?=.*\d)/, 'Password must contain at least one number')
    .regex(/(?=.*[@$!%*?&])/, 'Password must contain at least one special character'),

  confirmPassword: (passwordField: string) =>
    z.string().min(1, 'Please confirm your password'),

  fullName: z
    .string()
    .max(255, 'Full name must be less than 255 characters')
    .optional(),

  required: (fieldName: string) =>
    z.string().min(1, `${fieldName} is required`),

  optionalString: z.string().optional(),

  url: z
    .string()
    .url('Please enter a valid URL')
    .optional()
    .or(z.literal('')),

  phoneNumber: z
    .string()
    .regex(/^\+?[\d\s\-\(\)]+$/, 'Please enter a valid phone number')
    .optional()
    .or(z.literal('')),
};

// Authentication schemas
export const loginSchema = z.object({
  username: commonValidations.username,
  password: commonValidations.password,
  rememberMe: z.boolean().optional(),
});

export const registerSchema = z
  .object({
    username: commonValidations.username,
    email: commonValidations.email,
    password: commonValidations.strongPassword,
    confirmPassword: z.string().min(1, 'Please confirm your password'),
    fullName: commonValidations.fullName,
    acceptTerms: z.boolean().refine((val) => val === true, {
      message: 'You must accept the terms and conditions',
    }),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

export const forgotPasswordSchema = z.object({
  email: commonValidations.email,
});

export const resetPasswordSchema = z
  .object({
    token: z.string().min(1, 'Reset token is required'),
    password: commonValidations.strongPassword,
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  });

export const changePasswordSchema = z
  .object({
    currentPassword: commonValidations.password,
    newPassword: commonValidations.strongPassword,
    confirmPassword: z.string().min(1, 'Please confirm your password'),
  })
  .refine((data) => data.newPassword === data.confirmPassword, {
    message: 'Passwords do not match',
    path: ['confirmPassword'],
  })
  .refine((data) => data.currentPassword !== data.newPassword, {
    message: 'New password must be different from current password',
    path: ['newPassword'],
  });

// Profile schemas
export const profileUpdateSchema = z.object({
  fullName: commonValidations.fullName,
  email: commonValidations.email,
  phoneNumber: commonValidations.phoneNumber,
  bio: z.string().max(500, 'Bio must be less than 500 characters').optional(),
  website: commonValidations.url,
  location: z.string().max(100, 'Location must be less than 100 characters').optional(),
});

// Bot schemas
export const botCreateSchema = z.object({
  name: z
    .string()
    .min(1, 'Bot name is required')
    .min(3, 'Bot name must be at least 3 characters')
    .max(100, 'Bot name must be less than 100 characters'),
  description: z
    .string()
    .max(500, 'Description must be less than 500 characters')
    .optional(),
  model: z.string().min(1, 'Please select a model'),
  provider: z.string().min(1, 'Please select a provider'),
  systemPrompt: z
    .string()
    .max(2000, 'System prompt must be less than 2000 characters')
    .optional(),
  temperature: z
    .number()
    .min(0, 'Temperature must be between 0 and 2')
    .max(2, 'Temperature must be between 0 and 2')
    .optional(),
  maxTokens: z
    .number()
    .min(1, 'Max tokens must be at least 1')
    .max(4000, 'Max tokens must be less than 4000')
    .optional(),
  isPublic: z.boolean().optional(),
});

export const botUpdateSchema = botCreateSchema.partial().extend({
  id: z.string().min(1, 'Bot ID is required'),
});

// Document schemas
export const documentUploadSchema = z.object({
  files: z
    .array(z.instanceof(File))
    .min(1, 'Please select at least one file')
    .refine(
      (files) => files.every((file) => file.size <= 10 * 1024 * 1024), // 10MB
      'Each file must be less than 10MB'
    )
    .refine(
      (files) =>
        files.every((file) =>
          ['application/pdf', 'text/plain', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'].includes(
            file.type
          )
        ),
      'Only PDF, TXT, DOC, and DOCX files are allowed'
    ),
  description: z.string().max(500, 'Description must be less than 500 characters').optional(),
});

// API Key schemas
export const apiKeyCreateSchema = z.object({
  provider: z.string().min(1, 'Please select a provider'),
  apiKey: z
    .string()
    .min(1, 'API key is required')
    .min(10, 'API key seems too short')
    .max(500, 'API key is too long'),
  name: z
    .string()
    .max(100, 'Name must be less than 100 characters')
    .optional(),
});

// Chat schemas
export const chatMessageSchema = z.object({
  message: z
    .string()
    .min(1, 'Message cannot be empty')
    .max(4000, 'Message must be less than 4000 characters'),
  sessionId: z.string().optional(),
});

// Collaboration schemas
export const collaboratorInviteSchema = z.object({
  email: commonValidations.email,
  role: z.enum(['viewer', 'editor', 'admin'], {
    errorMap: () => ({ message: 'Please select a valid role' }),
  }),
  message: z.string().max(500, 'Message must be less than 500 characters').optional(),
});

// Search schemas
export const searchSchema = z.object({
  query: z
    .string()
    .min(1, 'Search query is required')
    .min(2, 'Search query must be at least 2 characters')
    .max(200, 'Search query must be less than 200 characters'),
  filters: z
    .object({
      dateFrom: z.date().optional(),
      dateTo: z.date().optional(),
      type: z.string().optional(),
      botId: z.string().optional(),
    })
    .optional(),
});

// Contact/Support schemas
export const contactSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .max(100, 'Name must be less than 100 characters'),
  email: commonValidations.email,
  subject: z
    .string()
    .min(1, 'Subject is required')
    .max(200, 'Subject must be less than 200 characters'),
  message: z
    .string()
    .min(1, 'Message is required')
    .min(10, 'Message must be at least 10 characters')
    .max(2000, 'Message must be less than 2000 characters'),
  category: z.enum(['general', 'technical', 'billing', 'feature-request'], {
    errorMap: () => ({ message: 'Please select a category' }),
  }),
});

// Type exports for use in components
export type LoginFormData = z.infer<typeof loginSchema>;
export type RegisterFormData = z.infer<typeof registerSchema>;
export type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;
export type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;
export type ChangePasswordFormData = z.infer<typeof changePasswordSchema>;
export type ProfileUpdateFormData = z.infer<typeof profileUpdateSchema>;
export type BotCreateFormData = z.infer<typeof botCreateSchema>;
export type BotUpdateFormData = z.infer<typeof botUpdateSchema>;
export type DocumentUploadFormData = z.infer<typeof documentUploadSchema>;
export type ApiKeyCreateFormData = z.infer<typeof apiKeyCreateSchema>;
export type ChatMessageFormData = z.infer<typeof chatMessageSchema>;
export type CollaboratorInviteFormData = z.infer<typeof collaboratorInviteSchema>;
export type SearchFormData = z.infer<typeof searchSchema>;
export type ContactFormData = z.infer<typeof contactSchema>;

// Utility functions
export const validateField = (schema: z.ZodSchema, value: any): string | null => {
  try {
    schema.parse(value);
    return null;
  } catch (error) {
    if (error instanceof z.ZodError) {
      return error.errors[0]?.message || 'Invalid input';
    }
    return 'Validation error';
  }
};

export const validateForm = <T>(schema: z.ZodSchema<T>, data: any): { success: boolean; errors?: Record<string, string>; data?: T } => {
  try {
    const validatedData = schema.parse(data);
    return { success: true, data: validatedData };
  } catch (error) {
    if (error instanceof z.ZodError) {
      const errors: Record<string, string> = {};
      error.errors.forEach((err) => {
        const path = err.path.join('.');
        errors[path] = err.message;
      });
      return { success: false, errors };
    }
    return { success: false, errors: { _form: 'Validation failed' } };
  }
};

// Custom validation helpers
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