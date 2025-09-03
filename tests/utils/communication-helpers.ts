/**
 * Communication Helpers
 * 
 * Utilities for testing communication between Management Platform
 * and Tenant Containers, including WebSocket connections, event
 * propagation, and real-time notifications.
 */

import { Page, BrowserContext } from '@playwright/test';

export interface CommunicationEvent {
  type: string;
  source: 'management' | 'tenant';
  target?: 'management' | 'tenant' | 'broadcast';
  data: any;
  timestamp: number;
}

export interface EventPropagationConfig {
  expectedDelay?: number;
  maxRetries?: number;
  retryInterval?: number;
}

/**
 * Wait for event propagation between management and tenant systems
 */
export async function waitForEventPropagation(
  delayMs: number = 3000,
  config: EventPropagationConfig = {}
): Promise<void> {
  const {
    expectedDelay = delayMs,
    maxRetries = 3,
    retryInterval = 1000
  } = config;

  let attempt = 0;
  while (attempt < maxRetries) {
    try {
      await new Promise(resolve => setTimeout(resolve, expectedDelay));
      return;
    } catch (error) {
      attempt++;
      if (attempt >= maxRetries) {
        throw new Error(`Event propagation failed after ${maxRetries} attempts: ${error}`);
      }
      await new Promise(resolve => setTimeout(resolve, retryInterval));
    }
  }
}

/**
 * Monitor WebSocket messages for communication testing
 */
export async function monitorWebSocketMessages(
  page: Page,
  duration: number = 30000
): Promise<any[]> {
  const messages: any[] = [];
  
  // Listen for WebSocket messages
  await page.evaluateOnNewDocument(() => {
    const originalWebSocket = window.WebSocket;
    window.WebSocket = class extends originalWebSocket {
      constructor(url: string, protocols?: string | string[]) {
        super(url, protocols);
        
        const originalOnMessage = this.onmessage;
        this.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            (window as any)._webSocketMessages = (window as any)._webSocketMessages || [];
            (window as any)._webSocketMessages.push({
              url,
              data,
              timestamp: Date.now()
            });
          } catch (e) {
            // Ignore non-JSON messages
          }
          
          if (originalOnMessage) {
            originalOnMessage.call(this, event);
          }
        };
      }
    };
  });

  // Wait for the specified duration
  await page.waitForTimeout(duration);

  // Extract collected messages
  const collectedMessages = await page.evaluate(() => {
    return (window as any)._webSocketMessages || [];
  });

  return collectedMessages;
}

/**
 * Mock WebSocket connection for testing
 */
export async function mockWebSocketConnection(
  context: BrowserContext,
  messageHandler?: (message: any) => void
): Promise<void> {
  await context.addInitScript((handler) => {
    class MockWebSocket extends EventTarget {
      public readyState: number = WebSocket.CONNECTING;
      public url: string;
      public onopen: ((event: Event) => any) | null = null;
      public onclose: ((event: CloseEvent) => any) | null = null;
      public onmessage: ((event: MessageEvent) => any) | null = null;
      public onerror: ((event: Event) => any) | null = null;

      constructor(url: string) {
        super();
        this.url = url;
        
        // Simulate connection opening
        setTimeout(() => {
          this.readyState = WebSocket.OPEN;
          if (this.onopen) {
            this.onopen(new Event('open'));
          }
        }, 100);
      }

      send(data: string): void {
        if (this.readyState !== WebSocket.OPEN) {
          throw new Error('WebSocket is not open');
        }

        // Simulate server response
        setTimeout(() => {
          try {
            const message = JSON.parse(data);
            const response = {
              type: 'response',
              originalType: message.type,
              timestamp: Date.now(),
              data: message
            };

            if (this.onmessage) {
              this.onmessage(new MessageEvent('message', {
                data: JSON.stringify(response)
              }));
            }

            // Call external handler if provided
            if (handler) {
              handler(response);
            }
          } catch (e) {
            console.warn('Failed to parse WebSocket message:', e);
          }
        }, 50);
      }

      close(code?: number, reason?: string): void {
        this.readyState = WebSocket.CLOSED;
        if (this.onclose) {
          this.onclose(new CloseEvent('close', { code, reason }));
        }
      }
    }

    // Replace native WebSocket with mock
    (window as any).WebSocket = MockWebSocket;
    (MockWebSocket as any).CONNECTING = 0;
    (MockWebSocket as any).OPEN = 1;
    (MockWebSocket as any).CLOSING = 2;
    (MockWebSocket as any).CLOSED = 3;
  }, messageHandler?.toString());
}

/**
 * Simulate notification delivery from management to tenant
 */
export async function simulateNotificationDelivery(
  managementPage: Page,
  tenantPage: Page,
  notification: {
    title: string;
    message: string;
    type: 'info' | 'warning' | 'error' | 'success';
    priority: 'low' | 'medium' | 'high' | 'urgent';
  }
): Promise<void> {
  // Send notification from management
  await managementPage.evaluate((notif) => {
    // Simulate WebSocket message to tenant
    const wsMessage = {
      type: 'notification',
      ...notif,
      timestamp: Date.now(),
      id: Math.random().toString(36).substr(2, 9)
    };

    // Store in session storage for tenant to pick up
    sessionStorage.setItem('pending_notification', JSON.stringify(wsMessage));
  }, notification);

  // Simulate tenant receiving notification
  await tenantPage.evaluate(() => {
    const pendingNotif = sessionStorage.getItem('pending_notification');
    if (pendingNotif) {
      const notification = JSON.parse(pendingNotif);
      
      // Trigger notification UI
      const event = new CustomEvent('websocket-notification', {
        detail: notification
      });
      window.dispatchEvent(event);
      
      // Clean up
      sessionStorage.removeItem('pending_notification');
    }
  });
}

/**
 * Test cross-portal communication reliability
 */
export async function testCommunicationReliability(
  managementPage: Page,
  tenantPage: Page,
  testCount: number = 10
): Promise<{
  sent: number;
  received: number;
  failed: number;
  averageLatency: number;
}> {
  const results = {
    sent: 0,
    received: 0,
    failed: 0,
    latencies: [] as number[]
  };

  for (let i = 0; i < testCount; i++) {
    const testMessage = {
      id: `test_${i}`,
      type: 'communication_test',
      data: `Test message ${i}`,
      timestamp: Date.now()
    };

    try {
      // Send from management
      await managementPage.evaluate((msg) => {
        (window as any).testCommunication = (window as any).testCommunication || [];
        (window as any).testCommunication.push(msg);
      }, testMessage);

      results.sent++;

      // Wait for propagation
      await waitForEventPropagation(1000);

      // Check if received in tenant
      const received = await tenantPage.evaluate((msgId) => {
        const messages = (window as any).testCommunication || [];
        return messages.find((m: any) => m.id === msgId);
      }, testMessage.id);

      if (received) {
        results.received++;
        const latency = Date.now() - testMessage.timestamp;
        results.latencies.push(latency);
      } else {
        results.failed++;
      }

    } catch (error) {
      results.failed++;
      console.warn(`Communication test ${i} failed:`, error);
    }
  }

  const averageLatency = results.latencies.length > 0
    ? results.latencies.reduce((a, b) => a + b, 0) / results.latencies.length
    : 0;

  return {
    sent: results.sent,
    received: results.received,
    failed: results.failed,
    averageLatency
  };
}

/**
 * Monitor real-time data synchronization
 */
export async function monitorDataSynchronization(
  pages: Page[],
  dataSelector: string,
  timeout: number = 30000
): Promise<{
  synchronized: boolean;
  syncTime: number;
  values: string[];
}> {
  const startTime = Date.now();
  let synchronized = false;
  let values: string[] = [];

  while (Date.now() - startTime < timeout && !synchronized) {
    // Get current values from all pages
    const currentValues = await Promise.all(
      pages.map(async (page) => {
        try {
          const element = await page.locator(dataSelector).first();
          return await element.textContent() || '';
        } catch {
          return '';
        }
      })
    );

    values = currentValues;

    // Check if all values are the same (synchronized)
    const firstValue = currentValues[0];
    synchronized = currentValues.every(value => value === firstValue && value !== '');

    if (!synchronized) {
      await new Promise(resolve => setTimeout(resolve, 500));
    }
  }

  return {
    synchronized,
    syncTime: Date.now() - startTime,
    values
  };
}

/**
 * Test notification delivery reliability
 */
export async function testNotificationReliability(
  context: BrowserContext,
  tenantDomains: string[],
  notificationCount: number = 5
): Promise<{
  totalSent: number;
  totalReceived: number;
  deliveryRate: number;
  averageDeliveryTime: number;
}> {
  const results = {
    sent: 0,
    received: 0,
    deliveryTimes: [] as number[]
  };

  // Create pages for all tenant domains
  const tenantPages = await Promise.all(
    tenantDomains.map(async (domain) => {
      const page = await context.newPage();
      await page.goto(`https://${domain}/dashboard`);
      return page;
    })
  );

  try {
    for (let i = 0; i < notificationCount; i++) {
      const notification = {
        id: `reliability_test_${i}`,
        title: `Test Notification ${i}`,
        message: `This is test notification number ${i}`,
        timestamp: Date.now(),
        type: 'info' as const
      };

      results.sent++;

      // Send notification to all tenants
      await Promise.all(
        tenantPages.map(async (page) => {
          await page.evaluate((notif) => {
            const event = new CustomEvent('test-notification', {
              detail: notif
            });
            window.dispatchEvent(event);
          }, notification);
        })
      );

      // Wait for delivery
      await waitForEventPropagation(2000);

      // Check delivery on each tenant
      for (const page of tenantPages) {
        try {
          const delivered = await page.evaluate((notifId) => {
            return !!(window as any)[`notification_${notifId}`];
          }, notification.id);

          if (delivered) {
            results.received++;
            results.deliveryTimes.push(Date.now() - notification.timestamp);
          }
        } catch (error) {
          console.warn('Failed to check notification delivery:', error);
        }
      }
    }
  } finally {
    // Cleanup
    await Promise.all(tenantPages.map(page => page.close()));
  }

  const deliveryRate = results.sent > 0 ? (results.received / results.sent) * 100 : 0;
  const averageDeliveryTime = results.deliveryTimes.length > 0
    ? results.deliveryTimes.reduce((a, b) => a + b, 0) / results.deliveryTimes.length
    : 0;

  return {
    totalSent: results.sent,
    totalReceived: results.received,
    deliveryRate,
    averageDeliveryTime
  };
}

/**
 * Create communication load test
 */
export async function createCommunicationLoadTest(
  pages: Page[],
  messagesPerSecond: number,
  durationSeconds: number
): Promise<{
  messagesSent: number;
  messagesReceived: number;
  errors: string[];
  throughput: number;
}> {
  const results = {
    sent: 0,
    received: 0,
    errors: [] as string[]
  };

  const totalMessages = messagesPerSecond * durationSeconds;
  const interval = 1000 / messagesPerSecond;

  const startTime = Date.now();

  for (let i = 0; i < totalMessages; i++) {
    try {
      const message = {
        id: `load_test_${i}`,
        timestamp: Date.now(),
        data: `Load test message ${i}`
      };

      // Send to random page
      const randomPage = pages[Math.floor(Math.random() * pages.length)];
      await randomPage.evaluate((msg) => {
        (window as any).loadTestMessages = (window as any).loadTestMessages || [];
        (window as any).loadTestMessages.push(msg);
      }, message);

      results.sent++;

      // Wait for next message
      if (i < totalMessages - 1) {
        await new Promise(resolve => setTimeout(resolve, interval));
      }

    } catch (error) {
      results.errors.push(`Message ${i}: ${error}`);
    }
  }

  // Wait for processing
  await waitForEventPropagation(5000);

  // Count received messages across all pages
  for (const page of pages) {
    try {
      const receivedCount = await page.evaluate(() => {
        return ((window as any).loadTestMessages || []).length;
      });
      results.received += receivedCount;
    } catch (error) {
      results.errors.push(`Failed to count messages: ${error}`);
    }
  }

  const duration = (Date.now() - startTime) / 1000;
  const throughput = results.sent / duration;

  return {
    messagesSent: results.sent,
    messagesReceived: results.received,
    errors: results.errors,
    throughput
  };
}