/**
 * Middleware Behavior Validation Tests
 * Tests the updated middleware that returns JSON instead of redirects
 */

import { NextRequest, NextResponse } from 'next/server';
import { middleware } from '../middleware';

// Mock dependencies
jest.mock('@dotmac/headless/utils/csp', () => ({
  generateCSP: jest.fn(() => "default-src 'self'"),
  generateNonce: jest.fn(() => 'test-nonce-123'),
}));

jest.mock('@dotmac/monitoring', () => ({
  audit: {
    security: jest.fn(),
  },
  auditContext: {
    fromRequest: jest.fn(() => ({
      traceId: 'test-trace-id',
      correlationId: 'test-correlation-id',
      userAgent: 'test-user-agent',
    })),
  },
}));

describe('Customer Portal Middleware', () => {
  const createMockRequest = (
    url: string,
    options: {
      cookies?: Record<string, string>;
      headers?: Record<string, string>;
      method?: string;
    } = {}
  ) => {
    const request = new NextRequest(url, {
      method: options.method || 'GET',
      headers: new Headers({
        'user-agent': 'test-user-agent',
        'x-forwarded-for': '127.0.0.1',
        ...options.headers,
      }),
    });

    // Mock cookies
    if (options.cookies) {
      Object.entries(options.cookies).forEach(([key, value]) => {
        request.cookies.set(key, value);
      });
    }

    return request;
  };

  describe('Authentication Middleware Behavior', () => {
    it('should return 401 JSON response for missing auth token on protected route', async () => {
      const request = createMockRequest('http://localhost:3000/dashboard');
      const response = await middleware(request);

      expect(response).toBeInstanceOf(NextResponse);
      expect(response.status).toBe(401);

      const responseBody = await response.json();
      expect(responseBody).toEqual({
        error: 'Authentication required',
        redirect: '/?redirect=' + encodeURIComponent('/dashboard'),
      });
    });

    it('should allow access to public routes without authentication', async () => {
      const publicRoutes = ['/', '/login', '/register', '/forgot-password', '/reset-password'];

      for (const route of publicRoutes) {
        const request = createMockRequest(`http://localhost:3000${route}`);
        const response = await middleware(request);

        // Should continue to next middleware or return OK response
        expect(response.status).not.toBe(401);
        expect(response.status).not.toBe(403);
      }
    });

    it('should return 403 JSON response for wrong portal type', async () => {
      const request = createMockRequest('http://localhost:3000/dashboard', {
        cookies: {
          'secure-auth-token': 'valid-token',
          'portal-type': 'admin', // Wrong portal type for customer app
        },
      });

      const response = await middleware(request);

      expect(response.status).toBe(403);

      const responseBody = await response.json();
      expect(responseBody).toEqual({
        error: 'Access denied - incorrect portal type',
        redirect: '/unauthorized',
      });
    });

    it('should allow access with correct authentication and portal type', async () => {
      const request = createMockRequest('http://localhost:3000/dashboard', {
        cookies: {
          'secure-auth-token': 'valid-token',
          'portal-type': 'customer',
        },
      });

      const response = await middleware(request);

      // Should continue with security headers
      expect(response.status).toBe(200);
      expect(response.headers.get('Content-Security-Policy')).toBeTruthy();
      expect(response.headers.get('X-Frame-Options')).toBe('DENY');
    });
  });

  describe('CSRF Protection', () => {
    it('should validate CSRF token for POST requests', async () => {
      const request = createMockRequest('http://localhost:3000/api/update', {
        method: 'POST',
        cookies: {
          'secure-auth-token': 'valid-token',
          'portal-type': 'customer',
          'csrf-token': 'valid-csrf-token',
        },
        headers: {
          'x-csrf-token': 'invalid-csrf-token', // Mismatched token
        },
      });

      const response = await middleware(request);

      expect(response.status).toBe(403);

      const responseBody = await response.json();
      expect(responseBody).toEqual({
        error: 'CSRF token mismatch',
      });
    });

    it('should allow POST requests with valid CSRF token', async () => {
      const request = createMockRequest('http://localhost:3000/api/update', {
        method: 'POST',
        cookies: {
          'secure-auth-token': 'valid-token',
          'portal-type': 'customer',
          'csrf-token': 'valid-csrf-token',
        },
        headers: {
          'x-csrf-token': 'valid-csrf-token',
        },
      });

      const response = await middleware(request);

      // Should continue processing
      expect(response.status).toBe(200);
    });

    it('should skip CSRF validation for GET requests', async () => {
      const request = createMockRequest('http://localhost:3000/dashboard', {
        method: 'GET',
        cookies: {
          'secure-auth-token': 'valid-token',
          'portal-type': 'customer',
        },
        // No CSRF token needed for GET requests
      });

      const response = await middleware(request);

      expect(response.status).toBe(200);
    });
  });

  describe('Security Headers', () => {
    it('should add comprehensive security headers', async () => {
      const request = createMockRequest('http://localhost:3000/', {
        cookies: {
          'secure-auth-token': 'valid-token',
          'portal-type': 'customer',
        },
      });

      const response = await middleware(request);

      // Check all security headers
      expect(response.headers.get('X-Frame-Options')).toBe('DENY');
      expect(response.headers.get('X-Content-Type-Options')).toBe('nosniff');
      expect(response.headers.get('Referrer-Policy')).toBe('strict-origin-when-cross-origin');
      expect(response.headers.get('Permissions-Policy')).toBeTruthy();
      expect(response.headers.get('Content-Security-Policy')).toBeTruthy();

      // CSP should include nonce
      const csp = response.headers.get('Content-Security-Policy');
      expect(csp).toContain('nonce-test-nonce-123');
    });

    it('should set strict CSP for customer portal', async () => {
      const request = createMockRequest('http://localhost:3000/dashboard');

      const response = await middleware(request);

      const csp = response.headers.get('Content-Security-Policy');
      expect(csp).toBeTruthy();
      expect(csp).toContain("default-src 'self'");
    });
  });

  describe('Rate Limiting Removal', () => {
    it('should not perform client-side rate limiting', async () => {
      const request = createMockRequest('http://localhost:3000/login', {
        method: 'POST',
      });

      const response = await middleware(request);

      // Should not return 429 from middleware (handled by server)
      expect(response.status).not.toBe(429);

      // Should not have rate limit headers from middleware
      expect(response.headers.get('X-RateLimit-Limit')).toBeNull();
      expect(response.headers.get('X-RateLimit-Remaining')).toBeNull();
      expect(response.headers.get('Retry-After')).toBeNull();
    });

    it('should focus on security headers and authentication only', async () => {
      const request = createMockRequest('http://localhost:3000/api/auth/login', {
        method: 'POST',
      });

      const response = await middleware(request);

      // Should add security headers
      expect(response.headers.get('Content-Security-Policy')).toBeTruthy();

      // Should not add rate limiting headers (delegated to server)
      expect(response.headers.get('X-RateLimit-Limit')).toBeNull();
    });
  });

  describe('Audit Logging', () => {
    it('should log security events for unauthorized access', async () => {
      const { audit } = require('@dotmac/monitoring');

      const request = createMockRequest('http://localhost:3000/dashboard');
      await middleware(request);

      expect(audit.security).toHaveBeenCalledWith(
        'unauthorized_access_attempt',
        expect.objectContaining({
          traceId: 'test-trace-id',
          correlationId: 'test-correlation-id',
        }),
        'medium',
        false
      );
    });

    it('should log portal type mismatches', async () => {
      const { audit } = require('@dotmac/monitoring');

      const request = createMockRequest('http://localhost:3000/dashboard', {
        cookies: {
          'secure-auth-token': 'valid-token',
          'portal-type': 'admin',
        },
      });

      await middleware(request);

      expect(audit.security).toHaveBeenCalledWith(
        'portal_type_mismatch',
        expect.objectContaining({
          userId: 'valid-token',
        }),
        'medium',
        false
      );
    });
  });

  describe('Error Response Format', () => {
    it('should return consistent JSON error format', async () => {
      const request = createMockRequest('http://localhost:3000/dashboard');
      const response = await middleware(request);

      expect(response.status).toBe(401);
      expect(response.headers.get('Content-Type')).toContain('application/json');

      const responseBody = await response.json();
      expect(responseBody).toHaveProperty('error');
      expect(typeof responseBody.error).toBe('string');
    });

    it('should include redirect information in error responses', async () => {
      const request = createMockRequest('http://localhost:3000/billing');
      const response = await middleware(request);

      const responseBody = await response.json();
      expect(responseBody).toHaveProperty('redirect');
      expect(responseBody.redirect).toContain('billing');
    });

    it('should not expose sensitive information in error responses', async () => {
      const request = createMockRequest('http://localhost:3000/dashboard', {
        cookies: {
          'secure-auth-token': 'expired-or-invalid-token',
          'portal-type': 'customer',
        },
      });

      const response = await middleware(request);
      const responseBody = await response.json();

      // Should not expose token details or internal errors
      expect(JSON.stringify(responseBody)).not.toContain('expired-or-invalid-token');
      expect(responseBody.error).not.toContain('token');
      expect(responseBody.error).not.toContain('database');
      expect(responseBody.error).not.toContain('internal');
    });
  });

  describe('Performance and Reliability', () => {
    it('should handle malformed requests gracefully', async () => {
      const request = createMockRequest('http://localhost:3000/dashboard', {
        headers: {
          'x-malformed-header': '\\x00\\x01\\x02', // Binary data
        },
      });

      const response = await middleware(request);

      // Should still process the request
      expect(response).toBeInstanceOf(NextResponse);
      expect(response.status).toBe(401); // Expected for no auth
    });

    it('should handle missing cookies gracefully', async () => {
      const request = createMockRequest('http://localhost:3000/dashboard');
      // No cookies set

      const response = await middleware(request);

      expect(response.status).toBe(401);
      const responseBody = await response.json();
      expect(responseBody.error).toBe('Authentication required');
    });

    it('should be fast and not block requests unnecessarily', async () => {
      const start = Date.now();

      const request = createMockRequest('http://localhost:3000/', {
        cookies: {
          'secure-auth-token': 'valid-token',
          'portal-type': 'customer',
        },
      });

      await middleware(request);

      const duration = Date.now() - start;
      expect(duration).toBeLessThan(50); // Should be very fast
    });
  });
});
