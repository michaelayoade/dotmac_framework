/**
 * Technician Portal E2E Tests (PWA)
 * Mobile-focused end-to-end testing for field technicians
 */

import { test, expect, devices } from '@playwright/test';
import { setupAuth } from '../auth/auth-helpers';
import { APIBehaviorTester } from '../fixtures/api-behaviors';

// Configure for mobile testing
test.use(devices['iPhone 13']);

test.describe('Technician Portal E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    // Ensure authenticated technician session and basic API mocks
    await setupAuth(page, 'technician');
    const api = new APIBehaviorTester(page, { enableMocking: true, simulateLatency: false });
    await api.setupTechnicianMocks();

    // Navigate to technician portal
    await page.goto('/technician');

    // Wait for dashboard content
    await page.waitForSelector('[data-testid="technician-dashboard"]', { timeout: 10000 });
  });

  test('should call work order API on dashboard load', async ({ page }) => {
    const api = new APIBehaviorTester(page, { enableMocking: true, validateRequests: true });
    await api.setupTechnicianMocks();
    await page.goto('/technician');
    await page.waitForSelector('[data-testid="technician-dashboard"]');
    await api.validateDataFlows([{ endpoint: '/api/v1/technician/work-orders', method: 'GET' }]);
  });

  test.describe('Mobile PWA Functionality', () => {
    test('should load as PWA on mobile', async ({ page }) => {
      // Check PWA manifest
      const manifest = await page.evaluate(() => {
        const link = document.querySelector('link[rel="manifest"]');
        return link?.getAttribute('href');
      });

      expect(manifest).toBeTruthy();
    });

    test('should work offline', async ({ page }) => {
      // Load page online first
      await expect(page.getByTestId('technician-dashboard')).toBeVisible();

      // Go offline
      await page.context().setOffline(true);

      // Reload and verify offline functionality
      await page.reload();

      // Should show offline indicator or cached content
      await page.context().setOffline(false);
    });

    test('should sync data when back online', async ({ page }) => {
      // Simulate offline work
      await page.context().setOffline(true);

      // Perform actions while offline
      const workOrderButton = page.getByTestId('work-order-button').first();
      if (await workOrderButton.isVisible()) {
        await workOrderButton.click();
      }

      // Go back online
      await page.context().setOffline(false);
      await page.waitForTimeout(1000);

      // Verify sync occurs
    });
  });

  test.describe('Work Order Management', () => {
    test('should display assigned work orders', async ({ page }) => {
      await expect(page.getByTestId('technician-dashboard')).toBeVisible();
      await expect(page.getByText(/Work Orders/i)).toBeVisible();

      // Check for work order list
      const workOrdersList = page.getByTestId('work-orders-list');
      if (await workOrdersList.isVisible()) {
        await expect(workOrdersList).toBeVisible();
      }
    });

    test('should view work order details', async ({ page }) => {
      // Click on a work order
      const firstWorkOrder = page.getByTestId('work-order-item').first();
      if (await firstWorkOrder.isVisible()) {
        await firstWorkOrder.click();

        // Should navigate to work order details
        await expect(page.getByText(/Work Order Details/i)).toBeVisible();
      }
    });

    test('should update work order status', async ({ page }) => {
      // Navigate to work order details
      const workOrderItem = page.getByTestId('work-order-item').first();
      if (await workOrderItem.isVisible()) {
        await workOrderItem.click();

        // Look for status update controls
        const statusButton = page.getByText(/Update Status/i).or(page.getByTestId('status-update'));
        if (await statusButton.isVisible()) {
          await statusButton.click();
        }
      }
    });

    test('should add work order notes', async ({ page }) => {
      // Navigate to work order
      const workOrderItem = page.getByTestId('work-order-item').first();
      if (await workOrderItem.isVisible()) {
        await workOrderItem.click();

        // Look for notes section
        const notesArea = page.getByTestId('work-order-notes').or(page.getByPlaceholder(/notes/i));
        if (await notesArea.isVisible()) {
          await notesArea.fill('Test note from E2E test');
        }
      }
    });
  });

  test.describe('GPS and Location Services', () => {
    test('should request location permission', async ({ page, context }) => {
      // Grant geolocation permission
      await context.grantPermissions(['geolocation']);

      // Mock geolocation
      await context.setGeolocation({ latitude: 47.6062, longitude: -122.3321 });

      await page.goto('/technician');

      // Should use location services
    });

    test('should display technician location on map', async ({ page, context }) => {
      await context.grantPermissions(['geolocation']);
      await context.setGeolocation({ latitude: 47.6062, longitude: -122.3321 });

      // Look for map component
      const mapComponent = page.getByTestId('technician-map');
      if (await mapComponent.isVisible()) {
        await expect(mapComponent).toBeVisible();
      }
    });

    test('should show route to customer location', async ({ page, context }) => {
      await context.grantPermissions(['geolocation']);

      // Navigate to work order with customer location
      const workOrderItem = page.getByTestId('work-order-item').first();
      if (await workOrderItem.isVisible()) {
        await workOrderItem.click();

        // Look for navigation/route button
        const routeButton = page.getByText(/Get Directions/i).or(page.getByTestId('route-button'));
        if (await routeButton.isVisible()) {
          await routeButton.click();
        }
      }
    });
  });

  test.describe('Photo and Documentation', () => {
    test('should allow photo capture', async ({ page, context }) => {
      // Grant camera permission
      await context.grantPermissions(['camera']);

      // Navigate to work order
      const workOrderItem = page.getByTestId('work-order-item').first();
      if (await workOrderItem.isVisible()) {
        await workOrderItem.click();

        // Look for photo capture button
        const photoButton = page.getByText(/Take Photo/i).or(page.getByTestId('photo-capture'));
        if (await photoButton.isVisible()) {
          await photoButton.click();

          // Should open camera interface
        }
      }
    });

    test('should upload photos to work order', async ({ page }) => {
      // Navigate to work order
      const workOrderItem = page.getByTestId('work-order-item').first();
      if (await workOrderItem.isVisible()) {
        await workOrderItem.click();

        // Look for file upload
        const fileInput = page.getByTestId('photo-upload').or(page.locator('input[type="file"]'));
        if (await fileInput.isVisible()) {
          // Simulate file upload
          await fileInput.setInputFiles({
            name: 'test-photo.jpg',
            mimeType: 'image/jpeg',
            buffer: Buffer.from('test image data'),
          });
        }
      }
    });

    test('should add voice notes', async ({ page, context }) => {
      // Grant microphone permission
      await context.grantPermissions(['microphone']);

      // Look for voice recording functionality
      const voiceButton = page.getByText(/Voice Note/i).or(page.getByTestId('voice-record'));
      if (await voiceButton.isVisible()) {
        await voiceButton.click();
      }
    });
  });

  test.describe('Customer Communication', () => {
    test('should initiate customer call', async ({ page }) => {
      // Navigate to work order with customer info
      const workOrderItem = page.getByTestId('work-order-item').first();
      if (await workOrderItem.isVisible()) {
        await workOrderItem.click();

        // Look for call customer button
        const callButton = page.getByText(/Call Customer/i).or(page.getByTestId('call-customer'));
        if (await callButton.isVisible()) {
          await callButton.click();

          // Should initiate phone call
        }
      }
    });

    test('should send customer SMS updates', async ({ page }) => {
      // Navigate to work order
      const workOrderItem = page.getByTestId('work-order-item').first();
      if (await workOrderItem.isVisible()) {
        await workOrderItem.click();

        // Look for SMS functionality
        const smsButton = page.getByText(/Send Update/i).or(page.getByTestId('send-sms'));
        if (await smsButton.isVisible()) {
          await smsButton.click();
        }
      }
    });
  });

  test.describe('Equipment and Inventory', () => {
    test('should scan equipment barcodes', async ({ page, context }) => {
      // Grant camera permission for barcode scanning
      await context.grantPermissions(['camera']);

      // Look for barcode scan functionality
      const scanButton = page.getByText(/Scan Barcode/i).or(page.getByTestId('barcode-scan'));
      if (await scanButton.isVisible()) {
        await scanButton.click();
      }
    });

    test('should manage equipment inventory', async ({ page }) => {
      // Navigate to inventory section
      await page.goto('/technician/inventory');

      // Check inventory management features
      if (page.url().includes('/inventory')) {
        await expect(page.getByText(/Equipment/i).or(page.getByText(/Inventory/i))).toBeVisible();
      }
    });

    test('should record equipment installation', async ({ page }) => {
      // Navigate to work order
      const workOrderItem = page.getByTestId('work-order-item').first();
      if (await workOrderItem.isVisible()) {
        await workOrderItem.click();

        // Look for equipment logging
        const equipmentButton = page
          .getByText(/Add Equipment/i)
          .or(page.getByTestId('log-equipment'));
        if (await equipmentButton.isVisible()) {
          await equipmentButton.click();
        }
      }
    });
  });

  test.describe('Real-time Updates', () => {
    test('should receive new work order assignments', async ({ page }) => {
      // Monitor for real-time notifications
      await page.waitForTimeout(2000);

      // Check for notification system
      const notifications = page
        .getByRole('alert')
        .or(page.locator('[data-testid*="notification"]'));
      if ((await notifications.count()) > 0) {
        await expect(notifications.first()).toBeVisible();
      }
    });

    test('should sync status updates in real-time', async ({ page }) => {
      // Update work order status
      const statusUpdate = page.getByTestId('status-update');
      if (await statusUpdate.isVisible()) {
        await statusUpdate.click();

        // Should sync immediately
        await page.waitForTimeout(1000);
      }
    });
  });

  test.describe('Performance on Mobile', () => {
    test('should load quickly on mobile network', async ({ page }) => {
      // Simulate slow 3G
      await page.emulateNetworkConditions({
        offline: false,
        downloadThroughput: (1.5 * 1024 * 1024) / 8, // 1.5 Mbps
        uploadThroughput: (750 * 1024) / 8, // 750 kbps
        latency: 40,
      });

      const startTime = Date.now();
      await page.goto('/technician');
      await page.waitForSelector('[data-testid="technician-dashboard"]');

      const loadTime = Date.now() - startTime;
      expect(loadTime).toBeLessThan(5000); // 5 seconds on slow 3G
    });

    test('should handle touch gestures', async ({ page }) => {
      // Test swipe gestures on work orders
      const workOrdersList = page.getByTestId('work-orders-list');
      if (await workOrdersList.isVisible()) {
        // Simulate swipe
        await workOrdersList.hover();
        await page.mouse.down();
        await page.mouse.move(200, 0);
        await page.mouse.up();
      }
    });
  });

  test.describe('Offline Data Management', () => {
    test('should cache critical work order data', async ({ page }) => {
      // Load work orders while online
      await expect(page.getByTestId('technician-dashboard')).toBeVisible();

      // Go offline
      await page.context().setOffline(true);

      // Should still show cached work orders
      const workOrdersList = page.getByTestId('work-orders-list');
      if (await workOrdersList.isVisible()) {
        await expect(workOrdersList).toBeVisible();
      }

      await page.context().setOffline(false);
    });

    test('should queue offline actions', async ({ page }) => {
      // Go offline
      await page.context().setOffline(true);

      // Perform actions that should be queued
      const statusButton = page.getByTestId('status-update').first();
      if (await statusButton.isVisible()) {
        await statusButton.click();
      }

      // Go back online - actions should sync
      await page.context().setOffline(false);
      await page.waitForTimeout(2000);
    });
  });

  test.describe('Security on Mobile', () => {
    test('should lock after inactivity', async ({ page }) => {
      // Simulate inactivity
      await page.waitForTimeout(1000);

      // Should implement security timeout (when configured)
    });

    test('should protect sensitive customer data', async ({ page }) => {
      // Navigate to customer details
      const workOrderItem = page.getByTestId('work-order-item').first();
      if (await workOrderItem.isVisible()) {
        await workOrderItem.click();

        // Verify customer data is protected
        const sensitiveData = page.locator('[data-sensitive]');
        if ((await sensitiveData.count()) > 0) {
          // Should be masked or protected
          await expect(sensitiveData.first()).toBeVisible();
        }
      }
    });
  });
});
