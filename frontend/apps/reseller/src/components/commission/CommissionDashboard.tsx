/**
 * Commission Dashboard Component
 * 
 * Comprehensive commission management dashboard for resellers
 * with real-time tracking, automated calculations, and payout management.
 * 
 * Features:
 * - Real-time commission tracking
 * - Multi-tier commission visualization
 * - Automated payout scheduling
 * - Performance analytics
 * - Tax compliance reporting
 * - Commission calculator
 */

import React, { useState, useMemo, useCallback } from 'react';
import {
  LineChart, Line, AreaChart, Area, BarChart, Bar, PieChart, Pie,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  Cell
} from 'recharts';
import { useCommissions, useCommissionCalculator, usePayoutHistory } from '@dotmac/headless';

interface CommissionDashboardProps {
  resellerId: string;
  className?: string;
}

const CHART_COLORS = {
  primary: '#3B82F6',
  secondary: '#10B981',
  accent: '#F59E0B',
  danger: '#EF4444',
  success: '#10B981',
  warning: '#F59E0B',
};

const formatCurrency = (amount: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
  }).format(amount);
};

const formatPercent = (value: number): string => {
  return `${value.toFixed(1)}%`;
};

export const CommissionDashboard: React.FC<CommissionDashboardProps> = ({
  resellerId,
  className = '',
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'transactions' | 'payouts' | 'calculator'>('overview');
  const [dateRange, setDateRange] = useState({
    start: new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0],
    end: new Date().toISOString().split('T')[0],
  });

  // Hooks
  const {
    summary,
    metrics,
    transactions,
    isLoading,
    isError,
    requestCommissionPayout,
    exportCommissionData,
    refreshData,
  } = useCommissions({
    resellerId,
    filters: { dateRange },
    autoRefresh: true,
  });

  const calculator = useCommissionCalculator(resellerId);
  const payoutHistory = usePayoutHistory(resellerId);

  // Calculator state
  const [calculatorForm, setCalculatorForm] = useState({
    amount: '',
    serviceType: '',
    monthlyRevenue: '',
  });
  const [calculatorResult, setCalculatorResult] = useState<any>(null);

  // Handle calculator submission
  const handleCalculateCommission = useCallback(async () => {
    if (!calculatorForm.amount || !calculatorForm.serviceType) return;

    const amount = parseFloat(calculatorForm.amount);
    const monthlyRevenue = parseFloat(calculatorForm.monthlyRevenue) || 0;

    try {
      const estimate = calculator.estimateCommission(
        amount,
        calculatorForm.serviceType,
        monthlyRevenue
      );
      
      const preview = await calculator.calculateCommissionPreview(
        amount,
        calculatorForm.serviceType,
        'sale'
      );

      setCalculatorResult({
        estimate,
        preview,
      });
    } catch (error) {
      console.error('Commission calculation failed:', error);
    }
  }, [calculatorForm, calculator]);

  // Handle payout request
  const handleRequestPayout = useCallback(async () => {
    if (!metrics?.isPayoutReady) return;

    try {
      await requestCommissionPayout();
      refreshData();
    } catch (error) {
      console.error('Payout request failed:', error);
    }
  }, [metrics, requestCommissionPayout, refreshData]);

  // Chart data
  const transactionsByMonth = useMemo(() => {
    if (!transactions.length) return [];

    const monthlyData = transactions.reduce((acc, transaction) => {
      const month = new Date(transaction.transactionDate).toISOString().slice(0, 7);
      if (!acc[month]) {
        acc[month] = { month, amount: 0, count: 0 };
      }
      acc[month].amount += transaction.commissionAmount;
      acc[month].count++;
      return acc;
    }, {} as Record<string, { month: string; amount: number; count: number }>);

    return Object.values(monthlyData).sort((a, b) => a.month.localeCompare(b.month));
  }, [transactions]);

  const servicePerformanceData = useMemo(() => {
    if (!metrics?.servicePerformance) return [];

    return metrics.servicePerformance.map((service, index) => ({
      ...service,
      color: Object.values(CHART_COLORS)[index % Object.values(CHART_COLORS).length],
    }));
  }, [metrics]);

  if (isLoading) {
    return (
      <div className={`commission-dashboard loading ${className}`}>
        <div className="loading-spinner">Loading commission data...</div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className={`commission-dashboard error ${className}`}>
        <div className="error-message">Failed to load commission data</div>
        <button onClick={refreshData} className="retry-button">Retry</button>
      </div>
    );
  }

  return (
    <div className={`commission-dashboard ${className}`}>
      {/* Header */}
      <div className="dashboard-header">
        <div className="header-content">
          <h1>Commission Dashboard</h1>
          <div className="header-actions">
            <select
              value={`${dateRange.start}|${dateRange.end}`}
              onChange={(e) => {
                const [start, end] = e.target.value.split('|');
                setDateRange({ start, end });
              }}
              className="date-range-select"
            >
              <option value={`${new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]}|${new Date().toISOString().split('T')[0]}`}>
                Last 30 days
              </option>
              <option value={`${new Date(Date.now() - 90 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]}|${new Date().toISOString().split('T')[0]}`}>
                Last 90 days
              </option>
              <option value={`${new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]}|${new Date().toISOString().split('T')[0]}`}>
                Last year
              </option>
            </select>
            
            <button 
              onClick={() => exportCommissionData('csv', dateRange)}
              className="export-button"
            >
              Export CSV
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="dashboard-tabs">
          {(['overview', 'transactions', 'payouts', 'calculator'] as const).map((tab) => (
            <button
              key={tab}
              className={`tab-button ${activeTab === tab ? 'active' : ''}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Summary Cards */}
      {metrics && (
        <div className="summary-cards">
          <div className="summary-card">
            <div className="card-header">
              <h3>Total Earned</h3>
              <span className={`trend ${metrics.growthRate >= 0 ? 'positive' : 'negative'}`}>
                {metrics.growthRate >= 0 ? '↗' : '↘'} {formatPercent(Math.abs(metrics.growthRate))}
              </span>
            </div>
            <div className="card-value">{formatCurrency(metrics.totalEarned)}</div>
            <div className="card-subtitle">
              {formatCurrency(metrics.currentMonth)} this month
            </div>
          </div>

          <div className="summary-card">
            <div className="card-header">
              <h3>Pending Payout</h3>
              {metrics.isPayoutReady && (
                <span className="payout-ready">Ready</span>
              )}
            </div>
            <div className="card-value">{formatCurrency(metrics.pendingAmount)}</div>
            <div className="card-subtitle">
              Min: {formatCurrency(metrics.minPayoutAmount)}
            </div>
          </div>

          <div className="summary-card">
            <div className="card-header">
              <h3>Average Commission</h3>
            </div>
            <div className="card-value">{formatPercent(metrics.averageCommissionRate)}</div>
            <div className="card-subtitle">
              {metrics.transactionCount} transactions
            </div>
          </div>

          <div className="summary-card">
            <div className="card-header">
              <h3>Top Service</h3>
            </div>
            <div className="card-value">
              {metrics.topService ? formatCurrency(metrics.topService.amount) : 'N/A'}
            </div>
            <div className="card-subtitle">
              {metrics.topService?.count || 0} sales
            </div>
          </div>
        </div>
      )}

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'overview' && (
          <div className="overview-tab">
            {/* Commission Trend Chart */}
            <div className="chart-section">
              <h3>Commission Trends</h3>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={transactionsByMonth}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="month" />
                  <YAxis tickFormatter={formatCurrency} />
                  <Tooltip 
                    formatter={(value: number) => [formatCurrency(value), 'Commission']}
                    labelFormatter={(label) => `Month: ${label}`}
                  />
                  <Area
                    type="monotone"
                    dataKey="amount"
                    stroke={CHART_COLORS.primary}
                    fill={CHART_COLORS.primary}
                    fillOpacity={0.6}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Service Performance */}
            <div className="chart-section">
              <h3>Service Performance</h3>
              <div className="chart-row">
                <div className="chart-half">
                  <ResponsiveContainer width="100%" height={250}>
                    <PieChart>
                      <Pie
                        data={servicePerformanceData}
                        dataKey="amount"
                        nameKey="serviceId"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={({ serviceId, amount }) => 
                          `${serviceId}: ${formatCurrency(amount)}`
                        }
                      >
                        {servicePerformanceData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Pie>
                      <Tooltip formatter={(value) => formatCurrency(value as number)} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                
                <div className="service-list">
                  {servicePerformanceData.map((service) => (
                    <div key={service.serviceId} className="service-item">
                      <div 
                        className="service-color" 
                        style={{ backgroundColor: service.color }}
                      />
                      <div className="service-info">
                        <div className="service-name">{service.serviceId}</div>
                        <div className="service-stats">
                          {formatCurrency(service.amount)} • {service.count} sales
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Payout Actions */}
            {metrics?.isPayoutReady && (
              <div className="payout-section">
                <div className="payout-card">
                  <h3>Payout Available</h3>
                  <p>
                    You have {formatCurrency(metrics.pendingAmount)} available for payout.
                  </p>
                  <button 
                    onClick={handleRequestPayout}
                    className="payout-button primary"
                  >
                    Request Payout
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'transactions' && (
          <div className="transactions-tab">
            <div className="transactions-table">
              <div className="table-header">
                <div className="table-row header">
                  <div className="table-cell">Date</div>
                  <div className="table-cell">Customer</div>
                  <div className="table-cell">Service</div>
                  <div className="table-cell">Type</div>
                  <div className="table-cell">Amount</div>
                  <div className="table-cell">Commission</div>
                  <div className="table-cell">Rate</div>
                  <div className="table-cell">Status</div>
                </div>
              </div>
              <div className="table-body">
                {transactions.map((transaction) => (
                  <div key={transaction.id} className="table-row">
                    <div className="table-cell">
                      {new Date(transaction.transactionDate).toLocaleDateString()}
                    </div>
                    <div className="table-cell">{transaction.customerId}</div>
                    <div className="table-cell">{transaction.serviceId}</div>
                    <div className="table-cell">
                      <span className={`transaction-type ${transaction.transactionType}`}>
                        {transaction.transactionType}
                      </span>
                    </div>
                    <div className="table-cell">
                      {formatCurrency(transaction.amount)}
                    </div>
                    <div className="table-cell">
                      {formatCurrency(transaction.commissionAmount)}
                    </div>
                    <div className="table-cell">
                      {formatPercent(transaction.commissionRate * 100)}
                    </div>
                    <div className="table-cell">
                      <span className={`status ${transaction.status}`}>
                        {transaction.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'payouts' && (
          <div className="payouts-tab">
            <div className="payout-summary">
              {payoutHistory.payoutStats && (
                <div className="payout-stats">
                  <div className="stat-item">
                    <label>Total Paid</label>
                    <value>{formatCurrency(payoutHistory.payoutStats.totalPaid)}</value>
                  </div>
                  <div className="stat-item">
                    <label>Average Payout</label>
                    <value>{formatCurrency(payoutHistory.payoutStats.averagePayout)}</value>
                  </div>
                  <div className="stat-item">
                    <label>Payout Count</label>
                    <value>{payoutHistory.payoutStats.payoutCount}</value>
                  </div>
                  <div className="stat-item">
                    <label>Last Payout</label>
                    <value>
                      {payoutHistory.payoutStats.lastPayout 
                        ? new Date(payoutHistory.payoutStats.lastPayout.payoutDate).toLocaleDateString()
                        : 'None'
                      }
                    </value>
                  </div>
                </div>
              )}
            </div>

            <div className="payouts-table">
              <div className="table-header">
                <div className="table-row header">
                  <div className="table-cell">Payout Date</div>
                  <div className="table-cell">Period</div>
                  <div className="table-cell">Amount</div>
                  <div className="table-cell">Transactions</div>
                  <div className="table-cell">Fees</div>
                  <div className="table-cell">Net Amount</div>
                  <div className="table-cell">Status</div>
                </div>
              </div>
              <div className="table-body">
                {payoutHistory.payouts.map((payout) => (
                  <div key={payout.id} className="table-row">
                    <div className="table-cell">
                      {new Date(payout.payoutDate).toLocaleDateString()}
                    </div>
                    <div className="table-cell">
                      {new Date(payout.periodStart).toLocaleDateString()} - {' '}
                      {new Date(payout.periodEnd).toLocaleDateString()}
                    </div>
                    <div className="table-cell">
                      {formatCurrency(payout.totalAmount)}
                    </div>
                    <div className="table-cell">{payout.transactionCount}</div>
                    <div className="table-cell">
                      {formatCurrency(payout.fees || 0)}
                    </div>
                    <div className="table-cell">
                      {formatCurrency(payout.netAmount)}
                    </div>
                    <div className="table-cell">
                      <span className={`status ${payout.status}`}>
                        {payout.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'calculator' && (
          <div className="calculator-tab">
            <div className="calculator-form">
              <h3>Commission Calculator</h3>
              
              <div className="form-group">
                <label>Sale Amount</label>
                <input
                  type="number"
                  value={calculatorForm.amount}
                  onChange={(e) => setCalculatorForm(prev => ({ 
                    ...prev, 
                    amount: e.target.value 
                  }))}
                  placeholder="Enter sale amount"
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label>Service Type</label>
                <select
                  value={calculatorForm.serviceType}
                  onChange={(e) => setCalculatorForm(prev => ({ 
                    ...prev, 
                    serviceType: e.target.value 
                  }))}
                  className="form-select"
                >
                  <option value="">Select service type</option>
                  <option value="internet">Internet</option>
                  <option value="phone">Phone</option>
                  <option value="tv">TV</option>
                  <option value="bundle">Bundle</option>
                </select>
              </div>

              <div className="form-group">
                <label>Monthly Revenue (Optional)</label>
                <input
                  type="number"
                  value={calculatorForm.monthlyRevenue}
                  onChange={(e) => setCalculatorForm(prev => ({ 
                    ...prev, 
                    monthlyRevenue: e.target.value 
                  }))}
                  placeholder="For tier calculation"
                  className="form-input"
                />
              </div>

              <button 
                onClick={handleCalculateCommission}
                className="calculate-button"
                disabled={!calculatorForm.amount || !calculatorForm.serviceType}
              >
                Calculate Commission
              </button>

              {calculatorResult && (
                <div className="calculator-result">
                  <h4>Commission Estimate</h4>
                  <div className="result-row">
                    <span>Sale Amount:</span>
                    <span>{formatCurrency(parseFloat(calculatorForm.amount))}</span>
                  </div>
                  <div className="result-row">
                    <span>Commission Rate:</span>
                    <span>{formatPercent(calculatorResult.estimate.rate * 100)}</span>
                  </div>
                  <div className="result-row">
                    <span>Commission Amount:</span>
                    <span className="commission-amount">
                      {formatCurrency(calculatorResult.estimate.amount)}
                    </span>
                  </div>
                  {calculatorResult.estimate.tier && (
                    <div className="result-row">
                      <span>Commission Tier:</span>
                      <span>{calculatorResult.estimate.tier.name}</span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default CommissionDashboard;