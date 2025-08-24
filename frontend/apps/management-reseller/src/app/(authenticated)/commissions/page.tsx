'use client';

import { useState, useEffect } from 'react';
import { 
  DollarSign, 
  CheckCircle, 
  Clock, 
  AlertTriangle,
  Download,
  Filter,
  Search,
  Eye,
  CreditCard,
  FileText,
  TrendingUp,
  Users,
  Calendar,
} from 'lucide-react';
import { useManagementAuth } from '@/components/auth/ManagementAuthProvider';

interface CommissionPayment {
  id: string;
  payment_number: string;
  partner_id: string;
  partner_name: string;
  partner_tier: string;
  period_start: string;
  period_end: string;
  gross_commission: number;
  deductions: Array<{
    type: string;
    description: string;
    amount: number;
  }>;
  net_commission: number;
  payment_date?: string;
  payment_method: string;
  status: string;
  created_at: string;
  sales_count: number;
  approval_notes?: string;
}

interface CommissionSummary {
  total_pending: number;
  total_approved: number;
  total_paid_this_month: number;
  partners_awaiting_payment: number;
  average_commission_amount: number;
  top_earners: Array<{
    partner_name: string;
    amount: number;
    tier: string;
  }>;
}

export default function CommissionsPage() {
  const { user, canApproveCommissions } = useManagementAuth();
  const [payments, setPayments] = useState<CommissionPayment[]>([]);
  const [summary, setSummary] = useState<CommissionSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedPayments, setSelectedPayments] = useState<string[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'date' | 'amount' | 'partner'>('date');

  useEffect(() => {
    loadCommissionData();
  }, [statusFilter]);

  const loadCommissionData = async () => {
    setIsLoading(true);
    try {
      // Mock data - would fetch from management API
      const mockSummary: CommissionSummary = {
        total_pending: 487500,
        total_approved: 156000,
        total_paid_this_month: 2340000,
        partners_awaiting_payment: 47,
        average_commission_amount: 12750,
        top_earners: [
          { partner_name: 'TechConnect Solutions', amount: 58200, tier: 'DIAMOND' },
          { partner_name: 'Network Pro Services', amount: 50760, tier: 'PLATINUM' },
          { partner_name: 'Digital Wave Communications', amount: 42779, tier: 'PLATINUM' },
          { partner_name: 'Metro Fiber Solutions', amount: 40370, tier: 'GOLD' },
          { partner_name: 'Connectivity First', amount: 37950, tier: 'GOLD' },
        ],
      };

      const mockPayments: CommissionPayment[] = [
        {
          id: 'comm_001',
          payment_number: 'PAY-2024-001847',
          partner_id: 'partner_001',
          partner_name: 'TechConnect Solutions',
          partner_tier: 'DIAMOND',
          period_start: '2024-01-01',
          period_end: '2024-01-31',
          gross_commission: 58200,
          deductions: [
            { type: 'TAX', description: 'Federal withholding', amount: 8730 },
            { type: 'FEE', description: 'Processing fee', amount: 292 },
          ],
          net_commission: 49178,
          payment_method: 'ACH',
          status: 'APPROVED',
          created_at: '2024-02-01T10:00:00Z',
          sales_count: 28,
          approval_notes: 'All sales verified, performance bonus included',
        },
        {
          id: 'comm_002',
          payment_number: 'PAY-2024-001848',
          partner_id: 'partner_002',
          partner_name: 'Network Pro Services',
          partner_tier: 'PLATINUM',
          period_start: '2024-01-01',
          period_end: '2024-01-31',
          gross_commission: 50760,
          deductions: [
            { type: 'TAX', description: 'Federal withholding', amount: 7614 },
            { type: 'CHARGEBACK', description: 'Customer refund adjustment', amount: 1250 },
          ],
          net_commission: 41896,
          payment_method: 'ACH',
          status: 'CALCULATED',
          created_at: '2024-02-01T10:15:00Z',
          sales_count: 24,
        },
        {
          id: 'comm_003',
          payment_number: 'PAY-2024-001849',
          partner_id: 'partner_003',
          partner_name: 'Digital Wave Communications',
          partner_tier: 'PLATINUM',
          period_start: '2024-01-01',
          period_end: '2024-01-31',
          gross_commission: 42779,
          deductions: [
            { type: 'TAX', description: 'Federal withholding', amount: 6417 },
          ],
          net_commission: 36362,
          payment_method: 'ACH',
          status: 'PAID',
          payment_date: '2024-02-15',
          created_at: '2024-02-01T10:30:00Z',
          sales_count: 21,
        },
        {
          id: 'comm_004',
          payment_number: 'PAY-2024-001850',
          partner_id: 'partner_004',
          partner_name: 'Metro Fiber Solutions',
          partner_tier: 'GOLD',
          period_start: '2024-01-01',
          period_end: '2024-01-31',
          gross_commission: 40370,
          deductions: [
            { type: 'TAX', description: 'Federal withholding', amount: 6056 },
            { type: 'PENALTY', description: 'Late reporting fee', amount: 500 },
          ],
          net_commission: 33814,
          payment_method: 'CHECK',
          status: 'DISPUTED',
          created_at: '2024-02-01T10:45:00Z',
          sales_count: 19,
        },
        {
          id: 'comm_005',
          payment_number: 'PAY-2024-001851',
          partner_id: 'partner_005',
          partner_name: 'Connectivity First',
          partner_tier: 'GOLD',
          period_start: '2024-01-01',
          period_end: '2024-01-31',
          gross_commission: 37950,
          deductions: [
            { type: 'TAX', description: 'Federal withholding', amount: 5693 },
          ],
          net_commission: 32257,
          payment_method: 'ACH',
          status: 'CALCULATED',
          created_at: '2024-02-01T11:00:00Z',
          sales_count: 18,
        },
      ];

      setSummary(mockSummary);
      setPayments(mockPayments);
    } catch (error) {
      console.error('Failed to load commission data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleApprovePayment = async (paymentId: string) => {
    try {
      // TODO: Call API to approve payment
      setPayments(prev => prev.map(payment => 
        payment.id === paymentId 
          ? { ...payment, status: 'APPROVED' }
          : payment
      ));
    } catch (error) {
      console.error('Failed to approve payment:', error);
    }
  };

  const handleBulkAction = async (action: 'approve' | 'process' | 'export') => {
    try {
      switch (action) {
        case 'approve':
          setPayments(prev => prev.map(payment => 
            selectedPayments.includes(payment.id) && payment.status === 'CALCULATED'
              ? { ...payment, status: 'APPROVED' }
              : payment
          ));
          break;
        case 'process':
          setPayments(prev => prev.map(payment => 
            selectedPayments.includes(payment.id) && payment.status === 'APPROVED'
              ? { ...payment, status: 'PAID', payment_date: new Date().toISOString() }
              : payment
          ));
          break;
        case 'export':
          // TODO: Export selected payments
          console.log('Exporting payments:', selectedPayments);
          break;
      }
      setSelectedPayments([]);
    } catch (error) {
      console.error(`Failed to ${action} payments:`, error);
    }
  };

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'PAID': return <CheckCircle className="h-4 w-4 text-green-600" />;
      case 'APPROVED': return <CheckCircle className="h-4 w-4 text-blue-600" />;
      case 'CALCULATED': return <Clock className="h-4 w-4 text-yellow-600" />;
      case 'DISPUTED': return <AlertTriangle className="h-4 w-4 text-red-600" />;
      default: return <Clock className="h-4 w-4 text-gray-600" />;
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'PAID': return 'status-active';
      case 'APPROVED': return 'status-badge bg-blue-100 text-blue-800';
      case 'CALCULATED': return 'status-pending';
      case 'DISPUTED': return 'status-suspended';
      default: return 'status-badge bg-gray-100 text-gray-800';
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier.toLowerCase()) {
      case 'bronze': return 'tier-bronze';
      case 'silver': return 'tier-silver';
      case 'gold': return 'tier-gold';
      case 'platinum': return 'tier-platinum';
      case 'diamond': return 'tier-diamond';
      default: return 'tier-bronze';
    }
  };

  const filteredPayments = payments.filter(payment => {
    const matchesStatus = statusFilter === 'all' || payment.status.toLowerCase().includes(statusFilter.toLowerCase());
    const matchesSearch = payment.partner_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         payment.payment_number.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesStatus && matchesSearch;
  });

  if (isLoading || !summary) {
    return (
      <div className="space-y-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-24 bg-gray-200 rounded-lg"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Commission Management</h2>
        <p className="text-gray-600">
          Process partner commission payments and manage payout workflows.
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="commission-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="text-2xl font-bold text-commission-700">
                {formatCurrency(summary.total_pending)}
              </div>
              <div className="text-sm text-gray-600 mt-1">Pending Approval</div>
            </div>
            <Clock className="h-8 w-8 text-commission-600" />
          </div>
          <div className="text-xs text-gray-500 mt-2">
            {summary.partners_awaiting_payment} partners
          </div>
        </div>

        <div className="metric-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="metric-value text-blue-700">
                {formatCurrency(summary.total_approved)}
              </div>
              <div className="metric-label">Ready to Pay</div>
            </div>
            <CheckCircle className="h-8 w-8 text-blue-600" />
          </div>
          <div className="text-xs text-gray-500 mt-2">Approved this period</div>
        </div>

        <div className="metric-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="metric-value text-green-700">
                {formatCurrency(summary.total_paid_this_month)}
              </div>
              <div className="metric-label">Paid This Month</div>
            </div>
            <CreditCard className="h-8 w-8 text-green-600" />
          </div>
          <div className="text-xs text-gray-500 mt-2">Successfully processed</div>
        </div>

        <div className="metric-card">
          <div className="flex items-center justify-between">
            <div>
              <div className="metric-value">
                {formatCurrency(summary.average_commission_amount)}
              </div>
              <div className="metric-label">Average Payment</div>
            </div>
            <TrendingUp className="h-8 w-8 text-management-600" />
          </div>
          <div className="text-xs text-gray-500 mt-2">Per partner</div>
        </div>
      </div>

      {/* Actions and Filters */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="flex items-center space-x-4">
          {canApproveCommissions() && selectedPayments.length > 0 && (
            <div className="flex space-x-2">
              <button
                onClick={() => handleBulkAction('approve')}
                className="management-button-primary text-sm px-3 py-1.5"
              >
                Approve ({selectedPayments.length})
              </button>
              <button
                onClick={() => handleBulkAction('process')}
                className="management-button-secondary text-sm px-3 py-1.5"
              >
                Process
              </button>
              <button
                onClick={() => handleBulkAction('export')}
                className="management-button-secondary text-sm px-3 py-1.5"
              >
                <Download className="h-4 w-4 mr-1" />
                Export
              </button>
            </div>
          )}
        </div>

        <div className="flex items-center space-x-3">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search partners..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="management-input pl-10 w-64"
            />
          </div>
          
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="management-input w-40"
          >
            <option value="all">All Status</option>
            <option value="calculated">Calculated</option>
            <option value="approved">Approved</option>
            <option value="paid">Paid</option>
            <option value="disputed">Disputed</option>
          </select>
        </div>
      </div>

      {/* Commission Payments Table */}
      <div className="management-card overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">Commission Payments</h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={selectedPayments.length === filteredPayments.length}
                    onChange={(e) => {
                      if (e.target.checked) {
                        setSelectedPayments(filteredPayments.map(p => p.id));
                      } else {
                        setSelectedPayments([]);
                      }
                    }}
                    className="rounded border-gray-300 text-management-600 focus:ring-management-500"
                  />
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Partner
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Period
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Gross Amount
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Net Amount
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {filteredPayments.map((payment) => (
                <tr key={payment.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <input
                      type="checkbox"
                      checked={selectedPayments.includes(payment.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setSelectedPayments(prev => [...prev, payment.id]);
                        } else {
                          setSelectedPayments(prev => prev.filter(id => id !== payment.id));
                        }
                      }}
                      className="rounded border-gray-300 text-management-600 focus:ring-management-500"
                    />
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div>
                        <div className="text-sm font-medium text-gray-900">
                          {payment.partner_name}
                        </div>
                        <div className="text-sm text-gray-500">
                          {payment.payment_number}
                        </div>
                      </div>
                      <span className={`ml-2 ${getTierColor(payment.partner_tier)}`}>
                        {payment.partner_tier}
                      </span>
                    </div>
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    <div>
                      {new Date(payment.period_start).toLocaleDateString()} -<br />
                      {new Date(payment.period_end).toLocaleDateString()}
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      {payment.sales_count} sales
                    </div>
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    {formatCurrency(payment.gross_commission)}
                    {payment.deductions.length > 0 && (
                      <div className="text-xs text-red-600 mt-1">
                        -{formatCurrency(payment.deductions.reduce((sum, d) => sum + d.amount, 0))} deductions
                      </div>
                    )}
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-commission-600">
                    {formatCurrency(payment.net_commission)}
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      {getStatusIcon(payment.status)}
                      <span className={`ml-2 ${getStatusBadge(payment.status)}`}>
                        {payment.status}
                      </span>
                    </div>
                    {payment.payment_date && (
                      <div className="text-xs text-gray-500 mt-1">
                        Paid: {new Date(payment.payment_date).toLocaleDateString()}
                      </div>
                    )}
                  </td>
                  
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium space-x-2">
                    <button className="text-management-600 hover:text-management-700">
                      <Eye className="h-4 w-4" />
                    </button>
                    
                    {canApproveCommissions() && payment.status === 'CALCULATED' && (
                      <button
                        onClick={() => handleApprovePayment(payment.id)}
                        className="text-green-600 hover:text-green-700"
                      >
                        <CheckCircle className="h-4 w-4" />
                      </button>
                    )}
                    
                    <button className="text-gray-600 hover:text-gray-700">
                      <FileText className="h-4 w-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Top Earners */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="management-card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Top Commission Earners</h3>
            <Calendar className="h-5 w-5 text-gray-400" />
          </div>
          
          <div className="space-y-3">
            {summary.top_earners.map((earner, index) => (
              <div key={earner.partner_name} className="flex items-center justify-between">
                <div className="flex items-center">
                  <div className="flex items-center justify-center w-6 h-6 bg-commission-100 rounded-full text-commission-700 font-bold text-xs mr-3">
                    {index + 1}
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">{earner.partner_name}</div>
                    <span className={getTierColor(earner.tier)}>{earner.tier}</span>
                  </div>
                </div>
                <div className="font-bold text-commission-600">
                  {formatCurrency(earner.amount)}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Quick Stats */}
        <div className="management-card p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Payment Processing Stats</h3>
          
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Average Processing Time</span>
              <span className="font-medium">3.2 days</span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Payment Success Rate</span>
              <span className="font-medium text-green-600">99.7%</span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Dispute Rate</span>
              <span className="font-medium text-yellow-600">0.8%</span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">Partners with ACH</span>
              <span className="font-medium">94.3%</span>
            </div>
            
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-600">YTD Commissions Paid</span>
              <span className="font-bold text-commission-600">
                {formatCurrency(summary.total_paid_this_month * 12)}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}