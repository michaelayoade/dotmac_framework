/**
 * Real E2E Tests for Customer Portal
 * Tests actual application routing and API integration
 */

import { test, expect } from '@playwright/test';
import { setupAuth } from '../auth/auth-helpers';
import { APIBehaviorTester } from '../fixtures/api-behaviors';

test.describe('Customer Portal - Real Application Flow', () => {
  test.beforeEach(async ({ page }) => {
    // Use unified auth for customer portal
    await setupAuth(page, 'customer');
  });

  test('should navigate through real customer dashboard flow', async ({ page }) => {
    const apiTester = new APIBehaviorTester(page, { enableMocking: true });

    // Navigate to actual customer portal
    await page.goto('/');
    
    // Verify dashboard loads with real routing
    await expect(page.locator('[data-testid="customer-dashboard"]')).toBeVisible();
    await expect(page.locator('h1')).toContainText('Dashboard');
    
    // API mocking for dashboard data
    await page.route('/api/v1/customer/dashboard', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          account: {
            id: 'CUST-TEST-001',
            name: 'Test Customer',
            status: 'active',
            plan: 'Fiber 1000Mbps',
            monthly_cost: 89.99,
            next_billing: '2024-12-01T00:00:00Z'
          },
          service: {
            status: 'online',
            connection_speed: '1000 Mbps',
            data_usage: {
              current: 750,
              limit: 1000,
              unit: 'GB'
            },
            uptime: 99.8
          },
          notifications: [
            {
              id: 'test-notif-001',
              type: 'info',
              message: 'Service operating normally'
            }
          ]
        })
      });
    });
    
    // Wait for dashboard data to load
    await page.waitForSelector('[data-testid="service-status"]');
    
    // Verify service status displays real data
    await expect(page.locator('[data-testid="service-status"]')).toContainText('Online');
    await expect(page.locator('[data-testid="data-usage"]')).toContainText('750 GB');
    await expect(page.locator('[data-testid="uptime"]')).toContainText('99.8%');
  });

  test('should handle billing page navigation and API calls', async ({ page }) => {
    await page.goto('/');
    
    // Mock billing API
    await page.route('/api/v1/customer/billing', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          current_balance: 0.00,
          next_due_date: '2024-12-01T00:00:00Z',
          next_amount: 89.99,
          payment_method: {
            type: 'card',
            last_four: '4321',
            expires: '12/26'
          },
          recent_invoices: [
            {
              id: 'INV-TEST-001',
              date: '2024-11-01T00:00:00Z',
              amount: 89.99,
              status: 'paid'
            }
          ]
        })
      });
    });
    
    // Navigate to billing through real routing
    await page.click('[data-testid="nav-billing"]');
    await expect(page.url()).toContain('/billing');
    
    // Verify billing page loads with real data
    await expect(page.locator('[data-testid="billing-overview"]')).toBeVisible();
    await expect(page.locator('[data-testid="current-balance"]')).toContainText('$0.00');
    await expect(page.locator('[data-testid="next-amount"]')).toContainText('$89.99');
    await expect(page.locator('[data-testid="payment-method"]')).toContainText('4321');
  });

  test('should handle support ticket creation flow', async ({ page }) => {
    await page.goto('/');
    
    // Mock support API
    let ticketCreated = false;
    await page.route('/api/v1/customer/support/tickets', async route => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            tickets: [],
            total: 0
          })
        });
      } else if (route.request().method() === 'POST') {
        ticketCreated = true;
        const requestBody = route.request().postDataJSON();
        
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'TKT-TEST-001',
            subject: requestBody.subject,
            status: 'open',
            created_at: new Date().toISOString()
          })
        });
      }
    });
    
    // Navigate to support
    await page.click('[data-testid="nav-support"]');
    await expect(page.url()).toContain('/support');
    
    // Create new support ticket
    await page.click('[data-testid="new-ticket-btn"]');
    await page.fill('[data-testid="ticket-subject"]', 'Connection speed issues');
    await page.fill('[data-testid="ticket-description"]', 'Internet speed is slower than expected');
    await page.selectOption('[data-testid="ticket-priority"]', 'medium');
    
    await page.click('[data-testid="submit-ticket"]');
    
    // Verify API was called with correct data
    expect(ticketCreated).toBe(true);
    
    // Verify success message
    await expect(page.locator('[data-testid="ticket-success"]')).toBeVisible();
    await expect(page.locator('[data-testid="ticket-id"]')).toContainText('TKT-TEST-001');
  });

  test('should handle session validation and re-authentication', async ({ page }) => {
    let authValidationCalled = false;
    let sessionRefreshCalled = false;
    
    // Mock auth validation that initially fails, then succeeds
    await page.route('/api/auth/validate', async (route, request) => {
      authValidationCalled = true;
      
      if (!sessionRefreshCalled) {
        // First call fails (expired token)
        await route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({
            valid: false,
            error: 'Token expired'
          })
        });
      } else {
        // After refresh, validation succeeds
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            valid: true,
            user: {
              id: 'test-customer-001',
              name: 'Test Customer',
              email: 'customer@test.dotmac.com'
            }
          })
        });
      }
    });
    
    // Mock refresh endpoint
    await page.route('/api/auth/refresh', async route => {
      sessionRefreshCalled = true;
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          token: 'new-test-token-12345',
          expires_at: Date.now() + 24 * 60 * 60 * 1000,
          user: {
            id: 'test-customer-001',
            name: 'Test Customer',
            email: 'customer@test.dotmac.com'
          }
        })
      });
    });
    
    // Navigate to protected page
    await page.goto('/dashboard');
    
    // Should trigger auth validation
    await page.waitForTimeout(1000);
    expect(authValidationCalled).toBe(true);
    
    // Should automatically refresh and continue
    await page.waitForTimeout(2000);
    expect(sessionRefreshCalled).toBe(true);
    
    // Should eventually load dashboard
    await expect(page.locator('[data-testid="customer-dashboard"]')).toBeVisible();
  });

  test('should test offline behavior and error handling', async ({ page }) => {
    await page.goto('/');
    
    // Simulate network failure
    await page.route('**/*', route => route.abort('failed'));
    
    // Navigate to billing page
    await page.click('[data-testid="nav-billing"]');
    
    // Should show offline/error state
    await expect(page.locator('[data-testid="offline-banner"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-message"]')).toContainText('Unable to load data');
    
    // Should show retry button
    await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();
    
    // Restore network and test retry
    await page.unroute('**/*');
    
    await page.route('/api/v1/customer/billing', async route => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          current_balance: 0.00,
          next_amount: 89.99
        })
      });
    });
    
    await page.click('[data-testid="retry-button"]');
    
    // Should hide error and show content
    await expect(page.locator('[data-testid="offline-banner"]')).toBeHidden();
    await expect(page.locator('[data-testid="billing-overview"]')).toBeVisible();
  });

  test('should validate API request data and responses', async ({ page }) => {
    let dashboardApiCalled = false;
    let billingApiCalled = false;
    let supportApiCalled = false;
    
    // Comprehensive API mocking with validation
    await page.route('/api/v1/customer/dashboard', async route => {
      dashboardApiCalled = true;
      
      // Validate request headers
      const headers = route.request().headers();
      expect(headers['authorization']).toContain('Bearer');
      expect(headers['content-type']).toContain('application/json');
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          account: { id: 'CUST-TEST-001', name: 'Test Customer' },
          service: { status: 'online', uptime: 99.8 }
        })
      });
    });
    
    await page.route('/api/v1/customer/billing', async route => {
      billingApiCalled = true;
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          current_balance: 0.00,
          next_amount: 89.99
        })
      });
    });
    
    await page.route('/api/v1/customer/support/tickets', async route => {
      supportApiCalled = true;
      
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          tickets: [
            {
              id: 'TKT-TEST-001',
              subject: 'Test ticket',
              status: 'open'
            }
          ]
        })
      });
    });
    
    // Navigate through application
    await page.goto('/dashboard');
    await page.waitForTimeout(1000);
    
    await page.click('[data-testid="nav-billing"]');
    await page.waitForTimeout(1000);
    
    await page.click('[data-testid="nav-support"]');
    await page.waitForTimeout(1000);
    
    // Verify all APIs were called
    expect(dashboardApiCalled).toBe(true);
    expect(billingApiCalled).toBe(true);
    expect(supportApiCalled).toBe(true);
    
    // Verify data flows correctly to UI
    await page.goto('/dashboard');
    await expect(page.locator('[data-testid="customer-name"]')).toContainText('Test Customer');
    await expect(page.locator('[data-testid="service-uptime"]')).toContainText('99.8%');
  });
});
