/**
 * Portal Visualization Demo Test
 * Demonstrates the working portal visualization testing framework
 */

import { test, expect } from '@playwright/test';

test.describe('Portal Visualization Demo', () => {
  test('should demonstrate admin portal component structure @visual', async ({ page }) => {
    // Create a simple HTML page to test our component structure
    const htmlContent = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Admin Portal Demo</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .dashboard-container { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .metric-card { 
              background: #f5f5f5; 
              padding: 20px; 
              border-radius: 8px; 
              border-left: 4px solid #3b82f6;
            }
            .metric-value { font-size: 2em; font-weight: bold; color: #3b82f6; }
            .metric-label { color: #666; margin-top: 5px; }
            .chart-placeholder { 
              height: 200px; 
              background: linear-gradient(45deg, #e5e7eb, #f3f4f6);
              display: flex; 
              align-items: center; 
              justify-content: center;
              border-radius: 8px;
              margin: 20px 0;
            }
            .customer-table { 
              width: 100%; 
              border-collapse: collapse; 
              margin: 20px 0;
            }
            .customer-table th, .customer-table td { 
              padding: 12px; 
              text-align: left; 
              border-bottom: 1px solid #ddd; 
            }
            .customer-table th { background: #f8f9fa; }
            .view-toggle { margin: 20px 0; }
            .view-toggle button { 
              margin-right: 10px; 
              padding: 8px 16px; 
              border: 1px solid #ddd;
              background: white;
              cursor: pointer;
              border-radius: 4px;
            }
            .view-toggle button.active { 
              background: #3b82f6; 
              color: white; 
            }
          </style>
        </head>
        <body>
          <div data-testid="admin-dashboard">
            <h1>Admin Dashboard</h1>
            
            <!-- Dashboard Metrics -->
            <div class="dashboard-container">
              <div class="metric-card" data-testid="customer-count">
                <div class="metric-value">1,247</div>
                <div class="metric-label">Total Customers</div>
              </div>
              
              <div class="metric-card" data-testid="revenue-metric">
                <div class="metric-value">$45,678</div>
                <div class="metric-label">Monthly Revenue</div>
              </div>
            </div>
            
            <!-- Chart Visualization -->
            <div class="chart-placeholder" data-testid="revenue-chart">
              📊 Revenue Trends Chart (Mock)
            </div>
            
            <!-- Customer Management Section -->
            <div data-testid="customer-management">
              <h2>Customer Management</h2>
              
              <!-- View Toggle -->
              <div class="view-toggle">
                <button class="active" data-testid="table-view">📊 Table View</button>
                <button data-testid="map-view">🗺️ Geographic View</button>
              </div>
              
              <!-- Customer Table -->
              <table class="customer-table" data-testid="customer-table">
                <thead>
                  <tr>
                    <th>Customer Name</th>
                    <th>Email</th>
                    <th>Plan</th>
                    <th>Status</th>
                    <th>Location</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td>John Doe</td>
                    <td>john@example.com</td>
                    <td>Premium</td>
                    <td>Active</td>
                    <td>New York, NY</td>
                  </tr>
                  <tr>
                    <td>Jane Smith</td>
                    <td>jane@example.com</td>
                    <td>Basic</td>
                    <td>Active</td>
                    <td>Los Angeles, CA</td>
                  </tr>
                  <tr>
                    <td>Bob Johnson</td>
                    <td>bob@example.com</td>
                    <td>Premium</td>
                    <td>Suspended</td>
                    <td>Chicago, IL</td>
                  </tr>
                </tbody>
              </table>
            </div>
            
            <!-- Map View (Hidden by default) -->
            <div data-testid="map-container" style="display: none;">
              <h3>Customer Geographic Distribution</h3>
              <div class="chart-placeholder">
                🗺️ Interactive Map (Mock)
              </div>
            </div>
          </div>
          
          <script>
            // Simple view toggle functionality
            const tableViewBtn = document.querySelector('[data-testid="table-view"]');
            const mapViewBtn = document.querySelector('[data-testid="map-view"]');
            const customerTable = document.querySelector('[data-testid="customer-table"]');
            const mapContainer = document.querySelector('[data-testid="map-container"]');
            
            tableViewBtn.addEventListener('click', () => {
              tableViewBtn.classList.add('active');
              mapViewBtn.classList.remove('active');
              customerTable.style.display = 'table';
              mapContainer.style.display = 'none';
            });
            
            mapViewBtn.addEventListener('click', () => {
              mapViewBtn.classList.add('active');
              tableViewBtn.classList.remove('active');
              customerTable.style.display = 'none';
              mapContainer.style.display = 'block';
            });
          </script>
        </body>
      </html>
    `;

    // Load the demo page
    await page.setContent(htmlContent);

    // Test: Verify dashboard elements are visible
    await expect(page.getByTestId('admin-dashboard')).toBeVisible();
    await expect(page.getByTestId('customer-count')).toBeVisible();
    await expect(page.getByTestId('revenue-metric')).toBeVisible();

    // Test: Verify metric values are displayed
    const customerCount = await page.getByTestId('customer-count').textContent();
    expect(customerCount).toContain('1,247');

    const revenueMetric = await page.getByTestId('revenue-metric').textContent();
    expect(revenueMetric).toContain('$45,678');

    // Test: Verify chart visualization
    await expect(page.getByTestId('revenue-chart')).toBeVisible();

    // Take screenshot of admin dashboard
    await page.screenshot({
      path: 'test-results/admin-dashboard-demo.png',
      fullPage: true,
    });
  });

  test('should test customer management view switching @visual @interactive', async ({ page }) => {
    const htmlContent = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Customer Management Demo</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .view-toggle { margin: 20px 0; }
            .view-toggle button { 
              margin-right: 10px; 
              padding: 8px 16px; 
              border: 1px solid #ddd;
              background: white;
              cursor: pointer;
              border-radius: 4px;
            }
            .view-toggle button.active { 
              background: #3b82f6; 
              color: white; 
            }
            .customer-table { 
              width: 100%; 
              border-collapse: collapse; 
              margin: 20px 0;
            }
            .customer-table th, .customer-table td { 
              padding: 12px; 
              text-align: left; 
              border-bottom: 1px solid #ddd; 
            }
            .customer-table th { background: #f8f9fa; }
            .chart-placeholder { 
              height: 300px; 
              background: linear-gradient(45deg, #10b981, #34d399);
              display: flex; 
              align-items: center; 
              justify-content: center;
              border-radius: 8px;
              color: white;
              font-size: 1.2em;
            }
          </style>
        </head>
        <body>
          <div data-testid="customer-management">
            <h1>Customer Management</h1>
            
            <!-- View Toggle -->
            <div class="view-toggle">
              <button class="active" data-testid="table-view">📊 Table View</button>
              <button data-testid="map-view">🗺️ Geographic View</button>
            </div>
            
            <!-- Customer Table -->
            <table class="customer-table" data-testid="customer-table">
              <thead>
                <tr>
                  <th>Customer Name</th>
                  <th>Location</th>
                  <th>Plan</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>John Doe</td>
                  <td>New York, NY</td>
                  <td>Premium</td>
                  <td>Active</td>
                </tr>
                <tr>
                  <td>Jane Smith</td>
                  <td>Los Angeles, CA</td>
                  <td>Basic</td>
                  <td>Active</td>
                </tr>
              </tbody>
            </table>
            
            <!-- Map View -->
            <div data-testid="map-container" style="display: none;">
              <h2>Customer Geographic Distribution</h2>
              <div class="chart-placeholder" data-testid="geographic-map">
                🗺️ Interactive Geographic Map<br/>
                Customer Distribution Visualization
              </div>
            </div>
          </div>
          
          <script>
            const tableViewBtn = document.querySelector('[data-testid="table-view"]');
            const mapViewBtn = document.querySelector('[data-testid="map-view"]');
            const customerTable = document.querySelector('[data-testid="customer-table"]');
            const mapContainer = document.querySelector('[data-testid="map-container"]');
            
            tableViewBtn.addEventListener('click', () => {
              tableViewBtn.classList.add('active');
              mapViewBtn.classList.remove('active');
              customerTable.style.display = 'table';
              mapContainer.style.display = 'none';
            });
            
            mapViewBtn.addEventListener('click', () => {
              mapViewBtn.classList.add('active');
              tableViewBtn.classList.remove('active');
              customerTable.style.display = 'none';
              mapContainer.style.display = 'block';
            });
          </script>
        </body>
      </html>
    `;

    await page.setContent(htmlContent);

    // Test: Initial state - table view should be active
    await expect(page.getByTestId('table-view')).toHaveClass(/active/);
    await expect(page.getByTestId('customer-table')).toBeVisible();
    await expect(page.getByTestId('map-container')).not.toBeVisible();

    // Take screenshot of table view
    await page.screenshot({
      path: 'test-results/customer-table-view.png',
      fullPage: true,
    });

    // Test: Switch to map view
    await page.click('[data-testid="map-view"]');

    // Verify map view is now active
    await expect(page.getByTestId('map-view')).toHaveClass(/active/);
    await expect(page.getByTestId('map-container')).toBeVisible();
    await expect(page.getByTestId('geographic-map')).toBeVisible();
    await expect(page.getByText('Customer Geographic Distribution')).toBeVisible();

    // Take screenshot of map view
    await page.screenshot({
      path: 'test-results/customer-map-view.png',
      fullPage: true,
    });

    // Test: Switch back to table view
    await page.click('[data-testid="table-view"]');
    await expect(page.getByTestId('table-view')).toHaveClass(/active/);
    await expect(page.getByTestId('customer-table')).toBeVisible();
  });

  test('should demonstrate responsive layout testing @visual @responsive', async ({ page }) => {
    const htmlContent = `
      <!DOCTYPE html>
      <html>
        <head>
          <title>Responsive Portal Demo</title>
          <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            .dashboard { display: grid; gap: 20px; }
            .metric-card { 
              background: #f5f5f5; 
              padding: 20px; 
              border-radius: 8px; 
              text-align: center;
            }
            .metric-value { font-size: 2em; font-weight: bold; color: #3b82f6; }
            
            /* Desktop */
            @media (min-width: 768px) {
              .dashboard { grid-template-columns: repeat(3, 1fr); }
            }
            
            /* Tablet */
            @media (max-width: 767px) and (min-width: 481px) {
              .dashboard { grid-template-columns: repeat(2, 1fr); }
            }
            
            /* Mobile */
            @media (max-width: 480px) {
              .dashboard { grid-template-columns: 1fr; }
              .metric-card { padding: 15px; }
              .metric-value { font-size: 1.5em; }
            }
          </style>
        </head>
        <body>
          <div data-testid="responsive-dashboard">
            <h1>Responsive Dashboard</h1>
            <div class="dashboard">
              <div class="metric-card" data-testid="metric-1">
                <div class="metric-value">1,247</div>
                <div>Customers</div>
              </div>
              <div class="metric-card" data-testid="metric-2">
                <div class="metric-value">$45,678</div>
                <div>Revenue</div>
              </div>
              <div class="metric-card" data-testid="metric-3">
                <div class="metric-value">98.5%</div>
                <div>Uptime</div>
              </div>
            </div>
          </div>
        </body>
      </html>
    `;

    // Test desktop layout
    await page.setViewportSize({ width: 1200, height: 800 });
    await page.setContent(htmlContent);
    await expect(page.getByTestId('responsive-dashboard')).toBeVisible();
    await page.screenshot({ path: 'test-results/responsive-desktop.png', fullPage: true });

    // Test tablet layout
    await page.setViewportSize({ width: 768, height: 1024 });
    await page.screenshot({ path: 'test-results/responsive-tablet.png', fullPage: true });

    // Test mobile layout
    await page.setViewportSize({ width: 375, height: 667 });
    await page.screenshot({ path: 'test-results/responsive-mobile.png', fullPage: true });

    // Verify all metrics are still visible on mobile
    await expect(page.getByTestId('metric-1')).toBeVisible();
    await expect(page.getByTestId('metric-2')).toBeVisible();
    await expect(page.getByTestId('metric-3')).toBeVisible();
  });
});
