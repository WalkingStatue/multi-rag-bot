/**
 * Enhanced form field component with React Hook Form integration
 */
import React from 'react';
import { useController, Control, FieldPath, FieldValues } from 'react-hook-form';
import { Input } from '../common/Input';
import { InlineError } from '../common/ErrorDisplay';

interface FormFieldProps<T extends FieldValues> {
  name: FieldPath<T>;
  control: Control<T>;
  label: string;
  type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url';
  placeholder?: string;
  description?: string;
  required?: boolean;
  disabled?: boolean;
  autoComplete?: string;
  className?: string;
}

export function FormField<T extends FieldValues>({
  name,
  control,
  label,
  type = 'text',
  placeholder,
  description,
  required = false,
  disabled = false,
  autoComplete,
  className = '',
}: FormFieldProps<T>) {
  const {
    field,
    fieldState: { error, invalid },
  } = useController({
    name,
    control,
  });

  return (
    <div className={`space-y-1 ${className}`}>
      <label htmlFor={name} className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      
      {description && (
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          {description}
        </p>
      )}
      
      <Input
        {...field}
        id={name}
        type={type}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete={autoComplete}
        error={error?.message}
        aria-invalid={invalid}
        aria-describedby={error ? `${name}-error` : undefined}
      />
      
      {error && (
        <div id={`${name}-error`} role="alert">
          <InlineError error={error.message || 'Invalid input'} />
        </div>
      )}
    </div>
  );
}

/**
 * Textarea form field component
 */
interface TextareaFieldProps<T extends FieldValues> extends Omit<FormFieldProps<T>, 'type'> {
  rows?: number;
  maxLength?: number;
  resize?: 'none' | 'vertical' | 'horizontal' | 'both';
}

export function TextareaField<T extends FieldValues>({
  name,
  control,
  label,
  placeholder,
  description,
  required = false,
  disabled = false,
  rows = 3,
  maxLength,
  resize = 'vertical',
  className = '',
}: TextareaFieldProps<T>) {
  const {
    field,
    fieldState: { error, invalid },
  } = useController({
    name,
    control,
  });

  return (
    <div className={`space-y-1 ${className}`}>
      <label htmlFor={name} className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      
      {description && (
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          {description}
        </p>
      )}
      
      <textarea
        {...field}
        id={name}
        rows={rows}
        maxLength={maxLength}
        placeholder={placeholder}
        disabled={disabled}
        className={`
          block w-full rounded-md border-neutral-300 dark:border-neutral-600 
          shadow-sm focus:border-primary-500 focus:ring-primary-500 
          dark:bg-neutral-800 dark:text-neutral-100
          ${resize === 'none' ? 'resize-none' : ''}
          ${resize === 'vertical' ? 'resize-y' : ''}
          ${resize === 'horizontal' ? 'resize-x' : ''}
          ${invalid ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
          ${disabled ? 'bg-neutral-50 dark:bg-neutral-700 cursor-not-allowed' : ''}
        `}
        aria-invalid={invalid}
        aria-describedby={error ? `${name}-error` : undefined}
      />
      
      {maxLength && (
        <div className="text-right text-xs text-neutral-500 dark:text-neutral-400">
          {field.value?.length || 0}/{maxLength}
        </div>
      )}
      
      {error && (
        <div id={`${name}-error`} role="alert">
          <InlineError error={error.message || 'Invalid input'} />
        </div>
      )}
    </div>
  );
}

/**
 * Select form field component
 */
interface SelectFieldProps<T extends FieldValues> extends Omit<FormFieldProps<T>, 'type'> {
  options: Array<{ value: string; label: string; disabled?: boolean }>;
  emptyOption?: string;
}

export function SelectField<T extends FieldValues>({
  name,
  control,
  label,
  options,
  emptyOption,
  description,
  required = false,
  disabled = false,
  className = '',
}: SelectFieldProps<T>) {
  const {
    field,
    fieldState: { error, invalid },
  } = useController({
    name,
    control,
  });

  return (
    <div className={`space-y-1 ${className}`}>
      <label htmlFor={name} className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      
      {description && (
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          {description}
        </p>
      )}
      
      <select
        {...field}
        id={name}
        disabled={disabled}
        className={`
          block w-full rounded-md border-neutral-300 dark:border-neutral-600 
          shadow-sm focus:border-primary-500 focus:ring-primary-500 
          dark:bg-neutral-800 dark:text-neutral-100
          ${invalid ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : ''}
          ${disabled ? 'bg-neutral-50 dark:bg-neutral-700 cursor-not-allowed' : ''}
        `}
        aria-invalid={invalid}
        aria-describedby={error ? `${name}-error` : undefined}
      >
        {emptyOption && (
          <option value="">{emptyOption}</option>
        )}
        {options.map((option) => (
          <option
            key={option.value}
            value={option.value}
            disabled={option.disabled}
          >
            {option.label}
          </option>
        ))}
      </select>
      
      {error && (
        <div id={`${name}-error`} role="alert">
          <InlineError error={error.message || 'Invalid selection'} />
        </div>
      )}
    </div>
  );
}

/**
 * Checkbox form field component
 */
interface CheckboxFieldProps<T extends FieldValues> extends Omit<FormFieldProps<T>, 'type' | 'placeholder'> {
  checkboxLabel?: string;
}

export function CheckboxField<T extends FieldValues>({
  name,
  control,
  label,
  checkboxLabel,
  description,
  disabled = false,
  className = '',
}: CheckboxFieldProps<T>) {
  const {
    field,
    fieldState: { error, invalid },
  } = useController({
    name,
    control,
  });

  return (
    <div className={`space-y-1 ${className}`}>
      {label && (
        <div className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
          {label}
        </div>
      )}
      
      {description && (
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          {description}
        </p>
      )}
      
      <div className="flex items-center">
        <input
          {...field}
          id={name}
          type="checkbox"
          checked={field.value || false}
          disabled={disabled}
          className={`
            h-4 w-4 text-primary-600 focus:ring-primary-500 border-neutral-300 
            dark:border-neutral-600 rounded dark:bg-neutral-800
            ${disabled ? 'cursor-not-allowed opacity-50' : ''}
          `}
          aria-invalid={invalid}
          aria-describedby={error ? `${name}-error` : undefined}
        />
        {checkboxLabel && (
          <label htmlFor={name} className="ml-2 block text-sm text-neutral-900 dark:text-neutral-100">
            {checkboxLabel}
          </label>
        )}
      </div>
      
      {error && (
        <div id={`${name}-error`} role="alert">
          <InlineError error={error.message || 'Invalid selection'} />
        </div>
      )}
    </div>
  );
}

/**
 * File upload form field component
 */
interface FileFieldProps<T extends FieldValues> extends Omit<FormFieldProps<T>, 'type' | 'placeholder'> {
  accept?: string;
  multiple?: boolean;
  maxSize?: number; // in bytes
  onFileSelect?: (files: FileList | null) => void;
}

export function FileField<T extends FieldValues>({
  name,
  control,
  label,
  accept,
  multiple = false,
  maxSize,
  description,
  required = false,
  disabled = false,
  onFileSelect,
  className = '',
}: FileFieldProps<T>) {
  const {
    field: { onChange, value, ...field },
    fieldState: { error, invalid },
  } = useController({
    name,
    control,
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    
    // Validate file size if specified
    if (files && maxSize) {
      for (let i = 0; i < files.length; i++) {
        if (files[i].size > maxSize) {
          // You might want to set a custom error here
          return;
        }
      }
    }
    
    onChange(files);
    onFileSelect?.(files);
  };

  return (
    <div className={`space-y-1 ${className}`}>
      <label htmlFor={name} className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      
      {description && (
        <p className="text-sm text-neutral-500 dark:text-neutral-400">
          {description}
          {maxSize && (
            <span className="block">
              Max file size: {(maxSize / 1024 / 1024).toFixed(1)}MB
            </span>
          )}
        </p>
      )}
      
      <input
        {...field}
        id={name}
        type="file"
        accept={accept}
        multiple={multiple}
        disabled={disabled}
        onChange={handleFileChange}
        className={`
          block w-full text-sm text-neutral-500 dark:text-neutral-400
          file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0
          file:text-sm file:font-medium file:bg-primary-50 file:text-primary-700
          hover:file:bg-primary-100 dark:file:bg-primary-900 dark:file:text-primary-300
          ${disabled ? 'cursor-not-allowed opacity-50' : ''}
        `}
        aria-invalid={invalid}
        aria-describedby={error ? `${name}-error` : undefined}
      />
      
      {error && (
        <div id={`${name}-error`} role="alert">
          <InlineError error={error.message || 'Invalid file'} />
        </div>
      )}
    </div>
  );
}