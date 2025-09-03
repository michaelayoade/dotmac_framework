'use client';

import { FixedSizeList, VariableSizeList } from 'react-window';
import { memo, useCallback, useMemo } from 'react';
import InfiniteLoader from 'react-window-infinite-loader';

interface VirtualizedListProps<T> {
  items: T[];
  itemHeight: number | ((index: number) => number);
  containerHeight: number;
  renderItem: ({
    item,
    index,
    style,
  }: {
    item: T;
    index: number;
    style: React.CSSProperties;
  }) => React.ReactNode;
  onLoadMore?: () => Promise<void>;
  hasNextPage?: boolean;
  isLoading?: boolean;
  threshold?: number;
  overscan?: number;
}

export function VirtualizedList<T>({
  items,
  itemHeight,
  containerHeight,
  renderItem,
  onLoadMore,
  hasNextPage = false,
  isLoading = false,
  threshold = 15,
  overscan = 5,
}: VirtualizedListProps<T>) {
  const itemCount = hasNextPage ? items.length + 1 : items.length;
  const isItemLoaded = useCallback((index: number) => !!items[index], [items]);

  const MemoizedItem = memo(({ index, style }: { index: number; style: React.CSSProperties }) => {
    const item = items[index];

    // Show loading placeholder for items being loaded
    if (!item) {
      return (
        <div style={style} className='flex items-center justify-center p-4'>
          <div className='animate-pulse flex space-x-4 w-full'>
            <div className='rounded-full bg-gray-300 h-10 w-10'></div>
            <div className='flex-1 space-y-2 py-1'>
              <div className='h-4 bg-gray-300 rounded w-3/4'></div>
              <div className='h-4 bg-gray-300 rounded w-1/2'></div>
            </div>
          </div>
        </div>
      );
    }

    return <div style={style}>{renderItem({ item, index, style })}</div>;
  });

  MemoizedItem.displayName = 'VirtualizedListItem';

  // Use fixed or variable size list based on itemHeight type
  const ListComponent = (
    typeof itemHeight === 'function' ? VariableSizeList : FixedSizeList
  ) as any;

  const listProps = useMemo(() => {
    const baseProps = {
      height: containerHeight,
      itemCount,
      overscanCount: overscan,
      width: '100%',
    };

    if (typeof itemHeight === 'function') {
      return {
        ...baseProps,
        itemSize: itemHeight,
      };
    } else {
      return {
        ...baseProps,
        itemSize: itemHeight,
      };
    }
  }, [containerHeight, itemCount, itemHeight, overscan]);

  if (onLoadMore && hasNextPage) {
    return (
      <InfiniteLoader
        isItemLoaded={isItemLoaded}
        itemCount={itemCount}
        loadMoreItems={onLoadMore}
        threshold={threshold}
      >
        {({ onItemsRendered, ref }) => (
          <ListComponent {...listProps} ref={ref} onItemsRendered={onItemsRendered}>
            {MemoizedItem}
          </ListComponent>
        )}
      </InfiniteLoader>
    );
  }

  return <ListComponent {...listProps}>{MemoizedItem}</ListComponent>;
}

// Specialized components for common use cases
export const VirtualizedPartnerList = memo(
  ({
    partners,
    onLoadMore,
    hasNextPage,
    isLoading,
  }: {
    partners: any[];
    onLoadMore?: () => Promise<void>;
    hasNextPage?: boolean;
    isLoading?: boolean;
  }) => {
    const renderPartner = useCallback(
      ({ item: partner, style }: any) => (
        <div className='border-b border-gray-200 p-4 hover:bg-gray-50'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center space-x-3'>
              <div className='h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center'>
                {partner.company_name.charAt(0).toUpperCase()}
              </div>
              <div>
                <h3 className='font-medium text-gray-900'>{partner.company_name}</h3>
                <p className='text-sm text-gray-500'>{partner.contact_email}</p>
              </div>
            </div>
            <div className='text-right'>
              <div
                className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                  partner.status === 'ACTIVE'
                    ? 'bg-green-100 text-green-800'
                    : partner.status === 'PENDING'
                      ? 'bg-yellow-100 text-yellow-800'
                      : 'bg-red-100 text-red-800'
                }`}
              >
                {partner.status}
              </div>
              <p className='text-sm text-gray-500 mt-1'>{partner.tier}</p>
            </div>
          </div>
        </div>
      ),
      []
    );

    return (
      <VirtualizedList
        items={partners}
        itemHeight={88} // Fixed height for partner items
        containerHeight={600}
        renderItem={renderPartner}
        onLoadMore={onLoadMore}
        hasNextPage={hasNextPage}
        isLoading={isLoading}
      />
    );
  }
);

VirtualizedPartnerList.displayName = 'VirtualizedPartnerList';

export const VirtualizedCommissionList = memo(
  ({
    commissions,
    onLoadMore,
    hasNextPage,
    isLoading,
  }: {
    commissions: any[];
    onLoadMore?: () => Promise<void>;
    hasNextPage?: boolean;
    isLoading?: boolean;
  }) => {
    const renderCommission = useCallback(
      ({ item: commission, style }: any) => (
        <div className='border-b border-gray-200 p-4 hover:bg-gray-50'>
          <div className='flex items-center justify-between'>
            <div>
              <h3 className='font-medium text-gray-900'>{commission.payment_number}</h3>
              <p className='text-sm text-gray-500'>{commission.partner_name}</p>
              <p className='text-xs text-gray-400'>
                {new Date(commission.period_start).toLocaleDateString()} -
                {new Date(commission.period_end).toLocaleDateString()}
              </p>
            </div>
            <div className='text-right'>
              <p className='font-semibold text-gray-900'>
                ${commission.net_amount.toLocaleString()}
              </p>
              <div
                className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                  commission.status === 'PAID'
                    ? 'bg-green-100 text-green-800'
                    : commission.status === 'APPROVED'
                      ? 'bg-blue-100 text-blue-800'
                      : commission.status === 'CALCULATED'
                        ? 'bg-yellow-100 text-yellow-800'
                        : 'bg-red-100 text-red-800'
                }`}
              >
                {commission.status}
              </div>
            </div>
          </div>
        </div>
      ),
      []
    );

    return (
      <VirtualizedList
        items={commissions}
        itemHeight={96} // Fixed height for commission items
        containerHeight={600}
        renderItem={renderCommission}
        onLoadMore={onLoadMore}
        hasNextPage={hasNextPage}
        isLoading={isLoading}
      />
    );
  }
);

VirtualizedCommissionList.displayName = 'VirtualizedCommissionList';
