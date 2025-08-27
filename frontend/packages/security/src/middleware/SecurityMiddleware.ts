/**
 * Next.js Security Middleware
 * Implements comprehensive security controls for ISP customer portals
 */

import { NextRequest, NextResponse } from 'next/server';
import { SecurityHeadersGenerator, ISP_PORTAL_SECURITY_CONFIG, DEVELOPMENT_SECURITY_CONFIG } from '../headers/SecurityHeaders';

interface SecurityMiddlewareConfig {
  environment: 'development' | 'staging' | 'production';
  enableCSRF: boolean;
  enableRateLimiting: boolean;
  allowedOrigins: string[];
  trustedProxies: string[];
  sessionConfig: {
    cookieName: string;
    maxAge: number;
    secure: boolean;
    sameSite: 'strict' | 'lax' | 'none';
  };
}

interface RateLimitRule {
  path: string | RegExp;
  windowMs: number;
  maxRequests: number;
  skipSuccessful?: boolean;
  keyGenerator?: (request: NextRequest) => string;
}

export class SecurityMiddleware {
  private config: SecurityMiddlewareConfig;
  private headersGenerator: SecurityHeadersGenerator;
  private rateLimitStore = new Map<string, { count: number; resetTime: number }>();
  private trustedTokens = new Set<string>();
  private blockedIPs = new Set<string>();

  // Default rate limiting rules
  private rateLimitRules: RateLimitRule[] = [
    {
      path: '/api/auth/login',
      windowMs: 15 * 60 * 1000, // 15 minutes
      maxRequests: 5,
      skipSuccessful: true,
    },
    {
      path: '/api/auth/register',
      windowMs: 60 * 60 * 1000, // 1 hour
      maxRequests: 3,
    },
    {
      path: '/api/auth/reset-password',
      windowMs: 60 * 60 * 1000, // 1 hour
      maxRequests: 3,
    },
    {
      path: /^\/api\/.*$/,
      windowMs: 60 * 1000, // 1 minute
      maxRequests: 100,
    },
  ];

  constructor(config: SecurityMiddlewareConfig) {
    this.config = config;
    
    const securityConfig = config.environment === 'development' 
      ? DEVELOPMENT_SECURITY_CONFIG 
      : ISP_PORTAL_SECURITY_CONFIG;
      
    this.headersGenerator = new SecurityHeadersGenerator(securityConfig, config.environment);
    
    this.setupCleanupInterval();
  }

  /**
   * Main middleware handler
   */
  async handle(request: NextRequest): Promise<NextResponse> {
    const startTime = Date.now();
    let response: NextResponse;

    try {
      // Security checks
      await this.performSecurityChecks(request);
      
      // Rate limiting
      if (this.config.enableRateLimiting) {
        await this.checkRateLimit(request);
      }
      
      // CSRF protection
      if (this.config.enableCSRF && this.isStatefulRequest(request)) {
        await this.verifyCSRFToken(request);
      }
      
      // Continue with the request
      response = NextResponse.next();
      
      // Apply security headers
      this.applySecurityHeaders(response);
      
      // Log security metrics
      this.logSecurityMetrics(request, response, Date.now() - startTime);
      
    } catch (error) {
      response = this.handleSecurityError(error as SecurityError, request);
    }

    return response;
  }

  /**
   * Perform basic security checks
   */
  private async performSecurityChecks(request: NextRequest): Promise<void> {
    const clientIP = this.getClientIP(request);
    const userAgent = request.headers.get('user-agent') || '';
    const origin = request.headers.get('origin');
    const referer = request.headers.get('referer');

    // Check blocked IPs
    if (this.blockedIPs.has(clientIP)) {
      throw new SecurityError('blocked-ip', 'IP address is blocked', { ip: clientIP });
    }

    // Validate Origin header for sensitive requests
    if (this.isSensitiveRequest(request) && origin && !this.isAllowedOrigin(origin)) {
      throw new SecurityError('invalid-origin', 'Invalid origin header', { origin });
    }

    // Check for suspicious user agents
    if (this.isSuspiciousUserAgent(userAgent)) {
      this.logSecurityEvent('suspicious-user-agent', { userAgent, ip: clientIP });
    }

    // Validate request size
    const contentLength = parseInt(request.headers.get('content-length') || '0');
    if (contentLength > 10 * 1024 * 1024) { // 10MB limit
      throw new SecurityError('request-too-large', 'Request entity too large', { size: contentLength });
    }

    // Check for common attack patterns in URL
    const url = request.url;
    if (this.containsAttackPattern(url)) {
      throw new SecurityError('malicious-request', 'Malicious request pattern detected', { url });
    }

    // Host header validation
    const host = request.headers.get('host');
    if (host && !this.isValidHost(host)) {
      throw new SecurityError('invalid-host', 'Invalid host header', { host });
    }
  }

  /**
   * Check rate limiting rules
   */
  private async checkRateLimit(request: NextRequest): Promise<void> {
    const clientIP = this.getClientIP(request);
    const path = new URL(request.url).pathname;
    
    for (const rule of this.rateLimitRules) {
      if (this.matchesPath(path, rule.path)) {
        const key = rule.keyGenerator ? rule.keyGenerator(request) : `${clientIP}:${path}`;
        
        if (this.isRateLimited(key, rule)) {
          throw new SecurityError('rate-limited', 'Rate limit exceeded', {
            rule: rule.path.toString(),
            resetTime: this.getRateLimitResetTime(key),
          });
        }
        
        this.recordRequest(key, rule);
        break; // Apply only the first matching rule
      }
    }
  }

  /**
   * Verify CSRF token for stateful requests
   */
  private async verifyCSRFToken(request: NextRequest): Promise<void> {
    const token = this.extractCSRFToken(request);
    const sessionToken = this.getSessionToken(request);
    
    if (!token) {
      throw new SecurityError('missing-csrf-token', 'CSRF token is required');
    }
    
    if (!sessionToken) {
      throw new SecurityError('missing-session', 'Valid session is required');
    }
    
    if (!this.validateCSRFToken(token, sessionToken)) {
      throw new SecurityError('invalid-csrf-token', 'Invalid CSRF token');
    }
  }

  /**
   * Apply security headers to response
   */
  private applySecurityHeaders(response: NextResponse): void {
    const headers = this.headersGenerator.generateHeaders();
    
    for (const [name, value] of Object.entries(headers)) {
      response.headers.set(name, value);
    }

    // Add request ID for tracking
    response.headers.set('X-Request-ID', this.generateRequestId());
    
    // Add processing time
    response.headers.set('X-Response-Time', `${Date.now()}ms`);
  }

  /**
   * Handle security errors
   */
  private handleSecurityError(error: SecurityError, request: NextRequest): NextResponse {
    this.logSecurityEvent(error.type, {
      message: error.message,
      context: error.context,
      ip: this.getClientIP(request),
      userAgent: request.headers.get('user-agent'),
      url: request.url,
    });

    // Return appropriate error response
    switch (error.type) {
      case 'rate-limited':
        return new NextResponse('Rate limit exceeded', { 
          status: 429,
          headers: {
            'Retry-After': String(Math.ceil((error.context?.resetTime - Date.now()) / 1000)),
            'X-RateLimit-Limit': '100',
            'X-RateLimit-Remaining': '0',
          }
        });
      
      case 'blocked-ip':
        return new NextResponse('Access denied', { status: 403 });
      
      case 'invalid-origin':
      case 'invalid-host':
        return new NextResponse('Invalid request', { status: 400 });
      
      case 'missing-csrf-token':
      case 'invalid-csrf-token':
        return new NextResponse('CSRF token validation failed', { status: 403 });
      
      case 'request-too-large':
        return new NextResponse('Request entity too large', { status: 413 });
      
      case 'malicious-request':
        return new NextResponse('Bad request', { status: 400 });
      
      default:
        return new NextResponse('Security error', { status: 400 });
    }
  }

  /**
   * Check if request matches a path pattern
   */
  private matchesPath(path: string, pattern: string | RegExp): boolean {
    if (typeof pattern === 'string') {
      return path === pattern;
    }
    return pattern.test(path);
  }

  /**
   * Check if request is rate limited
   */
  private isRateLimited(key: string, rule: RateLimitRule): boolean {
    const now = Date.now();
    const record = this.rateLimitStore.get(key);
    
    if (!record || now > record.resetTime) {
      return false;
    }
    
    return record.count >= rule.maxRequests;
  }

  /**
   * Record request for rate limiting
   */
  private recordRequest(key: string, rule: RateLimitRule): void {
    const now = Date.now();
    const record = this.rateLimitStore.get(key);
    
    if (!record || now > record.resetTime) {
      this.rateLimitStore.set(key, {
        count: 1,
        resetTime: now + rule.windowMs,
      });
    } else {
      record.count++;
    }
  }

  /**
   * Get rate limit reset time
   */
  private getRateLimitResetTime(key: string): number {
    const record = this.rateLimitStore.get(key);
    return record?.resetTime || Date.now();
  }

  /**
   * Extract client IP address
   */
  private getClientIP(request: NextRequest): string {
    // Check trusted proxy headers
    const forwarded = request.headers.get('x-forwarded-for');
    if (forwarded) {
      const ips = forwarded.split(',').map(ip => ip.trim());
      return ips[0]; // Return first IP (original client)
    }
    
    return request.headers.get('x-real-ip') || 
           request.headers.get('cf-connecting-ip') || // Cloudflare
           request.ip || 
           '127.0.0.1';
  }

  /**
   * Check if origin is allowed
   */
  private isAllowedOrigin(origin: string): boolean {
    return this.config.allowedOrigins.some(allowed => {
      if (allowed === '*') return true;
      if (allowed.startsWith('*.')) {
        const domain = allowed.slice(2);
        return origin.endsWith(domain);
      }
      return origin === allowed;
    });
  }

  /**
   * Check if user agent is suspicious
   */
  private isSuspiciousUserAgent(userAgent: string): boolean {
    const suspiciousPatterns = [
      /bot/i,
      /crawler/i,
      /spider/i,
      /scan/i,
      /curl/i,
      /wget/i,
      /python/i,
      /^$/,
    ];
    
    return suspiciousPatterns.some(pattern => pattern.test(userAgent));
  }

  /**
   * Check for attack patterns in URL
   */
  private containsAttackPattern(url: string): boolean {
    const attackPatterns = [
      /<script/i,
      /javascript:/i,
      /onload=/i,
      /onerror=/i,
      /\.\.\/\.\.\//,
      /etc\/passwd/,
      /bin\/sh/,
      /cmd\.exe/,
      /union.*select/i,
      /drop.*table/i,
      /'.*or.*'/i,
    ];
    
    return attackPatterns.some(pattern => pattern.test(url));
  }

  /**
   * Validate host header
   */
  private isValidHost(host: string): boolean {
    const allowedHosts = [
      'localhost',
      '127.0.0.1',
      'portal.dotmac.com',
      'admin.dotmac.com',
      'reseller.dotmac.com',
      'technician.dotmac.com',
    ];
    
    return allowedHosts.includes(host.split(':')[0]);
  }

  /**
   * Check if request is sensitive (requires CSRF protection)
   */
  private isSensitiveRequest(request: NextRequest): boolean {
    const method = request.method.toLowerCase();
    const path = new URL(request.url).pathname;
    
    // All state-changing methods are sensitive
    if (['post', 'put', 'patch', 'delete'].includes(method)) {
      return true;
    }
    
    // Specific sensitive paths
    const sensitivePaths = [
      '/api/auth/',
      '/api/admin/',
      '/api/billing/',
      '/api/account/',
    ];
    
    return sensitivePaths.some(sensitive => path.startsWith(sensitive));
  }

  /**
   * Check if request is stateful
   */
  private isStatefulRequest(request: NextRequest): boolean {
    return ['POST', 'PUT', 'PATCH', 'DELETE'].includes(request.method);
  }

  /**
   * Extract CSRF token from request
   */
  private extractCSRFToken(request: NextRequest): string | null {
    // Check header first
    const headerToken = request.headers.get('x-csrf-token');
    if (headerToken) return headerToken;
    
    // Check form data or JSON body (would need to be parsed)
    return null;
  }

  /**
   * Get session token from request
   */
  private getSessionToken(request: NextRequest): string | null {
    const cookieStore = request.cookies;
    return cookieStore.get(this.config.sessionConfig.cookieName)?.value || null;
  }

  /**
   * Validate CSRF token
   */
  private validateCSRFToken(token: string, sessionToken: string): boolean {
    // Implementation would verify token against session
    // For now, just check if both exist
    return Boolean(token && sessionToken);
  }

  /**
   * Generate unique request ID
   */
  private generateRequestId(): string {
    return `req_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
  }

  /**
   * Log security events
   */
  private logSecurityEvent(type: string, context: any): void {
    console.warn(`[Security] ${type}:`, JSON.stringify(context, null, 2));
    
    // In production, this would send to monitoring service
    if (this.config.environment === 'production') {
      // Send to external monitoring/SIEM
      this.sendToMonitoring(type, context);
    }
  }

  /**
   * Log security metrics
   */
  private logSecurityMetrics(request: NextRequest, response: NextResponse, duration: number): void {
    const metrics = {
      path: new URL(request.url).pathname,
      method: request.method,
      status: response.status,
      duration,
      ip: this.getClientIP(request),
      userAgent: request.headers.get('user-agent'),
      timestamp: Date.now(),
    };
    
    // In production, send metrics to monitoring service
    if (this.config.environment === 'production') {
      this.sendMetrics(metrics);
    }
  }

  /**
   * Send events to monitoring service
   */
  private async sendToMonitoring(type: string, context: any): Promise<void> {
    try {
      await fetch('/api/monitoring/security-events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ type, context, timestamp: Date.now() }),
      });
    } catch (error) {
      console.error('Failed to send security event to monitoring:', error);
    }
  }

  /**
   * Send metrics to monitoring service
   */
  private async sendMetrics(metrics: any): Promise<void> {
    try {
      await fetch('/api/monitoring/metrics', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(metrics),
      });
    } catch (error) {
      console.error('Failed to send metrics to monitoring:', error);
    }
  }

  /**
   * Setup periodic cleanup of rate limit store
   */
  private setupCleanupInterval(): void {
    setInterval(() => {
      const now = Date.now();
      for (const [key, record] of this.rateLimitStore.entries()) {
        if (now > record.resetTime) {
          this.rateLimitStore.delete(key);
        }
      }
    }, 60000); // Cleanup every minute
  }

  /**
   * Add IP to blocklist
   */
  blockIP(ip: string): void {
    this.blockedIPs.add(ip);
    this.logSecurityEvent('ip-blocked', { ip });
  }

  /**
   * Remove IP from blocklist
   */
  unblockIP(ip: string): void {
    this.blockedIPs.delete(ip);
    this.logSecurityEvent('ip-unblocked', { ip });
  }

  /**
   * Add custom rate limit rule
   */
  addRateLimitRule(rule: RateLimitRule): void {
    this.rateLimitRules.push(rule);
  }
}

/**
 * Security error class
 */
class SecurityError extends Error {
  constructor(
    public type: string,
    message: string,
    public context?: any
  ) {
    super(message);
    this.name = 'SecurityError';
  }
}

/**
 * Default configuration for ISP portals
 */
export const DEFAULT_SECURITY_CONFIG: SecurityMiddlewareConfig = {
  environment: 'production',
  enableCSRF: true,
  enableRateLimiting: true,
  allowedOrigins: [
    'https://portal.dotmac.com',
    'https://admin.dotmac.com',
    'https://reseller.dotmac.com',
    'https://technician.dotmac.com',
  ],
  trustedProxies: [
    '10.0.0.0/8',
    '172.16.0.0/12',
    '192.168.0.0/16',
  ],
  sessionConfig: {
    cookieName: 'dotmac-session',
    maxAge: 24 * 60 * 60 * 1000, // 24 hours
    secure: true,
    sameSite: 'strict',
  },
};

export type { SecurityMiddlewareConfig, RateLimitRule };