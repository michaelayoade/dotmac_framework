/**
 * Cross-Portal Email Verification E2E Tests with MailHog Integration  
 * Tests email verification flow: registration → email → MailHog fetch → verification link click
 */

import { test, expect } from '@playwright/test';
import { MailHogHelper } from '../testing/e2e/shared-scenarios/mailhog-helper';

interface VerificationPortalConfig {
  name: string;
  registrationUrl: string;
  loginUrl: string;
  verificationSuccessUrl: string;
  testUser: {
    email: string;
    password: string;
    name: string;
    company?: string;
  };
}

class EmailVerificationJourney {
  constructor(
    public page: any,
    public mailHogHelper: MailHogHelper
  ) {}

  async testCompleteEmailVerification(portal: VerificationPortalConfig) {
    console.log(`Testing email verification flow for ${portal.name} portal`);

    // Step 1: Navigate to registration page
    await this.page.goto(portal.registrationUrl);
    await expect(this.page.getByTestId('registration-form')).toBeVisible();

    // Step 2: Fill registration form
    await this.page.fill('[data-testid="email-input"]', portal.testUser.email);
    await this.page.fill('[data-testid="password-input"]', portal.testUser.password);
    await this.page.fill('[data-testid="name-input"]', portal.testUser.name);
    
    if (portal.testUser.company) {
      await this.page.fill('[data-testid="company-input"]', portal.testUser.company);
    }

    await this.page.click('[data-testid="register-button"]');

    // Step 3: Verify registration success and email verification prompt
    await expect(this.page.getByTestId('registration-success')).toBeVisible();
    await expect(this.page.getByTestId('email-verification-prompt')).toBeVisible();
    await expect(this.page.getByText(/verification email sent/i)).toBeVisible();

    // Step 4: Wait for verification email in MailHog
    console.log('Waiting for verification email in MailHog...');
    const verificationEmail = await this.mailHogHelper.waitForEmail({
      to: portal.testUser.email,
      subject: /verify.*email|email.*verification|confirm.*email/i,
      timeout: 30000
    });

    expect(verificationEmail).toBeTruthy();
    console.log(`Received verification email: ${verificationEmail.subject}`);

    // Step 5: Extract verification link
    const verificationLink = this.mailHogHelper.extractVerificationLinkFromEmail(verificationEmail);
    expect(verificationLink).toBeTruthy();
    expect(verificationLink).toContain('/auth/verify-email');

    console.log(`Extracted verification link: ${verificationLink}`);

    // Step 6: Click verification link
    await this.page.goto(verificationLink);

    // Step 7: Verify email verification success
    await expect(this.page.getByTestId('email-verified-success')).toBeVisible();
    await expect(this.page.getByText(/email verified|verification complete/i)).toBeVisible();

    // Step 8: Verify redirect to appropriate page
    await expect(this.page).toHaveURL(new RegExp(portal.verificationSuccessUrl));

    // Step 9: Verify user can now login normally
    await this.verifyLoginAfterVerification(portal);

    return true;
  }

  async verifyLoginAfterVerification(portal: VerificationPortalConfig) {
    console.log('Verifying login works after email verification');

    await this.page.goto(portal.loginUrl);
    
    await this.page.fill('[data-testid="email"]', portal.testUser.email);
    await this.page.fill('[data-testid="password"]', portal.testUser.password);
    await this.page.click('[data-testid="login-button"]');

    // Should successfully login without email verification warning
    await expect(this.page.getByTestId('dashboard') || this.page.getByTestId('user-menu')).toBeVisible();
    
    // Should not show unverified email warning
    await expect(this.page.getByTestId('email-unverified-warning')).not.toBeVisible();
  }

  async testResendVerificationEmail(portal: VerificationPortalConfig) {
    console.log('Testing resend verification email flow');

    // Clear existing emails
    await this.mailHogHelper.clearAllEmails();

    // Register user
    await this.page.goto(portal.registrationUrl);
    await this.fillRegistrationForm(portal);
    await this.page.click('[data-testid="register-button"]');

    // Wait for initial verification email
    await this.mailHogHelper.waitForEmail({
      to: portal.testUser.email,
      subject: /verify.*email/i,
      timeout: 15000
    });

    // Click resend verification link
    await this.page.click('[data-testid="resend-verification-email"]');

    // Verify success message
    await expect(this.page.getByTestId('verification-email-resent')).toBeVisible();
    await expect(this.page.getByText(/verification email sent again/i)).toBeVisible();

    // Verify second email was sent
    const emails = await this.mailHogHelper.getAllEmailsForRecipient(portal.testUser.email);
    expect(emails.length).toBe(2);

    // Both emails should have verification links
    const link1 = this.mailHogHelper.extractVerificationLinkFromEmail(emails[0]);
    const link2 = this.mailHogHelper.extractVerificationLinkFromEmail(emails[1]);
    
    expect(link1).toBeTruthy();
    expect(link2).toBeTruthy();
    
    // Links should be different (different tokens)
    expect(link1).not.toBe(link2);

    return true;
  }

  async testExpiredVerificationToken(portal: VerificationPortalConfig) {
    console.log('Testing expired verification token handling');

    // Test with expired token
    const expiredToken = 'expired_verification_token_123';
    const expiredVerificationUrl = `/auth/verify-email?token=${expiredToken}`;

    await this.page.goto(expiredVerificationUrl);

    // Should show expired token error
    await expect(this.page.getByTestId('verification-token-expired')).toBeVisible();
    await expect(this.page.getByText(/link expired|token invalid|link no longer valid/i)).toBeVisible();

    // Should provide option to resend verification
    await expect(this.page.getByTestId('resend-verification-link')).toBeVisible();

    return true;
  }

  async testUnverifiedUserLogin(portal: VerificationPortalConfig) {
    console.log('Testing login with unverified email');

    // Register user but don't verify email
    await this.page.goto(portal.registrationUrl);
    await this.fillRegistrationForm(portal);
    await this.page.click('[data-testid="register-button"]');

    // Try to login without verifying email
    await this.page.goto(portal.loginUrl);
    await this.page.fill('[data-testid="email"]', portal.testUser.email);
    await this.page.fill('[data-testid="password"]', portal.testUser.password);
    await this.page.click('[data-testid="login-button"]');

    // Should login but show unverified warning
    await expect(this.page.getByTestId('email-unverified-warning')).toBeVisible();
    await expect(this.page.getByText(/email not verified|please verify your email/i)).toBeVisible();

    // Should show resend verification option
    await expect(this.page.getByTestId('resend-verification-button')).toBeVisible();

    return true;
  }

  private async fillRegistrationForm(portal: VerificationPortalConfig) {
    await this.page.fill('[data-testid="email-input"]', portal.testUser.email);
    await this.page.fill('[data-testid="password-input"]', portal.testUser.password);
    await this.page.fill('[data-testid="name-input"]', portal.testUser.name);
    
    if (portal.testUser.company) {
      await this.page.fill('[data-testid="company-input"]', portal.testUser.company);
    }
  }
}

test.describe('Cross-Portal Email Verification with MailHog', () => {
  let mailHogHelper: MailHogHelper;

  // Portal configurations
  const verificationPortals: VerificationPortalConfig[] = [
    {
      name: 'Customer',
      registrationUrl: 'http://localhost:3001/auth/register',
      loginUrl: 'http://localhost:3001/auth/login',
      verificationSuccessUrl: '/dashboard',
      testUser: {
        email: 'customer-verify@dotmac.local',
        password: 'TestP@ssw0rd123',
        name: 'Test Customer',
        company: 'Test Company Inc.'
      }
    },
    {
      name: 'Reseller',
      registrationUrl: 'http://localhost:3004/auth/register',
      loginUrl: 'http://localhost:3004/auth/login', 
      verificationSuccessUrl: '/reseller/dashboard',
      testUser: {
        email: 'reseller-verify@dotmac.local',
        password: 'ResellerP@ss123',
        name: 'Test Reseller',
        company: 'Reseller Corp'
      }
    }
  ];

  test.beforeAll(async () => {
    mailHogHelper = new MailHogHelper('http://localhost:8025');
    
    // Verify MailHog is accessible
    const isConnected = await mailHogHelper.validateMailHogConnection();
    if (!isConnected) {
      throw new Error('MailHog is not accessible at http://localhost:8025. Please start MailHog service.');
    }
    
    await mailHogHelper.clearAllEmails();
  });

  test.beforeEach(async ({ page }) => {
    await mailHogHelper.clearAllEmails();
  });

  test.afterAll(async () => {
    if (mailHogHelper) {
      await mailHogHelper.clearAllEmails();
    }
  });

  // Test complete email verification for each portal
  for (const portal of verificationPortals) {
    test(`completes email verification flow for ${portal.name} portal @email-verification @${portal.name.toLowerCase()}`, async ({ page }) => {
      const journey = new EmailVerificationJourney(page, mailHogHelper);
      
      await test.step(`complete email verification for ${portal.name}`, async () => {
        const result = await journey.testCompleteEmailVerification(portal);
        expect(result).toBe(true);
      });
    });

    test(`handles verification email resend for ${portal.name} portal @email-verification @resend`, async ({ page }) => {
      const journey = new EmailVerificationJourney(page, mailHogHelper);
      
      await test.step(`test resend verification email`, async () => {
        const result = await journey.testResendVerificationEmail(portal);
        expect(result).toBe(true);
      });
    });

    test(`handles unverified login for ${portal.name} portal @email-verification @unverified`, async ({ page }) => {
      const journey = new EmailVerificationJourney(page, mailHogHelper);
      
      await test.step(`test unverified user login`, async () => {
        const result = await journey.testUnverifiedUserLogin(portal);
        expect(result).toBe(true);
      });
    });
  }

  test('handles expired verification tokens @email-verification @security', async ({ page }) => {
    const journey = new EmailVerificationJourney(page, mailHogHelper);
    const portal = verificationPortals[0];
    
    await test.step('test expired verification token', async () => {
      const result = await journey.testExpiredVerificationToken(portal);
      expect(result).toBe(true);
    });
  });

  test('email verification performance @email-verification @performance', async ({ page }) => {
    const journey = new EmailVerificationJourney(page, mailHogHelper);
    
    const startTime = Date.now();
    
    // Test verification flow for first portal
    await journey.testCompleteEmailVerification(verificationPortals[0]);
    
    const totalTime = Date.now() - startTime;
    expect(totalTime).toBeLessThan(60000); // 1 minute max for complete flow
  });

  test('email verification accessibility @email-verification @a11y', async ({ page }) => {
    const portal = verificationPortals[0];
    
    await page.goto(portal.registrationUrl);
    
    // Check form accessibility
    await expect(page.getByRole('form')).toBeVisible();
    
    // Check required field attributes
    const emailInput = page.getByTestId('email-input');
    await expect(emailInput).toHaveAttribute('aria-required', 'true');
    await expect(emailInput).toHaveAttribute('type', 'email');
    
    // Test keyboard navigation
    await page.keyboard.press('Tab'); // Email field
    await expect(emailInput).toBeFocused();
    
    await page.keyboard.press('Tab'); // Password field
    await expect(page.getByTestId('password-input')).toBeFocused();
    
    // Fill form and submit
    await page.fill('[data-testid="email-input"]', portal.testUser.email);
    await page.fill('[data-testid="password-input"]', portal.testUser.password);
    await page.fill('[data-testid="name-input"]', portal.testUser.name);
    await page.click('[data-testid="register-button"]');
    
    // Check success message accessibility
    await expect(page.getByTestId('registration-success')).toHaveAttribute('role', 'status');
    await expect(page.getByTestId('email-verification-prompt')).toHaveAttribute('aria-live', 'polite');
  });

  test('mailhog integration stats @email-verification @testing', async ({ page }) => {
    const journey = new EmailVerificationJourney(page, mailHogHelper);
    
    // Generate some test emails
    await journey.testCompleteEmailVerification(verificationPortals[0]);
    await journey.testResendVerificationEmail(verificationPortals[1]);
    
    // Get email statistics
    const stats = await mailHogHelper.getEmailStats();
    
    expect(stats.totalEmails).toBeGreaterThan(0);
    expect(stats.emailsByDomain['dotmac.local']).toBeGreaterThan(0);
    expect(stats.recentEmails).toBeGreaterThan(0);
    
    console.log('Email stats:', stats);
  });
});

export { EmailVerificationJourney };