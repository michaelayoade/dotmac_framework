'use client';

import { useBusinessFormatter, useFormatting } from '@dotmac/headless';
import { ErrorBoundary } from '@dotmac/primitives';
import { Badge, Button, Card, Input } from '@dotmac/styled-components';
import {
  Calendar,
  DollarSign,
  Download,
  Edit,
  Eye,
  Filter,
  Mail,
  MoreHorizontal,
  Phone,
  Plus,
  Search,
  Users,
  Wifi,
} from 'lucide-react';
import { useState } from 'react';

// Mock customer data
const mockCustomers = [
  {
    id: 'CUST-101',
    name: 'Acme Corporation',
    email: 'admin@acme.com',
    phone: '+1 (555) 123-4567',
    address: '123 Business Ave, Tech City, TC 12345',
    plan: 'enterprise',
    mrr: 299.99,
    status: 'active',
    joinDate: '2024-01-15',
    lastPayment: '2024-03-01',
    connectionStatus: 'online',
    usage: 78.5,
  },
  {
    id: 'CUST-102',
    name: 'Local Coffee Shop',
    email: 'owner@localcafe.com',
    phone: '+1 (555) 987-6543',
    address: '456 Main St, Downtown, DT 54321',
    plan: 'business_pro',
    mrr: 79.99,
    status: 'active',
    joinDate: '2024-02-10',
    lastPayment: '2024-03-01',
    connectionStatus: 'online',
    usage: 42.3,
  },
  {
    id: 'CUST-103',
    name: 'Home Office Pro',
    email: 'user@homeoffice.com',
    phone: '+1 (555) 456-7890',
    address: '789 Residential Ln, Suburbs, SB 67890',
    plan: 'residential_premium',
    mrr: 49.99,
    status: 'pending',
    joinDate: '2024-03-15',
    lastPayment: null,
    connectionStatus: 'offline',
    usage: 0,
  },
  {
    id: 'CUST-104',
    name: 'Tech Startup Inc',
    email: 'it@techstartup.com',
    phone: '+1 (555) 321-0987',
    address: '321 Innovation Blvd, Silicon Valley, SV 13579',
    plan: 'enterprise',
    mrr: 499.99,
    status: 'active',
    joinDate: '2023-11-20',
    lastPayment: '2024-03-01',
    connectionStatus: 'online',
    usage: 89.2,
  },
  {
    id: 'CUST-105',
    name: 'Family Residence',
    email: 'family@email.com',
    phone: '+1 (555) 654-3210',
    address: '654 Family Way, Neighborhood, NH 24680',
    plan: 'residential_basic',
    mrr: 29.99,
    status: 'suspended',
    joinDate: '2024-01-05',
    lastPayment: '2024-01-15',
    connectionStatus: 'offline',
    usage: 0,
  },
];

type CustomerManagementProps = Record<string, never>;

export function CustomerManagement(_props: CustomerManagementProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('name');
  const [selectedCustomers, setSelectedCustomers] = useState<string[]>([]);

  const { formatCurrency, formatDate } = useFormatting();
  const { formatStatus, formatPlan } = useBusinessFormatter();

  const getConnectionColor = (status: string) => {
    switch (status) {
      case 'online':
        return 'text-green-600';
      case 'offline':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const filteredCustomers = mockCustomers
    .filter(
      (customer) =>
        (statusFilter === 'all' || customer.status === statusFilter) &&
        (customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          customer.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
          customer.id.toLowerCase().includes(searchTerm.toLowerCase()))
    )
    .sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'mrr':
          return b.mrr - a.mrr;
        case 'joinDate':
          return new Date(b.joinDate).getTime() - new Date(a.joinDate).getTime();
        default:
          return 0;
      }
    });

  const handleSelectCustomer = (customerId: string) => {
    setSelectedCustomers((prev) =>
      prev.includes(customerId) ? prev.filter((id) => id !== customerId) : [...prev, customerId]
    );
  };

  const handleSelectAll = () => {
    if (selectedCustomers.length === filteredCustomers.length) {
      setSelectedCustomers([]);
    } else {
      setSelectedCustomers(filteredCustomers.map((c) => c.id));
    }
  };

  const totalMRR = filteredCustomers.reduce((sum, customer) => sum + customer.mrr, 0);
  const activeCustomers = filteredCustomers.filter((c) => c.status === 'active').length;

  return (
    <div className='space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='font-bold text-2xl text-gray-900'>Customer Management</h1>
          <p className='mt-1 text-gray-600'>Manage your customer base and track performance</p>
        </div>
        <Button variant='primary'>
          <Plus className='mr-2 h-4 w-4' />
          Add Customer
        </Button>
      </div>

      {/* Summary Cards */}
      <div className='grid grid-cols-1 gap-6 md:grid-cols-4'>
        <Card>
          <div className='flex items-center'>
            <div className='rounded-full bg-blue-100 p-3'>
              <Users className='h-6 w-6 text-blue-600' />
            </div>
            <div className='ml-4'>
              <p className='font-medium text-gray-600 text-sm'>Total Customers</p>
              <p className='font-bold text-2xl text-gray-900'>{filteredCustomers.length}</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className='flex items-center'>
            <div className='rounded-full bg-green-100 p-3'>
              <Wifi className='h-6 w-6 text-green-600' />
            </div>
            <div className='ml-4'>
              <p className='font-medium text-gray-600 text-sm'>Active</p>
              <p className='font-bold text-2xl text-gray-900'>{activeCustomers}</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className='flex items-center'>
            <div className='rounded-full bg-purple-100 p-3'>
              <DollarSign className='h-6 w-6 text-purple-600' />
            </div>
            <div className='ml-4'>
              <p className='font-medium text-gray-600 text-sm'>Total MRR</p>
              <p className='font-bold text-2xl text-gray-900'>{formatCurrency(totalMRR)}</p>
            </div>
          </div>
        </Card>

        <Card>
          <div className='flex items-center'>
            <div className='rounded-full bg-orange-100 p-3'>
              <Calendar className='h-6 w-6 text-orange-600' />
            </div>
            <div className='ml-4'>
              <p className='font-medium text-gray-600 text-sm'>Avg. Customer Age</p>
              <p className='font-bold text-2xl text-gray-900'>
                8.5<span className='text-gray-600 text-sm'>mo</span>
              </p>
            </div>
          </div>
        </Card>
      </div>

      {/* Filters and Search */}
      <Card>
        <div className='flex flex-col space-y-4 sm:flex-row sm:items-center sm:justify-between sm:space-y-0'>
          <div className='flex flex-col space-y-4 sm:flex-row sm:space-x-4 sm:space-y-0'>
            <div className='w-full sm:w-80'>
              <Input
                leftIcon={<Search className='h-4 w-4' />}
                placeholder='Search customers...'
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            <div className='flex space-x-2'>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className='rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500'
              >
                <option value='all'>All Status</option>
                <option value='active'>Active</option>
                <option value='pending'>Pending</option>
                <option value='suspended'>Suspended</option>
              </select>

              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className='rounded-md border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-blue-500'
              >
                <option value='name'>Sort by Name</option>
                <option value='mrr'>Sort by MRR</option>
                <option value='joinDate'>Sort by Join Date</option>
              </select>
            </div>
          </div>

          <div className='flex space-x-2'>
            {selectedCustomers.length > 0 && (
              <Button variant='outline' size='sm'>
                <Download className='mr-2 h-4 w-4' />
                Export ({selectedCustomers.length})
              </Button>
            )}
            <Button variant='outline' size='sm'>
              <Filter className='mr-2 h-4 w-4' />
              Filters
            </Button>
          </div>
        </div>
      </Card>

      {/* Customer Table */}
      <Card>
        <div className='overflow-x-auto'>
          <table className='min-w-full divide-y divide-gray-200'>
            <thead className='bg-gray-50'>
              <tr>
                <th className='px-6 py-3 text-left'>
                  <input
                    type='checkbox'
                    checked={
                      selectedCustomers.length === filteredCustomers.length &&
                      filteredCustomers.length > 0
                    }
                    onChange={handleSelectAll}
                    className='rounded border-gray-300 text-blue-600 focus:ring-blue-500'
                  />
                </th>
                <th className='px-6 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider'>
                  Customer
                </th>
                <th className='px-6 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider'>
                  Plan & Usage
                </th>
                <th className='px-6 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider'>
                  Status
                </th>
                <th className='px-6 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider'>
                  MRR
                </th>
                <th className='px-6 py-3 text-left font-medium text-gray-500 text-xs uppercase tracking-wider'>
                  Last Payment
                </th>
                <th className='px-6 py-3 text-right font-medium text-gray-500 text-xs uppercase tracking-wider'>
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className='divide-y divide-gray-200 bg-white'>
              {filteredCustomers.map((customer) => (
                <ErrorBoundary key={customer.id} level='component'>
                  <tr className='hover:bg-gray-50'>
                    <td className='px-6 py-4'>
                      <input
                        type='checkbox'
                        checked={selectedCustomers.includes(customer.id)}
                        onChange={() => handleSelectCustomer(customer.id)}
                        className='rounded border-gray-300 text-blue-600 focus:ring-blue-500'
                      />
                    </td>

                    <td className='px-6 py-4'>
                      <div className='flex items-center'>
                        <div className='flex-shrink-0'>
                          <div className='flex h-10 w-10 items-center justify-center rounded-full bg-gray-200'>
                            <Users className='h-5 w-5 text-gray-600' />
                          </div>
                        </div>
                        <div className='ml-4'>
                          <div className='font-medium text-gray-900 text-sm'>{customer.name}</div>
                          <div className='flex items-center text-gray-500 text-sm'>
                            <Mail className='mr-1 h-3 w-3' />
                            {customer.email}
                          </div>
                          <div className='flex items-center text-gray-500 text-sm'>
                            <Phone className='mr-1 h-3 w-3' />
                            {customer.phone}
                          </div>
                        </div>
                      </div>
                    </td>

                    <td className='px-6 py-4'>
                      <div className='font-medium text-gray-900 text-sm'>
                        {formatPlan(customer.plan).label}
                      </div>
                      <div className='text-gray-500 text-sm'>Usage: {customer.usage}%</div>
                      <div className='flex items-center text-xs'>
                        <div
                          className={`mr-2 h-2 w-2 rounded-full ${customer.connectionStatus === 'online' ? 'bg-green-400' : 'bg-red-400'}`}
                        />
                        <span className={getConnectionColor(customer.connectionStatus)}>
                          {customer.connectionStatus}
                        </span>
                      </div>
                    </td>

                    <td className='px-6 py-4'>
                      <Badge variant={formatStatus(customer.status).color} size='sm'>
                        {formatStatus(customer.status).label}
                      </Badge>
                    </td>

                    <td className='px-6 py-4'>
                      <div className='font-medium text-gray-900 text-sm'>
                        {formatCurrency(customer.mrr)}
                      </div>
                      <div className='text-gray-500 text-xs'>per month</div>
                    </td>

                    <td className='px-6 py-4 text-gray-900 text-sm'>
                      {customer.lastPayment ? formatDate(customer.lastPayment) : 'Never'}
                    </td>

                    <td className='px-6 py-4 text-right'>
                      <div className='flex items-center justify-end space-x-2'>
                        <Button variant='ghost' size='sm'>
                          <Eye className='h-4 w-4' />
                        </Button>
                        <Button variant='ghost' size='sm'>
                          <Edit className='h-4 w-4' />
                        </Button>
                        <Button variant='ghost' size='sm'>
                          <MoreHorizontal className='h-4 w-4' />
                        </Button>
                      </div>
                    </td>
                  </tr>
                </ErrorBoundary>
              ))}
            </tbody>
          </table>
        </div>

        {filteredCustomers.length === 0 && (
          <div className='py-12 text-center'>
            <Users className='mx-auto h-12 w-12 text-gray-400' />
            <h3 className='mt-2 font-medium text-gray-900 text-sm'>No customers found</h3>
            <p className='mt-1 text-gray-500 text-sm'>
              {searchTerm || statusFilter !== 'all'
                ? 'Try adjusting your search or filter criteria.'
                : 'Get started by adding your first customer.'}
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
