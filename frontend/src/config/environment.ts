/**
 * Environment configuration management
 */

export interface AppConfig {
  // API Configuration
  apiUrl: string;
  wsUrl: string;
  
  // App Information
  appName: string;
  appVersion: string;
  
  // Feature Flags
  features: {
    enableAnalytics: boolean;
    enableDebugMode: boolean;
    enableOfflineMode: boolean;
    enablePushNotifications: boolean;
    enableExperimentalFeatures: boolean;
  };
  
  // Performance Settings
  performance: {
    queryStaleTime: number;
    queryCacheTime: number;
    retryAttempts: number;
    requestTimeout: number;
  };
  
  // UI Settings
  ui: {
    defaultTheme: 'light' | 'dark' | 'system';
    enableAnimations: boolean;
    compactMode: boolean;
  };
  
  // Security Settings
  security: {
    enableCSP: boolean;
    tokenRefreshThreshold: number; // minutes before expiry to refresh
    maxLoginAttempts: number;
  };
  
  // Development Settings
  development: {
    enableMockData: boolean;
    enableApiLogging: boolean;
    enablePerformanceMonitoring: boolean;
  };
}

// Default configuration
const defaultConfig: AppConfig = {
  apiUrl: 'http://localhost:8000',
  wsUrl: 'ws://localhost:8000',
  appName: 'Multi-Bot RAG Platform',
  appVersion: '1.0.0',
  
  features: {
    enableAnalytics: false,
    enableDebugMode: false,
    enableOfflineMode: false,
    enablePushNotifications: false,
    enableExperimentalFeatures: false,
  },
  
  performance: {
    queryStaleTime: 5 * 60 * 1000, // 5 minutes
    queryCacheTime: 10 * 60 * 1000, // 10 minutes
    retryAttempts: 3,
    requestTimeout: 30000, // 30 seconds
  },
  
  ui: {
    defaultTheme: 'system',
    enableAnimations: true,
    compactMode: false,
  },
  
  security: {
    enableCSP: true,
    tokenRefreshThreshold: 5, // 5 minutes
    maxLoginAttempts: 5,
  },
  
  development: {
    enableMockData: false,
    enableApiLogging: false,
    enablePerformanceMonitoring: false,
  },
};

// Environment-specific overrides
const environmentConfigs: Record<string, DeepPartial<AppConfig>> = {
  development: {
    features: {
      enableDebugMode: true,
      enableExperimentalFeatures: true,
    },
    development: {
      enableApiLogging: true,
      enablePerformanceMonitoring: true,
    },
    security: {
      enableCSP: false, // Disable for easier development
    },
  },
  
  staging: {
    apiUrl: 'https://staging-api.example.com',
    wsUrl: 'wss://staging-api.example.com',
    features: {
      enableAnalytics: true,
      enableDebugMode: true,
    },
    development: {
      enablePerformanceMonitoring: true,
    },
  },
  
  production: {
    apiUrl: 'https://api.example.com',
    wsUrl: 'wss://api.example.com',
    features: {
      enableAnalytics: true,
      enableOfflineMode: true,
      enablePushNotifications: true,
    },
    performance: {
      queryStaleTime: 10 * 60 * 1000, // 10 minutes in production
      queryCacheTime: 30 * 60 * 1000, // 30 minutes in production
    },
    development: {
      enableMockData: false,
      enableApiLogging: false,
      enablePerformanceMonitoring: false,
    },
  },
};

// Deep partial type for nested configuration overrides
type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

// Get environment from Vite
const getEnvironment = (): string => {
  return import.meta.env.MODE || 'development';
};

// Merge configurations
const createConfig = (): AppConfig => {
  const env = getEnvironment();
  const envConfig = environmentConfigs[env] || {};
  
  // Override with environment variables
  const envVarOverrides: DeepPartial<AppConfig> = {
    apiUrl: import.meta.env.VITE_API_URL || defaultConfig.apiUrl,
    wsUrl: import.meta.env.VITE_WS_URL || defaultConfig.wsUrl,
    appName: import.meta.env.VITE_APP_NAME || defaultConfig.appName,
    appVersion: import.meta.env.VITE_APP_VERSION || defaultConfig.appVersion,
  };
  
  // Feature flags from environment
  const featureOverrides: DeepPartial<AppConfig['features']> = {};
  if (import.meta.env.VITE_ENABLE_ANALYTICS !== undefined) {
    featureOverrides.enableAnalytics = import.meta.env.VITE_ENABLE_ANALYTICS === 'true';
  }
  if (import.meta.env.VITE_ENABLE_DEBUG !== undefined || env === 'development') {
    featureOverrides.enableDebugMode = import.meta.env.VITE_ENABLE_DEBUG === 'true' || env === 'development';
  }
  if (import.meta.env.VITE_ENABLE_OFFLINE !== undefined) {
    featureOverrides.enableOfflineMode = import.meta.env.VITE_ENABLE_OFFLINE === 'true';
  }
  if (import.meta.env.VITE_ENABLE_PUSH !== undefined) {
    featureOverrides.enablePushNotifications = import.meta.env.VITE_ENABLE_PUSH === 'true';
  }
  if (import.meta.env.VITE_ENABLE_EXPERIMENTAL !== undefined) {
    featureOverrides.enableExperimentalFeatures = import.meta.env.VITE_ENABLE_EXPERIMENTAL === 'true';
  }
  
  return {
    ...defaultConfig,
    ...envVarOverrides,
    features: {
      ...defaultConfig.features,
      ...envConfig.features,
      ...featureOverrides,
    },
    performance: {
      ...defaultConfig.performance,
      ...envConfig.performance,
    },
    ui: {
      ...defaultConfig.ui,
      ...envConfig.ui,
    },
    security: {
      ...defaultConfig.security,
      ...envConfig.security,
    },
    development: {
      ...defaultConfig.development,
      ...envConfig.development,
    },
  };
};

// Export the configuration
export const config = createConfig();

// Export environment utilities
export const isDevelopment = () => getEnvironment() === 'development';
export const isProduction = () => getEnvironment() === 'production';
export const isStaging = () => getEnvironment() === 'staging';

// Configuration validation
export const validateConfig = (config: AppConfig): string[] => {
  const errors: string[] = [];
  
  if (!config.apiUrl) {
    errors.push('API URL is required');
  }
  
  if (!config.wsUrl) {
    errors.push('WebSocket URL is required');
  }
  
  if (!config.appName) {
    errors.push('App name is required');
  }
  
  if (config.performance.requestTimeout < 1000) {
    errors.push('Request timeout should be at least 1000ms');
  }
  
  if (config.security.tokenRefreshThreshold < 1) {
    errors.push('Token refresh threshold should be at least 1 minute');
  }
  
  return errors;
};

// Runtime configuration updates (for feature flags)
class ConfigManager {
  private static instance: ConfigManager;
  private currentConfig: AppConfig;
  private listeners: ((config: AppConfig) => void)[] = [];
  
  private constructor() {
    this.currentConfig = config;
  }
  
  static getInstance(): ConfigManager {
    if (!ConfigManager.instance) {
      ConfigManager.instance = new ConfigManager();
    }
    return ConfigManager.instance;
  }
  
  getConfig(): AppConfig {
    return { ...this.currentConfig };
  }
  
  updateFeatureFlag(flag: keyof AppConfig['features'], value: boolean): void {
    this.currentConfig = {
      ...this.currentConfig,
      features: {
        ...this.currentConfig.features,
        [flag]: value,
      },
    };
    
    this.notifyListeners();
  }
  
  updateUISettings(settings: Partial<AppConfig['ui']>): void {
    this.currentConfig = {
      ...this.currentConfig,
      ui: {
        ...this.currentConfig.ui,
        ...settings,
      },
    };
    
    this.notifyListeners();
  }
  
  subscribe(listener: (config: AppConfig) => void): () => void {
    this.listeners.push(listener);
    return () => {
      const index = this.listeners.indexOf(listener);
      if (index > -1) {
        this.listeners.splice(index, 1);
      }
    };
  }
  
  private notifyListeners(): void {
    this.listeners.forEach(listener => {
      try {
        listener(this.currentConfig);
      } catch (error) {
        console.error('Error in config listener:', error);
      }
    });
  }
}

export const configManager = ConfigManager.getInstance();

// React hook for using configuration
export const useConfig = () => {
  return configManager.getConfig();
};

// Utility functions
export const getApiUrl = (path: string = ''): string => {
  const baseUrl = config.apiUrl.replace(/\/$/, '');
  const cleanPath = path.replace(/^\//, '');
  return cleanPath ? `${baseUrl}/${cleanPath}` : baseUrl;
};

export const getWsUrl = (path: string = ''): string => {
  const baseUrl = config.wsUrl.replace(/\/$/, '');
  const cleanPath = path.replace(/^\//, '');
  return cleanPath ? `${baseUrl}/${cleanPath}` : baseUrl;
};

// Typed environment helpers
export const getEnvVar = {
  // Core environment variables
  NODE_ENV: (): string => import.meta.env.NODE_ENV || 'development',
  MODE: (): string => import.meta.env.MODE || 'development',
  PROD: (): boolean => import.meta.env.PROD || false,
  DEV: (): boolean => import.meta.env.DEV || true,
  
  // API Configuration
  VITE_API_URL: (): string => import.meta.env.VITE_API_URL || '',
  VITE_WS_URL: (): string => import.meta.env.VITE_WS_URL || '',
  VITE_LOG_ENDPOINT: (): string => import.meta.env.VITE_LOG_ENDPOINT || '',
  
  // App Configuration  
  VITE_APP_NAME: (): string => import.meta.env.VITE_APP_NAME || '',
  VITE_APP_VERSION: (): string => import.meta.env.VITE_APP_VERSION || '',
  
  // Feature Flags
  VITE_ENABLE_ANALYTICS: (): boolean => import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
  VITE_ENABLE_DEBUG: (): boolean => import.meta.env.VITE_ENABLE_DEBUG === 'true',
  VITE_ENABLE_OFFLINE: (): boolean => import.meta.env.VITE_ENABLE_OFFLINE === 'true',
  VITE_ENABLE_PUSH: (): boolean => import.meta.env.VITE_ENABLE_PUSH === 'true',
  VITE_ENABLE_EXPERIMENTAL: (): boolean => import.meta.env.VITE_ENABLE_EXPERIMENTAL === 'true',
  
  // Development flags
  VITE_ENABLE_MOCK_DATA: (): boolean => import.meta.env.VITE_ENABLE_MOCK_DATA === 'true',
  VITE_ENABLE_PERFORMANCE_MONITORING: (): boolean => import.meta.env.VITE_ENABLE_PERFORMANCE_MONITORING === 'true',
  VITE_ENABLE_SERVICE_WORKER: (): boolean => import.meta.env.VITE_ENABLE_SERVICE_WORKER === 'true',
  
  // Custom getter for any environment variable with optional default
  get: <T = string>(key: string, defaultValue?: T): T | string => {
    const value = (import.meta.env as any)[key];
    return value !== undefined ? value : (defaultValue ?? '');
  },
  
  // Type-safe boolean getter
  getBoolean: (key: string, defaultValue: boolean = false): boolean => {
    const value = (import.meta.env as any)[key];
    if (value === undefined) return defaultValue;
    return value === 'true' || value === '1' || value === true;
  },
  
  // Type-safe number getter
  getNumber: (key: string, defaultValue: number = 0): number => {
    const value = (import.meta.env as any)[key];
    if (value === undefined) return defaultValue;
    const parsed = Number(value);
    return isNaN(parsed) ? defaultValue : parsed;
  }
};

// Backwards compatibility exports
export const env = getEnvVar;
export const getEnvironmentVariable = getEnvVar.get;
export const isEnvironment = (envName: string): boolean => getEnvVar.MODE() === envName;

// Debug utilities
export const logConfig = (): void => {
  if (config.features.enableDebugMode) {
    console.group('🔧 Application Configuration');
    console.info('Environment:', getEnvironment());
    console.info('Config:', config);
    console.info('Validation errors:', validateConfig(config));
    console.groupEnd();
  }
};

// Initialize configuration logging in development
if (isDevelopment()) {
  logConfig();
}