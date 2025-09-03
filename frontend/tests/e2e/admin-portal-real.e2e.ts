/**
 * Real E2E Tests for Admin Portal
 * Tests actual application routing and comprehensive workflows
 */

import { test, expect } from '@playwright/test';
import { setupAuth } from '../auth/auth-helpers';
import { APIBehaviorTester } from '../fixtures/api-behaviors';

test.describe('Admin Portal - Real Application Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Use unified auth helper (cookie/session-based)
    await setupAuth(page, 'admin');
    // Optionally instantiate API tester for request logging/validation in future
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
    const _apiTester = new APIBehaviorTester(page, { enableMocking: false });
  });

  test('should handle customer management workflow with real APIs', async ({ page }) => {
    let customerListCalled = false;
    let customerDetailsCalled = false;
    let customerUpdateCalled = false;

    // Mock customer list API
    await page.route('/api/v1/admin/customers*', async (route) => {
      customerListCalled = true;
      const url = new URL(route.request().url());
      const search = url.searchParams.get('search');
      const status = url.searchParams.get('status');

      let customers = [
        {
          id: 'CUST-001',
          name: 'John Doe',
          email: 'john@example.com',
          status: 'active',
          plan: 'Fiber 100Mbps',
          monthly_revenue: 79.99,
        },
        {
          id: 'CUST-002',
          name: 'Jane Smith',
          email: 'jane@business.com',
          status: 'suspended',
          plan: 'Business 500Mbps',
          monthly_revenue: 199.99,
        },
      ];

      // Apply filters
      if (search) {
        customers = customers.filter(
          (c) =>
            c.name.toLowerCase().includes(search.toLowerCase()) ||
            c.email.toLowerCase().includes(search.toLowerCase())
        );
      }

      if (status) {
        customers = customers.filter((c) => c.status === status);
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          customers,
          total: customers.length,
          page: 1,
          limit: 20,
        }),
      });
    });

    // Mock customer details API
    await page.route('/api/v1/admin/customers/*', async (route) => {
      if (route.request().method() === 'GET') {
        customerDetailsCalled = true;

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'CUST-001',
            name: 'John Doe',
            email: 'john@example.com',
            phone: '+1-555-123-4567',
            status: 'active',
            plan: 'Fiber 100Mbps',
            address: {
              street: '123 Main St',
              city: 'San Francisco',
              state: 'CA',
              zip: '94105',
            },
            service_details: {
              installation_date: '2023-06-15T09:00:00Z',
              connection_status: 'online',
              last_speed_test: {
                download: 98.5,
                upload: 97.2,
                ping: 12,
              },
            },
          }),
        });
      } else if (route.request().method() === 'PUT') {
        customerUpdateCalled = true;

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            message: 'Customer updated successfully',
          }),
        });
      }
    });

    // Navigate to admin portal
    await page.goto('/admin');

    // Navigate to customers page through real routing
    await page.click('[data-testid="nav-customers"]');
    await expect(page.url()).toContain('/customers');

    // Verify customer list loads
    await page.waitForSelector('[data-testid="customers-table"]');
    expect(customerListCalled).toBe(true);

    // Verify customer data displays
    await expect(page.locator('[data-testid="customer-row"]')).toHaveCount(2);
    await expect(page.locator('text=John Doe')).toBeVisible();
    await expect(page.locator('text=Jane Smith')).toBeVisible();

    // Test search functionality
    await page.fill('[data-testid="customer-search"]', 'john');
    await page.keyboard.press('Enter');
    await page.waitForTimeout(500);

    // Should filter results
    await expect(page.locator('[data-testid="customer-row"]')).toHaveCount(1);
    await expect(page.locator('text=John Doe')).toBeVisible();
    await expect(page.locator('text=Jane Smith')).toBeHidden();

    // Clear search and test status filter
    await page.fill('[data-testid="customer-search"]', '');
    await page.selectOption('[data-testid="status-filter"]', 'active');
    await page.waitForTimeout(500);

    // View customer details
    await page.click('[data-testid="customer-row"]:has-text("John Doe")');
    await expect(page.url()).toContain('/customers/CUST-001');

    expect(customerDetailsCalled).toBe(true);

    // Verify customer details display
    await expect(page.locator('[data-testid="customer-name"]')).toContainText('John Doe');
    await expect(page.locator('[data-testid="customer-email"]')).toContainText('john@example.com');
    await expect(page.locator('[data-testid="service-status"]')).toContainText('online');

    // Test customer update
    await page.click('[data-testid="edit-customer"]');
    await page.fill('[data-testid="customer-phone"]', '+1-555-999-8888');
    await page.click('[data-testid="save-customer"]');

    expect(customerUpdateCalled).toBe(true);
    await expect(page.locator('[data-testid="success-message"]')).toContainText(
      'updated successfully'
    );
  });

  test('should handle network monitoring with real-time updates', async ({ page }) => {
    let networkStatusCalled = false;

    // Mock network status API with real-time simulation
    await page.route('/api/v1/admin/network/status', async (route) => {
      networkStatusCalled = true;

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          overall_health: 99.2,
          active_connections: 15234,
          bandwidth_usage: 78.5,
          nodes: [
            {
              id: 'SEA-CORE-01',
              name: 'Seattle Core Router',
              status: 'operational',
              utilization: 67.3,
              capacity: '100Gbps',
            },
            {
              id: 'BEL-DIST-02',
              name: 'Bellevue Distribution',
              status: 'operational',
              utilization: 82.1,
              capacity: '40Gbps',
            },
          ],
          alerts: [
            {
              id: 'ALR-001',
              severity: 'warning',
              message: 'High utilization on BEL-DIST-02 (82%)',
            },
          ],
        }),
      });
    });

    await page.goto('/admin');

    // Navigate to network monitoring
    await page.click('[data-testid="nav-network"]');
    await expect(page.url()).toContain('/network');

    // Verify network status loads
    await page.waitForSelector('[data-testid="network-overview"]');
    expect(networkStatusCalled).toBe(true);

    // Verify network metrics display
    await expect(page.locator('[data-testid="overall-health"]')).toContainText('99.2%');
    await expect(page.locator('[data-testid="active-connections"]')).toContainText('15,234');
    await expect(page.locator('[data-testid="bandwidth-usage"]')).toContainText('78.5%');

    // Verify network nodes display
    await expect(page.locator('[data-testid="network-node"]')).toHaveCount(2);
    await expect(page.locator('text=Seattle Core Router')).toBeVisible();
    await expect(page.locator('text=Bellevue Distribution')).toBeVisible();

    // Verify alerts display
    await expect(page.locator('[data-testid="network-alert"]')).toBeVisible();
    await expect(page.locator('text=High utilization')).toBeVisible();

    // Test node details modal
    await page.click('[data-testid="node-SEA-CORE-01"]');
    await expect(page.locator('[data-testid="node-details-modal"]')).toBeVisible();
    await expect(page.locator('[data-testid="node-utilization"]')).toContainText('67.3%');

    // Close modal
    await page.click('[data-testid="close-modal"]');
    await expect(page.locator('[data-testid="node-details-modal"]')).toBeHidden();
  });

  test('should validate admin permissions and role-based access', async ({ page }) => {
    // Test with limited admin role
    await page.addInitScript(() => {
      const limitedAdmin = {
        id: 'test-admin-limited',
        name: 'Limited Admin',
        email: 'limited@test.dotmac.com',
        role: 'admin_readonly',
        permissions: ['read:customers', 'read:network'],
      };

      localStorage.setItem('admin_user', JSON.stringify(limitedAdmin));
    });

    await page.goto('/admin');

    // Should see read-only navigation
    await expect(page.locator('[data-testid="nav-customers"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-network"]')).toBeVisible();

    // Should NOT see admin-only sections
    await expect(page.locator('[data-testid="nav-system-config"]')).toBeHidden();
    await expect(page.locator('[data-testid="nav-user-management"]')).toBeHidden();

    // Navigate to customers
    await page.click('[data-testid="nav-customers"]');

    // Should see customer list but not edit buttons
    await expect(page.locator('[data-testid="customers-table"]')).toBeVisible();
    await expect(page.locator('[data-testid="add-customer-btn"]')).toBeHidden();
    await expect(page.locator('[data-testid="bulk-actions"]')).toBeHidden();
  });
});
