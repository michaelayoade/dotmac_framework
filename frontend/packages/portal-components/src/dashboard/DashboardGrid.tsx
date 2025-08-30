'use client';

import { ReactNode } from 'react';
import { LoadingSpinner } from '@dotmac/primitives';
import clsx from 'clsx';

export interface StatItem {
  name: string;
  value: string | number | ReactNode;
  change?: string;
  changeType?: 'positive' | 'negative' | 'neutral';
  icon?: any;
  href?: string;
  onClick?: () => void;
  loading?: boolean;
}

export interface DashboardGridProps {
  stats: StatItem[];
  columns?: 1 | 2 | 3 | 4;
  loading?: boolean;
  className?: string;
}

export function DashboardGrid({
  stats,
  columns = 4,
  loading = false,
  className
}: DashboardGridProps) {
  const gridCols = {
    1: 'grid-cols-1',
    2: 'grid-cols-1 sm:grid-cols-2',
    3: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3',
    4: 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-4'
  };

  return (
    <div className={clsx('grid gap-5', gridCols[columns], className)}>
      {stats.map((item) => {
        const Icon = item.icon;
        const isClickable = item.href || item.onClick;

        const content = (
          <div className={clsx(
            'card transition-shadow',
            isClickable && 'hover:shadow-md cursor-pointer'
          )}>
            <div className="card-content">
              <div className="flex items-center">
                {Icon && (
                  <div className="flex-shrink-0">
                    <Icon className={clsx(
                      'h-8 w-8',
                      item.changeType === 'positive' ? 'text-success-600' :
                      item.changeType === 'negative' ? 'text-danger-600' :
                      'text-primary-600'
                    )} />
                  </div>
                )}
                <div className={clsx('flex-1', Icon && 'ml-4')}>
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">
                      {item.name}
                    </dt>
                    <dd className="text-lg font-medium text-gray-900">
                      {loading || item.loading ? (
                        <LoadingSpinner size="small" />
                      ) : (
                        item.value
                      )}
                    </dd>
                  </dl>
                </div>
              </div>
              {item.change && (
                <div className="mt-2">
                  <div className={clsx(
                    'text-sm',
                    item.changeType === 'positive' ? 'text-success-600' :
                    item.changeType === 'negative' ? 'text-danger-600' :
                    'text-gray-600'
                  )}>
                    {item.change}
                  </div>
                </div>
              )}
            </div>
          </div>
        );

        if (item.onClick) {
          return (
            <div key={item.name} onClick={item.onClick}>
              {content}
            </div>
          );
        }

        if (item.href) {
          return (
            <a key={item.name} href={item.href}>
              {content}
            </a>
          );
        }

        return (
          <div key={item.name}>
            {content}
          </div>
        );
      })}
    </div>
  );
}
