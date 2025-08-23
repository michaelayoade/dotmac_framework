'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/Card';
import { Button } from '../../ui/Button';
import { Input } from '../../ui/Input';
import { Users, Plus, Search, Edit, Eye, UserPlus } from 'lucide-react';

interface Customer {
  id: string;
  name: string;
  email: string;
  phone: string;
  status: 'active' | 'suspended' | 'pending';
  services_count: number;
  portal_id: string;
  created_at: string;
}

export function CustomerManagement() {
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    fetchCustomers();
  }, []);

  const fetchCustomers = async () => {
    try {
      const response = await fetch('/api/isp/identity/customers', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('isp-admin-token')}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setCustomers(data.customers || []);
      } else {
        // Demo data fallback
        setCustomers([
          {
            id: '1',
            name: 'John Smith',
            email: 'john@example.com',
            phone: '+1-555-0123',
            status: 'active',
            services_count: 2,
            portal_id: 'ABC123XY',
            created_at: '2024-01-15T10:30:00Z',
          },
          {
            id: '2',
            name: 'Jane Doe',
            email: 'jane@example.com',
            phone: '+1-555-0124',
            status: 'active',
            services_count: 1,
            portal_id: 'DEF456ZW',
            created_at: '2024-01-14T14:20:00Z',
          },
          {
            id: '3',
            name: 'Bob Johnson',
            email: 'bob@example.com',
            phone: '+1-555-0125',
            status: 'pending',
            services_count: 0,
            portal_id: 'GHI789UV',
            created_at: '2024-01-16T09:15:00Z',
          },
        ]);
      }
    } catch (error) {
      console.error('Failed to fetch customers:', error);
      // Use demo data on error
      setCustomers([
        {
          id: '1',
          name: 'John Smith',
          email: 'john@example.com',
          phone: '+1-555-0123',
          status: 'active',
          services_count: 2,
          portal_id: 'ABC123XY',
          created_at: '2024-01-15T10:30:00Z',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'suspended':
        return 'bg-red-100 text-red-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const filteredCustomers = customers.filter(
    (customer) =>
      customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      customer.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      customer.portal_id.toLowerCase().includes(searchTerm.toLowerCase())
  );

  if (loading) {
    return (
      <div className='flex items-center justify-center h-64'>
        <div className='animate-spin rounded-full h-8 w-8 border-2 border-blue-600 border-t-transparent'></div>
      </div>
    );
  }

  return (
    <div className='space-y-6'>
      {/* Header */}
      <div className='flex items-center justify-between'>
        <div>
          <h1 className='text-2xl font-bold text-gray-900'>Customer Management</h1>
          <p className='text-gray-600'>Manage customer accounts and Portal ID authentication</p>
        </div>
        <Button className='flex items-center'>
          <UserPlus className='w-4 h-4 mr-2' />
          Add Customer
        </Button>
      </div>

      {/* Stats Cards */}
      <div className='grid grid-cols-1 md:grid-cols-4 gap-6'>
        <Card>
          <CardContent className='p-6'>
            <div className='flex items-center'>
              <Users className='w-8 h-8 text-blue-600' />
              <div className='ml-4'>
                <p className='text-sm font-medium text-gray-600'>Total Customers</p>
                <p className='text-2xl font-bold text-gray-900'>{customers.length}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6'>
            <div className='flex items-center'>
              <div className='w-8 h-8 bg-green-100 rounded-full flex items-center justify-center'>
                <div className='w-3 h-3 bg-green-500 rounded-full'></div>
              </div>
              <div className='ml-4'>
                <p className='text-sm font-medium text-gray-600'>Active</p>
                <p className='text-2xl font-bold text-gray-900'>
                  {customers.filter((c) => c.status === 'active').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6'>
            <div className='flex items-center'>
              <div className='w-8 h-8 bg-yellow-100 rounded-full flex items-center justify-center'>
                <div className='w-3 h-3 bg-yellow-500 rounded-full'></div>
              </div>
              <div className='ml-4'>
                <p className='text-sm font-medium text-gray-600'>Pending</p>
                <p className='text-2xl font-bold text-gray-900'>
                  {customers.filter((c) => c.status === 'pending').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6'>
            <div className='flex items-center'>
              <div className='w-8 h-8 bg-red-100 rounded-full flex items-center justify-center'>
                <div className='w-3 h-3 bg-red-500 rounded-full'></div>
              </div>
              <div className='ml-4'>
                <p className='text-sm font-medium text-gray-600'>Suspended</p>
                <p className='text-2xl font-bold text-gray-900'>
                  {customers.filter((c) => c.status === 'suspended').length}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Search and Filter */}
      <Card>
        <CardContent className='p-6'>
          <div className='flex items-center space-x-4'>
            <div className='relative flex-1'>
              <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4' />
              <Input
                placeholder='Search customers by name, email, or Portal ID...'
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className='pl-10'
              />
            </div>
            <Button variant='outline'>Filter</Button>
          </div>
        </CardContent>
      </Card>

      {/* Customer List */}
      <Card>
        <CardHeader>
          <CardTitle>Customer Accounts</CardTitle>
        </CardHeader>
        <CardContent>
          <div className='overflow-x-auto'>
            <table className='w-full'>
              <thead>
                <tr className='border-b'>
                  <th className='text-left py-3 px-4 font-medium text-gray-600'>Customer</th>
                  <th className='text-left py-3 px-4 font-medium text-gray-600'>Portal ID</th>
                  <th className='text-left py-3 px-4 font-medium text-gray-600'>Status</th>
                  <th className='text-left py-3 px-4 font-medium text-gray-600'>Services</th>
                  <th className='text-left py-3 px-4 font-medium text-gray-600'>Created</th>
                  <th className='text-left py-3 px-4 font-medium text-gray-600'>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredCustomers.map((customer) => (
                  <tr key={customer.id} className='border-b hover:bg-gray-50'>
                    <td className='py-3 px-4'>
                      <div>
                        <div className='font-medium text-gray-900'>{customer.name}</div>
                        <div className='text-sm text-gray-500'>{customer.email}</div>
                        <div className='text-sm text-gray-500'>{customer.phone}</div>
                      </div>
                    </td>
                    <td className='py-3 px-4'>
                      <code className='bg-gray-100 px-2 py-1 rounded text-sm'>
                        {customer.portal_id}
                      </code>
                    </td>
                    <td className='py-3 px-4'>
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(customer.status)}`}
                      >
                        {customer.status}
                      </span>
                    </td>
                    <td className='py-3 px-4'>
                      <span className='text-gray-900'>{customer.services_count}</span>
                    </td>
                    <td className='py-3 px-4'>
                      <span className='text-sm text-gray-500'>
                        {new Date(customer.created_at).toLocaleDateString()}
                      </span>
                    </td>
                    <td className='py-3 px-4'>
                      <div className='flex items-center space-x-2'>
                        <Button variant='outline' size='sm'>
                          <Eye className='w-4 h-4' />
                        </Button>
                        <Button variant='outline' size='sm'>
                          <Edit className='w-4 h-4' />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {filteredCustomers.length === 0 && (
            <div className='text-center py-8 text-gray-500'>
              No customers found matching your search criteria.
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
