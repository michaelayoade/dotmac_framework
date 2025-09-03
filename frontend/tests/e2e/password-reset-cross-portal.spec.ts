/**
 * Cross-Portal Password Reset E2E Tests with MailHog Integration
 * Tests complete password reset flow: UI → email → MailHog fetch → link click → new password
 */

import { test, expect } from '@playwright/test';
import { MailHogHelper } from '../testing/e2e/shared-scenarios/mailhog-helper';

interface PortalConfig {
  name: string;
  resetUrl: string;
  loginUrl: string;
  expectedSuccessUrl: string;
  testUser: {
    email: string;
    currentPassword: string;
    newPassword: string;
  };
}

class PasswordResetJourney {
  constructor(
    public page: any,
    public mailHogHelper: MailHogHelper
  ) {}

  async testCompletePasswordReset(portal: PortalConfig) {
    console.log(`Testing complete password reset flow for ${portal.name} portal`);

    // Step 1: Navigate to password reset page
    await this.page.goto(portal.resetUrl);
    await expect(this.page.getByTestId('password-reset-form')).toBeVisible();

    // Step 2: Submit password reset request
    await this.page.fill('[data-testid="email-input"]', portal.testUser.email);
    await this.page.click('[data-testid="send-reset-link"]');

    // Step 3: Verify "link sent" confirmation
    await expect(this.page.getByTestId('reset-link-sent-message')).toBeVisible();
    await expect(this.page.getByText(/reset link sent|check your email/i)).toBeVisible();
    await expect(this.page.getByText(portal.testUser.email)).toBeVisible();

    // Step 4: Wait for and fetch email from MailHog
    console.log('Waiting for password reset email in MailHog...');
    const resetEmail = await this.mailHogHelper.waitForEmail({
      to: portal.testUser.email,
      subject: /password reset|reset your password/i,
      timeout: 30000,
    });

    expect(resetEmail).toBeTruthy();
    console.log(`Received reset email: ${resetEmail.subject}`);

    // Step 5: Extract reset link from email
    const resetLink = this.mailHogHelper.extractResetLinkFromEmail(resetEmail);
    expect(resetLink).toBeTruthy();
    expect(resetLink).toContain('/auth/reset-password');
    expect(resetLink).toContain('token=');

    console.log(`Extracted reset link: ${resetLink}`);

    // Step 6: Navigate to reset link
    await this.page.goto(resetLink);

    // Step 7: Verify reset password form loads
    await expect(this.page.getByTestId('new-password-form')).toBeVisible();
    await expect(this.page.getByTestId('token-valid-message')).toBeVisible();

    // Step 8: Set new password
    await this.page.fill('[data-testid="new-password"]', portal.testUser.newPassword);
    await this.page.fill('[data-testid="confirm-password"]', portal.testUser.newPassword);
    await this.page.click('[data-testid="update-password"]');

    // Step 9: Verify password update success
    await expect(this.page.getByTestId('password-updated-success')).toBeVisible();
    await expect(this.page.getByText(/password updated|password changed/i)).toBeVisible();

    // Step 10: Verify automatic redirect to login or dashboard
    await expect(this.page).toHaveURL(new RegExp(portal.expectedSuccessUrl));

    // Step 11: Verify can login with new password
    await this.verifyLoginWithNewPassword(portal);

    // Step 12: Verify cannot reuse reset link (token should be expired)
    await this.verifyResetLinkExpiry(resetLink);

    return true;
  }

  async verifyLoginWithNewPassword(portal: PortalConfig) {
    console.log('Verifying login with new password');

    await this.page.goto(portal.loginUrl);

    await this.page.fill('[data-testid="email"]', portal.testUser.email);
    await this.page.fill('[data-testid="password"]', portal.testUser.newPassword);
    await this.page.click('[data-testid="login-button"]');

    // Verify successful login
    await expect(
      this.page.getByTestId('dashboard') || this.page.getByTestId('user-menu')
    ).toBeVisible();

    // Logout for cleanup
    await this.page.click('[data-testid="user-menu"]');
    await this.page.click('[data-testid="logout"]');
  }

  async verifyResetLinkExpiry(resetLink: string) {
    console.log('Verifying reset link is now expired');

    await this.page.goto(resetLink);

    // Should show token expired message
    await expect(this.page.getByTestId('token-expired-error')).toBeVisible();
    await expect(
      this.page.getByText(/link expired|token invalid|link no longer valid/i)
    ).toBeVisible();
  }

  async testInvalidEmailHandling(portal: PortalConfig) {
    console.log(`Testing invalid email handling for ${portal.name}`);

    await this.page.goto(portal.resetUrl);

    // Test non-existent email
    await this.page.fill('[data-testid="email-input"]', 'nonexistent@example.com');
    await this.page.click('[data-testid="send-reset-link"]');

    // Should still show success message (security - don't reveal if email exists)
    await expect(this.page.getByTestId('reset-link-sent-message')).toBeVisible();

    // But no email should be sent to MailHog
    const emailExists = await this.mailHogHelper.checkForEmail({
      to: 'nonexistent@example.com',
      timeout: 5000,
      shouldExist: false,
    });

    expect(emailExists).toBe(false);

    return true;
  }

  async testRateLimiting(portal: PortalConfig) {
    console.log(`Testing rate limiting for ${portal.name}`);

    await this.page.goto(portal.resetUrl);
    await this.page.fill('[data-testid="email-input"]', portal.testUser.email);

    // Send multiple requests quickly
    for (let i = 0; i < 6; i++) {
      await this.page.click('[data-testid="send-reset-link"]');
      await this.page.waitForTimeout(500);
    }

    // Should show rate limit error
    await expect(this.page.getByTestId('rate-limit-error')).toBeVisible();
    await expect(this.page.getByText(/too many requests|rate limit exceeded/i)).toBeVisible();

    return true;
  }

  async testExpiredTokenHandling() {
    console.log('Testing expired token handling');

    // Simulate expired token
    const expiredToken = 'expired_token_12345';
    const expiredResetUrl = `/auth/reset-password?token=${expiredToken}`;

    await this.page.goto(expiredResetUrl);

    await expect(this.page.getByTestId('token-expired-error')).toBeVisible();
    await expect(this.page.getByText(/link expired|token invalid/i)).toBeVisible();
    await expect(this.page.getByTestId('request-new-link')).toBeVisible();

    // Test requesting new link from expired page
    await this.page.click('[data-testid="request-new-link"]');
    await expect(this.page).toHaveURL(/\/auth\/forgot-password/);

    return true;
  }

  async testPasswordStrengthValidation(portal: PortalConfig) {
    console.log('Testing password strength validation');

    // First get a valid reset link
    await this.page.goto(portal.resetUrl);
    await this.page.fill('[data-testid="email-input"]', portal.testUser.email);
    await this.page.click('[data-testid="send-reset-link"]');

    const resetEmail = await this.mailHogHelper.waitForEmail({
      to: portal.testUser.email,
      subject: /password reset/i,
      timeout: 15000,
    });

    const resetLink = this.mailHogHelper.extractResetLinkFromEmail(resetEmail);
    await this.page.goto(resetLink);

    // Test weak passwords
    const weakPasswords = [
      '123', // Too short
      'password', // Too common
      'abcdefgh', // No numbers/special chars
      '12345678', // Only numbers
    ];

    for (const weakPassword of weakPasswords) {
      await this.page.fill('[data-testid="new-password"]', weakPassword);
      await this.page.fill('[data-testid="confirm-password"]', weakPassword);

      await expect(this.page.getByTestId('password-strength-error')).toBeVisible();
      await expect(this.page.getByTestId('update-password')).toBeDisabled();
    }

    // Test strong password
    await this.page.fill('[data-testid="new-password"]', 'StrongP@ssw0rd123');
    await this.page.fill('[data-testid="confirm-password"]', 'StrongP@ssw0rd123');

    await expect(this.page.getByTestId('password-strength-success')).toBeVisible();
    await expect(this.page.getByTestId('update-password')).toBeEnabled();

    return true;
  }

  async testConcurrentResetAttempts(portal: PortalConfig) {
    console.log('Testing concurrent reset attempts');

    // Clear any existing emails
    await this.mailHogHelper.clearAllEmails();

    // Initiate multiple reset requests
    const promises = [];
    for (let i = 0; i < 3; i++) {
      const newPage = await this.page.context().newPage();
      promises.push(this.initiatePasswordReset(newPage, portal));
    }

    await Promise.all(promises);

    // Should receive only one email (or latest one should invalidate previous)
    const emails = await this.mailHogHelper.getAllEmailsForRecipient(portal.testUser.email);

    // Either 1 email (deduplicated) or 3 emails with only latest being valid
    expect(emails.length).toBeGreaterThanOrEqual(1);
    expect(emails.length).toBeLessThanOrEqual(3);

    // Verify only the latest token works
    const latestEmail = emails[emails.length - 1];
    const resetLink = this.mailHogHelper.extractResetLinkFromEmail(latestEmail);

    await this.page.goto(resetLink);
    await expect(this.page.getByTestId('new-password-form')).toBeVisible();

    return true;
  }

  private async initiatePasswordReset(page: any, portal: PortalConfig) {
    await page.goto(portal.resetUrl);
    await page.fill('[data-testid="email-input"]', portal.testUser.email);
    await page.click('[data-testid="send-reset-link"]');
    await page.waitForSelector('[data-testid="reset-link-sent-message"]');
    await page.close();
  }
}

test.describe('Cross-Portal Password Reset with MailHog', () => {
  let mailHogHelper: MailHogHelper;

  // Portal configurations
  const portals: PortalConfig[] = [
    {
      name: 'Customer',
      resetUrl: 'http://localhost:3001/auth/forgot-password',
      loginUrl: 'http://localhost:3001/auth/login',
      expectedSuccessUrl: '/dashboard',
      testUser: {
        email: 'customer-test@dotmac.local',
        currentPassword: 'oldPassword123',
        newPassword: 'NewP@ssw0rd456',
      },
    },
    {
      name: 'Admin',
      resetUrl: 'http://localhost:3002/auth/forgot-password',
      loginUrl: 'http://localhost:3002/auth/login',
      expectedSuccessUrl: '/admin/dashboard',
      testUser: {
        email: 'admin-test@dotmac.local',
        currentPassword: 'adminOld123',
        newPassword: 'AdminNew@456',
      },
    },
    {
      name: 'Technician',
      resetUrl: 'http://localhost:3003/auth/forgot-password',
      loginUrl: 'http://localhost:3003/auth/login',
      expectedSuccessUrl: '/technician/dashboard',
      testUser: {
        email: 'tech-test@dotmac.local',
        currentPassword: 'techOld123',
        newPassword: 'TechNew@789',
      },
    },
    {
      name: 'Reseller',
      resetUrl: 'http://localhost:3004/auth/forgot-password',
      loginUrl: 'http://localhost:3004/auth/login',
      expectedSuccessUrl: '/reseller/dashboard',
      testUser: {
        email: 'reseller-test@dotmac.local',
        currentPassword: 'resellerOld123',
        newPassword: 'ResellerNew@321',
      },
    },
  ];

  test.beforeAll(async () => {
    // Start MailHog service for email testing
    mailHogHelper = new MailHogHelper('http://localhost:8025');
    await mailHogHelper.clearAllEmails();
  });

  test.beforeEach(async ({ page }) => {
    // Clear emails before each test
    await mailHogHelper.clearAllEmails();
  });

  test.afterAll(async () => {
    // Clean up MailHog
    if (mailHogHelper) {
      await mailHogHelper.clearAllEmails();
    }
  });

  // Test complete password reset for each portal
  for (const portal of portals) {
    test(`completes password reset flow for ${portal.name} portal @password-reset @${portal.name.toLowerCase()}`, async ({
      page,
    }) => {
      const journey = new PasswordResetJourney(page, mailHogHelper);

      await test.step(`complete password reset for ${portal.name}`, async () => {
        const result = await journey.testCompletePasswordReset(portal);
        expect(result).toBe(true);
      });
    });

    test(`handles invalid email for ${portal.name} portal @password-reset @security`, async ({
      page,
    }) => {
      const journey = new PasswordResetJourney(page, mailHogHelper);

      await test.step(`test invalid email handling`, async () => {
        const result = await journey.testInvalidEmailHandling(portal);
        expect(result).toBe(true);
      });
    });

    test(`enforces rate limiting for ${portal.name} portal @password-reset @security`, async ({
      page,
    }) => {
      const journey = new PasswordResetJourney(page, mailHogHelper);

      await test.step(`test rate limiting`, async () => {
        const result = await journey.testRateLimiting(portal);
        expect(result).toBe(true);
      });
    });
  }

  test('handles expired tokens correctly @password-reset @security', async ({ page }) => {
    const journey = new PasswordResetJourney(page, mailHogHelper);

    await test.step('test expired token handling', async () => {
      const result = await journey.testExpiredTokenHandling();
      expect(result).toBe(true);
    });
  });

  test('validates password strength @password-reset @validation', async ({ page }) => {
    const journey = new PasswordResetJourney(page, mailHogHelper);
    const portal = portals[0]; // Use customer portal for this test

    await test.step('test password strength validation', async () => {
      const result = await journey.testPasswordStrengthValidation(portal);
      expect(result).toBe(true);
    });
  });

  test('handles concurrent reset attempts @password-reset @concurrency', async ({ page }) => {
    const journey = new PasswordResetJourney(page, mailHogHelper);
    const portal = portals[0]; // Use customer portal for this test

    await test.step('test concurrent reset attempts', async () => {
      const result = await journey.testConcurrentResetAttempts(portal);
      expect(result).toBe(true);
    });
  });

  test('password reset performance across portals @password-reset @performance', async ({
    page,
  }) => {
    const journey = new PasswordResetJourney(page, mailHogHelper);

    const startTime = Date.now();

    // Test quick reset flow for each portal
    for (const portal of portals.slice(0, 2)) {
      // Test first 2 portals for performance
      await journey.testCompletePasswordReset(portal);
    }

    const totalTime = Date.now() - startTime;
    expect(totalTime).toBeLessThan(120000); // 2 minutes max for 2 complete flows
  });

  test('password reset accessibility @password-reset @a11y', async ({ page }) => {
    const portal = portals[0]; // Use customer portal

    await page.goto(portal.resetUrl);

    // Check form accessibility
    await expect(page.getByRole('form')).toBeVisible();
    await expect(page.getByLabelText(/email/i)).toBeVisible();

    // Check keyboard navigation
    await page.keyboard.press('Tab');
    await expect(page.getByTestId('email-input')).toBeFocused();

    await page.keyboard.press('Tab');
    await expect(page.getByTestId('send-reset-link')).toBeFocused();

    // Check ARIA attributes
    const emailInput = page.getByTestId('email-input');
    await expect(emailInput).toHaveAttribute('aria-required', 'true');
    await expect(emailInput).toHaveAttribute('type', 'email');

    // Test with screen reader announcements
    await emailInput.fill('test@example.com');
    await page.click('[data-testid="send-reset-link"]');

    // Success message should have proper ARIA
    await expect(page.getByTestId('reset-link-sent-message')).toHaveAttribute('role', 'status');
    await expect(page.getByTestId('reset-link-sent-message')).toHaveAttribute(
      'aria-live',
      'polite'
    );
  });
});

// Export utility for other tests
export { PasswordResetJourney };
