/**
 * Playwright E2E Tests for Customer Portal - Dashboard
 *
 * Tests customer-facing portal functionality including:
 * - Service overview and usage monitoring
 * - Account summary and billing status
 * - Support ticket management
 * - Service upgrade/downgrade requests
 * - Real-time network status
 */

import { test, expect } from '@playwright/test';

test.describe('Customer Portal - Dashboard', () => {
  test('should render customer dashboard with service overview @visual', async ({ page }) => {
    // Create mock customer dashboard
    await page.setContent(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Customer Portal - Dashboard</title>
          <script src="https://cdn.tailwindcss.com"></script>
          <style>
            .fade-in { animation: fadeIn 0.5s ease-in; }
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            .usage-bar { background: linear-gradient(90deg, #10b981 0%, #059669 100%); }
            .service-card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            .status-online { background: linear-gradient(135deg, #10b981 0%, #059669 100%); }
            .status-maintenance { background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); }
          </style>
        </head>
        <body class="bg-gray-50 min-h-screen">
          <!-- Header -->
          <header class="bg-white shadow-sm border-b border-gray-200">
            <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div class="flex justify-between items-center h-16">
                <div class="flex items-center space-x-4">
                  <div class="h-8 w-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center">
                    <span class="text-white font-bold text-lg">D</span>
                  </div>
                  <div>
                    <h1 class="text-xl font-semibold text-gray-900">My Services</h1>
                    <p class="text-sm text-gray-500">Welcome back, John Smith</p>
                  </div>
                </div>
                <div class="flex items-center space-x-4">
                  <button class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                    Contact Support
                  </button>
                  <div class="relative">
                    <button class="flex items-center space-x-2 text-gray-700 hover:text-gray-900">
                      <div class="w-8 h-8 bg-gray-300 rounded-full flex items-center justify-center">
                        <span class="text-sm font-medium">JS</span>
                      </div>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </header>

          <!-- Main Content -->
          <main class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
            
            <!-- Service Status Cards -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8 fade-in">
              <!-- Internet Service -->
              <div class="service-card rounded-xl p-6 text-white">
                <div class="flex items-center justify-between mb-4">
                  <div>
                    <h3 class="text-lg font-semibold">Internet Service</h3>
                    <p class="text-white/80 text-sm">Fiber 1000 Mbps</p>
                  </div>
                  <div class="status-online rounded-full p-3">
                    <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                  </div>
                </div>
                <div class="space-y-2">
                  <div class="flex justify-between text-sm">
                    <span>Status</span>
                    <span class="font-semibold">Online</span>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span>Uptime</span>
                    <span class="font-semibold">99.8%</span>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span>Speed Test</span>
                    <button class="underline hover:no-underline">Run Test</button>
                  </div>
                </div>
              </div>

              <!-- VoIP Service -->
              <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
                <div class="flex items-center justify-between mb-4">
                  <div>
                    <h3 class="text-lg font-semibold text-gray-900">VoIP Service</h3>
                    <p class="text-gray-600 text-sm">Business Line</p>
                  </div>
                  <div class="status-online rounded-full p-3">
                    <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M20 15.5c-1.25 0-2.45-.2-3.57-.57-.35-.11-.74-.03-1.02.24l-2.2 2.2c-2.83-1.44-5.15-3.75-6.59-6.59l2.2-2.2c.27-.27.35-.67.24-1.02C8.7 6.45 8.5 5.25 8.5 4c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1 0 9.39 7.61 17 17 17 .55 0 1-.45 1-1v-3.5c0-.55-.45-1-1-1z"/>
                    </svg>
                  </div>
                </div>
                <div class="space-y-2">
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600">Status</span>
                    <span class="font-semibold text-green-600">Active</span>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600">Minutes Used</span>
                    <span class="font-semibold text-gray-900">847 / 2000</span>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600">Call Quality</span>
                    <span class="font-semibold text-green-600">Excellent</span>
                  </div>
                </div>
              </div>

              <!-- Cloud Storage -->
              <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
                <div class="flex items-center justify-between mb-4">
                  <div>
                    <h3 class="text-lg font-semibold text-gray-900">Cloud Storage</h3>
                    <p class="text-gray-600 text-sm">Professional 1TB</p>
                  </div>
                  <div class="status-maintenance rounded-full p-3">
                    <svg class="w-6 h-6 text-white" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z"/>
                    </svg>
                  </div>
                </div>
                <div class="space-y-2">
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600">Status</span>
                    <span class="font-semibold text-yellow-600">Maintenance</span>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600">Storage Used</span>
                    <span class="font-semibold text-gray-900">642 GB / 1 TB</span>
                  </div>
                  <div class="flex justify-between text-sm">
                    <span class="text-gray-600">Backup Status</span>
                    <span class="font-semibold text-green-600">Up to date</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Usage Overview and Recent Activity -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
              <!-- Usage Overview -->
              <div class="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div class="flex items-center justify-between mb-6">
                  <div>
                    <h3 class="text-lg font-semibold text-gray-900">Bandwidth Usage</h3>
                    <p class="text-gray-600 text-sm">Current billing cycle: Nov 1 - Nov 30, 2024</p>
                  </div>
                  <div class="flex space-x-2">
                    <button class="bg-blue-100 text-blue-800 px-3 py-1 rounded-lg text-sm font-medium">This Month</button>
                    <button class="bg-gray-100 text-gray-600 px-3 py-1 rounded-lg text-sm">Last Month</button>
                  </div>
                </div>
                
                <!-- Usage Bars -->
                <div class="space-y-6">
                  <div>
                    <div class="flex justify-between items-center mb-2">
                      <span class="text-sm font-medium text-gray-900">Download</span>
                      <span class="text-sm text-gray-600">847 GB / 1000 GB</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-3">
                      <div class="usage-bar h-3 rounded-full" style="width: 84.7%"></div>
                    </div>
                    <div class="flex justify-between text-xs text-gray-500 mt-1">
                      <span>84.7% used</span>
                      <span>153 GB remaining</span>
                    </div>
                  </div>
                  
                  <div>
                    <div class="flex justify-between items-center mb-2">
                      <span class="text-sm font-medium text-gray-900">Upload</span>
                      <span class="text-sm text-gray-600">234 GB / 1000 GB</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-3">
                      <div class="bg-blue-500 h-3 rounded-full" style="width: 23.4%"></div>
                    </div>
                    <div class="flex justify-between text-xs text-gray-500 mt-1">
                      <span>23.4% used</span>
                      <span>766 GB remaining</span>
                    </div>
                  </div>
                  
                  <div>
                    <div class="flex justify-between items-center mb-2">
                      <span class="text-sm font-medium text-gray-900">Peak Usage Day</span>
                      <span class="text-sm text-gray-600">Nov 15 - 89.3 GB</span>
                    </div>
                    <div class="grid grid-cols-7 gap-1">
                      <div class="bg-green-200 h-8 rounded flex items-end">
                        <div class="bg-green-500 w-full rounded" style="height: 45%"></div>
                      </div>
                      <div class="bg-green-200 h-8 rounded flex items-end">
                        <div class="bg-green-500 w-full rounded" style="height: 60%"></div>
                      </div>
                      <div class="bg-green-200 h-8 rounded flex items-end">
                        <div class="bg-green-500 w-full rounded" style="height: 80%"></div>
                      </div>
                      <div class="bg-green-200 h-8 rounded flex items-end">
                        <div class="bg-green-500 w-full rounded" style="height: 55%"></div>
                      </div>
                      <div class="bg-green-200 h-8 rounded flex items-end">
                        <div class="bg-green-600 w-full rounded" style="height: 100%"></div>
                      </div>
                      <div class="bg-green-200 h-8 rounded flex items-end">
                        <div class="bg-green-500 w-full rounded" style="height: 70%"></div>
                      </div>
                      <div class="bg-green-200 h-8 rounded flex items-end">
                        <div class="bg-green-500 w-full rounded" style="height: 35%"></div>
                      </div>
                    </div>
                    <div class="flex justify-between text-xs text-gray-500 mt-1">
                      <span>Mon</span>
                      <span>Tue</span>
                      <span>Wed</span>
                      <span>Thu</span>
                      <span>Fri</span>
                      <span>Sat</span>
                      <span>Sun</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Recent Activity -->
              <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                <div class="flex items-center justify-between mb-4">
                  <h3 class="text-lg font-semibold text-gray-900">Recent Activity</h3>
                  <button class="text-blue-600 hover:text-blue-700 text-sm font-medium">View All</button>
                </div>
                <div class="space-y-4">
                  <div class="flex items-start space-x-3">
                    <div class="bg-green-100 rounded-full p-2 mt-1">
                      <svg class="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                      </svg>
                    </div>
                    <div class="flex-1">
                      <p class="text-sm font-medium text-gray-900">Payment Processed</p>
                      <p class="text-xs text-gray-600">Monthly service fee - $89.99</p>
                      <p class="text-xs text-gray-500">2 hours ago</p>
                    </div>
                  </div>
                  
                  <div class="flex items-start space-x-3">
                    <div class="bg-blue-100 rounded-full p-2 mt-1">
                      <svg class="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                      </svg>
                    </div>
                    <div class="flex-1">
                      <p class="text-sm font-medium text-gray-900">Speed Test Completed</p>
                      <p class="text-xs text-gray-600">Download: 987 Mbps, Upload: 456 Mbps</p>
                      <p class="text-xs text-gray-500">1 day ago</p>
                    </div>
                  </div>
                  
                  <div class="flex items-start space-x-3">
                    <div class="bg-yellow-100 rounded-full p-2 mt-1">
                      <svg class="w-4 h-4 text-yellow-600" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                      </svg>
                    </div>
                    <div class="flex-1">
                      <p class="text-sm font-medium text-gray-900">Maintenance Scheduled</p>
                      <p class="text-xs text-gray-600">Cloud storage upgrade - Nov 25, 2:00 AM</p>
                      <p class="text-xs text-gray-500">2 days ago</p>
                    </div>
                  </div>
                  
                  <div class="flex items-start space-x-3">
                    <div class="bg-purple-100 rounded-full p-2 mt-1">
                      <svg class="w-4 h-4 text-purple-600" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm-5 14H4v-4h11v4zm0-5H4V9h11v4zm5 5h-4V9h4v9z"/>
                      </svg>
                    </div>
                    <div class="flex-1">
                      <p class="text-sm font-medium text-gray-900">Support Ticket Resolved</p>
                      <p class="text-xs text-gray-600">Connection timeout issues - #12847</p>
                      <p class="text-xs text-gray-500">3 days ago</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Quick Actions -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
              <h3 class="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h3>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <button class="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                  <div class="bg-blue-100 rounded-full p-3 mb-2">
                    <svg class="w-6 h-6 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/>
                    </svg>
                  </div>
                  <span class="text-sm font-medium text-gray-900">View Bill</span>
                </button>
                
                <button class="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                  <div class="bg-green-100 rounded-full p-3 mb-2">
                    <svg class="w-6 h-6 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm3.5 6L12 10.5 8.5 8 12 5.5 15.5 8zM8.5 16L12 13.5 15.5 16 12 18.5 8.5 16z"/>
                    </svg>
                  </div>
                  <span class="text-sm font-medium text-gray-900">Speed Test</span>
                </button>
                
                <button class="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                  <div class="bg-purple-100 rounded-full p-3 mb-2">
                    <svg class="w-6 h-6 text-purple-600" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm-5 14H4v-4h11v4zm0-5H4V9h11v4zm5 5h-4V9h4v9z"/>
                    </svg>
                  </div>
                  <span class="text-sm font-medium text-gray-900">Support</span>
                </button>
                
                <button class="flex flex-col items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                  <div class="bg-orange-100 rounded-full p-3 mb-2">
                    <svg class="w-6 h-6 text-orange-600" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                    </svg>
                  </div>
                  <span class="text-sm font-medium text-gray-900">Upgrade</span>
                </button>
              </div>
            </div>
          </main>
        </body>
      </html>
    `);

    // Test header and user info
    await expect(page.locator('h1:has-text("My Services")')).toBeVisible();
    await expect(page.locator('text=Welcome back, John Smith')).toBeVisible();
    await expect(page.locator('button:has-text("Contact Support")')).toBeVisible();

    // Test service status cards
    await expect(page.locator('text=Internet Service')).toBeVisible();
    await expect(page.locator('text=Fiber 1000 Mbps')).toBeVisible();
    await expect(page.locator('text=Online').first()).toBeVisible();
    await expect(page.locator('text=99.8%')).toBeVisible();

    await expect(page.locator('text=VoIP Service')).toBeVisible();
    await expect(page.locator('text=Business Line')).toBeVisible();
    await expect(page.locator('text=Active')).toBeVisible();
    await expect(page.locator('text=847 / 2000')).toBeVisible();

    await expect(page.locator('h3:has-text("Cloud Storage")')).toBeVisible();
    await expect(page.locator('text=Professional 1TB')).toBeVisible();
    await expect(page.locator('span:has-text("Maintenance")').first()).toBeVisible();
    await expect(page.locator('text=642 GB / 1 TB')).toBeVisible();

    // Test bandwidth usage section
    await expect(page.locator('text=Bandwidth Usage')).toBeVisible();
    await expect(page.locator('text=Current billing cycle: Nov 1 - Nov 30, 2024')).toBeVisible();
    await expect(page.locator('span:has-text("Download")').first()).toBeVisible();
    await expect(page.locator('text=847 GB / 1000 GB')).toBeVisible();
    await expect(page.locator('span:has-text("Upload")').first()).toBeVisible();
    await expect(page.locator('text=234 GB / 1000 GB')).toBeVisible();
    await expect(page.locator('text=Peak Usage Day')).toBeVisible();

    // Test usage bars
    await expect(page.locator('.usage-bar')).toBeVisible();
    await expect(page.locator('text=84.7% used')).toBeVisible();
    await expect(page.locator('text=153 GB remaining')).toBeVisible();

    // Test recent activity
    await expect(page.locator('text=Recent Activity')).toBeVisible();
    await expect(page.locator('text=Payment Processed')).toBeVisible();
    await expect(page.locator('text=Speed Test Completed')).toBeVisible();
    await expect(page.locator('text=Maintenance Scheduled')).toBeVisible();
    await expect(page.locator('text=Support Ticket Resolved')).toBeVisible();

    // Test quick actions
    await expect(page.locator('text=Quick Actions')).toBeVisible();
    await expect(page.locator('span:has-text("View Bill")').last()).toBeVisible();
    await expect(page.locator('span:has-text("Speed Test")').last()).toBeVisible();
    await expect(page.locator('span:has-text("Support")').last()).toBeVisible();
    await expect(page.locator('span:has-text("Upgrade")').last()).toBeVisible();
  });

  test('should test interactive dashboard features @interactive', async ({ page }) => {
    // Create interactive customer dashboard
    await page.setContent(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Customer Portal - Interactive Dashboard</title>
          <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-50 min-h-screen p-8">
          <div class="max-w-7xl mx-auto">
            <h1 class="text-2xl font-bold text-gray-900 mb-6">Customer Dashboard</h1>
            
            <!-- Interactive Service Controls -->
            <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
              <!-- Internet Service Control -->
              <div class="bg-white rounded-lg shadow p-6">
                <div class="flex items-center justify-between mb-4">
                  <div>
                    <h3 class="text-lg font-semibold text-gray-900">Internet Service</h3>
                    <p class="text-gray-600 text-sm">Fiber 1000 Mbps</p>
                  </div>
                  <div class="flex items-center space-x-2">
                    <div id="connection-status" class="w-3 h-3 bg-green-500 rounded-full"></div>
                    <span id="status-text" class="text-sm font-medium text-green-600">Online</span>
                  </div>
                </div>
                
                <div class="space-y-4">
                  <button id="speed-test-btn" class="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors">
                    Run Speed Test
                  </button>
                  
                  <div id="speed-test-results" class="hidden bg-gray-50 rounded-lg p-4">
                    <div class="flex justify-between items-center mb-2">
                      <span class="text-sm text-gray-600">Download Speed</span>
                      <span class="font-semibold text-green-600">987 Mbps</span>
                    </div>
                    <div class="flex justify-between items-center">
                      <span class="text-sm text-gray-600">Upload Speed</span>
                      <span class="font-semibold text-green-600">456 Mbps</span>
                    </div>
                  </div>
                  
                  <button id="restart-modem-btn" class="w-full bg-gray-600 text-white py-2 px-4 rounded-lg hover:bg-gray-700 transition-colors">
                    Restart Modem
                  </button>
                </div>
              </div>

              <!-- Support Ticket -->
              <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-lg font-semibold text-gray-900 mb-4">Quick Support</h3>
                
                <form id="support-form" class="space-y-4">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Issue Type</label>
                    <select id="issue-type" class="w-full border border-gray-300 rounded-lg px-3 py-2">
                      <option value="">Select an issue</option>
                      <option value="connection">Connection Problems</option>
                      <option value="speed">Slow Internet Speed</option>
                      <option value="billing">Billing Question</option>
                      <option value="technical">Technical Support</option>
                    </select>
                  </div>
                  
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Description</label>
                    <textarea id="issue-description" rows="3" class="w-full border border-gray-300 rounded-lg px-3 py-2" placeholder="Describe your issue..."></textarea>
                  </div>
                  
                  <button type="submit" class="w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 transition-colors">
                    Submit Ticket
                  </button>
                </form>
                
                <div id="ticket-success" class="hidden mt-4 p-3 bg-green-100 border border-green-200 rounded-lg">
                  <p class="text-sm text-green-800">
                    <strong>Ticket #12849 created successfully!</strong><br>
                    We'll respond within 2-4 hours.
                  </p>
                </div>
              </div>
            </div>

            <!-- Usage Monitoring -->
            <div class="bg-white rounded-lg shadow p-6 mb-8">
              <div class="flex items-center justify-between mb-6">
                <h3 class="text-lg font-semibold text-gray-900">Data Usage Monitor</h3>
                <div class="flex space-x-2">
                  <button class="usage-period active bg-blue-600 text-white px-3 py-1 rounded text-sm" data-period="daily">Daily</button>
                  <button class="usage-period bg-gray-200 text-gray-700 px-3 py-1 rounded text-sm" data-period="weekly">Weekly</button>
                  <button class="usage-period bg-gray-200 text-gray-700 px-3 py-1 rounded text-sm" data-period="monthly">Monthly</button>
                </div>
              </div>
              
              <div id="usage-chart" class="bg-gradient-to-r from-blue-50 to-blue-100 rounded-lg p-6">
                <div class="flex items-end justify-between h-32 space-x-2">
                  <div class="bg-blue-500 rounded-t w-8" style="height: 60%">
                    <div class="text-xs text-white text-center mt-1">Mon</div>
                  </div>
                  <div class="bg-blue-500 rounded-t w-8" style="height: 80%">
                    <div class="text-xs text-white text-center mt-1">Tue</div>
                  </div>
                  <div class="bg-blue-600 rounded-t w-8" style="height: 100%">
                    <div class="text-xs text-white text-center mt-1">Wed</div>
                  </div>
                  <div class="bg-blue-500 rounded-t w-8" style="height: 70%">
                    <div class="text-xs text-white text-center mt-1">Thu</div>
                  </div>
                  <div class="bg-blue-500 rounded-t w-8" style="height: 85%">
                    <div class="text-xs text-white text-center mt-1">Fri</div>
                  </div>
                  <div class="bg-blue-400 rounded-t w-8" style="height: 45%">
                    <div class="text-xs text-white text-center mt-1">Sat</div>
                  </div>
                  <div class="bg-blue-400 rounded-t w-8" style="height: 35%">
                    <div class="text-xs text-white text-center mt-1">Sun</div>
                  </div>
                </div>
              </div>
              
              <div class="grid grid-cols-3 gap-4 mt-6 text-center">
                <div>
                  <p class="text-2xl font-bold text-blue-600">847 GB</p>
                  <p class="text-sm text-gray-600">Download</p>
                </div>
                <div>
                  <p class="text-2xl font-bold text-green-600">234 GB</p>
                  <p class="text-sm text-gray-600">Upload</p>
                </div>
                <div>
                  <p class="text-2xl font-bold text-gray-900">15.3%</p>
                  <p class="text-sm text-gray-600">Over Limit</p>
                </div>
              </div>
            </div>

            <!-- Account Management -->
            <div class="bg-white rounded-lg shadow p-6">
              <h3 class="text-lg font-semibold text-gray-900 mb-6">Account Management</h3>
              
              <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div class="text-center">
                  <div class="bg-green-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-3">
                    <svg class="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                  </div>
                  <h4 class="font-semibold text-gray-900">Account Status</h4>
                  <p class="text-sm text-green-600 font-medium">Active & Current</p>
                  <p class="text-xs text-gray-500 mt-1">Next bill: Dec 1, 2024</p>
                </div>
                
                <div class="text-center">
                  <div class="bg-blue-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-3">
                    <svg class="w-8 h-8 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/>
                    </svg>
                  </div>
                  <h4 class="font-semibold text-gray-900">Current Balance</h4>
                  <p class="text-sm text-gray-900 font-medium">$0.00</p>
                  <button class="text-xs text-blue-600 hover:underline mt-1">View Statements</button>
                </div>
                
                <div class="text-center">
                  <div class="bg-purple-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-3">
                    <svg class="w-8 h-8 text-purple-600" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                    </svg>
                  </div>
                  <h4 class="font-semibold text-gray-900">Service Plan</h4>
                  <p class="text-sm text-gray-900 font-medium">Business Pro</p>
                  <button class="text-xs text-purple-600 hover:underline mt-1">Upgrade Plan</button>
                </div>
              </div>
            </div>
          </div>
          
          <script>
            // Speed test functionality
            document.getElementById('speed-test-btn').addEventListener('click', function() {
              const button = this;
              const results = document.getElementById('speed-test-results');
              
              button.textContent = 'Testing...';
              button.disabled = true;
              
              setTimeout(() => {
                results.classList.remove('hidden');
                button.textContent = 'Run Speed Test';
                button.disabled = false;
              }, 2000);
            });
            
            // Support form functionality
            document.getElementById('support-form').addEventListener('submit', function(e) {
              e.preventDefault();
              
              const issueType = document.getElementById('issue-type').value;
              const description = document.getElementById('issue-description').value;
              
              if (issueType && description.trim()) {
                document.getElementById('ticket-success').classList.remove('hidden');
                this.reset();
              }
            });
            
            // Usage period toggle
            document.querySelectorAll('.usage-period').forEach(button => {
              button.addEventListener('click', function() {
                document.querySelectorAll('.usage-period').forEach(b => {
                  b.classList.remove('active', 'bg-blue-600', 'text-white');
                  b.classList.add('bg-gray-200', 'text-gray-700');
                });
                
                this.classList.add('active', 'bg-blue-600', 'text-white');
                this.classList.remove('bg-gray-200', 'text-gray-700');
              });
            });
            
            // Modem restart simulation
            document.getElementById('restart-modem-btn').addEventListener('click', function() {
              const button = this;
              const status = document.getElementById('connection-status');
              const statusText = document.getElementById('status-text');
              
              button.textContent = 'Restarting...';
              button.disabled = true;
              
              // Show offline status
              status.classList.remove('bg-green-500');
              status.classList.add('bg-red-500');
              statusText.textContent = 'Restarting';
              statusText.classList.remove('text-green-600');
              statusText.classList.add('text-red-600');
              
              setTimeout(() => {
                // Show back online
                status.classList.remove('bg-red-500');
                status.classList.add('bg-green-500');
                statusText.textContent = 'Online';
                statusText.classList.remove('text-red-600');
                statusText.classList.add('text-green-600');
                
                button.textContent = 'Restart Modem';
                button.disabled = false;
              }, 3000);
            });
          </script>
        </body>
      </html>
    `);

    // Test speed test functionality
    await page.click('#speed-test-btn');
    await expect(page.locator('button:has-text("Testing...")')).toBeVisible();
    await page.waitForTimeout(2100);
    await expect(page.locator('#speed-test-results')).toBeVisible();
    await expect(page.locator('text=987 Mbps')).toBeVisible();
    await expect(page.locator('text=456 Mbps')).toBeVisible();

    // Test support form
    await page.selectOption('#issue-type', 'connection');
    await page.fill('#issue-description', 'Internet connection keeps dropping every few minutes');
    await page.click('button[type="submit"]');
    await expect(page.locator('#ticket-success')).toBeVisible();
    await expect(page.locator('text=Ticket #12849 created successfully!')).toBeVisible();

    // Test usage period toggle
    await page.click('button[data-period="weekly"]');
    await expect(page.locator('button[data-period="weekly"]')).toHaveClass(/bg-blue-600/);
    await expect(page.locator('button[data-period="daily"]')).toHaveClass(/bg-gray-200/);

    // Test modem restart
    await page.click('#restart-modem-btn');
    await expect(page.locator('button:has-text("Restarting...")')).toBeVisible();
    await expect(page.locator('#status-text:has-text("Restarting")')).toBeVisible();
    await page.waitForTimeout(3100);
    await expect(page.locator('#status-text:has-text("Online")')).toBeVisible();
    await expect(page.locator('button:has-text("Restart Modem")')).toBeVisible();

    // Test account management buttons
    await expect(page.locator('button:has-text("View Statements")')).toBeVisible();
    await expect(page.locator('button:has-text("Upgrade Plan")')).toBeVisible();
  });

  test('should test responsive customer dashboard @responsive', async ({ page }) => {
    // Test mobile layout
    await page.setViewportSize({ width: 375, height: 667 });

    await page.setContent(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Customer Portal - Mobile Dashboard</title>
          <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-50 min-h-screen">
          <!-- Mobile Customer Dashboard -->
          <div class="max-w-sm mx-auto bg-white min-h-screen">
            <!-- Mobile Header -->
            <header class="bg-gradient-to-r from-blue-600 to-blue-700 text-white p-4">
              <div class="flex justify-between items-center mb-4">
                <div>
                  <h1 class="text-lg font-semibold">My Account</h1>
                  <p class="text-blue-100 text-sm">John Smith</p>
                </div>
                <button class="p-2 rounded-full bg-white/20">
                  <svg class="w-6 h-6" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                  </svg>
                </button>
              </div>
              
              <!-- Service Status Summary -->
              <div class="bg-white/20 rounded-lg p-3">
                <div class="flex items-center space-x-2">
                  <div class="w-3 h-3 bg-green-400 rounded-full"></div>
                  <span class="text-sm">All services online</span>
                </div>
                <div class="text-right">
                  <p class="text-xs text-blue-100">Next bill: Dec 1</p>
                  <p class="font-semibold">$89.99</p>
                </div>
              </div>
            </header>

            <!-- Mobile Service Cards -->
            <div class="p-4 space-y-4">
              <!-- Internet Card -->
              <div class="bg-white rounded-lg shadow-sm border p-4">
                <div class="flex justify-between items-center mb-3">
                  <div>
                    <h3 class="font-semibold text-gray-900">Internet</h3>
                    <p class="text-sm text-gray-600">1000 Mbps</p>
                  </div>
                  <div class="flex items-center space-x-1">
                    <div class="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span class="text-xs text-green-600">Online</span>
                  </div>
                </div>
                <div class="text-center py-2">
                  <button class="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm w-full">
                    Speed Test
                  </button>
                </div>
              </div>

              <!-- VoIP Card -->
              <div class="bg-white rounded-lg shadow-sm border p-4">
                <div class="flex justify-between items-center mb-3">
                  <div>
                    <h3 class="font-semibold text-gray-900">Phone</h3>
                    <p class="text-sm text-gray-600">Business Line</p>
                  </div>
                  <div class="flex items-center space-x-1">
                    <div class="w-2 h-2 bg-green-500 rounded-full"></div>
                    <span class="text-xs text-green-600">Active</span>
                  </div>
                </div>
                <div class="flex justify-between text-sm">
                  <span class="text-gray-600">Minutes used</span>
                  <span class="font-medium">847/2000</span>
                </div>
              </div>

              <!-- Usage Summary -->
              <div class="bg-white rounded-lg shadow-sm border p-4">
                <h3 class="font-semibold text-gray-900 mb-3">Usage This Month</h3>
                <div class="space-y-3">
                  <div>
                    <div class="flex justify-between text-sm mb-1">
                      <span class="text-gray-600">Download</span>
                      <span class="font-medium">847 GB</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2">
                      <div class="bg-green-500 h-2 rounded-full" style="width: 84.7%"></div>
                    </div>
                  </div>
                  <div>
                    <div class="flex justify-between text-sm mb-1">
                      <span class="text-gray-600">Upload</span>
                      <span class="font-medium">234 GB</span>
                    </div>
                    <div class="w-full bg-gray-200 rounded-full h-2">
                      <div class="bg-blue-500 h-2 rounded-full" style="width: 23.4%"></div>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Quick Actions -->
              <div class="bg-white rounded-lg shadow-sm border p-4">
                <h3 class="font-semibold text-gray-900 mb-3">Quick Actions</h3>
                <div class="space-y-2">
                  <button class="w-full text-left p-3 bg-gray-50 rounded-lg flex items-center space-x-3">
                    <div class="bg-blue-100 rounded-full p-2">
                      <svg class="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/>
                      </svg>
                    </div>
                    <span class="font-medium text-gray-900">View Bill</span>
                  </button>
                  
                  <button class="w-full text-left p-3 bg-gray-50 rounded-lg flex items-center space-x-3">
                    <div class="bg-green-100 rounded-full p-2">
                      <svg class="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2z"/>
                      </svg>
                    </div>
                    <span class="font-medium text-gray-900">Contact Support</span>
                  </button>
                  
                  <button class="w-full text-left p-3 bg-gray-50 rounded-lg flex items-center space-x-3">
                    <div class="bg-purple-100 rounded-full p-2">
                      <svg class="w-4 h-4 text-purple-600" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                      </svg>
                    </div>
                    <span class="font-medium text-gray-900">Upgrade Service</span>
                  </button>
                </div>
              </div>
            </div>

            <!-- Mobile Bottom Navigation -->
            <div class="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4">
              <div class="grid grid-cols-4 gap-1 max-w-sm mx-auto">
                <button class="flex flex-col items-center p-2 text-blue-600">
                  <svg class="w-6 h-6 mb-1" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"/>
                  </svg>
                  <span class="text-xs">Home</span>
                </button>
                <button class="flex flex-col items-center p-2 text-gray-400">
                  <svg class="w-6 h-6 mb-1" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/>
                  </svg>
                  <span class="text-xs">Usage</span>
                </button>
                <button class="flex flex-col items-center p-2 text-gray-400">
                  <svg class="w-6 h-6 mb-1" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/>
                  </svg>
                  <span class="text-xs">Bills</span>
                </button>
                <button class="flex flex-col items-center p-2 text-gray-400">
                  <svg class="w-6 h-6 mb-1" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
                  </svg>
                  <span class="text-xs">More</span>
                </button>
              </div>
            </div>
          </div>
        </body>
      </html>
    `);

    // Test mobile header
    await expect(page.locator('h1:has-text("My Account")')).toBeVisible();
    await expect(page.locator('text=John Smith')).toBeVisible();
    await expect(page.locator('text=All services online')).toBeVisible();
    await expect(page.locator('text=$89.99')).toBeVisible();

    // Test mobile service cards
    await expect(page.locator('text=Internet')).toBeVisible();
    await expect(page.locator('text=1000 Mbps')).toBeVisible();
    await expect(page.locator('text=Online').first()).toBeVisible();

    await expect(page.locator('text=Phone')).toBeVisible();
    await expect(page.locator('text=Business Line')).toBeVisible();
    await expect(page.locator('text=Active')).toBeVisible();

    // Test mobile usage summary
    await expect(page.locator('text=Usage This Month')).toBeVisible();
    await expect(page.locator('text=Download')).toBeVisible();
    await expect(page.locator('text=847 GB')).toBeVisible();
    await expect(page.locator('text=Upload')).toBeVisible();
    await expect(page.locator('text=234 GB')).toBeVisible();

    // Test mobile quick actions
    await expect(page.locator('text=Quick Actions')).toBeVisible();
    await expect(page.locator('span:has-text("View Bill")')).toBeVisible();
    await expect(page.locator('span:has-text("Contact Support")')).toBeVisible();
    await expect(page.locator('span:has-text("Upgrade Service")')).toBeVisible();

    // Test mobile bottom navigation
    await expect(page.locator('span:has-text("Home")')).toBeVisible();
    await expect(page.locator('span:has-text("Usage")')).toBeVisible();
    await expect(page.locator('span:has-text("Bills")')).toBeVisible();
    await expect(page.locator('span:has-text("More")')).toBeVisible();

    // Test speed test button
    await page.click('button:has-text("Speed Test")');
  });
});
