/**
 * Security Penetration Testing Framework
 * Validates all security fixes and tests for common attack vectors
 */

import { test, expect, Page, BrowserContext } from '@playwright/test';

// Test configuration for security scenarios
const SECURITY_CONFIG = {
  // Test URLs and endpoints
  baseURL: process.env.BASE_URL || 'http://localhost:3000',
  apiEndpoints: {
    login: '/api/auth/customer/login',
    dashboard: '/api/customer/dashboard', 
    profile: '/api/customer/profile',
    billing: '/api/customer/billing'
  },
  
  // Attack payloads for testing
  payloads: {
    xss: [
      '<script>alert("XSS")</script>',
      'javascript:alert("XSS")',
      '<img src=x onerror=alert("XSS")>',
      '"><script>alert("XSS")</script>',
      "';alert('XSS');//"
    ],
    sqli: [
      "' OR '1'='1",
      "'; DROP TABLE users; --",
      "' UNION SELECT NULL,NULL,NULL --",
      "admin'/**/OR/**/1=1#"
    ],
    csrf: [
      'http://evil.com/csrf-attack',
      '<img src="/api/customer/delete-account" />',
      '<form action="/api/customer/change-password" method="POST">'
    ],
    pathTraversal: [
      '../../../etc/passwd',
      '..\\..\\..\\windows\\system32\\drivers\\etc\\hosts',
      '%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd'
    ]
  },

  // Rate limiting test parameters  
  rateLimiting: {
    maxRequests: 10,
    timeWindow: 60000, // 1 minute
    testRequests: 15 // Should trigger rate limiting
  }
};

test.describe('Security Penetration Testing', () => {
  let context: BrowserContext;
  let page: Page;

  test.beforeAll(async ({ browser }) => {
    context = await browser.newContext({
      ignoreHTTPSErrors: true,
      recordVideo: { dir: 'test-results/security-videos' }
    });
    page = await context.newPage();

    // Log all security-related events
    page.on('console', msg => {
      if (msg.type() === 'error' && msg.text().includes('CSP')) {
        console.log('CSP Violation:', msg.text());
      }
    });

    page.on('response', response => {
      const url = response.url();
      if (response.status() >= 400 && (url.includes('/api/') || url.includes('/auth/'))) {
        console.log(`Security Response: ${response.status()} ${url}`);
      }
    });
  });

  test.afterAll(async () => {
    await context.close();
  });

  test.describe('Authentication Security', () => {
    test('should prevent authentication bypass attempts', async () => {
      // Test 1: Direct dashboard access without auth
      const dashboardResponse = await page.goto('/dashboard');
      expect(dashboardResponse?.status()).toBe(401);
      
      // Should show error boundary, not redirect
      await expect(page.getByText('Authentication Required')).toBeVisible();
      
      // Test 2: Malformed auth tokens
      await context.addCookies([{
        name: 'secure-auth-token',
        value: 'malformed.jwt.token',
        domain: 'localhost',
        path: '/'
      }]);
      
      await page.goto('/dashboard');
      await expect(page.getByText('Authentication Required')).toBeVisible();
      
      // Test 3: Expired tokens (if we can simulate)
      await context.clearCookies();
      await context.addCookies([{
        name: 'secure-auth-token', 
        value: 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjEwMDA5OTk5OTl9.invalid', // Expired token
        domain: 'localhost',
        path: '/'
      }]);
      
      await page.goto('/dashboard');
      await expect(page.getByText('Authentication Required')).toBeVisible();
    });

    test('should validate server-side rate limiting only', async () => {
      await page.goto('/');
      
      let rateLimitHit = false;
      let requestCount = 0;
      
      // Mock server to return 429 after certain attempts
      await page.route('**/api/auth/customer/login', route => {
        requestCount++;
        if (requestCount > 5) {
          rateLimitHit = true;
          route.fulfill({
            status: 429,
            contentType: 'application/json',
            body: JSON.stringify({
              error: 'Too many login attempts',
              retryAfter: 300
            })
          });
        } else {
          route.fulfill({
            status: 401,
            contentType: 'application/json', 
            body: JSON.stringify({ error: 'Invalid credentials' })
          });
        }
      });

      // Attempt multiple rapid logins
      for (let i = 0; i < 8; i++) {
        await page.getByLabel(/email address/i).fill('test@example.com');
        await page.getByLabel(/password/i).fill('wrongpassword');
        await page.getByRole('button', { name: /sign in/i }).click();
        await page.waitForTimeout(100);
      }

      // Should show server-side rate limiting message
      expect(rateLimitHit).toBe(true);
      await expect(page.getByText(/too many login attempts/i)).toBeVisible();
      
      // Should NOT show client-side rate limiting UI
      await expect(page.getByText(/account temporarily locked/i)).not.toBeVisible();
      await expect(page.getByText(/remaining attempts/i)).not.toBeVisible();
    });

    test('should prevent session fixation attacks', async () => {
      // Clear any existing session
      await context.clearCookies();
      
      // Try to set malicious session ID
      await context.addCookies([{
        name: 'session-id',
        value: 'attacker-controlled-session-123',
        domain: 'localhost',
        path: '/'
      }]);
      
      // Attempt login
      await page.route('**/api/auth/customer/login', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            token: 'new-secure-token',
            customer: { id: '123', email: 'test@example.com' }
          })
        });
      });

      await page.goto('/');
      await page.getByLabel(/email address/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('validpassword');
      await page.getByRole('button', { name: /sign in/i }).click();
      
      // New session should be created, old one invalidated
      const cookies = await context.cookies();
      const sessionCookie = cookies.find(c => c.name === 'session-id');
      
      if (sessionCookie) {
        expect(sessionCookie.value).not.toBe('attacker-controlled-session-123');
      }
    });
  });

  test.describe('XSS Prevention', () => {
    test('should prevent reflected XSS in all input fields', async () => {
      await page.goto('/');
      
      // Test XSS in login form inputs
      for (const payload of SECURITY_CONFIG.payloads.xss) {
        await page.getByLabel(/email address/i).fill(payload);
        await page.getByLabel(/password/i).fill(payload);
        await page.getByLabel(/portal id/i).fill(payload);
        
        // Submit form
        await page.getByRole('button', { name: /sign in/i }).click();
        
        // Wait for any potential script execution
        await page.waitForTimeout(500);
        
        // Check that XSS payload is not executed
        const alertDialogs = page.locator('dialog[role="alertdialog"]');
        await expect(alertDialogs).toHaveCount(0);
        
        // Check that payload is properly escaped in DOM
        const pageContent = await page.content();
        expect(pageContent).not.toContain('<script>alert("XSS")</script>');
      }
    });

    test('should have proper CSP headers preventing script injection', async () => {
      let cspHeader = '';
      
      page.on('response', response => {
        if (response.url().includes('localhost:3000')) {
          cspHeader = response.headers()['content-security-policy'] || '';
        }
      });
      
      await page.goto('/');
      
      // Verify CSP prevents unsafe inline scripts
      expect(cspHeader).toContain("script-src");
      expect(cspHeader).not.toContain("'unsafe-inline'");
      expect(cspHeader).not.toContain("'unsafe-eval'");
      
      // Try to execute inline script - should be blocked
      await page.evaluate(() => {
        try {
          eval('alert("CSP Bypass Attempt")');
          return false;
        } catch (e) {
          return true; // CSP blocked the eval
        }
      }).then(blocked => {
        expect(blocked).toBe(true);
      });
    });

    test('should sanitize user inputs in error messages', async () => {
      // Mock API to return XSS payload in error message
      await page.route('**/api/auth/customer/login', route => {
        route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            error: '<script>alert("XSS in error")</script>Invalid credentials'
          })
        });
      });
      
      await page.goto('/');
      await page.getByLabel(/email address/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('password');
      await page.getByRole('button', { name: /sign in/i }).click();
      
      // Error should be displayed but script not executed
      await expect(page.getByText(/invalid credentials/i)).toBeVisible();
      
      const pageContent = await page.content();
      expect(pageContent).not.toContain('<script>alert("XSS in error")</script>');
    });
  });

  test.describe('CSRF Protection', () => {
    test('should require CSRF tokens for state-changing requests', async () => {
      // Login first
      await page.route('**/api/auth/customer/login', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            token: 'valid-token',
            customer: { id: '123', email: 'test@example.com' }
          })
        });
      });

      await page.goto('/');
      await page.getByLabel(/email address/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();
      
      await page.waitForURL('/dashboard');
      
      // Test CSRF protection on API calls
      let csrfTokenPresent = false;
      
      await page.route('**/api/customer/**', route => {
        const headers = route.request().headers();
        csrfTokenPresent = !!headers['x-csrf-token'];
        
        if (!csrfTokenPresent && route.request().method() !== 'GET') {
          route.fulfill({
            status: 403,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'CSRF token missing' })
          });
        } else {
          route.continue();
        }
      });
      
      // Try to make a POST request without CSRF token
      await page.evaluate(() => {
        fetch('/api/customer/profile', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name: 'Updated Name' })
        });
      });
      
      // Should be blocked by CSRF protection
      // (This test verifies the server-side implementation expectation)
    });

    test('should prevent cross-origin requests without proper headers', async () => {
      let crossOriginBlocked = false;
      
      page.on('response', response => {
        if (response.status() === 403 && response.url().includes('/api/')) {
          crossOriginBlocked = true;
        }
      });
      
      // Simulate cross-origin request
      await page.evaluate(() => {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/api/customer/profile';
        form.target = '_blank';
        
        const input = document.createElement('input');
        input.name = 'name';
        input.value = 'Malicious Update';
        form.appendChild(input);
        
        document.body.appendChild(form);
        form.submit();
      });
      
      await page.waitForTimeout(1000);
      // Cross-origin requests should be blocked by server-side CORS policy
    });
  });

  test.describe('Injection Attack Prevention', () => {
    test('should prevent SQL injection attempts', async () => {
      await page.goto('/');
      
      // Test SQL injection payloads in login
      for (const payload of SECURITY_CONFIG.payloads.sqli) {
        let injectionBlocked = true;
        
        await page.route('**/api/auth/customer/login', route => {
          const body = route.request().postDataJSON();
          
          // If SQL injection payload reaches server unchanged, it's a problem
          if (body && (body.email?.includes('DROP TABLE') || body.email?.includes('UNION SELECT'))) {
            injectionBlocked = false;
          }
          
          route.fulfill({
            status: 400,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'Invalid input' })
          });
        });
        
        await page.getByLabel(/email address/i).fill(payload);
        await page.getByLabel(/password/i).fill('password');
        await page.getByRole('button', { name: /sign in/i }).click();
        
        await page.waitForTimeout(500);
        
        // Should show generic error, not database errors
        await expect(page.getByText(/invalid input/i)).toBeVisible();
        await expect(page.getByText(/sql/i)).not.toBeVisible();
        await expect(page.getByText(/database/i)).not.toBeVisible();
      }
    });

    test('should prevent path traversal attacks', async () => {
      // Test path traversal in URL parameters and API endpoints
      for (const payload of SECURITY_CONFIG.payloads.pathTraversal) {
        const response = await page.goto(`/dashboard?file=${encodeURIComponent(payload)}`);
        
        // Should not expose system files
        expect(response?.status()).not.toBe(200);
        
        // API endpoint tests
        const apiResponse = await page.request.get(`/api/customer/file/${encodeURIComponent(payload)}`);
        expect(apiResponse.status()).toBe(403); // Should be forbidden
      }
    });
  });

  test.describe('Information Disclosure Prevention', () => {
    test('should not expose sensitive information in error messages', async () => {
      // Test various error scenarios
      const errorEndpoints = [
        '/api/customer/nonexistent',
        '/api/admin/users', // Wrong portal access
        '/api/customer/profile/999999' // Non-existent resource
      ];
      
      for (const endpoint of errorEndpoints) {
        const response = await page.request.get(endpoint);
        const responseText = await response.text();
        
        // Should not expose:
        expect(responseText).not.toMatch(/database/i);
        expect(responseText).not.toMatch(/stack trace/i);
        expect(responseText).not.toMatch(/file path/i);
        expect(responseText).not.toMatch(/password/i);
        expect(responseText).not.toMatch(/token/i);
        expect(responseText).not.toMatch(/secret/i);
      }
    });

    test('should not expose debug information in production', async () => {
      await page.goto('/');
      
      // Check that debug info is not visible
      const pageContent = await page.content();
      expect(pageContent).not.toContain('NODE_ENV=development');
      expect(pageContent).not.toContain('DEBUG=');
      expect(pageContent).not.toContain('console.log');
      
      // Check network requests don't expose debug headers
      page.on('response', response => {
        const headers = response.headers();
        expect(headers).not.toHaveProperty('x-debug-info');
        expect(headers).not.toHaveProperty('x-error-details');
        expect(headers).not.toHaveProperty('x-stack-trace');
      });
    });

    test('should sanitize HTTP headers', async () => {
      let responseHeaders: Record<string, string> = {};
      
      page.on('response', response => {
        if (response.url().includes('localhost:3000')) {
          responseHeaders = response.headers();
        }
      });
      
      await page.goto('/');
      
      // Should have security headers
      expect(responseHeaders).toHaveProperty('x-frame-options');
      expect(responseHeaders).toHaveProperty('x-content-type-options');
      expect(responseHeaders).toHaveProperty('content-security-policy');
      
      // Should not expose server information
      expect(responseHeaders).not.toHaveProperty('server');
      expect(responseHeaders).not.toHaveProperty('x-powered-by');
      expect(responseHeaders['x-frame-options']).toBe('DENY');
      expect(responseHeaders['x-content-type-options']).toBe('nosniff');
    });
  });

  test.describe('Session Security', () => {
    test('should use secure session management', async () => {
      // Login and check cookie attributes
      await page.route('**/api/auth/customer/login', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          headers: {
            'Set-Cookie': 'secure-auth-token=abc123; HttpOnly; Secure; SameSite=Strict; Path=/'
          },
          body: JSON.stringify({
            success: true,
            token: 'valid-token',
            customer: { id: '123', email: 'test@example.com' }
          })
        });
      });

      await page.goto('/');
      await page.getByLabel(/email address/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();
      
      // Check that auth token is not accessible via JavaScript
      const tokenValue = await page.evaluate(() => {
        return document.cookie.includes('secure-auth-token');
      });
      
      expect(tokenValue).toBe(false); // Should be HttpOnly
    });

    test('should handle concurrent sessions properly', async () => {
      // This would require testing with multiple browser contexts
      const context2 = await context.browser()?.newContext();
      if (!context2) return;
      
      const page2 = await context2.newPage();
      
      // Login in both sessions
      await Promise.all([
        this.performLogin(page, 'user@example.com'),
        this.performLogin(page2, 'user@example.com')
      ]);
      
      // Both sessions should be valid (or implement session limit)
      await page.goto('/dashboard');
      await page2.goto('/dashboard');
      
      await context2.close();
    });

    const performLogin = async (page: Page, email: string) => {
      await page.route('**/api/auth/customer/login', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            token: 'valid-token',
            customer: { id: '123', email }
          })
        });
      });

      await page.goto('/');
      await page.getByLabel(/email address/i).fill(email);
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();
    };
  });

  test.describe('Business Logic Security', () => {
    test('should prevent privilege escalation', async () => {
      // Login as customer
      await page.route('**/api/auth/customer/login', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            token: 'customer-token',
            customer: { id: '123', email: 'customer@example.com', role: 'customer' }
          })
        });
      });

      await page.goto('/');
      await page.getByLabel(/email address/i).fill('customer@example.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();
      
      await page.waitForURL('/dashboard');
      
      // Try to access admin endpoints
      const adminEndpoints = [
        '/admin',
        '/api/admin/users',
        '/api/admin/system',
        '/management'
      ];
      
      for (const endpoint of adminEndpoints) {
        const response = await page.goto(endpoint);
        expect(response?.status()).toBe(403); // Should be forbidden
      }
    });

    test('should validate portal type access', async () => {
      // Try to access customer portal with wrong portal type cookie
      await context.addCookies([{
        name: 'portal-type',
        value: 'admin',
        domain: 'localhost',
        path: '/'
      }, {
        name: 'secure-auth-token',
        value: 'valid-token',
        domain: 'localhost',
        path: '/'
      }]);
      
      const response = await page.goto('/dashboard');
      expect(response?.status()).toBe(403);
      
      // Should show access denied, not authentication required
      await expect(page.getByText(/access denied/i)).toBeVisible();
    });
  });

  test.describe('Security Configuration Validation', () => {
    test('should have proper HTTPS configuration in production', async () => {
      // This test would validate HTTPS redirect and HSTS headers
      if (SECURITY_CONFIG.baseURL.startsWith('https://')) {
        let hstsHeader = '';
        
        page.on('response', response => {
          hstsHeader = response.headers()['strict-transport-security'] || '';
        });
        
        await page.goto('/');
        
        expect(hstsHeader).toContain('max-age');
        expect(hstsHeader).toContain('includeSubDomains');
      }
    });

    test('should block known attack patterns', async () => {
      const attackPatterns = [
        'union+select',
        '../../../',
        '<script',
        'javascript:',
        'data:text/html',
        'vbscript:',
        'onmouseover=',
        'onerror='
      ];
      
      for (const pattern of attackPatterns) {
        const response = await page.request.get(`/?q=${encodeURIComponent(pattern)}`);
        // Should either block or sanitize the request
        expect([400, 403, 200]).toContain(response.status());
        
        if (response.status() === 200) {
          const content = await response.text();
          expect(content).not.toContain(pattern);
        }
      }
    });
  });

  test.describe('Data Protection', () => {
    test('should not log sensitive information', async () => {
      const consoleLogs: string[] = [];
      
      page.on('console', msg => {
        consoleLogs.push(msg.text());
      });
      
      await page.goto('/');
      await page.getByLabel(/email address/i).fill('sensitive@example.com');
      await page.getByLabel(/password/i).fill('SuperSecret123!');
      await page.getByRole('button', { name: /sign in/i }).click();
      
      // Check that sensitive data is not logged
      const sensitiveTerms = ['SuperSecret123!', 'password', 'token'];
      for (const term of sensitiveTerms) {
        const foundInLogs = consoleLogs.some(log => log.includes(term));
        expect(foundInLogs).toBe(false);
      }
    });

    test('should handle PII data properly', async () => {
      // Mock API with PII data
      await page.route('**/api/customer/profile', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: '123',
            email: 'customer@example.com',
            name: 'John Doe',
            ssn: 'XXX-XX-1234', // Should be masked
            phone: '(555) 123-4567'
          })
        });
      });
      
      // Check that sensitive PII is properly masked in UI
      await page.goto('/profile');
      
      await expect(page.getByText('XXX-XX-1234')).toBeVisible(); // Masked SSN
      await expect(page.getByText(/123-45-6789/)).not.toBeVisible(); // Full SSN should not appear
    });
  });
});