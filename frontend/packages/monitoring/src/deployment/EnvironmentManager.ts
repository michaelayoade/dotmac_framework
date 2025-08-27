/**
 * Environment-based Deployment Configuration Manager
 * Handles different deployment environments with proper configuration isolation
 */

export interface EnvironmentConfig {
  name: string;
  type: 'development' | 'staging' | 'production' | 'test';
  api: {
    baseUrl: string;
    timeout: number;
    retryAttempts: number;
    rateLimit: {
      requests: number;
      windowMs: number;
    };
  };
  database: {
    url: string;
    poolSize: number;
    ssl: boolean;
    migrations: {
      autoRun: boolean;
      directory: string;
    };
  };
  security: {
    enableCSP: boolean;
    enableHSTS: boolean;
    csrfProtection: boolean;
    sessionSecret: string;
    jwtSecret: string;
    encryptionKey: string;
  };
  monitoring: {
    errorReporting: {
      enabled: boolean;
      dsn?: string;
      sampleRate: number;
    };
    metrics: {
      enabled: boolean;
      endpoint?: string;
      interval: number;
    };
    logging: {
      level: 'debug' | 'info' | 'warn' | 'error';
      structured: boolean;
      destination: 'console' | 'file' | 'remote';
    };
  };
  features: {
    flags: Record<string, boolean>;
    experiments: Record<string, number>; // Percentage rollout
  };
  resources: {
    cdnUrl?: string;
    staticAssets: string;
    uploads: string;
    maxMemory: number;
    maxConcurrency: number;
  };
  notifications: {
    email: {
      enabled: boolean;
      provider: string;
      templates: string;
    };
    push: {
      enabled: boolean;
      vapidKeys?: {
        publicKey: string;
        privateKey: string;
      };
    };
    sms: {
      enabled: boolean;
      provider: string;
      fallback: boolean;
    };
  };
  deployment: {
    strategy: 'blue-green' | 'canary' | 'rolling';
    healthCheck: {
      path: string;
      timeout: number;
      interval: number;
      retries: number;
    };
    rollback: {
      enabled: boolean;
      automatic: boolean;
      errorThreshold: number;
    };
  };
}

export class EnvironmentManager {
  private config: EnvironmentConfig;
  private secrets: Map<string, string> = new Map();
  private featureFlags: Map<string, boolean> = new Map();
  private configValidators: Map<string, (value: any) => boolean> = new Map();

  constructor(environment: string) {
    this.config = this.loadEnvironmentConfig(environment);
    this.setupValidators();
    this.loadSecrets();
    this.initializeFeatureFlags();
    this.validateConfiguration();
  }

  /**
   * Get current environment configuration
   */
  getConfig(): EnvironmentConfig {
    return { ...this.config };
  }

  /**
   * Get configuration value by path
   */
  get<T>(path: string, defaultValue?: T): T {
    const value = this.getNestedValue(this.config, path);
    return value !== undefined ? value : defaultValue;
  }

  /**
   * Check if feature flag is enabled
   */
  isFeatureEnabled(flag: string): boolean {
    // Check experiment rollout first
    if (this.config.features.experiments[flag] !== undefined) {
      const rolloutPercentage = this.config.features.experiments[flag];
      const userId = this.getCurrentUserId();
      return this.isInRollout(userId, flag, rolloutPercentage);
    }

    // Check static feature flags
    return this.featureFlags.get(flag) ?? this.config.features.flags[flag] ?? false;
  }

  /**
   * Enable/disable feature flag at runtime
   */
  setFeatureFlag(flag: string, enabled: boolean): void {
    this.featureFlags.set(flag, enabled);
    console.log(`Feature flag '${flag}' ${enabled ? 'enabled' : 'disabled'}`);
  }

  /**
   * Get secret value (never logs the actual value)
   */
  getSecret(key: string): string | undefined {
    const value = this.secrets.get(key);
    if (!value) {
      console.warn(`Secret '${key}' not found`);
    }
    return value;
  }

  /**
   * Set secret value (for testing or dynamic updates)
   */
  setSecret(key: string, value: string): void {
    this.secrets.set(key, value);
    console.log(`Secret '${key}' updated`);
  }

  /**
   * Validate current configuration
   */
  validateConfiguration(): { isValid: boolean; errors: string[] } {
    const errors: string[] = [];

    // Validate required secrets
    const requiredSecrets = ['sessionSecret', 'jwtSecret', 'encryptionKey'];
    for (const secret of requiredSecrets) {
      if (!this.getSecret(secret)) {
        errors.push(`Missing required secret: ${secret}`);
      }
    }

    // Validate API configuration
    if (!this.config.api.baseUrl) {
      errors.push('API base URL is required');
    }

    try {
      new URL(this.config.api.baseUrl);
    } catch {
      errors.push('Invalid API base URL format');
    }

    // Validate database configuration
    if (!this.config.database.url) {
      errors.push('Database URL is required');
    }

    // Validate monitoring configuration
    if (this.config.monitoring.errorReporting.enabled && !this.config.monitoring.errorReporting.dsn) {
      errors.push('Error reporting DSN is required when error reporting is enabled');
    }

    // Validate deployment configuration
    if (!['blue-green', 'canary', 'rolling'].includes(this.config.deployment.strategy)) {
      errors.push('Invalid deployment strategy');
    }

    // Custom validations
    for (const [path, validator] of this.configValidators.entries()) {
      const value = this.getNestedValue(this.config, path);
      if (!validator(value)) {
        errors.push(`Invalid configuration at path: ${path}`);
      }
    }

    const isValid = errors.length === 0;
    
    if (!isValid) {
      console.error('Configuration validation failed:', errors);
    }

    return { isValid, errors };
  }

  /**
   * Get deployment health status
   */
  async getDeploymentHealth(): Promise<{
    healthy: boolean;
    checks: Array<{
      name: string;
      status: 'pass' | 'fail';
      duration: number;
      error?: string;
    }>;
  }> {
    const checks = [];
    let healthy = true;

    // Database health check
    try {
      const start = Date.now();
      await this.checkDatabaseHealth();
      checks.push({
        name: 'database',
        status: 'pass' as const,
        duration: Date.now() - start,
      });
    } catch (error) {
      healthy = false;
      checks.push({
        name: 'database',
        status: 'fail' as const,
        duration: Date.now() - Date.now(),
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }

    // API health check
    try {
      const start = Date.now();
      await this.checkAPIHealth();
      checks.push({
        name: 'api',
        status: 'pass' as const,
        duration: Date.now() - start,
      });
    } catch (error) {
      healthy = false;
      checks.push({
        name: 'api',
        status: 'fail' as const,
        duration: Date.now() - Date.now(),
        error: error instanceof Error ? error.message : 'Unknown error',
      });
    }

    // Memory usage check
    const memoryUsage = process.memoryUsage();
    const memoryHealthy = memoryUsage.heapUsed < this.config.resources.maxMemory * 0.9;
    checks.push({
      name: 'memory',
      status: memoryHealthy ? 'pass' : 'fail',
      duration: 0,
      error: memoryHealthy ? undefined : `Memory usage: ${Math.round(memoryUsage.heapUsed / 1024 / 1024)}MB`,
    });

    if (!memoryHealthy) healthy = false;

    return { healthy, checks };
  }

  /**
   * Trigger graceful shutdown
   */
  async gracefulShutdown(): Promise<void> {
    console.log('Starting graceful shutdown...');

    // Close database connections
    console.log('Closing database connections...');
    // Implementation would close DB connections

    // Wait for ongoing requests to complete
    console.log('Waiting for ongoing requests...');
    await new Promise(resolve => setTimeout(resolve, 5000));

    // Clean up resources
    console.log('Cleaning up resources...');
    this.secrets.clear();
    this.featureFlags.clear();

    console.log('Graceful shutdown complete');
  }

  /**
   * Hot reload configuration (for development)
   */
  async hotReload(): Promise<void> {
    if (this.config.type !== 'development') {
      console.warn('Hot reload is only available in development environment');
      return;
    }

    console.log('Hot reloading configuration...');
    const newConfig = this.loadEnvironmentConfig(this.config.name);
    
    // Merge with existing config
    this.config = { ...this.config, ...newConfig };
    this.initializeFeatureFlags();
    
    const validation = this.validateConfiguration();
    if (!validation.isValid) {
      console.error('Hot reload failed due to validation errors:', validation.errors);
      return;
    }

    console.log('Configuration hot reloaded successfully');
  }

  /**
   * Export configuration for debugging (secrets redacted)
   */
  exportConfig(): any {
    const exported = JSON.parse(JSON.stringify(this.config));
    
    // Redact sensitive information
    if (exported.security) {
      exported.security.sessionSecret = '[REDACTED]';
      exported.security.jwtSecret = '[REDACTED]';
      exported.security.encryptionKey = '[REDACTED]';
    }

    if (exported.database) {
      exported.database.url = this.redactConnectionString(exported.database.url);
    }

    if (exported.monitoring?.errorReporting?.dsn) {
      exported.monitoring.errorReporting.dsn = '[REDACTED]';
    }

    return exported;
  }

  /**
   * Load environment-specific configuration
   */
  private loadEnvironmentConfig(environment: string): EnvironmentConfig {
    const configs: Record<string, EnvironmentConfig> = {
      development: {
        name: 'development',
        type: 'development',
        api: {
          baseUrl: 'http://localhost:3001',
          timeout: 10000,
          retryAttempts: 2,
          rateLimit: { requests: 1000, windowMs: 60000 },
        },
        database: {
          url: 'postgresql://localhost:5432/dotmac_dev',
          poolSize: 10,
          ssl: false,
          migrations: { autoRun: true, directory: './migrations' },
        },
        security: {
          enableCSP: false,
          enableHSTS: false,
          csrfProtection: true,
          sessionSecret: 'dev-session-secret',
          jwtSecret: 'dev-jwt-secret',
          encryptionKey: 'dev-encryption-key-32-characters',
        },
        monitoring: {
          errorReporting: { enabled: false, sampleRate: 1.0 },
          metrics: { enabled: true, interval: 30000 },
          logging: { level: 'debug', structured: false, destination: 'console' },
        },
        features: {
          flags: { betaFeatures: true, advancedAnalytics: true },
          experiments: { newDashboard: 50 },
        },
        resources: {
          staticAssets: '/static',
          uploads: '/uploads',
          maxMemory: 512 * 1024 * 1024, // 512MB
          maxConcurrency: 100,
        },
        notifications: {
          email: { enabled: false, provider: 'console', templates: '/templates' },
          push: { enabled: false },
          sms: { enabled: false, provider: 'console', fallback: false },
        },
        deployment: {
          strategy: 'rolling',
          healthCheck: { path: '/health', timeout: 5000, interval: 10000, retries: 3 },
          rollback: { enabled: true, automatic: false, errorThreshold: 0.1 },
        },
      },

      staging: {
        name: 'staging',
        type: 'staging',
        api: {
          baseUrl: 'https://api-staging.dotmac.com',
          timeout: 15000,
          retryAttempts: 3,
          rateLimit: { requests: 500, windowMs: 60000 },
        },
        database: {
          url: process.env.STAGING_DATABASE_URL || '',
          poolSize: 20,
          ssl: true,
          migrations: { autoRun: false, directory: './migrations' },
        },
        security: {
          enableCSP: true,
          enableHSTS: true,
          csrfProtection: true,
          sessionSecret: process.env.STAGING_SESSION_SECRET || '',
          jwtSecret: process.env.STAGING_JWT_SECRET || '',
          encryptionKey: process.env.STAGING_ENCRYPTION_KEY || '',
        },
        monitoring: {
          errorReporting: {
            enabled: true,
            dsn: process.env.STAGING_SENTRY_DSN,
            sampleRate: 0.5,
          },
          metrics: { enabled: true, endpoint: 'https://metrics-staging.dotmac.com', interval: 60000 },
          logging: { level: 'info', structured: true, destination: 'remote' },
        },
        features: {
          flags: { betaFeatures: true, advancedAnalytics: false },
          experiments: { newDashboard: 100 },
        },
        resources: {
          cdnUrl: 'https://cdn-staging.dotmac.com',
          staticAssets: '/static',
          uploads: 's3://dotmac-staging-uploads',
          maxMemory: 1024 * 1024 * 1024, // 1GB
          maxConcurrency: 200,
        },
        notifications: {
          email: { enabled: true, provider: 'sendgrid', templates: '/templates' },
          push: { enabled: true, vapidKeys: { publicKey: '', privateKey: '' } },
          sms: { enabled: true, provider: 'twilio', fallback: true },
        },
        deployment: {
          strategy: 'blue-green',
          healthCheck: { path: '/health', timeout: 10000, interval: 30000, retries: 5 },
          rollback: { enabled: true, automatic: true, errorThreshold: 0.05 },
        },
      },

      production: {
        name: 'production',
        type: 'production',
        api: {
          baseUrl: 'https://api.dotmac.com',
          timeout: 30000,
          retryAttempts: 5,
          rateLimit: { requests: 200, windowMs: 60000 },
        },
        database: {
          url: process.env.DATABASE_URL || '',
          poolSize: 50,
          ssl: true,
          migrations: { autoRun: false, directory: './migrations' },
        },
        security: {
          enableCSP: true,
          enableHSTS: true,
          csrfProtection: true,
          sessionSecret: process.env.SESSION_SECRET || '',
          jwtSecret: process.env.JWT_SECRET || '',
          encryptionKey: process.env.ENCRYPTION_KEY || '',
        },
        monitoring: {
          errorReporting: {
            enabled: true,
            dsn: process.env.SENTRY_DSN,
            sampleRate: 0.1,
          },
          metrics: { enabled: true, endpoint: 'https://metrics.dotmac.com', interval: 30000 },
          logging: { level: 'warn', structured: true, destination: 'remote' },
        },
        features: {
          flags: { betaFeatures: false, advancedAnalytics: true },
          experiments: {},
        },
        resources: {
          cdnUrl: 'https://cdn.dotmac.com',
          staticAssets: '/static',
          uploads: 's3://dotmac-production-uploads',
          maxMemory: 2048 * 1024 * 1024, // 2GB
          maxConcurrency: 500,
        },
        notifications: {
          email: { enabled: true, provider: 'sendgrid', templates: '/templates' },
          push: { enabled: true, vapidKeys: { publicKey: process.env.VAPID_PUBLIC_KEY || '', privateKey: process.env.VAPID_PRIVATE_KEY || '' } },
          sms: { enabled: true, provider: 'twilio', fallback: true },
        },
        deployment: {
          strategy: 'canary',
          healthCheck: { path: '/health', timeout: 15000, interval: 60000, retries: 3 },
          rollback: { enabled: true, automatic: true, errorThreshold: 0.01 },
        },
      },
    };

    return configs[environment] || configs.development;
  }

  /**
   * Setup configuration validators
   */
  private setupValidators(): void {
    this.configValidators.set('api.timeout', (value) => 
      typeof value === 'number' && value > 0 && value <= 60000
    );
    
    this.configValidators.set('database.poolSize', (value) => 
      typeof value === 'number' && value > 0 && value <= 100
    );
    
    this.configValidators.set('monitoring.metrics.interval', (value) => 
      typeof value === 'number' && value >= 1000
    );
  }

  /**
   * Load secrets from environment or secure store
   */
  private loadSecrets(): void {
    const secretKeys = [
      'sessionSecret',
      'jwtSecret', 
      'encryptionKey',
      'databaseUrl',
      'sentryDsn',
      'vapidPublicKey',
      'vapidPrivateKey'
    ];

    for (const key of secretKeys) {
      const envKey = key.replace(/([A-Z])/g, '_$1').toUpperCase();
      const value = process.env[envKey] || this.getNestedValue(this.config, `security.${key}`);
      
      if (value) {
        this.secrets.set(key, value);
      }
    }
  }

  /**
   * Initialize feature flags
   */
  private initializeFeatureFlags(): void {
    for (const [flag, enabled] of Object.entries(this.config.features.flags)) {
      this.featureFlags.set(flag, enabled);
    }
  }

  /**
   * Get nested configuration value
   */
  private getNestedValue(obj: any, path: string): any {
    return path.split('.').reduce((current, key) => current?.[key], obj);
  }

  /**
   * Check if user is in experiment rollout
   */
  private isInRollout(userId: string, experiment: string, percentage: number): boolean {
    const hash = this.hashString(`${userId}-${experiment}`);
    return (hash % 100) < percentage;
  }

  /**
   * Get current user ID (implementation specific)
   */
  private getCurrentUserId(): string {
    // This would be implemented to get the current user ID
    // For now, return a placeholder
    return 'anonymous';
  }

  /**
   * Simple hash function for rollout determination
   */
  private hashString(str: string): number {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }
    return Math.abs(hash);
  }

  /**
   * Redact sensitive information from connection strings
   */
  private redactConnectionString(connectionString: string): string {
    return connectionString.replace(/:\/\/[^:]+:[^@]+@/, '://[REDACTED]:[REDACTED]@');
  }

  /**
   * Check database health
   */
  private async checkDatabaseHealth(): Promise<void> {
    // Implementation would check database connectivity
    // For now, simulate the check
    await new Promise(resolve => setTimeout(resolve, 100));
  }

  /**
   * Check API health
   */
  private async checkAPIHealth(): Promise<void> {
    // Implementation would check API endpoint
    // For now, simulate the check
    const response = await fetch(`${this.config.api.baseUrl}/health`, {
      timeout: this.config.deployment.healthCheck.timeout,
    });
    
    if (!response.ok) {
      throw new Error(`API health check failed: ${response.status}`);
    }
  }
}

// Global environment manager instance
let globalEnvironmentManager: EnvironmentManager | null = null;

/**
 * Initialize global environment manager
 */
export function initEnvironmentManager(environment?: string): EnvironmentManager {
  const env = environment || process.env.NODE_ENV || 'development';
  globalEnvironmentManager = new EnvironmentManager(env);
  return globalEnvironmentManager;
}

/**
 * Get global environment manager
 */
export function getEnvironmentManager(): EnvironmentManager | null {
  return globalEnvironmentManager;
}