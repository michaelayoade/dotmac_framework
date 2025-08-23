'use client';

import { useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import {
  CreditCardIcon,
  DollarSignIcon,
  TrendingUpIcon,
  TrendingDownIcon,
  AlertTriangleIcon,
  CheckCircleIcon,
  ClockIcon,
  XCircleIcon,
  FileTextIcon,
  DownloadIcon,
  SearchIcon,
  FilterIcon,
  CalendarIcon,
  MailIcon,
  PrinterIcon,
  RefreshCwIcon,
  ArrowUpIcon,
  ArrowDownIcon,
  EyeIcon,
  EditIcon,
  SendIcon,
  UserIcon,
  BanknotesIcon,
} from 'lucide-react';
import {
  RevenueChart,
  NetworkUsageChart,
  ServiceStatusChart,
  BandwidthChart,
} from '@dotmac/primitives/charts/InteractiveChart';
import {
  StatusBadge,
  UptimeIndicator,
  NetworkPerformanceIndicator,
  ServiceTierIndicator,
  AlertSeverityIndicator,
} from '@dotmac/primitives/indicators/StatusIndicators';
import {
  AnimatedCounter,
  FadeInWhenVisible,
  StaggeredFadeIn,
  StaggerChild,
  AnimatedCard,
  SlideIn,
  AnimatedProgressBar,
  PulseIndicator,
  BounceIn,
} from '@dotmac/primitives/animations/Animations';

interface Invoice {
  id: string;
  customerId: string;
  customerName: string;
  customerEmail: string;
  amount: number;
  tax: number;
  total: number;
  currency: string;
  status: 'paid' | 'pending' | 'overdue' | 'cancelled';
  dueDate: string;
  paidDate: string | null;
  paymentMethod: string;
  services: { name: string; amount: number }[];
  billingPeriod: { start: string; end: string };
  createdAt: string;
  updatedAt: string;
  tags: string[];
}

interface Payment {
  id: string;
  invoiceId: string | null;
  customerId: string;
  customerName: string;
  amount: number;
  currency: string;
  method: string;
  status: 'completed' | 'pending' | 'failed' | 'refunded';
  transactionId: string;
  gateway: string;
  processedAt: string | null;
  fees: { processing: number; gateway: number };
  metadata: Record<string, any>;
}

interface Metrics {
  totalRevenue: number;
  monthlyRecurring: number;
  outstandingAmount: number;
  collectionsRate: number;
  averageInvoiceValue: number;
  paymentFailureRate: number;
  trends: { revenue: number; collections: number; failures: number };
  chartData: {
    revenue: { month: string; amount: number }[];
    collections: { month: string; rate: number }[];
    paymentMethods: { method: string; percentage: number; amount: number }[];
  };
}

interface Report {
  id: string;
  name: string;
  type: string;
  description: string;
  lastGenerated: string;
  frequency: string;
  status: 'ready' | 'generating' | 'failed';
  format: string;
  size: string | null;
}

interface BillingManagementProps {
  invoices: Invoice[];
  payments: Payment[];
  metrics: Metrics;
  reports: Report[];
  totalCount: number;
  currentPage: number;
  pageSize: number;
  activeTab: string;
}

type TabType = 'invoices' | 'payments' | 'reports' | 'analytics';

export function BillingManagement({
  invoices,
  payments,
  metrics,
  reports,
  totalCount,
  currentPage,
  pageSize,
  activeTab,
}: BillingManagementProps) {
  const router = useRouter();
  const [selectedTab, setSelectedTab] = useState<TabType>(activeTab as TabType);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedItems, setSelectedItems] = useState<Set<string>>(new Set());
  const [showFilters, setShowFilters] = useState(false);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'paid':
      case 'completed':
        return 'bg-green-100 text-green-800';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800';
      case 'overdue':
      case 'failed':
        return 'bg-red-100 text-red-800';
      case 'cancelled':
      case 'refunded':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'paid':
      case 'completed':
        return CheckCircleIcon;
      case 'pending':
        return ClockIcon;
      case 'overdue':
      case 'failed':
        return XCircleIcon;
      default:
        return AlertTriangleIcon;
    }
  };

  const MetricCard = ({
    title,
    value,
    trend,
    icon: Icon,
    format = 'currency',
  }: {
    title: string;
    value: number;
    trend?: number;
    icon: any;
    format?: 'currency' | 'percentage' | 'number';
  }) => {
    const formatValue = (val: number) => {
      switch (format) {
        case 'currency':
          return `$${val.toLocaleString()}`;
        case 'percentage':
          return `${val.toFixed(1)}%`;
        default:
          return val.toLocaleString();
      }
    };

    return (
      <FadeInWhenVisible>
        <AnimatedCard className='bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center space-x-3'>
              <PulseIndicator active={trend !== undefined && Math.abs(trend) > 5}>
                <div className='p-2 bg-gradient-to-r from-blue-100 to-indigo-100 rounded-lg'>
                  <Icon className='w-6 h-6 text-blue-600' />
                </div>
              </PulseIndicator>
              <div>
                <p className='text-sm font-medium text-gray-600'>{title}</p>
                <AnimatedCounter
                  value={value}
                  prefix={format === 'currency' ? '$' : ''}
                  suffix={format === 'percentage' ? '%' : ''}
                  className='text-2xl font-bold text-gray-900'
                />
              </div>
            </div>
            {trend !== undefined && (
              <BounceIn>
                <StatusBadge
                  variant={trend > 0 ? 'online' : trend < 0 ? 'overdue' : 'pending'}
                  size='sm'
                  showDot={true}
                  pulse={Math.abs(trend) > 10}
                >
                  {trend > 0 ? (
                    <ArrowUpIcon className='w-3 h-3 mr-1' />
                  ) : trend < 0 ? (
                    <ArrowDownIcon className='w-3 h-3 mr-1' />
                  ) : null}
                  {Math.abs(trend).toFixed(1)}%
                </StatusBadge>
              </BounceIn>
            )}
          </div>
        </AnimatedCard>
      </FadeInWhenVisible>
    );
  };

  const InvoiceRow = ({ invoice }: { invoice: Invoice }) => {
    const StatusIcon = getStatusIcon(invoice.status);

    return (
      <tr className='hover:bg-gray-50'>
        <td className='px-6 py-4'>
          <input
            type='checkbox'
            checked={selectedItems.has(invoice.id)}
            onChange={() => {
              const newSelected = new Set(selectedItems);
              if (newSelected.has(invoice.id)) {
                newSelected.delete(invoice.id);
              } else {
                newSelected.add(invoice.id);
              }
              setSelectedItems(newSelected);
            }}
            className='h-4 w-4 text-blue-600 rounded border-gray-300'
          />
        </td>
        <td className='px-6 py-4'>
          <div className='flex items-center space-x-3'>
            <div className='flex-shrink-0'>
              <FileTextIcon className='w-5 h-5 text-gray-400' />
            </div>
            <div>
              <div className='text-sm font-medium text-gray-900'>{invoice.id}</div>
              <div className='text-sm text-gray-500'>
                {new Date(invoice.createdAt).toLocaleDateString()}
              </div>
            </div>
          </div>
        </td>
        <td className='px-6 py-4'>
          <div className='flex items-center space-x-3'>
            <div className='flex-shrink-0 w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center'>
              <UserIcon className='w-4 h-4 text-gray-600' />
            </div>
            <div>
              <div className='text-sm font-medium text-gray-900'>{invoice.customerName}</div>
              <div className='text-sm text-gray-500'>{invoice.customerEmail}</div>
            </div>
          </div>
        </td>
        <td className='px-6 py-4'>
          <div className='text-sm text-gray-900'>${invoice.total.toFixed(2)}</div>
          <div className='text-xs text-gray-500'>
            Amount: ${invoice.amount.toFixed(2)} + Tax: ${invoice.tax.toFixed(2)}
          </div>
        </td>
        <td className='px-6 py-4'>
          <StatusBadge
            variant={
              invoice.status === 'paid'
                ? 'paid'
                : invoice.status === 'pending'
                  ? 'pending'
                  : invoice.status === 'overdue'
                    ? 'overdue'
                    : 'suspended'
            }
            size='sm'
            showDot={true}
            pulse={invoice.status === 'overdue'}
          >
            {invoice.status}
          </StatusBadge>
        </td>
        <td className='px-6 py-4'>
          <div className='text-sm text-gray-900'>
            {new Date(invoice.dueDate).toLocaleDateString()}
          </div>
          {invoice.status === 'overdue' && (
            <div className='text-xs text-red-600'>
              {Math.floor(
                (Date.now() - new Date(invoice.dueDate).getTime()) / (1000 * 60 * 60 * 24)
              )}{' '}
              days overdue
            </div>
          )}
        </td>
        <td className='px-6 py-4'>
          <div className='flex items-center space-x-2'>
            <button
              onClick={() => router.push(`/billing/invoices/${invoice.id}`)}
              className='p-2 text-gray-400 hover:text-blue-600 hover:bg-blue-50 rounded'
              title='View Invoice'
            >
              <EyeIcon className='w-4 h-4' />
            </button>
            <button
              className='p-2 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded'
              title='Send Reminder'
            >
              <MailIcon className='w-4 h-4' />
            </button>
            <button
              className='p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-50 rounded'
              title='Download PDF'
            >
              <DownloadIcon className='w-4 h-4' />
            </button>
          </div>
        </td>
      </tr>
    );
  };

  const PaymentRow = ({ payment }: { payment: Payment }) => {
    const StatusIcon = getStatusIcon(payment.status);

    return (
      <tr className='hover:bg-gray-50'>
        <td className='px-6 py-4'>
          <div className='flex items-center space-x-3'>
            <div className='flex-shrink-0'>
              <CreditCardIcon className='w-5 h-5 text-gray-400' />
            </div>
            <div>
              <div className='text-sm font-medium text-gray-900'>{payment.id}</div>
              <div className='text-sm text-gray-500'>{payment.transactionId}</div>
            </div>
          </div>
        </td>
        <td className='px-6 py-4'>
          <div className='text-sm font-medium text-gray-900'>{payment.customerName}</div>
          <div className='text-sm text-gray-500'>
            {payment.invoiceId ? `Invoice: ${payment.invoiceId}` : 'Standalone Payment'}
          </div>
        </td>
        <td className='px-6 py-4'>
          <div className='text-sm text-gray-900'>${payment.amount.toFixed(2)}</div>
          <div className='text-xs text-gray-500'>
            Fees: ${(payment.fees.processing + payment.fees.gateway).toFixed(2)}
          </div>
        </td>
        <td className='px-6 py-4'>
          <div className='text-sm text-gray-900 capitalize'>{payment.method.replace('_', ' ')}</div>
          <div className='text-xs text-gray-500'>{payment.gateway}</div>
        </td>
        <td className='px-6 py-4'>
          <StatusBadge
            variant={
              payment.status === 'completed'
                ? 'paid'
                : payment.status === 'pending'
                  ? 'processing'
                  : payment.status === 'failed'
                    ? 'overdue'
                    : 'suspended'
            }
            size='sm'
            showDot={true}
            pulse={payment.status === 'pending'}
          >
            {payment.status}
          </StatusBadge>
        </td>
        <td className='px-6 py-4'>
          <div className='text-sm text-gray-900'>
            {payment.processedAt ? new Date(payment.processedAt).toLocaleDateString() : 'Pending'}
          </div>
        </td>
      </tr>
    );
  };

  const ReportRow = ({ report }: { report: Report }) => {
    const getStatusIcon = () => {
      switch (report.status) {
        case 'ready':
          return CheckCircleIcon;
        case 'generating':
          return RefreshCwIcon;
        case 'failed':
          return XCircleIcon;
        default:
          return ClockIcon;
      }
    };

    const StatusIcon = getStatusIcon();

    return (
      <div className='bg-white border border-gray-200 rounded-lg p-6 hover:shadow-md transition-shadow'>
        <div className='flex items-center justify-between'>
          <div className='flex items-center space-x-4'>
            <div className='flex-shrink-0'>
              <div className='w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center'>
                <FileTextIcon className='w-6 h-6 text-blue-600' />
              </div>
            </div>
            <div>
              <h3 className='text-lg font-semibold text-gray-900'>{report.name}</h3>
              <p className='text-sm text-gray-500'>{report.description}</p>
              <div className='mt-2 flex items-center space-x-4 text-xs text-gray-500'>
                <span>Type: {report.type}</span>
                <span>•</span>
                <span>Frequency: {report.frequency}</span>
                <span>•</span>
                <span>Format: {report.format}</span>
                {report.size && (
                  <>
                    <span>•</span>
                    <span>Size: {report.size}</span>
                  </>
                )}
              </div>
            </div>
          </div>
          <div className='flex items-center space-x-3'>
            <span
              className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(report.status)}`}
            >
              <StatusIcon
                className={`w-3 h-3 mr-1 ${report.status === 'generating' ? 'animate-spin' : ''}`}
              />
              {report.status}
            </span>
            {report.status === 'ready' && (
              <button className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium'>
                Download
              </button>
            )}
          </div>
        </div>

        <div className='mt-4 text-sm text-gray-500'>
          Last generated: {new Date(report.lastGenerated).toLocaleString()}
        </div>
      </div>
    );
  };

  return (
    <div className='space-y-6'>
      {/* Key Metrics */}
      <StaggeredFadeIn>
        <div className='grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6'>
          <StaggerChild>
            <MetricCard
              title='Total Revenue'
              value={metrics.totalRevenue}
              trend={metrics.trends.revenue}
              icon={DollarSignIcon}
              format='currency'
            />
          </StaggerChild>
          <StaggerChild>
            <MetricCard
              title='Monthly Recurring'
              value={metrics.monthlyRecurring}
              trend={metrics.trends.revenue}
              icon={TrendingUpIcon}
              format='currency'
            />
          </StaggerChild>
          <StaggerChild>
            <MetricCard
              title='Outstanding Amount'
              value={metrics.outstandingAmount}
              icon={AlertTriangleIcon}
              format='currency'
            />
          </StaggerChild>
          <StaggerChild>
            <MetricCard
              title='Collections Rate'
              value={metrics.collectionsRate}
              trend={metrics.trends.collections}
              icon={CheckCircleIcon}
              format='percentage'
            />
          </StaggerChild>
        </div>
      </StaggeredFadeIn>

      {/* Navigation Tabs */}
      <div className='border-b border-gray-200'>
        <nav className='flex space-x-8'>
          {[
            { id: 'invoices', label: 'Invoices', count: invoices.length },
            { id: 'payments', label: 'Payments', count: payments.length },
            { id: 'reports', label: 'Reports', count: reports.length },
            { id: 'analytics', label: 'Analytics', count: null },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setSelectedTab(tab.id as TabType)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                selectedTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
            >
              {tab.label}
              {tab.count !== null && (
                <span className='ml-2 py-0.5 px-2 rounded-full bg-gray-100 text-xs'>
                  {tab.count}
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className='bg-white rounded-lg shadow-sm border border-gray-200'>
        {selectedTab === 'invoices' && (
          <div>
            {/* Search and Actions Bar */}
            <div className='p-6 border-b border-gray-200'>
              <div className='flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between'>
                <div className='flex-1 max-w-lg'>
                  <div className='relative'>
                    <SearchIcon className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-5 w-5' />
                    <input
                      type='text'
                      placeholder='Search invoices by ID, customer, or email...'
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className='w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                    />
                  </div>
                </div>
                <div className='flex items-center gap-2'>
                  <button
                    onClick={() => setShowFilters(!showFilters)}
                    className={`px-4 py-2 rounded-lg border font-medium transition-colors ${
                      showFilters
                        ? 'bg-blue-50 border-blue-200 text-blue-700'
                        : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
                    }`}
                  >
                    <FilterIcon className='h-4 w-4 mr-2 inline' />
                    Filters
                  </button>
                  {selectedItems.size > 0 && (
                    <div className='flex items-center gap-2'>
                      <span className='text-sm text-gray-600'>{selectedItems.size} selected</span>
                      <button className='px-3 py-2 bg-blue-100 text-blue-800 rounded-lg text-sm font-medium hover:bg-blue-200'>
                        Send Reminders
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Invoices Table */}
            <div className='overflow-x-auto'>
              <table className='min-w-full divide-y divide-gray-200'>
                <thead className='bg-gray-50'>
                  <tr>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      <input
                        type='checkbox'
                        className='h-4 w-4 text-blue-600 rounded border-gray-300'
                      />
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Invoice
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Customer
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Amount
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Status
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Due Date
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className='bg-white divide-y divide-gray-200'>
                  {invoices.map((invoice) => (
                    <InvoiceRow key={invoice.id} invoice={invoice} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {selectedTab === 'payments' && (
          <div>
            <div className='p-6 border-b border-gray-200'>
              <h3 className='text-lg font-semibold text-gray-900'>Payment Transactions</h3>
              <p className='text-sm text-gray-500'>Track and manage all payment transactions</p>
            </div>

            <div className='overflow-x-auto'>
              <table className='min-w-full divide-y divide-gray-200'>
                <thead className='bg-gray-50'>
                  <tr>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Payment
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Customer
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Amount
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Method
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Status
                    </th>
                    <th className='px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider'>
                      Date
                    </th>
                  </tr>
                </thead>
                <tbody className='bg-white divide-y divide-gray-200'>
                  {payments.map((payment) => (
                    <PaymentRow key={payment.id} payment={payment} />
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {selectedTab === 'reports' && (
          <div>
            <div className='p-6 border-b border-gray-200'>
              <div className='flex items-center justify-between'>
                <div>
                  <h3 className='text-lg font-semibold text-gray-900'>Financial Reports</h3>
                  <p className='text-sm text-gray-500'>
                    Generate and download comprehensive financial reports
                  </p>
                </div>
                <button className='px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium'>
                  Generate Report
                </button>
              </div>
            </div>

            <div className='p-6 space-y-4'>
              {reports.map((report) => (
                <ReportRow key={report.id} report={report} />
              ))}
            </div>
          </div>
        )}

        {selectedTab === 'analytics' && (
          <div className='p-6 space-y-8'>
            {/* Revenue Trend Chart */}
            <SlideIn direction='up' className='space-y-4'>
              <h3 className='text-lg font-semibold text-gray-900'>Revenue Trends</h3>
              <div className='bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-4'>
                <RevenueChart
                  data={metrics.chartData.revenue.map((item) => ({
                    month: item.month,
                    revenue: item.amount,
                    target: item.amount * 1.1,
                    previousYear: item.amount * 0.85,
                  }))}
                  height={350}
                />
              </div>
            </SlideIn>

            <div className='grid grid-cols-1 lg:grid-cols-2 gap-8'>
              {/* Collections Performance */}
              <SlideIn direction='left' delay={0.2}>
                <div className='bg-gradient-to-r from-green-50 to-emerald-50 rounded-lg p-6'>
                  <h3 className='text-lg font-semibold text-gray-900 mb-4'>
                    Collections Performance
                  </h3>
                  <div className='space-y-4'>
                    <div className='flex items-center justify-between'>
                      <span className='text-sm font-medium text-gray-600'>Current Rate</span>
                      <AnimatedCounter
                        value={metrics.collectionsRate}
                        suffix='%'
                        className='text-lg font-bold text-green-600'
                      />
                    </div>
                    <AnimatedProgressBar
                      progress={metrics.collectionsRate}
                      color='bg-green-500'
                      backgroundColor='bg-green-100'
                      showLabel={false}
                      className='mt-2'
                    />
                    <div className='pt-4'>
                      <UptimeIndicator uptime={metrics.collectionsRate} />
                    </div>
                  </div>
                </div>
              </SlideIn>

              {/* Payment Methods Distribution */}
              <SlideIn direction='right' delay={0.4}>
                <div className='bg-gradient-to-r from-purple-50 to-indigo-50 rounded-lg p-6'>
                  <h3 className='text-lg font-semibold text-gray-900 mb-4'>Payment Methods</h3>
                  <ServiceStatusChart
                    data={metrics.chartData.paymentMethods.map((method, index) => ({
                      name: method.method,
                      value: method.percentage,
                      status:
                        index === 0
                          ? 'online'
                          : index === 1
                            ? 'online'
                            : index === 2
                              ? 'maintenance'
                              : 'offline',
                    }))}
                    height={250}
                  />
                  <div className='mt-4 space-y-3'>
                    {metrics.chartData.paymentMethods.map((method, index) => (
                      <FadeInWhenVisible key={method.method} delay={index * 0.1}>
                        <div className='flex items-center justify-between'>
                          <div className='flex items-center space-x-3'>
                            <StatusBadge
                              variant={
                                index === 0
                                  ? 'online'
                                  : index === 1
                                    ? 'active'
                                    : index === 2
                                      ? 'maintenance'
                                      : 'offline'
                              }
                              size='sm'
                            >
                              {method.method}
                            </StatusBadge>
                          </div>
                          <div className='text-right'>
                            <div className='text-sm font-semibold text-gray-900'>
                              <AnimatedCounter value={method.percentage} suffix='%' />
                            </div>
                            <div className='text-xs text-gray-500'>
                              $<AnimatedCounter value={method.amount} />
                            </div>
                          </div>
                        </div>
                      </FadeInWhenVisible>
                    ))}
                  </div>
                </div>
              </SlideIn>
            </div>

            {/* Additional Analytics */}
            <SlideIn direction='up' delay={0.6}>
              <div className='grid grid-cols-1 md:grid-cols-3 gap-6'>
                <div className='bg-white border-2 border-dashed border-gray-200 rounded-lg p-6 text-center'>
                  <AlertSeverityIndicator
                    severity={
                      metrics.paymentFailureRate > 5
                        ? 'error'
                        : metrics.paymentFailureRate > 2
                          ? 'warning'
                          : 'info'
                    }
                    message={`Payment failure rate: ${metrics.paymentFailureRate}%`}
                  />
                </div>
                <div className='bg-white border-2 border-dashed border-gray-200 rounded-lg p-6'>
                  <h4 className='text-sm font-medium text-gray-600 mb-3'>Average Invoice Value</h4>
                  <div className='text-center'>
                    <AnimatedCounter
                      value={metrics.averageInvoiceValue}
                      prefix='$'
                      className='text-2xl font-bold text-blue-600'
                    />
                  </div>
                </div>
                <div className='bg-white border-2 border-dashed border-gray-200 rounded-lg p-6'>
                  <NetworkPerformanceIndicator latency={15} packetLoss={0.1} bandwidth={85} />
                </div>
              </div>
            </SlideIn>
          </div>
        )}
      </div>
    </div>
  );
}
