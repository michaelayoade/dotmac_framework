/**
 * Create support ticket via API proxy (requires live platform API)
 * Set E2E_SUPPORT_API=true to enable this test in CI.
 */

import { test, expect } from '@playwright/test';

const ENABLED = process.env.E2E_SUPPORT_API === 'true';

(ENABLED ? test : test.skip)(
  'create support ticket via /api/support @journey @admin @api',
  async ({ request }) => {
    // Basic payload with stable identifiers
    const payload = {
      title: 'E2E Test Ticket',
      description: 'Created by Playwright test',
      priority: 'low',
      category: 'testing',
      customerEmail: 'e2e-test@example.com',
    };

    const res = await request.post('/api/support/tickets', {
      data: payload,
    });

    expect(res.status()).toBeLessThan(500);
    const json = await res.json();
    expect(json).toBeTruthy();
  }
);
