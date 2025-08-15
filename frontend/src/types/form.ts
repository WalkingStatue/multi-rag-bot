/**
 * Form-related type definitions
 */

export interface FormField<T = any> {
  name: string;
  label: string;
  type: FormFieldType;
  value: T;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  validation?: ValidationRule<T>[];
  options?: FormFieldOption[];
}

export type FormFieldType = 
  | 'text' 
  | 'email' 
  | 'password' 
  | 'number' 
  | 'textarea' 
  | 'select' 
  | 'checkbox' 
  | 'radio' 
  | 'file' 
  | 'date' 
  | 'datetime-local';

export interface FormFieldOption {
  label: string;
  value: string | number;
  disabled?: boolean;
}

export interface ValidationRule<T = any> {
  required?: boolean;
  min?: number;
  max?: number;
  minLength?: number;
  maxLength?: number;
  pattern?: RegExp;
  custom?: (value: T) => boolean | string;
  message?: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

export interface FormState<T = Record<string, any>> {
  values: T;
  errors: Record<keyof T, string[]>;
  touched: Record<keyof T, boolean>;
  isSubmitting: boolean;
  isValid: boolean;
}

export interface FormConfig<T = Record<string, any>> {
  initialValues: T;
  validationSchema?: Record<keyof T, ValidationRule[]>;
  onSubmit: (values: T) => Promise<void> | void;
  onValidate?: (values: T) => Record<keyof T, string[]>;
}