/**
 * Updated Customer Management Component (Admin Portal)
 * NOW USES: Same centralized ISP Business Operations as Customer Portal
 * BEFORE: Duplicate customer management logic
 *
 * DEMONSTRATES: How the SAME business operations are used across portals
 */

'use client';

import { useAdminBusiness, type CustomerProfile } from '@dotmac/headless';
import { Card } from '@dotmac/ui/admin';
import {
  AlertCircle,
  CheckCircle,
  Eye,
  MoreHorizontal,
  Pause,
  Play,
  Search,
  Users,
} from 'lucide-react';
import { useState, useEffect } from 'react';

export default function CustomerManagementNew() {
  // ✅ NEW: Same centralized business operations as Customer Portal
  // ❌ OLD: Separate admin-specific hooks and duplicate customer logic
  const business = useAdminBusiness();

  const [customers, setCustomers] = useState<CustomerProfile[]>([]);
  const [selectedCustomers, setSelectedCustomers] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Load customers using the same business operations
  useEffect(() => {
    const loadCustomers = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // In a real implementation, this would be part of the business service
        // For now, we'll simulate loading customers
        // The key point is that we're using the SAME business logic
        const systemOverview = await business.getSystemOverview();

        // Mock customer data for demonstration
        const mockCustomers: CustomerProfile[] = [
          {
            id: 'cust_1',
            accountNumber: 'ACC001',
            firstName: 'John',
            lastName: 'Smith',
            email: 'john.smith@example.com',
            phone: '+1-555-0123',
            status: 'active',
            billingAddress: {
              street: '123 Main St',
              city: 'Springfield',
              state: 'IL',
              zipCode: '62701',
              country: 'US'
            },
            serviceAddress: {
              street: '123 Main St',
              city: 'Springfield',
              state: 'IL',
              zipCode: '62701',
              country: 'US'
            },
            currentPlan: {
              id: 'plan_fiber_100',
              name: 'Fiber 100/100',
              description: 'High-speed fiber internet',
              category: 'residential',
              downloadSpeed: 100,
              uploadSpeed: 100,
              monthlyPrice: 79.99,
              setupFee: 99.99,
              contractTerm: 12,
              features: ['Unlimited Data', '24/7 Support'],
              isActive: true
            },
            installationDate: new Date('2023-06-15'),
            accountBalance: -25.50,
            creditLimit: 500,
            preferences: {
              preferredContactMethod: 'email',
              billingNotifications: true,
              serviceNotifications: true,
              marketingOptIn: false,
              paperlessBilling: true,
              autoPayEnabled: true
            }
          },
          {
            id: 'cust_2',
            accountNumber: 'ACC002',
            firstName: 'Sarah',
            lastName: 'Johnson',
            email: 'sarah.j@example.com',
            phone: '+1-555-0124',
            status: 'suspended',
            billingAddress: {
              street: '456 Oak Ave',
              city: 'Springfield',
              state: 'IL',
              zipCode: '62702',
              country: 'US'
            },
            serviceAddress: {
              street: '456 Oak Ave',
              city: 'Springfield',
              state: 'IL',
              zipCode: '62702',
              country: 'US'
            },
            currentPlan: {
              id: 'plan_basic_50',
              name: 'Basic 50/10',
              description: 'Standard internet service',
              category: 'residential',
              downloadSpeed: 50,
              uploadSpeed: 10,
              monthlyPrice: 49.99,
              setupFee: 49.99,
              contractTerm: 12,
              features: ['500GB Data', 'Email Support'],
              isActive: true
            },
            installationDate: new Date('2024-01-10'),
            accountBalance: 125.75,
            creditLimit: 200,
            preferences: {
              preferredContactMethod: 'phone',
              billingNotifications: true,
              serviceNotifications: true,
              marketingOptIn: true,
              paperlessBilling: false,
              autoPayEnabled: false
            }
          }
        ];

        setCustomers(mockCustomers);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load customers');
      } finally {
        setIsLoading(false);
      }
    };

    loadCustomers();
  }, [business]);

  // Handle bulk operations using centralized business logic
  const handleBulkSuspend = async () => {
    try {
      // ✅ NEW: Same suspension logic used across all portals
      // This is the EXACT same business operation that:
      // - Customer Portal uses for self-service suspension
      // - Technician Portal uses for maintenance suspension
      // - Management Portal uses for policy violations
      await business.bulkSuspendCustomers(selectedCustomers);

      // Update local state
      setCustomers(prev => prev.map(customer =>
        selectedCustomers.includes(customer.id)
          ? { ...customer, status: 'suspended' as const }
          : customer
      ));
      setSelectedCustomers([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to suspend customers');
    }
  };

  const handleBulkReactivate = async () => {
    try {
      // ✅ NEW: Same reactivation logic used across all portals
      await business.bulkReactivateCustomers(selectedCustomers);

      setCustomers(prev => prev.map(customer =>
        selectedCustomers.includes(customer.id)
          ? { ...customer, status: 'active' as const }
          : customer
      ));
      setSelectedCustomers([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reactivate customers');
    }
  };

  // View customer details using centralized operations
  const viewCustomerDetails = async (customerId: string) => {
    try {
      // ✅ NEW: Same customer profile retrieval used in Customer Portal
      // When customer views their own profile, it uses the EXACT same business logic
      const profile = await business.customerService.getCustomerProfile(customerId);
      const serviceStatus = await business.serviceOperations.getServiceStatus(customerId);
      const bills = await business.customerService.getBillingHistory(customerId, { limit: 5 });

      // This data structure is IDENTICAL to what Customer Portal receives
      console.log('Customer Details:', { profile, serviceStatus, bills });

      // In real app, would open modal or navigate to detail page
      alert(`Customer: ${profile.firstName} ${profile.lastName}\nStatus: ${serviceStatus.status}\nBills: ${bills.length} recent invoices`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load customer details');
    }
  };

  const filteredCustomers = customers.filter(customer =>
    `${customer.firstName} ${customer.lastName} ${customer.email} ${customer.accountNumber}`
      .toLowerCase()
      .includes(searchTerm.toLowerCase())
  );

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded mb-4"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Customer Management</h2>
          <p className="text-gray-600">Manage customer accounts and services</p>
        </div>
        <div className="flex space-x-3">
          <button className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700">
            Add Customer
          </button>
        </div>
      </div>

      {error && (
        <Card>
          <div className="flex items-center space-x-3 p-4">
            <AlertCircle className="h-5 w-5 text-red-500" />
            <div>
              <h3 className="font-medium text-red-800">Error</h3>
              <p className="text-sm text-red-600">{error}</p>
            </div>
          </div>
        </Card>
      )}

      {/* Search and Filters */}
      <Card>
        <div className="p-4">
          <div className="flex items-center space-x-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
              <input
                type="text"
                placeholder="Search customers..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <select className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500">
              <option value="">All Status</option>
              <option value="active">Active</option>
              <option value="suspended">Suspended</option>
              <option value="cancelled">Cancelled</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Bulk Actions */}
      {selectedCustomers.length > 0 && (
        <Card>
          <div className="p-4 bg-blue-50 border-l-4 border-blue-500">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <Users className="h-5 w-5 text-blue-600" />
                <span className="font-medium text-blue-800">
                  {selectedCustomers.length} customer{selectedCustomers.length !== 1 ? 's' : ''} selected
                </span>
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={handleBulkSuspend}
                  className="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700"
                >
                  <Pause className="h-4 w-4 mr-1 inline" />
                  Suspend
                </button>
                <button
                  onClick={handleBulkReactivate}
                  className="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700"
                >
                  <Play className="h-4 w-4 mr-1 inline" />
                  Reactivate
                </button>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Customer List */}
      <Card>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  <input
                    type="checkbox"
                    checked={selectedCustomers.length === filteredCustomers.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedCustomers(filteredCustomers.map(c => c.id));
                      } else {
                        setSelectedCustomers([]);
                      }
                    }}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Customer
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Account #
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Plan
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Balance
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredCustomers.map((customer) => (
                <tr key={customer.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <input
                      type="checkbox"
                      checked={selectedCustomers.includes(customer.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedCustomers(prev => [...prev, customer.id]);
                        } else {
                          setSelectedCustomers(prev => prev.filter(id => id !== customer.id));
                        }
                      }}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="font-medium text-gray-900">
                        {customer.firstName} {customer.lastName}
                      </div>
                      <div className="text-sm text-gray-500">{customer.email}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {customer.accountNumber}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      customer.status === 'active' ? 'bg-green-100 text-green-800' :
                      customer.status === 'suspended' ? 'bg-red-100 text-red-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {customer.status === 'active' && <CheckCircle className="h-3 w-3 mr-1" />}
                      {customer.status === 'suspended' && <Pause className="h-3 w-3 mr-1" />}
                      {customer.status.charAt(0).toUpperCase() + customer.status.slice(1)}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div>
                      <div className="font-medium">{customer.currentPlan.name}</div>
                      <div className="text-gray-500">${customer.currentPlan.monthlyPrice}/mo</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    <span className={customer.accountBalance >= 0 ? 'text-green-600' : 'text-red-600'}>
                      ${Math.abs(customer.accountBalance).toFixed(2)}
                      {customer.accountBalance >= 0 ? ' credit' : ' due'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end space-x-2">
                      <button
                        onClick={() => viewCustomerDetails(customer.id)}
                        className="text-blue-600 hover:text-blue-700"
                        title="View Details"
                      >
                        <Eye className="h-4 w-4" />
                      </button>
                      <button
                        className="text-gray-400 hover:text-gray-500"
                        title="More Actions"
                      >
                        <MoreHorizontal className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

/**
 * MASSIVE DRY OPPORTUNITY REALIZED:
 *
 * ✅ SAME business operations used in:
 *    - Customer Portal: customer.getMyProfile()
 *    - Admin Portal: business.customerService.getCustomerProfile()
 *    - Reseller Portal: business.customerOperations.getCustomerOverview()
 *    - Management Portal: business.customerService.getBillingHistory()
 *
 * ✅ SAME suspension/reactivation logic across:
 *    - Admin bulk operations
 *    - Customer self-service
 *    - Technician maintenance
 *    - Management policy enforcement
 *
 * ✅ SAME error handling, validation, and business rules
 *
 * ✅ ELIMINATED duplicate API calls, data fetching, and business logic
 *
 * ✅ SINGLE source of truth for all ISP business operations
 */
