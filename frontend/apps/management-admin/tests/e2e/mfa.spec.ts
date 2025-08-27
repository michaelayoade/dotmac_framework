import { test, expect, type Page } from '@playwright/test';

test.describe('Multi-Factor Authentication (MFA)', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[type="email"]', 'admin@dotmac.com');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/dashboard');
  });

  test('should display MFA setup option in settings', async ({ page }) => {
    await page.goto('/settings/security');
    
    await expect(page.locator('h2')).toContainText('Multi-Factor Authentication');
    await expect(page.locator('button')).toContainText('Set up MFA');
  });

  test('should show MFA method selection', async ({ page }) => {
    await page.goto('/settings/security');
    await page.click('button:has-text("Set up MFA")');
    
    // Should show method selection
    await expect(page.locator('h2')).toContainText('Set up Multi-Factor Authentication');
    await expect(page.locator('button')).toContainText('Authenticator App');
    await expect(page.locator('button')).toContainText('SMS Verification');
    
    // SMS should be disabled
    await expect(page.locator('button:has-text("SMS Verification")')).toBeDisabled();
  });

  test('should show TOTP setup flow', async ({ page }) => {
    await page.goto('/settings/security');
    await page.click('button:has-text("Set up MFA")');
    await page.click('button:has-text("Authenticator App")');
    
    // Should show QR code setup
    await expect(page.locator('h2')).toContainText('Set up Authenticator App');
    await expect(page.locator('img')).toBeVisible(); // QR code
    await expect(page.locator('code')).toBeVisible(); // Manual entry code
    
    // Should have show/hide toggle for secret
    await expect(page.locator('button[title="Show"]')).toBeVisible();
    await expect(page.locator('button[title="Copy to clipboard"]')).toBeVisible();
  });

  test('should toggle secret visibility', async ({ page }) => {
    await page.goto('/settings/security');
    await page.click('button:has-text("Set up MFA")');
    await page.click('button:has-text("Authenticator App")');
    
    // Initially secret should be hidden
    await expect(page.locator('code')).toContainText('••••••••••••••••••••••••••••••••');
    
    // Click show button
    await page.click('button[title="Show"]');
    
    // Secret should be visible (not just dots)
    const secretText = await page.locator('code').textContent();
    expect(secretText).not.toBe('••••••••••••••••••••••••••••••••');
    expect(secretText?.length).toBeGreaterThan(10);
  });

  test('should proceed to verification step', async ({ page }) => {
    await page.goto('/settings/security');
    await page.click('button:has-text("Set up MFA")');
    await page.click('button:has-text("Authenticator App")');
    await page.click('button:has-text("Continue")');
    
    // Should show verification form
    await expect(page.locator('h2')).toContainText('Verify Your Setup');
    await expect(page.locator('input[type="text"]')).toBeVisible();
    await expect(page.locator('input[placeholder="000000"]')).toBeVisible();
    await expect(page.locator('button')).toContainText('Verify & Enable');
  });

  test('should validate TOTP code format', async ({ page }) => {
    await page.goto('/settings/security');
    await page.click('button:has-text("Set up MFA")');
    await page.click('button:has-text("Authenticator App")');
    await page.click('button:has-text("Continue")');
    
    // Try invalid codes
    await page.fill('input[placeholder="000000"]', '123');
    await expect(page.locator('button:has-text("Verify & Enable")')).toBeDisabled();
    
    await page.fill('input[placeholder="000000"]', 'abcdef');
    await expect(page.locator('button:has-text("Verify & Enable")')).toBeDisabled();
    
    // Valid format should enable button
    await page.fill('input[placeholder="000000"]', '123456');
    await expect(page.locator('button:has-text("Verify & Enable")')).toBeEnabled();
  });

  test('should handle invalid verification code', async ({ page }) => {
    await page.goto('/settings/security');
    await page.click('button:has-text("Set up MFA")');
    await page.click('button:has-text("Authenticator App")');
    await page.click('button:has-text("Continue")');
    
    // Enter invalid code
    await page.fill('input[placeholder="000000"]', '000000');
    await page.click('button:has-text("Verify & Enable")');
    
    // Should show error
    await expect(page.locator('.error-message')).toBeVisible();
    await expect(page.locator('text=Invalid verification code')).toBeVisible();
  });

  test('should complete MFA setup with valid code', async ({ page }) => {
    // Note: This test would require a valid TOTP code or mocking
    // For now, we'll test the UI flow assuming a valid code
    await page.goto('/settings/security');
    await page.click('button:has-text("Set up MFA")');
    await page.click('button:has-text("Authenticator App")');
    await page.click('button:has-text("Continue")');
    
    // Mock successful verification
    await page.route('**/api/v1/mfa/setup/totp/verify', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          success: true,
          backupCodes: ['CODE1234', 'CODE5678', 'CODE9012', 'CODEABCD', 'CODEEFGH', 'CODEIJKL', 'CODEMNOP', 'CODEQRST']
        })
      });
    });
    
    await page.fill('input[placeholder="000000"]', '123456');
    await page.click('button:has-text("Verify & Enable")');
    
    // Should show backup codes
    await expect(page.locator('h2')).toContainText('MFA Setup Complete!');
    await expect(page.locator('text=Your Backup Codes')).toBeVisible();
    await expect(page.locator('text=CODE1234')).toBeVisible();
  });

  test('should require backup codes confirmation', async ({ page }) => {
    await page.goto('/settings/security');
    await page.click('button:has-text("Set up MFA")');
    await page.click('button:has-text("Authenticator App")');
    await page.click('button:has-text("Continue")');
    
    // Mock successful verification
    await page.route('**/api/v1/mfa/setup/totp/verify', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          success: true,
          backupCodes: ['CODE1234', 'CODE5678']
        })
      });
    });
    
    await page.fill('input[placeholder="000000"]', '123456');
    await page.click('button:has-text("Verify & Enable")');
    
    // Complete setup button should be disabled initially
    await expect(page.locator('button:has-text("Complete Setup")')).toBeDisabled();
    
    // Check the confirmation checkbox
    await page.check('input[type="checkbox"]');
    
    // Now should be enabled
    await expect(page.locator('button:has-text("Complete Setup")')).toBeEnabled();
  });

  test('should show MFA as enabled after setup', async ({ page }) => {
    // Mock MFA as already enabled
    await page.route('**/api/v1/mfa/config', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          userId: 'user123',
          primaryMethod: 'totp',
          enabledMethods: ['totp'],
          status: 'enabled',
          backupCodesRemaining: 8,
          lastUsed: null,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString()
        })
      });
    });
    
    await page.goto('/settings/security');
    
    // Should show MFA as enabled
    await expect(page.locator('text=MFA is Already Enabled')).toBeVisible();
    await expect(page.locator('text=Your account is already protected')).toBeVisible();
  });
});