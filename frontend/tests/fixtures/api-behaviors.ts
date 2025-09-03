/**
 * Comprehensive API Behavior Testing for E2E Tests
 * Tests data flows, error handling, and business logic
 */

import { Page, Route } from '@playwright/test';

export interface APIBehaviorConfig {
  enableMocking: boolean;
  simulateLatency: boolean;
  simulateErrors: boolean;
  validateRequests: boolean;
}

export class APIBehaviorTester {
  private page: Page;
  private config: APIBehaviorConfig;
  private requestLog: Array<{
    url: string;
    method: string;
    headers: Record<string, string>;
    body: any;
    timestamp: number;
  }> = [];

  constructor(page: Page, config: Partial<APIBehaviorConfig> = {}) {
    this.page = page;
    this.config = {
      enableMocking: true,
      simulateLatency: false,
      simulateErrors: false,
      validateRequests: true,
      ...config,
    };
  }

  /**
   * Generic mock + log helper for arbitrary endpoints.
   * If responder is provided, it controls the fulfillment.
   * Otherwise, a 200 JSON {} is returned.
   */
  async mockAndLog(
    pattern: string | RegExp,
    responder?: (req: {
      url: string;
      method: string;
      body: any;
      headers: Record<string, string>;
    }) => Promise<
      | { status?: number; body?: any; headers?: Record<string, string> }
      | { status?: number; body?: any; headers?: Record<string, string> }
      | void
    >
  ) {
    await this.page.route(pattern as any, async (route) => {
      await this.logRequest(route);
      await this.simulateLatency();

      if (responder) {
        const req = route.request();
        const payload = {
          url: req.url(),
          method: req.method(),
          body: (() => {
            try {
              return req.postDataJSON();
            } catch {
              return req.postData();
            }
          })(),
          headers: req.headers(),
        };
        const res = await responder(payload);
        if (res) {
          return route.fulfill({
            status: res.status ?? 200,
            contentType: 'application/json',
            headers: res.headers,
            body: JSON.stringify(res.body ?? {}),
          });
        }
      }

      return route.fulfill({ status: 200, contentType: 'application/json', body: '{}' });
    });
  }

  /**
   * Minimal technician portal mocks for common endpoints
   */
  async setupTechnicianMocks() {
    if (!this.config.enableMocking) return;
    await this.mockAndLog(/\/api\/v1\/technician\/work-orders.*/, async () => ({
      body: { workOrders: [], total: 0 },
    }));
    await this.mockAndLog('/api/v1/technician/location', async () => ({ body: { ok: true } }));
    await this.mockAndLog('/api/v1/technician/uploads', async () => ({ body: { uploaded: true } }));
  }

  /**
   * Minimal reseller portal mocks for common endpoints
   */
  async setupResellerMocks() {
    if (!this.config.enableMocking) return;
    await this.mockAndLog(/\/api\/v1\/reseller\/territory.*/, async () => ({
      body: { regions: [] },
    }));
    await this.mockAndLog(/\/api\/v1\/reseller\/customers.*/, async () => ({
      body: { customers: [], total: 0 },
    }));
    await this.mockAndLog(/\/api\/v1\/reseller\/commissions.*/, async () => ({
      body: { total: 0 },
    }));
    await this.mockAndLog(/\/api\/v1\/reseller\/leads.*/, async () => ({ body: { leads: [] } }));
    await this.mockAndLog(/\/api\/v1\/reseller\/quotes.*/, async () => ({
      body: { quoteId: 'Q-TEST' },
    }));
    await this.mockAndLog(/\/api\/v1\/reseller\/orders.*/, async () => ({
      body: { orderId: 'O-TEST' },
    }));
  }

  /**
   * Setup comprehensive API mocking for customer portal
   */
  async setupCustomerAPIMocks() {
    if (!this.config.enableMocking) return;

    // Dashboard API with business logic validation
    await this.page.route('/api/v1/customer/dashboard', async (route) => {
      await this.logRequest(route);
      await this.simulateLatency();

      if (this.config.simulateErrors && Math.random() < 0.1) {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Internal server error',
            code: 'DASHBOARD_ERROR',
          }),
        });
        return;
      }

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
            next_billing: '2024-12-01T00:00:00Z',
          },
          service: {
            status: 'online',
            connection_speed: '1000 Mbps',
            data_usage: {
              current: 750,
              limit: 1000,
              unit: 'GB',
              reset_date: '2024-12-01T00:00:00Z',
            },
            uptime: 99.8,
          },
          notifications: [
            {
              id: 'notif-001',
              type: 'info',
              message: 'Service operating normally',
              timestamp: new Date().toISOString(),
            },
          ],
        }),
      });
    });

    // Billing API with payment validation
    await this.page.route('/api/v1/customer/billing', async (route) => {
      await this.logRequest(route);
      await this.simulateLatency();

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          current_balance: 0.0,
          next_due_date: '2024-12-01T00:00:00Z',
          next_amount: 89.99,
          payment_method: {
            type: 'card',
            last_four: '4321',
            expires: '12/26',
          },
          recent_invoices: [
            {
              id: 'INV-TEST-001',
              date: '2024-11-01T00:00:00Z',
              amount: 89.99,
              status: 'paid',
              due_date: '2024-12-01T00:00:00Z',
            },
          ],
          payment_history: [
            {
              id: 'PAY-TEST-001',
              date: '2024-11-01T10:30:00Z',
              amount: 89.99,
              method: 'auto-pay',
              status: 'completed',
            },
          ],
        }),
      });
    });

    // Support tickets API with CRUD operations
    await this.page.route('/api/v1/customer/support/tickets*', async (route) => {
      await this.logRequest(route);
      await this.simulateLatency();

      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            tickets: [
              {
                id: 'TKT-TEST-001',
                subject: 'Speed optimization inquiry',
                status: 'resolved',
                priority: 'medium',
                created_at: '2024-01-10T14:30:00Z',
                updated_at: '2024-01-12T16:45:00Z',
              },
            ],
            total: 1,
          }),
        });
      } else if (route.request().method() === 'POST') {
        const requestBody = route.request().postDataJSON();

        // Validate required fields
        if (!requestBody.subject || !requestBody.description) {
          await route.fulfill({
            status: 400,
            contentType: 'application/json',
            body: JSON.stringify({
              error: 'Missing required fields',
              fields: ['subject', 'description'],
            }),
          });
          return;
        }

        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'TKT-TEST-NEW',
            subject: requestBody.subject,
            status: 'open',
            priority: requestBody.priority || 'medium',
            created_at: new Date().toISOString(),
          }),
        });
      }
    });
  }

  /**
   * Setup admin portal API mocks with business logic
   */
  async setupAdminAPIMocks() {
    if (!this.config.enableMocking) return;

    // Customer management with filtering and pagination
    await this.page.route('/api/v1/admin/customers*', async (route) => {
      await this.logRequest(route);
      await this.simulateLatency();

      const url = new URL(route.request().url());
      const page = parseInt(url.searchParams.get('page') || '1');
      const limit = parseInt(url.searchParams.get('limit') || '20');
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
          created_at: '2023-06-15T09:00:00Z',
        },
        {
          id: 'CUST-002',
          name: 'Jane Smith',
          email: 'jane@business.com',
          status: 'suspended',
          plan: 'Business 500Mbps',
          monthly_revenue: 199.99,
          created_at: '2023-08-20T11:15:00Z',
        },
        {
          id: 'CUST-003',
          name: 'Bob Johnson',
          email: 'bob@startup.com',
          status: 'active',
          plan: 'Fiber 500Mbps',
          monthly_revenue: 149.99,
          created_at: '2024-01-10T14:20:00Z',
        },
      ];

      // Apply business logic filters
      if (search) {
        const query = search.toLowerCase();
        customers = customers.filter(
          (c) =>
            c.name.toLowerCase().includes(query) ||
            c.email.toLowerCase().includes(query) ||
            c.id.toLowerCase().includes(query)
        );
      }

      if (status) {
        customers = customers.filter((c) => c.status === status);
      }

      // Apply pagination
      const start = (page - 1) * limit;
      const end = start + limit;
      const paginatedCustomers = customers.slice(start, end);

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          customers: paginatedCustomers,
          total: customers.length,
          page,
          limit,
          total_pages: Math.ceil(customers.length / limit),
        }),
      });
    });

    // Network status with real-time simulation
    await this.page.route('/api/v1/admin/network/status', async (route) => {
      await this.logRequest(route);
      await this.simulateLatency();

      // Simulate varying network conditions
      const baseUtilization = 70;
      const variance = Math.random() * 20 - 10; // ±10%
      const currentUtilization = Math.max(0, Math.min(100, baseUtilization + variance));

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          overall_health: 99.2,
          active_connections: 15234 + Math.floor(Math.random() * 1000),
          bandwidth_usage: currentUtilization,
          nodes: [
            {
              id: 'SEA-CORE-01',
              name: 'Seattle Core Router',
              status: 'operational',
              utilization: 67.3 + Math.random() * 10,
              capacity: '100Gbps',
              location: 'Seattle, WA',
            },
            {
              id: 'BEL-DIST-02',
              name: 'Bellevue Distribution',
              status: currentUtilization > 85 ? 'warning' : 'operational',
              utilization: currentUtilization,
              capacity: '40Gbps',
              location: 'Bellevue, WA',
            },
          ],
          alerts:
            currentUtilization > 80
              ? [
                  {
                    id: 'ALR-001',
                    severity: 'warning',
                    message: `High utilization on BEL-DIST-02 (${currentUtilization.toFixed(1)}%)`,
                    timestamp: new Date().toISOString(),
                  },
                ]
              : [],
        }),
      });
    });
  }

  /**
   * Setup technician portal mocks with workflow validation
   */
  async setupTechnicianAPIMocks() {
    if (!this.config.enableMocking) return;

    // Work orders with status transitions
    await this.page.route('/api/v1/technician/work-orders*', async (route) => {
      await this.logRequest(route);
      await this.simulateLatency();

      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            work_orders: [
              {
                id: 'WO-TEST-001',
                customer_id: 'CUST-001',
                customer_name: 'John Doe',
                type: 'installation',
                priority: 'high',
                status: 'scheduled',
                scheduled_date: '2024-12-20T10:00:00Z',
                estimated_duration: 180,
                service_type: 'Fiber 1000Mbps',
              },
              {
                id: 'WO-TEST-002',
                customer_id: 'CUST-002',
                customer_name: 'Jane Smith',
                type: 'maintenance',
                priority: 'medium',
                status: 'in_progress',
                scheduled_date: '2024-12-19T14:00:00Z',
                estimated_duration: 120,
                service_type: 'Business 500Mbps',
              },
            ],
            total: 2,
            summary: {
              pending: 1,
              in_progress: 1,
              completed_today: 3,
              scheduled_today: 5,
            },
          }),
        });
      } else if (route.request().method() === 'PUT') {
        // Handle work order updates
        const requestBody = route.request().postDataJSON();

        // Validate status transitions
        const validTransitions = {
          scheduled: ['in_progress', 'cancelled'],
          in_progress: ['completed', 'paused', 'cancelled'],
          paused: ['in_progress', 'cancelled'],
          completed: [], // Cannot change completed orders
          cancelled: [], // Cannot change cancelled orders
        };

        const currentStatus = 'scheduled'; // Would come from database
        const newStatus = requestBody.status;

        if (!validTransitions[currentStatus]?.includes(newStatus)) {
          await route.fulfill({
            status: 400,
            contentType: 'application/json',
            body: JSON.stringify({
              error: `Invalid status transition from ${currentStatus} to ${newStatus}`,
              valid_transitions: validTransitions[currentStatus],
            }),
          });
          return;
        }

        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            success: true,
            work_order: {
              ...requestBody,
              updated_at: new Date().toISOString(),
            },
          }),
        });
      }
    });
  }

  /**
   * Setup reseller portal mocks with commission calculations
   */
  async setupResellerAPIMocks() {
    if (!this.config.enableMocking) return;

    // Dashboard with dynamic commission calculations
    await this.page.route('/api/v1/reseller/dashboard', async (route) => {
      await this.logRequest(route);
      await this.simulateLatency();

      const totalCustomers = 156;
      const avgRevenue = 120;
      const commissionRate = 15;
      const monthlyRevenue = totalCustomers * avgRevenue;
      const monthlyCommission = monthlyRevenue * (commissionRate / 100);

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          summary: {
            total_customers: totalCustomers,
            active_customers: Math.floor(totalCustomers * 0.91),
            monthly_revenue: monthlyRevenue,
            commission_rate: commissionRate,
            monthly_commission: monthlyCommission,
          },
          performance: {
            this_month: {
              new_customers: 8,
              churned_customers: 2,
              net_growth: 6,
              revenue_growth: 12.4,
            },
            targets: {
              monthly_customer_target: 10,
              monthly_revenue_target: 20000,
              progress: {
                customers: 80.0,
                revenue: (monthlyRevenue / 20000) * 100,
              },
            },
          },
          territories: [
            {
              name: 'Downtown District',
              customers: 89,
              potential_customers: 450,
              penetration_rate: (89 / 450) * 100,
            },
          ],
        }),
      });
    });

    // Commission calculations with validation
    await this.page.route('/api/v1/reseller/commissions', async (route) => {
      await this.logRequest(route);
      await this.simulateLatency();

      const baseCommission = 2812.5;
      const variance = Math.random() * 200 - 100; // ±$100 variance
      const totalCommission = baseCommission + variance;

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          current_period: {
            period: '2024-11',
            total_commission: totalCommission,
            status: 'pending',
            payout_date: '2024-12-05T00:00:00Z',
          },
          commission_breakdown: [
            {
              customer_id: 'CUST-RSL-001',
              customer_name: 'Tech Solutions LLC',
              monthly_value: 299.99,
              commission_rate: 15.0,
              commission_amount: 45.0,
            },
          ],
          yearly_total: totalCommission * 12,
          average_monthly: totalCommission,
        }),
      });
    });
  }

  /**
   * Test API error handling and recovery
   */
  async testErrorHandling() {
    // Test 401 Unauthorized
    await this.page.route('/api/v1/customer/dashboard', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Unauthorized',
          code: 'AUTH_REQUIRED',
        }),
      });
    });

    await this.page.goto('/dashboard');

    // Should redirect to login
    await this.page.waitForURL('**/login');

    // Test 500 Server Error
    await this.page.route('/api/v1/customer/dashboard', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({
          error: 'Internal server error',
          code: 'SERVER_ERROR',
        }),
      });
    });

    // Should show error banner
    await this.page.goto('/dashboard');
    await this.page.waitForSelector('[data-testid="error-banner"]');
  }

  /**
   * Test data flow validation
   */
  async validateDataFlows(
    expectedFlows: Array<{
      endpoint: string;
      method: string;
      requiredFields?: string[];
      dataTransformation?: (data: any) => boolean;
    }>
  ) {
    for (const flow of expectedFlows) {
      const matchingRequests = this.requestLog.filter(
        (req) => req.url.includes(flow.endpoint) && req.method === flow.method
      );

      if (matchingRequests.length === 0) {
        throw new Error(`Expected API call to ${flow.endpoint} (${flow.method}) not found`);
      }

      // Validate request structure
      for (const request of matchingRequests) {
        if (flow.requiredFields && request.body) {
          for (const field of flow.requiredFields) {
            if (!(field in request.body)) {
              throw new Error(`Required field '${field}' missing in request to ${flow.endpoint}`);
            }
          }
        }

        // Validate data transformation
        if (flow.dataTransformation && request.body) {
          const isValid = flow.dataTransformation(request.body);
          if (!isValid) {
            throw new Error(`Data transformation validation failed for ${flow.endpoint}`);
          }
        }
      }
    }
  }

  private async logRequest(route: Route) {
    if (!this.config.validateRequests) return;

    const request = route.request();
    this.requestLog.push({
      url: request.url(),
      method: request.method(),
      headers: request.headers(),
      body: request.postDataJSON(),
      timestamp: Date.now(),
    });
  }

  private async simulateLatency() {
    if (!this.config.simulateLatency) return;

    // Simulate realistic API latency (50-200ms)
    const latency = 50 + Math.random() * 150;
    await new Promise((resolve) => setTimeout(resolve, latency));
  }

  /**
   * Get request log for analysis
   */
  getRequestLog() {
    return [...this.requestLog];
  }

  /**
   * Clear request log
   */
  clearRequestLog() {
    this.requestLog = [];
  }
}
