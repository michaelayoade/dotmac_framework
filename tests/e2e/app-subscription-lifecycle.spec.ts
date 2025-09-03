/**
 * App Subscription Lifecycle E2E Tests
 * 
 * Tests the complete lifecycle of app subscriptions within a tenant
 * 
 * Test Scenarios:
 * - Subscribe to new app (CRM) → app becomes available
 * - App configuration and initial setup  
 * - Data migration between app versions
 * - App unsubscription → data archival and access removal
 * - Subscription billing and usage tracking
 */

import { test, expect, Page, BrowserContext } from '@playwright/test';
import { LicenseTestHelper, MultiAppTestHelper } from '../../src/dotmac_shared/tests/e2e/licensing/helpers';
import { LicenseAssertions } from '../../src/dotmac_shared/tests/e2e/licensing/assertions';
import { license_fixtures } from '../../src/dotmac_shared/tests/e2e/licensing/fixtures';

// Available apps for subscription
const AVAILABLE_APPS = {
  crm: {
    name: 'Customer Relationship Management',
    description: 'Manage leads, opportunities, and customer relationships',
    pricing: { basic: 25, premium: 50, enterprise: 100 },
    features: ['lead_management', 'opportunity_tracking', 'contact_management'],
    setup_required: true,
    data_migration: false
  },
  'field-ops': {
    name: 'Field Operations',
    description: 'Technician dispatch and field service management',
    pricing: { basic: 15, premium: 30, enterprise: 60 },
    features: ['technician_dispatch', 'work_orders', 'mobile_tools'],
    setup_required: true,
    data_migration: true
  },
  'inventory-management': {
    name: 'Inventory Management',
    description: 'Track and manage inventory across locations',
    pricing: { basic: 20, premium: 40, enterprise: 80 },
    features: ['inventory_tracking', 'purchase_orders', 'warehouse_management'],
    setup_required: false,
    data_migration: true
  },
  'analytics-pro': {
    name: 'Advanced Analytics',
    description: 'Advanced reporting and business intelligence',
    pricing: { basic: null, premium: 75, enterprise: 120 },
    features: ['custom_dashboards', 'predictive_analytics', 'data_export'],
    setup_required: false,
    data_migration: false
  }
};

test.describe('App Subscription Lifecycle', () => {
  let helper: LicenseTestHelper;
  let multiAppHelper: MultiAppTestHelper;
  
  test.beforeEach(async ({ page, context }) => {
    helper = new LicenseTestHelper(page);
    multiAppHelper = new MultiAppTestHelper(context);
  });

  test.afterEach(async () => {
    await multiAppHelper.cleanup();
  });

  test.describe('App Subscription Process', () => {
    
    test('should display available apps for subscription', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('premium');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Navigate to app marketplace
        await helper.navigate_to_feature('/apps/marketplace');
        
        // Should see available apps
        for (const [appKey, appInfo] of Object.entries(AVAILABLE_APPS)) {
          const appCard = page.locator(`[data-testid="app-card-${appKey}"]`);
          await expect(appCard).to_be_visible();
          await expect(appCard).to_contain_text(appInfo.name);
          await expect(appCard).to_contain_text(appInfo.description);
          
          // Should show pricing for current plan
          const pricing = appInfo.pricing.premium;
          if (pricing) {
            await expect(appCard).to_contain_text(`$${pricing}`);
          } else {
            await expect(appCard).to_contain_text('Not available');
          }
        }
      });
    });

    test('should subscribe to CRM app successfully', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('premium');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Navigate to app marketplace
        await helper.navigate_to_feature('/apps/marketplace');
        
        // Click subscribe on CRM app
        const crmCard = page.locator('[data-testid="app-card-crm"]');
        await crmCard.locator('[data-testid="subscribe-button"]').click();
        
        // Should show subscription confirmation dialog
        const confirmDialog = page.locator('[data-testid="subscription-confirm-dialog"]');
        await expect(confirmDialog).to_be_visible();
        await expect(confirmDialog).to_contain_text('Customer Relationship Management');
        await expect(confirmDialog).to_contain_text('$50/month');
        
        // Confirm subscription
        await page.click('[data-testid="confirm-subscription"]');
        
        // Should show success message
        await expect(page.locator('[data-testid="subscription-success"]')).to_be_visible();
        
        // CRM should now appear in subscribed apps
        await helper.navigate_to_feature('/apps/subscribed');
        const subscribedCrm = page.locator('[data-testid="subscribed-app-crm"]');
        await expect(subscribedCrm).to_be_visible();
        await expect(subscribedCrm).to_contain_text('Active');
        
        // Should have launch button
        await expect(subscribedCrm.locator('[data-testid="launch-app"]')).to_be_visible();
      });
    });

    test('should handle subscription failures gracefully', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('basic');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Try to subscribe to analytics-pro (not available on basic plan)
        await helper.navigate_to_feature('/apps/marketplace');
        
        const analyticsCard = page.locator('[data-testid="app-card-analytics-pro"]');
        await expect(analyticsCard.locator('[data-testid="subscribe-button"]')).to_be_disabled();
        
        // Should show upgrade prompt
        await analyticsCard.locator('[data-testid="upgrade-required"]').click();
        
        const upgradeDialog = page.locator('[data-testid="upgrade-plan-dialog"]');
        await expect(upgradeDialog).to_be_visible();
        await expect(upgradeDialog).to_contain_text('Premium plan required');
      });
    });

    test('should handle concurrent subscription attempts', async ({ context }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        // Create two browser contexts to simulate concurrent users
        const context1 = await context.browser()?.newContext();
        const context2 = await context.browser()?.newContext();
        
        const page1 = await context1?.newPage();
        const page2 = await context2?.newPage();
        
        const helper1 = new LicenseTestHelper(page1!);
        const helper2 = new LicenseTestHelper(page2!);
        
        // Both users try to subscribe to the same app
        await helper1.login_as_admin(tenant.tenant_id, 'admin1@test.com');
        await helper2.login_as_admin(tenant.tenant_id, 'admin2@test.com');
        
        await Promise.all([
          helper1.navigate_to_feature('/apps/marketplace'),
          helper2.navigate_to_feature('/apps/marketplace')
        ]);
        
        // Both try to subscribe to CRM simultaneously
        await Promise.all([
          page1!.click('[data-testid="app-card-crm"] [data-testid="subscribe-button"]'),
          page2!.click('[data-testid="app-card-crm"] [data-testid="subscribe-button"]')
        ]);
        
        await Promise.all([
          page1!.click('[data-testid="confirm-subscription"]'),
          page2!.click('[data-testid="confirm-subscription"]')
        ]);
        
        // One should succeed, the other should show "already subscribed"
        const results = await Promise.all([
          page1!.locator('[data-testid="subscription-success"], [data-testid="already-subscribed"]').textContent(),
          page2!.locator('[data-testid="subscription-success"], [data-testid="already-subscribed"]').textContent()
        ]);
        
        const successCount = results.filter(text => text?.includes('success')).length;
        const alreadySubscribedCount = results.filter(text => text?.includes('already')).length;
        
        expect(successCount).toBe(1);
        expect(alreadySubscribedCount).toBe(1);
        
        await context1?.close();
        await context2?.close();
      });
    });
  });

  test.describe('App Configuration and Setup', () => {
    
    test('should guide through initial app setup for CRM', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('premium');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        // Subscribe to CRM first
        await fixtures.create_feature_flag(tenant.tenant_id, 'crm_access', { enabled: true });
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Launch CRM for first time
        await helper.navigate_to_feature('/apps/subscribed');
        await page.click('[data-testid="launch-crm"]');
        
        // Should show setup wizard
        const setupWizard = page.locator('[data-testid="app-setup-wizard"]');
        await expect(setupWizard).to_be_visible();
        await expect(setupWizard).to_contain_text('Welcome to CRM');
        
        // Step 1: Basic Configuration
        await expect(page.locator('[data-testid="setup-step-1"]')).to_be_visible();
        await page.fill('[data-testid="company-name"]', 'Test ISP Company');
        await page.selectOption('[data-testid="industry"]', 'telecommunications');
        await page.fill('[data-testid="sales-team-size"]', '10');
        await page.click('[data-testid="next-step"]');
        
        // Step 2: Integration Setup  
        await expect(page.locator('[data-testid="setup-step-2"]')).to_be_visible();
        await page.check('[data-testid="integrate-customer-data"]');
        await page.check('[data-testid="integrate-billing-system"]');
        await page.click('[data-testid="next-step"]');
        
        // Step 3: User Permissions
        await expect(page.locator('[data-testid="setup-step-3"]')).to_be_visible();
        await page.check('[data-testid="import-existing-users"]');
        await page.click('[data-testid="complete-setup"]');
        
        // Should show setup completion
        await expect(page.locator('[data-testid="setup-complete"]')).to_be_visible();
        await expect(page.locator('[data-testid="setup-complete"]')).to_contain_text('CRM is ready');
        
        // Should redirect to CRM dashboard
        await page.click('[data-testid="enter-crm"]');
        await expect(page.locator('[data-testid="crm-dashboard"]')).to_be_visible();
      });
    });

    test('should save configuration and allow modification', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await fixtures.create_feature_flag(tenant.tenant_id, 'field_ops_access', { enabled: true });
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Complete initial setup
        await helper.navigate_to_feature('/apps/field-ops');
        
        // Go through setup wizard
        await page.fill('[data-testid="service-area-radius"]', '25');
        await page.selectOption('[data-testid="dispatch-strategy"]', 'closest_technician');
        await page.check('[data-testid="enable-gps-tracking"]');
        await page.click('[data-testid="complete-setup"]');
        
        // Later, modify configuration
        await helper.navigate_to_feature('/apps/field-ops/settings');
        
        // Should show current configuration
        await expect(page.locator('[data-testid="service-area-radius"]')).to_have_value('25');
        await expect(page.locator('[data-testid="dispatch-strategy"]')).to_have_value('closest_technician');
        await expect(page.locator('[data-testid="enable-gps-tracking"]')).to_be_checked();
        
        // Modify settings
        await page.fill('[data-testid="service-area-radius"]', '50');
        await page.selectOption('[data-testid="dispatch-strategy"]', 'skill_based');
        await page.click('[data-testid="save-settings"]');
        
        // Should see success confirmation
        await expect(page.locator('[data-testid="settings-saved"]')).to_be_visible();
        
        // Refresh and verify changes persisted
        await page.reload();
        await expect(page.locator('[data-testid="service-area-radius"]')).to_have_value('50');
        await expect(page.locator('[data-testid="dispatch-strategy"]')).to_have_value('skill_based');
      });
    });

    test('should validate configuration requirements', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('premium');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await fixtures.create_feature_flag(tenant.tenant_id, 'inventory_access', { enabled: true });
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Start inventory management setup
        await helper.navigate_to_feature('/apps/inventory-management');
        
        // Try to complete setup with missing required fields
        await page.click('[data-testid="complete-setup"]');
        
        // Should show validation errors
        await expect(page.locator('[data-testid="validation-error"]')).to_be_visible();
        await expect(page.locator('[data-testid="validation-error"]')).to_contain_text('Primary warehouse location is required');
        
        // Fill required fields
        await page.fill('[data-testid="warehouse-name"]', 'Main Warehouse');
        await page.fill('[data-testid="warehouse-address"]', '123 Storage Ave');
        await page.selectOption('[data-testid="currency"]', 'USD');
        
        // Should now allow completion
        await page.click('[data-testid="complete-setup"]');
        await expect(page.locator('[data-testid="setup-complete"]')).to_be_visible();
      });
    });
  });

  test.describe('Data Migration Between App Versions', () => {
    
    test('should migrate data when upgrading app version', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await fixtures.create_feature_flag(tenant.tenant_id, 'field_ops_access', { enabled: true });
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // App is currently on v1.0 with some data
        await helper.navigate_to_feature('/apps/field-ops');
        
        // Create some test data in v1.0
        await page.click('[data-testid="create-work-order"]');
        await page.fill('[data-testid="work-order-title"]', 'Install Fiber');
        await page.fill('[data-testid="customer-name"]', 'John Doe');
        await page.click('[data-testid="save-work-order"]');
        
        // Simulate app update notification
        await helper.navigate_to_feature('/apps/subscribed');
        
        // Should see update available
        const fieldOpsCard = page.locator('[data-testid="subscribed-app-field-ops"]');
        await expect(fieldOpsCard.locator('[data-testid="update-available"]')).to_be_visible();
        
        // Start update process
        await fieldOpsCard.locator('[data-testid="update-app"]').click();
        
        // Should show migration dialog
        const migrationDialog = page.locator('[data-testid="data-migration-dialog"]');
        await expect(migrationDialog).to_be_visible();
        await expect(migrationDialog).to_contain_text('migrate your existing data');
        await expect(migrationDialog).to_contain_text('1 work order will be migrated');
        
        // Confirm migration
        await page.click('[data-testid="start-migration"]');
        
        // Should show migration progress
        const progressBar = page.locator('[data-testid="migration-progress"]');
        await expect(progressBar).to_be_visible();
        
        // Wait for migration completion
        await expect(page.locator('[data-testid="migration-complete"]')).to_be_visible({ timeout: 30000 });
        
        // Launch updated app
        await page.click('[data-testid="launch-updated-app"]');
        
        // Should see migrated data in new version
        await expect(page.locator('[data-testid="work-order-Install Fiber"]')).to_be_visible();
        
        // Should see new v2.0 features
        await expect(page.locator('[data-testid="advanced-scheduling"]')).to_be_visible();
      });
    });

    test('should handle migration failures with rollback', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await fixtures.create_feature_flag(tenant.tenant_id, 'inventory_access', { enabled: true });
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Simulate migration failure
        await helper.navigate_to_feature('/apps/subscribed');
        
        const inventoryCard = page.locator('[data-testid="subscribed-app-inventory-management"]');
        await inventoryCard.locator('[data-testid="update-app"]').click();
        
        await page.click('[data-testid="start-migration"]');
        
        // Simulate migration failure by injecting error
        await page.evaluate(() => {
          window.localStorage.setItem('simulate_migration_failure', 'true');
        });
        
        // Should show error message
        await expect(page.locator('[data-testid="migration-failed"]')).to_be_visible({ timeout: 20000 });
        await expect(page.locator('[data-testid="migration-failed"]')).to_contain_text('Migration failed');
        
        // Should offer rollback option
        await expect(page.locator('[data-testid="rollback-button"]')).to_be_visible();
        
        // Perform rollback
        await page.click('[data-testid="rollback-button"]');
        
        await expect(page.locator('[data-testid="rollback-complete"]')).to_be_visible();
        
        // Should still be on original version
        await inventoryCard.locator('[data-testid="launch-app"]').click();
        await expect(page.locator('[data-testid="app-version"]')).to_contain_text('v1.0');
      });
    });

    test('should preserve custom configurations during migration', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await fixtures.create_feature_flag(tenant.tenant_id, 'crm_access', { enabled: true });
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Set up custom configuration in CRM v1
        await helper.navigate_to_feature('/apps/crm/settings');
        await page.selectOption('[data-testid="lead-source-default"]', 'website');
        await page.check('[data-testid="auto-assign-leads"]');
        await page.fill('[data-testid="follow-up-days"]', '3');
        await page.click('[data-testid="save-settings"]');
        
        // Update to v2
        await helper.navigate_to_feature('/apps/subscribed');
        await page.click('[data-testid="update-crm"]');
        await page.click('[data-testid="start-migration"]');
        
        await expect(page.locator('[data-testid="migration-complete"]')).to_be_visible({ timeout: 30000 });
        
        // Check that custom settings were preserved
        await page.click('[data-testid="launch-updated-app"]');
        await helper.navigate_to_feature('/apps/crm/settings');
        
        await expect(page.locator('[data-testid="lead-source-default"]')).to_have_value('website');
        await expect(page.locator('[data-testid="auto-assign-leads"]')).to_be_checked();
        await expect(page.locator('[data-testid="follow-up-days"]')).to_have_value('3');
      });
    });
  });

  test.describe('App Unsubscription and Data Archival', () => {
    
    test('should unsubscribe from app with data archival', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('premium');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await fixtures.create_feature_flag(tenant.tenant_id, 'crm_access', { enabled: true });
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Create some data in CRM
        await helper.navigate_to_feature('/apps/crm');
        await page.click('[data-testid="create-lead"]');
        await page.fill('[data-testid="lead-name"]', 'Potential Customer');
        await page.click('[data-testid="save-lead"]');
        
        // Unsubscribe from CRM
        await helper.navigate_to_feature('/apps/subscribed');
        const crmCard = page.locator('[data-testid="subscribed-app-crm"]');
        await crmCard.locator('[data-testid="manage-subscription"]').click();
        
        // Should show manage subscription dialog
        const manageDialog = page.locator('[data-testid="manage-subscription-dialog"]');
        await expect(manageDialog).to_be_visible();
        
        await page.click('[data-testid="unsubscribe-app"]');
        
        // Should warn about data archival
        const archivalWarning = page.locator('[data-testid="data-archival-warning"]');
        await expect(archivalWarning).to_be_visible();
        await expect(archivalWarning).to_contain_text('Your data will be archived');
        await expect(archivalWarning).to_contain_text('1 lead will be archived');
        
        // Should offer data export option
        await expect(page.locator('[data-testid="export-data-checkbox"]')).to_be_visible();
        await page.check('[data-testid="export-data-checkbox"]');
        
        // Confirm unsubscription
        await page.click('[data-testid="confirm-unsubscribe"]');
        
        // Should show export progress
        await expect(page.locator('[data-testid="data-export-progress"]')).to_be_visible();
        
        // Should complete unsubscription
        await expect(page.locator('[data-testid="unsubscription-complete"]')).to_be_visible({ timeout: 30000 });
        
        // Should offer download of exported data
        await expect(page.locator('[data-testid="download-export"]')).to_be_visible();
        
        // CRM should no longer appear in subscribed apps
        await helper.navigate_to_feature('/apps/subscribed');
        await expect(page.locator('[data-testid="subscribed-app-crm"]')).not_to_be_visible();
        
        // Should appear in marketplace again
        await helper.navigate_to_feature('/apps/marketplace');
        await expect(page.locator('[data-testid="app-card-crm"]')).to_be_visible();
      });
    });

    test('should handle grace period before data deletion', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await fixtures.create_feature_flag(tenant.tenant_id, 'field_ops_access', { enabled: true });
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Unsubscribe from field-ops
        await helper.navigate_to_feature('/apps/subscribed');
        const fieldOpsCard = page.locator('[data-testid="subscribed-app-field-ops"]');
        await fieldOpsCard.locator('[data-testid="manage-subscription"]').click();
        await page.click('[data-testid="unsubscribe-app"]');
        await page.click('[data-testid="confirm-unsubscribe"]');
        
        // Should show grace period information
        const gracePeriodInfo = page.locator('[data-testid="grace-period-info"]');
        await expect(gracePeriodInfo).to_be_visible();
        await expect(gracePeriodInfo).to_contain_text('30-day grace period');
        await expect(gracePeriodInfo).to_contain_text('reactivate subscription');
        
        // Should appear in recently unsubscribed section
        await helper.navigate_to_feature('/apps/recently-unsubscribed');
        const recentlyUnsubscribed = page.locator('[data-testid="recently-unsubscribed-field-ops"]');
        await expect(recentlyUnsubscribed).to_be_visible();
        
        // Should show days remaining
        await expect(recentlyUnsubscribed).to_contain_text('29 days remaining');
        
        // Should allow reactivation
        await expect(recentlyUnsubscribed.locator('[data-testid="reactivate-subscription"]')).to_be_visible();
      });
    });

    test('should reactivate subscription during grace period', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('premium');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        // Simulate app in grace period (recently unsubscribed)
        await fixtures.create_feature_flag(tenant.tenant_id, 'crm_grace_period', { 
          enabled: true,
          config: { grace_period_days: 30, days_remaining: 25 }
        });
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        await helper.navigate_to_feature('/apps/recently-unsubscribed');
        
        const gracePeriodApp = page.locator('[data-testid="recently-unsubscribed-crm"]');
        await expect(gracePeriodApp).to_be_visible();
        
        // Reactivate subscription
        await gracePeriodApp.locator('[data-testid="reactivate-subscription"]').click();
        
        // Should show reactivation confirmation
        const reactivationDialog = page.locator('[data-testid="reactivation-dialog"]');
        await expect(reactivationDialog).to_be_visible();
        await expect(reactivationDialog).to_contain_text('restore your CRM data');
        
        await page.click('[data-testid="confirm-reactivation"]');
        
        // Should show restoration progress
        await expect(page.locator('[data-testid="data-restoration-progress"]')).to_be_visible();
        
        // Should complete reactivation
        await expect(page.locator('[data-testid="reactivation-complete"]')).to_be_visible({ timeout: 20000 });
        
        // Should appear back in subscribed apps
        await helper.navigate_to_feature('/apps/subscribed');
        await expect(page.locator('[data-testid="subscribed-app-crm"]')).to_be_visible();
        
        // Data should be restored
        await page.click('[data-testid="launch-crm"]');
        await expect(page.locator('[data-testid="restored-data-notice"]')).to_be_visible();
      });
    });
  });

  test.describe('Subscription Billing and Usage Tracking', () => {
    
    test('should track app usage and generate billing data', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await fixtures.create_feature_flag(tenant.tenant_id, 'crm_access', { enabled: true });
        await fixtures.create_feature_flag(tenant.tenant_id, 'field_ops_access', { enabled: true });
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Navigate to billing dashboard
        await helper.navigate_to_feature('/billing/app-subscriptions');
        
        // Should show subscribed apps with usage
        const billingTable = page.locator('[data-testid="app-billing-table"]');
        await expect(billingTable).to_be_visible();
        
        // CRM subscription
        const crmBilling = billingTable.locator('[data-testid="billing-row-crm"]');
        await expect(crmBilling).to_be_visible();
        await expect(crmBilling).to_contain_text('Customer Relationship Management');
        await expect(crmBilling).to_contain_text('$100/month'); // Enterprise pricing
        await expect(crmBilling).to_contain_text('Active');
        
        // Field Ops subscription  
        const fieldOpsBilling = billingTable.locator('[data-testid="billing-row-field-ops"]');
        await expect(fieldOpsBilling).to_be_visible();
        await expect(fieldOpsBilling).to_contain_text('$60/month'); // Enterprise pricing
        
        // Should show total monthly cost
        const totalCost = page.locator('[data-testid="total-monthly-cost"]');
        await expect(totalCost).to_be_visible();
        await expect(totalCost).to_contain_text('$160'); // $100 + $60
        
        // Should show usage metrics
        await crmBilling.locator('[data-testid="view-usage"]').click();
        
        const usageDialog = page.locator('[data-testid="usage-details-dialog"]');
        await expect(usageDialog).to_be_visible();
        await expect(usageDialog).to_contain_text('Active Users');
        await expect(usageDialog).to_contain_text('API Calls');
        await expect(usageDialog).to_contain_text('Storage Used');
      });
    });

    test('should handle prorated billing for partial months', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('premium');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Subscribe to app mid-month (simulate)
        await helper.navigate_to_feature('/apps/marketplace');
        await page.click('[data-testid="app-card-crm"] [data-testid="subscribe-button"]');
        
        // Should show prorated pricing
        const confirmDialog = page.locator('[data-testid="subscription-confirm-dialog"]');
        await expect(confirmDialog).to_contain_text('Prorated for remaining 15 days');
        await expect(confirmDialog).to_contain_text('$25.00'); // Half of $50 for premium
        
        await page.click('[data-testid="confirm-subscription"]');
        
        // Check billing shows prorated amount
        await helper.navigate_to_feature('/billing/current-invoice');
        
        const currentInvoice = page.locator('[data-testid="current-invoice"]');
        await expect(currentInvoice).to_contain_text('CRM Subscription (Prorated)');
        await expect(currentInvoice).to_contain_text('$25.00');
      });
    });

    test('should generate usage reports for multiple apps', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        // Subscribe to multiple apps
        await fixtures.create_feature_flag(tenant.tenant_id, 'crm_access', { enabled: true });
        await fixtures.create_feature_flag(tenant.tenant_id, 'field_ops_access', { enabled: true });
        await fixtures.create_feature_flag(tenant.tenant_id, 'inventory_access', { enabled: true });
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Generate usage report
        await helper.navigate_to_feature('/billing/usage-reports');
        
        await page.selectOption('[data-testid="report-period"]', 'last_30_days');
        await page.click('[data-testid="generate-report"]');
        
        // Should show report generation progress
        await expect(page.locator('[data-testid="report-generating"]')).to_be_visible();
        
        // Should complete and show report
        await expect(page.locator('[data-testid="usage-report"]')).to_be_visible({ timeout: 15000 });
        
        const report = page.locator('[data-testid="usage-report"]');
        
        // Should show usage for each app
        await expect(report).to_contain_text('CRM');
        await expect(report).to_contain_text('Field Operations');  
        await expect(report).to_contain_text('Inventory Management');
        
        // Should show usage metrics
        await expect(report).to_contain_text('Total Users');
        await expect(report).to_contain_text('API Requests');
        await expect(report).to_contain_text('Data Storage');
        
        // Should allow export
        await expect(page.locator('[data-testid="export-report"]')).to_be_visible();
        
        // Export to CSV
        await page.click('[data-testid="export-report"]');
        await page.selectOption('[data-testid="export-format"]', 'csv');
        await page.click('[data-testid="download-export"]');
        
        // Should trigger download
        const downloadPromise = page.waitForEvent('download');
        const download = await downloadPromise;
        expect(download.suggestedFilename()).toContain('usage-report');
        expect(download.suggestedFilename()).toContain('.csv');
      });
    });

    test('should handle billing failures and notifications', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('premium');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await fixtures.create_feature_flag(tenant.tenant_id, 'crm_access', { enabled: true });
        
        // Simulate billing failure
        await fixtures.create_feature_flag(tenant.tenant_id, 'billing_failure', {
          enabled: true,
          config: { failed_apps: ['crm'], reason: 'payment_failed' }
        });
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Should show billing alert on dashboard
        await helper.navigate_to_feature('/dashboard');
        
        const billingAlert = page.locator('[data-testid="billing-alert"]');
        await expect(billingAlert).to_be_visible();
        await expect(billingAlert).to_contain_text('Payment failed');
        await expect(billingAlert).to_contain_text('CRM subscription');
        
        // Navigate to billing to resolve
        await billingAlert.locator('[data-testid="resolve-billing"]').click();
        
        // Should show billing resolution page
        await expect(page.locator('[data-testid="billing-resolution"]')).to_be_visible();
        await expect(page.locator('[data-testid="failed-payment-crm"]')).to_be_visible();
        
        // Should show retry payment option
        await expect(page.locator('[data-testid="retry-payment"]')).to_be_visible();
        
        // Should show grace period information
        await expect(page.locator('[data-testid="grace-period-warning"]')).to_be_visible();
        await expect(page.locator('[data-testid="grace-period-warning"]')).to_contain_text('7 days remaining');
      });
    });
  });
});