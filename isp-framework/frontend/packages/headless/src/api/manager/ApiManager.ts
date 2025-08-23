/**
 * API Client Orchestrator/Manager
 * Centralized management of all API clients with unified configuration,
 * error handling, rate limiting, and monitoring
 */

import { BaseApiClient } from '../clients/BaseApiClient';
import { AuthApiClient } from '../clients/AuthApiClient';
import { FileApiClient } from '../clients/FileApiClient';
import { AnalyticsApiClient } from '../clients/AnalyticsApiClient';
import { BillingApiClient } from '../clients/BillingApiClient';
import { ComplianceApiClient } from '../clients/ComplianceApiClient';
import { FieldOpsApiClient } from '../clients/FieldOpsApiClient';
import { IdentityApiClient } from '../clients/IdentityApiClient';
import { InventoryApiClient } from '../clients/InventoryApiClient';
import { LicensingApiClient } from '../clients/LicensingApiClient';
import { NetworkingApiClient } from '../clients/NetworkingApiClient';
import { NotificationsApiClient } from '../clients/NotificationsApiClient';
import { ResellersApiClient } from '../clients/ResellersApiClient';
import { ServicesApiClient } from '../clients/ServicesApiClient';
import { SupportApiClient } from '../clients/SupportApiClient';

import { 
  rateLimiter, 
  retryHandler, 
  circuitBreaker, 
  errorRecoveryManager,
  type RateLimitRule,
  type RetryConfig 
} from '../utils/rateLimiting';
import { ApiError } from '../types/errors';

// Manager configuration
export interface ApiManagerConfig {
  baseURL: string;
  timeout?: number;
  rateLimits?: RateLimitRule[];
  retryConfig?: Partial<RetryConfig>;
  enableMetrics?: boolean;
  enableLogging?: boolean;
  authTokenProvider?: () => Promise<string | null>;
  onUnauthorized?: () => void;
  onError?: (error: ApiError) => void;
}

// Client registry
export interface ClientRegistry {
  analytics: AnalyticsApiClient;
  auth: AuthApiClient;
  billing: BillingApiClient;
  compliance: ComplianceApiClient;
  fieldOps: FieldOpsApiClient;
  files: FileApiClient;
  identity: IdentityApiClient;
  inventory: InventoryApiClient;
  licensing: LicensingApiClient;
  networking: NetworkingApiClient;
  notifications: NotificationsApiClient;
  resellers: ResellersApiClient;
  services: ServicesApiClient;
  support: SupportApiClient;
}

// API metrics
export interface ApiMetrics {
  totalRequests: number;
  successfulRequests: number;
  failedRequests: number;
  averageResponseTime: number;
  requestsByEndpoint: Map<string, EndpointMetrics>;
  errorsByType: Map<string, number>;
  lastUpdated: Date;
}

interface EndpointMetrics {
  requests: number;
  successes: number;
  failures: number;
  averageResponseTime: number;
  lastAccessed: Date;
}

// Request context for tracking
interface RequestContext {
  endpoint: string;
  method: string;
  startTime: number;
  clientName: string;
}

export class ApiManager {
  private config: ApiManagerConfig;
  private clients: ClientRegistry;
  private metrics: ApiMetrics;
  private activeRequests = new Map<string, RequestContext>();

  constructor(config: ApiManagerConfig) {
    this.config = config;
    this.initializeMetrics();
    this.initializeClients();
    
    // Setup rate limiting if configured
    if (config.rateLimits) {
      rateLimiter.constructor(config.rateLimits);
    }
  }

  /**
   * Get all API clients
   */
  get api(): ClientRegistry {
    return this.clients;
  }

  /**
   * Get specific client by name
   */
  getClient<K extends keyof ClientRegistry>(clientName: K): ClientRegistry[K] {
    return this.clients[clientName];
  }

  /**
   * Execute request with full orchestration (rate limiting, retry, metrics)
   */
  async executeRequest<T>(
    clientName: keyof ClientRegistry,
    method: string,
    endpoint: string,
    data?: any,
    options?: {
      timeout?: number;
      skipRateLimit?: boolean;
      skipRetry?: boolean;
      idempotencyKey?: string;
    }
  ): Promise<T> {
    const requestId = this.generateRequestId();
    const context: RequestContext = {
      endpoint,
      method,
      startTime: Date.now(),
      clientName: clientName as string
    };

    this.activeRequests.set(requestId, context);

    try {
      // Check rate limits
      if (!options?.skipRateLimit) {
        const rateLimitCheck = await rateLimiter.checkRateLimit(endpoint, method);
        if (!rateLimitCheck.allowed) {
          throw new ApiError({
            error: {
              code: 'RATE_LIMIT_EXCEEDED',
              message: 'Rate limit exceeded',
              details: { waitTime: rateLimitCheck.waitTime }
            },
            timestamp: new Date().toISOString(),
            trace_id: requestId
          });
        }
      }

      // Execute with circuit breaker and retry logic
      const result = await circuitBreaker.execute(async () => {
        if (options?.skipRetry) {
          return this.executeDirectRequest<T>(clientName, method, endpoint, data, options);
        }
        
        return retryHandler.executeWithRetry(
          () => this.executeDirectRequest<T>(clientName, method, endpoint, data, options),
          { endpoint, method }
        );
      });

      // Update success metrics
      this.updateMetrics(context, true);
      
      return result;

    } catch (error) {
      // Update failure metrics
      this.updateMetrics(context, false, error as Error);
      
      // Attempt error recovery
      if (error instanceof ApiError) {
        const recovery = await errorRecoveryManager.attemptRecovery(error);
        if (recovery.recovered) {
          // Retry the request after successful recovery
          return this.executeRequest(clientName, method, endpoint, data, options);
        }
      }
      
      // Handle error callbacks
      if (this.config.onError && error instanceof ApiError) {
        this.config.onError(error);
      }
      
      throw error;
    } finally {
      this.activeRequests.delete(requestId);
    }
  }

  /**
   * Get current API metrics
   */
  getMetrics(): ApiMetrics {
    return { ...this.metrics };
  }

  /**
   * Reset API metrics
   */
  resetMetrics(): void {
    this.initializeMetrics();
  }

  /**
   * Get health status of all clients
   */
  async getHealthStatus(): Promise<{
    overall: 'healthy' | 'degraded' | 'unhealthy';
    clients: Record<keyof ClientRegistry, {
      status: 'healthy' | 'degraded' | 'unhealthy';
      responseTime?: number;
      errorRate?: number;
      lastSuccess?: Date;
    }>;
    circuitBreaker: ReturnType<typeof circuitBreaker.getState>;
  }> {
    const clientStatuses: any = {};
    let healthyClients = 0;
    let totalClients = 0;

    // Check each client's health
    for (const [clientName] of Object.entries(this.clients)) {
      totalClients++;
      const clientKey = clientName as keyof ClientRegistry;
      const endpointMetrics = this.metrics.requestsByEndpoint.get(`${clientName}:health`) || {
        requests: 0,
        successes: 0,
        failures: 0,
        averageResponseTime: 0,
        lastAccessed: new Date(0)
      };

      const errorRate = endpointMetrics.requests > 0 
        ? (endpointMetrics.failures / endpointMetrics.requests) * 100 
        : 0;

      let status: 'healthy' | 'degraded' | 'unhealthy' = 'healthy';
      
      if (errorRate > 50) {
        status = 'unhealthy';
      } else if (errorRate > 20 || endpointMetrics.averageResponseTime > 5000) {
        status = 'degraded';
      } else {
        healthyClients++;
      }

      clientStatuses[clientKey] = {
        status,
        responseTime: endpointMetrics.averageResponseTime,
        errorRate,
        lastSuccess: endpointMetrics.lastAccessed
      };
    }

    // Determine overall health
    let overall: 'healthy' | 'degraded' | 'unhealthy' = 'healthy';
    const healthyPercentage = (healthyClients / totalClients) * 100;
    
    if (healthyPercentage < 50) {
      overall = 'unhealthy';
    } else if (healthyPercentage < 80) {
      overall = 'degraded';
    }

    return {
      overall,
      clients: clientStatuses,
      circuitBreaker: circuitBreaker.getState()
    };
  }

  /**
   * Update authentication token for all clients
   */
  async updateAuthToken(): Promise<void> {
    if (!this.config.authTokenProvider) {
      throw new Error('No auth token provider configured');
    }

    const token = await this.config.authTokenProvider();
    if (!token) {
      if (this.config.onUnauthorized) {
        this.config.onUnauthorized();
      }
      return;
    }

    // Update auth headers for all clients
    const authHeader = { 'Authorization': `Bearer ${token}` };
    Object.values(this.clients).forEach(client => {
      if ('updateDefaultHeaders' in client) {
        (client as any).updateDefaultHeaders(authHeader);
      }
    });
  }

  /**
   * Bulk execute multiple requests with optional batching
   */
  async executeBatch<T>(
    requests: Array<{
      clientName: keyof ClientRegistry;
      method: string;
      endpoint: string;
      data?: any;
    }>,
    options?: {
      parallel?: boolean;
      batchSize?: number;
      continueOnError?: boolean;
    }
  ): Promise<Array<{ success: boolean; data?: T; error?: Error }>> {
    const { parallel = true, batchSize = 10, continueOnError = true } = options || {};
    
    if (parallel && requests.length <= batchSize) {
      // Execute all in parallel
      return Promise.allSettled(
        requests.map(req => 
          this.executeRequest<T>(req.clientName, req.method, req.endpoint, req.data)
        )
      ).then(results => 
        results.map(result => ({
          success: result.status === 'fulfilled',
          data: result.status === 'fulfilled' ? result.value : undefined,
          error: result.status === 'rejected' ? result.reason : undefined
        }))
      );
    } else {
      // Execute in batches or sequentially
      const results: Array<{ success: boolean; data?: T; error?: Error }> = [];
      
      for (let i = 0; i < requests.length; i += batchSize) {
        const batch = requests.slice(i, i + batchSize);
        
        const batchResults = await Promise.allSettled(
          batch.map(req => 
            this.executeRequest<T>(req.clientName, req.method, req.endpoint, req.data)
          )
        );
        
        const processedResults = batchResults.map(result => ({
          success: result.status === 'fulfilled',
          data: result.status === 'fulfilled' ? result.value : undefined,
          error: result.status === 'rejected' ? result.reason : undefined
        }));
        
        results.push(...processedResults);
        
        // Stop on first error if continueOnError is false
        if (!continueOnError && processedResults.some(r => !r.success)) {
          break;
        }
      }
      
      return results;
    }
  }

  private initializeClients(): void {
    const defaultHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      'X-Client-Version': '1.0.0'
    };

    // Initialize all clients
    this.clients = {
      analytics: new AnalyticsApiClient(this.config.baseURL, defaultHeaders),
      auth: new AuthApiClient(this.config.baseURL, defaultHeaders),
      billing: new BillingApiClient(this.config.baseURL, defaultHeaders),
      compliance: new ComplianceApiClient(this.config.baseURL, defaultHeaders),
      fieldOps: new FieldOpsApiClient(this.config.baseURL, defaultHeaders),
      files: new FileApiClient(this.config.baseURL, defaultHeaders),
      identity: new IdentityApiClient(this.config.baseURL, defaultHeaders),
      inventory: new InventoryApiClient(this.config.baseURL, defaultHeaders),
      licensing: new LicensingApiClient(this.config.baseURL, defaultHeaders),
      networking: new NetworkingApiClient(this.config.baseURL, defaultHeaders),
      notifications: new NotificationsApiClient(this.config.baseURL, defaultHeaders),
      resellers: new ResellersApiClient(this.config.baseURL, defaultHeaders),
      services: new ServicesApiClient(this.config.baseURL, defaultHeaders),
      support: new SupportApiClient(this.config.baseURL, defaultHeaders)
    };
  }

  private initializeMetrics(): void {
    this.metrics = {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      averageResponseTime: 0,
      requestsByEndpoint: new Map(),
      errorsByType: new Map(),
      lastUpdated: new Date()
    };
  }

  private async executeDirectRequest<T>(
    clientName: keyof ClientRegistry,
    method: string,
    endpoint: string,
    data?: any,
    options?: { timeout?: number; idempotencyKey?: string }
  ): Promise<T> {
    const client = this.clients[clientName];
    
    // This is a simplified version - in reality, you'd need to call the appropriate method
    // based on the HTTP method and endpoint. This would require extending the base client
    // with a generic request method.
    
    if ('request' in client) {
      return (client as any).request<T>(method, endpoint, data, {
        timeout: options?.timeout || this.config.timeout,
        headers: options?.idempotencyKey ? 
          { 'Idempotency-Key': options.idempotencyKey } : undefined
      });
    }
    
    throw new Error(`Client ${clientName} does not support generic requests`);
  }

  private updateMetrics(context: RequestContext, success: boolean, error?: Error): void {
    const responseTime = Date.now() - context.startTime;
    const endpointKey = `${context.clientName}:${context.endpoint}`;
    
    // Update overall metrics
    this.metrics.totalRequests++;
    if (success) {
      this.metrics.successfulRequests++;
    } else {
      this.metrics.failedRequests++;
      
      // Track error types
      if (error instanceof ApiError) {
        const currentCount = this.metrics.errorsByType.get(error.code) || 0;
        this.metrics.errorsByType.set(error.code, currentCount + 1);
      }
    }
    
    // Update average response time
    this.metrics.averageResponseTime = 
      (this.metrics.averageResponseTime * (this.metrics.totalRequests - 1) + responseTime) / 
      this.metrics.totalRequests;
    
    // Update endpoint-specific metrics
    const endpointMetrics = this.metrics.requestsByEndpoint.get(endpointKey) || {
      requests: 0,
      successes: 0,
      failures: 0,
      averageResponseTime: 0,
      lastAccessed: new Date()
    };
    
    endpointMetrics.requests++;
    if (success) {
      endpointMetrics.successes++;
    } else {
      endpointMetrics.failures++;
    }
    
    endpointMetrics.averageResponseTime = 
      (endpointMetrics.averageResponseTime * (endpointMetrics.requests - 1) + responseTime) / 
      endpointMetrics.requests;
    
    endpointMetrics.lastAccessed = new Date();
    
    this.metrics.requestsByEndpoint.set(endpointKey, endpointMetrics);
    this.metrics.lastUpdated = new Date();
  }

  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substring(2)}`;
  }
}

// Default instance
let defaultManager: ApiManager | null = null;

/**
 * Create and configure the default API manager
 */
export function createApiManager(config: ApiManagerConfig): ApiManager {
  defaultManager = new ApiManager(config);
  return defaultManager;
}

/**
 * Get the default API manager instance
 */
export function getApiManager(): ApiManager {
  if (!defaultManager) {
    throw new Error('API Manager not initialized. Call createApiManager() first.');
  }
  return defaultManager;
}