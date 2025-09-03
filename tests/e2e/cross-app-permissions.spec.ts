/**
 * Cross-App Permissions E2E Tests
 * 
 * Tests user permissions and access control across multiple apps within a tenant
 * 
 * Test Scenarios:
 * - User has ISP access but not CRM → correct restrictions
 * - Tenant admin grants CRM access → user can access CRM
 * - Role changes propagate across subscribed apps
 * - Single sign-on across multiple apps in tenant
 * - Permission inheritance and conflicts resolution
 */

import { test, expect, Page, BrowserContext } from '@playwright/test';
import { LicenseTestHelper, MultiAppTestHelper } from '../../src/dotmac_shared/tests/e2e/licensing/helpers';
import { LicenseAssertions } from '../../src/dotmac_shared/tests/e2e/licensing/assertions';
import { license_fixtures } from '../../src/dotmac_shared/tests/e2e/licensing/fixtures';

// App definitions with permissions
const APP_PERMISSIONS = {
  'isp-admin': {
    url: 'http://localhost:3000',
    required_permissions: ['isp_access', 'network_management'],
    admin_permissions: ['user_management', 'billing_access']
  },
  'customer-portal': {
    url: 'http://localhost:3001', 
    required_permissions: ['customer_access'],
    admin_permissions: ['customer_support']
  },
  'crm': {
    url: 'http://localhost:3004',
    required_permissions: ['crm_access', 'lead_management'],
    admin_permissions: ['crm_admin', 'sales_reports']
  },
  'reseller': {
    url: 'http://localhost:3003',
    required_permissions: ['reseller_access', 'partner_management'],
    admin_permissions: ['commission_management']
  },
  'field-ops': {
    url: 'http://localhost:3002',
    required_permissions: ['field_access', 'technician_tools'],
    admin_permissions: ['dispatch_management']
  }
};

// User role definitions
const USER_ROLES = {
  'isp_user': {
    permissions: ['isp_access', 'customer_access', 'network_read'],
    apps: ['isp-admin', 'customer-portal']
  },
  'isp_admin': {
    permissions: ['isp_access', 'user_management', 'billing_access', 'network_management'],
    apps: ['isp-admin', 'customer-portal']
  },
  'crm_user': {
    permissions: ['crm_access', 'lead_management', 'customer_access'],
    apps: ['crm', 'customer-portal']
  },
  'sales_manager': {
    permissions: ['crm_access', 'lead_management', 'sales_reports', 'reseller_access'],
    apps: ['crm', 'reseller']
  },
  'super_admin': {
    permissions: ['*'], // All permissions
    apps: ['*'] // All apps
  },
  'field_technician': {
    permissions: ['field_access', 'technician_tools', 'customer_access'],
    apps: ['field-ops', 'customer-portal']
  }
};

test.describe('Cross-App Permissions', () => {
  let helper: LicenseTestHelper;
  let multiAppHelper: MultiAppTestHelper;
  
  test.beforeEach(async ({ page, context }) => {
    helper = new LicenseTestHelper(page);
    multiAppHelper = new MultiAppTestHelper(context);
  });

  test.afterEach(async () => {
    await multiAppHelper.cleanup();
  });

  test.describe('Restricted Access Scenarios', () => {
    
    test('should restrict ISP user from accessing CRM when not subscribed', async ({ context }) => {
      await license_fixtures(async (fixtures) => {
        // Create enterprise tenant with ISP but no CRM subscription
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const ispUser = await fixtures.create_user_for_tenant(tenant.tenant_id, 'user');
        
        // Set user role to ISP user (no CRM access)
        ispUser.role = 'isp_user';
        ispUser.permissions = USER_ROLES.isp_user.permissions;
        
        await multiAppHelper.setup_app_pages(['isp-admin', 'crm']);
        await multiAppHelper.login_to_all_apps(tenant.tenant_id, {
          email: 'user@test.com',
          password: 'password123'
        });
        
        // Should have access to ISP admin
        const ispPage = multiAppHelper.app_pages['isp-admin'];
        await ispPage.goto('/dashboard');
        await expect(ispPage.locator('[data-testid="dashboard"]')).to_be_visible();
        
        // Should NOT have access to CRM
        const crmPage = multiAppHelper.app_pages['crm'];
        await crmPage.goto('/dashboard');
        
        // Should see access denied or be redirected
        const accessDeniedSelectors = [
          '[data-testid="access-denied"]',
          '[data-testid="unauthorized"]',
          '[data-testid="subscription-required"]'
        ];
        
        let accessDenied = false;
        for (const selector of accessDeniedSelectors) {
          if (await crmPage.locator(selector).isVisible()) {
            accessDenied = true;
            break;
          }
        }
        
        expect(accessDenied).toBe(true);
      });
    });

    test('should show app subscription prompts for unavailable apps', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('premium');
        const user = await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Navigate to app directory/launcher
        await helper.navigate_to_feature('/apps');
        
        // CRM should show as available for subscription
        const crmTile = page.locator('[data-testid="app-crm"]');
        await expect(crmTile).to_be_visible();
        
        const subscribeButton = crmTile.locator('[data-testid="subscribe-button"]');
        await expect(subscribeButton).to_be_visible();
        await expect(subscribeButton).to_contain_text('Subscribe');
        
        // Field Ops should also show subscription option
        const fieldOpsTile = page.locator('[data-testid="app-field-ops"]');
        await expect(fieldOpsTile).to_be_visible();
        await expect(fieldOpsTile.locator('[data-testid="subscribe-button"]')).to_be_visible();
      });
    });

    test('should enforce feature-level permissions within apps', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const limitedUser = await fixtures.create_user_for_tenant(tenant.tenant_id, 'user');
        
        // User has ISP access but limited permissions
        limitedUser.permissions = ['isp_access', 'customer_read'];
        
        await helper.login_as_admin(tenant.tenant_id, 'user@test.com');
        
        // Should access ISP admin dashboard
        await helper.navigate_to_feature('/dashboard');
        await expect(page.locator('[data-testid="dashboard"]')).to_be_visible();
        
        // Should see customer data (read permission)
        await helper.navigate_to_feature('/customers');
        await expect(page.locator('[data-testid="customers-table"]')).to_be_visible();
        
        // Should NOT see add customer button (no write permission)
        const addCustomerBtn = page.locator('[data-testid="add-customer-button"]');
        await expect(addCustomerBtn).not_to_be_visible();
        
        // Should NOT access billing (no billing permission)
        await helper.navigate_to_feature('/billing');
        await LicenseAssertions.assert_feature_access_denied(page, '[data-testid="billing-dashboard"]');
      });
    });
  });

  test.describe('Permission Grant Scenarios', () => {
    
    test('should enable CRM access when admin grants permission', async ({ context }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const admin = await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        const user = await fixtures.create_user_for_tenant(tenant.tenant_id, 'user');
        
        // Initially user only has ISP access
        user.permissions = USER_ROLES.isp_user.permissions;
        
        await multiAppHelper.setup_app_pages(['isp-admin', 'crm']);
        
        // Admin grants CRM subscription to tenant
        const adminHelper = new LicenseTestHelper(multiAppHelper.app_pages['isp-admin']);
        await adminHelper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Subscribe to CRM app
        await adminHelper.navigate_to_feature('/apps/manage');
        await multiAppHelper.app_pages['isp-admin'].click('[data-testid="subscribe-crm"]');
        
        // Grant CRM access to user
        await adminHelper.navigate_to_feature(`/users/${user.user_id}/permissions`);
        await multiAppHelper.app_pages['isp-admin'].check('[data-testid="permission-crm_access"]');
        await multiAppHelper.app_pages['isp-admin'].click('[data-testid="save-permissions"]');
        
        // Wait for permission propagation
        await fixtures.wait_for_feature_propagation(tenant.tenant_id, 'crm_access');
        
        // Now user should be able to access CRM
        const userHelper = new LicenseTestHelper(multiAppHelper.app_pages['crm']);
        await userHelper.login_as_admin(tenant.tenant_id, 'user@test.com');
        
        await multiAppHelper.app_pages['crm'].goto('/dashboard');
        await expect(multiAppHelper.app_pages['crm'].locator('[data-testid="crm-dashboard"]')).to_be_visible();
      });
    });

    test('should handle bulk permission assignments', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const admin = await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        // Create multiple users
        const users = await Promise.all([
          fixtures.create_user_for_tenant(tenant.tenant_id, 'user'),
          fixtures.create_user_for_tenant(tenant.tenant_id, 'user'),
          fixtures.create_user_for_tenant(tenant.tenant_id, 'user')
        ]);
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Navigate to bulk permissions page
        await helper.navigate_to_feature('/admin/permissions/bulk');
        
        // Select all users
        for (const user of users) {
          await page.check(`[data-testid="user-checkbox-${user.user_id}"]`);
        }
        
        // Grant CRM access to all selected users
        await page.selectOption('[data-testid="permission-selector"]', 'crm_access');
        await page.click('[data-testid="grant-permission"]');
        
        // Confirm bulk operation
        await page.click('[data-testid="confirm-bulk-grant"]');
        
        // Should see success message
        await expect(page.locator('[data-testid="bulk-success-message"]')).to_be_visible();
        await expect(page.locator('[data-testid="bulk-success-message"]')).to_contain_text('3 users');
      });
    });
  });

  test.describe('Role Change Propagation', () => {
    
    test('should propagate role changes across all subscribed apps', async ({ context }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const user = await fixtures.create_user_for_tenant(tenant.tenant_id, 'user');
        
        // Subscribe to multiple apps
        await fixtures.create_feature_flag(tenant.tenant_id, 'crm_access', { enabled: true });
        await fixtures.create_feature_flag(tenant.tenant_id, 'reseller_access', { enabled: true });
        
        // Initially user has limited access
        user.role = 'isp_user';
        user.permissions = USER_ROLES.isp_user.permissions;
        
        await multiAppHelper.setup_app_pages(['isp-admin', 'crm', 'reseller']);
        await multiAppHelper.login_to_all_apps(tenant.tenant_id, {
          email: 'user@test.com',
          password: 'password123'
        });
        
        // Verify initial limited access
        await multiAppHelper.app_pages['isp-admin'].goto('/dashboard');
        await expect(multiAppHelper.app_pages['isp-admin'].locator('[data-testid="dashboard"]')).to_be_visible();
        
        // CRM should be restricted
        await multiAppHelper.app_pages['crm'].goto('/dashboard');
        await LicenseAssertions.assert_feature_access_denied(
          multiAppHelper.app_pages['crm'], 
          '[data-testid="crm-dashboard"]'
        );
        
        // Admin promotes user to sales manager role
        const adminPage = await context.newPage();
        const adminHelper = new LicenseTestHelper(adminPage);
        await adminHelper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        await adminHelper.navigate_to_feature(`/users/${user.user_id}/profile`);
        await adminPage.selectOption('[data-testid="user-role"]', 'sales_manager');
        await adminPage.click('[data-testid="save-user-changes"]');
        
        // Wait for role change propagation
        await adminPage.waitForTimeout(3000);
        
        // Now user should have access to CRM and Reseller apps
        await multiAppHelper.app_pages['crm'].reload();
        await expect(multiAppHelper.app_pages['crm'].locator('[data-testid="crm-dashboard"]')).to_be_visible();
        
        await multiAppHelper.app_pages['reseller'].goto('/dashboard');
        await expect(multiAppHelper.app_pages['reseller'].locator('[data-testid="reseller-dashboard"]')).to_be_visible();
        
        await adminPage.close();
      });
    });

    test('should handle role conflicts and resolution', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const user = await fixtures.create_user_for_tenant(tenant.tenant_id, 'user');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Assign conflicting roles/permissions to user
        await helper.navigate_to_feature(`/users/${user.user_id}/permissions`);
        
        // Grant both read and deny permissions for same feature
        await page.check('[data-testid="permission-billing_read"]');
        await page.check('[data-testid="permission-billing_deny"]');  // Conflict
        
        await page.click('[data-testid="save-permissions"]');
        
        // Should see conflict resolution dialog
        const conflictDialog = page.locator('[data-testid="permission-conflict-dialog"]');
        await expect(conflictDialog).to_be_visible();
        
        // Should suggest resolution (deny typically takes precedence)
        await expect(conflictDialog).to_contain_text('billing_deny will override billing_read');
        
        // Accept suggested resolution
        await page.click('[data-testid="accept-resolution"]');
        
        // Verify final permissions are correct
        await expect(page.locator('[data-testid="permission-billing_read"]')).not_to_be_checked();
        await expect(page.locator('[data-testid="permission-billing_deny"]')).to_be_checked();
      });
    });

    test('should maintain permission consistency during role transitions', async ({ context }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const user = await fixtures.create_user_for_tenant(tenant.tenant_id, 'user');
        
        await multiAppHelper.setup_app_pages(['isp-admin', 'crm']);
        
        // User starts as ISP admin
        user.role = 'isp_admin';
        user.permissions = USER_ROLES.isp_admin.permissions;
        
        await multiAppHelper.login_to_all_apps(tenant.tenant_id, {
          email: 'user@test.com', 
          password: 'password123'
        });
        
        // Should have ISP admin access
        await multiAppHelper.app_pages['isp-admin'].goto('/admin/users');
        await expect(multiAppHelper.app_pages['isp-admin'].locator('[data-testid="user-management"]')).to_be_visible();
        
        // Transition to sales manager role
        const adminPage = await context.newPage();
        const adminHelper = new LicenseTestHelper(adminPage);
        await adminHelper.login_as_admin(tenant.tenant_id, 'superadmin@test.com');
        
        await adminHelper.navigate_to_feature(`/users/${user.user_id}/profile`);
        await adminPage.selectOption('[data-testid="user-role"]', 'sales_manager');
        await adminPage.click('[data-testid="save-user-changes"]');
        
        // During transition, user should maintain existing sessions
        // but new permissions should apply to new actions
        await multiAppHelper.app_pages['isp-admin'].reload();
        
        // Should lose ISP admin privileges but keep basic ISP access
        await multiAppHelper.app_pages['isp-admin'].goto('/admin/users');
        await LicenseAssertions.assert_feature_access_denied(
          multiAppHelper.app_pages['isp-admin'],
          '[data-testid="user-management"]'
        );
        
        // Should gain CRM access
        await multiAppHelper.app_pages['crm'].goto('/dashboard');
        await expect(multiAppHelper.app_pages['crm'].locator('[data-testid="crm-dashboard"]')).to_be_visible();
        
        await adminPage.close();
      });
    });
  });

  test.describe('Single Sign-On (SSO)', () => {
    
    test('should enable SSO across all tenant apps', async ({ context }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const user = await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        // Enable SSO feature
        await fixtures.create_feature_flag(tenant.tenant_id, 'sso', { enabled: true });
        
        // Subscribe to multiple apps
        await fixtures.create_feature_flag(tenant.tenant_id, 'crm_access', { enabled: true });
        await fixtures.create_feature_flag(tenant.tenant_id, 'reseller_access', { enabled: true });
        
        await multiAppHelper.setup_app_pages(['isp-admin', 'crm', 'reseller']);
        
        // Login to first app (ISP Admin)
        const ispHelper = new LicenseTestHelper(multiAppHelper.app_pages['isp-admin']);
        await ispHelper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Should be automatically logged in to other apps
        await multiAppHelper.app_pages['crm'].goto('/dashboard');
        await expect(multiAppHelper.app_pages['crm'].locator('[data-testid="crm-dashboard"]')).to_be_visible();
        
        await multiAppHelper.app_pages['reseller'].goto('/dashboard');
        await expect(multiAppHelper.app_pages['reseller'].locator('[data-testid="reseller-dashboard"]')).to_be_visible();
        
        // Logout from one app should log out from all
        await multiAppHelper.app_pages['isp-admin'].click('[data-testid="logout-button"]');
        
        // Other apps should also be logged out
        await multiAppHelper.app_pages['crm'].reload();
        await expect(multiAppHelper.app_pages['crm'].locator('[data-testid="login-form"]')).to_be_visible();
        
        await multiAppHelper.app_pages['reseller'].reload();
        await expect(multiAppHelper.app_pages['reseller'].locator('[data-testid="login-form"]')).to_be_visible();
      });
    });

    test('should handle SSO token refresh across apps', async ({ context }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const user = await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await fixtures.create_feature_flag(tenant.tenant_id, 'sso', { enabled: true });
        await fixtures.create_feature_flag(tenant.tenant_id, 'crm_access', { enabled: true });
        
        await multiAppHelper.setup_app_pages(['isp-admin', 'crm']);
        await multiAppHelper.login_to_all_apps(tenant.tenant_id, {
          email: 'admin@test.com',
          password: 'password123'
        });
        
        // Simulate token expiry by advancing browser time
        await multiAppHelper.app_pages['isp-admin'].evaluate(() => {
          // Mock token expiry
          localStorage.setItem('token_expires_at', String(Date.now() - 1000));
        });
        
        // Make API call that would trigger token refresh
        await multiAppHelper.app_pages['isp-admin'].goto('/api/v1/user/profile');
        
        // Should still be logged in due to token refresh
        await multiAppHelper.app_pages['isp-admin'].goto('/dashboard');
        await expect(multiAppHelper.app_pages['isp-admin'].locator('[data-testid="dashboard"]')).to_be_visible();
        
        // Other apps should also have refreshed tokens
        await multiAppHelper.app_pages['crm'].goto('/dashboard');
        await expect(multiAppHelper.app_pages['crm'].locator('[data-testid="crm-dashboard"]')).to_be_visible();
      });
    });

    test('should enforce SSO security policies', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const user = await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await fixtures.create_feature_flag(tenant.tenant_id, 'sso', { 
          enabled: true,
          config: {
            session_timeout_minutes: 30,
            require_mfa: true,
            allowed_domains: ['test.com']
          }
        });
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Should enforce MFA during SSO login
        const mfaPrompt = page.locator('[data-testid="mfa-challenge"]');
        if (await mfaPrompt.isVisible()) {
          await page.fill('[data-testid="mfa-code"]', '123456');
          await page.click('[data-testid="verify-mfa"]');
        }
        
        // Should be logged in successfully
        await expect(page.locator('[data-testid="dashboard"]')).to_be_visible();
        
        // Should enforce session timeout
        await page.evaluate(() => {
          // Simulate session timeout
          localStorage.setItem('session_started_at', String(Date.now() - (31 * 60 * 1000))); // 31 minutes ago
        });
        
        await page.reload();
        
        // Should be redirected to login due to timeout
        await expect(page.locator('[data-testid="login-form"]')).to_be_visible();
      });
    });
  });

  test.describe('Permission Inheritance and Conflicts', () => {
    
    test('should inherit permissions from parent roles', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const user = await fixtures.create_user_for_tenant(tenant.tenant_id, 'user');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // Set up role hierarchy: Manager > Supervisor > User
        await helper.navigate_to_feature('/admin/roles');
        
        // Create supervisor role that inherits from user
        await page.click('[data-testid="create-role"]');
        await page.fill('[data-testid="role-name"]', 'supervisor');
        await page.selectOption('[data-testid="parent-role"]', 'user');
        await page.check('[data-testid="permission-team_management"]');
        await page.click('[data-testid="save-role"]');
        
        // Create manager role that inherits from supervisor
        await page.click('[data-testid="create-role"]');
        await page.fill('[data-testid="role-name"]', 'manager');
        await page.selectOption('[data-testid="parent-role"]', 'supervisor');
        await page.check('[data-testid="permission-budget_approval"]');
        await page.click('[data-testid="save-role"]');
        
        // Assign manager role to user
        await helper.navigate_to_feature(`/users/${user.user_id}/profile`);
        await page.selectOption('[data-testid="user-role"]', 'manager');
        await page.click('[data-testid="save-user-changes"]');
        
        // User should have all inherited permissions
        await helper.navigate_to_feature(`/users/${user.user_id}/permissions`);
        
        // Should have user base permissions
        await expect(page.locator('[data-testid="permission-basic_access"]')).to_be_checked();
        
        // Should have supervisor permissions
        await expect(page.locator('[data-testid="permission-team_management"]')).to_be_checked();
        
        // Should have manager permissions
        await expect(page.locator('[data-testid="permission-budget_approval"]')).to_be_checked();
      });
    });

    test('should resolve permission conflicts with explicit rules', async ({ page }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const user = await fixtures.create_user_for_tenant(tenant.tenant_id, 'user');
        
        await helper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        
        // User has multiple role assignments with conflicts
        await helper.navigate_to_feature(`/users/${user.user_id}/roles`);
        
        // Add user to multiple roles with conflicting permissions
        await page.check('[data-testid="role-financial_viewer"]');  // Can view billing
        await page.check('[data-testid="role-billing_restricted"]'); // Cannot view billing
        await page.click('[data-testid="save-role-assignments"]');
        
        // Should show conflict resolution interface
        const conflictResolver = page.locator('[data-testid="conflict-resolver"]');
        await expect(conflictResolver).to_be_visible();
        
        // Should show specific conflicts
        await expect(conflictResolver).to_contain_text('billing_view');
        await expect(conflictResolver).to_contain_text('conflict detected');
        
        // Set explicit resolution rule
        await page.selectOption('[data-testid="conflict-resolution-billing_view"]', 'deny');
        await page.click('[data-testid="apply-resolution"]');
        
        // Verify final permission state
        await helper.navigate_to_feature(`/users/${user.user_id}/effective-permissions`);
        
        const billingPermission = page.locator('[data-testid="effective-permission-billing_view"]');
        await expect(billingPermission).to_contain_text('Denied');
        await expect(billingPermission).to_contain_text('Explicit rule');
      });
    });

    test('should handle dynamic permission inheritance', async ({ context }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const user = await fixtures.create_user_for_tenant(tenant.tenant_id, 'user');
        const manager = await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        // Set up team hierarchy
        user.manager_id = manager.user_id;
        user.department = 'sales';
        
        await multiAppHelper.setup_app_pages(['isp-admin', 'crm']);
        
        // Manager grants temporary project access
        const managerHelper = new LicenseTestHelper(multiAppHelper.app_pages['isp-admin']);
        await managerHelper.login_as_admin(tenant.tenant_id, 'manager@test.com');
        
        await managerHelper.navigate_to_feature('/projects/special-project/team');
        await multiAppHelper.app_pages['isp-admin'].click(`[data-testid="add-team-member-${user.user_id}"]`);
        await multiAppHelper.app_pages['isp-admin'].selectOption('[data-testid="project-role"]', 'project_contributor');
        await multiAppHelper.app_pages['isp-admin'].click('[data-testid="grant-access"]');
        
        // User should now have temporary project permissions
        const userHelper = new LicenseTestHelper(multiAppHelper.app_pages['crm']);
        await userHelper.login_as_admin(tenant.tenant_id, 'user@test.com');
        
        await multiAppHelper.app_pages['crm'].goto('/projects/special-project');
        await expect(multiAppHelper.app_pages['crm'].locator('[data-testid="project-dashboard"]')).to_be_visible();
        
        // Should have project-specific permissions
        await expect(multiAppHelper.app_pages['crm'].locator('[data-testid="project-contribute-button"]')).to_be_visible();
        
        // But not administrative permissions
        await expect(multiAppHelper.app_pages['crm'].locator('[data-testid="project-admin-button"]')).not_to_be_visible();
      });
    });
  });

  test.describe('Cross-App Data Consistency', () => {
    
    test('should maintain user profile consistency across apps', async ({ context }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const user = await fixtures.create_user_for_tenant(tenant.tenant_id, 'user');
        
        await fixtures.create_feature_flag(tenant.tenant_id, 'crm_access', { enabled: true });
        
        await multiAppHelper.setup_app_pages(['isp-admin', 'crm']);
        await multiAppHelper.login_to_all_apps(tenant.tenant_id, {
          email: 'user@test.com',
          password: 'password123'
        });
        
        // Update profile in ISP Admin
        await multiAppHelper.app_pages['isp-admin'].goto('/profile');
        await multiAppHelper.app_pages['isp-admin'].fill('[data-testid="display-name"]', 'Updated User Name');
        await multiAppHelper.app_pages['isp-admin'].click('[data-testid="save-profile"]');
        
        // Should see success message
        await expect(multiAppHelper.app_pages['isp-admin'].locator('[data-testid="profile-updated"]')).to_be_visible();
        
        // Profile should be updated in CRM app
        await multiAppHelper.app_pages['crm'].goto('/profile');
        await expect(multiAppHelper.app_pages['crm'].locator('[data-testid="display-name"]')).to_have_value('Updated User Name');
        
        // User name should appear consistently in app headers
        await multiAppHelper.app_pages['crm'].goto('/dashboard');
        await expect(multiAppHelper.app_pages['crm'].locator('[data-testid="user-name-display"]')).to_contain_text('Updated User Name');
      });
    });

    test('should sync permission changes in real-time across apps', async ({ context }) => {
      await license_fixtures(async (fixtures) => {
        const [tenant, license] = await fixtures.create_tenant_with_license('enterprise');
        const user = await fixtures.create_user_for_tenant(tenant.tenant_id, 'user');
        const admin = await fixtures.create_user_for_tenant(tenant.tenant_id, 'admin');
        
        await fixtures.create_feature_flag(tenant.tenant_id, 'crm_access', { enabled: true });
        
        await multiAppHelper.setup_app_pages(['isp-admin', 'crm']);
        
        // User logs in to both apps
        await multiAppHelper.login_to_all_apps(tenant.tenant_id, {
          email: 'user@test.com',
          password: 'password123'
        });
        
        // Initially user doesn't have CRM admin access
        await multiAppHelper.app_pages['crm'].goto('/admin');
        await LicenseAssertions.assert_feature_access_denied(
          multiAppHelper.app_pages['crm'],
          '[data-testid="crm-admin-panel"]'
        );
        
        // Admin grants CRM admin permission in another browser
        const adminContext = await context.browser()?.newContext();
        const adminPage = await adminContext?.newPage();
        const adminHelper = new LicenseTestHelper(adminPage!);
        
        await adminHelper.login_as_admin(tenant.tenant_id, 'admin@test.com');
        await adminHelper.navigate_to_feature(`/users/${user.user_id}/permissions`);
        await adminPage!.check('[data-testid="permission-crm_admin"]');
        await adminPage!.click('[data-testid="save-permissions"]');
        
        // User should see permission change in real-time
        await multiAppHelper.app_pages['crm'].waitForTimeout(2000); // Brief wait for propagation
        await multiAppHelper.app_pages['crm'].reload();
        
        await multiAppHelper.app_pages['crm'].goto('/admin');
        await expect(multiAppHelper.app_pages['crm'].locator('[data-testid="crm-admin-panel"]')).to_be_visible();
        
        await adminContext?.close();
      });
    });
  });
});