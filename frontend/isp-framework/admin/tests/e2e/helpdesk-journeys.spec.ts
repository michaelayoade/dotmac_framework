/**
 * Exercise chat and knowledge base endpoints via support proxy.
 * Requires live platform API. Enable with E2E_SUPPORT_API=true.
 */

import { test, expect } from '@playwright/test';

const ENABLED = process.env.E2E_SUPPORT_API === 'true';

(ENABLED ? test : test.skip)(
  'chat start/end via /api/support @journey @admin @api',
  async ({ request }) => {
    // Start a chat session
    const start = await request.post('/api/support/chat/sessions', {
      data: { customerId: 'e2e-test-customer' },
    });
    expect(start.status()).toBeLessThan(500);
    const startJson = await start.json().catch(() => ({}));
    const sessionId = startJson?.data?.sessionId || startJson?.sessionId;
    // End session if possible
    if (sessionId) {
      const end = await request.post(`/api/support/chat/sessions/${sessionId}/end`);
      expect(end.status()).toBeLessThan(500);
    }
  }
);

(ENABLED ? test : test.skip)(
  'knowledge base vote via /api/support @journey @admin @api',
  async ({ request }) => {
    // Vote on an article; use a stable test id if available
    const articleId = process.env.E2E_KB_ARTICLE_ID || 'kb-article-e2e';
    const res = await request.post(`/api/support/kb/articles/${articleId}/vote`, {
      data: { helpful: true },
    });
    expect(res.status()).toBeLessThan(500);
  }
);
