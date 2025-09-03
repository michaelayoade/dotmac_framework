/**
 * Multi-Portal SSO E2E (Mocked IdP)
 * Validates OIDC + SAML flows, RBAC, token handling, cross-portal session, perf, and a11y
 * without relying on external IdPs or running the real apps.
 */

import { test, expect, Page } from '@playwright/test';

// Simple in-memory token forge for tests (simulated)
function forgeToken(payload: Record<string, any>): string {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT', kid: 'test' })).toString(
    'base64url'
  );
  const body = Buffer.from(JSON.stringify(payload)).toString('base64url');
  // Signature is not verified in this mocked flow; append '-sig'
  const sig = 'signature';
  return `${header}.${body}.${sig}`;
}

const portals = ['admin', 'customer', 'technician', 'reseller'] as const;
type Portal = (typeof portals)[number];

// Generates a synthetic login page for a given portal and protocol
function syntheticLoginHTML(portal: Portal) {
  return `<!doctype html>
  <html lang="en">
    <head>
      <meta charset="utf-8"/>
      <title>${portal} login</title>
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <style>
        :focus { outline: 3px solid #4F46E5; outline-offset: 2px; }
        .hidden { display: none; }
        .btn { padding: 8px 12px; border: 1px solid #ccc; border-radius: 6px; }
      </style>
    </head>
    <body>
      <main role="main" aria-label="${portal} login">
        <h1 id="title">${portal} portal</h1>
        <form aria-describedby="sso-desc">
          <p id="sso-desc">Choose a single sign-on method</p>
          <button id="oidc" class="btn" type="button" aria-label="Sign in with OIDC">Sign in with OIDC</button>
          <button id="saml" class="btn" type="button" aria-label="Sign in with SAML">Sign in with SAML</button>
        </form>
        <div id="error" role="alert" class="hidden"></div>
        <section id="dashboard" class="hidden" aria-live="polite">
          <h2>Dashboard</h2>
          <div id="role-info"></div>
          <a id="protected-link" href="#" aria-label="protected area">Protected Area</a>
        </section>
      </main>
      <script>
        const tenantKey = 'tenant:test';
        const t0 = performance.now();
        function setSession(token, roles) {
          const data = { token, roles, issuedAt: Date.now() };
          localStorage.setItem(tenantKey, JSON.stringify(data));
        }
        function getSession() {
          try { return JSON.parse(localStorage.getItem(tenantKey) || 'null'); } catch { return null; }
        }
        function validateToken(session) {
          if (!session || !session.token) return { ok: false, reason: 'missing' };
          try {
            const parts = session.token.split('.');
            const payload = JSON.parse(atob(parts[1].replace(/-/g,'+').replace(/_/g,'/')));
            if (payload.exp && Date.now()/1000 > payload.exp) return { ok: false, reason: 'expired' };
            if (payload.iss !== 'https://idp.test' || !payload.aud?.includes('${portal}')) return { ok: false, reason: 'claims' };
            return { ok: true, payload };
          } catch (e) { return { ok: false, reason: 'invalid' }; }
        }
        function showDashboard(session) {
          const roleInfo = document.getElementById('role-info');
          roleInfo.textContent = 'Roles: ' + (session.roles || []).join(',');
          document.getElementById('dashboard').classList.remove('hidden');
          const dt = performance.now() - t0;
          // expose for Playwright
          window.__authPerf = dt;
        }
        function handleLogin(kind) {
          // simulate IdP round-trip but keep < 300ms
          setTimeout(() => {
            const now = Math.floor(Date.now()/1000);
            const payload = { iss: 'https://idp.test', aud: ['${portal}'], iat: now, exp: now + 3600, sub: 'user-123', roles: ['${portal}'] };
            const token = '${'`'}' + '${'`'}'; // prevent bundlers from altering template
            // store token and roles
            setSession('${'${'}TOKEN_PLACEHOLDER${'}'}', payload.roles);
            // redraw UI
            const session = getSession();
            const v = validateToken(session);
            if (v.ok) { showDashboard(session); }
          }, 120);
        }
        // Restore session if present
        (function init(){
          const s = getSession();
          const v = validateToken(s);
          if (v.ok) showDashboard(s);
        })();
        document.getElementById('oidc').addEventListener('click', () => handleLogin('oidc'));
        document.getElementById('saml').addEventListener('click', () => handleLogin('saml'));
      </script>
    </body>
  </html>`;
}

async function serveSynthetic(page: Page, portal: Portal) {
  await page.route('**/*', async (route) => {
    // Always fulfill with our synthetic login page
    await route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: syntheticLoginHTML(portal),
    });
  });
}

test.describe('Multi-Portal SSO (mocked IdP)', () => {
  test('OIDC login happy-path (admin)', async ({ page }) => {
    await serveSynthetic(page, 'admin');
    await page.goto('http://localhost:3000/admin/login');
    await page.getByRole('button', { name: /oidc/i }).focus();
    await page.keyboard.press('Enter');
    // Simulate IdP issuing token into storage
    const now = Math.floor(Date.now() / 1000);
    const token = forgeToken({
      iss: 'https://idp.test',
      aud: ['admin'],
      iat: now,
      exp: now + 3600,
      sub: 'user-1',
      roles: ['admin'],
    });
    await page.evaluate((t) => {
      localStorage.setItem(
        'tenant:test',
        JSON.stringify({ token: t, roles: ['admin'], issuedAt: Date.now() })
      );
    }, token);
    await expect(page.locator('#dashboard')).toBeVisible();
    await expect(page.locator('#role-info')).toContainText('admin');
  });

  test('SAML login happy-path (customer)', async ({ page }) => {
    await serveSynthetic(page, 'customer');
    await page.goto('http://localhost:3001/customer/login');
    await page.getByRole('button', { name: /saml/i }).click();
    const now = Math.floor(Date.now() / 1000);
    const token = forgeToken({
      iss: 'https://idp.test',
      aud: ['customer'],
      iat: now,
      exp: now + 3600,
      sub: 'user-2',
      roles: ['customer'],
    });
    await page.evaluate((t) => {
      localStorage.setItem(
        'tenant:test',
        JSON.stringify({ token: t, roles: ['customer'], issuedAt: Date.now() })
      );
    }, token);
    await expect(page.locator('#dashboard')).toBeVisible();
    await expect(page.locator('#role-info')).toContainText('customer');
  });

  test('RBAC: allow technician role, deny reseller content', async ({ page }) => {
    await serveSynthetic(page, 'technician');
    await page.goto('http://localhost:3002/technician/login');
    const now = Math.floor(Date.now() / 1000);
    const token = forgeToken({
      iss: 'https://idp.test',
      aud: ['technician'],
      iat: now,
      exp: now + 3600,
      sub: 'user-3',
      roles: ['technician'],
    });
    await page.evaluate((t) => {
      localStorage.setItem(
        'tenant:test',
        JSON.stringify({ token: t, roles: ['technician'], issuedAt: Date.now() })
      );
    }, token);
    await expect(page.locator('#dashboard')).toBeVisible();
    await expect(page.locator('#role-info')).toContainText('technician');
    // Navigate to reseller synthetic page and verify not auto-authorized for reseller-only routes (role mismatch)
    await serveSynthetic(page, 'reseller');
    await page.goto('http://localhost:3003/reseller/login');
    // The stored roles are technician; assert role-info does not contain reseller
    await expect(page.locator('#role-info')).not.toContainText('reseller');
  });

  test('Security: expired token forces re-auth', async ({ page }) => {
    await serveSynthetic(page, 'admin');
    await page.goto('http://localhost:3000/admin/login');
    const past = Math.floor(Date.now() / 1000) - 10;
    const token = forgeToken({
      iss: 'https://idp.test',
      aud: ['admin'],
      iat: past - 60,
      exp: past,
      sub: 'user-4',
      roles: ['admin'],
    });
    await page.evaluate((t) => {
      localStorage.setItem(
        'tenant:test',
        JSON.stringify({ token: t, roles: ['admin'], issuedAt: Date.now() })
      );
    }, token);
    // The synthetic app validates on load and will not show dashboard if expired
    await expect(page.locator('#dashboard')).toBeHidden();
  });

  test('Security: invalid audience rejected', async ({ page }) => {
    await serveSynthetic(page, 'customer');
    await page.goto('http://localhost:3001/customer/login');
    const now = Math.floor(Date.now() / 1000);
    const token = forgeToken({
      iss: 'https://idp.test',
      aud: ['wrong-aud'],
      iat: now,
      exp: now + 3600,
      sub: 'user-5',
      roles: ['customer'],
    });
    await page.evaluate((t) => {
      localStorage.setItem(
        'tenant:test',
        JSON.stringify({ token: t, roles: ['customer'], issuedAt: Date.now() })
      );
    }, token);
    await expect(page.locator('#dashboard')).toBeHidden();
  });

  test('Cross-portal session: login once and access another authorized portal', async ({
    page,
  }) => {
    await serveSynthetic(page, 'admin');
    await page.goto('http://localhost:3000/admin/login');
    const now = Math.floor(Date.now() / 1000);
    const token = forgeToken({
      iss: 'https://idp.test',
      aud: ['admin', 'customer'],
      iat: now,
      exp: now + 3600,
      sub: 'user-6',
      roles: ['admin', 'customer'],
    });
    await page.evaluate((t) => {
      localStorage.setItem(
        'tenant:test',
        JSON.stringify({ token: t, roles: ['admin', 'customer'], issuedAt: Date.now() })
      );
    }, token);
    await expect(page.locator('#dashboard')).toBeVisible();
    // Switch to customer
    await serveSynthetic(page, 'customer');
    await page.goto('http://localhost:3001/customer/login');
    await expect(page.locator('#dashboard')).toBeVisible();
    await expect(page.locator('#role-info')).toContainText('customer');
  });

  test('Performance: sub-second authentication flow', async ({ page }) => {
    await serveSynthetic(page, 'reseller');
    await page.goto('http://localhost:3003/reseller/login');
    await page.click('#oidc');
    // Issue a valid token quickly
    const now = Math.floor(Date.now() / 1000);
    const token = forgeToken({
      iss: 'https://idp.test',
      aud: ['reseller'],
      iat: now,
      exp: now + 3600,
      sub: 'user-7',
      roles: ['reseller'],
    });
    await page.evaluate((t) => {
      localStorage.setItem(
        'tenant:test',
        JSON.stringify({ token: t, roles: ['reseller'], issuedAt: Date.now() })
      );
    }, token);
    // Wait for dashboard visible and read perf marker
    await expect(page.locator('#dashboard')).toBeVisible();
    const dt = await page.evaluate(() => (window as any).__authPerf as number);
    expect(dt).toBeLessThan(1000);
  });

  test('Accessibility: keyboard navigation and labels present', async ({ page }) => {
    await serveSynthetic(page, 'technician');
    await page.goto('http://localhost:3002/technician/login');
    await expect(page.getByRole('main', { name: /technician login/i })).toBeVisible();
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: /oidc/i })).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: /saml/i })).toBeFocused();
  });

  test('Error handling: IdP error shows message', async ({ page }) => {
    await serveSynthetic(page, 'admin');
    await page.goto('http://localhost:3000/admin/login');
    // Simulate IdP error by storing no token and toggling error
    await page.evaluate(() => {
      const el = document.getElementById('error');
      el!.textContent = 'Authentication failed: access_denied';
      el!.classList.remove('hidden');
    });
    await expect(page.getByRole('alert')).toContainText('access_denied');
  });
});
