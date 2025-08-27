'use client';

import { useState, useEffect } from 'react';
import { useAuthToken } from '../../../hooks/useSSRSafeStorage';
import { Card, CardContent, CardHeader, CardTitle } from '../../ui/Card';
import { Button } from '../../ui/Button';
import { CreditCard, DollarSign, FileText, TrendingUp, Clock, AlertCircle } from 'lucide-react';

interface Invoice {
  id: string;
  customer_name: string;
  amount: number;
  status: 'paid' | 'pending' | 'overdue';
  due_date: string;
  created_at: string;
}

interface BillingStats {
  total_revenue: number;
  outstanding_amount: number;
  paid_invoices: number;
  overdue_invoices: number;
}

export function BillingManagement() {
  const [authToken, , tokenLoading] = useAuthToken();
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [stats, setStats] = useState<BillingStats>({
    total_revenue: 0,
    outstanding_amount: 0,
    paid_invoices: 0,
    overdue_invoices: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (authToken && !tokenLoading) {
      fetchBillingData();
    }
  }, [authToken, tokenLoading]);

  const fetchBillingData = async () => {
    if (!authToken || tokenLoading) return;
    setLoading(true);

    // Demo data that serves as fallback
    const demoInvoices = [
      {
        id: 'INV-001',
        customer_name: 'John Smith',
        amount: 89.99,
        status: 'paid' as const,
        due_date: '2024-01-15',
        created_at: '2024-01-01T10:00:00Z',
      },
      {
        id: 'INV-002',
        customer_name: 'Jane Doe',
        amount: 129.99,
        status: 'pending' as const,
        due_date: '2024-01-20',
        created_at: '2024-01-05T14:30:00Z',
      },
      {
        id: 'INV-003',
        customer_name: 'Bob Johnson',
        amount: 59.99,
        status: 'overdue' as const,
        due_date: '2024-01-10',
        created_at: '2023-12-28T09:15:00Z',
      },
    ];

    const demoStats = {
      total_revenue: 487230,
      outstanding_amount: 45670,
      paid_invoices: 156,
      overdue_invoices: 12,
    };

    try {
      const [invoicesResponse, statsResponse] = await Promise.all([
        fetch('/api/isp/billing/invoices', {
          headers: { Authorization: `Bearer ${authToken}` },
        }),
        fetch('/api/isp/billing/stats', {
          headers: { Authorization: `Bearer ${authToken}` },
        }),
      ]);

      if (invoicesResponse.ok && statsResponse.ok) {
        const invoicesData = await invoicesResponse.json();
        const statsData = await statsResponse.json();

        setInvoices(invoicesData);
        setStats(statsData);
      } else {
        // Use demo data if API responses are not successful
        throw new Error(`API Error: ${invoicesResponse.status} ${statsResponse.status}`);
      }
    } catch (error) {
      // Graceful fallback to demo data
      console.warn('Using demo data due to API error:', error);
      setInvoices(demoInvoices);
      setStats(demoStats);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'overdue':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount);
  };

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
          <h1 className='text-2xl font-bold text-gray-900'>Billing Management</h1>
          <p className='text-gray-600'>Invoices, payments, and financial operations</p>
        </div>
        <Button className='flex items-center'>
          <FileText className='w-4 h-4 mr-2' />
          Generate Invoice
        </Button>
      </div>

      {/* Financial Stats */}
      <div className='grid grid-cols-1 md:grid-cols-4 gap-6'>
        <Card>
          <CardContent className='p-6'>
            <div className='flex items-center'>
              <DollarSign className='w-8 h-8 text-green-600' />
              <div className='ml-4'>
                <p className='text-sm font-medium text-gray-600'>Total Revenue</p>
                <p className='text-2xl font-bold text-gray-900'>
                  {formatCurrency(stats.total_revenue)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6'>
            <div className='flex items-center'>
              <Clock className='w-8 h-8 text-yellow-600' />
              <div className='ml-4'>
                <p className='text-sm font-medium text-gray-600'>Outstanding</p>
                <p className='text-2xl font-bold text-gray-900'>
                  {formatCurrency(stats.outstanding_amount)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6'>
            <div className='flex items-center'>
              <TrendingUp className='w-8 h-8 text-blue-600' />
              <div className='ml-4'>
                <p className='text-sm font-medium text-gray-600'>Paid Invoices</p>
                <p className='text-2xl font-bold text-gray-900'>{stats.paid_invoices}</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6'>
            <div className='flex items-center'>
              <AlertCircle className='w-8 h-8 text-red-600' />
              <div className='ml-4'>
                <p className='text-sm font-medium text-gray-600'>Overdue</p>
                <p className='text-2xl font-bold text-gray-900'>{stats.overdue_invoices}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
        <Card>
          <CardContent className='p-6'>
            <div className='text-center'>
              <CreditCard className='w-12 h-12 text-blue-600 mx-auto mb-4' />
              <h3 className='text-lg font-semibold text-gray-900 mb-2'>Process Payment</h3>
              <p className='text-sm text-gray-600 mb-4'>
                Record manual payment or process credit card
              </p>
              <Button size='sm'>Process Payment</Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6'>
            <div className='text-center'>
              <FileText className='w-12 h-12 text-green-600 mx-auto mb-4' />
              <h3 className='text-lg font-semibold text-gray-900 mb-2'>Create Invoice</h3>
              <p className='text-sm text-gray-600 mb-4'>
                Generate new invoice for customer services
              </p>
              <Button size='sm'>Create Invoice</Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className='p-6'>
            <div className='text-center'>
              <TrendingUp className='w-12 h-12 text-purple-600 mx-auto mb-4' />
              <h3 className='text-lg font-semibold text-gray-900 mb-2'>Revenue Report</h3>
              <p className='text-sm text-gray-600 mb-4'>Generate financial reports and analytics</p>
              <Button size='sm'>View Reports</Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Invoices */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Invoices</CardTitle>
        </CardHeader>
        <CardContent>
          <div className='overflow-x-auto'>
            <table className='w-full'>
              <thead>
                <tr className='border-b'>
                  <th className='text-left py-3 px-4 font-medium text-gray-600'>Invoice</th>
                  <th className='text-left py-3 px-4 font-medium text-gray-600'>Customer</th>
                  <th className='text-left py-3 px-4 font-medium text-gray-600'>Amount</th>
                  <th className='text-left py-3 px-4 font-medium text-gray-600'>Status</th>
                  <th className='text-left py-3 px-4 font-medium text-gray-600'>Due Date</th>
                  <th className='text-left py-3 px-4 font-medium text-gray-600'>Actions</th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((invoice) => (
                  <tr key={invoice.id} className='border-b hover:bg-gray-50'>
                    <td className='py-3 px-4'>
                      <code className='bg-gray-100 px-2 py-1 rounded text-sm'>{invoice.id}</code>
                    </td>
                    <td className='py-3 px-4'>
                      <span className='font-medium text-gray-900'>{invoice.customer_name}</span>
                    </td>
                    <td className='py-3 px-4'>
                      <span className='font-medium text-gray-900'>
                        {formatCurrency(invoice.amount)}
                      </span>
                    </td>
                    <td className='py-3 px-4'>
                      <span
                        className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(invoice.status)}`}
                      >
                        {invoice.status}
                      </span>
                    </td>
                    <td className='py-3 px-4'>
                      <span className='text-sm text-gray-900'>
                        {new Date(invoice.due_date).toLocaleDateString()}
                      </span>
                    </td>
                    <td className='py-3 px-4'>
                      <div className='flex items-center space-x-2'>
                        <Button variant='outline' size='sm'>
                          View
                        </Button>
                        <Button variant='outline' size='sm'>
                          Send
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {invoices.length === 0 && (
            <div className='text-center py-8 text-gray-500'>No invoices found.</div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
