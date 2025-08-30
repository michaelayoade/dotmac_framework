/**
 * Rate Limiting Service
 *
 * Implements client-side rate limiting for authentication attempts and API requests
 * Provides protection against brute force attacks and excessive API usage
 */

interface RateLimitConfig {
  maxAttempts: number;
  windowMs: number;
  blockDurationMs: number;
  progressive?: boolean;
}

interface RateLimitAttempt {
  timestamp: number;
  success: boolean;
  ip?: string;
}

interface RateLimitStatus {
  allowed: boolean;
  remaining: number;
  resetTime: Date;
  retryAfter?: number;
}

interface RateLimitData {
  attempts: RateLimitAttempt[];
  blockedUntil?: number;
  consecutiveFailures: number;
}

export class RateLimiter {
  private storage: Map<string, RateLimitData> = new Map();
  private configs: Map<string, RateLimitConfig> = new Map();

  constructor() {
    this.setupDefaultConfigs();
    this.loadFromStorage();
  }

  /**
   * Setup default rate limiting configurations
   */
  private setupDefaultConfigs(): void {
    this.configs.set('login', {
      maxAttempts: 5,
      windowMs: 15 * 60 * 1000, // 15 minutes
      blockDurationMs: 30 * 60 * 1000, // 30 minutes
      progressive: true,
    });

    this.configs.set('password_reset', {
      maxAttempts: 3,
      windowMs: 60 * 60 * 1000, // 1 hour
      blockDurationMs: 2 * 60 * 60 * 1000, // 2 hours
      progressive: false,
    });

    this.configs.set('mfa_verification', {
      maxAttempts: 5,
      windowMs: 10 * 60 * 1000, // 10 minutes
      blockDurationMs: 15 * 60 * 1000, // 15 minutes
      progressive: false,
    });

    this.configs.set('api_request', {
      maxAttempts: 100,
      windowMs: 60 * 1000, // 1 minute
      blockDurationMs: 60 * 1000, // 1 minute
      progressive: false,
    });

    this.configs.set('profile_update', {
      maxAttempts: 10,
      windowMs: 60 * 1000, // 1 minute
      blockDurationMs: 5 * 60 * 1000, // 5 minutes
      progressive: false,
    });
  }

  /**
   * Set custom rate limit configuration
   */
  setConfig(key: string, config: RateLimitConfig): void {
    this.configs.set(key, config);
  }

  /**
   * Check if action is allowed under rate limits
   */
  async checkLimit(key: string, identifier?: string): Promise<RateLimitStatus> {
    const config = this.configs.get(key);
    if (!config) {
      throw new Error(`No rate limit configuration found for key: ${key}`);
    }

    const storageKey = this.getStorageKey(key, identifier);
    const data = this.storage.get(storageKey) || {
      attempts: [],
      consecutiveFailures: 0,
    };

    const now = Date.now();

    // Check if currently blocked
    if (data.blockedUntil && now < data.blockedUntil) {
      return {
        allowed: false,
        remaining: 0,
        resetTime: new Date(data.blockedUntil),
        retryAfter: Math.ceil((data.blockedUntil - now) / 1000),
      };
    }

    // Clean up old attempts outside the window
    const windowStart = now - config.windowMs;
    data.attempts = data.attempts.filter(attempt => attempt.timestamp > windowStart);

    // Check if within rate limit
    const attemptsInWindow = data.attempts.length;
    const remaining = Math.max(0, config.maxAttempts - attemptsInWindow);

    if (attemptsInWindow >= config.maxAttempts) {
      // Calculate block duration (progressive if enabled)
      const blockDuration = config.progressive
        ? this.calculateProgressiveBlockDuration(config.blockDurationMs, data.consecutiveFailures)
        : config.blockDurationMs;

      data.blockedUntil = now + blockDuration;
      this.storage.set(storageKey, data);
      this.saveToStorage();

      return {
        allowed: false,
        remaining: 0,
        resetTime: new Date(data.blockedUntil),
        retryAfter: Math.ceil(blockDuration / 1000),
      };
    }

    return {
      allowed: true,
      remaining,
      resetTime: new Date(now + config.windowMs),
    };
  }

  /**
   * Record an attempt (success or failure)
   */
  async recordAttempt(key: string, success: boolean, identifier?: string): Promise<void> {
    const config = this.configs.get(key);
    if (!config) return;

    const storageKey = this.getStorageKey(key, identifier);
    const data = this.storage.get(storageKey) || {
      attempts: [],
      consecutiveFailures: 0,
    };

    const now = Date.now();
    const attempt: RateLimitAttempt = {
      timestamp: now,
      success,
      ip: await this.getClientIP(),
    };

    data.attempts.push(attempt);

    // Update consecutive failure count
    if (success) {
      data.consecutiveFailures = 0;
      // Clear block if successful attempt
      if (data.blockedUntil) {
        delete data.blockedUntil;
      }
    } else {
      data.consecutiveFailures++;
    }

    this.storage.set(storageKey, data);
    this.saveToStorage();
  }

  /**
   * Get current status for a rate limit key
   */
  async getStatus(key: string, identifier?: string): Promise<RateLimitStatus | null> {
    const config = this.configs.get(key);
    if (!config) return null;

    const storageKey = this.getStorageKey(key, identifier);
    const data = this.storage.get(storageKey);
    if (!data) {
      return {
        allowed: true,
        remaining: config.maxAttempts,
        resetTime: new Date(Date.now() + config.windowMs),
      };
    }

    const now = Date.now();

    // Check if blocked
    if (data.blockedUntil && now < data.blockedUntil) {
      return {
        allowed: false,
        remaining: 0,
        resetTime: new Date(data.blockedUntil),
        retryAfter: Math.ceil((data.blockedUntil - now) / 1000),
      };
    }

    // Calculate remaining attempts in current window
    const windowStart = now - config.windowMs;
    const attemptsInWindow = data.attempts.filter(
      attempt => attempt.timestamp > windowStart
    ).length;

    return {
      allowed: attemptsInWindow < config.maxAttempts,
      remaining: Math.max(0, config.maxAttempts - attemptsInWindow),
      resetTime: new Date(now + config.windowMs),
    };
  }

  /**
   * Reset rate limits for a specific key
   */
  async resetLimit(key: string, identifier?: string): Promise<void> {
    const storageKey = this.getStorageKey(key, identifier);
    this.storage.delete(storageKey);
    this.saveToStorage();
  }

  /**
   * Clear all rate limit data (useful for testing)
   */
  async clearAll(): Promise<void> {
    this.storage.clear();
    this.saveToStorage();
  }

  /**
   * Get rate limit statistics
   */
  async getStatistics(key: string): Promise<{
    totalAttempts: number;
    successfulAttempts: number;
    failedAttempts: number;
    blockedClients: number;
    averageAttemptsPerWindow: number;
  }> {
    const config = this.configs.get(key);
    if (!config) {
      return {
        totalAttempts: 0,
        successfulAttempts: 0,
        failedAttempts: 0,
        blockedClients: 0,
        averageAttemptsPerWindow: 0,
      };
    }

    let totalAttempts = 0;
    let successfulAttempts = 0;
    let failedAttempts = 0;
    let blockedClients = 0;
    let clientsWithAttempts = 0;

    const now = Date.now();
    const windowStart = now - config.windowMs;

    // Iterate through all storage keys for this rate limit key
    for (const [storageKey, data] of this.storage.entries()) {
      if (storageKey.startsWith(`${key}:`)) {
        clientsWithAttempts++;

        if (data.blockedUntil && now < data.blockedUntil) {
          blockedClients++;
        }

        const recentAttempts = data.attempts.filter(
          attempt => attempt.timestamp > windowStart
        );

        totalAttempts += recentAttempts.length;
        successfulAttempts += recentAttempts.filter(a => a.success).length;
        failedAttempts += recentAttempts.filter(a => !a.success).length;
      }
    }

    return {
      totalAttempts,
      successfulAttempts,
      failedAttempts,
      blockedClients,
      averageAttemptsPerWindow: clientsWithAttempts > 0 ? totalAttempts / clientsWithAttempts : 0,
    };
  }

  /**
   * Check if client is currently blocked
   */
  async isBlocked(key: string, identifier?: string): Promise<boolean> {
    const storageKey = this.getStorageKey(key, identifier);
    const data = this.storage.get(storageKey);

    if (!data || !data.blockedUntil) return false;

    const now = Date.now();
    return now < data.blockedUntil;
  }

  /**
   * Get time until unblocked (in milliseconds)
   */
  async getTimeUntilUnblocked(key: string, identifier?: string): Promise<number> {
    const storageKey = this.getStorageKey(key, identifier);
    const data = this.storage.get(storageKey);

    if (!data || !data.blockedUntil) return 0;

    const now = Date.now();
    return Math.max(0, data.blockedUntil - now);
  }

  /**
   * Calculate progressive block duration based on consecutive failures
   */
  private calculateProgressiveBlockDuration(baseDuration: number, consecutiveFailures: number): number {
    // Exponential backoff: base * 2^(failures - 1)
    const multiplier = Math.pow(2, Math.min(consecutiveFailures - 1, 10)); // Cap at 2^10
    return Math.min(baseDuration * multiplier, 24 * 60 * 60 * 1000); // Max 24 hours
  }

  /**
   * Generate storage key for rate limit data
   */
  private getStorageKey(key: string, identifier?: string): string {
    const id = identifier || this.getDefaultIdentifier();
    return `${key}:${id}`;
  }

  /**
   * Get default identifier (IP address or fingerprint)
   */
  private getDefaultIdentifier(): string {
    if (typeof window === 'undefined') return 'server';

    // Create a simple browser fingerprint
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');
    if (ctx) {
      ctx.textBaseline = 'top';
      ctx.font = '14px Arial';
      ctx.fillText('Rate limit fingerprint', 2, 2);
    }

    const fingerprint = [
      navigator.userAgent,
      navigator.language,
      screen.width + 'x' + screen.height,
      new Date().getTimezoneOffset(),
      canvas.toDataURL(),
    ].join('|');

    // Simple hash function
    let hash = 0;
    for (let i = 0; i < fingerprint.length; i++) {
      const char = fingerprint.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32-bit integer
    }

    return hash.toString(36);
  }

  /**
   * Get client IP address (placeholder - would be handled by server)
   */
  private async getClientIP(): Promise<string> {
    try {
      // In a real implementation, this would be provided by the server
      // or obtained through a service like ipinfo.io
      return 'client_ip_placeholder';
    } catch {
      return 'unknown';
    }
  }

  /**
   * Load rate limit data from localStorage
   */
  private loadFromStorage(): void {
    if (typeof window === 'undefined') return;

    try {
      const stored = localStorage.getItem('rate_limit_data');
      if (stored) {
        const data = JSON.parse(stored);
        this.storage = new Map(Object.entries(data));

        // Clean up expired data
        this.cleanupExpiredData();
      }
    } catch (error) {
      console.error('Failed to load rate limit data:', error);
    }
  }

  /**
   * Save rate limit data to localStorage
   */
  private saveToStorage(): void {
    if (typeof window === 'undefined') return;

    try {
      const data = Object.fromEntries(this.storage.entries());
      localStorage.setItem('rate_limit_data', JSON.stringify(data));
    } catch (error) {
      console.error('Failed to save rate limit data:', error);
    }
  }

  /**
   * Clean up expired rate limit data
   */
  private cleanupExpiredData(): void {
    const now = Date.now();
    const expiredKeys: string[] = [];

    for (const [storageKey, data] of this.storage.entries()) {
      const [configKey] = storageKey.split(':');
      const config = this.configs.get(configKey!);

      if (!config) {
        expiredKeys.push(storageKey);
        continue;
      }

      // Remove if blocked period has passed and no recent attempts
      if (data.blockedUntil && now > data.blockedUntil) {
        const windowStart = now - config.windowMs;
        const hasRecentAttempts = data.attempts.some(attempt => attempt.timestamp > windowStart);

        if (!hasRecentAttempts) {
          expiredKeys.push(storageKey);
        }
      }
    }

    // Remove expired entries
    expiredKeys.forEach(key => this.storage.delete(key));
  }

  /**
   * Start periodic cleanup of expired data
   */
  startPeriodicCleanup(intervalMs: number = 5 * 60 * 1000): () => void {
    const interval = setInterval(() => {
      this.cleanupExpiredData();
      this.saveToStorage();
    }, intervalMs);

    return () => clearInterval(interval);
  }
}
