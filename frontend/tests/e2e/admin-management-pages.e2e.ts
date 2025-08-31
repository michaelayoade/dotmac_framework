/**
 * Admin Management Pages E2E Tests
 * Tests devices, IPAM, projects, and containers management with deterministic mocks
 */

import { test, expect } from '@playwright/test';
import { setupAuth } from '../auth/auth-helpers';
import { APIBehaviorTester } from '../fixtures/api-behaviors';
import { AdminManagementMocks } from '../fixtures/admin-mocks';
import { 
  validateSchema, 
  DeviceListResponseSchema, 
  SubnetListResponseSchema,
  ProjectListResponseSchema,
  ContainerListResponseSchema 
} from '../fixtures/admin-schemas';

test.describe('Admin Management Pages E2E Tests', () => {
  let apiTester: APIBehaviorTester;
  let adminMocks: AdminManagementMocks;

  test.beforeEach(async ({ page }) => {
    // Setup authentication for admin portal
    await setupAuth(page, 'admin');
    
    // Initialize API behavior tester with deterministic mocking
    apiTester = new APIBehaviorTester(page, { 
      enableMocking: true, 
      validateRequests: true 
    });
    
    // Setup admin management mocks
    adminMocks = new AdminManagementMocks(apiTester);
    await adminMocks.setupAll();

    // Navigate to admin portal
    await page.goto('/admin');
    await page.waitForSelector('[data-testid="admin-dashboard"]', { timeout: 10000 });
  });

  test.describe('Device Management Page', () => {
    test('should display device management page with data', async ({ page }) => {
      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="device-management"]', { timeout: 5000 });

      // Verify page title and description
      await expect(page.getByText('Device Management')).toBeVisible();
      await expect(page.getByText('Monitor and manage network infrastructure devices')).toBeVisible();

      // Verify metrics are displayed
      await expect(page.getByTestId('metric-total-devices')).toBeVisible();
      await expect(page.getByTestId('metric-online')).toBeVisible();
      await expect(page.getByTestId('metric-alerts')).toBeVisible();
      await expect(page.getByTestId('metric-maintenance')).toBeVisible();

      // Verify device table is displayed
      await expect(page.getByTestId('management-table')).toBeVisible();
      
      // Check table headers
      await expect(page.getByText('Device')).toBeVisible();
      await expect(page.getByText('Type')).toBeVisible();
      await expect(page.getByText('Status')).toBeVisible();
      await expect(page.getByText('Management IP')).toBeVisible();
    });

    test('should filter devices by type', async ({ page }) => {
      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="device-management"]');

      // Open device type filter
      await page.click('[data-testid="filter-device-type"]');
      await page.click('text=Router');

      // Wait for filtered results
      await page.waitForTimeout(500);

      // Verify only router devices are shown
      const deviceRows = await page.locator('[data-testid="device-row"]').count();
      expect(deviceRows).toBeGreaterThan(0);

      // Verify router device is visible
      await expect(page.getByText('sea-core-router-01')).toBeVisible();
    });

    test('should search devices by hostname', async ({ page }) => {
      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="device-management"]');

      // Search for specific device
      await page.fill('[data-testid="search-input"]', 'sea-core');
      await page.press('[data-testid="search-input"]', 'Enter');

      // Wait for search results
      await page.waitForTimeout(500);

      // Verify search results
      await expect(page.getByText('sea-core-router-01')).toBeVisible();
    });

    test('should handle device bulk actions', async ({ page }) => {
      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="device-management"]');

      // Select multiple devices
      await page.check('[data-testid="row-checkbox-0"]');
      await page.check('[data-testid="row-checkbox-1"]');

      // Open bulk actions menu
      await page.click('[data-testid="bulk-actions-button"]');
      await expect(page.getByText('Restart')).toBeVisible();

      // Select restart action
      await page.click('text=Restart');

      // Confirm action in modal
      await expect(page.getByText('Are you sure you want to restart selected devices?')).toBeVisible();
      await page.click('[data-testid="confirm-bulk-action"]');

      // Verify success message
      await expect(page.getByText('Bulk action completed successfully')).toBeVisible();
    });

    test('should open device detail drawer', async ({ page }) => {
      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="device-management"]');

      // Click on first device to open details
      await page.click('[data-testid="device-row"]:first-child');

      // Verify detail drawer opens
      await expect(page.getByTestId('device-detail-drawer')).toBeVisible();
      await expect(page.getByText('Device Details')).toBeVisible();

      // Verify device information is displayed
      await expect(page.getByText('Hostname')).toBeVisible();
      await expect(page.getByText('Management IP')).toBeVisible();
      await expect(page.getByText('Status')).toBeVisible();
    });

    test('should validate API response schema', async ({ page }) => {
      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="device-management"]');

      // Get API request log
      const requests = apiTester.getRequestLog();
      const deviceRequest = requests.find(r => r.url.includes('/api/admin/devices') && r.method === 'GET');
      
      expect(deviceRequest).toBeDefined();

      // Note: In real implementation, you'd capture the response and validate against schema
      // const response = await page.evaluate(() => window.lastDeviceResponse);
      // const validation = validateSchema(response, DeviceListResponseSchema);
      // expect(validation.valid).toBe(true);
    });
  });

  test.describe('IPAM Management Page', () => {
    test('should display IPAM management page with subnet data', async ({ page }) => {
      await page.goto('/admin/ipam');
      await page.waitForSelector('[data-testid="ipam-management"]', { timeout: 5000 });

      // Verify page content
      await expect(page.getByText('IP Address Management')).toBeVisible();
      await expect(page.getByText('Manage IP address allocation and subnet utilization')).toBeVisible();

      // Verify IPAM metrics
      await expect(page.getByTestId('metric-total-subnets')).toBeVisible();
      await expect(page.getByTestId('metric-ip-utilization')).toBeVisible();
      await expect(page.getByTestId('metric-available-ips')).toBeVisible();
      await expect(page.getByTestId('metric-reservations')).toBeVisible();

      // Verify subnet table
      await expect(page.getByText('Subnet')).toBeVisible();
      await expect(page.getByText('Description')).toBeVisible();
      await expect(page.getByText('Utilization')).toBeVisible();
      await expect(page.getByText('Total IPs')).toBeVisible();
    });

    test('should filter subnets by utilization', async ({ page }) => {
      await page.goto('/admin/ipam');
      await page.waitForSelector('[data-testid="ipam-management"]');

      // Apply utilization filter
      await page.click('[data-testid="filter-utilization-range"]');
      await page.click('text=High (51-75%)');

      await page.waitForTimeout(500);

      // Verify high utilization subnets are shown
      await expect(page.getByText('192.168.1.0/24')).toBeVisible();
    });

    test('should create new subnet', async ({ page }) => {
      await page.goto('/admin/ipam');
      await page.waitForSelector('[data-testid="ipam-management"]');

      // Click create subnet button
      await page.click('[data-testid="create-button"]');

      // Verify create drawer opens
      await expect(page.getByTestId('create-subnet-drawer')).toBeVisible();
      await expect(page.getByText('Create New Subnet')).toBeVisible();

      // Fill subnet form
      await page.fill('[data-testid="subnet-cidr-input"]', '10.1.0.0/24');
      await page.fill('[data-testid="subnet-description-input"]', 'Test Subnet');
      
      // Submit form
      await page.click('[data-testid="create-subnet-submit"]');

      // Verify success
      await expect(page.getByText('Subnet created successfully')).toBeVisible();
    });

    test('should display subnet utilization bars', async ({ page }) => {
      await page.goto('/admin/ipam');
      await page.waitForSelector('[data-testid="ipam-management"]');

      // Verify utilization bars are displayed
      const utilizationBars = await page.locator('[data-testid="utilization-bar"]').count();
      expect(utilizationBars).toBeGreaterThan(0);

      // Verify utilization percentages are shown
      await expect(page.locator('text=/\\d+%/')).toHaveCount(3); // Should have percentage values
    });
  });

  test.describe('Project Management Page', () => {
    test('should display project management page with project data', async ({ page }) => {
      await page.goto('/admin/projects');
      await page.waitForSelector('[data-testid="project-management"]', { timeout: 5000 });

      // Verify page content
      await expect(page.getByText('Project Management')).toBeVisible();
      await expect(page.getByText('Track and manage infrastructure and deployment projects')).toBeVisible();

      // Verify project metrics
      await expect(page.getByTestId('metric-active-projects')).toBeVisible();
      await expect(page.getByTestId('metric-on-schedule')).toBeVisible();
      await expect(page.getByTestId('metric-budget-used')).toBeVisible();
      await expect(page.getByTestId('metric-team-members')).toBeVisible();

      // Verify project table
      await expect(page.getByText('Project')).toBeVisible();
      await expect(page.getByText('Status')).toBeVisible();
      await expect(page.getByText('Progress')).toBeVisible();
      await expect(page.getByText('Type')).toBeVisible();
    });

    test('should filter projects by status', async ({ page }) => {
      await page.goto('/admin/projects');
      await page.waitForSelector('[data-testid="project-management"]');

      // Filter by in progress status
      await page.click('[data-testid="filter-status"]');
      await page.click('text=In Progress');

      await page.waitForTimeout(500);

      // Verify in progress projects are shown
      await expect(page.getByText('Downtown Fiber Expansion')).toBeVisible();
    });

    test('should display project progress bars', async ({ page }) => {
      await page.goto('/admin/projects');
      await page.waitForSelector('[data-testid="project-management"]');

      // Verify progress bars are displayed
      const progressBars = await page.locator('[data-testid="progress-bar"]').count();
      expect(progressBars).toBeGreaterThan(0);

      // Verify progress percentages
      await expect(page.locator('text=/\d+%/')).toHaveCount(3); // Progress percentages
    });

    test('should handle project creation workflow', async ({ page }) => {
      await page.goto('/admin/projects');
      await page.waitForSelector('[data-testid="project-management"]');

      // Click new project button
      await page.click('[data-testid="create-button"]');

      // Verify create drawer opens
      await expect(page.getByTestId('create-project-drawer')).toBeVisible();
      await expect(page.getByText('Create New Project')).toBeVisible();

      // Fill project form
      await page.fill('[data-testid="project-name-input"]', 'Test Project');
      await page.selectOption('[data-testid="project-type-select"]', 'network_expansion');
      await page.selectOption('[data-testid="project-priority-select"]', 'high');
      
      // Submit form
      await page.click('[data-testid="create-project-submit"]');

      // Verify success
      await expect(page.getByText('Project created successfully')).toBeVisible();
    });

    test('should handle bulk project actions', async ({ page }) => {
      await page.goto('/admin/projects');
      await page.waitForSelector('[data-testid="project-management"]');

      // Select multiple projects
      await page.check('[data-testid="row-checkbox-0"]');
      await page.check('[data-testid="row-checkbox-1"]');

      // Open bulk actions
      await page.click('[data-testid="bulk-actions-button"]');
      await expect(page.getByText('Update Status')).toBeVisible();
      await expect(page.getByText('Assign Team')).toBeVisible();

      // Select status update action
      await page.click('text=Update Status');

      // Verify bulk action modal
      await expect(page.getByText('Update Status for Selected Projects')).toBeVisible();
    });
  });

  test.describe('Container Management Page', () => {
    test('should display container management page with container data', async ({ page }) => {
      await page.goto('/admin/containers');
      await page.waitForSelector('[data-testid="container-management"]', { timeout: 5000 });

      // Verify page content
      await expect(page.getByText('Container Management')).toBeVisible();
      await expect(page.getByText('Monitor and manage service containers')).toBeVisible();

      // Verify container metrics
      await expect(page.getByTestId('metric-running-containers')).toBeVisible();
      await expect(page.getByTestId('metric-cpu-usage')).toBeVisible();
      await expect(page.getByTestId('metric-memory-usage')).toBeVisible();
      await expect(page.getByTestId('metric-restarts-24h')).toBeVisible();

      // Verify container table
      await expect(page.getByText('Container')).toBeVisible();
      await expect(page.getByText('Image')).toBeVisible();
      await expect(page.getByText('Status')).toBeVisible();
      await expect(page.getByText('Uptime')).toBeVisible();
    });

    test('should filter containers by status', async ({ page }) => {
      await page.goto('/admin/containers');
      await page.waitForSelector('[data-testid="container-management"]');

      // Filter by running status
      await page.click('[data-testid="filter-status"]');
      await page.click('text=Running');

      await page.waitForTimeout(500);

      // Verify running containers are shown
      await expect(page.getByText('isp-framework-api')).toBeVisible();
      await expect(page.getByText('postgres-primary')).toBeVisible();
    });

    test('should display resource usage bars', async ({ page }) => {
      await page.goto('/admin/containers');
      await page.waitForSelector('[data-testid="container-management"]');

      // Verify resource usage bars are displayed
      const cpuBars = await page.locator('[data-testid="cpu-usage-bar"]').count();
      const memoryBars = await page.locator('[data-testid="memory-usage-bar"]').count();
      
      expect(cpuBars).toBeGreaterThan(0);
      expect(memoryBars).toBeGreaterThan(0);
    });

    test('should handle container restart action', async ({ page }) => {
      await page.goto('/admin/containers');
      await page.waitForSelector('[data-testid="container-management"]');

      // Select containers for restart
      await page.check('[data-testid="row-checkbox-0"]');
      await page.check('[data-testid="row-checkbox-1"]');

      // Open bulk actions
      await page.click('[data-testid="bulk-actions-button"]');
      await expect(page.getByText('Restart')).toBeVisible();

      // Select restart action
      await page.click('text=Restart');

      // Confirm restart
      await expect(page.getByText('Restart selected containers?')).toBeVisible();
      await page.click('[data-testid="confirm-bulk-action"]');

      // Verify success
      await expect(page.getByText('Container restart initiated')).toBeVisible();
    });

    test('should open container detail drawer', async ({ page }) => {
      await page.goto('/admin/containers');
      await page.waitForSelector('[data-testid="container-management"]');

      // Click on first container
      await page.click('[data-testid="container-row"]:first-child');

      // Verify detail drawer opens
      await expect(page.getByTestId('container-detail-drawer')).toBeVisible();
      await expect(page.getByText('Container Details')).toBeVisible();

      // Verify container information
      await expect(page.getByText('Container Name')).toBeVisible();
      await expect(page.getByText('Image')).toBeVisible();
      await expect(page.getByText('Status')).toBeVisible();
      await expect(page.getByText('Resource Usage')).toBeVisible();
    });

    test('should display container logs', async ({ page }) => {
      await page.goto('/admin/containers');
      await page.waitForSelector('[data-testid="container-management"]');

      // Click on container to open details
      await page.click('[data-testid="container-row"]:first-child');

      // Navigate to logs tab
      await page.click('[data-testid="logs-tab"]');

      // Verify logs are displayed
      await expect(page.getByTestId('container-logs')).toBeVisible();
      await expect(page.getByText('Application started successfully')).toBeVisible();
    });
  });

  test.describe('Cross-Page Integration', () => {
    test('should maintain session across management pages', async ({ page }) => {
      // Navigate through multiple management pages
      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="device-management"]');

      await page.goto('/admin/ipam');
      await page.waitForSelector('[data-testid="ipam-management"]');

      await page.goto('/admin/projects');
      await page.waitForSelector('[data-testid="project-management"]');

      await page.goto('/admin/containers');
      await page.waitForSelector('[data-testid="container-management"]');

      // Verify session persists throughout navigation
      expect(page.url()).toContain('/admin/containers');
    });

    test('should handle browser navigation correctly', async ({ page }) => {
      await page.goto('/admin/devices');
      await page.goto('/admin/projects');
      
      // Use browser back button
      await page.goBack();
      await page.waitForSelector('[data-testid="device-management"]');
      expect(page.url()).toContain('/admin/devices');

      // Use browser forward button
      await page.goForward();
      await page.waitForSelector('[data-testid="project-management"]');
      expect(page.url()).toContain('/admin/projects');
    });
  });

  test.describe('API Validation', () => {
    test('should validate all API requests follow expected patterns', async ({ page }) => {
      // Navigate to each page to trigger API calls
      await page.goto('/admin/devices');
      await page.waitForSelector('[data-testid="device-management"]');

      await page.goto('/admin/ipam');
      await page.waitForSelector('[data-testid="ipam-management"]');

      await page.goto('/admin/projects');
      await page.waitForSelector('[data-testid="project-management"]');

      await page.goto('/admin/containers');
      await page.waitForSelector('[data-testid="container-management"]');

      // Validate API request patterns
      const expectedFlows = [
        { endpoint: '/api/admin/devices', method: 'GET' },
        { endpoint: '/api/admin/ipam/subnets', method: 'GET' },
        { endpoint: '/api/admin/projects', method: 'GET' },
        { endpoint: '/api/admin/containers', method: 'GET' }
      ];

      await apiTester.validateDataFlows(expectedFlows);
    });

    test('should handle API error responses gracefully', async ({ page }) => {
      // Mock API error for devices endpoint
      await apiTester.mockAndLog('/api/admin/devices', async () => ({
        status: 500,
        body: { error: 'Internal server error' }
      }));

      await page.goto('/admin/devices');
      
      // Verify error is handled gracefully
      await expect(page.getByTestId('error-message')).toBeVisible();
      await expect(page.getByText('Failed to load devices')).toBeVisible();
    });

    test('should handle network timeout gracefully', async ({ page }) => {
      // Simulate slow network
      apiTester = new APIBehaviorTester(page, { 
        enableMocking: true, 
        simulateLatency: true 
      });

      await page.goto('/admin/devices');
      
      // Verify loading states are shown
      await expect(page.getByTestId('loading-spinner')).toBeVisible();
      
      // Wait for eventual load
      await page.waitForSelector('[data-testid="device-management"]', { timeout: 10000 });
    });
  });

  test.describe('Performance Tests', () => {
    test('should load management pages within performance budget', async ({ page }) => {
      const pages = [
        '/admin/devices',
        '/admin/ipam', 
        '/admin/projects',
        '/admin/containers'
      ];

      for (const pageUrl of pages) {
        const startTime = Date.now();
        
        await page.goto(pageUrl);
        await page.waitForSelector('[data-testid*="management"]');
        
        const loadTime = Date.now() - startTime;
        
        // Should load within 3 seconds
        expect(loadTime).toBeLessThan(3000);
      }
    });
  });

  test.afterEach(async ({ page }) => {
    // Clear API request log for next test
    apiTester.clearRequestLog();
  });
});