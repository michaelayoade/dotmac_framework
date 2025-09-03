/**
 * Production Configuration
 * Environment-specific settings for production deployment
 */

export interface ProductionConfig {
  logging: {
    level: 'error' | 'warn' | 'info' | 'debug';
    enableConsole: boolean;
    enableRemoteLogging: boolean;
    remoteEndpoint?: string;
  };
  api: {
    baseUrl: string;
    timeout: number;
    retryAttempts: number;
    enableMockData: boolean;
  };
  cache: {
    enableCache: boolean;
    ttl: number;
    maxSize: number;
    strategy: 'memory' | 'localStorage' | 'indexedDB';
  };
  maps: {
    defaultProvider: 'leaflet' | 'google' | 'mapbox';
    enableFallback: boolean;
    fallbackProvider: 'leaflet' | 'mock';
    maxZoom: number;
    enableClustering: boolean;
    clusterThreshold: number;
  };
  security: {
    enableCSP: boolean;
    allowedOrigins: string[];
    enableSanitization: boolean;
  };
}

// Production configuration
export const PRODUCTION_CONFIG: ProductionConfig = {
  logging: {
    level: 'error',
    enableConsole: false,
    enableRemoteLogging: true,
    remoteEndpoint: process.env.LOGGING_ENDPOINT || '/api/logs',
  },
  api: {
    baseUrl: process.env.API_BASE_URL || '/api',
    timeout: 30000,
    retryAttempts: 3,
    enableMockData: false,
  },
  cache: {
    enableCache: true,
    ttl: 300000, // 5 minutes
    maxSize: 50, // MB
    strategy: 'indexedDB',
  },
  maps: {
    defaultProvider: 'leaflet',
    enableFallback: true,
    fallbackProvider: 'leaflet',
    maxZoom: 18,
    enableClustering: true,
    clusterThreshold: 100,
  },
  security: {
    enableCSP: true,
    allowedOrigins: ['https://yourdomain.com'],
    enableSanitization: true,
  },
};

// Development configuration
export const DEVELOPMENT_CONFIG: ProductionConfig = {
  ...PRODUCTION_CONFIG,
  logging: {
    level: 'debug',
    enableConsole: true,
    enableRemoteLogging: false,
  },
  api: {
    ...PRODUCTION_CONFIG.api,
    enableMockData: true,
  },
  maps: {
    ...PRODUCTION_CONFIG.maps,
    fallbackProvider: 'mock',
  },
};

// Get configuration based on environment
export function getConfig(): ProductionConfig {
  const env = process.env.NODE_ENV || 'development';
  return env === 'production' ? PRODUCTION_CONFIG : DEVELOPMENT_CONFIG;
}
