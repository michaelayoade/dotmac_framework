/**
 * Real-time System E2E Tests
 * 
 * Tests WebSocket connections, real-time notifications, and live collaboration
 * features across the Management Platform and Tenant Containers. Validates
 * connection lifecycle, failure recovery, and performance under load.
 */

import { test, expect, Browser, Page } from '@playwright/test';
import { createTestTenant, cleanupTestTenant } from '../utils/tenant-factory';
import { authenticateAsManagementAdmin, authenticateAsTenant } from '../utils/auth-helpers';
import { 
  establishWebSocketConnection,
  monitorWebSocketMessages,
  simulateConnectionFailure,
  measureWebSocketLatency
} from '../utils/websocket-helpers';

test.describe('WebSocket Connection Lifecycle', () => {
  let testTenantId: string;
  let wsConnections: WebSocket[] = [];

  test.beforeAll(async () => {
    const tenant = await createTestTenant({
      name: 'WebSocket Test Corp',
      realtimeEnabled: true
    });
    testTenantId = tenant.id;
  });

  test.afterAll(async () => {
    // Cleanup WebSocket connections
    wsConnections.forEach(ws => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.close();
      }
    });
    await cleanupTestTenant(testTenantId);
  });

  test('WebSocket connection establishment and authentication', async ({ page, context }) => {
    // Step 1: Management Admin establishes WebSocket connection
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto('/dashboard');

    // Monitor WebSocket connection establishment
    const wsMessages: any[] = [];
    const wsConnection = await establishWebSocketConnection(page, {
      url: 'wss://api.dotmac.com/ws/management',
      onMessage: (message) => wsMessages.push(message),
      authentication: true
    });

    wsConnections.push(wsConnection);

    // Verify connection established
    await page.waitForTimeout(2000);
    expect(wsConnection.readyState).toBe(WebSocket.OPEN);

    // Check authentication success message
    const authMessage = wsMessages.find(msg => msg.type === 'auth_success');
    expect(authMessage).toBeTruthy();
    expect(authMessage.user_id).toBeTruthy();
    expect(authMessage.permissions).toContain('management_admin');

    // Step 2: Tenant establishes separate WebSocket connection
    const tenantPage = await context.newPage();
    const tenant = await getTenantDetails(testTenantId);
    await tenantPage.goto(`https://${tenant.domain}/login`);

    await authenticateAsTenant(tenantPage, {
      email: `admin@${tenant.domain.replace('.dotmac.app', '')}.com`,
      password: 'tenant123'
    });

    await tenantPage.goto('/dashboard');

    const tenantWsMessages: any[] = [];
    const tenantWsConnection = await establishWebSocketConnection(tenantPage, {
      url: `wss://${tenant.domain}/ws/tenant`,
      onMessage: (message) => tenantWsMessages.push(message),
      authentication: true
    });

    wsConnections.push(tenantWsConnection);

    // Verify tenant connection
    expect(tenantWsConnection.readyState).toBe(WebSocket.OPEN);

    const tenantAuthMessage = tenantWsMessages.find(msg => msg.type === 'auth_success');
    expect(tenantAuthMessage).toBeTruthy();
    expect(tenantAuthMessage.tenant_id).toBe(testTenantId);
  });

  test('WebSocket reconnection after network failure', async ({ page }) => {
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto('/dashboard');

    let reconnectionCount = 0;
    const wsMessages: any[] = [];

    const wsConnection = await establishWebSocketConnection(page, {
      url: 'wss://api.dotmac.com/ws/management',
      onMessage: (message) => {
        wsMessages.push(message);
        if (message.type === 'reconnection_success') {
          reconnectionCount++;
        }
      },
      authentication: true,
      reconnectOnFailure: true
    });

    wsConnections.push(wsConnection);

    // Wait for initial connection
    await page.waitForTimeout(2000);
    expect(wsConnection.readyState).toBe(WebSocket.OPEN);

    // Simulate network failure
    await simulateConnectionFailure(wsConnection);
    
    // Wait for reconnection attempts
    await page.waitForTimeout(10000);

    // Verify reconnection occurred
    expect(reconnectionCount).toBeGreaterThan(0);
    expect(wsConnection.readyState).toBe(WebSocket.OPEN);

    // Test that messages work after reconnection
    wsConnection.send(JSON.stringify({ type: 'ping' }));
    
    await page.waitForTimeout(1000);
    const pongMessage = wsMessages.find(msg => msg.type === 'pong');
    expect(pongMessage).toBeTruthy();
  });

  test('WebSocket connection scaling with multiple concurrent users', async ({ browser }) => {
    const connections: { page: Page, ws: WebSocket }[] = [];

    try {
      // Create multiple browser contexts simulating concurrent users
      for (let i = 0; i < 10; i++) {
        const context = await browser.newContext();
        const page = await context.newPage();
        
        await authenticateAsManagementAdmin(page, {
          email: 'admin@dotmac.com',
          password: 'admin123'
        });

        await page.goto('/dashboard');

        const wsConnection = await establishWebSocketConnection(page, {
          url: 'wss://api.dotmac.com/ws/management',
          onMessage: () => {}, // No message handling needed for scale test
          authentication: true
        });

        connections.push({ page, ws: wsConnection });
        wsConnections.push(wsConnection);

        // Small delay between connections
        await page.waitForTimeout(100);
      }

      // Verify all connections are established
      await Promise.all(connections.map(async ({ page }) => {
        await page.waitForTimeout(2000);
      }));

      for (const { ws } of connections) {
        expect(ws.readyState).toBe(WebSocket.OPEN);
      }

      // Test broadcast message to all connections
      const testMessage = { type: 'system_announcement', message: 'Scale test message' };
      
      // Send message from first connection
      connections[0].ws.send(JSON.stringify(testMessage));

      // Wait for message propagation
      await connections[0].page.waitForTimeout(2000);

      // All connections should receive the broadcast
      // (This would be verified through UI indicators in a real test)
      for (const { page } of connections) {
        await expect(page.locator('[data-testid="system-announcement"]')).toContainText('Scale test message');
      }

    } finally {
      // Cleanup all connections
      for (const { page, ws } of connections) {
        ws.close();
        await page.close();
      }
    }
  });
});

test.describe('Real-time Notifications', () => {
  let testTenantId: string;

  test.beforeAll(async () => {
    const tenant = await createTestTenant({
      name: 'Notification Test Corp',
      realtimeEnabled: true
    });
    testTenantId = tenant.id;
  });

  test.afterAll(async () => {
    await cleanupTestTenant(testTenantId);
  });

  test('Real-time system notifications from Management to Tenant', async ({ page, context }) => {
    // Step 1: Setup tenant WebSocket listener
    const tenantPage = await context.newPage();
    const tenant = await getTenantDetails(testTenantId);
    await tenantPage.goto(`https://${tenant.domain}/login`);

    await authenticateAsTenant(tenantPage, {
      email: `admin@${tenant.domain.replace('.dotmac.app', '')}.com`,
      password: 'tenant123'
    });

    await tenantPage.goto('/dashboard');

    const tenantNotifications: any[] = [];
    await establishWebSocketConnection(tenantPage, {
      url: `wss://${tenant.domain}/ws/tenant`,
      onMessage: (message) => {
        if (message.type === 'notification') {
          tenantNotifications.push(message);
        }
      },
      authentication: true
    });

    // Step 2: Management admin sends notification
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto('/system/notifications');
    await page.click('[data-testid="create-notification"]');

    const notificationTitle = 'Real-time Test Notification';
    const notificationMessage = 'This is a real-time notification test';

    await page.fill('[data-testid="notification-title"]', notificationTitle);
    await page.fill('[data-testid="notification-message"]', notificationMessage);
    await page.selectOption('[data-testid="notification-type"]', 'info');
    await page.check(`[data-testid="target-tenant-${testTenantId}"]`);
    await page.click('[data-testid="send-notification"]');

    // Step 3: Verify real-time delivery
    await tenantPage.waitForTimeout(3000);

    // Check WebSocket message received
    const wsNotification = tenantNotifications.find(n => n.title === notificationTitle);
    expect(wsNotification).toBeTruthy();
    expect(wsNotification.message).toBe(notificationMessage);

    // Check UI updated in real-time
    await expect(tenantPage.locator('[data-testid="notification-toast"]')).toBeVisible();
    await expect(tenantPage.locator('[data-testid="notification-toast"]')).toContainText(notificationTitle);

    // Check notification appears in notification center
    await tenantPage.click('[data-testid="notification-bell"]');
    await expect(tenantPage.locator('[data-testid="notification-dropdown"]')).toContainText(notificationTitle);
  });

  test('Real-time billing and invoice notifications', async ({ page, context }) => {
    // Setup tenant to receive billing notifications
    const tenantPage = await context.newPage();
    const tenant = await getTenantDetails(testTenantId);
    await tenantPage.goto(`https://${tenant.domain}/login`);

    await authenticateAsTenant(tenantPage, {
      email: `admin@${tenant.domain.replace('.dotmac.app', '')}.com`,
      password: 'tenant123'
    });

    await tenantPage.goto('/billing');

    const billingNotifications: any[] = [];
    await establishWebSocketConnection(tenantPage, {
      url: `wss://${tenant.domain}/ws/tenant`,
      onMessage: (message) => {
        if (message.type === 'billing_update') {
          billingNotifications.push(message);
        }
      },
      authentication: true
    });

    // Management generates invoice
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto(`/tenants/${testTenantId}/billing`);
    await page.click('[data-testid="generate-invoice"]');
    await page.fill('[data-testid="invoice-amount"]', '199.99');
    await page.check('[data-testid="send-realtime-notification"]');
    await page.click('[data-testid="confirm-generate-invoice"]');

    const invoiceNumber = await page.locator('[data-testid="invoice-number"]').textContent();

    // Verify real-time billing notification
    await tenantPage.waitForTimeout(5000);

    const billingUpdate = billingNotifications.find(n => n.invoice_number === invoiceNumber);
    expect(billingUpdate).toBeTruthy();
    expect(billingUpdate.amount).toBe('199.99');
    expect(billingUpdate.status).toBe('pending');

    // Check UI updated without refresh
    await expect(tenantPage.locator('[data-testid="new-invoice-alert"]')).toBeVisible();
    await expect(tenantPage.locator('[data-testid="new-invoice-alert"]')).toContainText(invoiceNumber!);
    
    // Invoice should appear in billing list
    await expect(tenantPage.locator(`[data-testid="invoice-${invoiceNumber}"]`)).toBeVisible();
  });

  test('Real-time license and feature access updates', async ({ page, context }) => {
    const tenantPage = await context.newPage();
    const tenant = await getTenantDetails(testTenantId);
    await tenantPage.goto(`https://${tenant.domain}/dashboard`);

    await authenticateAsTenant(tenantPage, {
      email: `admin@${tenant.domain.replace('.dotmac.app', '')}.com`,
      password: 'tenant123'
    });

    const featureUpdates: any[] = [];
    await establishWebSocketConnection(tenantPage, {
      url: `wss://${tenant.domain}/ws/tenant`,
      onMessage: (message) => {
        if (message.type === 'feature_access_updated') {
          featureUpdates.push(message);
        }
      },
      authentication: true
    });

    // Management admin adds new feature
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto(`/tenants/${testTenantId}/features`);
    await page.check('[data-testid="feature-advanced-analytics"]');
    await page.check('[data-testid="feature-ai-insights"]');
    await page.click('[data-testid="update-features"]');

    // Verify real-time feature update
    await tenantPage.waitForTimeout(3000);

    const featureUpdate = featureUpdates.find(u => u.features.includes('advanced_analytics'));
    expect(featureUpdate).toBeTruthy();
    expect(featureUpdate.features).toContain('advanced_analytics');
    expect(featureUpdate.features).toContain('ai_insights');

    // Menu items should appear without page refresh
    await expect(tenantPage.locator('[data-testid="menu-advanced-analytics"]')).toBeVisible();
    await expect(tenantPage.locator('[data-testid="menu-ai-insights"]')).toBeVisible();

    // Features should be immediately accessible
    await tenantPage.click('[data-testid="menu-advanced-analytics"]');
    await expect(tenantPage).toHaveURL(/.*\/analytics\/advanced/);
    await expect(tenantPage.locator('[data-testid="advanced-analytics-dashboard"]')).toBeVisible();
  });
});

test.describe('Multi-User Real-time Collaboration', () => {
  let testTenantId: string;

  test.beforeAll(async () => {
    const tenant = await createTestTenant({
      name: 'Collaboration Test Corp',
      realtimeEnabled: true,
      users: [
        { email: 'user1@collabtest.com', role: 'admin' },
        { email: 'user2@collabtest.com', role: 'manager' },
        { email: 'user3@collabtest.com', role: 'user' }
      ]
    });
    testTenantId = tenant.id;
  });

  test.afterAll(async () => {
    await cleanupTestTenant(testTenantId);
  });

  test('Real-time user activity indicators', async ({ browser }) => {
    const tenant = await getTenantDetails(testTenantId);
    const contexts = await Promise.all([
      browser.newContext(),
      browser.newContext(),
      browser.newContext()
    ]);

    const users = [
      { email: 'user1@collabtest.com', context: contexts[0] },
      { email: 'user2@collabtest.com', context: contexts[1] },
      { email: 'user3@collabtest.com', context: contexts[2] }
    ];

    const pages = await Promise.all(
      users.map(async (user) => {
        const page = await user.context.newPage();
        await page.goto(`https://${tenant.domain}/login`);
        
        await authenticateAsTenant(page, {
          email: user.email,
          password: 'tenant123'
        });

        await page.goto('/dashboard');
        return page;
      })
    );

    // Establish WebSocket connections for all users
    const wsConnections = await Promise.all(
      pages.map(async (page) => {
        return await establishWebSocketConnection(page, {
          url: `wss://${tenant.domain}/ws/tenant`,
          onMessage: () => {}, // We'll check UI indicators instead
          authentication: true
        });
      })
    );

    // Wait for all connections to establish
    await pages[0].waitForTimeout(3000);

    // Verify active users indicator shows 3 users online
    for (const page of pages) {
      await expect(page.locator('[data-testid="active-users-count"]')).toContainText('3');
      await expect(page.locator('[data-testid="online-users-list"]')).toContainText('user1@collabtest.com');
      await expect(page.locator('[data-testid="online-users-list"]')).toContainText('user2@collabtest.com');
      await expect(page.locator('[data-testid="online-users-list"]')).toContainText('user3@collabtest.com');
    }

    // User 1 navigates to different page
    await pages[0].goto('/customers');

    // Wait for activity update
    await pages[1].waitForTimeout(2000);

    // Other users should see User 1's activity
    await expect(pages[1].locator('[data-testid="user-activity"]')).toContainText('user1@collabtest.com is viewing customers');

    // Cleanup
    wsConnections.forEach(ws => ws.close());
    await Promise.all(contexts.map(context => context.close()));
  });

  test('Real-time shared document editing', async ({ browser }) => {
    const tenant = await getTenantDetails(testTenantId);
    const context1 = await browser.newContext();
    const context2 = await browser.newContext();

    const page1 = await context1.newPage();
    const page2 = await context2.newPage();

    // Both users login and navigate to shared document
    await Promise.all([
      (async () => {
        await page1.goto(`https://${tenant.domain}/login`);
        await authenticateAsTenant(page1, {
          email: 'user1@collabtest.com',
          password: 'tenant123'
        });
        await page1.goto('/documents/shared-notes');
      })(),
      (async () => {
        await page2.goto(`https://${tenant.domain}/login`);
        await authenticateAsTenant(page2, {
          email: 'user2@collabtest.com',
          password: 'tenant123'
        });
        await page2.goto('/documents/shared-notes');
      })()
    ]);

    // Establish collaborative editing connections
    const editorMessages1: any[] = [];
    const editorMessages2: any[] = [];

    await Promise.all([
      establishWebSocketConnection(page1, {
        url: `wss://${tenant.domain}/ws/collaborative-editor`,
        onMessage: (msg) => editorMessages1.push(msg),
        authentication: true
      }),
      establishWebSocketConnection(page2, {
        url: `wss://${tenant.domain}/ws/collaborative-editor`,
        onMessage: (msg) => editorMessages2.push(msg),
        authentication: true
      })
    ]);

    await page1.waitForTimeout(2000);

    // User 1 types in document
    const testText = 'This is collaborative editing test';
    await page1.locator('[data-testid="document-editor"]').fill(testText);

    // Wait for synchronization
    await page2.waitForTimeout(1000);

    // User 2 should see the text without refresh
    await expect(page2.locator('[data-testid="document-editor"]')).toHaveValue(testText);

    // Check WebSocket messages were exchanged
    const textUpdateMessage1 = editorMessages2.find(msg => msg.type === 'text_update');
    expect(textUpdateMessage1).toBeTruthy();
    expect(textUpdateMessage1.content).toContain(testText);

    // User 2 adds more text
    const additionalText = ' - updated by user2';
    await page2.locator('[data-testid="document-editor"]').fill(testText + additionalText);

    await page1.waitForTimeout(1000);

    // User 1 should see the combined text
    await expect(page1.locator('[data-testid="document-editor"]')).toHaveValue(testText + additionalText);

    // Both users should see active editor indicators
    await expect(page1.locator('[data-testid="active-editors"]')).toContainText('user2@collabtest.com');
    await expect(page2.locator('[data-testid="active-editors"]')).toContainText('user1@collabtest.com');

    await Promise.all([context1.close(), context2.close()]);
  });

  test('Real-time system status and alerts collaboration', async ({ browser }) => {
    const tenant = await getTenantDetails(testTenantId);
    
    // Create multiple admin users to test alert collaboration
    const contexts = await Promise.all([
      browser.newContext(),
      browser.newContext()
    ]);

    const [adminPage, managerPage] = await Promise.all([
      contexts[0].newPage(),
      contexts[1].newPage()
    ]);

    await Promise.all([
      (async () => {
        await adminPage.goto(`https://${tenant.domain}/login`);
        await authenticateAsTenant(adminPage, {
          email: 'user1@collabtest.com', // admin role
          password: 'tenant123'
        });
        await adminPage.goto('/system/monitoring');
      })(),
      (async () => {
        await managerPage.goto(`https://${tenant.domain}/login`);
        await authenticateAsTenant(managerPage, {
          email: 'user2@collabtest.com', // manager role
          password: 'tenant123'
        });
        await managerPage.goto('/system/monitoring');
      })()
    ]);

    // Setup real-time monitoring connections
    await Promise.all([
      establishWebSocketConnection(adminPage, {
        url: `wss://${tenant.domain}/ws/system-monitoring`,
        onMessage: () => {},
        authentication: true
      }),
      establishWebSocketConnection(managerPage, {
        url: `wss://${tenant.domain}/ws/system-monitoring`,
        onMessage: () => {},
        authentication: true
      })
    ]);

    await adminPage.waitForTimeout(2000);

    // Simulate system alert
    await adminPage.click('[data-testid="simulate-alert"]');
    await adminPage.selectOption('[data-testid="alert-type"]', 'high_cpu_usage');
    await adminPage.click('[data-testid="trigger-alert"]');

    // Both users should see the alert simultaneously
    await Promise.all([
      expect(adminPage.locator('[data-testid="system-alert"]')).toContainText('High CPU Usage'),
      expect(managerPage.locator('[data-testid="system-alert"]')).toContainText('High CPU Usage')
    ]);

    // Admin acknowledges alert
    await adminPage.click('[data-testid="acknowledge-alert"]');

    // Manager should see acknowledgment status update
    await managerPage.waitForTimeout(1000);
    await expect(managerPage.locator('[data-testid="alert-status"]')).toContainText('Acknowledged by user1@collabtest.com');

    // Manager can see real-time system metrics updates
    const initialCpuValue = await managerPage.locator('[data-testid="cpu-usage-value"]').textContent();
    
    // Wait for metrics update (they should update every few seconds)
    await managerPage.waitForTimeout(5000);
    
    const updatedCpuValue = await managerPage.locator('[data-testid="cpu-usage-value"]').textContent();
    expect(updatedCpuValue).not.toBe(initialCpuValue); // Should have updated

    await Promise.all(contexts.map(context => context.close()));
  });
});

test.describe('WebSocket Performance and Load Testing', () => {
  test('WebSocket latency measurement under normal load', async ({ page }) => {
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto('/dashboard');

    const latencyMeasurements: number[] = [];
    
    const wsConnection = await establishWebSocketConnection(page, {
      url: 'wss://api.dotmac.com/ws/management',
      onMessage: (message) => {
        if (message.type === 'pong' && message.timestamp) {
          const latency = Date.now() - message.timestamp;
          latencyMeasurements.push(latency);
        }
      },
      authentication: true
    });

    // Send ping messages every second for 30 seconds
    for (let i = 0; i < 30; i++) {
      await measureWebSocketLatency(wsConnection);
      await page.waitForTimeout(1000);
    }

    // Calculate average latency
    const averageLatency = latencyMeasurements.reduce((a, b) => a + b, 0) / latencyMeasurements.length;
    const maxLatency = Math.max(...latencyMeasurements);

    // Performance assertions
    expect(averageLatency).toBeLessThan(100); // Average < 100ms
    expect(maxLatency).toBeLessThan(500); // Max < 500ms
    expect(latencyMeasurements.length).toBeGreaterThan(25); // At least 25 successful pings

    console.log(`WebSocket Performance - Avg: ${averageLatency}ms, Max: ${maxLatency}ms`);
    
    wsConnection.close();
  });

  test('Connection stability under message burst', async ({ page }) => {
    await authenticateAsManagementAdmin(page, {
      email: 'admin@dotmac.com',
      password: 'admin123'
    });

    await page.goto('/dashboard');

    let messagesReceived = 0;
    let connectionLost = false;

    const wsConnection = await establishWebSocketConnection(page, {
      url: 'wss://api.dotmac.com/ws/management',
      onMessage: () => messagesReceived++,
      onClose: () => connectionLost = true,
      authentication: true
    });

    // Send burst of messages (100 messages rapidly)
    for (let i = 0; i < 100; i++) {
      wsConnection.send(JSON.stringify({
        type: 'test_message',
        id: i,
        data: 'A'.repeat(1000) // 1KB message
      }));
    }

    // Wait for processing
    await page.waitForTimeout(5000);

    // Connection should remain stable
    expect(connectionLost).toBe(false);
    expect(wsConnection.readyState).toBe(WebSocket.OPEN);
    expect(messagesReceived).toBeGreaterThan(0);

    wsConnection.close();
  });
});

// Helper function to get tenant details
async function getTenantDetails(tenantId: string) {
  return {
    id: tenantId,
    domain: `tenant-${tenantId}.dotmac.app`
  };
}