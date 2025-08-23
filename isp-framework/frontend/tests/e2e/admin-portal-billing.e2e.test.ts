/**
 * Playwright E2E Tests for Admin Portal - Billing Management
 *
 * Tests comprehensive billing functionality including:
 * - Invoice management and viewing
 * - Payment processing and tracking
 * - Revenue analytics and reporting
 * - Customer billing profiles
 * - Automated billing workflows
 */

import { test, expect } from '@playwright/test';

test.describe('Admin Portal - Billing Management', () => {
  test('should render billing dashboard with revenue overview @visual', async ({ page }) => {
    // Create mock billing dashboard with comprehensive revenue data
    await page.setContent(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Admin Portal - Billing Dashboard</title>
          <script src="https://cdn.tailwindcss.com"></script>
          <script src="https://unpkg.com/recharts@2.8.0/esm/index.js" type="module"></script>
          <style>
            .fade-in { animation: fadeIn 0.5s ease-in; }
            @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
            .slide-up { animation: slideUp 0.6s ease-out; }
            @keyframes slideUp { from { transform: translateY(20px); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
            .chart-container { min-height: 400px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            .metric-card { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
            .revenue-trend { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
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
                    <h1 class="text-xl font-semibold text-gray-900">Billing Management</h1>
                    <p class="text-sm text-gray-500">Revenue tracking and payment processing</p>
                  </div>
                </div>
                <div class="flex items-center space-x-4">
                  <button class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                    Generate Invoice
                  </button>
                  <button class="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 transition-colors">
                    Process Payments
                  </button>
                </div>
              </div>
            </div>
          </header>

          <!-- Main Content -->
          <main class="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
            
            <!-- Revenue Metrics Cards -->
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8 fade-in">
              <div class="metric-card rounded-xl p-6 text-white">
                <div class="flex items-center justify-between">
                  <div>
                    <p class="text-white/80 text-sm">Monthly Revenue</p>
                    <p class="text-3xl font-bold">$847,329</p>
                    <p class="text-white/80 text-sm mt-1">+12.3% from last month</p>
                  </div>
                  <div class="bg-white/20 rounded-lg p-3">
                    <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                  </div>
                </div>
              </div>
              
              <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
                <div class="flex items-center justify-between">
                  <div>
                    <p class="text-gray-600 text-sm">Outstanding Invoices</p>
                    <p class="text-3xl font-bold text-gray-900">$142,847</p>
                    <p class="text-red-600 text-sm mt-1">23 overdue</p>
                  </div>
                  <div class="bg-red-100 rounded-lg p-3">
                    <svg class="w-8 h-8 text-red-600" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                    </svg>
                  </div>
                </div>
              </div>
              
              <div class="revenue-trend rounded-xl p-6 text-white">
                <div class="flex items-center justify-between">
                  <div>
                    <p class="text-white/80 text-sm">Payment Success Rate</p>
                    <p class="text-3xl font-bold">94.7%</p>
                    <p class="text-white/80 text-sm mt-1">+2.1% improvement</p>
                  </div>
                  <div class="bg-white/20 rounded-lg p-3">
                    <svg class="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                    </svg>
                  </div>
                </div>
              </div>
              
              <div class="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
                <div class="flex items-center justify-between">
                  <div>
                    <p class="text-gray-600 text-sm">Active Subscriptions</p>
                    <p class="text-3xl font-bold text-gray-900">12,847</p>
                    <p class="text-green-600 text-sm mt-1">+347 this month</p>
                  </div>
                  <div class="bg-green-100 rounded-lg p-3">
                    <svg class="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M16 4c0-1.11.89-2 2-2s2 .89 2 2-.89 2-2 2-2-.89-2-2zM4 18v-1c0-1.1.9-2 2-2h7c1.1 0 2 .9 2 2v1h2v5H2v-5h2z"/>
                    </svg>
                  </div>
                </div>
              </div>
            </div>

            <!-- Revenue Chart and Recent Transactions -->
            <div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
              <!-- Revenue Chart -->
              <div class="lg:col-span-2 bg-white rounded-xl shadow-sm border border-gray-200 p-6 slide-up">
                <div class="flex items-center justify-between mb-6">
                  <div>
                    <h3 class="text-lg font-semibold text-gray-900">Revenue Trends</h3>
                    <p class="text-gray-600 text-sm">Monthly revenue over the last 12 months</p>
                  </div>
                  <div class="flex space-x-2">
                    <button class="bg-blue-100 text-blue-800 px-3 py-1 rounded-lg text-sm font-medium">12M</button>
                    <button class="bg-gray-100 text-gray-600 px-3 py-1 rounded-lg text-sm">6M</button>
                    <button class="bg-gray-100 text-gray-600 px-3 py-1 rounded-lg text-sm">3M</button>
                  </div>
                </div>
                <div class="chart-container rounded-lg p-4 text-white">
                  <div class="flex items-end justify-between h-64 space-x-2">
                    <div class="bg-white/30 rounded-t w-12 h-32 flex items-end pb-2">
                      <span class="text-xs w-full text-center">Jan</span>
                    </div>
                    <div class="bg-white/40 rounded-t w-12 h-40 flex items-end pb-2">
                      <span class="text-xs w-full text-center">Feb</span>
                    </div>
                    <div class="bg-white/50 rounded-t w-12 h-48 flex items-end pb-2">
                      <span class="text-xs w-full text-center">Mar</span>
                    </div>
                    <div class="bg-white/30 rounded-t w-12 h-36 flex items-end pb-2">
                      <span class="text-xs w-full text-center">Apr</span>
                    </div>
                    <div class="bg-white/60 rounded-t w-12 h-56 flex items-end pb-2">
                      <span class="text-xs w-full text-center">May</span>
                    </div>
                    <div class="bg-white/70 rounded-t w-12 h-64 flex items-end pb-2">
                      <span class="text-xs w-full text-center">Jun</span>
                    </div>
                    <div class="bg-white/45 rounded-t w-12 h-44 flex items-end pb-2">
                      <span class="text-xs w-full text-center">Jul</span>
                    </div>
                    <div class="bg-white/55 rounded-t w-12 h-52 flex items-end pb-2">
                      <span class="text-xs w-full text-center">Aug</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Recent Transactions -->
              <div class="bg-white rounded-xl shadow-sm border border-gray-200 p-6 slide-up">
                <div class="flex items-center justify-between mb-4">
                  <h3 class="text-lg font-semibold text-gray-900">Recent Transactions</h3>
                  <button class="text-blue-600 hover:text-blue-700 text-sm font-medium">View All</button>
                </div>
                <div class="space-y-4">
                  <div class="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                    <div class="flex items-center space-x-3">
                      <div class="bg-green-100 rounded-full p-2">
                        <svg class="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                        </svg>
                      </div>
                      <div>
                        <p class="text-sm font-medium text-gray-900">Payment Received</p>
                        <p class="text-xs text-gray-600">Acme Corp #INV-2024-001</p>
                      </div>
                    </div>
                    <span class="text-green-600 font-semibold">+$2,340</span>
                  </div>
                  
                  <div class="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                    <div class="flex items-center space-x-3">
                      <div class="bg-blue-100 rounded-full p-2">
                        <svg class="w-4 h-4 text-blue-600" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/>
                        </svg>
                      </div>
                      <div>
                        <p class="text-sm font-medium text-gray-900">Invoice Generated</p>
                        <p class="text-xs text-gray-600">TechFlow Ltd #INV-2024-002</p>
                      </div>
                    </div>
                    <span class="text-blue-600 font-semibold">$4,890</span>
                  </div>
                  
                  <div class="flex items-center justify-between p-3 bg-yellow-50 rounded-lg">
                    <div class="flex items-center space-x-3">
                      <div class="bg-yellow-100 rounded-full p-2">
                        <svg class="w-4 h-4 text-yellow-600" fill="currentColor" viewBox="0 0 24 24">
                          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
                        </svg>
                      </div>
                      <div>
                        <p class="text-sm font-medium text-gray-900">Payment Pending</p>
                        <p class="text-xs text-gray-600">StartupXYZ #INV-2024-003</p>
                      </div>
                    </div>
                    <span class="text-yellow-600 font-semibold">$1,250</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Invoice Management Table -->
            <div class="bg-white rounded-xl shadow-sm border border-gray-200 slide-up">
              <div class="p-6 border-b border-gray-200">
                <div class="flex items-center justify-between">
                  <div>
                    <h3 class="text-lg font-semibold text-gray-900">Invoice Management</h3>
                    <p class="text-gray-600 text-sm">Track and manage customer invoices</p>
                  </div>
                  <div class="flex items-center space-x-4">
                    <div class="relative">
                      <input 
                        type="text" 
                        placeholder="Search invoices..." 
                        class="pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      >
                      <svg class="absolute left-3 top-2.5 w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 24 24">
                        <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                      </svg>
                    </div>
                    <select class="border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500">
                      <option>All Statuses</option>
                      <option>Paid</option>
                      <option>Pending</option>
                      <option>Overdue</option>
                    </select>
                  </div>
                </div>
              </div>
              
              <div class="overflow-x-auto">
                <table class="w-full">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Invoice</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Customer</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Amount</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Due Date</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody class="bg-white divide-y divide-gray-200">
                    <tr class="hover:bg-gray-50">
                      <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-medium text-gray-900">#INV-2024-001</div>
                        <div class="text-sm text-gray-500">Created: Nov 15, 2024</div>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <div class="flex items-center">
                          <div class="flex-shrink-0 h-10 w-10">
                            <div class="h-10 w-10 bg-blue-100 rounded-full flex items-center justify-center">
                              <span class="text-sm font-medium text-blue-800">AC</span>
                            </div>
                          </div>
                          <div class="ml-4">
                            <div class="text-sm font-medium text-gray-900">Acme Corp</div>
                            <div class="text-sm text-gray-500">accounting@acme.com</div>
                          </div>
                        </div>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-semibold text-gray-900">$2,340.00</div>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                          Paid
                        </span>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        Dec 15, 2024
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button class="text-blue-600 hover:text-blue-900 mr-3">View</button>
                        <button class="text-gray-600 hover:text-gray-900">Download</button>
                      </td>
                    </tr>
                    
                    <tr class="hover:bg-gray-50">
                      <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-medium text-gray-900">#INV-2024-002</div>
                        <div class="text-sm text-gray-500">Created: Nov 16, 2024</div>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <div class="flex items-center">
                          <div class="flex-shrink-0 h-10 w-10">
                            <div class="h-10 w-10 bg-purple-100 rounded-full flex items-center justify-center">
                              <span class="text-sm font-medium text-purple-800">TF</span>
                            </div>
                          </div>
                          <div class="ml-4">
                            <div class="text-sm font-medium text-gray-900">TechFlow Ltd</div>
                            <div class="text-sm text-gray-500">billing@techflow.com</div>
                          </div>
                        </div>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-semibold text-gray-900">$4,890.00</div>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                          Pending
                        </span>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        Dec 16, 2024
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button class="text-blue-600 hover:text-blue-900 mr-3">View</button>
                        <button class="text-green-600 hover:text-green-900 mr-3">Remind</button>
                        <button class="text-gray-600 hover:text-gray-900">Download</button>
                      </td>
                    </tr>
                    
                    <tr class="hover:bg-gray-50">
                      <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-medium text-gray-900">#INV-2024-003</div>
                        <div class="text-sm text-gray-500">Created: Nov 10, 2024</div>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <div class="flex items-center">
                          <div class="flex-shrink-0 h-10 w-10">
                            <div class="h-10 w-10 bg-red-100 rounded-full flex items-center justify-center">
                              <span class="text-sm font-medium text-red-800">SX</span>
                            </div>
                          </div>
                          <div class="ml-4">
                            <div class="text-sm font-medium text-gray-900">StartupXYZ</div>
                            <div class="text-sm text-gray-500">finance@startupxyz.com</div>
                          </div>
                        </div>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <div class="text-sm font-semibold text-gray-900">$1,250.00</div>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <span class="px-2 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                          Overdue
                        </span>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        Dec 10, 2024
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                        <button class="text-blue-600 hover:text-blue-900 mr-3">View</button>
                        <button class="text-red-600 hover:text-red-900 mr-3">Follow Up</button>
                        <button class="text-gray-600 hover:text-gray-900">Download</button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
              
              <div class="bg-gray-50 px-6 py-3 flex items-center justify-between">
                <div class="text-sm text-gray-700">
                  Showing 1 to 3 of 847 invoices
                </div>
                <div class="flex space-x-2">
                  <button class="px-3 py-1 border border-gray-300 rounded text-sm hover:bg-white">Previous</button>
                  <button class="px-3 py-1 bg-blue-600 text-white rounded text-sm">1</button>
                  <button class="px-3 py-1 border border-gray-300 rounded text-sm hover:bg-white">2</button>
                  <button class="px-3 py-1 border border-gray-300 rounded text-sm hover:bg-white">3</button>
                  <button class="px-3 py-1 border border-gray-300 rounded text-sm hover:bg-white">Next</button>
                </div>
              </div>
            </div>
          </main>
        </body>
      </html>
    `);

    // Test header and navigation
    await expect(page.locator('header')).toBeVisible();
    await expect(page.locator('h1:has-text("Billing Management")')).toBeVisible();
    await expect(page.locator('button:has-text("Generate Invoice")')).toBeVisible();
    await expect(page.locator('button:has-text("Process Payments")')).toBeVisible();

    // Test revenue metrics cards
    await expect(page.locator('text=Monthly Revenue').first()).toBeVisible();
    await expect(page.locator('text=$847,329')).toBeVisible();
    await expect(page.locator('text=Outstanding Invoices')).toBeVisible();
    await expect(page.locator('text=$142,847')).toBeVisible();
    await expect(page.locator('text=Payment Success Rate')).toBeVisible();
    await expect(page.locator('text=94.7%')).toBeVisible();
    await expect(page.locator('text=Active Subscriptions')).toBeVisible();
    await expect(page.locator('text=12,847')).toBeVisible();

    // Test revenue chart
    await expect(page.locator('text=Revenue Trends')).toBeVisible();
    await expect(page.locator('.chart-container')).toBeVisible();

    // Test recent transactions
    await expect(page.locator('text=Recent Transactions')).toBeVisible();
    await expect(page.locator('text=Payment Received')).toBeVisible();
    await expect(page.locator('text=Invoice Generated')).toBeVisible();
    await expect(page.locator('text=Payment Pending')).toBeVisible();

    // Test invoice management table
    await expect(page.locator('text=Invoice Management')).toBeVisible();
    await expect(page.locator('table td:has-text("#INV-2024-001")').first()).toBeVisible();
    await expect(page.locator('text=Acme Corp').first()).toBeVisible();
    await expect(page.locator('text=$2,340.00')).toBeVisible();

    // Test table functionality
    await expect(page.locator('input[placeholder="Search invoices..."]')).toBeVisible();
    await expect(page.locator('select')).toBeVisible();
    await expect(page.locator('span.bg-green-100:has-text("Paid")')).toBeVisible();
    await expect(page.locator('span.bg-yellow-100:has-text("Pending")')).toBeVisible();
    await expect(page.locator('span.bg-red-100:has-text("Overdue")')).toBeVisible();

    // Test action buttons
    await expect(page.locator('button:has-text("View")').first()).toBeVisible();
    await expect(page.locator('button:has-text("Download")').first()).toBeVisible();
    await expect(page.locator('button:has-text("Remind")')).toBeVisible();
    await expect(page.locator('button:has-text("Follow Up")')).toBeVisible();

    // Test pagination
    await expect(page.locator('text=Showing 1 to 3 of 847 invoices')).toBeVisible();
    await expect(page.locator('button:has-text("Previous")')).toBeVisible();
    await expect(page.locator('button:has-text("Next")')).toBeVisible();
  });

  test('should test billing search and filtering functionality @interactive', async ({ page }) => {
    // Create billing page with search functionality
    await page.setContent(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Admin Portal - Billing Search</title>
          <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-50 min-h-screen p-8">
          <div class="max-w-7xl mx-auto">
            <h1 class="text-2xl font-bold text-gray-900 mb-6">Billing Management</h1>
            
            <!-- Search and Filter Controls -->
            <div class="bg-white rounded-lg shadow p-6 mb-6">
              <div class="flex items-center space-x-4 mb-4">
                <input 
                  type="text" 
                  id="invoice-search"
                  placeholder="Search by invoice number, customer name, or email..." 
                  class="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                >
                <select id="status-filter" class="px-3 py-2 border border-gray-300 rounded-lg">
                  <option value="">All Statuses</option>
                  <option value="paid">Paid</option>
                  <option value="pending">Pending</option>
                  <option value="overdue">Overdue</option>
                </select>
                <select id="date-filter" class="px-3 py-2 border border-gray-300 rounded-lg">
                  <option value="">All Dates</option>
                  <option value="today">Today</option>
                  <option value="week">This Week</option>
                  <option value="month">This Month</option>
                </select>
                <button id="search-button" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
                  Search
                </button>
                <button id="clear-button" class="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700">
                  Clear
                </button>
              </div>
              
              <!-- Quick Filters -->
              <div class="flex space-x-2">
                <button class="quick-filter bg-red-100 text-red-800 px-3 py-1 rounded-lg text-sm" data-filter="overdue">
                  Overdue (23)
                </button>
                <button class="quick-filter bg-yellow-100 text-yellow-800 px-3 py-1 rounded-lg text-sm" data-filter="pending">
                  Pending (156)
                </button>
                <button class="quick-filter bg-green-100 text-green-800 px-3 py-1 rounded-lg text-sm" data-filter="paid">
                  Paid This Month (1,247)
                </button>
              </div>
            </div>
            
            <!-- Results Table -->
            <div class="bg-white rounded-lg shadow overflow-hidden">
              <div class="p-4 border-b border-gray-200">
                <div class="flex justify-between items-center">
                  <span id="results-count" class="text-gray-600">Showing 847 invoices</span>
                  <div class="flex items-center space-x-2">
                    <span class="text-sm text-gray-500">Sort by:</span>
                    <select id="sort-select" class="text-sm border border-gray-300 rounded px-2 py-1">
                      <option value="date-desc">Date (Newest)</option>
                      <option value="date-asc">Date (Oldest)</option>
                      <option value="amount-desc">Amount (High to Low)</option>
                      <option value="amount-asc">Amount (Low to High)</option>
                      <option value="customer">Customer Name</option>
                    </select>
                  </div>
                </div>
              </div>
              
              <div class="overflow-x-auto">
                <table class="w-full">
                  <thead class="bg-gray-50">
                    <tr>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Invoice</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                      <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Date</th>
                    </tr>
                  </thead>
                  <tbody id="invoice-table-body" class="bg-white divide-y divide-gray-200">
                    <tr class="invoice-row hover:bg-gray-50" data-status="paid" data-customer="acme corp" data-invoice="inv-2024-001">
                      <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">#INV-2024-001</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">Acme Corp</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">$2,340.00</td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <span class="status-badge px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">Paid</span>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">Nov 15, 2024</td>
                    </tr>
                    <tr class="invoice-row hover:bg-gray-50" data-status="pending" data-customer="techflow ltd" data-invoice="inv-2024-002">
                      <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">#INV-2024-002</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">TechFlow Ltd</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">$4,890.00</td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <span class="status-badge px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800">Pending</span>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">Nov 16, 2024</td>
                    </tr>
                    <tr class="invoice-row hover:bg-gray-50" data-status="overdue" data-customer="startupxyz" data-invoice="inv-2024-003">
                      <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">#INV-2024-003</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">StartupXYZ</td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm font-semibold text-gray-900">$1,250.00</td>
                      <td class="px-6 py-4 whitespace-nowrap">
                        <span class="status-badge px-2 py-1 text-xs rounded-full bg-red-100 text-red-800">Overdue</span>
                      </td>
                      <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">Nov 10, 2024</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
          
          <script>
            // Search functionality
            const searchInput = document.getElementById('invoice-search');
            const statusFilter = document.getElementById('status-filter');
            const searchButton = document.getElementById('search-button');
            const clearButton = document.getElementById('clear-button');
            const quickFilters = document.querySelectorAll('.quick-filter');
            const invoiceRows = document.querySelectorAll('.invoice-row');
            const resultsCount = document.getElementById('results-count');
            
            function filterInvoices() {
              const searchTerm = searchInput.value.toLowerCase();
              const statusValue = statusFilter.value.toLowerCase();
              let visibleCount = 0;
              
              invoiceRows.forEach(row => {
                const customer = row.dataset.customer.toLowerCase();
                const invoice = row.dataset.invoice.toLowerCase();
                const status = row.dataset.status.toLowerCase();
                
                const matchesSearch = !searchTerm || 
                  customer.includes(searchTerm) || 
                  invoice.includes(searchTerm);
                const matchesStatus = !statusValue || status === statusValue;
                
                if (matchesSearch && matchesStatus) {
                  row.style.display = '';
                  visibleCount++;
                } else {
                  row.style.display = 'none';
                }
              });
              
              resultsCount.textContent = 'Showing ' + visibleCount + ' invoices';
            }
            
            searchInput.addEventListener('input', filterInvoices);
            statusFilter.addEventListener('change', filterInvoices);
            searchButton.addEventListener('click', filterInvoices);
            
            clearButton.addEventListener('click', () => {
              searchInput.value = '';
              statusFilter.value = '';
              filterInvoices();
            });
            
            quickFilters.forEach(filter => {
              filter.addEventListener('click', () => {
                const filterValue = filter.dataset.filter;
                statusFilter.value = filterValue;
                filterInvoices();
              });
            });
          </script>
        </body>
      </html>
    `);

    // Test search functionality
    await page.fill('#invoice-search', 'acme');
    await page.waitForTimeout(100);
    await expect(page.locator('tr[data-customer="acme corp"]')).toBeVisible();
    await expect(page.locator('tr[data-customer="techflow ltd"]')).not.toBeVisible();
    await expect(page.locator('text=Showing 1 invoices')).toBeVisible();

    // Test status filter
    await page.click('#clear-button');
    await page.selectOption('#status-filter', 'pending');
    await page.waitForTimeout(100);
    await expect(page.locator('tr[data-status="pending"]')).toBeVisible();
    await expect(page.locator('tr[data-status="paid"]')).not.toBeVisible();
    await expect(page.locator('text=Showing 1 invoices')).toBeVisible();

    // Test quick filters
    await page.click('#clear-button');
    await page.click('.quick-filter[data-filter="overdue"]');
    await page.waitForTimeout(100);
    await expect(page.locator('tr[data-status="overdue"]')).toBeVisible();
    await expect(page.locator('tr[data-status="paid"]')).not.toBeVisible();

    // Test combined filters
    await page.fill('#invoice-search', 'inv-2024');
    await page.selectOption('#status-filter', 'paid');
    await page.waitForTimeout(100);
    await expect(page.locator('tr[data-status="paid"]')).toBeVisible();
    await expect(page.locator('tr[data-status="pending"]')).not.toBeVisible();
  });

  test('should test responsive billing dashboard layout @responsive', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    await page.setContent(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Admin Portal - Billing Mobile</title>
          <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-50 min-h-screen">
          <!-- Mobile Header -->
          <header class="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-10">
            <div class="px-4 py-3">
              <div class="flex justify-between items-center">
                <div class="flex items-center space-x-3">
                  <button class="p-2 rounded-md hover:bg-gray-100">
                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"></path>
                    </svg>
                  </button>
                  <div>
                    <h1 class="text-lg font-semibold text-gray-900">Billing</h1>
                  </div>
                </div>
                <button class="p-2 rounded-md hover:bg-gray-100">
                  <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"></path>
                  </svg>
                </button>
              </div>
            </div>
          </header>

          <!-- Mobile Metrics -->
          <div class="p-4 space-y-4">
            <div class="grid grid-cols-2 gap-4">
              <div class="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-4 text-white">
                <p class="text-white/80 text-xs">Monthly Revenue</p>
                <p class="text-xl font-bold">$847K</p>
                <p class="text-white/80 text-xs">+12.3%</p>
              </div>
              <div class="bg-white rounded-xl p-4 shadow-sm border">
                <p class="text-gray-600 text-xs">Outstanding</p>
                <p class="text-xl font-bold text-gray-900">$142K</p>
                <p class="text-red-600 text-xs">23 overdue</p>
              </div>
            </div>
            
            <div class="grid grid-cols-2 gap-4">
              <div class="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-4 text-white">
                <p class="text-white/80 text-xs">Success Rate</p>
                <p class="text-xl font-bold">94.7%</p>
                <p class="text-white/80 text-xs">+2.1%</p>
              </div>
              <div class="bg-white rounded-xl p-4 shadow-sm border">
                <p class="text-gray-600 text-xs">Subscriptions</p>
                <p class="text-xl font-bold text-gray-900">12.8K</p>
                <p class="text-green-600 text-xs">+347</p>
              </div>
            </div>
          </div>

          <!-- Mobile Quick Actions -->
          <div class="px-4 mb-6">
            <div class="grid grid-cols-2 gap-3">
              <button class="bg-blue-600 text-white p-3 rounded-lg text-sm font-medium">
                New Invoice
              </button>
              <button class="bg-green-600 text-white p-3 rounded-lg text-sm font-medium">
                Process Payment
              </button>
            </div>
          </div>

          <!-- Mobile Invoice List -->
          <div class="px-4">
            <div class="bg-white rounded-lg shadow-sm border">
              <div class="p-4 border-b border-gray-200">
                <h3 class="text-lg font-semibold text-gray-900">Recent Invoices</h3>
              </div>
              
              <!-- Mobile Invoice Items -->
              <div class="divide-y divide-gray-200">
                <div class="p-4">
                  <div class="flex justify-between items-start mb-2">
                    <div>
                      <p class="font-medium text-gray-900">#INV-2024-001</p>
                      <p class="text-sm text-gray-600">Acme Corp</p>
                    </div>
                    <div class="text-right">
                      <p class="font-semibold text-gray-900">$2,340</p>
                      <span class="inline-block px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">Paid</span>
                    </div>
                  </div>
                  <div class="flex justify-between text-sm text-gray-500">
                    <span>Nov 15, 2024</span>
                    <button class="text-blue-600">View</button>
                  </div>
                </div>
                
                <div class="p-4">
                  <div class="flex justify-between items-start mb-2">
                    <div>
                      <p class="font-medium text-gray-900">#INV-2024-002</p>
                      <p class="text-sm text-gray-600">TechFlow Ltd</p>
                    </div>
                    <div class="text-right">
                      <p class="font-semibold text-gray-900">$4,890</p>
                      <span class="inline-block px-2 py-1 text-xs rounded-full bg-yellow-100 text-yellow-800">Pending</span>
                    </div>
                  </div>
                  <div class="flex justify-between text-sm text-gray-500">
                    <span>Nov 16, 2024</span>
                    <button class="text-blue-600">View</button>
                  </div>
                </div>
                
                <div class="p-4">
                  <div class="flex justify-between items-start mb-2">
                    <div>
                      <p class="font-medium text-gray-900">#INV-2024-003</p>
                      <p class="text-sm text-gray-600">StartupXYZ</p>
                    </div>
                    <div class="text-right">
                      <p class="font-semibold text-gray-900">$1,250</p>
                      <span class="inline-block px-2 py-1 text-xs rounded-full bg-red-100 text-red-800">Overdue</span>
                    </div>
                  </div>
                  <div class="flex justify-between text-sm text-gray-500">
                    <span>Nov 10, 2024</span>
                    <button class="text-blue-600">View</button>
                  </div>
                </div>
              </div>
              
              <div class="p-4 bg-gray-50 text-center">
                <button class="text-blue-600 text-sm font-medium">View All Invoices</button>
              </div>
            </div>
          </div>

          <!-- Mobile Bottom Navigation -->
          <div class="fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 p-4">
            <div class="grid grid-cols-4 gap-1">
              <button class="flex flex-col items-center p-2 text-blue-600">
                <svg class="w-6 h-6 mb-1" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/>
                </svg>
                <span class="text-xs">Dashboard</span>
              </button>
              <button class="flex flex-col items-center p-2 text-gray-400">
                <svg class="w-6 h-6 mb-1" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6z"/>
                </svg>
                <span class="text-xs">Invoices</span>
              </button>
              <button class="flex flex-col items-center p-2 text-gray-400">
                <svg class="w-6 h-6 mb-1" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
                </svg>
                <span class="text-xs">Reports</span>
              </button>
              <button class="flex flex-col items-center p-2 text-gray-400">
                <svg class="w-6 h-6 mb-1" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
                <span class="text-xs">More</span>
              </button>
            </div>
          </div>
        </body>
      </html>
    `);

    // Test mobile header
    await expect(page.locator('h1:has-text("Billing")')).toBeVisible();
    await expect(page.locator('button svg[viewBox="0 0 24 24"]').first()).toBeVisible(); // Menu button

    // Test mobile metrics grid
    await expect(page.locator('text=$847K')).toBeVisible();
    await expect(page.locator('text=$142K')).toBeVisible();
    await expect(page.locator('text=94.7%')).toBeVisible();
    await expect(page.locator('text=12.8K')).toBeVisible();

    // Test mobile quick actions
    await expect(page.locator('button:has-text("New Invoice")')).toBeVisible();
    await expect(page.locator('button:has-text("Process Payment")')).toBeVisible();

    // Test mobile invoice list
    await expect(page.locator('text=Recent Invoices')).toBeVisible();
    await expect(page.locator('text=#INV-2024-001')).toBeVisible();
    await expect(page.locator('text=Acme Corp')).toBeVisible();
    await expect(page.locator('text=$2,340')).toBeVisible();

    // Test mobile bottom navigation
    await expect(page.locator('text=Dashboard')).toBeVisible();
    await expect(page.locator('button span:has-text("Invoices")')).toBeVisible();
    await expect(page.locator('text=Reports')).toBeVisible();
    await expect(page.locator('text=More')).toBeVisible();

    // Test desktop layout
    await page.setViewportSize({ width: 1024, height: 768 });

    // Desktop version should show different layout
    await page.setContent(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Admin Portal - Billing Desktop</title>
          <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-gray-50 min-h-screen">
          <!-- Desktop Header -->
          <header class="bg-white shadow-sm border-b">
            <div class="max-w-7xl mx-auto px-6 py-4">
              <div class="flex justify-between items-center">
                <h1 class="text-2xl font-bold text-gray-900">Billing Management Dashboard</h1>
                <div class="flex space-x-4">
                  <button class="bg-blue-600 text-white px-6 py-2 rounded-lg">Generate Report</button>
                  <button class="bg-green-600 text-white px-6 py-2 rounded-lg">Export Data</button>
                </div>
              </div>
            </div>
          </header>
          
          <!-- Desktop Metrics Grid -->
          <main class="max-w-7xl mx-auto px-6 py-6">
            <div class="grid grid-cols-4 gap-6 mb-8">
              <div class="bg-white rounded-xl p-6 shadow-sm border">
                <h3 class="text-lg font-semibold text-gray-900">Desktop Layout</h3>
                <p class="text-3xl font-bold text-blue-600 mt-2">$847,329</p>
              </div>
              <div class="bg-white rounded-xl p-6 shadow-sm border">
                <h3 class="text-lg font-semibold text-gray-900">Outstanding</h3>
                <p class="text-3xl font-bold text-red-600 mt-2">$142,847</p>
              </div>
              <div class="bg-white rounded-xl p-6 shadow-sm border">
                <h3 class="text-lg font-semibold text-gray-900">Success Rate</h3>
                <p class="text-3xl font-bold text-green-600 mt-2">94.7%</p>
              </div>
              <div class="bg-white rounded-xl p-6 shadow-sm border">
                <h3 class="text-lg font-semibold text-gray-900">Subscriptions</h3>
                <p class="text-3xl font-bold text-gray-900 mt-2">12,847</p>
              </div>
            </div>
          </main>
        </body>
      </html>
    `);

    // Test desktop layout
    await expect(page.locator('h1:has-text("Billing Management Dashboard")')).toBeVisible();
    await expect(page.locator('button:has-text("Generate Report")')).toBeVisible();
    await expect(page.locator('button:has-text("Export Data")')).toBeVisible();
    await expect(page.locator('text=Desktop Layout')).toBeVisible();
  });
});
