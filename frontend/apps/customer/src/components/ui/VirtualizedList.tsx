/**
 * Performance-optimized virtualized list component for large datasets
 */
import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';

export interface VirtualizedListProps<T> {
  items: T[];
  itemHeight: number;
  containerHeight: number;
  renderItem: (item: T, index: number) => React.ReactNode;
  overscan?: number;
  className?: string;
  onScroll?: (scrollTop: number) => void;
  loading?: boolean;
  emptyMessage?: string;
}

export function VirtualizedList<T>({
  items,
  itemHeight,
  containerHeight,
  renderItem,
  overscan = 5,
  className = '',
  onScroll,
  loading = false,
  emptyMessage = 'No items to display'
}: VirtualizedListProps<T>) {
  const [scrollTop, setScrollTop] = useState(0);
  const scrollElementRef = useRef<HTMLDivElement>(null);

  // Calculate visible range with overscan
  const visibleRange = useMemo(() => {
    const start = Math.floor(scrollTop / itemHeight);
    const end = Math.min(
      start + Math.ceil(containerHeight / itemHeight),
      items.length - 1
    );

    return {
      start: Math.max(0, start - overscan),
      end: Math.min(items.length - 1, end + overscan)
    };
  }, [scrollTop, itemHeight, containerHeight, overscan, items.length]);

  // Get visible items
  const visibleItems = useMemo(() => {
    return items.slice(visibleRange.start, visibleRange.end + 1);
  }, [items, visibleRange]);

  // Handle scroll with throttling
  const handleScroll = useCallback((e: React.UIEvent<HTMLDivElement>) => {
    const newScrollTop = e.currentTarget.scrollTop;
    setScrollTop(newScrollTop);
    onScroll?.(newScrollTop);
  }, [onScroll]);

  // Calculate total height
  const totalHeight = items.length * itemHeight;

  // Calculate offset for visible items
  const offsetY = visibleRange.start * itemHeight;

  if (loading) {
    return (
      <div className={`${className}`} style={{ height: containerHeight }}>
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
          <span className="ml-3 text-gray-600">Loading...</span>
        </div>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className={`${className}`} style={{ height: containerHeight }}>
        <div className="flex items-center justify-center h-full text-gray-500">
          {emptyMessage}
        </div>
      </div>
    );
  }

  return (
    <div
      ref={scrollElementRef}
      className={`overflow-auto ${className}`}
      style={{ height: containerHeight }}
      onScroll={handleScroll}
    >
      {/* Total height container for scrollbar */}
      <div style={{ height: totalHeight, position: 'relative' }}>
        {/* Visible items container */}
        <div style={{ transform: `translateY(${offsetY}px)` }}>
          {visibleItems.map((item, index) => (
            <div
              key={visibleRange.start + index}
              style={{ height: itemHeight }}
              className="flex items-center"
            >
              {renderItem(item, visibleRange.start + index)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// Optimized list item component with memoization
interface ListItemProps<T> {
  item: T;
  index: number;
  isSelected?: boolean;
  onClick?: (item: T, index: number) => void;
  className?: string;
  children: React.ReactNode;
}

export const VirtualizedListItem = React.memo(<T,>({
  item,
  index,
  isSelected = false,
  onClick,
  className = '',
  children
}: ListItemProps<T>) => {
  const handleClick = useCallback(() => {
    onClick?.(item, index);
  }, [onClick, item, index]);

  return (
    <div
      className={`
        w-full px-4 py-2 cursor-pointer transition-colors
        ${isSelected ? 'bg-blue-50 border-l-4 border-blue-500' : 'hover:bg-gray-50'}
        ${className}
      `}
      onClick={handleClick}
    >
      {children}
    </div>
  );
}) as <T>(props: ListItemProps<T>) => JSX.Element;

// Hook for managing virtualized list state
export function useVirtualizedList<T>(items: T[], itemHeight: number = 50) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [scrollTop, setScrollTop] = useState(0);

  const selectedItem = useMemo(() => {
    return selectedIndex !== null ? items[selectedIndex] : null;
  }, [items, selectedIndex]);

  const selectItem = useCallback((index: number) => {
    setSelectedIndex(index);
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedIndex(null);
  }, []);

  const scrollToItem = useCallback((index: number, behavior: ScrollBehavior = 'smooth') => {
    const targetScrollTop = index * itemHeight;
    setScrollTop(targetScrollTop);
    
    // If we have a ref to the scroll container, scroll it
    return targetScrollTop;
  }, [itemHeight]);

  const getItemsInRange = useCallback((start: number, end: number) => {
    return items.slice(Math.max(0, start), Math.min(items.length, end + 1));
  }, [items]);

  return {
    selectedIndex,
    selectedItem,
    scrollTop,
    selectItem,
    clearSelection,
    scrollToItem,
    getItemsInRange,
    setScrollTop
  };
}