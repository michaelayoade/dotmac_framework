/**
 * E2E Tests for Authentication Flow
 * Tests complete user authentication journey
 */

import { test, expect } from '@playwright/test';

// Test data
const testUser = {
  email: 'test@example.com',
  password: 'SecurePass123!',
  portalId: 'test-portal',
};

const invalidUser = {
  email: 'invalid@example.com',
  password: 'wrongpassword',
};

test.describe('Customer Authentication', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test.describe('Login Page', () => {
    test('should display login form with all required elements', async ({ page }) => {
      // Check page title and branding
      await expect(page).toHaveTitle(/DotMac/);
      await expect(page.getByText('DotMac')).toBeVisible();
      await expect(page.getByText('Welcome Back')).toBeVisible();

      // Check form elements
      await expect(page.getByLabel(/email address/i)).toBeVisible();
      await expect(page.getByLabel(/password/i)).toBeVisible();
      await expect(page.getByLabel(/portal id/i)).toBeVisible();
      await expect(page.getByRole('checkbox', { name: /remember me/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();

      // Check links
      await expect(page.getByText('Forgot password?')).toBeVisible();
      await expect(page.getByText('Contact us to get started')).toBeVisible();
    });

    test('should show security notice', async ({ page }) => {
      await expect(page.getByText(/secure login/i)).toBeVisible();
      await expect(page.getByText(/your connection is encrypted/i)).toBeVisible();
    });

    test('should display support contact information', async ({ page }) => {
      await expect(page.getByText('support@dotmac.com')).toBeVisible();
      await expect(page.getByText('+1 (555) DOT-MAC')).toBeVisible();
    });
  });

  test.describe('Login Process', () => {
    test('should successfully log in with valid credentials', async ({ page }) => {
      // Mock successful API response
      await page.route('**/api/auth/customer/login', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            token: 'valid-token',
            customer: { id: '123', email: testUser.email, name: 'Test User' },
          }),
        });
      });

      // Fill in login form
      await page.getByLabel(/email address/i).fill(testUser.email);
      await page.getByLabel(/password/i).fill(testUser.password);
      await page.getByLabel(/portal id/i).fill(testUser.portalId);

      // Submit form
      await page.getByRole('button', { name: /sign in/i }).click();

      // Should show loading state
      await expect(page.getByText(/signing in/i)).toBeVisible();

      // Should show success message and redirect
      await expect(page.getByText('Login Successful!')).toBeVisible();

      // Should redirect to dashboard after success message
      await page.waitForURL('/dashboard', { timeout: 10000 });
      await expect(page).toHaveURL('/dashboard');
    });

    test('should show error message for invalid credentials', async ({ page }) => {
      // Mock failed API response
      await page.route('**/api/auth/customer/login', (route) => {
        route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({
            success: false,
            error: 'Invalid email or password',
          }),
        });
      });

      // Fill in invalid credentials
      await page.getByLabel(/email address/i).fill(invalidUser.email);
      await page.getByLabel(/password/i).fill(invalidUser.password);

      // Submit form
      await page.getByRole('button', { name: /sign in/i }).click();

      // Should show error message with graceful error handling
      await expect(page.getByText(/invalid email or password/i)).toBeVisible();

      // Should remain on login page (no hard redirect)
      expect(page.url()).toContain('/');
    });

    test('should validate required fields', async ({ page }) => {
      // Try to submit without filling required fields
      await page.getByRole('button', { name: /sign in/i }).click();

      // Browser validation should prevent submission
      const emailInput = page.getByLabel(/email address/i);
      const passwordInput = page.getByLabel(/password/i);

      await expect(emailInput).toHaveAttribute('required');
      await expect(passwordInput).toHaveAttribute('required');

      // Check for HTML5 validation
      const emailValidation = await emailInput.evaluate(
        (el) => (el as HTMLInputElement).validationMessage
      );
      expect(emailValidation).toBeTruthy();
    });

    test('should clear error message when user starts typing', async ({ page }) => {
      // First create an error
      await page.getByLabel(/email address/i).fill(invalidUser.email);
      await page.getByLabel(/password/i).fill(invalidUser.password);
      await page.getByRole('button', { name: /sign in/i }).click();

      await expect(page.getByText(/invalid credentials/i)).toBeVisible();

      // Start typing in email field
      await page.getByLabel(/email address/i).fill(testUser.email);

      // Error should disappear
      await expect(page.getByText(/invalid credentials/i)).not.toBeVisible();
    });

    test('should handle remember me option', async ({ page }) => {
      const rememberMeCheckbox = page.getByRole('checkbox', { name: /remember me/i });

      // Initially unchecked
      await expect(rememberMeCheckbox).not.toBeChecked();

      // Check the box
      await rememberMeCheckbox.check();
      await expect(rememberMeCheckbox).toBeChecked();

      // Fill and submit form
      await page.getByLabel(/email address/i).fill(testUser.email);
      await page.getByLabel(/password/i).fill(testUser.password);
      await page.getByRole('button', { name: /sign in/i }).click();

      // The remember me state should be sent with the request
      // This would need to be verified through network interception in a real test
    });
  });

  test.describe('Password Visibility Toggle', () => {
    test('should toggle password visibility', async ({ page }) => {
      const passwordInput = page.getByLabel(/password/i);
      const toggleButton = page
        .locator('[data-testid="password-toggle"]')
        .or(page.locator('button').filter({ hasText: /eye/i }))
        .or(passwordInput.locator('..').locator('button'));

      // Initially password should be hidden
      await expect(passwordInput).toHaveAttribute('type', 'password');

      // Click toggle to show password
      await toggleButton.click();
      await expect(passwordInput).toHaveAttribute('type', 'text');

      // Click again to hide password
      await toggleButton.click();
      await expect(passwordInput).toHaveAttribute('type', 'password');
    });
  });

  test.describe('Navigation', () => {
    test('should navigate to forgot password page', async ({ page }) => {
      await page.getByText('Forgot password?').click();
      await page.waitForURL('/forgot-password');
      expect(page.url()).toContain('/forgot-password');
    });

    test('should navigate to contact page', async ({ page }) => {
      await page.getByText('Contact us to get started').click();
      await page.waitForURL('/contact');
      expect(page.url()).toContain('/contact');
    });

    test('should have working support links', async ({ page }) => {
      // Check email link
      const emailLink = page.getByText('support@dotmac.com');
      await expect(emailLink).toHaveAttribute('href', /mailto:support@dotmac\.com/);

      // Check phone link
      const phoneLink = page.getByText('+1 (555) DOT-MAC');
      await expect(phoneLink).toHaveAttribute('href', /tel:\+1-555-DOTMAC/);
    });
  });

  test.describe('Success State', () => {
    test('should show success message before redirect', async ({ page }) => {
      // Mock successful login response
      await page.route('**/api/auth/login', (route) => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            accessToken: 'mock-token',
            user: { id: '123', email: testUser.email, name: 'Test User' },
          }),
        });
      });

      // Fill and submit form
      await page.getByLabel(/email address/i).fill(testUser.email);
      await page.getByLabel(/password/i).fill(testUser.password);
      await page.getByRole('button', { name: /sign in/i }).click();

      // Should show success message
      await expect(page.getByText('Login Successful!')).toBeVisible();
      await expect(page.getByText('Redirecting you to your dashboard...')).toBeVisible();

      // Should eventually redirect
      await page.waitForURL('/dashboard', { timeout: 5000 });
    });
  });

  test.describe('Security Features', () => {
    test('should have proper input types and autocomplete', async ({ page }) => {
      const emailInput = page.getByLabel(/email address/i);
      const passwordInput = page.getByLabel(/password/i);

      await expect(emailInput).toHaveAttribute('type', 'email');
      await expect(emailInput).toHaveAttribute('autocomplete', 'email');
      await expect(passwordInput).toHaveAttribute('type', 'password');
      await expect(passwordInput).toHaveAttribute('autocomplete', 'current-password');
    });

    test('should prevent CSRF attacks', async ({ page }) => {
      // This would need to be tested by examining network requests
      // to ensure CSRF tokens are properly included
      let csrfTokenSent = false;

      await page.route('**/api/auth/login', (route) => {
        const headers = route.request().headers();
        csrfTokenSent = !!headers['x-csrf-token'];

        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ success: true }),
        });
      });

      await page.getByLabel(/email address/i).fill(testUser.email);
      await page.getByLabel(/password/i).fill(testUser.password);
      await page.getByRole('button', { name: /sign in/i }).click();

      // CSRF token should be included in the request
      expect(csrfTokenSent).toBe(true);
    });
  });

  test.describe('Accessibility', () => {
    test('should be keyboard navigable', async ({ page }) => {
      // Tab through all form elements
      await page.keyboard.press('Tab');
      await expect(page.getByLabel(/email address/i)).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.getByLabel(/portal id/i)).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.getByLabel(/password/i)).toBeFocused();

      await page.keyboard.press('Tab');
      // Password toggle button should be focusable

      await page.keyboard.press('Tab');
      await expect(page.getByRole('checkbox', { name: /remember me/i })).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.getByText('Forgot password?')).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.getByRole('button', { name: /sign in/i })).toBeFocused();
    });

    test('should have proper ARIA labels and roles', async ({ page }) => {
      const emailInput = page.getByLabel(/email address/i);
      const passwordInput = page.getByLabel(/password/i);

      // Check for proper labeling
      await expect(emailInput).toHaveAttribute('aria-label');
      await expect(passwordInput).toHaveAttribute('aria-label');

      // Form should have proper structure
      const form = page.locator('form');
      await expect(form).toBeVisible();
    });

    test('should announce errors to screen readers', async ({ page }) => {
      // Submit with invalid credentials
      await page.getByLabel(/email address/i).fill(invalidUser.email);
      await page.getByLabel(/password/i).fill(invalidUser.password);
      await page.getByRole('button', { name: /sign in/i }).click();

      // Error message should be announced
      const errorMessage = page.getByRole('alert');
      await expect(errorMessage).toBeVisible();
      await expect(errorMessage).toContainText(/invalid credentials/i);
    });
  });

  test.describe('Responsive Design', () => {
    test('should work on mobile devices', async ({ page }) => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });

      // All elements should still be visible and usable
      await expect(page.getByText('DotMac')).toBeVisible();
      await expect(page.getByLabel(/email address/i)).toBeVisible();
      await expect(page.getByLabel(/password/i)).toBeVisible();
      await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();

      // Form should still be functional
      await page.getByLabel(/email address/i).fill(testUser.email);
      await page.getByLabel(/password/i).fill(testUser.password);

      // Button should be easily tappable
      const submitButton = page.getByRole('button', { name: /sign in/i });
      const buttonBox = await submitButton.boundingBox();
      expect(buttonBox?.height).toBeGreaterThan(44); // iOS minimum tap target
    });

    test('should work on tablet devices', async ({ page }) => {
      // Set tablet viewport
      await page.setViewportSize({ width: 768, height: 1024 });

      await expect(page.getByText('Welcome Back')).toBeVisible();
      await expect(page.getByLabel(/email address/i)).toBeVisible();

      // Layout should adapt appropriately for tablet
      const form = page.locator('form');
      const formBox = await form.boundingBox();
      expect(formBox?.width).toBeLessThan(768); // Should not stretch full width
    });
  });

  test.describe('Performance', () => {
    test('should load quickly', async ({ page }) => {
      const startTime = Date.now();
      await page.goto('/');

      // Main content should be visible quickly
      await expect(page.getByText('Welcome Back')).toBeVisible();

      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(3000); // Should load in under 3 seconds
    });

    test('should not have console errors', async ({ page }) => {
      const errors: string[] = [];
      page.on('console', (msg) => {
        if (msg.type() === 'error') {
          errors.push(msg.text());
        }
      });

      await page.goto('/');
      await page.waitForTimeout(2000); // Wait for any async operations

      // Filter out known acceptable errors (if any)
      const criticalErrors = errors.filter(
        (error) =>
          !error.includes('favicon.ico') && // Favicon errors are common and non-critical
          !error.includes('DevTools') // DevTools related errors
      );

      expect(criticalErrors).toHaveLength(0);
    });
  });
});
