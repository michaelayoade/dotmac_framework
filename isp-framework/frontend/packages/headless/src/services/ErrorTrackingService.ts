/**
 * Comprehensive Client-side Error Tracking System
 * 
 * Captures, analyzes, and reports all types of client-side errors
 * including React errors, JavaScript errors, network errors, and performance issues
 */

import { performanceAggregator, PerformanceReport } from '@/packages/monitoring/src/performance/PerformanceMonitor';

export interface ErrorContext {
  userId?: string;
  sessionId?: string;
  tenantId?: string;
  route?: string;
  userAgent?: string;
  timestamp?: Date;
  url?: string;
  referrer?: string;
  componentStack?: string;
  errorBoundary?: string;
  props?: Record<string, any>;
  state?: Record<string, any>;
  breadcrumbs?: ErrorBreadcrumb[];
}

export interface ErrorBreadcrumb {
  timestamp: Date;
  category: 'navigation' | 'user' | 'console' | 'request' | 'error';
  message: string;
  level: 'info' | 'warning' | 'error';
  data?: Record<string, any>;
}

export interface ErrorReport {
  id: string;
  type: 'javascript' | 'react' | 'network' | 'promise' | 'resource' | 'performance';
  message: string;
  stack?: string;
  filename?: string;
  lineno?: number;
  colno?: number;
  severity: 'low' | 'medium' | 'high' | 'critical';
  context: ErrorContext;
  fingerprint: string;
  count: number;
  firstOccurrence: Date;
  lastOccurrence: Date;
  resolved: boolean;
  tags: string[];
  environment: 'development' | 'staging' | 'production';
  release?: string;
}

export interface NetworkError {
  url: string;
  method: string;
  status: number;
  statusText: string;
  requestHeaders?: Record<string, string>;
  responseHeaders?: Record<string, string>;
  requestBody?: any;
  responseBody?: any;
  duration: number;
}

export interface ErrorTrackingConfig {
  apiEndpoint?: string;
  apiKey?: string;
  environment: 'development' | 'staging' | 'production';
  release?: string;
  userId?: string;
  sessionId?: string;
  tenantId?: string;
  enableConsoleCapture: boolean;
  enableBreadcrumbs: boolean;
  enablePerformanceTracking: boolean;
  enableNetworkTracking: boolean;
  maxBreadcrumbs: number;
  beforeSend?: (error: ErrorReport) => ErrorReport | null;
  onError?: (error: ErrorReport) => void;
  ignoreErrors?: (string | RegExp)[];
  ignoreUrls?: (string | RegExp)[];
  sampleRate: number; // 0.0 to 1.0
  maxReportsPerSession: number;
}

class ErrorTrackingService {
  private config: ErrorTrackingConfig;
  private breadcrumbs: ErrorBreadcrumb[] = [];
  private errorCache = new Map<string, ErrorReport>();
  private sessionErrors = 0;
  private originalConsole: any = {};
  private sessionId: string;
  private isInitialized = false;

  constructor(config: Partial<ErrorTrackingConfig> = {}) {
    this.sessionId = this.generateSessionId();
    
    this.config = {
      environment: 'development',
      enableConsoleCapture: true,
      enableBreadcrumbs: true,
      enablePerformanceTracking: true,
      enableNetworkTracking: true,
      maxBreadcrumbs: 100,
      sampleRate: 1.0,
      maxReportsPerSession: 50,
      ...config,
    };
  }

  initialize() {
    if (this.isInitialized) return;
    
    this.setupGlobalErrorHandlers();
    this.setupConsoleCapture();
    this.setupNetworkTracking();
    this.setupPerformanceTracking();
    this.setupReactErrorTracking();
    
    this.addBreadcrumb({
      timestamp: new Date(),
      category: 'navigation',
      message: 'Error tracking initialized',
      level: 'info',
      data: { environment: this.config.environment }
    });

    this.isInitialized = true;
  }

  private generateSessionId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateFingerprint(message: string, stack?: string, filename?: string): string {
    const hashData = `${message}${stack || ''}${filename || ''}`;
    return btoa(hashData).replace(/[^a-zA-Z0-9]/g, '').substr(0, 16);
  }

  private shouldIgnoreError(message: string, filename?: string): boolean {
    const { ignoreErrors = [], ignoreUrls = [] } = this.config;
    
    // Check ignored error messages
    for (const pattern of ignoreErrors) {
      if (typeof pattern === 'string' && message.includes(pattern)) return true;
      if (pattern instanceof RegExp && pattern.test(message)) return true;
    }

    // Check ignored URLs
    if (filename) {
      for (const pattern of ignoreUrls) {
        if (typeof pattern === 'string' && filename.includes(pattern)) return true;
        if (pattern instanceof RegExp && pattern.test(filename)) return true;
      }
    }

    return false;
  }

  private shouldSample(): boolean {
    return Math.random() < this.config.sampleRate;
  }

  private setupGlobalErrorHandlers() {
    // Global JavaScript error handler
    window.addEventListener('error', (event) => {
      const { error, message, filename, lineno, colno } = event;
      
      if (this.shouldIgnoreError(message, filename)) return;
      if (!this.shouldSample()) return;

      this.captureError({
        type: 'javascript',
        message: message || 'Unknown error',
        stack: error?.stack,
        filename,
        lineno,
        colno,
        severity: this.determineSeverity(error, message),
        context: this.getErrorContext(),
      });
    });

    // Unhandled promise rejection handler
    window.addEventListener('unhandledrejection', (event) => {
      const error = event.reason;
      
      if (this.shouldIgnoreError(error?.message || 'Promise rejection')) return;
      if (!this.shouldSample()) return;

      this.captureError({
        type: 'promise',
        message: error?.message || 'Unhandled promise rejection',
        stack: error?.stack,
        severity: 'high',
        context: this.getErrorContext(),
      });
    });

    // Resource loading error handler
    window.addEventListener('error', (event) => {
      const target = event.target as HTMLElement;
      
      if (target !== window && (target.tagName === 'IMG' || target.tagName === 'SCRIPT' || target.tagName === 'LINK')) {
        this.captureError({
          type: 'resource',
          message: `Failed to load resource: ${target.tagName}`,
          filename: (target as any).src || (target as any).href,
          severity: 'medium',
          context: this.getErrorContext(),
        });
      }
    }, true);
  }

  private setupConsoleCapture() {
    if (!this.config.enableConsoleCapture) return;

    const consoleMethodsToCapture = ['error', 'warn', 'info', 'log'] as const;

    consoleMethodsToCapture.forEach(method => {
      this.originalConsole[method] = console[method];
      
      console[method] = (...args: any[]) => {
        // Call original console method
        this.originalConsole[method]?.(...args);

        // Add breadcrumb for console messages
        this.addBreadcrumb({
          timestamp: new Date(),
          category: 'console',
          message: args.join(' '),
          level: method === 'error' ? 'error' : method === 'warn' ? 'warning' : 'info',
          data: { method, args }
        });

        // Capture console errors as actual errors
        if (method === 'error') {
          const message = args.join(' ');
          if (!this.shouldIgnoreError(message)) {
            this.captureError({
              type: 'javascript',
              message: `Console Error: ${message}`,
              severity: 'medium',
              context: this.getErrorContext(),
            });
          }
        }
      };
    });
  }

  private setupNetworkTracking() {
    if (!this.config.enableNetworkTracking) return;

    // Intercept fetch
    const originalFetch = window.fetch;
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const startTime = performance.now();
      const url = input.toString();
      const method = init?.method || 'GET';

      try {
        const response = await originalFetch(input, init);
        const duration = performance.now() - startTime;

        // Add successful request breadcrumb
        this.addBreadcrumb({
          timestamp: new Date(),
          category: 'request',
          message: `${method} ${url}`,
          level: 'info',
          data: { 
            method, 
            url, 
            status: response.status, 
            duration: Math.round(duration) 
          }
        });

        // Track failed requests
        if (!response.ok) {
          const networkError: NetworkError = {
            url,
            method,
            status: response.status,
            statusText: response.statusText,
            duration,
          };

          this.captureError({
            type: 'network',
            message: `Network request failed: ${method} ${url} (${response.status})`,
            severity: response.status >= 500 ? 'high' : 'medium',
            context: {
              ...this.getErrorContext(),
              networkError,
            },
          });
        }

        return response;
      } catch (error: any) {
        const duration = performance.now() - startTime;

        this.captureError({
          type: 'network',
          message: `Network request error: ${method} ${url}`,
          stack: error.stack,
          severity: 'high',
          context: {
            ...this.getErrorContext(),
            networkError: {
              url,
              method,
              status: 0,
              statusText: 'Network Error',
              duration,
            } as NetworkError,
          },
        });

        throw error;
      }
    };

    // Intercept XMLHttpRequest
    const originalXHROpen = XMLHttpRequest.prototype.open;
    const originalXHRSend = XMLHttpRequest.prototype.send;

    XMLHttpRequest.prototype.open = function(method: string, url: string | URL, ...args: any[]) {
      (this as any)._errorTracking = { method, url: url.toString(), startTime: 0 };
      return originalXHROpen.apply(this, [method, url, ...args]);
    };

    XMLHttpRequest.prototype.send = function(body?: Document | XMLHttpRequestBodyInit | null) {
      const tracking = (this as any)._errorTracking;
      if (tracking) {
        tracking.startTime = performance.now();

        this.addEventListener('loadend', () => {
          const duration = performance.now() - tracking.startTime;
          const status = this.status;

          if (status === 0 || status >= 400) {
            errorTracker.captureError({
              type: 'network',
              message: `XMLHttpRequest failed: ${tracking.method} ${tracking.url} (${status})`,
              severity: status >= 500 || status === 0 ? 'high' : 'medium',
              context: {
                ...errorTracker.getErrorContext(),
                networkError: {
                  url: tracking.url,
                  method: tracking.method,
                  status,
                  statusText: this.statusText,
                  duration,
                } as NetworkError,
              },
            });
          }
        });
      }

      return originalXHRSend.call(this, body);
    };
  }

  private setupPerformanceTracking() {
    if (!this.config.enablePerformanceTracking) return;

    // Listen to performance reports
    performanceAggregator.onReport((report: PerformanceReport) => {
      // Convert performance warnings to error reports
      report.warnings.forEach(warning => {
        if (warning.severity === 'high') {
          this.captureError({
            type: 'performance',
            message: `Performance issue: ${warning.message}`,
            severity: 'medium',
            context: {
              ...this.getErrorContext(),
              performanceReport: report,
            },
          });
        }
      });
    });
  }

  private setupReactErrorTracking() {
    // This will be used by React Error Boundaries
    (window as any).__ERROR_TRACKER__ = this;
  }

  private determineSeverity(error: any, message: string): 'low' | 'medium' | 'high' | 'critical' {
    // Critical errors that break core functionality
    if (
      message.includes('ChunkLoadError') ||
      message.includes('Loading CSS chunk') ||
      message.includes('Loading chunk')
    ) {
      return 'critical';
    }

    // High severity for React errors and network failures
    if (
      error?.name === 'ChunkLoadError' ||
      message.includes('Network request failed') ||
      message.includes('Unhandled promise rejection')
    ) {
      return 'high';
    }

    // Medium severity for common JavaScript errors
    if (
      message.includes('TypeError') ||
      message.includes('ReferenceError') ||
      message.includes('SyntaxError')
    ) {
      return 'medium';
    }

    return 'low';
  }

  private getErrorContext(): ErrorContext {
    return {
      userId: this.config.userId,
      sessionId: this.sessionId,
      tenantId: this.config.tenantId,
      route: window.location.pathname,
      userAgent: navigator.userAgent,
      timestamp: new Date(),
      url: window.location.href,
      referrer: document.referrer,
      breadcrumbs: [...this.breadcrumbs],
    };
  }

  captureError(errorData: Partial<ErrorReport>) {
    if (this.sessionErrors >= this.config.maxReportsPerSession) {
      return;
    }

    const fingerprint = this.generateFingerprint(
      errorData.message || 'Unknown error',
      errorData.stack,
      errorData.filename
    );

    const existingError = this.errorCache.get(fingerprint);
    const now = new Date();

    let errorReport: ErrorReport;

    if (existingError) {
      // Update existing error
      errorReport = {
        ...existingError,
        count: existingError.count + 1,
        lastOccurrence: now,
        context: {
          ...existingError.context,
          ...errorData.context,
        },
      };
    } else {
      // Create new error report
      errorReport = {
        id: `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
        type: errorData.type || 'javascript',
        message: errorData.message || 'Unknown error',
        stack: errorData.stack,
        filename: errorData.filename,
        lineno: errorData.lineno,
        colno: errorData.colno,
        severity: errorData.severity || 'medium',
        context: {
          ...this.getErrorContext(),
          ...errorData.context,
        },
        fingerprint,
        count: 1,
        firstOccurrence: now,
        lastOccurrence: now,
        resolved: false,
        tags: this.generateTags(errorData),
        environment: this.config.environment,
        release: this.config.release,
      };
    }

    this.errorCache.set(fingerprint, errorReport);
    this.sessionErrors++;

    // Apply beforeSend filter
    const filteredError = this.config.beforeSend?.(errorReport) ?? errorReport;
    if (!filteredError) return;

    // Call onError callback
    this.config.onError?.(filteredError);

    // Send to backend (if configured)
    this.sendToBackend(filteredError);

    // Store locally for debugging
    this.storeLocally(filteredError);
  }

  captureReactError(error: Error, errorInfo: { componentStack: string }, errorBoundary?: string) {
    this.captureError({
      type: 'react',
      message: error.message,
      stack: error.stack,
      severity: 'high',
      context: {
        componentStack: errorInfo.componentStack,
        errorBoundary,
      },
    });
  }

  private generateTags(errorData: Partial<ErrorReport>): string[] {
    const tags: string[] = [];

    if (errorData.type) tags.push(`type:${errorData.type}`);
    if (errorData.filename) {
      const filename = errorData.filename.split('/').pop();
      tags.push(`file:${filename}`);
    }
    if (this.config.tenantId) tags.push(`tenant:${this.config.tenantId}`);

    return tags;
  }

  addBreadcrumb(breadcrumb: ErrorBreadcrumb) {
    if (!this.config.enableBreadcrumbs) return;

    this.breadcrumbs.push(breadcrumb);

    // Keep only the most recent breadcrumbs
    if (this.breadcrumbs.length > this.config.maxBreadcrumbs) {
      this.breadcrumbs = this.breadcrumbs.slice(-this.config.maxBreadcrumbs);
    }
  }

  private async sendToBackend(error: ErrorReport) {
    if (!this.config.apiEndpoint || !this.config.apiKey) return;

    try {
      await fetch(this.config.apiEndpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.apiKey}`,
        },
        body: JSON.stringify(error),
      });
    } catch (e) {
      // Silently fail to avoid infinite error loops
      console.warn('Failed to send error report to backend:', e);
    }
  }

  private storeLocally(error: ErrorReport) {
    try {
      const stored = localStorage.getItem('errorTracker_errors');
      const errors = stored ? JSON.parse(stored) : [];
      
      errors.push(error);
      
      // Keep only last 100 errors
      const recentErrors = errors.slice(-100);
      
      localStorage.setItem('errorTracker_errors', JSON.stringify(recentErrors));
    } catch (e) {
      // Storage might be full or unavailable
    }
  }

  getStoredErrors(): ErrorReport[] {
    try {
      const stored = localStorage.getItem('errorTracker_errors');
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      return [];
    }
  }

  clearStoredErrors() {
    try {
      localStorage.removeItem('errorTracker_errors');
    } catch (e) {
      // Ignore storage errors
    }
  }

  updateConfig(config: Partial<ErrorTrackingConfig>) {
    this.config = { ...this.config, ...config };
  }

  setUser(userId: string) {
    this.config.userId = userId;
  }

  setTenant(tenantId: string) {
    this.config.tenantId = tenantId;
  }

  addTag(key: string, value: string) {
    // This would be used to add custom tags to future errors
  }

  flush() {
    // Send any pending errors immediately
    // This could be called before page unload
  }

  destroy() {
    // Restore original console methods
    Object.keys(this.originalConsole).forEach(method => {
      (console as any)[method] = this.originalConsole[method];
    });

    // Clear caches
    this.errorCache.clear();
    this.breadcrumbs = [];
    
    this.isInitialized = false;
  }
}

// Global error tracker instance
export const errorTracker = new ErrorTrackingService();

// React hook for error tracking
export function useErrorTracking() {
  const captureError = (error: Error | string, context?: Partial<ErrorContext>) => {
    if (typeof error === 'string') {
      errorTracker.captureError({
        message: error,
        context,
      });
    } else {
      errorTracker.captureError({
        message: error.message,
        stack: error.stack,
        context,
      });
    }
  };

  const addBreadcrumb = (message: string, category: ErrorBreadcrumb['category'] = 'user', data?: any) => {
    errorTracker.addBreadcrumb({
      timestamp: new Date(),
      category,
      message,
      level: 'info',
      data,
    });
  };

  return {
    captureError,
    addBreadcrumb,
    errorTracker,
  };
}

// Enhanced Error Boundary that integrates with error tracking
export function createErrorBoundary(errorBoundaryName?: string) {
  return class TrackedErrorBoundary extends React.Component<
    { children: React.ReactNode; fallback?: React.ComponentType<any> },
    { hasError: boolean }
  > {
    constructor(props: any) {
      super(props);
      this.state = { hasError: false };
    }

    static getDerivedStateFromError() {
      return { hasError: true };
    }

    componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
      errorTracker.captureReactError(error, errorInfo, errorBoundaryName);
    }

    render() {
      if (this.state.hasError) {
        const Fallback = this.props.fallback || DefaultErrorFallback;
        return <Fallback />;
      }

      return this.props.children;
    }
  };
}

function DefaultErrorFallback() {
  return (
    <div className="error-boundary-fallback">
      <h2>Something went wrong</h2>
      <p>An error occurred while rendering this component.</p>
    </div>
  );
}

export default ErrorTrackingService;