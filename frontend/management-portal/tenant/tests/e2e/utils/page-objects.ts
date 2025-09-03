/**
 * Page Object Models for Tenant Portal E2E Tests
 * Provides reusable page interactions and selectors
 */

import { Page, Locator, expect } from '@playwright/test';

export class BasePage {
  constructor(protected page: Page) {}

  async waitForPageLoad(): Promise<void> {
    await this.page.waitForLoadState('networkidle');
  }

  async waitForElement(selector: string, timeout: number = 10000): Promise<Locator> {
    return this.page.waitForSelector(selector, { timeout });
  }

  async clickAndWait(selector: string, waitForSelector?: string): Promise<void> {
    await this.page.click(selector);
    if (waitForSelector) {
      await this.waitForElement(waitForSelector);
    } else {
      await this.waitForPageLoad();
    }
  }

  async fillAndWait(selector: string, value: string): Promise<void> {
    await this.page.fill(selector, value);
    await this.page.waitForTimeout(100); // Brief wait for input processing
  }
}

export class LoginPage extends BasePage {
  readonly emailInput = '[data-testid="email-input"]';
  readonly passwordInput = '[data-testid="password-input"]';
  readonly loginButton = '[data-testid="login-button"]';
  readonly errorMessage = '[data-testid="error-message"]';

  async goto(): Promise<void> {
    await this.page.goto('/login');
    await this.waitForPageLoad();
  }

  async login(email: string, password: string): Promise<void> {
    await this.fillAndWait(this.emailInput, email);
    await this.fillAndWait(this.passwordInput, password);
    await this.clickAndWait(this.loginButton, '[data-testid="dashboard"]');
  }

  async getErrorMessage(): Promise<string | null> {
    try {
      return await this.page.textContent(this.errorMessage);
    } catch {
      return null;
    }
  }
}

export class DashboardPage extends BasePage {
  readonly dashboardContainer = '[data-testid="dashboard"]';
  readonly subscriptionsCard = '[data-testid="subscriptions-card"]';
  readonly licenseUsageCard = '[data-testid="license-usage-card"]';
  readonly userManagementCard = '[data-testid="user-management-card"]';
  readonly billingCard = '[data-testid="billing-card"]';
  readonly navigationMenu = '[data-testid="navigation-menu"]';

  async goto(): Promise<void> {
    await this.page.goto('/dashboard');
    await this.waitForPageLoad();
  }

  async navigateToSubscriptions(): Promise<void> {
    await this.clickAndWait(
      '[data-testid="nav-subscriptions"]',
      '[data-testid="subscription-management"]'
    );
  }

  async navigateToLicenses(): Promise<void> {
    await this.clickAndWait('[data-testid="nav-licenses"]', '[data-testid="license-management"]');
  }

  async navigateToBilling(): Promise<void> {
    await this.clickAndWait('[data-testid="nav-billing"]', '[data-testid="billing-management"]');
  }

  async navigateToSettings(): Promise<void> {
    await this.clickAndWait('[data-testid="nav-settings"]', '[data-testid="tenant-settings"]');
  }

  async getSubscriptionCount(): Promise<number> {
    const countText = await this.page.textContent('[data-testid="subscription-count"]');
    return parseInt(countText || '0', 10);
  }

  async getLicenseUsagePercentage(): Promise<number> {
    const usageText = await this.page.textContent('[data-testid="license-usage-percentage"]');
    return parseInt((usageText || '0').replace('%', ''), 10);
  }
}

export class SubscriptionManagementPage extends BasePage {
  readonly subscriptionContainer = '[data-testid="subscription-management"]';
  readonly appCatalogButton = '[data-testid="browse-app-catalog"]';
  readonly subscriptionsList = '[data-testid="subscriptions-list"]';
  readonly subscriptionCard = (id: string) => `[data-testid="subscription-${id}"]`;
  readonly upgradeButton = (id: string) => `[data-testid="upgrade-subscription-${id}"]`;
  readonly cancelButton = (id: string) => `[data-testid="cancel-subscription-${id}"]`;
  readonly subscriptionHistoryTab = '[data-testid="subscription-history-tab"]';

  async goto(): Promise<void> {
    await this.page.goto('/subscriptions');
    await this.waitForPageLoad();
  }

  async browseAppCatalog(): Promise<void> {
    await this.clickAndWait(this.appCatalogButton, '[data-testid="app-catalog"]');
  }

  async getActiveSubscriptions(): Promise<string[]> {
    await this.waitForElement(this.subscriptionsList);
    const subscriptions = await this.page.$$(
      '[data-testid^="subscription-"][data-status="active"]'
    );
    return Promise.all(subscriptions.map((sub) => sub.getAttribute('data-testid')));
  }

  async upgradeSubscription(subscriptionId: string, newTier: string): Promise<void> {
    await this.clickAndWait(this.upgradeButton(subscriptionId), '[data-testid="upgrade-modal"]');
    await this.clickAndWait(`[data-testid="tier-${newTier}"]`, '[data-testid="confirm-upgrade"]');
    await this.clickAndWait('[data-testid="confirm-upgrade"]', '[data-testid="upgrade-success"]');
  }

  async cancelSubscription(
    subscriptionId: string,
    reason: string = 'No longer needed'
  ): Promise<void> {
    await this.clickAndWait(this.cancelButton(subscriptionId), '[data-testid="cancel-modal"]');
    await this.fillAndWait('[data-testid="cancellation-reason"]', reason);
    await this.clickAndWait(
      '[data-testid="confirm-cancellation"]',
      '[data-testid="cancellation-success"]'
    );
  }

  async viewSubscriptionHistory(): Promise<void> {
    await this.clickAndWait(
      this.subscriptionHistoryTab,
      '[data-testid="subscription-history-list"]'
    );
  }
}

export class AppCatalogPage extends BasePage {
  readonly catalogContainer = '[data-testid="app-catalog"]';
  readonly categoryFilter = (category: string) =>
    `[data-testid="filter-${category.toLowerCase()}"]`;
  readonly appCard = (appId: string) => `[data-testid="app-${appId}"]`;
  readonly subscribeButton = (appId: string) => `[data-testid="subscribe-${appId}"]`;
  readonly tierSelector = '[data-testid="tier-selector"]';
  readonly licenseQuantity = '[data-testid="license-quantity"]';

  async goto(): Promise<void> {
    await this.page.goto('/app-catalog');
    await this.waitForPageLoad();
  }

  async filterByCategory(
    category: 'ISP' | 'CRM' | 'E-commerce' | 'Project Management'
  ): Promise<void> {
    await this.clickAndWait(this.categoryFilter(category), '[data-testid="filtered-apps"]');
  }

  async subscribeToApp(
    appId: string,
    tier: string = 'standard',
    licenses: number = 5
  ): Promise<void> {
    await this.clickAndWait(this.subscribeButton(appId), '[data-testid="subscription-modal"]');

    // Select tier
    await this.clickAndWait(`${this.tierSelector} [data-value="${tier}"]`);

    // Set license quantity
    await this.fillAndWait(this.licenseQuantity, licenses.toString());

    // Confirm subscription
    await this.clickAndWait(
      '[data-testid="confirm-subscription"]',
      '[data-testid="subscription-success"]'
    );
  }

  async getAppDetails(appId: string): Promise<{ name: string; category: string; price: string }> {
    const appCard = this.page.locator(this.appCard(appId));
    const name = await appCard.locator('[data-testid="app-name"]').textContent();
    const category = await appCard.locator('[data-testid="app-category"]').textContent();
    const price = await appCard.locator('[data-testid="app-price"]').textContent();

    return { name: name || '', category: category || '', price: price || '' };
  }
}

export class LicenseManagementPage extends BasePage {
  readonly licenseContainer = '[data-testid="license-management"]';
  readonly licensesList = '[data-testid="licenses-list"]';
  readonly licenseCard = (appId: string) => `[data-testid="license-${appId}"]`;
  readonly upgradeButton = (appId: string) => `[data-testid="upgrade-license-${appId}"]`;
  readonly usageChart = '[data-testid="license-usage-chart"]';
  readonly alertsList = '[data-testid="license-alerts"]';

  async goto(): Promise<void> {
    await this.page.goto('/licenses');
    await this.waitForPageLoad();
  }

  async getLicenseInfo(
    appId: string
  ): Promise<{ used: number; total: number; features: string[] }> {
    const card = this.page.locator(this.licenseCard(appId));
    const used = parseInt(
      (await card.locator('[data-testid="licenses-used"]').textContent()) || '0'
    );
    const total = parseInt(
      (await card.locator('[data-testid="licenses-total"]').textContent()) || '0'
    );
    const features = await card.locator('[data-testid="license-features"] li').allTextContents();

    return { used, total, features };
  }

  async requestLicenseUpgrade(appId: string, newQuantity: number): Promise<void> {
    await this.clickAndWait(this.upgradeButton(appId), '[data-testid="upgrade-license-modal"]');
    await this.fillAndWait('[data-testid="license-quantity-input"]', newQuantity.toString());
    await this.clickAndWait(
      '[data-testid="submit-upgrade-request"]',
      '[data-testid="upgrade-request-success"]'
    );
  }

  async getUsageAlerts(): Promise<string[]> {
    await this.waitForElement(this.alertsList);
    return await this.page.locator('[data-testid="license-alert"]').allTextContents();
  }

  async validateFeatureAccess(appId: string, feature: string): Promise<boolean> {
    const card = this.page.locator(this.licenseCard(appId));
    const features = await card.locator('[data-testid="available-features"] li').allTextContents();
    return features.some((f) => f.includes(feature));
  }
}

export class BillingPage extends BasePage {
  readonly billingContainer = '[data-testid="billing-management"]';
  readonly currentBillCard = '[data-testid="current-bill"]';
  readonly paymentMethodsCard = '[data-testid="payment-methods"]';
  readonly billingHistoryTable = '[data-testid="billing-history"]';
  readonly usageAnalyticsCard = '[data-testid="usage-analytics"]';
  readonly downloadInvoiceButton = (invoiceId: string) =>
    `[data-testid="download-invoice-${invoiceId}"]`;

  async goto(): Promise<void> {
    await this.page.goto('/billing');
    await this.waitForPageLoad();
  }

  async getCurrentBillAmount(): Promise<number> {
    const amountText = await this.page.textContent('[data-testid="current-bill-amount"]');
    return parseFloat((amountText || '0').replace(/[^0-9.]/g, ''));
  }

  async getPaymentMethods(): Promise<string[]> {
    return await this.page.locator('[data-testid="payment-method"]').allTextContents();
  }

  async getBillingHistory(): Promise<Array<{ date: string; amount: string; status: string }>> {
    const rows = await this.page.locator('[data-testid="billing-history"] tbody tr').all();
    const history = [];

    for (const row of rows) {
      const date = await row.locator('td:nth-child(1)').textContent();
      const amount = await row.locator('td:nth-child(2)').textContent();
      const status = await row.locator('td:nth-child(3)').textContent();
      history.push({ date: date || '', amount: amount || '', status: status || '' });
    }

    return history;
  }

  async downloadInvoice(invoiceId: string): Promise<void> {
    const downloadPromise = this.page.waitForEvent('download');
    await this.page.click(this.downloadInvoiceButton(invoiceId));
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain('invoice');
  }
}

export class SettingsPage extends BasePage {
  readonly settingsContainer = '[data-testid="tenant-settings"]';
  readonly organizationTab = '[data-testid="organization-tab"]';
  readonly usersTab = '[data-testid="users-tab"]';
  readonly permissionsTab = '[data-testid="permissions-tab"]';
  readonly addUserButton = '[data-testid="add-user-button"]';
  readonly userRow = (userId: string) => `[data-testid="user-${userId}"]`;

  async goto(): Promise<void> {
    await this.page.goto('/settings');
    await this.waitForPageLoad();
  }

  async navigateToUsersTab(): Promise<void> {
    await this.clickAndWait(this.usersTab, '[data-testid="users-list"]');
  }

  async navigateToPermissionsTab(): Promise<void> {
    await this.clickAndWait(this.permissionsTab, '[data-testid="permissions-matrix"]');
  }

  async addUser(email: string, name: string, role: 'admin' | 'manager' | 'user'): Promise<void> {
    await this.clickAndWait(this.addUserButton, '[data-testid="add-user-modal"]');
    await this.fillAndWait('[data-testid="user-email"]', email);
    await this.fillAndWait('[data-testid="user-name"]', name);
    await this.clickAndWait(`[data-testid="role-${role}"]`);
    await this.clickAndWait('[data-testid="save-user"]', '[data-testid="user-added-success"]');
  }

  async editUserRole(userId: string, newRole: 'admin' | 'manager' | 'user'): Promise<void> {
    await this.clickAndWait(
      `${this.userRow(userId)} [data-testid="edit-user"]`,
      '[data-testid="edit-user-modal"]'
    );
    await this.clickAndWait(`[data-testid="role-${newRole}"]`);
    await this.clickAndWait('[data-testid="save-changes"]', '[data-testid="user-updated-success"]');
  }

  async getUsersList(): Promise<
    Array<{ id: string; email: string; role: string; status: string }>
  > {
    const rows = await this.page.locator('[data-testid="users-list"] tbody tr').all();
    const users = [];

    for (const row of rows) {
      const id = await row.getAttribute('data-user-id');
      const email = await row.locator('[data-testid="user-email"]').textContent();
      const role = await row.locator('[data-testid="user-role"]').textContent();
      const status = await row.locator('[data-testid="user-status"]').textContent();
      users.push({
        id: id || '',
        email: email || '',
        role: role || '',
        status: status || '',
      });
    }

    return users;
  }
}
