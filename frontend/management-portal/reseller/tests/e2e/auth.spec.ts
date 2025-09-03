import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Start from login page
    await page.goto('/login');
  });

  test('should show login form', async ({ page }) => {
    // Check that login form is visible
    await expect(page.locator('[data-testid="login-form"]')).toBeVisible();
    await expect(page.locator('[data-testid="email-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="password-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="login-button"]')).toBeVisible();
  });

  test('should show validation errors for empty fields', async ({ page }) => {
    // Click login without filling fields
    await page.click('[data-testid="login-button"]');

    // Check for validation messages
    await expect(page.locator('text=Email is required')).toBeVisible();
    await expect(page.locator('text=Password is required')).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    // Fill in invalid credentials
    await page.fill('[data-testid="email-input"]', 'invalid@example.com');
    await page.fill('[data-testid="password-input"]', 'wrongpassword');

    // Submit form
    await page.click('[data-testid="login-button"]');

    // Check for error message
    await expect(page.locator('text=Invalid credentials')).toBeVisible();
  });

  test('should successfully login with valid credentials', async ({ page }) => {
    // Fill in valid test credentials
    await page.fill('[data-testid="email-input"]', 'test-manager@dotmac.com');
    await page.fill('[data-testid="password-input"]', 'test-password-123');

    // Submit form
    await page.click('[data-testid="login-button"]');

    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard');

    // Check for dashboard elements
    await expect(page.locator('[data-testid="dashboard-header"]')).toBeVisible();
    await expect(page.locator('[data-testid="user-profile"]')).toContainText(
      'test-manager@dotmac.com'
    );
  });

  test('should logout successfully', async ({ page }) => {
    // Login first
    await page.fill('[data-testid="email-input"]', 'test-manager@dotmac.com');
    await page.fill('[data-testid="password-input"]', 'test-password-123');
    await page.click('[data-testid="login-button"]');

    // Wait for dashboard
    await expect(page).toHaveURL('/dashboard');

    // Click logout
    await page.click('[data-testid="user-menu"]');
    await page.click('[data-testid="logout-button"]');

    // Should redirect to login
    await expect(page).toHaveURL('/login');
    await expect(page.locator('[data-testid="login-form"]')).toBeVisible();
  });

  test('should redirect to login when accessing protected route without auth', async ({ page }) => {
    // Try to access dashboard directly
    await page.goto('/dashboard');

    // Should redirect to login
    await expect(page).toHaveURL('/login');
  });

  test('should remember login state after page refresh', async ({ page }) => {
    // Login
    await page.fill('[data-testid="email-input"]', 'test-manager@dotmac.com');
    await page.fill('[data-testid="password-input"]', 'test-password-123');
    await page.click('[data-testid="login-button"]');

    await expect(page).toHaveURL('/dashboard');

    // Refresh page
    await page.reload();

    // Should still be on dashboard
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('[data-testid="dashboard-header"]')).toBeVisible();
  });
});

test.describe('Protected Routes', () => {
  test.beforeEach(async ({ page }) => {
    // Login before each test
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'test-manager@dotmac.com');
    await page.fill('[data-testid="password-input"]', 'test-password-123');
    await page.click('[data-testid="login-button"]');
    await expect(page).toHaveURL('/dashboard');
  });

  test('should access partners page', async ({ page }) => {
    await page.goto('/partners');
    await expect(page.locator('[data-testid="partners-page"]')).toBeVisible();
    await expect(page.locator('[data-testid="partners-header"]')).toContainText('Partners');
  });

  test('should access commissions page', async ({ page }) => {
    await page.goto('/commissions');
    await expect(page.locator('[data-testid="commissions-page"]')).toBeVisible();
    await expect(page.locator('[data-testid="commissions-header"]')).toContainText('Commissions');
  });

  test('should access analytics page', async ({ page }) => {
    await page.goto('/analytics');
    await expect(page.locator('[data-testid="analytics-page"]')).toBeVisible();
    await expect(page.locator('[data-testid="analytics-header"]')).toContainText('Analytics');
  });
});

test.describe('Permission-based Access', () => {
  test('should show different UI elements based on user role', async ({ page }) => {
    // Login as channel manager
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'channel-manager@dotmac.com');
    await page.fill('[data-testid="password-input"]', 'test-password-123');
    await page.click('[data-testid="login-button"]');

    await expect(page).toHaveURL('/dashboard');

    // Check for channel manager specific elements
    await expect(page.locator('[data-testid="manage-partners-button"]')).toBeVisible();
    await expect(page.locator('[data-testid="approve-commissions-button"]')).toBeVisible();
  });

  test('should restrict operations manager access', async ({ page }) => {
    // Login as operations manager
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'operations-manager@dotmac.com');
    await page.fill('[data-testid="password-input"]', 'test-password-123');
    await page.click('[data-testid="login-button"]');

    await expect(page).toHaveURL('/dashboard');

    // Should not see partner management buttons
    await expect(page.locator('[data-testid="manage-partners-button"]')).not.toBeVisible();

    // But should see analytics
    await expect(page.locator('[data-testid="view-analytics-button"]')).toBeVisible();
  });
});
