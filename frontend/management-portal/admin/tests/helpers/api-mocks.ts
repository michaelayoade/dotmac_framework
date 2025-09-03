import { type Page } from '@playwright/test';
import {
  testTenants,
  testMetrics,
  testSystemAlerts,
  testUserActivities,
  apiResponses,
} from '../fixtures/test-data';

/**
 * API mocking helpers for E2E tests
 */

export async function mockDashboardAPI(page: Page): Promise<void> {
  // Mock dashboard stats
  await page.route('**/api/v1/dashboard/stats', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify(apiResponses.dashboardStats),
    });
  });

  // Mock system status
  await page.route('**/api/v1/system/status', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify(apiResponses.systemStatus),
    });
  });

  // Mock recent activity
  await page.route('**/api/v1/activity/recent', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        activities: testUserActivities.slice(0, 10),
        total: testUserActivities.length,
      }),
    });
  });
}

export async function mockTenantsAPI(page: Page): Promise<void> {
  // Mock tenant list
  await page.route('**/api/v1/tenants', (route) => {
    if (route.request().method() === 'GET') {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          tenants: testTenants,
          total: testTenants.length,
          page: 1,
          limit: 10,
        }),
      });
    } else if (route.request().method() === 'POST') {
      // Mock tenant creation
      const requestBody = route.request().postDataJSON();
      const newTenant = {
        id: 'tenant-new-' + Date.now(),
        ...requestBody,
        status: 'active',
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      route.fulfill({
        status: 201,
        body: JSON.stringify(newTenant),
      });
    }
  });

  // Mock individual tenant operations
  await page.route('**/api/v1/tenants/*', (route) => {
    const tenantId = route.request().url().split('/').pop();
    const tenant = testTenants.find((t) => t.id === tenantId);

    if (route.request().method() === 'GET') {
      route.fulfill({
        status: tenant ? 200 : 404,
        body: JSON.stringify(tenant || { error: 'Tenant not found' }),
      });
    } else if (route.request().method() === 'PATCH') {
      const updates = route.request().postDataJSON();
      const updatedTenant = { ...tenant, ...updates, updatedAt: new Date().toISOString() };

      route.fulfill({
        status: 200,
        body: JSON.stringify(updatedTenant),
      });
    } else if (route.request().method() === 'DELETE') {
      route.fulfill({
        status: 204,
        body: '',
      });
    }
  });
}

export async function mockRealtimeAPI(page: Page): Promise<void> {
  // Mock WebSocket token endpoint
  await page.route('**/api/auth/ws-token', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        token: 'mock-ws-token-' + Date.now(),
      }),
    });
  });

  // Mock real-time metrics
  await page.route('**/api/v1/metrics/realtime', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        metrics: testMetrics,
      }),
    });
  });

  // Mock system alerts
  await page.route('**/api/v1/system/alerts', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        alerts: testSystemAlerts,
      }),
    });
  });
}

export async function mockMFAAPI(page: Page): Promise<void> {
  // Mock MFA configuration
  await page.route('**/api/v1/mfa/config', (route) => {
    route.fulfill({
      status: 404,
      body: JSON.stringify({ message: 'MFA not configured' }),
    });
  });

  // Mock TOTP setup initialization
  await page.route('**/api/v1/mfa/setup/totp', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        secret: 'JBSWY3DPEHPK3PXP',
        qrCodeUrl:
          'otpauth://totp/DotMac%20Management:admin@dotmac.com?secret=JBSWY3DPEHPK3PXP&issuer=DotMac%20Management',
        manualEntryCode: 'JBSWY3DPEHPK3PXP',
        backupCodes: [],
      }),
    });
  });

  // Mock TOTP verification
  await page.route('**/api/v1/mfa/setup/totp/verify', (route) => {
    const body = route.request().postDataJSON();
    const isValidCode = body.code === '123456'; // Accept 123456 as valid test code

    if (isValidCode) {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          success: true,
          backupCodes: [
            'BACKUP01',
            'BACKUP02',
            'BACKUP03',
            'BACKUP04',
            'BACKUP05',
            'BACKUP06',
            'BACKUP07',
            'BACKUP08',
          ],
        }),
      });
    } else {
      route.fulfill({
        status: 400,
        body: JSON.stringify({
          error: 'Invalid verification code',
        }),
      });
    }
  });
}

export async function mockAuditAPI(page: Page): Promise<void> {
  // Mock audit logs
  await page.route('**/api/v1/audit/logs', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        logs: [],
        total: 0,
        page: 1,
        limit: 50,
      }),
    });
  });

  // Mock audit event creation
  await page.route('**/api/v1/audit/events', (route) => {
    if (route.request().method() === 'POST') {
      route.fulfill({
        status: 201,
        body: JSON.stringify({
          id: 'audit-' + Date.now(),
          ...route.request().postDataJSON(),
          timestamp: new Date().toISOString(),
        }),
      });
    }
  });
}

export async function mockUsersAPI(page: Page): Promise<void> {
  // Mock users list
  await page.route('**/api/v1/users', (route) => {
    route.fulfill({
      status: 200,
      body: JSON.stringify({
        users: [
          {
            id: 'user-1',
            email: 'admin@dotmac.com',
            firstName: 'Admin',
            lastName: 'User',
            role: 'admin',
            status: 'active',
            createdAt: '2024-01-01T00:00:00Z',
          },
        ],
        total: 1,
        page: 1,
        limit: 10,
      }),
    });
  });
}

export async function mockAllAPIs(page: Page): Promise<void> {
  await mockDashboardAPI(page);
  await mockTenantsAPI(page);
  await mockRealtimeAPI(page);
  await mockMFAAPI(page);
  await mockAuditAPI(page);
  await mockUsersAPI(page);
}

export async function mockAPIError(
  page: Page,
  endpoint: string,
  status = 500,
  message = 'Internal Server Error'
): Promise<void> {
  await page.route(endpoint, (route) => {
    route.fulfill({
      status,
      body: JSON.stringify({ error: message }),
    });
  });
}

export async function mockAPIDelay(page: Page, endpoint: string, delay: number): Promise<void> {
  await page.route(endpoint, async (route) => {
    await new Promise((resolve) => setTimeout(resolve, delay));
    route.continue();
  });
}

export async function mockPagination(
  page: Page,
  endpoint: string,
  data: any[],
  pageSize = 10
): Promise<void> {
  await page.route(endpoint, (route) => {
    const url = new URL(route.request().url());
    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || pageSize.toString());

    const startIndex = (page - 1) * limit;
    const endIndex = startIndex + limit;
    const paginatedData = data.slice(startIndex, endIndex);

    route.fulfill({
      status: 200,
      body: JSON.stringify({
        data: paginatedData,
        total: data.length,
        page,
        limit,
        totalPages: Math.ceil(data.length / limit),
      }),
    });
  });
}
