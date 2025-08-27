/**
 * E2E Tests for Error Boundary Flows
 * Tests graceful error handling instead of hard redirects
 */

import { test, expect } from '@playwright/test';

test.describe('Error Boundary Authentication Flows', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test.describe('Authentication Error Boundaries', () => {
    test('should show authentication required UI instead of redirecting', async ({ page }) => {
      // Mock middleware to return 401 JSON response instead of redirect
      await page.route('**/dashboard', route => {
        route.fulfill({
          status: 401,
          contentType: 'application/json', 
          body: JSON.stringify({
            error: 'Authentication required',
            redirect: '/?redirect=' + encodeURIComponent('/dashboard')
          })
        });
      });

      // Try to access protected dashboard directly
      await page.goto('/dashboard');

      // Should show authentication required UI from AuthErrorProvider
      await expect(page.getByText('Authentication Required')).toBeVisible();
      await expect(page.getByText('Your session has expired or you need to log in')).toBeVisible();
      
      // Should have action buttons, not automatic redirect
      await expect(page.getByText('Go to Login')).toBeVisible();
      await expect(page.getByText('Retry')).toBeVisible();
    });

    test('should handle API authentication errors gracefully', async ({ page }) => {
      // First, log in successfully
      await page.route('**/api/auth/customer/login', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            token: 'valid-token',
            customer: { id: '123', email: 'test@example.com', name: 'Test User' }
          })
        });
      });

      await page.getByLabel(/email address/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();
      
      await page.waitForURL('/dashboard');

      // Now mock API calls to return 401 (session expired)
      await page.route('**/api/customer/**', route => {
        route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Token expired',
            code: 'TOKEN_EXPIRED'
          })
        });
      });

      // Trigger an API call that will fail
      await page.reload();

      // Should show error boundary instead of crashing or redirecting
      await expect(page.getByText('Authentication Required')).toBeVisible();
      
      // User should be able to recover
      await page.getByText('Go to Login').click();
      await expect(page).toHaveURL('/login');
    });

    test('should handle server-side rate limiting gracefully', async ({ page }) => {
      // Mock rate limit response from server
      await page.route('**/api/auth/customer/login', route => {
        route.fulfill({
          status: 429,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Too many login attempts',
            retryAfter: 300
          })
        });
      });

      await page.getByLabel(/email address/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();

      // Should show server-side rate limit message
      await expect(page.getByText(/too many login attempts/i)).toBeVisible();
      
      // Should not show client-side rate limiting UI
      await expect(page.queryByText(/account temporarily locked/i)).not.toBeVisible();
      await expect(page.queryByText(/remaining attempts/i)).not.toBeVisible();
    });

    test('should handle 403 portal access errors gracefully', async ({ page }) => {
      // Mock portal access denied response
      await page.route('**/api/auth/customer/login', route => {
        route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Access denied - incorrect portal type',
            code: 'PORTAL_ACCESS_DENIED'
          })
        });
      });

      await page.getByLabel(/email address/i).fill('admin@example.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();

      // Should show access denied error without redirect
      await expect(page.getByText(/access denied/i)).toBeVisible();
      
      // Should remain on login page for user to try different credentials
      expect(page.url()).toContain('/');
    });
  });

  test.describe('Error Recovery Flows', () => {
    test('should allow retry after authentication error', async ({ page }) => {
      let attemptCount = 0;
      
      await page.route('**/api/auth/customer/login', route => {
        attemptCount++;
        if (attemptCount === 1) {
          // First attempt fails
          route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'Server error' })
          });
        } else {
          // Second attempt succeeds
          route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
              success: true,
              token: 'valid-token',
              customer: { id: '123', email: 'test@example.com', name: 'Test User' }
            })
          });
        }
      });

      await page.getByLabel(/email address/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('password123');
      
      // First attempt
      await page.getByRole('button', { name: /sign in/i }).click();
      await expect(page.getByText(/server error/i)).toBeVisible();

      // Retry should work
      await page.getByRole('button', { name: /sign in/i }).click();
      await expect(page.getByText('Login Successful!')).toBeVisible();
      
      await page.waitForURL('/dashboard');
      await expect(page).toHaveURL('/dashboard');
    });

    test('should clear errors when user starts typing', async ({ page }) => {
      // Mock failed login
      await page.route('**/api/auth/customer/login', route => {
        route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Invalid credentials' })
        });
      });

      await page.getByLabel(/email address/i).fill('wrong@example.com');
      await page.getByLabel(/password/i).fill('wrongpassword');
      await page.getByRole('button', { name: /sign in/i }).click();

      // Should show error
      await expect(page.getByText(/invalid credentials/i)).toBeVisible();

      // Start typing in email field
      await page.getByLabel(/email address/i).fill('correct@example.com');

      // Error should clear
      await expect(page.getByText(/invalid credentials/i)).not.toBeVisible();
    });
  });

  test.describe('Platform Integration', () => {
    test('should integrate with platform error handling system', async ({ page }) => {
      // Mock a complex error scenario
      await page.route('**/api/customer/dashboard', route => {
        route.fulfill({
          status: 503,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Service temporarily unavailable',
            code: 'SERVICE_UNAVAILABLE',
            retryAfter: 120
          })
        });
      });

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

      await page.getByLabel(/email address/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();
      
      await page.waitForURL('/dashboard');

      // Should show platform error boundary
      await expect(page.getByText('Something went wrong')).toBeVisible();
      await expect(page.getByRole('button', { name: /try again/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /reload page/i })).toBeVisible();
    });

    test('should handle network errors consistently', async ({ page }) => {
      // Simulate network failure
      await page.route('**/api/**', route => route.abort('failed'));

      await page.getByLabel(/email address/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();

      // Should show network error handling
      await expect(page.getByText(/network error/i)).toBeVisible();
      
      // Should remain functional for retry
      await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
    });
  });

  test.describe('Security Validation', () => {
    test('should not expose sensitive error details in production', async ({ page }) => {
      // Mock internal server error with sensitive details
      await page.route('**/api/auth/customer/login', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Database connection failed: postgres://user:pass@db:5432/prod',
            stack: 'Error at /internal/database.js:42',
            code: 'DB_CONNECTION_ERROR'
          })
        });
      });

      await page.getByLabel(/email address/i).fill('test@example.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();

      // Should show generic error message
      await expect(page.getByText(/server error/i)).toBeVisible();
      
      // Should not expose sensitive details
      await expect(page.getByText(/postgres/i)).not.toBeVisible();
      await expect(page.getByText(/database.js/i)).not.toBeVisible();
      await expect(page.getByText(/user:pass/i)).not.toBeVisible();
    });

    test('should maintain security headers during error scenarios', async ({ page }) => {
      let headers: Record<string, string> = {};
      
      page.on('response', response => {
        if (response.url().includes('/dashboard')) {
          headers = response.headers();
        }
      });

      await page.goto('/dashboard');

      // Should have security headers even during errors
      expect(headers['x-frame-options']).toBeDefined();
      expect(headers['content-security-policy']).toBeDefined();
      expect(headers['x-content-type-options']).toBe('nosniff');
    });
  });
});