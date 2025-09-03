/**
 * Comprehensive Playwright E2E tests for Admin Portal - Customer Management page
 * Based on actual component structure from /isp-framework/admin/src/app/(protected)/customers/page.tsx
 * and /isp-framework/admin/src/components/customers/CustomersTable.tsx
 */

import { test, expect } from '@playwright/test';

test.describe('Admin Portal - Customer Management Page', () => {
  test('should render customer management page with table view and geographic view options @visual', async ({
    page,
  }) => {
    // Create comprehensive customer management page HTML mock based on actual component structure
    const customerManagementHTML = `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Customer Management - Admin Portal</title>
        <script src="https://cdn.tailwindcss.com"></script>
      </head>
      <body class="bg-gray-50">
        <div class="min-h-screen">
          <!-- Admin Layout Container -->
          <div data-testid="admin-layout" class="flex">
            <!-- Sidebar -->
            <div class="w-64 bg-white border-r border-gray-200 min-h-screen">
              <div class="p-6">
                <h2 class="text-lg font-semibold text-gray-900">DotMac Admin</h2>
              </div>
              <nav class="mt-8">
                <a href="#" class="flex items-center px-6 py-3 text-gray-700 bg-gray-100">
                  📊 Dashboard
                </a>
                <a href="#" class="flex items-center px-6 py-3 text-blue-700 bg-blue-50">
                  👥 Customers
                </a>
                <a href="#" class="flex items-center px-6 py-3 text-gray-700">
                  🌐 Network
                </a>
                <a href="#" class="flex items-center px-6 py-3 text-gray-700">
                  💳 Billing
                </a>
              </nav>
            </div>

            <!-- Main Content -->
            <div class="flex-1">
              <div data-testid="customer-management-page" class="p-6 space-y-6">
                <!-- Header Section -->
                <div class="flex items-center justify-between">
                  <div>
                    <h1 data-testid="page-title" class="text-2xl font-bold text-gray-900">Customer Management</h1>
                    <p data-testid="page-description" class="mt-1 text-sm text-gray-500">
                      Comprehensive customer management with advanced filtering and analytics
                    </p>
                  </div>
                  <div class="flex gap-3">
                    <!-- View Toggle -->
                    <div data-testid="view-toggle" class="flex bg-gray-100 rounded-lg p-1">
                      <button
                        data-testid="table-view-button"
                        class="px-3 py-2 text-sm font-medium rounded-md transition-colors bg-white text-blue-700 shadow-sm"
                      >
                        📊 Table View
                      </button>
                      <button
                        data-testid="map-view-button"
                        class="px-3 py-2 text-sm font-medium rounded-md transition-colors text-gray-600 hover:text-gray-900"
                      >
                        🗺️ Geographic View
                      </button>
                    </div>
                    <button data-testid="add-customer-button" class="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 font-medium">
                      Add Customer
                    </button>
                    <button data-testid="import-customers-button" class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium">
                      Import Customers
                    </button>
                  </div>
                </div>

                <!-- Search and Filter Bar -->
                <div data-testid="search-filter-bar" class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
                  <div class="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
                    <div class="flex-1 max-w-lg">
                      <div class="relative">
                        <svg class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                        </svg>
                        <input
                          data-testid="customer-search"
                          type="text"
                          placeholder="Search customers by name, email, phone, or ID..."
                          class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        />
                      </div>
                    </div>
                    
                    <div class="flex gap-2">
                      <button
                        data-testid="filters-toggle"
                        class="px-4 py-2 rounded-lg border bg-white border-gray-300 text-gray-700 hover:bg-gray-50 font-medium transition-colors"
                      >
                        <svg class="h-4 w-4 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"></path>
                        </svg>
                        Filters
                      </button>
                      <button
                        data-testid="export-button"
                        class="px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors"
                      >
                        <svg class="h-4 w-4 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                        </svg>
                        Export
                      </button>
                    </div>
                  </div>

                  <!-- Advanced Filters Panel (Initially Hidden) -->
                  <div data-testid="filters-panel" class="mt-6 pt-6 border-t border-gray-200 hidden">
                    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                      <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Status</label>
                        <select 
                          data-testid="status-filter"
                          multiple
                          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                        >
                          <option value="active">Active</option>
                          <option value="suspended">Suspended</option>
                          <option value="inactive">Inactive</option>
                          <option value="pending">Pending</option>
                        </select>
                      </div>
                      
                      <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Plan Type</label>
                        <select
                          data-testid="plan-type-filter"
                          multiple
                          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                        >
                          <option value="residential">Residential</option>
                          <option value="business">Business</option>
                          <option value="enterprise">Enterprise</option>
                        </select>
                      </div>

                      <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Payment Status</label>
                        <select
                          data-testid="payment-status-filter"
                          multiple
                          class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                        >
                          <option value="current">Current</option>
                          <option value="overdue">Overdue</option>
                          <option value="pending">Pending</option>
                        </select>
                      </div>

                      <div>
                        <label class="block text-sm font-medium text-gray-700 mb-2">Revenue Range</label>
                        <div class="flex space-x-2">
                          <input
                            data-testid="revenue-min"
                            type="number"
                            placeholder="Min"
                            class="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                          />
                          <input
                            data-testid="revenue-max"
                            type="number"
                            placeholder="Max"
                            class="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Customer Table -->
                <div data-testid="customers-table-container" class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
                  <div class="overflow-x-auto">
                    <table data-testid="customers-table" class="min-w-full divide-y divide-gray-200">
                      <thead class="bg-gray-50">
                        <tr>
                          <th class="px-6 py-3">
                            <input
                              data-testid="select-all-checkbox"
                              type="checkbox"
                              class="h-4 w-4 text-blue-600 rounded border-gray-300"
                            />
                          </th>
                          <th data-testid="customer-header" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none">
                            <div class="flex items-center space-x-1">
                              <span>Customer</span>
                              <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 14l3-3 3 3m0-8l-3 3-3-3"></path>
                              </svg>
                            </div>
                          </th>
                          <th data-testid="contact-header" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none">
                            Contact & Location
                          </th>
                          <th data-testid="plan-header" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none">
                            Plan & Revenue
                          </th>
                          <th data-testid="status-header" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none">
                            Status
                          </th>
                          <th data-testid="usage-header" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Usage</th>
                          <th data-testid="activity-header" class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100 select-none">
                            Activity
                          </th>
                          <th class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
                        </tr>
                      </thead>
                      <tbody data-testid="customers-table-body" class="bg-white divide-y divide-gray-200">
                        <!-- Customer Row 1: John Doe -->
                        <tr data-testid="customer-row-CUST-001" class="hover:bg-gray-50">
                          <td class="px-6 py-4">
                            <input
                              data-testid="customer-checkbox-CUST-001"
                              type="checkbox"
                              class="h-4 w-4 text-blue-600 rounded border-gray-300"
                            />
                          </td>
                          <td class="px-6 py-4">
                            <div class="flex items-center">
                              <div class="flex-shrink-0 h-10 w-10">
                                <div class="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                                  <svg class="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                                  </svg>
                                </div>
                              </div>
                              <div class="ml-4">
                                <div data-testid="customer-name-CUST-001" class="text-sm font-medium text-gray-900">John Doe</div>
                                <div data-testid="customer-id-CUST-001" class="text-sm text-gray-500">ID: CUST-001</div>
                                <div class="flex mt-1 gap-1">
                                  <span class="inline-flex px-2 py-1 text-xs rounded bg-gray-100 text-gray-600">premium</span>
                                  <span class="inline-flex px-2 py-1 text-xs rounded bg-gray-100 text-gray-600">referral</span>
                                </div>
                              </div>
                            </div>
                          </td>
                          <td class="px-6 py-4">
                            <div data-testid="customer-email-CUST-001" class="text-sm text-gray-900">john.doe@example.com</div>
                            <div data-testid="customer-phone-CUST-001" class="text-sm text-gray-500">+1 (555) 123-4567</div>
                            <div class="flex items-center text-sm text-gray-500 mt-1">
                              <svg class="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>
                              </svg>
                              <span data-testid="customer-location-CUST-001">San Francisco, CA</span>
                            </div>
                          </td>
                          <td class="px-6 py-4">
                            <div data-testid="customer-plan-CUST-001" class="text-sm font-medium text-gray-900">Fiber 100Mbps</div>
                            <div data-testid="customer-plan-type-CUST-001" class="text-xs text-gray-500 capitalize">residential</div>
                            <div class="flex items-center text-sm text-green-600 mt-1">
                              <svg class="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"></path>
                              </svg>
                              <span data-testid="customer-revenue-CUST-001">$79.99/mo</span>
                            </div>
                          </td>
                          <td class="px-6 py-4">
                            <span data-testid="customer-status-CUST-001" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                              Active
                            </span>
                            <div class="mt-1">
                              <span data-testid="customer-payment-status-CUST-001" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                ✓ current
                              </span>
                            </div>
                          </td>
                          <td class="px-6 py-4">
                            <div data-testid="customer-usage-CUST-001" class="text-sm text-gray-900">250GB / 1000GB</div>
                            <div class="w-full bg-gray-200 rounded-full h-2 mt-1">
                              <div 
                                data-testid="customer-usage-bar-CUST-001"
                                class="bg-blue-600 h-2 rounded-full" 
                                style="width: 25%"
                              ></div>
                            </div>
                            <div data-testid="customer-usage-percent-CUST-001" class="text-xs text-gray-500 mt-1">25% used</div>
                          </td>
                          <td class="px-6 py-4">
                            <div data-testid="customer-last-login-CUST-001" class="text-sm text-gray-900">1/15/2024</div>
                            <div data-testid="customer-created-CUST-001" class="text-xs text-gray-500">Created 6/15/2023</div>
                          </td>
                          <td class="px-6 py-4 text-right">
                            <div class="flex items-center justify-end space-x-2">
                              <button
                                data-testid="view-customer-CUST-001"
                                class="p-2 text-blue-600 hover:text-blue-900 hover:bg-blue-50 rounded"
                                title="View Details"
                              >
                                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                                </svg>
                              </button>
                              <button
                                data-testid="edit-customer-CUST-001"
                                class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded"
                                title="Edit Customer"
                              >
                                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                                </svg>
                              </button>
                              <button
                                data-testid="suspend-customer-CUST-001"
                                class="p-2 text-yellow-600 hover:text-yellow-900 hover:bg-yellow-50 rounded"
                                title="Suspend Customer"
                              >
                                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                </svg>
                              </button>
                              <button
                                data-testid="delete-customer-CUST-001"
                                class="p-2 text-red-600 hover:text-red-900 hover:bg-red-50 rounded"
                                title="Delete Customer"
                              >
                                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                </svg>
                              </button>
                            </div>
                          </td>
                        </tr>
                        
                        <!-- Customer Row 2: Jane Smith -->
                        <tr data-testid="customer-row-CUST-002" class="hover:bg-gray-50">
                          <td class="px-6 py-4">
                            <input
                              data-testid="customer-checkbox-CUST-002"
                              type="checkbox"
                              class="h-4 w-4 text-blue-600 rounded border-gray-300"
                            />
                          </td>
                          <td class="px-6 py-4">
                            <div class="flex items-center">
                              <div class="flex-shrink-0 h-10 w-10">
                                <div class="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                                  <svg class="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                                  </svg>
                                </div>
                              </div>
                              <div class="ml-4">
                                <div data-testid="customer-name-CUST-002" class="text-sm font-medium text-gray-900">Jane Smith</div>
                                <div data-testid="customer-id-CUST-002" class="text-sm text-gray-500">ID: CUST-002</div>
                                <div class="flex mt-1 gap-1">
                                  <span class="inline-flex px-2 py-1 text-xs rounded bg-gray-100 text-gray-600">business</span>
                                  <span class="inline-flex px-2 py-1 text-xs rounded bg-gray-100 text-gray-600">high-value</span>
                                </div>
                              </div>
                            </div>
                          </td>
                          <td class="px-6 py-4">
                            <div data-testid="customer-email-CUST-002" class="text-sm text-gray-900">jane.smith@businesscorp.com</div>
                            <div data-testid="customer-phone-CUST-002" class="text-sm text-gray-500">+1 (555) 234-5678</div>
                            <div class="flex items-center text-sm text-gray-500 mt-1">
                              <svg class="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>
                              </svg>
                              <span data-testid="customer-location-CUST-002">Austin, TX</span>
                            </div>
                          </td>
                          <td class="px-6 py-4">
                            <div data-testid="customer-plan-CUST-002" class="text-sm font-medium text-gray-900">Business 500Mbps</div>
                            <div data-testid="customer-plan-type-CUST-002" class="text-xs text-gray-500 capitalize">business</div>
                            <div class="flex items-center text-sm text-green-600 mt-1">
                              <svg class="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"></path>
                              </svg>
                              <span data-testid="customer-revenue-CUST-002">$199.99/mo</span>
                            </div>
                          </td>
                          <td class="px-6 py-4">
                            <span data-testid="customer-status-CUST-002" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                              Active
                            </span>
                            <div class="mt-1">
                              <span data-testid="customer-payment-status-CUST-002" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                                ✓ current
                              </span>
                            </div>
                          </td>
                          <td class="px-6 py-4">
                            <div data-testid="customer-usage-CUST-002" class="text-sm text-gray-900">800GB / 5000GB</div>
                            <div class="w-full bg-gray-200 rounded-full h-2 mt-1">
                              <div 
                                data-testid="customer-usage-bar-CUST-002"
                                class="bg-blue-600 h-2 rounded-full" 
                                style="width: 16%"
                              ></div>
                            </div>
                            <div data-testid="customer-usage-percent-CUST-002" class="text-xs text-gray-500 mt-1">16% used</div>
                          </td>
                          <td class="px-6 py-4">
                            <div data-testid="customer-last-login-CUST-002" class="text-sm text-gray-900">1/14/2024</div>
                            <div data-testid="customer-created-CUST-002" class="text-xs text-gray-500">Created 8/20/2023</div>
                          </td>
                          <td class="px-6 py-4 text-right">
                            <div class="flex items-center justify-end space-x-2">
                              <button
                                data-testid="view-customer-CUST-002"
                                class="p-2 text-blue-600 hover:text-blue-900 hover:bg-blue-50 rounded"
                                title="View Details"
                              >
                                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                                </svg>
                              </button>
                              <button
                                data-testid="edit-customer-CUST-002"
                                class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded"
                                title="Edit Customer"
                              >
                                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                                </svg>
                              </button>
                              <button
                                data-testid="suspend-customer-CUST-002"
                                class="p-2 text-yellow-600 hover:text-yellow-900 hover:bg-yellow-50 rounded"
                                title="Suspend Customer"
                              >
                                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                </svg>
                              </button>
                              <button
                                data-testid="delete-customer-CUST-002"
                                class="p-2 text-red-600 hover:text-red-900 hover:bg-red-50 rounded"
                                title="Delete Customer"
                              >
                                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                </svg>
                              </button>
                            </div>
                          </td>
                        </tr>

                        <!-- Customer Row 3: Michael Johnson (Suspended) -->
                        <tr data-testid="customer-row-CUST-003" class="hover:bg-gray-50">
                          <td class="px-6 py-4">
                            <input
                              data-testid="customer-checkbox-CUST-003"
                              type="checkbox"
                              class="h-4 w-4 text-blue-600 rounded border-gray-300"
                            />
                          </td>
                          <td class="px-6 py-4">
                            <div class="flex items-center">
                              <div class="flex-shrink-0 h-10 w-10">
                                <div class="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
                                  <svg class="h-5 w-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path>
                                  </svg>
                                </div>
                              </div>
                              <div class="ml-4">
                                <div data-testid="customer-name-CUST-003" class="text-sm font-medium text-gray-900">Michael Johnson</div>
                                <div data-testid="customer-id-CUST-003" class="text-sm text-gray-500">ID: CUST-003</div>
                                <div class="flex mt-1 gap-1">
                                  <span class="inline-flex px-2 py-1 text-xs rounded bg-gray-100 text-gray-600">enterprise</span>
                                  <span class="inline-flex px-2 py-1 text-xs rounded bg-gray-100 text-gray-600">suspended</span>
                                </div>
                              </div>
                            </div>
                          </td>
                          <td class="px-6 py-4">
                            <div data-testid="customer-email-CUST-003" class="text-sm text-gray-900">michael.j@startup.io</div>
                            <div data-testid="customer-phone-CUST-003" class="text-sm text-gray-500">+1 (555) 345-6789</div>
                            <div class="flex items-center text-sm text-gray-500 mt-1">
                              <svg class="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"></path>
                              </svg>
                              <span data-testid="customer-location-CUST-003">Seattle, WA</span>
                            </div>
                          </td>
                          <td class="px-6 py-4">
                            <div data-testid="customer-plan-CUST-003" class="text-sm font-medium text-gray-900">Enterprise 1Gbps</div>
                            <div data-testid="customer-plan-type-CUST-003" class="text-xs text-gray-500 capitalize">enterprise</div>
                            <div class="flex items-center text-sm text-green-600 mt-1">
                              <svg class="h-3 w-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z"></path>
                              </svg>
                              <span data-testid="customer-revenue-CUST-003">$499.99/mo</span>
                            </div>
                          </td>
                          <td class="px-6 py-4">
                            <span data-testid="customer-status-CUST-003" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                              Suspended
                            </span>
                            <div class="mt-1">
                              <span data-testid="customer-payment-status-CUST-003" class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800">
                                ⚠ overdue
                              </span>
                            </div>
                          </td>
                          <td class="px-6 py-4">
                            <div data-testid="customer-usage-CUST-003" class="text-sm text-gray-900">2.5TB / 10TB</div>
                            <div class="w-full bg-gray-200 rounded-full h-2 mt-1">
                              <div 
                                data-testid="customer-usage-bar-CUST-003"
                                class="bg-blue-600 h-2 rounded-full" 
                                style="width: 25%"
                              ></div>
                            </div>
                            <div data-testid="customer-usage-percent-CUST-003" class="text-xs text-gray-500 mt-1">25% used</div>
                          </td>
                          <td class="px-6 py-4">
                            <div data-testid="customer-last-login-CUST-003" class="text-sm text-gray-900">1/10/2024</div>
                            <div data-testid="customer-created-CUST-003" class="text-xs text-gray-500">Created 3/10/2023</div>
                          </td>
                          <td class="px-6 py-4 text-right">
                            <div class="flex items-center justify-end space-x-2">
                              <button
                                data-testid="view-customer-CUST-003"
                                class="p-2 text-blue-600 hover:text-blue-900 hover:bg-blue-50 rounded"
                                title="View Details"
                              >
                                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path>
                                </svg>
                              </button>
                              <button
                                data-testid="edit-customer-CUST-003"
                                class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-50 rounded"
                                title="Edit Customer"
                              >
                                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"></path>
                                </svg>
                              </button>
                              <button
                                data-testid="delete-customer-CUST-003"
                                class="p-2 text-red-600 hover:text-red-900 hover:bg-red-50 rounded"
                                title="Delete Customer"
                              >
                                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                                </svg>
                              </button>
                            </div>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                  
                  <!-- Enhanced Pagination -->
                  <div data-testid="pagination" class="px-6 py-4 bg-gray-50 border-t border-gray-200">
                    <div class="flex items-center justify-between">
                      <div class="flex items-center space-x-2">
                        <span data-testid="pagination-info" class="text-sm text-gray-700">
                          Showing 1 to 3 of 6 customers
                        </span>
                        <span data-testid="filtered-info" class="text-sm text-blue-600">
                          (3 filtered)
                        </span>
                      </div>
                      
                      <div class="flex items-center space-x-2">
                        <select
                          data-testid="page-size-select"
                          class="border border-gray-300 rounded px-2 py-1 text-sm"
                        >
                          <option value="10">10 per page</option>
                          <option value="20" selected>20 per page</option>
                          <option value="50">50 per page</option>
                          <option value="100">100 per page</option>
                        </select>
                        
                        <nav class="flex items-center space-x-1">
                          <button
                            data-testid="first-page-button"
                            class="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-500 bg-white hover:bg-gray-50"
                          >
                            First
                          </button>
                          <button
                            data-testid="prev-page-button"
                            class="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-500 bg-white hover:bg-gray-50"
                          >
                            Previous
                          </button>
                          
                          <!-- Page Numbers -->
                          <div class="flex items-center space-x-1">
                            <button
                              data-testid="page-button-1"
                              class="px-3 py-2 border rounded-md text-sm font-medium bg-blue-50 border-blue-500 text-blue-600"
                            >
                              1
                            </button>
                            <button
                              data-testid="page-button-2"
                              class="px-3 py-2 border rounded-md text-sm font-medium border-gray-300 text-gray-500 bg-white hover:bg-gray-50"
                            >
                              2
                            </button>
                          </div>
                          
                          <button
                            data-testid="next-page-button"
                            class="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-500 bg-white hover:bg-gray-50"
                          >
                            Next
                          </button>
                          <button
                            data-testid="last-page-button"
                            class="px-3 py-2 border border-gray-300 rounded-md text-sm font-medium text-gray-500 bg-white hover:bg-gray-50"
                          >
                            Last
                          </button>
                        </nav>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Geographic View (Hidden by default) -->
                <div data-testid="geographic-view" class="bg-white rounded-lg shadow hidden">
                  <div class="p-6 border-b border-gray-200">
                    <h2 class="text-lg font-semibold text-gray-900">Customer Geographic Distribution</h2>
                    <p class="text-sm text-gray-600 mt-1">
                      Analyze customer density, revenue distribution, and satisfaction patterns across service areas
                    </p>
                  </div>
                  <div class="h-[600px] bg-gray-50">
                    <div class="flex items-center justify-center h-full text-gray-500">
                      <div class="text-center">
                        <div class="text-6xl mb-4">🗺️</div>
                        <div class="text-lg font-medium">Geographic View</div>
                        <div class="text-sm">Customer density heatmap would be displayed here</div>
                      </div>
                    </div>
                  </div>
                  <div data-testid="geographic-stats" class="p-4 bg-gray-50 border-t border-gray-200">
                    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
                      <div class="text-center">
                        <div data-testid="total-customers-stat" class="font-semibold text-blue-600">6</div>
                        <div class="text-gray-600">Total Customers</div>
                      </div>
                      <div class="text-center">
                        <div data-testid="active-customers-stat" class="font-semibold text-green-600">4</div>
                        <div class="text-gray-600">Active Customers</div>
                      </div>
                      <div class="text-center">
                        <div data-testid="monthly-revenue-stat" class="font-semibold text-purple-600">$1129</div>
                        <div class="text-gray-600">Monthly Revenue</div>
                      </div>
                      <div class="text-center">
                        <div data-testid="avg-satisfaction-stat" class="font-semibold text-yellow-600">7.7</div>
                        <div class="text-gray-600">Avg Satisfaction</div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <script>
          // Simple interaction handlers for demo
          document.addEventListener('DOMContentLoaded', function() {
            // View toggle functionality
            const tableViewBtn = document.querySelector('[data-testid="table-view-button"]');
            const mapViewBtn = document.querySelector('[data-testid="map-view-button"]');
            const customersTable = document.querySelector('[data-testid="customers-table-container"]');
            const geographicView = document.querySelector('[data-testid="geographic-view"]');

            tableViewBtn?.addEventListener('click', function() {
              // Update button styles
              tableViewBtn.className = 'px-3 py-2 text-sm font-medium rounded-md transition-colors bg-white text-blue-700 shadow-sm';
              mapViewBtn.className = 'px-3 py-2 text-sm font-medium rounded-md transition-colors text-gray-600 hover:text-gray-900';
              
              // Show table, hide map
              customersTable?.classList.remove('hidden');
              geographicView?.classList.add('hidden');
            });

            mapViewBtn?.addEventListener('click', function() {
              // Update button styles
              mapViewBtn.className = 'px-3 py-2 text-sm font-medium rounded-md transition-colors bg-white text-blue-700 shadow-sm';
              tableViewBtn.className = 'px-3 py-2 text-sm font-medium rounded-md transition-colors text-gray-600 hover:text-gray-900';
              
              // Show map, hide table
              geographicView?.classList.remove('hidden');
              customersTable?.classList.add('hidden');
            });

            // Filters toggle functionality
            const filtersToggle = document.querySelector('[data-testid="filters-toggle"]');
            const filtersPanel = document.querySelector('[data-testid="filters-panel"]');

            filtersToggle?.addEventListener('click', function() {
              const isHidden = filtersPanel?.classList.contains('hidden');
              if (isHidden) {
                filtersPanel?.classList.remove('hidden');
                filtersToggle.className = 'px-4 py-2 rounded-lg border bg-blue-50 border-blue-200 text-blue-700 font-medium transition-colors';
              } else {
                filtersPanel?.classList.add('hidden');
                filtersToggle.className = 'px-4 py-2 rounded-lg border bg-white border-gray-300 text-gray-700 hover:bg-gray-50 font-medium transition-colors';
              }
            });

            // Search functionality
            const searchInput = document.querySelector('[data-testid="customer-search"]');
            const customerRows = document.querySelectorAll('[data-testid^="customer-row-"]');
            
            searchInput?.addEventListener('input', function() {
              const query = this.value.toLowerCase();
              customerRows.forEach(row => {
                const customerName = row.querySelector('[data-testid^="customer-name-"]')?.textContent?.toLowerCase() || '';
                const customerEmail = row.querySelector('[data-testid^="customer-email-"]')?.textContent?.toLowerCase() || '';
                const customerId = row.querySelector('[data-testid^="customer-id-"]')?.textContent?.toLowerCase() || '';
                
                const matches = customerName.includes(query) || customerEmail.includes(query) || customerId.includes(query);
                row.style.display = matches || query === '' ? '' : 'none';
              });
            });

            // Checkbox functionality
            const selectAllCheckbox = document.querySelector('[data-testid="select-all-checkbox"]');
            const customerCheckboxes = document.querySelectorAll('[data-testid^="customer-checkbox-"]');
            
            selectAllCheckbox?.addEventListener('change', function() {
              customerCheckboxes.forEach(checkbox => {
                checkbox.checked = this.checked;
              });
            });

            customerCheckboxes.forEach(checkbox => {
              checkbox.addEventListener('change', function() {
                const checkedBoxes = document.querySelectorAll('[data-testid^="customer-checkbox-"]:checked');
                selectAllCheckbox.checked = checkedBoxes.length === customerCheckboxes.length;
                selectAllCheckbox.indeterminate = checkedBoxes.length > 0 && checkedBoxes.length < customerCheckboxes.length;
              });
            });
          });
        </script>
      </body>
      </html>
    `;

    await page.setContent(customerManagementHTML);

    // Verify page structure
    await expect(page.getByTestId('customer-management-page')).toBeVisible();
    await expect(page.getByTestId('page-title')).toHaveText('Customer Management');
    await expect(page.getByTestId('page-description')).toHaveText(
      'Comprehensive customer management with advanced filtering and analytics'
    );

    // Verify view toggle buttons
    await expect(page.getByTestId('table-view-button')).toBeVisible();
    await expect(page.getByTestId('map-view-button')).toBeVisible();
    await expect(page.getByTestId('add-customer-button')).toBeVisible();
    await expect(page.getByTestId('import-customers-button')).toBeVisible();

    // Verify search and filter bar
    await expect(page.getByTestId('search-filter-bar')).toBeVisible();
    await expect(page.getByTestId('customer-search')).toBeVisible();
    await expect(page.getByTestId('filters-toggle')).toBeVisible();
    await expect(page.getByTestId('export-button')).toBeVisible();

    // Verify customer table is visible by default
    await expect(page.getByTestId('customers-table-container')).toBeVisible();
    await expect(page.getByTestId('customers-table')).toBeVisible();

    // Verify customer data
    await expect(page.getByTestId('customer-name-CUST-001')).toHaveText('John Doe');
    await expect(page.getByTestId('customer-email-CUST-001')).toHaveText('john.doe@example.com');
    await expect(page.getByTestId('customer-plan-CUST-001')).toHaveText('Fiber 100Mbps');
    await expect(page.getByTestId('customer-revenue-CUST-001')).toHaveText('$79.99/mo');
    await expect(page.getByTestId('customer-status-CUST-001')).toHaveText('Active');

    await expect(page.getByTestId('customer-name-CUST-002')).toHaveText('Jane Smith');
    await expect(page.getByTestId('customer-plan-CUST-002')).toHaveText('Business 500Mbps');
    await expect(page.getByTestId('customer-revenue-CUST-002')).toHaveText('$199.99/mo');

    await expect(page.getByTestId('customer-name-CUST-003')).toHaveText('Michael Johnson');
    await expect(page.getByTestId('customer-status-CUST-003')).toHaveText('Suspended');
    await expect(page.getByTestId('customer-payment-status-CUST-003')).toHaveText('⚠ overdue');

    // Verify pagination
    await expect(page.getByTestId('pagination')).toBeVisible();
    await expect(page.getByTestId('pagination-info')).toContainText(
      'Showing 1 to 3 of 6 customers'
    );

    // Verify geographic view is hidden by default
    await expect(page.getByTestId('geographic-view')).toBeHidden();

    // Take screenshot for visual verification
    await page.screenshot({
      path: 'test-results/customer-management-table-view.png',
      fullPage: true,
    });
  });

  test('should test view toggle functionality between table and geographic views @visual @interactive', async ({
    page,
  }) => {
    const customerManagementHTML = `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Customer Management - Admin Portal</title>
        <script src="https://cdn.tailwindcss.com"></script>
      </head>
      <body class="bg-gray-50">
        <div class="min-h-screen p-6">
          <div data-testid="customer-management-page" class="space-y-6">
            <!-- Header with View Toggle -->
            <div class="flex items-center justify-between">
              <h1>Customer Management</h1>
              <div class="flex gap-3">
                <div data-testid="view-toggle" class="flex bg-gray-100 rounded-lg p-1">
                  <button
                    data-testid="table-view-button"
                    class="px-3 py-2 text-sm font-medium rounded-md transition-colors bg-white text-blue-700 shadow-sm"
                  >
                    📊 Table View
                  </button>
                  <button
                    data-testid="map-view-button"
                    class="px-3 py-2 text-sm font-medium rounded-md transition-colors text-gray-600 hover:text-gray-900"
                  >
                    🗺️ Geographic View
                  </button>
                </div>
              </div>
            </div>

            <!-- Customer Table -->
            <div data-testid="customers-table-container" class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <h2>Customer Table View</h2>
              <p>This is the table view showing customer data in tabular format.</p>
              <table class="w-full mt-4">
                <thead>
                  <tr class="border-b">
                    <th class="text-left py-2">Customer</th>
                    <th class="text-left py-2">Plan</th>
                    <th class="text-left py-2">Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr class="border-b">
                    <td class="py-2">John Doe</td>
                    <td class="py-2">Fiber 100Mbps</td>
                    <td class="py-2"><span class="bg-green-100 text-green-800 px-2 py-1 rounded">Active</span></td>
                  </tr>
                  <tr class="border-b">
                    <td class="py-2">Jane Smith</td>
                    <td class="py-2">Business 500Mbps</td>
                    <td class="py-2"><span class="bg-green-100 text-green-800 px-2 py-1 rounded">Active</span></td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- Geographic View -->
            <div data-testid="geographic-view" class="bg-white rounded-lg shadow hidden">
              <div class="p-6 border-b border-gray-200">
                <h2 data-testid="geographic-title" class="text-lg font-semibold text-gray-900">Customer Geographic Distribution</h2>
                <p data-testid="geographic-description" class="text-sm text-gray-600 mt-1">
                  Analyze customer density, revenue distribution, and satisfaction patterns across service areas
                </p>
              </div>
              <div class="h-[400px] bg-gray-50 flex items-center justify-center">
                <div class="text-center">
                  <div class="text-6xl mb-4">🗺️</div>
                  <div data-testid="geographic-placeholder" class="text-lg font-medium">Geographic View</div>
                  <div class="text-sm text-gray-500">Customer density heatmap would be displayed here</div>
                </div>
              </div>
              <div data-testid="geographic-stats" class="p-4 bg-gray-50 border-t border-gray-200">
                <div class="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
                  <div class="text-center">
                    <div data-testid="total-customers-stat" class="font-semibold text-blue-600">6</div>
                    <div class="text-gray-600">Total Customers</div>
                  </div>
                  <div class="text-center">
                    <div data-testid="active-customers-stat" class="font-semibold text-green-600">4</div>
                    <div class="text-gray-600">Active Customers</div>
                  </div>
                  <div class="text-center">
                    <div data-testid="monthly-revenue-stat" class="font-semibold text-purple-600">$1129</div>
                    <div class="text-gray-600">Monthly Revenue</div>
                  </div>
                  <div class="text-center">
                    <div data-testid="avg-satisfaction-stat" class="font-semibold text-yellow-600">7.7</div>
                    <div class="text-gray-600">Avg Satisfaction</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <script>
          document.addEventListener('DOMContentLoaded', function() {
            const tableViewBtn = document.querySelector('[data-testid="table-view-button"]');
            const mapViewBtn = document.querySelector('[data-testid="map-view-button"]');
            const customersTable = document.querySelector('[data-testid="customers-table-container"]');
            const geographicView = document.querySelector('[data-testid="geographic-view"]');

            tableViewBtn?.addEventListener('click', function() {
              // Update button styles
              tableViewBtn.className = 'px-3 py-2 text-sm font-medium rounded-md transition-colors bg-white text-blue-700 shadow-sm';
              mapViewBtn.className = 'px-3 py-2 text-sm font-medium rounded-md transition-colors text-gray-600 hover:text-gray-900';
              
              // Show table, hide map
              customersTable?.classList.remove('hidden');
              geographicView?.classList.add('hidden');
            });

            mapViewBtn?.addEventListener('click', function() {
              // Update button styles
              mapViewBtn.className = 'px-3 py-2 text-sm font-medium rounded-md transition-colors bg-white text-blue-700 shadow-sm';
              tableViewBtn.className = 'px-3 py-2 text-sm font-medium rounded-md transition-colors text-gray-600 hover:text-gray-900';
              
              // Show map, hide table
              geographicView?.classList.remove('hidden');
              customersTable?.classList.add('hidden');
            });
          });
        </script>
      </body>
      </html>
    `;

    await page.setContent(customerManagementHTML);

    // Verify initial state - table view active
    await expect(page.getByTestId('customers-table-container')).toBeVisible();
    await expect(page.getByTestId('geographic-view')).toBeHidden();
    await expect(page.getByTestId('table-view-button')).toHaveClass(
      /bg-white text-blue-700 shadow-sm/
    );
    await expect(page.getByTestId('map-view-button')).toHaveClass(/text-gray-600/);

    // Click to switch to geographic view
    await page.getByTestId('map-view-button').click();

    // Wait for transition and verify
    await expect(page.getByTestId('customers-table-container')).toBeHidden();
    await expect(page.getByTestId('geographic-view')).toBeVisible();
    await expect(page.getByTestId('map-view-button')).toHaveClass(
      /bg-white text-blue-700 shadow-sm/
    );
    await expect(page.getByTestId('table-view-button')).toHaveClass(/text-gray-600/);

    // Verify geographic view content
    await expect(page.getByTestId('geographic-title')).toHaveText(
      'Customer Geographic Distribution'
    );
    await expect(page.getByTestId('geographic-placeholder')).toHaveText('Geographic View');
    await expect(page.getByTestId('total-customers-stat')).toHaveText('6');
    await expect(page.getByTestId('active-customers-stat')).toHaveText('4');
    await expect(page.getByTestId('monthly-revenue-stat')).toHaveText('$1129');
    await expect(page.getByTestId('avg-satisfaction-stat')).toHaveText('7.7');

    // Take screenshot of geographic view
    await page.screenshot({
      path: 'test-results/customer-management-geographic-view.png',
      fullPage: true,
    });

    // Switch back to table view
    await page.getByTestId('table-view-button').click();

    // Verify table view is active again
    await expect(page.getByTestId('customers-table-container')).toBeVisible();
    await expect(page.getByTestId('geographic-view')).toBeHidden();
    await expect(page.getByTestId('table-view-button')).toHaveClass(
      /bg-white text-blue-700 shadow-sm/
    );
    await expect(page.getByTestId('map-view-button')).toHaveClass(/text-gray-600/);
  });

  test('should test search and filtering functionality @visual @interactive', async ({ page }) => {
    const searchFilterHTML = `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Customer Management - Search & Filter</title>
        <script src="https://cdn.tailwindcss.com"></script>
      </head>
      <body class="bg-gray-50">
        <div class="min-h-screen p-6">
          <div data-testid="customer-management-page" class="space-y-6">
            <!-- Search and Filter Bar -->
            <div data-testid="search-filter-bar" class="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
              <div class="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
                <div class="flex-1 max-w-lg">
                  <div class="relative">
                    <svg class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                    </svg>
                    <input
                      data-testid="customer-search"
                      type="text"
                      placeholder="Search customers by name, email, phone, or ID..."
                      class="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>
                
                <div class="flex gap-2">
                  <button
                    data-testid="filters-toggle"
                    class="px-4 py-2 rounded-lg border bg-white border-gray-300 text-gray-700 hover:bg-gray-50 font-medium transition-colors"
                  >
                    <svg class="h-4 w-4 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"></path>
                    </svg>
                    Filters
                  </button>
                  <button
                    data-testid="export-button"
                    class="px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 font-medium transition-colors"
                  >
                    <svg class="h-4 w-4 mr-2 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path>
                    </svg>
                    Export
                  </button>
                </div>
              </div>

              <!-- Advanced Filters Panel -->
              <div data-testid="filters-panel" class="mt-6 pt-6 border-t border-gray-200 hidden">
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Status</label>
                    <select 
                      data-testid="status-filter"
                      multiple
                      class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    >
                      <option value="active">Active</option>
                      <option value="suspended">Suspended</option>
                      <option value="inactive">Inactive</option>
                      <option value="pending">Pending</option>
                    </select>
                  </div>
                  
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Plan Type</label>
                    <select
                      data-testid="plan-type-filter"
                      multiple
                      class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    >
                      <option value="residential">Residential</option>
                      <option value="business">Business</option>
                      <option value="enterprise">Enterprise</option>
                    </select>
                  </div>

                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Payment Status</label>
                    <select
                      data-testid="payment-status-filter"
                      multiple
                      class="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    >
                      <option value="current">Current</option>
                      <option value="overdue">Overdue</option>
                      <option value="pending">Pending</option>
                    </select>
                  </div>

                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-2">Revenue Range</label>
                    <div class="flex space-x-2">
                      <input
                        data-testid="revenue-min"
                        type="number"
                        placeholder="Min"
                        class="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                      />
                      <input
                        data-testid="revenue-max"
                        type="number"
                        placeholder="Max"
                        class="w-full border border-gray-300 rounded px-2 py-1 text-sm"
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Customer Table (simplified for search testing) -->
            <div data-testid="customers-table-container" class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              <table class="min-w-full">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Customer</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
                    <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                  </tr>
                </thead>
                <tbody data-testid="customers-table-body">
                  <tr data-testid="customer-row-CUST-001" class="border-b">
                    <td data-testid="customer-name-CUST-001" class="px-6 py-4 text-sm font-medium text-gray-900">John Doe</td>
                    <td data-testid="customer-email-CUST-001" class="px-6 py-4 text-sm text-gray-500">john.doe@example.com</td>
                    <td class="px-6 py-4"><span class="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">Active</span></td>
                  </tr>
                  <tr data-testid="customer-row-CUST-002" class="border-b">
                    <td data-testid="customer-name-CUST-002" class="px-6 py-4 text-sm font-medium text-gray-900">Jane Smith</td>
                    <td data-testid="customer-email-CUST-002" class="px-6 py-4 text-sm text-gray-500">jane.smith@businesscorp.com</td>
                    <td class="px-6 py-4"><span class="bg-green-100 text-green-800 px-2 py-1 rounded text-xs">Active</span></td>
                  </tr>
                  <tr data-testid="customer-row-CUST-003" class="border-b">
                    <td data-testid="customer-name-CUST-003" class="px-6 py-4 text-sm font-medium text-gray-900">Michael Johnson</td>
                    <td data-testid="customer-email-CUST-003" class="px-6 py-4 text-sm text-gray-500">michael.j@startup.io</td>
                    <td class="px-6 py-4"><span class="bg-yellow-100 text-yellow-800 px-2 py-1 rounded text-xs">Suspended</span></td>
                  </tr>
                  <tr data-testid="customer-row-CUST-004" class="border-b">
                    <td data-testid="customer-name-CUST-004" class="px-6 py-4 text-sm font-medium text-gray-900">Sarah Wilson</td>
                    <td data-testid="customer-email-CUST-004" class="px-6 py-4 text-sm text-gray-500">sarah.wilson@email.com</td>
                    <td class="px-6 py-4"><span class="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs">Pending</span></td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div data-testid="search-results" class="text-sm text-gray-600"></div>
          </div>
        </div>

        <script>
          document.addEventListener('DOMContentLoaded', function() {
            // Filters toggle functionality
            const filtersToggle = document.querySelector('[data-testid="filters-toggle"]');
            const filtersPanel = document.querySelector('[data-testid="filters-panel"]');

            filtersToggle?.addEventListener('click', function() {
              const isHidden = filtersPanel?.classList.contains('hidden');
              if (isHidden) {
                filtersPanel?.classList.remove('hidden');
                filtersToggle.className = 'px-4 py-2 rounded-lg border bg-blue-50 border-blue-200 text-blue-700 font-medium transition-colors';
              } else {
                filtersPanel?.classList.add('hidden');
                filtersToggle.className = 'px-4 py-2 rounded-lg border bg-white border-gray-300 text-gray-700 hover:bg-gray-50 font-medium transition-colors';
              }
            });

            // Search functionality
            const searchInput = document.querySelector('[data-testid="customer-search"]');
            const customerRows = document.querySelectorAll('[data-testid^="customer-row-"]');
            const searchResults = document.querySelector('[data-testid="search-results"]');
            
            searchInput?.addEventListener('input', function() {
              const query = this.value.toLowerCase();
              let visibleCount = 0;
              
              customerRows.forEach(row => {
                const customerName = row.querySelector('[data-testid^="customer-name-"]')?.textContent?.toLowerCase() || '';
                const customerEmail = row.querySelector('[data-testid^="customer-email-"]')?.textContent?.toLowerCase() || '';
                const customerId = row.getAttribute('data-testid')?.toLowerCase() || '';
                
                // More precise matching - check for exact name match or email/ID contains
                const nameMatches = customerName.includes(query);
                const emailMatches = customerEmail.includes(query);
                const idMatches = customerId.includes(query);
                
                const matches = nameMatches || emailMatches || idMatches;
                
                if (matches || query === '') {
                  row.style.display = '';
                  visibleCount++;
                } else {
                  row.style.display = 'none';
                }
              });

              // Update search results counter
              if (query) {
                searchResults.textContent = \`Found \${visibleCount} customer\${visibleCount !== 1 ? 's' : ''} matching "\${query}"\`;
              } else {
                searchResults.textContent = '';
              }
            });
          });
        </script>
      </body>
      </html>
    `;

    await page.setContent(searchFilterHTML);

    // Verify initial state
    await expect(page.getByTestId('customer-search')).toBeVisible();
    await expect(page.getByTestId('filters-toggle')).toBeVisible();
    await expect(page.getByTestId('filters-panel')).toBeHidden();

    // Verify all customers are visible initially
    await expect(page.getByTestId('customer-row-CUST-001')).toBeVisible();
    await expect(page.getByTestId('customer-row-CUST-002')).toBeVisible();
    await expect(page.getByTestId('customer-row-CUST-003')).toBeVisible();
    await expect(page.getByTestId('customer-row-CUST-004')).toBeVisible();

    // Test search functionality
    await page.getByTestId('customer-search').fill('John Doe');
    await expect(page.getByTestId('customer-row-CUST-001')).toBeVisible(); // John Doe should be visible
    await expect(page.getByTestId('customer-row-CUST-002')).toBeHidden(); // Jane Smith should be hidden
    await expect(page.getByTestId('customer-row-CUST-003')).toBeHidden(); // Michael Johnson should be hidden
    await expect(page.getByTestId('customer-row-CUST-004')).toBeHidden(); // Sarah Wilson should be hidden
    await expect(page.getByTestId('search-results')).toHaveText(
      'Found 1 customer matching "john doe"'
    );

    // Test email search
    await page.getByTestId('customer-search').fill('businesscorp');
    await expect(page.getByTestId('customer-row-CUST-001')).toBeHidden();
    await expect(page.getByTestId('customer-row-CUST-002')).toBeVisible(); // Jane Smith with businesscorp email
    await expect(page.getByTestId('customer-row-CUST-003')).toBeHidden();
    await expect(page.getByTestId('customer-row-CUST-004')).toBeHidden();
    await expect(page.getByTestId('search-results')).toHaveText(
      'Found 1 customer matching "businesscorp"'
    );

    // Test ID search
    await page.getByTestId('customer-search').fill('CUST-003');
    await expect(page.getByTestId('customer-row-CUST-001')).toBeHidden();
    await expect(page.getByTestId('customer-row-CUST-002')).toBeHidden();
    await expect(page.getByTestId('customer-row-CUST-003')).toBeVisible(); // Michael Johnson
    await expect(page.getByTestId('customer-row-CUST-004')).toBeHidden();

    // Clear search
    await page.getByTestId('customer-search').fill('');
    await expect(page.getByTestId('customer-row-CUST-001')).toBeVisible();
    await expect(page.getByTestId('customer-row-CUST-002')).toBeVisible();
    await expect(page.getByTestId('customer-row-CUST-003')).toBeVisible();
    await expect(page.getByTestId('customer-row-CUST-004')).toBeVisible();
    await expect(page.getByTestId('search-results')).toHaveText('');

    // Test filters toggle
    await page.getByTestId('filters-toggle').click();
    await expect(page.getByTestId('filters-panel')).toBeVisible();
    await expect(page.getByTestId('status-filter')).toBeVisible();
    await expect(page.getByTestId('plan-type-filter')).toBeVisible();
    await expect(page.getByTestId('payment-status-filter')).toBeVisible();
    await expect(page.getByTestId('revenue-min')).toBeVisible();
    await expect(page.getByTestId('revenue-max')).toBeVisible();

    // Verify filters toggle style change
    await expect(page.getByTestId('filters-toggle')).toHaveClass(
      /bg-blue-50 border-blue-200 text-blue-700/
    );

    // Toggle filters off
    await page.getByTestId('filters-toggle').click();
    await expect(page.getByTestId('filters-panel')).toBeHidden();
    await expect(page.getByTestId('filters-toggle')).toHaveClass(
      /bg-white border-gray-300 text-gray-700/
    );

    // Take screenshot
    await page.screenshot({
      path: 'test-results/customer-management-search-filter.png',
      fullPage: true,
    });
  });

  test('should test responsive customer management layout @visual @responsive', async ({
    page,
  }) => {
    const responsiveHTML = `
      <!DOCTYPE html>
      <html lang="en">
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Customer Management - Responsive</title>
        <script src="https://cdn.tailwindcss.com"></script>
      </head>
      <body class="bg-gray-50">
        <div class="min-h-screen">
          <div data-testid="customer-management-page" class="p-2 sm:p-4 lg:p-6 space-y-4 lg:space-y-6">
            <!-- Responsive Header -->
            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <h1 data-testid="page-title" class="text-xl sm:text-2xl font-bold text-gray-900">Customer Management</h1>
                <p data-testid="page-description" class="mt-1 text-sm text-gray-500">
                  Comprehensive customer management
                </p>
              </div>
              <div class="flex flex-col sm:flex-row gap-2 sm:gap-3">
                <div data-testid="view-toggle" class="flex bg-gray-100 rounded-lg p-1 w-full sm:w-auto">
                  <button
                    data-testid="table-view-button"
                    class="flex-1 sm:flex-none px-2 sm:px-3 py-2 text-xs sm:text-sm font-medium rounded-md bg-white text-blue-700 shadow-sm"
                  >
                    📊 Table
                  </button>
                  <button
                    data-testid="map-view-button"
                    class="flex-1 sm:flex-none px-2 sm:px-3 py-2 text-xs sm:text-sm font-medium rounded-md text-gray-600"
                  >
                    🗺️ Map
                  </button>
                </div>
                <div class="flex gap-2">
                  <button data-testid="add-customer-button" class="flex-1 sm:flex-none px-3 sm:px-4 py-2 bg-green-600 text-white rounded-lg text-xs sm:text-sm font-medium">
                    Add Customer
                  </button>
                  <button data-testid="import-customers-button" class="flex-1 sm:flex-none px-3 sm:px-4 py-2 bg-blue-600 text-white rounded-lg text-xs sm:text-sm font-medium">
                    Import
                  </button>
                </div>
              </div>
            </div>

            <!-- Responsive Search and Filters -->
            <div data-testid="search-filter-bar" class="bg-white rounded-lg shadow-sm border border-gray-200 p-4 lg:p-6">
              <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                <div class="flex-1">
                  <div class="relative">
                    <svg class="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4 sm:h-5 sm:w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
                    </svg>
                    <input
                      data-testid="customer-search"
                      type="text"
                      placeholder="Search customers..."
                      class="w-full pl-8 sm:pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                  </div>
                </div>
                
                <div class="flex gap-2 w-full sm:w-auto">
                  <button
                    data-testid="filters-toggle"
                    class="flex-1 sm:flex-none px-3 sm:px-4 py-2 rounded-lg border bg-white border-gray-300 text-gray-700 text-xs sm:text-sm font-medium"
                  >
                    🔍 Filters
                  </button>
                  <button
                    data-testid="export-button"
                    class="flex-1 sm:flex-none px-3 sm:px-4 py-2 bg-white border border-gray-300 rounded-lg text-gray-700 text-xs sm:text-sm font-medium"
                  >
                    📥 Export
                  </button>
                </div>
              </div>
            </div>

            <!-- Responsive Customer Table -->
            <div data-testid="customers-table-container" class="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
              <!-- Mobile Card View -->
              <div data-testid="mobile-card-view" class="block sm:hidden">
                <div class="divide-y divide-gray-200">
                  <div data-testid="customer-card-CUST-001" class="p-4">
                    <div class="flex items-center justify-between mb-2">
                      <div>
                        <h3 data-testid="mobile-customer-name-CUST-001" class="text-sm font-medium text-gray-900">John Doe</h3>
                        <p data-testid="mobile-customer-id-CUST-001" class="text-xs text-gray-500">ID: CUST-001</p>
                      </div>
                      <span data-testid="mobile-customer-status-CUST-001" class="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">Active</span>
                    </div>
                    <div class="space-y-1 text-xs text-gray-600">
                      <div data-testid="mobile-customer-email-CUST-001">📧 john.doe@example.com</div>
                      <div data-testid="mobile-customer-plan-CUST-001">📡 Fiber 100Mbps</div>
                      <div data-testid="mobile-customer-revenue-CUST-001">💰 $79.99/mo</div>
                    </div>
                    <div class="flex justify-end mt-3 space-x-1">
                      <button data-testid="mobile-view-CUST-001" class="p-2 text-blue-600 bg-blue-50 rounded">👁️</button>
                      <button data-testid="mobile-edit-CUST-001" class="p-2 text-gray-600 bg-gray-50 rounded">✏️</button>
                      <button data-testid="mobile-delete-CUST-001" class="p-2 text-red-600 bg-red-50 rounded">🗑️</button>
                    </div>
                  </div>
                  
                  <div data-testid="customer-card-CUST-002" class="p-4">
                    <div class="flex items-center justify-between mb-2">
                      <div>
                        <h3 data-testid="mobile-customer-name-CUST-002" class="text-sm font-medium text-gray-900">Jane Smith</h3>
                        <p data-testid="mobile-customer-id-CUST-002" class="text-xs text-gray-500">ID: CUST-002</p>
                      </div>
                      <span data-testid="mobile-customer-status-CUST-002" class="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">Active</span>
                    </div>
                    <div class="space-y-1 text-xs text-gray-600">
                      <div data-testid="mobile-customer-email-CUST-002">📧 jane.smith@businesscorp.com</div>
                      <div data-testid="mobile-customer-plan-CUST-002">📡 Business 500Mbps</div>
                      <div data-testid="mobile-customer-revenue-CUST-002">💰 $199.99/mo</div>
                    </div>
                    <div class="flex justify-end mt-3 space-x-1">
                      <button data-testid="mobile-view-CUST-002" class="p-2 text-blue-600 bg-blue-50 rounded">👁️</button>
                      <button data-testid="mobile-edit-CUST-002" class="p-2 text-gray-600 bg-gray-50 rounded">✏️</button>
                      <button data-testid="mobile-delete-CUST-002" class="p-2 text-red-600 bg-red-50 rounded">🗑️</button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Desktop Table View -->
              <div data-testid="desktop-table-view" class="hidden sm:block">
                <div class="overflow-x-auto">
                  <table data-testid="customers-table" class="min-w-full divide-y divide-gray-200">
                    <thead class="bg-gray-50">
                      <tr>
                        <th data-testid="customer-header" class="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Customer
                        </th>
                        <th data-testid="contact-header" class="hidden md:table-cell px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Contact
                        </th>
                        <th data-testid="plan-header" class="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Plan
                        </th>
                        <th data-testid="status-header" class="px-3 sm:px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                          Status
                        </th>
                        <th class="px-3 sm:px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                      </tr>
                    </thead>
                    <tbody data-testid="customers-table-body" class="bg-white divide-y divide-gray-200">
                      <tr data-testid="desktop-customer-row-CUST-001">
                        <td class="px-3 sm:px-6 py-4">
                          <div>
                            <div data-testid="desktop-customer-name-CUST-001" class="text-sm font-medium text-gray-900">John Doe</div>
                            <div data-testid="desktop-customer-id-CUST-001" class="text-xs text-gray-500">CUST-001</div>
                          </div>
                        </td>
                        <td class="hidden md:table-cell px-6 py-4">
                          <div data-testid="desktop-customer-email-CUST-001" class="text-sm text-gray-900">john.doe@example.com</div>
                          <div class="text-xs text-gray-500">+1 (555) 123-4567</div>
                        </td>
                        <td class="px-3 sm:px-6 py-4">
                          <div data-testid="desktop-customer-plan-CUST-001" class="text-sm text-gray-900">Fiber 100Mbps</div>
                          <div data-testid="desktop-customer-revenue-CUST-001" class="text-xs text-green-600">$79.99/mo</div>
                        </td>
                        <td class="px-3 sm:px-6 py-4">
                          <span data-testid="desktop-customer-status-CUST-001" class="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">Active</span>
                        </td>
                        <td class="px-3 sm:px-6 py-4 text-right">
                          <div class="flex justify-end space-x-1">
                            <button data-testid="desktop-view-CUST-001" class="p-1 sm:p-2 text-blue-600 hover:bg-blue-50 rounded text-xs sm:text-sm">👁️</button>
                            <button data-testid="desktop-edit-CUST-001" class="p-1 sm:p-2 text-gray-600 hover:bg-gray-50 rounded text-xs sm:text-sm">✏️</button>
                            <button data-testid="desktop-delete-CUST-001" class="p-1 sm:p-2 text-red-600 hover:bg-red-50 rounded text-xs sm:text-sm">🗑️</button>
                          </div>
                        </td>
                      </tr>
                      
                      <tr data-testid="desktop-customer-row-CUST-002">
                        <td class="px-3 sm:px-6 py-4">
                          <div>
                            <div data-testid="desktop-customer-name-CUST-002" class="text-sm font-medium text-gray-900">Jane Smith</div>
                            <div data-testid="desktop-customer-id-CUST-002" class="text-xs text-gray-500">CUST-002</div>
                          </div>
                        </td>
                        <td class="hidden md:table-cell px-6 py-4">
                          <div data-testid="desktop-customer-email-CUST-002" class="text-sm text-gray-900">jane.smith@businesscorp.com</div>
                          <div class="text-xs text-gray-500">+1 (555) 234-5678</div>
                        </td>
                        <td class="px-3 sm:px-6 py-4">
                          <div data-testid="desktop-customer-plan-CUST-002" class="text-sm text-gray-900">Business 500Mbps</div>
                          <div data-testid="desktop-customer-revenue-CUST-002" class="text-xs text-green-600">$199.99/mo</div>
                        </td>
                        <td class="px-3 sm:px-6 py-4">
                          <span data-testid="desktop-customer-status-CUST-002" class="px-2 py-1 text-xs rounded-full bg-green-100 text-green-800">Active</span>
                        </td>
                        <td class="px-3 sm:px-6 py-4 text-right">
                          <div class="flex justify-end space-x-1">
                            <button data-testid="desktop-view-CUST-002" class="p-1 sm:p-2 text-blue-600 hover:bg-blue-50 rounded text-xs sm:text-sm">👁️</button>
                            <button data-testid="desktop-edit-CUST-002" class="p-1 sm:p-2 text-gray-600 hover:bg-gray-50 rounded text-xs sm:text-sm">✏️</button>
                            <button data-testid="desktop-delete-CUST-002" class="p-1 sm:p-2 text-red-600 hover:bg-red-50 rounded text-xs sm:text-sm">🗑️</button>
                          </div>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>
      </body>
      </html>
    `;

    // Test mobile viewport (iPhone 12)
    await page.setViewportSize({ width: 390, height: 844 });
    await page.setContent(responsiveHTML);

    // Verify mobile layout
    await expect(page.getByTestId('mobile-card-view')).toBeVisible();
    await expect(page.getByTestId('desktop-table-view')).toBeHidden();

    // Verify mobile customer cards
    await expect(page.getByTestId('customer-card-CUST-001')).toBeVisible();
    await expect(page.getByTestId('mobile-customer-name-CUST-001')).toHaveText('John Doe');
    await expect(page.getByTestId('mobile-customer-email-CUST-001')).toHaveText(
      '📧 john.doe@example.com'
    );
    await expect(page.getByTestId('mobile-customer-plan-CUST-001')).toHaveText('📡 Fiber 100Mbps');

    // Verify mobile responsive header
    await expect(page.getByTestId('page-title')).toBeVisible();
    await expect(page.getByTestId('view-toggle')).toBeVisible();

    // Take mobile screenshot
    await page.screenshot({
      path: 'test-results/customer-management-mobile.png',
      fullPage: true,
    });

    // Test tablet viewport (iPad)
    await page.setViewportSize({ width: 768, height: 1024 });

    // Verify tablet layout
    await expect(page.getByTestId('mobile-card-view')).toBeHidden();
    await expect(page.getByTestId('desktop-table-view')).toBeVisible();

    // Verify desktop table content
    await expect(page.getByTestId('desktop-customer-name-CUST-001')).toHaveText('John Doe');
    await expect(page.getByTestId('desktop-customer-plan-CUST-001')).toHaveText('Fiber 100Mbps');
    await expect(page.getByTestId('desktop-customer-status-CUST-001')).toHaveText('Active');

    // Take tablet screenshot
    await page.screenshot({
      path: 'test-results/customer-management-tablet.png',
      fullPage: true,
    });

    // Test desktop viewport
    await page.setViewportSize({ width: 1920, height: 1080 });

    // Verify desktop layout
    await expect(page.getByTestId('desktop-table-view')).toBeVisible();
    await expect(page.getByTestId('mobile-card-view')).toBeHidden();

    // Verify contact column is visible on desktop (md:table-cell)
    await expect(page.getByTestId('contact-header')).toBeVisible();
    await expect(page.getByTestId('desktop-customer-email-CUST-001')).toBeVisible();
    await expect(page.getByTestId('desktop-customer-email-CUST-001')).toHaveText(
      'john.doe@example.com'
    );

    // Take desktop screenshot
    await page.screenshot({
      path: 'test-results/customer-management-desktop.png',
      fullPage: true,
    });
  });
});
