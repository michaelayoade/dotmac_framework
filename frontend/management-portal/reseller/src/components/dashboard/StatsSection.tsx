/**
 * Stats Section Component
 * Displays partner and commission statistics
 */

import React from 'react';

interface StatsData {
  total: number;
  active: number;
  pending: number;
  suspended?: number;
  approved?: number;
  paid?: number;
  totalAmount?: number;
  calculated?: number;
  disputed?: number;
  averageAmount?: number;
  byPaymentMethod?: Record<string, number>;
}

interface StatsSectionProps {
  partnerStats?: StatsData;
  commissionStats?: any; // Flexible type for commission stats to avoid type conflicts
  isLoading?: boolean;
}

export function StatsSection({ partnerStats, commissionStats, isLoading }: StatsSectionProps) {
  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(amount);
  };

  if (isLoading) {
    return <StatsSectionSkeleton />;
  }

  return (
    <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
      {partnerStats && (
        <StatsCard title='Partner Summary'>
          <StatItem label='Total Partners' value={partnerStats.total} />
          <StatItem label='Active' value={partnerStats.active} variant='success' />
          <StatItem label='Pending' value={partnerStats.pending} variant='warning' />
          {partnerStats.suspended !== undefined && (
            <StatItem label='Suspended' value={partnerStats.suspended} variant='error' />
          )}
        </StatsCard>
      )}

      {commissionStats && (
        <StatsCard title='Commission Summary'>
          <StatItem label='Total Commissions' value={commissionStats.total} />
          {commissionStats.approved !== undefined && (
            <StatItem label='Approved' value={commissionStats.approved} variant='success' />
          )}
          {commissionStats.paid !== undefined && (
            <StatItem label='Paid' value={commissionStats.paid} variant='info' />
          )}
          {commissionStats.totalAmount !== undefined && (
            <StatItem
              label='Total Amount'
              value={formatCurrency(commissionStats.totalAmount)}
              isFormatted
            />
          )}
        </StatsCard>
      )}
    </div>
  );
}

function StatsCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className='bg-white p-6 rounded-lg shadow-sm border border-gray-200'>
      <h3 className='text-lg font-semibold text-gray-900 mb-4'>{title}</h3>
      <div className='space-y-3'>{children}</div>
    </div>
  );
}

function StatItem({
  label,
  value,
  variant = 'default',
  isFormatted = false,
}: {
  label: string;
  value: number | string;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info';
  isFormatted?: boolean;
}) {
  const getVariantStyles = (variant: string) => {
    switch (variant) {
      case 'success':
        return 'text-green-600';
      case 'warning':
        return 'text-yellow-600';
      case 'error':
        return 'text-red-600';
      case 'info':
        return 'text-blue-600';
      default:
        return 'text-gray-900';
    }
  };

  const displayValue = isFormatted
    ? value
    : typeof value === 'number'
      ? value.toLocaleString()
      : value;

  return (
    <div className='flex justify-between items-center'>
      <span className='text-gray-600'>{label}:</span>
      <span className={`font-medium ${getVariantStyles(variant)}`}>{displayValue}</span>
    </div>
  );
}

function StatsSectionSkeleton() {
  return (
    <div className='grid grid-cols-1 md:grid-cols-2 gap-6'>
      {[1, 2].map((i) => (
        <div key={i} className='bg-white p-6 rounded-lg shadow-sm border border-gray-200'>
          <div className='animate-pulse'>
            <div className='h-5 bg-gray-300 rounded w-32 mb-4'></div>
            <div className='space-y-3'>
              {[1, 2, 3, 4].map((j) => (
                <div key={j} className='flex justify-between'>
                  <div className='h-4 bg-gray-300 rounded w-20'></div>
                  <div className='h-4 bg-gray-300 rounded w-12'></div>
                </div>
              ))}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
