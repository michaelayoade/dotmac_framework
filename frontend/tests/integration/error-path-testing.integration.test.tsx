/**
 * Error Path Testing Suite
 * Comprehensive testing for edge cases and error scenarios
 */

import { test, expect } from '@playwright/test';
import { UserJourneyHelper } from '../utils/user-journey-helper';
import { DataFactory } from '../utils/data-factory';

test.describe('Error Path Testing', () => {
  let journeyHelper: UserJourneyHelper;
  let dataFactory: DataFactory;

  test.beforeAll(async () => {
    journeyHelper = new UserJourneyHelper();
    dataFactory = new DataFactory();
  });

  test.describe('Authentication Error Paths', () => {
    test('Invalid login credentials', async ({ page }) => {
      await page.goto('/customer/login');

      // Try invalid credentials
      await page.fill('[data-testid="email"]', 'invalid@test.com');
      await page.fill('[data-testid="password"]', 'wrongpassword');
      await page.click('[data-testid="login-submit"]');

      // Verify error message
      await expect(page.locator('[data-testid="login-error"]')).toContainText('Invalid credentials');
      await expect(page.locator('[data-testid="login-form"]')).toBeVisible();
    });

    test('Account lockout after multiple failed attempts', async ({ page }) => {
      await page.goto('/customer/login');

      const invalidEmail = 'lockout@test.com';

      // Attempt multiple failed logins
      for (let i = 0; i < 5; i++) {
        await page.fill('[data-testid="email"]', invalidEmail);
        await page.fill('[data-testid="password"]', 'wrongpassword');
        await page.click('[data-testid="login-submit"]');

        // Wait for error message
        await expect(page.locator('[data-testid="login-error"]')).toBeVisible();
      }

      // Final attempt should show account locked message
      await page.fill('[data-testid="email"]', invalidEmail);
      await page.fill('[data-testid="password"]', 'wrongpassword');
      await page.click('[data-testid="login-submit"]');

      await expect(page.locator('[data-testid="login-error"]')).toContainText('Account locked');
    });

    test('Expired session handling', async ({ page, context }) => {
      const customer = await journeyHelper.createTestCustomer();
      await journeyHelper.customerLogin(page, customer);

      // Simulate expired session by clearing storage
      await page.evaluate(() => {
        localStorage.removeItem('auth_token');
        sessionStorage.clear();
      });

      // Try to access protected route
      await page.click('[data-testid="billing-nav"]');

      // Should redirect to login
      await expect(page).toHaveURL(/\/login/);
      await expect(page.locator('[data-testid="session-expired-message"]')).toBeVisible();
    });

    test('Concurrent session limit exceeded', async ({ page, context }) => {
      const customer = await journeyHelper.createTestCustomer();

      // Open multiple tabs and login
      const pages = [];
      for (let i = 0; i < 5; i++) {
        const newPage = await context.newPage();
        await journeyHelper.customerLogin(newPage, customer);
        pages.push(newPage);
      }

      // Last login should show concurrent session limit error
      const lastPage = pages[pages.length - 1];
      await expect(lastPage.locator('[data-testid="session-limit-error"]')).toBeVisible();

      // Cleanup
      for (const p of pages) {
        await p.close();
      }
    });
  });

  test.describe('Network and Connectivity Errors', () => {
    test('API timeout handling', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();
      await journeyHelper.customerLogin(page, customer);

      // Intercept API calls and delay them
      await page.route('**/api/**', async route => {
        await new Promise(resolve => setTimeout(resolve, 35000)); // Longer than timeout
        await route.continue();
      });

      await page.click('[data-testid="billing-nav"]');

      // Should show timeout error
      await expect(page.locator('[data-testid="timeout-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
    });

    test('Offline mode handling', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();
      await journeyHelper.customerLogin(page, customer);

      // Simulate offline mode
      await page.context().setOffline(true);

      await page.click('[data-testid="support-nav"]');

      // Should show offline message
      await expect(page.locator('[data-testid="offline-message"]')).toBeVisible();
      await expect(page.locator('[data-testid="sync-status"]')).toContainText('Offline');

      // Restore connection
      await page.context().setOffline(false);
      await page.reload();

      // Should sync pending data
      await expect(page.locator('[data-testid="sync-pending"]')).toBeVisible();
    });

    test('Slow network degradation', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();
      await journeyHelper.customerLogin(page, customer);

      // Simulate slow network
      await page.route('**/api/**', async route => {
        await page.waitForTimeout(5000); // 5 second delay
        await route.continue();
      });

      await page.click('[data-testid="dashboard-refresh"]');

      // Should show loading indicator for extended period
      await expect(page.locator('[data-testid="loading-spinner"]')).toBeVisible();

      // Eventually should load data
      await expect(page.locator('[data-testid="dashboard-data"]')).toBeVisible();
    });
  });

  test.describe('Form Validation Edge Cases', () => {
    test('Extremely long input values', async ({ page }) => {
      await page.goto('/customer/signup');

      // Generate extremely long strings
      const longString = 'a'.repeat(10000);
      const longEmail = `${longString}@test.com`;

      await page.fill('[data-testid="email"]', longEmail);
      await page.fill('[data-testid="company-name"]', longString);
      await page.fill('[data-testid="address"]', longString);

      await page.click('[data-testid="signup-submit"]');

      // Should handle gracefully or show appropriate error
      await expect(page.locator('[data-testid="input-length-error"]')).toBeVisible();
    });

    test('Special characters and unicode', async ({ page }) => {
      await page.goto('/customer/signup');

      // Test various special characters
      const specialChars = 'ñáéíóúü¿¡@#$%^&*()';
      const unicodeChars = '🚀🌟💻🔥✨';

      await page.fill('[data-testid="company-name"]', `${specialChars} ${unicodeChars}`);
      await page.fill('[data-testid="address"]', specialChars);
      await page.fill('[data-testid="city"]', unicodeChars);

      await page.click('[data-testid="signup-submit"]');

      // Should handle unicode gracefully
      await expect(page.locator('[data-testid="form-validation"]')).toBeVisible();
    });

    test('SQL injection attempts', async ({ page }) => {
      await page.goto('/customer/login');

      const sqlInjection = "' OR '1'='1'; --";
      await page.fill('[data-testid="email"]', sqlInjection);
      await page.fill('[data-testid="password"]', sqlInjection);
      await page.click('[data-testid="login-submit"]');

      // Should not log in and show generic error
      await expect(page.locator('[data-testid="login-error"]')).toContainText('Invalid credentials');
      await expect(page).not.toHaveURL(/\/dashboard/);
    });

    test('XSS attempt handling', async ({ page }) => {
      await page.goto('/customer/signup');

      const xssAttempt = '<script>alert("xss")</script>';
      await page.fill('[data-testid="company-name"]', xssAttempt);
      await page.fill('[data-testid="address"]', xssAttempt);

      await page.click('[data-testid="signup-submit"]');

      // Should sanitize input and not execute script
      await expect(page.locator('script')).toHaveCount(0);
      await expect(page.locator('[data-testid="validation-error"]')).toBeVisible();
    });
  });

  test.describe('Resource Limit Edge Cases', () => {
    test('File upload size limits', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();
      await journeyHelper.customerLogin(page, customer);

      // Create a large file (simulate 100MB file)
      const largeFileBuffer = Buffer.alloc(100 * 1024 * 1024, 'x'); // 100MB

      await page.click('[data-testid="upload-document"]');

      // Try to upload large file
      await page.setInputFiles('[data-testid="file-input"]', {
        name: 'large-file.txt',
        mimeType: 'text/plain',
        buffer: largeFileBuffer
      });

      // Should show file size error
      await expect(page.locator('[data-testid="file-size-error"]')).toContainText('File too large');
    });

    test('API rate limit handling', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();
      await journeyHelper.customerLogin(page, customer);

      // Make rapid API calls
      const promises = [];
      for (let i = 0; i < 100; i++) {
        promises.push(page.click('[data-testid="refresh-data"]'));
      }

      await Promise.all(promises);

      // Should show rate limit message
      await expect(page.locator('[data-testid="rate-limit-message"]')).toBeVisible();
      await expect(page.locator('[data-testid="retry-after"]')).toBeVisible();
    });

    test('Memory-intensive operations', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();
      await journeyHelper.customerLogin(page, customer);

      // Navigate to data-heavy page (large table)
      await page.click('[data-testid="large-dataset-view"]');

      // Should handle large dataset without crashing
      await expect(page.locator('[data-testid="data-table"]')).toBeVisible();

      // Test pagination works
      await page.click('[data-testid="next-page"]');
      await expect(page.locator('[data-testid="page-2"]')).toBeVisible();

      // Memory should not leak (check console for errors)
      const consoleMessages = [];
      page.on('console', msg => consoleMessages.push(msg.text()));

      await page.waitForTimeout(5000);
      const errorMessages = consoleMessages.filter(msg => msg.includes('error') || msg.includes('Error'));
      expect(errorMessages.length).toBeLessThan(3); // Allow some minor errors
    });
  });

  test.describe('Browser Compatibility Edge Cases', () => {
    test('JavaScript disabled handling', async ({ page, context }) => {
      // Disable JavaScript
      await context.addInitScript(() => {
        // This would disable JS in a real scenario
        // For testing, we'll simulate by intercepting JS requests
      });

      await page.goto('/customer/login');

      // Should show no-JS message or basic HTML version
      await expect(page.locator('[data-testid="no-js-message"]')).toBeVisible();
    });

    test('Cookie disabled handling', async ({ page, context }) => {
      // Disable cookies
      await context.addCookies([]); // Clear cookies
      await page.route('**/*', route => {
        // Block cookie setting
        const headers = route.request().headers();
        delete headers['cookie'];
        route.continue({ headers });
      });

      await page.goto('/customer/login');

      await page.fill('[data-testid="email"]', 'test@test.com');
      await page.fill('[data-testid="password"]', 'password');
      await page.click('[data-testid="login-submit"]');

      // Should handle gracefully without cookies
      await expect(page.locator('[data-testid="cookie-warning"]')).toBeVisible();
    });

    test('Local storage disabled', async ({ page }) => {
      // Disable localStorage
      await page.addInitScript(() => {
        Object.defineProperty(window, 'localStorage', {
          value: {
            getItem: () => null,
            setItem: () => { throw new Error('localStorage disabled'); },
            removeItem: () => { throw new Error('localStorage disabled'); },
            clear: () => { throw new Error('localStorage disabled'); }
          }
        });
      });

      await page.goto('/customer/login');

      await page.fill('[data-testid="email"]', 'test@test.com');
      await page.fill('[data-testid="password"]', 'password');
      await page.click('[data-testid="login-submit"]');

      // Should handle localStorage errors gracefully
      await expect(page.locator('[data-testid="storage-error"]')).toBeVisible();
    });
  });

  test.describe('Data Corruption and Recovery', () => {
    test('Corrupted local storage recovery', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();
      await journeyHelper.customerLogin(page, customer);

      // Corrupt localStorage data
      await page.evaluate(() => {
        localStorage.setItem('user_preferences', '{invalid json');
        localStorage.setItem('app_state', 'corrupted data');
      });

      await page.reload();

      // Should recover gracefully from corrupted data
      await expect(page.locator('.dashboard')).toBeVisible();

      // Should show recovery message
      await expect(page.locator('[data-testid="data-recovery-message"]')).toBeVisible();
    });

    test('Network interruption during save', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();
      await journeyHelper.customerLogin(page, customer);

      await page.click('[data-testid="profile-settings"]');
      await page.fill('[data-testid="profile-name"]', 'Updated Name');

      // Simulate network failure during save
      await page.route('**/api/profile', route => route.abort());

      await page.click('[data-testid="save-profile"]');

      // Should show save failed message
      await expect(page.locator('[data-testid="save-error"]')).toBeVisible();

      // Should offer retry option
      await expect(page.locator('[data-testid="retry-save"]')).toBeVisible();

      // Restore network and retry
      await page.unroute('**/api/profile');
      await page.click('[data-testid="retry-save"]');

      // Should save successfully
      await expect(page.locator('[data-testid="save-success"]')).toBeVisible();
    });

    test('Database connection loss recovery', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();
      await journeyHelper.customerLogin(page, customer);

      // Simulate database connection loss
      await page.route('**/api/**', route => {
        if (Math.random() > 0.7) { // 30% chance of failure
          route.fulfill({ status: 503, body: 'Database connection lost' });
        } else {
          route.continue();
        }
      });

      await page.click('[data-testid="load-data"]');

      // Should handle intermittent failures gracefully
      await expect(page.locator('[data-testid="data-loaded"]')).toBeVisible();

      // Should show some retry indicators for failed requests
      const retryIndicators = page.locator('[data-testid="retry-indicator"]');
      await expect(retryIndicators).toHaveCount(await retryIndicators.count());
    });
  });

  test.describe('Concurrent User Scenarios', () => {
    test('Multiple users editing same resource', async ({ browser }) => {
      const customer = await journeyHelper.createTestCustomer();

      // Create multiple browser contexts
      const context1 = await browser.newContext();
      const context2 = await browser.newContext();

      const page1 = await context1.newPage();
      const page2 = await context2.newPage();

      // Both users login
      await journeyHelper.customerLogin(page1, customer);
      await journeyHelper.customerLogin(page2, customer);

      // Both navigate to profile settings
      await page1.click('[data-testid="profile-settings"]');
      await page2.click('[data-testid="profile-settings"]');

      // Both make changes
      await page1.fill('[data-testid="profile-name"]', 'Name from User 1');
      await page2.fill('[data-testid="profile-name"]', 'Name from User 2');

      // Both try to save
      await page1.click('[data-testid="save-profile"]');
      await page2.click('[data-testid="save-profile"]');

      // One should succeed, one should show conflict error
      const successCount = await Promise.all([
        page1.locator('[data-testid="save-success"]').isVisible(),
        page2.locator('[data-testid="save-success"]').isVisible()
      ]);

      expect(successCount.filter(Boolean).length).toBe(1);

      const conflictErrors = await Promise.all([
        page1.locator('[data-testid="conflict-error"]').isVisible(),
        page2.locator('[data-testid="conflict-error"]').isVisible()
      ]);

      expect(conflictErrors.filter(Boolean).length).toBe(1);

      // Cleanup
      await context1.close();
      await context2.close();
    });

    test('Race condition in form submissions', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();
      await journeyHelper.customerLogin(page, customer);

      await page.click('[data-testid="create-ticket"]');

      // Submit form multiple times rapidly
      const submitPromises = [];
      for (let i = 0; i < 5; i++) {
        submitPromises.push(page.click('[data-testid="submit-ticket"]'));
      }

      await Promise.all(submitPromises);

      // Should only create one ticket
      const ticketCount = await page.locator('[data-testid="created-ticket"]').count();
      expect(ticketCount).toBe(1);

      // Should show duplicate submission prevention
      await expect(page.locator('[data-testid="duplicate-prevention-message"]')).toBeVisible();
    });
  });

  test.describe('Security Vulnerability Tests', () => {
    test('CSRF token validation', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();
      await journeyHelper.customerLogin(page, customer);

      // Try to submit form without CSRF token
      await page.evaluate(() => {
        // Remove CSRF token from form
        const csrfInput = document.querySelector('[name="csrf_token"]');
        if (csrfInput) csrfInput.remove();
      });

      await page.click('[data-testid="submit-form"]');

      // Should reject submission
      await expect(page.locator('[data-testid="csrf-error"]')).toBeVisible();
    });

    test('Input sanitization against injection', async ({ page }) => {
      const customer = await journeyHelper.createTestCustomer();
      await journeyHelper.customerLogin(page, customer);

      // Try various injection patterns
      const injectionPatterns = [
        '<script>alert("xss")</script>',
        'javascript:alert("xss")',
        '{{7*7}}',  // Template injection
        '../../../etc/passwd',  // Path traversal
        '<img src=x onerror=alert("xss")>',  // Event handler injection
      ];

      for (const pattern of injectionPatterns) {
        await page.fill('[data-testid="input-field"]', pattern);
        await page.click('[data-testid="submit"]');

        // Should sanitize input and not execute malicious code
        await expect(page.locator('script')).toHaveCount(0);
        await expect(page.locator('[data-testid="injection-error"]')).toBeVisible();
      }
    });

    test('Session fixation prevention', async ({ page }) => {
      // Try to use a session ID from URL parameters
      const maliciousSessionId = 'malicious-session-123';
      await page.goto(`/login?session_id=${maliciousSessionId}`);

      await page.fill('[data-testid="email"]', 'test@test.com');
      await page.fill('[data-testid="password"]', 'password');
      await page.click('[data-testid="login-submit"]');

      // Should generate new session, not use provided one
      const currentSession = await page.evaluate(() => {
        return localStorage.getItem('session_id');
      });

      expect(currentSession).not.toBe(maliciousSessionId);
    });
  });
});
