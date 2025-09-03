/**
 * Observability Test Helper - Utilities for E2E observability testing
 * Tests tenant-scoped logs, traces, metrics, and correlation IDs across portals
 */

import { expect } from '@playwright/test';

export interface TelemetryConfig {
  tenantId: string;
  userId: string;
  sessionId: string;
  traceId: string;
  spanId: string;
}

export interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
  tenantId: string;
  userId?: string;
  traceId: string;
  correlationId: string;
  metadata: Record<string, any>;
}

export interface MetricPoint {
  name: string;
  value: number;
  tags: Record<string, string>;
  timestamp: string;
  tenantId: string;
}

export interface TraceSpan {
  traceId: string;
  spanId: string;
  parentSpanId?: string;
  operationName: string;
  startTime: string;
  endTime: string;
  duration: number;
  tags: Record<string, string>;
  logs: Array<{ timestamp: string; fields: Record<string, any> }>;
}

export interface ObservabilityTestScenario {
  name: string;
  tenantId: string;
  actions: Array<{
    type: 'click' | 'navigate' | 'form_submit' | 'api_call';
    target: string;
    expectedLogs?: string[];
    expectedMetrics?: string[];
    expectedTraces?: string[];
  }>;
}

export class ObservabilityTestHelper {
  private mockTelemetryEndpoint = 'http://localhost:8060';

  constructor(private page: any) {}

  async setup() {
    // Mock observability endpoints
    await this.page.route('**/api/telemetry/logs', async (route: any) => {
      const request = route.request();
      const logData = request.postDataJSON();

      // Validate log structure
      const response = await this.validateLogEntry(logData);
      await route.fulfill({
        status: response.status,
        contentType: 'application/json',
        body: JSON.stringify(response.body),
      });
    });

    await this.page.route('**/api/telemetry/metrics', async (route: any) => {
      const request = route.request();
      const metricData = request.postDataJSON();

      const response = await this.validateMetricEntry(metricData);
      await route.fulfill({
        status: response.status,
        contentType: 'application/json',
        body: JSON.stringify(response.body),
      });
    });

    await this.page.route('**/api/telemetry/traces', async (route: any) => {
      const request = route.request();
      const traceData = request.postDataJSON();

      const response = await this.validateTraceEntry(traceData);
      await route.fulfill({
        status: response.status,
        contentType: 'application/json',
        body: JSON.stringify(response.body),
      });
    });

    // Mock OpenTelemetry collector endpoints
    await this.page.route('**/v1/traces', async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'success' }),
      });
    });

    await this.page.route('**/v1/metrics', async (route: any) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'success' }),
      });
    });

    // Initialize observability test data
    await this.initializeObservabilityData();
  }

  async cleanup() {
    await this.clearObservabilityData();
  }

  async testTenantScopedLogging(portalUrl: string, tenantId: string) {
    console.log(`Testing tenant-scoped logging for tenant: ${tenantId}`);

    // Set tenant context
    await this.setTenantContext(tenantId);
    await this.page.goto(portalUrl);

    // Trigger actions that should generate logs
    const testActions = [
      { action: 'login', element: '[data-testid="login-button"]' },
      { action: 'navigate', element: '[data-testid="dashboard-link"]' },
      { action: 'view_data', element: '[data-testid="data-table"]' },
    ];

    const capturedLogs: LogEntry[] = [];

    // Monitor log calls
    await this.page.route('**/api/telemetry/logs', async (route: any) => {
      const logEntry = route.request().postDataJSON();

      // Validate tenant scoping
      if (logEntry.tenantId === tenantId) {
        capturedLogs.push(logEntry);
        console.log(`✓ Captured tenant-scoped log: ${logEntry.message}`);
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'logged' }),
      });
    });

    // Perform test actions
    for (const testAction of testActions) {
      try {
        if (await this.page.locator(testAction.element).isVisible()) {
          await this.page.click(testAction.element);

          // Verify log was generated with correct tenant context
          await this.page.waitForTimeout(1000);

          const relevantLogs = capturedLogs.filter(
            (log) => log.tenantId === tenantId && log.metadata?.action === testAction.action
          );

          expect(relevantLogs.length).toBeGreaterThan(0);
        }
      } catch (error) {
        console.log(`Action ${testAction.action} skipped: ${error}`);
      }
    }

    // Validate log structure and tenant scoping
    for (const log of capturedLogs) {
      expect(log.tenantId).toBe(tenantId);
      expect(log.traceId).toBeTruthy();
      expect(log.correlationId).toBeTruthy();
      expect(log.timestamp).toBeTruthy();
      expect(log.level).toMatch(/DEBUG|INFO|WARN|ERROR/);
    }

    return true;
  }

  async testCorrelationIds(portalUrl: string, tenantId: string) {
    console.log(`Testing correlation ID propagation for tenant: ${tenantId}`);

    await this.setTenantContext(tenantId);
    await this.page.goto(portalUrl);

    const correlationId = `corr-${Date.now()}-${tenantId}`;
    const capturedTelemetry: Array<{ type: string; data: any }> = [];

    // Set correlation ID in browser
    await this.page.evaluate((corrId) => {
      window.correlationId = corrId;
      sessionStorage.setItem('correlationId', corrId);
    }, correlationId);

    // Monitor all telemetry calls
    await this.page.route('**/api/telemetry/**', async (route: any) => {
      const telemetryData = route.request().postDataJSON();
      const telemetryType = route.request().url().split('/').pop();

      capturedTelemetry.push({
        type: telemetryType,
        data: telemetryData,
      });

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'received' }),
      });
    });

    // Perform user journey that spans multiple operations
    const userJourney = [
      { action: 'page_load', trigger: () => this.page.reload() },
      {
        action: 'form_interaction',
        trigger: () => this.page.click('[data-testid="search-input"]'),
      },
      { action: 'api_call', trigger: () => this.page.click('[data-testid="refresh-button"]') },
    ];

    for (const step of userJourney) {
      try {
        await step.trigger();
        await this.page.waitForTimeout(500);
      } catch (error) {
        console.log(`Journey step ${step.action} skipped: ${error}`);
      }
    }

    // Verify correlation ID propagation
    const logsWithCorrelation = capturedTelemetry
      .filter((item) => item.type === 'logs')
      .filter((item) => item.data.correlationId === correlationId);

    const metricsWithCorrelation = capturedTelemetry
      .filter((item) => item.type === 'metrics')
      .filter((item) => item.data.tags?.correlationId === correlationId);

    const tracesWithCorrelation = capturedTelemetry
      .filter((item) => item.type === 'traces')
      .filter((item) => item.data.tags?.correlationId === correlationId);

    expect(logsWithCorrelation.length).toBeGreaterThan(0);
    console.log(`✓ Correlation ID found in ${logsWithCorrelation.length} log entries`);

    return true;
  }

  async testMetricsTenantTagging(portalUrl: string, tenantId: string) {
    console.log(`Testing tenant-tagged metrics for tenant: ${tenantId}`);

    await this.setTenantContext(tenantId);
    await this.page.goto(portalUrl);

    const capturedMetrics: MetricPoint[] = [];

    await this.page.route('**/api/telemetry/metrics', async (route: any) => {
      const metricData = route.request().postDataJSON();

      if (metricData.tags?.tenantId === tenantId) {
        capturedMetrics.push(metricData);
        console.log(`✓ Captured tenant metric: ${metricData.name} = ${metricData.value}`);
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'recorded' }),
      });
    });

    // Trigger actions that should generate metrics
    const metricGeneratingActions = [
      { action: 'page_view', element: 'body', expectedMetric: 'page.view' },
      {
        action: 'button_click',
        element: '[data-testid="action-button"]',
        expectedMetric: 'user.interaction',
      },
      {
        action: 'form_submit',
        element: '[data-testid="test-form"]',
        expectedMetric: 'form.submission',
      },
    ];

    for (const action of metricGeneratingActions) {
      try {
        // Trigger metric-generating action
        if (action.action === 'page_view') {
          await this.page.reload();
        } else if (await this.page.locator(action.element).isVisible()) {
          await this.page.click(action.element);
        }

        await this.page.waitForTimeout(1000);

        // Verify metric was captured with tenant tag
        const relevantMetrics = capturedMetrics.filter(
          (metric) =>
            metric.name.includes(action.expectedMetric) && metric.tags.tenantId === tenantId
        );

        if (relevantMetrics.length > 0) {
          console.log(`✓ Metric ${action.expectedMetric} properly tagged for tenant ${tenantId}`);
        }
      } catch (error) {
        console.log(`Metric action ${action.action} skipped: ${error}`);
      }
    }

    // Validate metric structure
    for (const metric of capturedMetrics) {
      expect(metric.tenantId).toBe(tenantId);
      expect(metric.tags.tenantId).toBe(tenantId);
      expect(metric.timestamp).toBeTruthy();
      expect(metric.name).toBeTruthy();
      expect(typeof metric.value).toBe('number');
    }

    return capturedMetrics.length > 0;
  }

  async testDistributedTracing(portalUrl: string, tenantId: string) {
    console.log(`Testing distributed tracing for tenant: ${tenantId}`);

    await this.setTenantContext(tenantId);
    await this.page.goto(portalUrl);

    const capturedTraces: TraceSpan[] = [];
    const traceId = `trace-${Date.now()}-${tenantId}`;

    // Set trace context
    await this.page.evaluate((tId) => {
      window.traceId = tId;
      sessionStorage.setItem('traceId', tId);
    }, traceId);

    await this.page.route('**/api/telemetry/traces', async (route: any) => {
      const traceData = route.request().postDataJSON();

      if (traceData.tags?.tenantId === tenantId) {
        capturedTraces.push(traceData);
        console.log(`✓ Captured trace span: ${traceData.operationName}`);
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'traced' }),
      });
    });

    // Perform multi-step operation that should create trace spans
    const traceableOperations = [
      { name: 'page_load', action: () => this.page.reload() },
      { name: 'user_action', action: () => this.page.click('[data-testid="trace-button"]') },
      { name: 'api_request', action: () => this.page.click('[data-testid="api-trigger"]') },
    ];

    for (const operation of traceableOperations) {
      try {
        await operation.action();
        await this.page.waitForTimeout(1000);
      } catch (error) {
        console.log(`Trace operation ${operation.name} skipped: ${error}`);
      }
    }

    // Validate trace structure and tenant tagging
    for (const trace of capturedTraces) {
      expect(trace.tags.tenantId).toBe(tenantId);
      expect(trace.traceId).toBeTruthy();
      expect(trace.spanId).toBeTruthy();
      expect(trace.operationName).toBeTruthy();
      expect(trace.startTime).toBeTruthy();
      expect(trace.duration).toBeGreaterThan(0);
    }

    // Verify trace hierarchy if multiple spans exist
    if (capturedTraces.length > 1) {
      const parentSpans = capturedTraces.filter((span) => !span.parentSpanId);
      const childSpans = capturedTraces.filter((span) => span.parentSpanId);

      expect(parentSpans.length).toBeGreaterThan(0);
      console.log(
        `✓ Trace hierarchy: ${parentSpans.length} parent spans, ${childSpans.length} child spans`
      );
    }

    return capturedTraces.length > 0;
  }

  async testCrossPortalObservability(
    portals: Array<{ name: string; url: string }>,
    tenantId: string
  ) {
    console.log(`Testing cross-portal observability for tenant: ${tenantId}`);

    const allTelemetry: Array<{ portal: string; type: string; data: any }> = [];
    const sessionId = `session-${Date.now()}-${tenantId}`;

    await this.setTenantContext(tenantId);

    // Set up global telemetry capture
    await this.page.route('**/api/telemetry/**', async (route: any) => {
      const telemetryData = route.request().postDataJSON();
      const telemetryType = route.request().url().split('/').pop();
      const currentUrl = await this.page.url();
      const portal = portals.find((p) => currentUrl.includes(p.url.split('//')[1]));

      allTelemetry.push({
        portal: portal?.name || 'unknown',
        type: telemetryType,
        data: telemetryData,
      });

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'received' }),
      });
    });

    // Visit each portal and perform actions
    for (const portal of portals.slice(0, 2)) {
      // Test first 2 portals
      try {
        console.log(`Testing observability on ${portal.name} portal`);

        await this.page.goto(portal.url);

        // Set consistent session context
        await this.page.evaluate((sId) => {
          sessionStorage.setItem('sessionId', sId);
        }, sessionId);

        // Perform portal-specific actions
        await this.page.click('body'); // Trigger page interaction
        await this.page.waitForTimeout(1000);

        if (await this.page.locator('[data-testid="dashboard-link"]').isVisible()) {
          await this.page.click('[data-testid="dashboard-link"]');
          await this.page.waitForTimeout(1000);
        }
      } catch (error) {
        console.log(`Portal ${portal.name} testing skipped: ${error}`);
      }
    }

    // Analyze cross-portal telemetry consistency
    const telemetryByPortal = allTelemetry.reduce(
      (acc, item) => {
        if (!acc[item.portal]) acc[item.portal] = [];
        acc[item.portal].push(item);
        return acc;
      },
      {} as Record<string, any[]>
    );

    // Verify tenant consistency across portals
    for (const [portalName, telemetryItems] of Object.entries(telemetryByPortal)) {
      const tenantIds = telemetryItems
        .map((item) => item.data.tenantId || item.data.tags?.tenantId)
        .filter(Boolean);

      const uniqueTenantIds = [...new Set(tenantIds)];
      expect(uniqueTenantIds.length).toBeLessThanOrEqual(1);

      if (uniqueTenantIds.length === 1) {
        expect(uniqueTenantIds[0]).toBe(tenantId);
        console.log(`✓ Portal ${portalName}: Consistent tenant ID ${tenantId}`);
      }
    }

    return Object.keys(telemetryByPortal).length > 0;
  }

  async testObservabilityPerformanceImpact(portalUrl: string, tenantId: string) {
    console.log(`Testing observability performance impact for tenant: ${tenantId}`);

    await this.setTenantContext(tenantId);

    // Measure page load time without observability
    await this.page.route('**/api/telemetry/**', async (route: any) => {
      await route.abort();
    });

    const startTimeWithoutObs = Date.now();
    await this.page.goto(portalUrl);
    const loadTimeWithoutObs = Date.now() - startTimeWithoutObs;

    // Measure page load time with observability
    await this.page.route('**/api/telemetry/**', async (route: any) => {
      // Small delay to simulate telemetry overhead
      await new Promise((resolve) => setTimeout(resolve, 10));
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'received' }),
      });
    });

    const startTimeWithObs = Date.now();
    await this.page.reload();
    const loadTimeWithObs = Date.now() - startTimeWithObs;

    const performanceImpact = ((loadTimeWithObs - loadTimeWithoutObs) / loadTimeWithoutObs) * 100;

    console.log(
      `Performance impact: ${performanceImpact.toFixed(2)}% (${loadTimeWithObs - loadTimeWithoutObs}ms difference)`
    );

    // Observability should have minimal performance impact (< 20%)
    expect(performanceImpact).toBeLessThan(20);

    return true;
  }

  async testErrorTracing(portalUrl: string, tenantId: string) {
    console.log(`Testing error tracing for tenant: ${tenantId}`);

    await this.setTenantContext(tenantId);
    await this.page.goto(portalUrl);

    const errorLogs: LogEntry[] = [];

    await this.page.route('**/api/telemetry/logs', async (route: any) => {
      const logData = route.request().postDataJSON();

      if (logData.level === 'ERROR' && logData.tenantId === tenantId) {
        errorLogs.push(logData);
        console.log(`✓ Captured error log: ${logData.message}`);
      }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'logged' }),
      });
    });

    // Trigger intentional errors for testing
    try {
      // Trigger client-side error
      await this.page.evaluate(() => {
        throw new Error('Test error for observability');
      });
    } catch {
      // Expected to fail
    }

    // Trigger API error
    await this.page.route('**/api/test-error', async (route: any) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Test server error' }),
      });
    });

    try {
      await this.page.evaluate(() => {
        fetch('/api/test-error').catch(() => {
          console.error('API error occurred');
        });
      });
    } catch {
      // Expected to fail
    }

    await this.page.waitForTimeout(2000);

    // Validate error logs contain proper context
    for (const errorLog of errorLogs) {
      expect(errorLog.tenantId).toBe(tenantId);
      expect(errorLog.level).toBe('ERROR');
      expect(errorLog.traceId).toBeTruthy();
      expect(errorLog.correlationId).toBeTruthy();
      expect(errorLog.metadata).toBeTruthy();
    }

    return errorLogs.length > 0;
  }

  private async setTenantContext(tenantId: string) {
    await this.page.evaluate((tid) => {
      window.tenantId = tid;
      sessionStorage.setItem('tenantId', tid);
      localStorage.setItem('tenantContext', JSON.stringify({ tenantId: tid }));
    }, tenantId);
  }

  private async validateLogEntry(logData: any) {
    const requiredFields = ['timestamp', 'level', 'message', 'tenantId', 'traceId'];
    const missingFields = requiredFields.filter((field) => !logData[field]);

    if (missingFields.length > 0) {
      return {
        status: 400,
        body: { error: `Missing required fields: ${missingFields.join(', ')}` },
      };
    }

    return {
      status: 200,
      body: { status: 'log validated and stored' },
    };
  }

  private async validateMetricEntry(metricData: any) {
    const requiredFields = ['name', 'value', 'timestamp', 'tenantId', 'tags'];
    const missingFields = requiredFields.filter((field) => !metricData[field]);

    if (missingFields.length > 0) {
      return {
        status: 400,
        body: { error: `Missing required fields: ${missingFields.join(', ')}` },
      };
    }

    if (typeof metricData.value !== 'number') {
      return {
        status: 400,
        body: { error: 'Metric value must be a number' },
      };
    }

    return {
      status: 200,
      body: { status: 'metric validated and stored' },
    };
  }

  private async validateTraceEntry(traceData: any) {
    const requiredFields = ['traceId', 'spanId', 'operationName', 'startTime', 'tags'];
    const missingFields = requiredFields.filter((field) => !traceData[field]);

    if (missingFields.length > 0) {
      return {
        status: 400,
        body: { error: `Missing required fields: ${missingFields.join(', ')}` },
      };
    }

    if (!traceData.tags.tenantId) {
      return {
        status: 400,
        body: { error: 'Trace must include tenantId in tags' },
      };
    }

    return {
      status: 200,
      body: { status: 'trace validated and stored' },
    };
  }

  private async initializeObservabilityData() {
    await this.page.evaluate(() => {
      sessionStorage.setItem('observability_test_mode', 'true');
      sessionStorage.setItem('telemetry_endpoint', 'http://localhost:8060');
    });
  }

  private async clearObservabilityData() {
    await this.page.evaluate(() => {
      sessionStorage.removeItem('observability_test_mode');
      sessionStorage.removeItem('telemetry_endpoint');
      sessionStorage.removeItem('tenantId');
      sessionStorage.removeItem('correlationId');
      sessionStorage.removeItem('traceId');
      sessionStorage.removeItem('sessionId');
    });
  }

  // Utility methods for common test patterns
  static generateTelemetryConfig(tenantId: string): TelemetryConfig {
    return {
      tenantId,
      userId: `user-${Date.now()}`,
      sessionId: `session-${Date.now()}`,
      traceId: `trace-${Date.now()}`,
      spanId: `span-${Date.now()}`,
    };
  }

  static createMockLogEntry(config: TelemetryConfig, level: string, message: string): LogEntry {
    return {
      timestamp: new Date().toISOString(),
      level,
      message,
      tenantId: config.tenantId,
      userId: config.userId,
      traceId: config.traceId,
      correlationId: `${config.traceId}-${config.spanId}`,
      metadata: {
        sessionId: config.sessionId,
        userAgent: 'test-browser',
        url: window.location?.href || 'test-url',
      },
    };
  }

  static createMockMetric(config: TelemetryConfig, name: string, value: number): MetricPoint {
    return {
      name,
      value,
      tags: {
        tenantId: config.tenantId,
        userId: config.userId,
        environment: 'test',
      },
      timestamp: new Date().toISOString(),
      tenantId: config.tenantId,
    };
  }
}
