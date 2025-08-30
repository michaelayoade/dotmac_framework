/**
 * Comprehensive Security Test Suite
 * Production-level security testing with 90% coverage target
 * Leverages existing unified architecture for DRY patterns
 */

import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { createCSRFMiddleware } from '../csrf-protection';
import { SecurityMiddleware } from '../middleware/SecurityMiddleware';
import { InputSanitizer } from '../sanitization/input-sanitizer';
import { SecurityHeaders } from '../headers/SecurityHeaders';
import { useSanitizedInput } from '../hooks/useSanitizedInput';
import { TestWrapper } from '@dotmac/testing';

// Mock implementations leveraging unified patterns
const mockRequest = (overrides = {}) => ({
  headers: new Headers(),
  method: 'GET',
  url: 'https://example.com',
  json: jest.fn(),
  text: jest.fn(),
  ...overrides
});

const mockResponse = () => ({
  headers: new Headers(),
  status: 200,
  json: jest.fn(),
  text: jest.fn(),
  setHeader: jest.fn(),
  getHeader: jest.fn(),
  writeHead: jest.fn(),
  end: jest.fn()
});

describe('🔒 CSRF Protection Suite', () => {
  let middleware: any;
  let req: any;
  let res: any;

  beforeEach(() => {
    middleware = createCSRFMiddleware({
      secret: 'test-secret-key-for-testing-only',
      cookieName: 'csrf-token',
      headerName: 'X-CSRF-Token'
    });
    req = mockRequest();
    res = mockResponse();
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('Token Generation', () => {
    it('should generate valid CSRF tokens', async () => {
      const token = await middleware.generateToken();

      expect(token).toBeTruthy();
      expect(typeof token).toBe('string');
      expect(token.length).toBeGreaterThan(20);
    });

    it('should generate unique tokens per request', async () => {
      const token1 = await middleware.generateToken();
      const token2 = await middleware.generateToken();

      expect(token1).not.toBe(token2);
    });

    it('should create tokens with proper entropy', async () => {
      const tokens = await Promise.all(
        Array(10).fill(0).map(() => middleware.generateToken())
      );

      const uniqueTokens = new Set(tokens);
      expect(uniqueTokens.size).toBe(10);
    });
  });

  describe('Token Validation', () => {
    it('should validate correct CSRF tokens', async () => {
      const token = await middleware.generateToken();
      req.headers.set('X-CSRF-Token', token);
      req.method = 'POST';

      const isValid = await middleware.validateToken(req);
      expect(isValid).toBe(true);
    });

    it('should reject invalid CSRF tokens', async () => {
      req.headers.set('X-CSRF-Token', 'invalid-token');
      req.method = 'POST';

      const isValid = await middleware.validateToken(req);
      expect(isValid).toBe(false);
    });

    it('should reject missing tokens for POST requests', async () => {
      req.method = 'POST';

      const isValid = await middleware.validateToken(req);
      expect(isValid).toBe(false);
    });

    it('should allow GET requests without tokens', async () => {
      req.method = 'GET';

      const isValid = await middleware.validateToken(req);
      expect(isValid).toBe(true);
    });
  });

  describe('Middleware Integration', () => {
    it('should set CSRF token in response headers', async () => {
      await middleware(req, res, jest.fn());

      expect(res.setHeader).toHaveBeenCalledWith(
        'X-CSRF-Token',
        expect.any(String)
      );
    });

    it('should block requests with invalid tokens', async () => {
      req.method = 'POST';
      req.headers.set('X-CSRF-Token', 'invalid');

      await middleware(req, res, jest.fn());

      expect(res.writeHead).toHaveBeenCalledWith(403);
    });
  });
});

describe('🛡️ Input Sanitization Suite', () => {
  let sanitizer: InputSanitizer;

  beforeEach(() => {
    sanitizer = new InputSanitizer({
      allowedTags: ['p', 'br', 'strong', 'em'],
      allowedAttributes: { '*': ['class'] }
    });
  });

  describe('XSS Prevention', () => {
    it('should remove script tags', () => {
      const maliciousInput = '<script>alert("xss")</script><p>Safe content</p>';
      const sanitized = sanitizer.sanitize(maliciousInput);

      expect(sanitized).not.toContain('<script>');
      expect(sanitized).not.toContain('alert');
      expect(sanitized).toContain('<p>Safe content</p>');
    });

    it('should neutralize javascript: URLs', () => {
      const maliciousInput = '<a href="javascript:alert(1)">Click me</a>';
      const sanitized = sanitizer.sanitize(maliciousInput);

      expect(sanitized).not.toContain('javascript:');
      expect(sanitized).not.toContain('alert');
    });

    it('should handle event handlers', () => {
      const maliciousInput = '<p onclick="alert(1)">Content</p>';
      const sanitized = sanitizer.sanitize(maliciousInput);

      expect(sanitized).not.toContain('onclick');
      expect(sanitized).not.toContain('alert');
      expect(sanitized).toContain('Content');
    });

    it('should preserve safe HTML', () => {
      const safeInput = '<p class="highlight"><strong>Important</strong> info</p>';
      const sanitized = sanitizer.sanitize(safeInput);

      expect(sanitized).toBe(safeInput);
    });
  });

  describe('SQL Injection Prevention', () => {
    it('should escape SQL injection attempts in text', () => {
      const sqlInput = "'; DROP TABLE users; --";
      const sanitized = sanitizer.sanitizeText(sqlInput);

      expect(sanitized).not.toContain('DROP TABLE');
      expect(sanitized).not.toContain('--');
    });

    it('should handle parameterized query patterns', () => {
      const input = "user'; DELETE FROM accounts WHERE 1=1; --";
      const sanitized = sanitizer.sanitizeText(input);

      expect(sanitized).not.toContain('DELETE');
      expect(sanitized).not.toContain('WHERE 1=1');
    });
  });

  describe('Data Type Validation', () => {
    it('should validate email formats', () => {
      expect(sanitizer.validateEmail('test@example.com')).toBe(true);
      expect(sanitizer.validateEmail('invalid-email')).toBe(false);
      expect(sanitizer.validateEmail('test@')).toBe(false);
      expect(sanitizer.validateEmail('@example.com')).toBe(false);
    });

    it('should validate phone numbers', () => {
      expect(sanitizer.validatePhone('+1-555-123-4567')).toBe(true);
      expect(sanitizer.validatePhone('(555) 123-4567')).toBe(true);
      expect(sanitizer.validatePhone('invalid-phone')).toBe(false);
      expect(sanitizer.validatePhone('123')).toBe(false);
    });

    it('should validate numeric ranges', () => {
      expect(sanitizer.validateNumber('123', { min: 100, max: 200 })).toBe(true);
      expect(sanitizer.validateNumber('50', { min: 100, max: 200 })).toBe(false);
      expect(sanitizer.validateNumber('250', { min: 100, max: 200 })).toBe(false);
    });
  });
});

describe('🔐 Security Headers Suite', () => {
  let securityHeaders: SecurityHeaders;
  let mockRes: any;

  beforeEach(() => {
    securityHeaders = new SecurityHeaders();
    mockRes = mockResponse();
  });

  describe('CSP Headers', () => {
    it('should set Content Security Policy', () => {
      securityHeaders.setCSP(mockRes, {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'"],
        'style-src': ["'self'", "'unsafe-inline'"]
      });

      expect(mockRes.setHeader).toHaveBeenCalledWith(
        'Content-Security-Policy',
        expect.stringContaining("default-src 'self'")
      );
    });

    it('should handle nonce generation for CSP', () => {
      const nonce = securityHeaders.generateNonce();

      expect(nonce).toBeTruthy();
      expect(typeof nonce).toBe('string');
      expect(nonce.length).toBeGreaterThan(10);
    });

    it('should set strict CSP for production', () => {
      securityHeaders.setStrictCSP(mockRes);

      const cspCall = mockRes.setHeader.mock.calls.find(
        call => call[0] === 'Content-Security-Policy'
      );

      expect(cspCall).toBeTruthy();
      expect(cspCall[1]).toContain("default-src 'self'");
      expect(cspCall[1]).not.toContain("'unsafe-eval'");
    });
  });

  describe('Security Headers', () => {
    it('should set HSTS headers', () => {
      securityHeaders.setHSTS(mockRes);

      expect(mockRes.setHeader).toHaveBeenCalledWith(
        'Strict-Transport-Security',
        'max-age=31536000; includeSubDomains; preload'
      );
    });

    it('should set X-Frame-Options', () => {
      securityHeaders.setFrameOptions(mockRes, 'DENY');

      expect(mockRes.setHeader).toHaveBeenCalledWith(
        'X-Frame-Options',
        'DENY'
      );
    });

    it('should set X-Content-Type-Options', () => {
      securityHeaders.setContentTypeOptions(mockRes);

      expect(mockRes.setHeader).toHaveBeenCalledWith(
        'X-Content-Type-Options',
        'nosniff'
      );
    });

    it('should set comprehensive security headers', () => {
      securityHeaders.setAllHeaders(mockRes);

      const expectedHeaders = [
        'Strict-Transport-Security',
        'X-Frame-Options',
        'X-Content-Type-Options',
        'X-XSS-Protection',
        'Referrer-Policy'
      ];

      expectedHeaders.forEach(header => {
        expect(mockRes.setHeader).toHaveBeenCalledWith(
          header,
          expect.any(String)
        );
      });
    });
  });
});

describe('⚡ Security Middleware Integration', () => {
  let middleware: SecurityMiddleware;
  let req: any;
  let res: any;
  let next: jest.Mock;

  beforeEach(() => {
    middleware = new SecurityMiddleware({
      csrfProtection: true,
      rateLimiting: true,
      inputSanitization: true
    });
    req = mockRequest();
    res = mockResponse();
    next = jest.fn();
  });

  describe('Request Processing', () => {
    it('should process GET requests successfully', async () => {
      req.method = 'GET';

      await middleware.process(req, res, next);

      expect(next).toHaveBeenCalled();
      expect(res.writeHead).not.toHaveBeenCalledWith(403);
    });

    it('should validate POST requests with CSRF', async () => {
      req.method = 'POST';
      req.headers.set('X-CSRF-Token', 'valid-token');

      // Mock token validation to pass
      jest.spyOn(middleware as any, 'validateCSRF').mockResolvedValue(true);

      await middleware.process(req, res, next);

      expect(next).toHaveBeenCalled();
    });

    it('should block requests exceeding rate limits', async () => {
      // Mock rate limiter to reject
      jest.spyOn(middleware as any, 'checkRateLimit').mockResolvedValue(false);

      await middleware.process(req, res, next);

      expect(res.writeHead).toHaveBeenCalledWith(429);
      expect(next).not.toHaveBeenCalled();
    });
  });

  describe('Input Sanitization Integration', () => {
    it('should sanitize request body', async () => {
      req.json = jest.fn().mockResolvedValue({
        message: '<script>alert("xss")</script>Safe content',
        email: 'user@example.com'
      });

      await middleware.process(req, res, next);

      expect(req.sanitizedBody).toBeDefined();
      expect(req.sanitizedBody.message).not.toContain('<script>');
      expect(req.sanitizedBody.message).toContain('Safe content');
      expect(req.sanitizedBody.email).toBe('user@example.com');
    });

    it('should validate input data types', async () => {
      req.json = jest.fn().mockResolvedValue({
        email: 'invalid-email',
        phone: '123',
        age: 'not-a-number'
      });

      await middleware.process(req, res, next);

      expect(req.validationErrors).toBeDefined();
      expect(req.validationErrors.length).toBeGreaterThan(0);
    });
  });
});

describe('🎣 useSanitizedInput Hook', () => {
  const TestComponent = ({ initialValue = '' }) => {
    const { value, setValue, sanitizedValue, errors } = useSanitizedInput(initialValue, {
      type: 'text',
      maxLength: 100,
      allowedTags: ['p', 'strong']
    });

    return (
      <div>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          data-testid="input"
        />
        <div data-testid="sanitized">{sanitizedValue}</div>
        <div data-testid="errors">{JSON.stringify(errors)}</div>
      </div>
    );
  };

  it('should sanitize input in real-time', async () => {
    render(<TestComponent />, { wrapper: TestWrapper });

    const input = screen.getByTestId('input');
    const sanitized = screen.getByTestId('sanitized');

    fireEvent.change(input, {
      target: { value: '<script>alert("xss")</script><p>Safe</p>' }
    });

    await waitFor(() => {
      expect(sanitized.textContent).not.toContain('<script>');
      expect(sanitized.textContent).toContain('Safe');
    });
  });

  it('should validate input constraints', async () => {
    render(<TestComponent />, { wrapper: TestWrapper });

    const input = screen.getByTestId('input');
    const errors = screen.getByTestId('errors');

    // Test max length validation
    fireEvent.change(input, {
      target: { value: 'a'.repeat(150) }
    });

    await waitFor(() => {
      const errorData = JSON.parse(errors.textContent || '[]');
      expect(errorData).toContain('Input exceeds maximum length');
    });
  });

  it('should handle different input types', async () => {
    const EmailComponent = () => {
      const { value, setValue, errors } = useSanitizedInput('', {
        type: 'email'
      });

      return (
        <div>
          <input
            value={value}
            onChange={(e) => setValue(e.target.value)}
            data-testid="email-input"
          />
          <div data-testid="email-errors">{JSON.stringify(errors)}</div>
        </div>
      );
    };

    render(<EmailComponent />, { wrapper: TestWrapper });

    const input = screen.getByTestId('email-input');
    const errors = screen.getByTestId('email-errors');

    fireEvent.change(input, { target: { value: 'invalid-email' } });

    await waitFor(() => {
      const errorData = JSON.parse(errors.textContent || '[]');
      expect(errorData.some((error: string) => error.includes('email'))).toBe(true);
    });
  });
});
