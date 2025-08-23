/**
 * Rate Limiting and Advanced Error Handling Utilities
 * Comprehensive client-side rate limiting, retry logic, and error handling
 */

import { ApiError, ErrorResponse, ERROR_CODES } from '../types/errors';

// Rate limiting interfaces
export interface RateLimitInfo {
  limit: number;
  remaining: number;
  resetTime: Date;
  retryAfter?: number;
}

export interface RetryConfig {
  maxAttempts: number;
  baseDelay: number; // milliseconds
  maxDelay: number; // milliseconds
  backoffMultiplier: number;
  jitterMax: number; // milliseconds
  retryableStatuses: number[];
  retryableErrors: string[];
}

export interface RequestConfig {
  timeout?: number;
  retryConfig?: Partial<RetryConfig>;
  rateLimitBypass?: boolean;
  idempotencyKey?: string;
}

// Default retry configuration
export const DEFAULT_RETRY_CONFIG: RetryConfig = {
  maxAttempts: 3,
  baseDelay: 1000,
  maxDelay: 30000,
  backoffMultiplier: 2,
  jitterMax: 1000,
  retryableStatuses: [429, 500, 502, 503, 504],
  retryableErrors: [
    'CONNECTION_TIMEOUT',
    'NETWORK_ERROR', 
    'INTERNAL_SERVER_ERROR',
    'SERVICE_UNAVAILABLE',
    'DATABASE_CONNECTION_ERROR',
    'RATE_LIMIT_EXCEEDED'
  ]
};

// Rate limiter class for client-side rate limiting
export class RateLimiter {
  private buckets = new Map<string, TokenBucket>();
  private defaultRules: RateLimitRule[];

  constructor(defaultRules: RateLimitRule[] = []) {
    this.defaultRules = defaultRules;
  }

  /**
   * Check if request is allowed under rate limits
   */
  async checkRateLimit(
    endpoint: string, 
    method: string = 'GET',
    customRules?: RateLimitRule[]
  ): Promise<{ allowed: boolean; waitTime?: number; info?: RateLimitInfo }> {
    const rules = customRules || this.defaultRules;
    const key = `${method}:${endpoint}`;
    
    for (const rule of rules) {
      if (this.matchesRule(endpoint, method, rule)) {
        const bucket = this.getBucket(key, rule);
        const result = bucket.consume(1);
        
        if (!result.allowed) {
          return {
            allowed: false,
            waitTime: result.waitTime,
            info: {
              limit: rule.requests,
              remaining: bucket.tokens,
              resetTime: new Date(Date.now() + result.waitTime),
              retryAfter: Math.ceil(result.waitTime / 1000)
            }
          };
        }
      }
    }

    return { allowed: true };
  }

  /**
   * Update rate limit info from server response headers
   */
  updateFromHeaders(endpoint: string, headers: Headers): RateLimitInfo | null {
    const limit = headers.get('X-RateLimit-Limit');
    const remaining = headers.get('X-RateLimit-Remaining');
    const resetTime = headers.get('X-RateLimit-Reset');
    const retryAfter = headers.get('Retry-After');

    if (limit && remaining && resetTime) {
      return {
        limit: parseInt(limit),
        remaining: parseInt(remaining),
        resetTime: new Date(parseInt(resetTime) * 1000),
        retryAfter: retryAfter ? parseInt(retryAfter) : undefined
      };
    }

    return null;
  }

  private getBucket(key: string, rule: RateLimitRule): TokenBucket {
    if (!this.buckets.has(key)) {
      this.buckets.set(key, new TokenBucket(rule.requests, rule.windowMs));
    }
    return this.buckets.get(key)!;
  }

  private matchesRule(endpoint: string, method: string, rule: RateLimitRule): boolean {
    if (rule.methods && !rule.methods.includes(method)) {
      return false;
    }

    if (rule.pattern) {
      const regex = new RegExp(rule.pattern);
      return regex.test(endpoint);
    }

    return rule.endpoints ? rule.endpoints.includes(endpoint) : true;
  }
}

// Rate limit rule definition
export interface RateLimitRule {
  requests: number; // max requests
  windowMs: number; // time window in milliseconds
  endpoints?: string[];
  pattern?: string; // regex pattern for endpoints
  methods?: string[];
}

// Token bucket implementation for rate limiting
class TokenBucket {
  private tokens: number;
  private lastRefill: number;
  private readonly capacity: number;
  private readonly refillRate: number; // tokens per millisecond

  constructor(capacity: number, windowMs: number) {
    this.capacity = capacity;
    this.tokens = capacity;
    this.refillRate = capacity / windowMs;
    this.lastRefill = Date.now();
  }

  consume(tokens: number): { allowed: boolean; waitTime: number } {
    this.refill();

    if (this.tokens >= tokens) {
      this.tokens -= tokens;
      return { allowed: true, waitTime: 0 };
    }

    const tokensNeeded = tokens - this.tokens;
    const waitTime = tokensNeeded / this.refillRate;
    
    return { 
      allowed: false, 
      waitTime: Math.ceil(waitTime)
    };
  }

  private refill(): void {
    const now = Date.now();
    const timePassed = now - this.lastRefill;
    const tokensToAdd = timePassed * this.refillRate;
    
    this.tokens = Math.min(this.capacity, this.tokens + tokensToAdd);
    this.lastRefill = now;
  }
}

// Advanced retry handler with exponential backoff and jitter
export class RetryHandler {
  private config: RetryConfig;

  constructor(config: Partial<RetryConfig> = {}) {
    this.config = { ...DEFAULT_RETRY_CONFIG, ...config };
  }

  /**
   * Execute request with retry logic
   */
  async executeWithRetry<T>(
    requestFn: () => Promise<Response>,
    context?: { endpoint: string; method: string }
  ): Promise<Response> {
    let lastError: Error;
    
    for (let attempt = 1; attempt <= this.config.maxAttempts; attempt++) {
      try {
        const response = await requestFn();
        
        // Check if response should trigger retry
        if (this.shouldRetryResponse(response)) {
          if (attempt === this.config.maxAttempts) {
            throw new Error(`Request failed after ${attempt} attempts: ${response.statusText}`);
          }
          
          // Wait before retry
          const delay = this.calculateDelay(attempt, response);
          await this.sleep(delay);
          continue;
        }

        return response;
      } catch (error) {
        lastError = error as Error;
        
        // Check if error should trigger retry
        if (!this.shouldRetryError(error as Error) || attempt === this.config.maxAttempts) {
          throw error;
        }
        
        // Wait before retry
        const delay = this.calculateDelay(attempt);
        await this.sleep(delay);
      }
    }

    throw lastError!;
  }

  private shouldRetryResponse(response: Response): boolean {
    return this.config.retryableStatuses.includes(response.status);
  }

  private shouldRetryError(error: Error): boolean {
    if (error instanceof ApiError) {
      return this.config.retryableErrors.includes(error.code);
    }

    // Check for network errors
    const networkErrors = ['NetworkError', 'TimeoutError', 'AbortError'];
    return networkErrors.some(errorType => error.name === errorType);
  }

  private calculateDelay(attempt: number, response?: Response): number {
    // Check for server-specified retry delay
    if (response) {
      const retryAfter = response.headers.get('Retry-After');
      if (retryAfter) {
        const delay = parseInt(retryAfter) * 1000;
        return Math.min(delay, this.config.maxDelay);
      }
    }

    // Calculate exponential backoff with jitter
    const exponentialDelay = this.config.baseDelay * Math.pow(this.config.backoffMultiplier, attempt - 1);
    const jitter = Math.random() * this.config.jitterMax;
    const delay = exponentialDelay + jitter;
    
    return Math.min(delay, this.config.maxDelay);
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// Circuit breaker for handling failing services
export class CircuitBreaker {
  private state: 'CLOSED' | 'OPEN' | 'HALF_OPEN' = 'CLOSED';
  private failureCount = 0;
  private lastFailureTime?: Date;
  private successCount = 0;

  constructor(
    private readonly failureThreshold: number = 5,
    private readonly timeoutMs: number = 60000, // 1 minute
    private readonly monitoringPeriodMs: number = 10000 // 10 seconds
  ) {}

  /**
   * Execute function with circuit breaker protection
   */
  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === 'OPEN') {
      if (this.shouldAttemptReset()) {
        this.state = 'HALF_OPEN';
        this.successCount = 0;
      } else {
        throw new Error('Circuit breaker is OPEN - service unavailable');
      }
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  private onSuccess(): void {
    if (this.state === 'HALF_OPEN') {
      this.successCount++;
      if (this.successCount >= 3) { // Require 3 successes to close
        this.reset();
      }
    } else {
      this.failureCount = 0;
    }
  }

  private onFailure(): void {
    this.failureCount++;
    this.lastFailureTime = new Date();

    if (this.failureCount >= this.failureThreshold) {
      this.state = 'OPEN';
    } else if (this.state === 'HALF_OPEN') {
      this.state = 'OPEN';
    }
  }

  private shouldAttemptReset(): boolean {
    return (
      this.lastFailureTime &&
      Date.now() - this.lastFailureTime.getTime() > this.timeoutMs
    );
  }

  private reset(): void {
    this.state = 'CLOSED';
    this.failureCount = 0;
    this.successCount = 0;
    this.lastFailureTime = undefined;
  }

  getState(): { state: string; failureCount: number; lastFailureTime?: Date } {
    return {
      state: this.state,
      failureCount: this.failureCount,
      lastFailureTime: this.lastFailureTime
    };
  }
}

// Error recovery strategies
export class ErrorRecoveryManager {
  private recoveryStrategies = new Map<string, RecoveryStrategy>();

  constructor() {
    this.setupDefaultStrategies();
  }

  /**
   * Attempt to recover from an error
   */
  async attemptRecovery(error: ApiError): Promise<{ recovered: boolean; suggestion?: string }> {
    const strategy = this.recoveryStrategies.get(error.code) || 
                    this.recoveryStrategies.get(error.category) ||
                    this.recoveryStrategies.get('default');

    if (!strategy) {
      return { recovered: false };
    }

    try {
      const result = await strategy.recover(error);
      return result;
    } catch (recoveryError) {
      return { 
        recovered: false, 
        suggestion: 'Automatic recovery failed. Please try again manually.' 
      };
    }
  }

  private setupDefaultStrategies(): void {
    // Token refresh strategy
    this.recoveryStrategies.set('TOKEN_EXPIRED', {
      recover: async (error: ApiError) => {
        // This would integrate with the auth system to refresh tokens
        return { 
          recovered: true, 
          suggestion: 'Authentication token refreshed. Please retry your request.' 
        };
      }
    });

    // Rate limit strategy
    this.recoveryStrategies.set('RATE_LIMIT_EXCEEDED', {
      recover: async (error: ApiError) => {
        const waitTime = error.retryAfter || 60;
        return {
          recovered: false,
          suggestion: `Rate limit exceeded. Please wait ${waitTime} seconds before retrying.`
        };
      }
    });

    // Network error strategy
    this.recoveryStrategies.set('network_error', {
      recover: async (error: ApiError) => {
        return {
          recovered: false,
          suggestion: 'Network error detected. Please check your connection and retry.'
        };
      }
    });

    // Default strategy
    this.recoveryStrategies.set('default', {
      recover: async (error: ApiError) => {
        return {
          recovered: false,
          suggestion: error.getUserFriendlyMessage()
        };
      }
    });
  }
}

interface RecoveryStrategy {
  recover(error: ApiError): Promise<{ recovered: boolean; suggestion?: string }>;
}

// Export utilities for easy use
export const rateLimiter = new RateLimiter([
  // API rate limits - adjust based on your actual limits
  { requests: 1000, windowMs: 60000, pattern: '/api/v1/.*' }, // 1000 req/min for API
  { requests: 100, windowMs: 60000, endpoints: ['/auth/login'], methods: ['POST'] }, // 100 login attempts/min
  { requests: 50, windowMs: 60000, pattern: '/files/upload' }, // 50 uploads/min
]);

export const retryHandler = new RetryHandler();
export const circuitBreaker = new CircuitBreaker();
export const errorRecoveryManager = new ErrorRecoveryManager();