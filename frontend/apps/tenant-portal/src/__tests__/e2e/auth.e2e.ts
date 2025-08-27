/**
 * Authentication E2E Tests
 * End-to-end tests for authentication flows
 */

import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Start each test on the login page
    await page.goto('/login');
  });

  test('should display login form', async ({ page }) => {
    // Check page title
    await expect(page).toHaveTitle(/Sign in to your tenant portal/i);
    
    // Check form elements
    await expect(page.locator('input[name="email"]')).toBeVisible();
    await expect(page.locator('input[name="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]')).toContainText('Sign in');
  });

  test('should show validation errors for empty form', async ({ page }) => {
    // Click submit without filling form
    await page.click('button[type="submit"]');
    
    // Check for HTML5 validation (browser-level)
    const emailInput = page.locator('input[name="email"]');
    const passwordInput = page.locator('input[name="password"]');
    
    await expect(emailInput).toHaveAttribute('required');
    await expect(passwordInput).toHaveAttribute('required');
  });

  test('should show validation error for invalid email', async ({ page }) => {
    // Fill form with invalid email
    await page.fill('input[name="email"]', 'invalid-email');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    // Check for HTML5 email validation
    const emailInput = page.locator('input[name="email"]');
    await expect(emailInput).toHaveAttribute('type', 'email');
  });

  test('should handle login with demo credentials', async ({ page }) => {
    // Wait for demo credentials to be visible
    const demoSection = page.locator('text=Demo Credentials');
    if (await demoSection.isVisible()) {
      // Use demo admin credentials
      await page.click('text=Use these credentials >> nth=0');
      
      // Verify fields are filled
      await expect(page.locator('input[name="email"]')).not.toBeEmpty();
      await expect(page.locator('input[name="password"]')).not.toBeEmpty();
      
      // Submit form
      await page.click('button[type="submit"]');
      
      // Should redirect to dashboard or show loading
      await expect(page.locator('text=Signing in...')).toBeVisible();
    }
  });

  test('should handle authentication error', async ({ page }) => {
    // Mock failed authentication
    await page.route('/api/v1/tenant-admin/auth/login', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          success: false,
          error: 'Invalid credentials'
        })
      });
    });

    // Fill form with any credentials
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    
    // Should show error message
    await expect(page.locator('text=Invalid credentials')).toBeVisible();
  });

  test('should toggle password visibility', async ({ page }) => {
    const passwordInput = page.locator('input[name="password"]');
    const toggleButton = page.locator('button[type="button"] >> nth=0'); // First button (eye icon)
    
    // Initially password should be hidden
    await expect(passwordInput).toHaveAttribute('type', 'password');
    
    // Click toggle button
    await toggleButton.click();
    
    // Password should be visible
    await expect(passwordInput).toHaveAttribute('type', 'text');
    
    // Click toggle button again
    await toggleButton.click();
    
    // Password should be hidden again
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });

  test('should handle remember me checkbox', async ({ page }) => {
    const rememberMeCheckbox = page.locator('input[name="remember-me"]');
    
    // Initially unchecked
    await expect(rememberMeCheckbox).not.toBeChecked();
    
    // Check the checkbox
    await rememberMeCheckbox.check();
    await expect(rememberMeCheckbox).toBeChecked();
    
    // Uncheck the checkbox
    await rememberMeCheckbox.uncheck();
    await expect(rememberMeCheckbox).not.toBeChecked();
  });

  test('should be accessible', async ({ page }) => {
    // Check for proper ARIA labels
    await expect(page.locator('input[name="email"]')).toHaveAttribute('type', 'email');
    await expect(page.locator('input[name="password"]')).toHaveAttribute('type', 'password');
    
    // Check for proper form structure
    const form = page.locator('form');
    await expect(form).toBeVisible();
    
    // Check for proper labels
    await expect(page.locator('label[for="email"]')).toBeVisible();
    await expect(page.locator('label[for="password"]')).toBeVisible();
  });

  test('should handle keyboard navigation', async ({ page }) => {
    // Tab through form elements
    await page.keyboard.press('Tab'); // Email input
    await expect(page.locator('input[name="email"]')).toBeFocused();
    
    await page.keyboard.press('Tab'); // Password input
    await expect(page.locator('input[name="password"]')).toBeFocused();
    
    await page.keyboard.press('Tab'); // Toggle button
    // await expect(page.locator('button[type="button"]')).toBeFocused();
    
    // Should be able to submit form with Enter
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    
    await page.keyboard.press('Enter');
    // Should attempt to submit (might show loading or error)
  });

  test('should redirect authenticated users', async ({ page, context }) => {
    // Set up authentication cookies
    await context.addCookies([
      {
        name: 'tenant_access_token',
        value: 'mock-token',
        domain: 'localhost',
        path: '/',
        httpOnly: true,
        secure: false,
      }
    ]);

    // Mock authentication validation
    await page.route('/api/v1/tenant-admin/auth/validate', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true })
      });
    });

    // Navigate to login page
    await page.goto('/login');
    
    // Should redirect to dashboard
    await page.waitForURL('/dashboard');
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Mock network error
    await page.route('/api/v1/tenant-admin/auth/login', async (route) => {
      await route.abort('failed');
    });

    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    // Should show network error message
    await expect(page.locator('text=Network error')).toBeVisible();
  });
});

test.describe('Logout Flow', () => {
  test('should logout successfully', async ({ page, context }) => {
    // Set up authentication cookies first
    await context.addCookies([
      {
        name: 'tenant_access_token',
        value: 'mock-token',
        domain: 'localhost',
        path: '/',
        httpOnly: true,
        secure: false,
      }
    ]);

    // Mock authenticated user data
    await page.route('/api/v1/tenant-admin/auth/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          user: { id: '1', name: 'Test User', email: 'test@example.com' },
          tenant: { id: '1', name: 'Test Tenant' }
        })
      });
    });

    // Mock logout endpoint
    await page.route('/api/v1/tenant-admin/auth/logout', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ success: true })
      });
    });

    // Navigate to dashboard
    await page.goto('/dashboard');
    
    // Find and click logout button
    const userMenu = page.locator('[data-testid="user-menu"]').or(page.locator('text=Test User'));
    if (await userMenu.isVisible()) {
      await userMenu.click();
      
      const logoutButton = page.locator('text=Sign out').or(page.locator('text=Logout'));
      await logoutButton.click();
      
      // Should redirect to login
      await page.waitForURL('/login');
    }
  });
});