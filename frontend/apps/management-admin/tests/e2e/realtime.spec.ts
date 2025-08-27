import { test, expect, type Page } from '@playwright/test';

test.describe('Real-time Features', () => {
  test.beforeEach(async ({ page }) => {
    // Login first
    await page.goto('/login');
    await page.fill('input[type="email"]', 'admin@dotmac.com');
    await page.fill('input[type="password"]', 'admin123');
    await page.click('button[type="submit"]');
    
    // Mock WebSocket connection
    await page.addInitScript(() => {
      class MockWebSocket extends EventTarget {
        readyState = WebSocket.OPEN;
        url: string;
        
        constructor(url: string) {
          super();
          this.url = url;
          // Simulate successful connection
          setTimeout(() => {
            this.dispatchEvent(new Event('open'));
          }, 100);
        }
        
        send(data: string) {
          // Echo back for testing
          setTimeout(() => {
            this.dispatchEvent(new MessageEvent('message', {
              data: JSON.stringify({
                type: 'pong',
                payload: { timestamp: Date.now() },
                id: 'test-msg-' + Date.now(),
                timestamp: new Date().toISOString()
              })
            }));
          }, 50);
        }
        
        close() {
          this.dispatchEvent(new CloseEvent('close', { code: 1000, reason: 'Normal close' }));
        }
      }
      
      (window as any).WebSocket = MockWebSocket;
    });
  });

  test('should display real-time dashboard', async ({ page }) => {
    await page.goto('/realtime');
    
    await expect(page.locator('h1')).toContainText('Real-time Dashboard');
    await expect(page.locator('[data-testid="connection-status"]')).toBeVisible();
    await expect(page.locator('[data-testid="metrics-grid"]')).toBeVisible();
  });

  test('should show WebSocket connection status', async ({ page }) => {
    await page.goto('/realtime');
    
    // Should show connection indicator
    const connectionStatus = page.locator('[data-testid="connection-status"]');
    await expect(connectionStatus).toBeVisible();
    
    // Should show as connected
    await expect(connectionStatus.locator('text=Connected')).toBeVisible();
    await expect(connectionStatus.locator('.text-green-500')).toBeVisible(); // Green indicator
  });

  test('should display WebSocket statistics', async ({ page }) => {
    await page.goto('/realtime');
    
    const statsSection = page.locator('[data-testid="connection-stats"]');
    if (await statsSection.isVisible()) {
      await expect(statsSection.locator('text=Active Subscriptions')).toBeVisible();
      await expect(statsSection.locator('text=Reconnect Attempts')).toBeVisible();
      await expect(statsSection.locator('text=Queued Messages')).toBeVisible();
    }
  });

  test('should handle manual connection control', async ({ page }) => {
    await page.goto('/realtime');
    
    // Should have connect/disconnect buttons
    const disconnectBtn = page.locator('button:has-text("Disconnect")');
    const connectBtn = page.locator('button:has-text("Connect")');
    
    // Initially connected, so disconnect should be enabled
    await expect(disconnectBtn).toBeEnabled();
    await expect(connectBtn).toBeDisabled();
    
    // Click disconnect
    await disconnectBtn.click();
    
    // Should update button states
    await expect(disconnectBtn).toBeDisabled();
    await expect(connectBtn).toBeEnabled();
  });

  test('should display real-time metrics when connected', async ({ page }) => {
    await page.goto('/realtime');
    
    // Mock real-time metrics data
    await page.evaluate(() => {
      // Simulate receiving metrics update
      const mockMetrics = [
        {
          name: 'Active Users',
          value: 1234,
          change: 5.2,
          trend: 'up' as const,
          lastUpdated: new Date().toISOString()
        },
        {
          name: 'System Load',
          value: '67%',
          change: -2.1,
          trend: 'down' as const,
          lastUpdated: new Date().toISOString()
        }
      ];
      
      // Dispatch custom event to simulate WebSocket message
      window.dispatchEvent(new CustomEvent('ws-message', {
        detail: {
          type: 'metrics_updated',
          payload: mockMetrics
        }
      }));
    });
    
    // Should display metrics
    await expect(page.locator('text=Active Users')).toBeVisible();
    await expect(page.locator('text=1234')).toBeVisible();
    await expect(page.locator('text=System Load')).toBeVisible();
    await expect(page.locator('text=67%')).toBeVisible();
  });

  test('should show system alerts in real-time', async ({ page }) => {
    await page.goto('/realtime');
    
    const alertsSection = page.locator('[data-testid="system-alerts"]');
    await expect(alertsSection).toBeVisible();
    
    // Mock receiving a new alert
    await page.evaluate(() => {
      const mockAlert = {
        id: 'alert-' + Date.now(),
        type: 'warning',
        title: 'High CPU Usage',
        message: 'Server CPU usage is above 80%',
        timestamp: new Date().toISOString(),
        acknowledged: false
      };
      
      window.dispatchEvent(new CustomEvent('ws-message', {
        detail: {
          type: 'system_alert',
          payload: mockAlert
        }
      }));
    });
    
    // Should display the alert
    await expect(page.locator('text=High CPU Usage')).toBeVisible();
    await expect(page.locator('text=Server CPU usage is above 80%')).toBeVisible();
  });

  test('should acknowledge system alerts', async ({ page }) => {
    await page.goto('/realtime');
    
    // Mock an unacknowledged alert
    await page.evaluate(() => {
      window.dispatchEvent(new CustomEvent('ws-message', {
        detail: {
          type: 'system_alert',
          payload: {
            id: 'alert-123',
            type: 'warning',
            title: 'Test Alert',
            message: 'This is a test alert',
            timestamp: new Date().toISOString(),
            acknowledged: false
          }
        }
      }));
    });
    
    await expect(page.locator('text=Test Alert')).toBeVisible();
    
    // Should have acknowledge button
    const acknowledgeBtn = page.locator('button:has-text("Acknowledge")');
    await expect(acknowledgeBtn).toBeVisible();
    
    await acknowledgeBtn.click();
    
    // Button should disappear after acknowledgment
    await expect(acknowledgeBtn).not.toBeVisible();
  });

  test('should display live activity feed', async ({ page }) => {
    await page.goto('/realtime');
    
    const activityFeed = page.locator('[data-testid="activity-feed"]');
    await expect(activityFeed).toBeVisible();
    
    // Mock user activity
    await page.evaluate(() => {
      const mockActivity = {
        userId: 'user123',
        userName: 'John Doe',
        action: 'Created new tenant "Acme Corp"',
        timestamp: new Date().toISOString(),
        metadata: { tenantId: 'tenant123' }
      };
      
      window.dispatchEvent(new CustomEvent('ws-message', {
        detail: {
          type: 'activity_log',
          payload: mockActivity
        }
      }));
    });
    
    // Should show activity
    await expect(page.locator('text=John Doe')).toBeVisible();
    await expect(page.locator('text=Created new tenant "Acme Corp"')).toBeVisible();
  });

  test('should handle connection errors gracefully', async ({ page }) => {
    // Override WebSocket to simulate connection error
    await page.addInitScript(() => {
      class FailingWebSocket extends EventTarget {
        readyState = WebSocket.CLOSED;
        
        constructor(url: string) {
          super();
          setTimeout(() => {
            this.dispatchEvent(new Event('error'));
            this.dispatchEvent(new CloseEvent('close', { code: 1006, reason: 'Connection failed' }));
          }, 100);
        }
        
        send() {}
        close() {}
      }
      
      (window as any).WebSocket = FailingWebSocket;
    });
    
    await page.goto('/realtime');
    
    // Should show disconnected state
    await expect(page.locator('text=Disconnected')).toBeVisible();
    await expect(page.locator('.text-red-500')).toBeVisible(); // Red indicator
  });

  test('should show reconnection attempts', async ({ page }) => {
    // Simulate WebSocket that fails initially then succeeds
    await page.addInitScript(() => {
      let attempts = 0;
      
      class ReconnectingWebSocket extends EventTarget {
        readyState: number = 3; // WebSocket.CLOSED
        
        constructor(url: string) {
          super();
          attempts++;
          
          if (attempts < 3) {
            // Fail first few attempts
            setTimeout(() => {
              this.dispatchEvent(new Event('error'));
              this.dispatchEvent(new CloseEvent('close', { code: 1006, reason: 'Connection failed' }));
            }, 100);
          } else {
            // Succeed on 3rd attempt
            this.readyState = 1; // WebSocket.OPEN
            setTimeout(() => {
              this.dispatchEvent(new Event('open'));
            }, 100);
          }
        }
        
        send() {}
        close() {}
      }
      
      (window as any).WebSocket = ReconnectingWebSocket;
    });
    
    await page.goto('/realtime');
    
    // Should show reconnecting status
    await expect(page.locator('text=Reconnecting')).toBeVisible();
    
    // Eventually should connect
    await expect(page.locator('text=Connected')).toBeVisible({ timeout: 10000 });
  });

  test('should limit the number of displayed items', async ({ page }) => {
    await page.goto('/realtime');
    
    // Simulate receiving many alerts
    await page.evaluate(() => {
      for (let i = 0; i < 15; i++) {
        window.dispatchEvent(new CustomEvent('ws-message', {
          detail: {
            type: 'system_alert',
            payload: {
              id: `alert-${i}`,
              type: 'info',
              title: `Alert ${i}`,
              message: `This is alert number ${i}`,
              timestamp: new Date().toISOString(),
              acknowledged: false
            }
          }
        }));
      }
    });
    
    // Should only show the last 10 alerts (as per component logic)
    const alertItems = page.locator('[data-testid="alert-item"]');
    const count = await alertItems.count();
    expect(count).toBeLessThanOrEqual(10);
  });
});