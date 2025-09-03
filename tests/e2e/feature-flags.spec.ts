/**
 * Feature Flag Enforcement E2E Tests
 * 
 * Tests license-based feature access and multi-app coordination
 * 
 * Test Scenarios:
 * - Tenant with Basic plan cannot access Premium features
 * - License upgrade immediately enables new features
 * - Feature flag propagation across all apps in tenant container
 * - Grace period handling during subscription changes
 * - Feature access logging and audit trails
 */

import { test, expect, Page, BrowserContext } from '@playwright/test';
import { LicenseTestHelper, MultiAppTestHelper } from '../../src/dotmac_shared/tests/e2e/licensing/helpers';
import { LicenseAssertions } from '../../src/dotmac_shared/tests/e2e/licensing/assertions';
import { license_fixtures } from '../../src/dotmac_shared/tests/e2e/licensing/fixtures';

// Test configuration
const TENANT_APPS = [
  { name: 'admin', url: 'http://localhost:3000', port: 3000 },
  { name: 'customer', url: 'http://localhost:3001', port: 3001 },
  { name: 'reseller', url: 'http://localhost:3003', port: 3003 }
];

const FEATURE_MATRIX = {
  basic: {
    available: ['basic_analytics', 'standard_api', 'email_support'],
    unavailable: ['advanced_analytics', 'premium_api', 'sso', 'white_label', 'priority_support']
  },
  premium: {
    available: ['basic_analytics', 'advanced_analytics', 'premium_api', 'custom_branding', 'phone_support'],
    unavailable: ['sso', 'white_label', 'enterprise_integration', 'priority_support']
  },
  enterprise: {
    available: ['basic_analytics', 'advanced_analytics', 'enterprise_api', 'sso', 'white_label', 
               'enterprise_integration', 'priority_support', 'advanced_security'],
    unavailable: []
  }
};

test.describe('Feature Flag Enforcement', () => {
  let helper: LicenseTestHelper;
  let multiAppHelper: MultiAppTestHelper;
  
  test.beforeEach(async ({ page, context }) => {
    helper = new LicenseTestHelper(page);
    multiAppHelper = new MultiAppTestHelper(context);
    await multiAppHelper.setup_app_pages(['admin', 'customer', 'reseller']);
  });

  test.afterEach(async () => {
    await multiAppHelper.cleanup();
  });

  test.describe('Basic Plan Feature Restrictions', () => {
    
    test('should deny access to premium features for basic plan tenant', async ({ page }) => {
      await test.step('Setup basic plan tenant', async () => {
        await license_fixtures(async (fixtures) => {
          const [tenant, license] = await fixtures.create_tenant_with_license('basic');
          await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
          
          // Login as admin user
          await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
          
          // Test access to basic features (should work)
          for (const feature of FEATURE_MATRIX.basic.available) {
            await test.step(`Verify access to basic feature: ${feature}`, async () => {
              await helper.check_feature_access(`[data-feature="${feature}"]`, true);
            });
          }
          
          // Test access to premium features (should be denied)
          for (const feature of FEATURE_MATRIX.basic.unavailable) {
            await test.step(`Verify denial of premium feature: ${feature}`, async () => {
              await LicenseAssertions.assert_feature_access_denied(page, `[data-feature="${feature}"]`);
            });
          }
        });
      });
    });

    test('should show upgrade prompts for restricted features', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('basic');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Try to access advanced analytics
        await helper.navigate_to_feature('/analytics/advanced');
        
        // Should see upgrade prompt
        const upgradePrompt = page.locator('[data-testid="upgrade-prompt"]');
        await expect(upgradePrompt).to_be_visible();
        await expect(upgradePrompt).to_contain_text('Premium');
        
        // Should have upgrade button
        const upgradeButton = page.locator('[data-testid="upgrade-button"]');
        await expect(upgradeButton).to_be_visible();
      });
    });

    test('should enforce API rate limits for basic plan', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('basic');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Trigger API rate limit by making many requests
        await helper.trigger_license_limit_scenario('api_calls');
        
        // Should see rate limit error
        await LicenseAssertions.assert_license_limit_error(page, 'api_calls', 1000);
      });
    });

    test('should enforce customer limit for basic plan', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('basic');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        // Simulate tenant near customer limit
        await fixtures.simulate_usage_near_limit(tenant.tenant_id, 'customers', 95);
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Try to create another customer (should hit limit)
        await helper.trigger_license_limit_scenario('customers');
        
        // Should see customer limit error
        await LicenseAssertions.assert_license_limit_error(page, 'customers', 100);
      });
    });
  });

  test.describe('License Upgrade Scenarios', () => {
    
    test('should immediately enable premium features after upgrade', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('basic');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Verify premium feature is initially disabled
        await LicenseAssertions.assert_feature_flag_state(page, 'advanced_analytics', false);
        
        // Upgrade license to premium
        await fixtures.upgrade_license_plan(license.contract_id, 'premium');
        
        // Features should be immediately available
        await helper.check_feature_flag_propagation('advanced_analytics', true);
        await helper.check_feature_access('[data-feature="advanced_analytics"]', true);
        
        // Verify subscription change is reflected in UI
        await helper.verify_subscription_changes_reflected('basic', 'premium');
      });
    });

    test('should handle enterprise upgrade with all features enabled', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('premium');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Upgrade to enterprise
        await fixtures.upgrade_license_plan(license.contract_id, 'enterprise');
        
        // All enterprise features should be available
        for (const feature of FEATURE_MATRIX.enterprise.available) {
          await test.step(`Verify enterprise feature enabled: ${feature}`, async () => {
            await helper.check_feature_flag_propagation(feature, true);
          });
        }
        
        // Verify enterprise-specific features work
        await helper.navigate_to_feature('/security/sso');
        await helper.check_feature_access('[data-testid="sso-configuration"]', true);
        
        await helper.navigate_to_feature('/settings/white-label');
        await helper.check_feature_access('[data-testid="white-label-settings"]', true);
      });
    });
  });

  test.describe('Cross-App Feature Propagation', () => {
    
    test('should propagate feature flags across all tenant apps', async ({ context }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('premium');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        // Login to all apps
        await multiAppHelper.login_to_all_apps(tenant.tenant_id, {
          email: 'admin@test.com',
          password: 'password123'
        });
        
        // Create custom feature flag
        await fixtures.create_feature_flag(tenant.tenant_id, 'custom_reporting', {
          enabled: true,
          rollout_percentage: 100.0
        });
        
        // Wait for propagation
        await fixtures.wait_for_feature_propagation(tenant.tenant_id, 'custom_reporting');
        
        // Verify feature is available in all apps
        const results = await multiAppHelper.verify_feature_across_apps('custom_reporting', {
          admin: true,
          customer: true,
          reseller: true
        });
        
        // All apps should have the feature enabled
        for (const [app, result] of Object.entries(results)) {
          expect(result.success).toBe(true);
          expect(result.state).toBe(true);
        }
      });
    });

    test('should handle partial rollout across apps', async ({ context }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const adminUser = await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        // Create feature flag with 50% rollout
        await fixtures.create_feature_flag(tenant.tenant_id, 'beta_feature', {
          enabled: true,
          rollout_percentage: 50.0,
          target_user_ids: [adminUser.user_id]  // Ensure admin is included
        });
        
        await multiAppHelper.login_to_all_apps(tenant.tenant_id, {
          email: 'admin@test.com',
          password: 'password123'
        });
        
        // Admin user should have access due to targeting
        const results = await multiAppHelper.verify_feature_across_apps('beta_feature', {
          admin: true,
          customer: true,
          reseller: true
        });
        
        // Feature should be consistently available for targeted user
        Object.values(results).forEach(result => {
          expect(result.success).toBe(true);
        });
      });
    });

    test('should disable features across all apps when license expires', async ({ context }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('premium');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await multiAppHelper.login_to_all_apps(tenant.tenant_id, {
          email: 'admin@test.com',
          password: 'password123'
        });
        
        // Initially premium features should be available
        let results = await multiAppHelper.verify_feature_across_apps('premium_api', {
          admin: true,
          customer: true,
          reseller: true
        });
        
        Object.values(results).forEach(result => {
          expect(result.success).toBe(true);
        });
        
        // Expire the license
        await fixtures.expire_license(license.contract_id);
        
        // Features should be disabled across all apps
        await fixtures.wait_for_feature_propagation(tenant.tenant_id, 'premium_api');
        
        results = await multiAppHelper.verify_feature_across_apps('premium_api', {
          admin: false,
          customer: false, 
          reseller: false
        });
        
        Object.values(results).forEach(result => {
          expect(result.success).toBe(true);
        });
      });
    });
  });

  test.describe('Grace Period Handling', () => {
    
    test('should maintain access during grace period after downgrade', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Initially should have enterprise features
        await helper.check_feature_access('[data-feature="sso"]', true);
        
        // Downgrade to premium (with grace period)
        await fixtures.upgrade_license_plan(license.contract_id, 'premium');
        
        // During grace period, enterprise features should still work
        await helper.check_grace_period_handling(5); // 5 minute grace period
        
        // SSO should still be accessible during grace period
        await helper.check_feature_access('[data-feature="sso"]', true);
        
        // Should show grace period notice
        await LicenseAssertions.assert_grace_period_active(page, 5);
      });
    });

    test('should disable features after grace period expires', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Simulate grace period expiration by directly updating license
        // In real scenario, this would be handled by background jobs
        await page.evaluate(`
          // Simulate grace period expiration
          localStorage.setItem('grace_period_expired', 'true');
          window.dispatchEvent(new Event('license_updated'));
        `);
        
        // Wait for feature state to update
        await page.waitForTimeout(2000);
        
        // Enterprise features should now be disabled
        await LicenseAssertions.assert_feature_access_denied(page, '[data-feature="sso"]');
        await LicenseAssertions.assert_feature_access_denied(page, '[data-feature="white_label"]');
        
        // Premium features should still work
        await helper.check_feature_access('[data-feature="premium_api"]', true);
      });
    });
  });

  test.describe('Feature Access Logging and Audit', () => {
    
    test('should log feature access attempts', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('basic');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Attempt to access premium feature (should be denied and logged)
        await helper.navigate_to_feature('/analytics/advanced');
        
        // Should see access denied
        await LicenseAssertions.assert_feature_access_denied(page, '[data-testid="advanced-analytics"]');
        
        // Should create audit log entry
        await LicenseAssertions.assert_audit_log_entry(
          page, 
          'feature_access_denied', 
          tenant.tenant_id,
          2 // Within 2 minutes
        );
      });
    });

    test('should log license limit violations', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('basic');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        // Simulate approaching customer limit
        await fixtures.simulate_usage_near_limit(tenant.tenant_id, 'customers', 95);
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Attempt to exceed customer limit
        await helper.trigger_license_limit_scenario('customers');
        
        // Should log limit violation
        await LicenseAssertions.assert_audit_log_entry(
          page,
          'license_limit_exceeded',
          tenant.tenant_id,
          2
        );
      });
    });

    test('should track usage metrics accurately', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('premium');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        // Create some usage data
        await fixtures.simulate_usage_near_limit(tenant.tenant_id, 'customers', 60); // 60% of limit
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Navigate to usage dashboard
        await helper.navigate_to_feature(`/admin/tenants/${tenant.tenant_id}/usage`);
        
        // Verify usage tracking is working
        await LicenseAssertions.assert_license_usage_tracking(
          page, 
          tenant.tenant_id, 
          'customers',
          Math.floor(1000 * 0.6) // 60% of 1000 customer limit
        );
      });
    });
  });

  test.describe('Real-time Feature Updates', () => {
    
    test('should reflect feature changes in real-time', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('premium');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Create a feature flag that's initially disabled
        await fixtures.create_feature_flag(tenant.tenant_id, 'realtime_feature', {
          enabled: false
        });
        
        // Verify it's disabled
        await LicenseAssertions.assert_feature_flag_state(page, 'realtime_feature', false);
        
        // Enable the feature flag externally (simulating admin change)
        await page.evaluate(`
          // Simulate external feature flag update
          setTimeout(() => {
            window.dispatchEvent(new CustomEvent('feature_updated', {
              detail: { feature_name: 'realtime_feature', enabled: true }
            }));
          }, 1000);
        `);
        
        // Should update in real-time
        await LicenseAssertions.assert_real_time_updates(page, 'realtime_feature', false, 10);
      });
    });

    test('should handle feature flag rollout changes', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const user = await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        // Create feature with 0% rollout
        await fixtures.create_feature_flag(tenant.tenant_id, 'gradual_rollout', {
          enabled: true,
          rollout_percentage: 0.0
        });
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Should not have access initially
        await LicenseAssertions.assert_feature_flag_state(page, 'gradual_rollout', false);
        
        // Increase rollout to include this user
        await page.evaluate(`
          // Simulate rollout percentage increase
          setTimeout(() => {
            window.dispatchEvent(new CustomEvent('rollout_updated', {
              detail: { 
                feature_name: 'gradual_rollout', 
                rollout_percentage: 100.0,
                target_users: ['${user.user_id}']
              }
            }));
          }, 2000);
        `);
        
        // Should now have access
        await LicenseAssertions.assert_real_time_updates(page, 'gradual_rollout', false, 15);
      });
    });
  });

  test.describe('Performance and Scalability', () => {
    
    test('should maintain fast feature check performance', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Test performance of feature flag checks
        const features = FEATURE_MATRIX.enterprise.available;
        
        for (const feature of features.slice(0, 5)) { // Test first 5 features
          await test.step(`Performance test for feature: ${feature}`, async () => {
            await LicenseAssertions.assert_feature_check_performance(page, feature, 100); // < 100ms
          });
        }
      });
    });

    test('should handle concurrent feature flag updates', async ({ context }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('premium');
        await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        // Create multiple browser contexts to simulate concurrent users
        const contexts = await Promise.all([
          context.browser()?.newContext(),
          context.browser()?.newContext(),
          context.browser()?.newContext()
        ]);
        
        const pages = await Promise.all(
          contexts.map(ctx => ctx?.newPage()).filter(Boolean)
        );
        
        // Login with all contexts
        await Promise.all(
          pages.map(async (page) => {
            const pageHelper = new LicenseTestHelper(page!);
            await pageHelper.login_as_admin(tenant.tenant_id, 'admin@test.com');
          })
        );
        
        // Create feature flag
        await fixtures.create_feature_flag(tenant.tenant_id, 'concurrent_feature', {
          enabled: true
        });
        
        // All pages should see the feature consistently
        await Promise.all(
          pages.map(async (page) => {
            await LicenseAssertions.assert_feature_flag_state(page!, 'concurrent_feature', true);
          })
        );
        
        // Cleanup
        await Promise.all(contexts.map(ctx => ctx?.close()));
      });
    });
  });
});