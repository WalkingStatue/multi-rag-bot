/**
 * Global type definitions for the Multi-Bot RAG Platform
 */

// Re-export all types from individual modules
export * from './api';
export * from './auth';
export * from './bot';
export * from './chat';
export * from './document';
export * from './user';
export * from './common';
export * from './form';
export * from './routing';
export * from './error';
export * from './offline';

// Global utility types
export type Nullable<T> = T | null;
export type Optional<T> = T | undefined;
export type Maybe<T> = T | null | undefined;

// Brand types for type safety
export type Brand<T, B> = T & { __brand: B };
export type UserId = Brand<string, 'UserId'>;
export type BotId = Brand<string, 'BotId'>;
export type DocumentId = Brand<string, 'DocumentId'>;
export type ConversationId = Brand<string, 'ConversationId'>;
export type MessageId = Brand<string, 'MessageId'>;

// Timestamp types
export type Timestamp = Brand<number, 'Timestamp'>;
export type ISODateString = Brand<string, 'ISODateString'>;

// Status enums
export enum LoadingState {
  IDLE = 'idle',
  LOADING = 'loading',
  SUCCESS = 'success',
  ERROR = 'error',
}

export enum ConnectionStatus {
  CONNECTED = 'connected',
  CONNECTING = 'connecting',
  DISCONNECTED = 'disconnected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error',
}

// Generic response wrapper
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  success: boolean;
  timestamp: ISODateString;
}

// Pagination types
export interface PaginationParams {
  page: number;
  limit: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    page: number;
    limit: number;
    total: number;
    totalPages: number;
    hasNext: boolean;
    hasPrev: boolean;
  };
}

// Search and filter types
export interface SearchParams {
  query?: string;
  filters?: Record<string, any>;
  dateRange?: {
    start: ISODateString;
    end: ISODateString;
  };
}

// File upload types
export interface FileUploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface UploadedFile {
  id: DocumentId;
  name: string;
  size: number;
  type: string;
  url: string;
  uploadedAt: ISODateString;
}

// Theme and UI types
export type ThemeMode = 'light' | 'dark' | 'system';
export type ColorScheme = 'blue' | 'green' | 'purple' | 'orange' | 'red';

export interface ThemeConfig {
  mode: ThemeMode;
  colorScheme: ColorScheme;
  fontSize: 'small' | 'medium' | 'large';
  compactMode: boolean;
}

// Notification types
export type NotificationType = 'info' | 'success' | 'warning' | 'error';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  timestamp: Timestamp;
  read: boolean;
  persistent?: boolean;
  action?: {
    label: string;
    onClick: () => void;
  };
}

// Environment types
export interface EnvironmentConfig {
  NODE_ENV: 'development' | 'production' | 'test';
  VITE_API_URL: string;
  VITE_WS_URL: string;
  VITE_APP_NAME: string;
  VITE_APP_VERSION: string;
  VITE_ENABLE_ANALYTICS: boolean;
  VITE_ENABLE_LOGGING: boolean;
  VITE_LOG_LEVEL: 'debug' | 'info' | 'warn' | 'error';
}

// Component prop types
export interface BaseComponentProps {
  className?: string;
  children?: React.ReactNode;
  testId?: string;
}

export interface LoadingProps extends BaseComponentProps {
  loading?: boolean;
  error?: string | null;
  retry?: () => void;
}

// Event handler types
export type EventHandler<T = Event> = (event: T) => void;
export type AsyncEventHandler<T = Event> = (event: T) => Promise<void>;

// Utility function types
export type Predicate<T> = (value: T) => boolean;
export type Mapper<T, U> = (value: T) => U;
export type Reducer<T, U> = (accumulator: U, current: T) => U;

// Promise utility types
export type PromiseValue<T> = T extends Promise<infer U> ? U : T;
export type AsyncReturnType<T extends (...args: any) => Promise<any>> = T extends (
  ...args: any
) => Promise<infer R>
  ? R
  : any;

// Object utility types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type DeepRequired<T> = {
  [P in keyof T]-?: T[P] extends object ? DeepRequired<T[P]> : T[P];
};

export type PickByType<T, U> = {
  [K in keyof T as T[K] extends U ? K : never]: T[K];
};

export type OmitByType<T, U> = {
  [K in keyof T as T[K] extends U ? never : K]: T[K];
};

// Function overload types
export interface Overloaded {
  <T>(value: T[]): T[];
  <T>(value: T): T;
}

// Conditional types
export type NonEmptyArray<T> = [T, ...T[]];
export type AtLeastOne<T> = [T, ...T[]];

// String literal utility types
export type StringLiteral<T> = T extends string ? (string extends T ? never : T) : never;

// React component types
export type ComponentWithChildren<P = {}> = React.FC<P & { children: React.ReactNode }>;
export type ComponentWithOptionalChildren<P = {}> = React.FC<P & { children?: React.ReactNode }>;

// Hook return types
export interface UseAsyncState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  execute: (...args: any[]) => Promise<void>;
  reset: () => void;
}

export interface UseToggleReturn {
  value: boolean;
  toggle: () => void;
  setTrue: () => void;
  setFalse: () => void;
  setValue: (value: boolean) => void;
}

// Storage types
export interface StorageItem<T = any> {
  value: T;
  timestamp: Timestamp;
  expiresAt?: Timestamp;
}

// Validation types
export interface ValidationRule<T = any> {
  required?: boolean;
  min?: number;
  max?: number;
  pattern?: RegExp;
  custom?: (value: T) => boolean | string;
  message?: string;
}

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

// Performance monitoring types
export interface PerformanceMetric {
  name: string;
  value: number;
  unit: 'ms' | 'bytes' | 'count';
  timestamp: Timestamp;
  tags?: Record<string, string>;
}

// Feature flag types
export interface FeatureFlag {
  key: string;
  enabled: boolean;
  description?: string;
  rolloutPercentage?: number;
  conditions?: Record<string, any>;
}

// Analytics types
export interface AnalyticsEvent {
  name: string;
  properties?: Record<string, any>;
  timestamp: Timestamp;
  userId?: UserId;
  sessionId?: string;
}

// Accessibility types
export interface A11yProps {
  'aria-label'?: string;
  'aria-labelledby'?: string;
  'aria-describedby'?: string;
  'aria-expanded'?: boolean;
  'aria-hidden'?: boolean;
  role?: string;
  tabIndex?: number;
}

// Export default type collection
export default {
  LoadingState,
  ConnectionStatus,
};