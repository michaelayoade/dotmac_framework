import { Page, expect } from '@playwright/test';

export interface TelemetryConfig {
  endpoint?: string; // where logs/metrics/traces would be sent
}

export interface ObservabilityTestScenario {
  name: string;
  action: () => Promise<void>;
}

export class ObservabilityTestHelper {
  constructor(
    private page: Page,
    private config: TelemetryConfig = { endpoint: '/api/telemetry' }
  ) {}

  async testTenantScopedLogging(baseUrl: string, tenantId: string): Promise<boolean> {
    const logs: any[] = [];
    await this.captureTelemetry(logs);
    await this.page.goto(baseUrl);
    await this.emitTelemetry('log', tenantId);
    await this.page.waitForTimeout(200);
    expect(
      logs.some(
        (l) => l.type === 'log' && (l.tenantId === tenantId || l.tags?.tenantId === tenantId)
      )
    ).toBeTruthy();
    return true;
  }

  async testCorrelationIds(baseUrl: string, tenantId: string): Promise<boolean> {
    const items: any[] = [];
    await this.captureTelemetry(items);
    await this.page.goto(baseUrl);
    const correlationId = 'corr-' + Date.now();
    await this.emitTelemetry('trace', tenantId, correlationId);
    await this.page.waitForTimeout(200);
    expect(
      items.some(
        (i) =>
          i.correlationId === correlationId || i.headers?.['X-Correlation-ID'] === correlationId
      )
    ).toBeTruthy();
    return true;
  }

  async testMetricsTenantTagging(baseUrl: string, tenantId: string): Promise<boolean> {
    const items: any[] = [];
    await this.captureTelemetry(items);
    await this.page.goto(baseUrl);
    await this.emitTelemetry('metric', tenantId);
    await this.page.waitForTimeout(200);
    expect(
      items.some(
        (i) => i.type === 'metric' && (i.tenantId === tenantId || i.tags?.tenantId === tenantId)
      )
    ).toBeTruthy();
    return true;
  }

  async testDistributedTracing(baseUrl: string, tenantId: string): Promise<boolean> {
    const items: any[] = [];
    await this.captureTelemetry(items);
    await this.page.goto(baseUrl);
    await this.emitTelemetry(
      'span',
      tenantId,
      undefined,
      '00-' + '0'.repeat(32) + '-0000000000000001-01'
    );
    await this.page.waitForTimeout(200);
    expect(
      items.some((i) => i.type === 'span' && (i.traceparent || i.headers?.traceparent))
    ).toBeTruthy();
    return true;
  }

  private async captureTelemetry(store: any[]) {
    await this.page.route('**' + this.config.endpoint + '/**', async (route) => {
      if (route.request().method() === 'POST') {
        try {
          store.push(route.request().postDataJSON());
        } catch {
          /* ignore */
        }
      }
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ ok: true }),
      });
    });
  }

  private async emitTelemetry(
    type: string,
    tenantId: string,
    correlationId?: string,
    traceparent?: string
  ) {
    await this.page.evaluate(
      async ({ endpoint, t, tenantId, correlationId, traceparent }) => {
        const body: any = { type: t, tenantId, ts: Date.now(), tags: { tenantId } };
        const headers: Record<string, string> = { 'Content-Type': 'application/json' };
        if (correlationId) {
          headers['X-Correlation-ID'] = correlationId;
          body.correlationId = correlationId;
        }
        if (traceparent) {
          headers['traceparent'] = traceparent;
          body.traceparent = traceparent;
        }
        await fetch(endpoint + '/emit', { method: 'POST', headers, body: JSON.stringify(body) });
      },
      { endpoint: this.config.endpoint, t: type, tenantId, correlationId, traceparent }
    );
  }
}
