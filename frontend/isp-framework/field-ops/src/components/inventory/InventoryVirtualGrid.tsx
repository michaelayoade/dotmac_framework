'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { Package, AlertTriangle, CheckCircle, Barcode, Search, Filter } from 'lucide-react';
import { motion } from 'framer-motion';
import { useVirtualGrid } from '../../lib/performance/virtual-scrolling';
import { performanceMonitor } from '../../lib/performance/performance-monitor';
import { db } from '../../lib/offline-db';
import { technicianApiClient } from '../../lib/api/technician-client';
import { featureFlags } from '../../lib/config/environment';
import type { InventoryItem } from '../../lib/offline-db';

interface InventoryGridProps {
  onItemSelect?: (item: InventoryItem) => void;
  maxItems?: number;
  enableVirtualization?: boolean;
  columnsCount?: number;
}

export function InventoryVirtualGrid({
  onItemSelect,
  maxItems = 1000,
  enableVirtualization = true,
  columnsCount = 3,
}: InventoryGridProps) {
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [filteredInventory, setFilteredInventory] = useState<InventoryItem[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [stockFilter, setStockFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);
  const [containerDimensions, setContainerDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    performanceMonitor.markStart('inventory_load');
    loadInventory();
  }, []);

  useEffect(() => {
    // Update container dimensions based on screen size
    const updateDimensions = () => {
      const width = Math.min(window.innerWidth - 32, 1200); // Max width with padding
      const height = Math.min(window.innerHeight - 200, 800); // Max height accounting for header
      setContainerDimensions({ width, height });
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  useEffect(() => {
    performanceMonitor.markStart('inventory_filter');

    let filtered = inventory;

    // Search filter
    if (searchTerm.trim()) {
      filtered = filtered.filter(
        (item) =>
          item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          item.sku.toLowerCase().includes(searchTerm.toLowerCase()) ||
          item.description.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Category filter
    if (categoryFilter !== 'all') {
      filtered = filtered.filter((item) => item.category === categoryFilter);
    }

    // Stock filter
    if (stockFilter !== 'all') {
      switch (stockFilter) {
        case 'low':
          filtered = filtered.filter((item) => item.quantity <= item.minStock);
          break;
        case 'out':
          filtered = filtered.filter((item) => item.quantity === 0);
          break;
        case 'available':
          filtered = filtered.filter((item) => item.quantity > 0);
          break;
      }
    }

    // Limit items for performance
    if (filtered.length > maxItems) {
      filtered = filtered.slice(0, maxItems);
      console.warn(`InventoryGrid: Truncated to ${maxItems} items for performance`);
    }

    setFilteredInventory(filtered);

    const filterTime = performanceMonitor.markEnd('inventory_filter');
    if (filterTime && filterTime > 100) {
      console.warn(`Inventory filtering took ${filterTime}ms`);
    }
  }, [inventory, searchTerm, categoryFilter, stockFilter, maxItems]);

  const loadInventory = async () => {
    performanceMonitor.markStart('inventory_db_load');

    try {
      // Load from IndexedDB first
      const localInventory = await db.inventory.orderBy('name').toArray();
      setInventory(localInventory);
      setLoading(false);

      performanceMonitor.markEnd('inventory_db_load');
      performanceMonitor.markEnd('inventory_load');

      // Background sync with server
      syncInventory();
    } catch (error) {
      console.error('Failed to load inventory from local DB:', error);
      setLoading(false);
    }
  };

  const syncInventory = async () => {
    if (!navigator.onLine) return;

    try {
      performanceMonitor.markStart('inventory_api_sync');

      const apiResponse = await technicianApiClient.getInventory();

      if (apiResponse.success && apiResponse.data && apiResponse.data.length > 0) {
        await db.transaction('rw', db.inventory, async () => {
          await db.inventory.clear();
          await db.inventory.bulkAdd(apiResponse.data!);
        });

        setInventory(apiResponse.data);
        console.log('Inventory synced from server');
      }

      performanceMonitor.markEnd('inventory_api_sync');
    } catch (error) {
      console.error('Failed to sync inventory:', error);
    }
  };

  // Get unique categories for filter
  const categories = useMemo(() => {
    const uniqueCategories = [...new Set(inventory.map((item) => item.category))];
    return uniqueCategories.sort();
  }, [inventory]);

  // Calculate grid dimensions
  const itemWidth = Math.floor(
    (containerDimensions.width - 32 - (columnsCount - 1) * 16) / columnsCount
  );
  const itemHeight = 240;

  // Virtual grid configuration
  const virtualGridProps = useMemo(
    () => ({
      items: filteredInventory,
      itemWidth,
      itemHeight,
      containerWidth: containerDimensions.width,
      containerHeight: containerDimensions.height,
      columnsCount,
      gap: 16,
      overscan: 3,
    }),
    [filteredInventory, itemWidth, itemHeight, containerDimensions, columnsCount]
  );

  const { containerProps, virtualItems, totalHeight } = useVirtualGrid(virtualGridProps);

  // Render inventory item
  const renderInventoryItem = React.useCallback(
    (item: InventoryItem, index: number, style: React.CSSProperties) => {
      const getStockStatus = (item: InventoryItem) => {
        if (item.quantity === 0) return { status: 'out', color: 'text-red-600', bg: 'bg-red-50' };
        if (item.quantity <= item.minStock)
          return { status: 'low', color: 'text-orange-600', bg: 'bg-orange-50' };
        return { status: 'good', color: 'text-green-600', bg: 'bg-green-50' };
      };

      const stockStatus = getStockStatus(item);

      return (
        <div style={style} className='p-2'>
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.2, delay: index * 0.01 }}
            className='bg-white rounded-lg shadow-sm border border-gray-200 p-4 h-full
                     hover:shadow-md hover:border-blue-200 transition-all duration-200 cursor-pointer
                     flex flex-col'
            onClick={() => onItemSelect?.(item)}
          >
            {/* Header */}
            <div className='flex items-start justify-between mb-3'>
              <div className='flex items-center space-x-2'>
                <Package className='w-6 h-6 text-gray-400' />
                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium ${stockStatus.bg} ${stockStatus.color}`}
                >
                  {stockStatus.status === 'out'
                    ? 'Out'
                    : stockStatus.status === 'low'
                      ? 'Low'
                      : 'Available'}
                </span>
              </div>
              {item.barcode && <Barcode className='w-4 h-4 text-gray-400' />}
            </div>

            {/* Item Details */}
            <div className='flex-1'>
              <h3 className='font-semibold text-gray-900 text-sm mb-1 line-clamp-2'>{item.name}</h3>
              <p className='text-xs text-gray-500 mb-2'>SKU: {item.sku}</p>
              <p className='text-xs text-gray-600 mb-3 line-clamp-2'>{item.description}</p>
              <div className='text-xs text-gray-500'>
                <span className='font-medium'>{item.category}</span>
              </div>
            </div>

            {/* Stock Information */}
            <div className='border-t pt-3 mt-auto'>
              <div className='flex items-center justify-between text-xs'>
                <span className='text-gray-500'>Quantity</span>
                <span className={`font-semibold ${stockStatus.color}`}>{item.quantity}</span>
              </div>
              <div className='flex items-center justify-between text-xs mt-1'>
                <span className='text-gray-500'>Min Stock</span>
                <span className='text-gray-700'>{item.minStock}</span>
              </div>
              <div className='flex items-center justify-between text-xs mt-1'>
                <span className='text-gray-500'>Location</span>
                <span className='text-gray-700 truncate max-w-16' title={item.location}>
                  {item.location}
                </span>
              </div>
              {item.reserved > 0 && (
                <div className='flex items-center justify-between text-xs mt-1'>
                  <span className='text-gray-500'>Reserved</span>
                  <span className='text-orange-600 font-medium'>{item.reserved}</span>
                </div>
              )}
            </div>

            {/* Sync Status */}
            {item.syncStatus !== 'synced' && (
              <div className='mt-2 pt-2 border-t'>
                <span className='text-xs text-orange-600 bg-orange-50 px-2 py-1 rounded-full'>
                  Pending sync
                </span>
              </div>
            )}
          </motion.div>
        </div>
      );
    },
    [onItemSelect]
  );

  if (loading) {
    return (
      <div className='flex items-center justify-center py-12'>
        <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600' />
        <span className='ml-3 text-gray-600'>Loading inventory...</span>
      </div>
    );
  }

  return (
    <div className='w-full'>
      {/* Filters */}
      <div className='p-4 bg-gray-50 border-b'>
        <div className='flex flex-col lg:flex-row gap-3 mb-3'>
          {/* Search */}
          <div className='flex-1 relative'>
            <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5' />
            <input
              type='text'
              placeholder='Search inventory...'
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className='w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            />
          </div>

          {/* Category Filter */}
          <div className='relative min-w-40'>
            <Filter className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5' />
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className='w-full pl-10 pr-8 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white'
            >
              <option value='all'>All Categories</option>
              {categories.map((category) => (
                <option key={category} value={category}>
                  {category}
                </option>
              ))}
            </select>
          </div>

          {/* Stock Filter */}
          <div className='relative min-w-32'>
            <select
              value={stockFilter}
              onChange={(e) => setStockFilter(e.target.value)}
              className='w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white'
            >
              <option value='all'>All Stock</option>
              <option value='available'>Available</option>
              <option value='low'>Low Stock</option>
              <option value='out'>Out of Stock</option>
            </select>
          </div>
        </div>

        {/* Results count */}
        <div className='text-sm text-gray-600'>
          {filteredInventory.length === maxItems && inventory.length > maxItems ? (
            <span className='text-orange-600'>
              Showing first {filteredInventory.length} of {inventory.length} items
            </span>
          ) : (
            <span>
              {filteredInventory.length} item{filteredInventory.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Virtual Grid */}
      {enableVirtualization && filteredInventory.length > 12 ? (
        <div className='relative'>
          <div {...containerProps}>
            <div style={{ height: totalHeight, position: 'relative' }}>
              {virtualItems.map((virtualItem) => (
                <div key={virtualItem.index} style={virtualItem.style}>
                  {renderInventoryItem(virtualItem.data, virtualItem.index, virtualItem.style)}
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        // Fallback to regular grid for small lists
        <div className='p-4'>
          <div
            className='grid gap-4'
            style={{
              gridTemplateColumns: `repeat(${columnsCount}, 1fr)`,
              maxHeight: '600px',
              overflowY: 'auto',
            }}
          >
            {filteredInventory.map((item, index) => (
              <div key={item.id}>{renderInventoryItem(item, index, {})}</div>
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {filteredInventory.length === 0 && !loading && (
        <div className='flex flex-col items-center justify-center py-12'>
          <Package className='w-12 h-12 text-gray-400 mb-4' />
          <p className='text-lg font-medium text-gray-600 mb-2'>No inventory items found</p>
          <p className='text-sm text-gray-500 text-center max-w-md'>
            {searchTerm || categoryFilter !== 'all' || stockFilter !== 'all'
              ? 'Try adjusting your filters to see more results'
              : 'Inventory items will appear here once they are loaded'}
          </p>
        </div>
      )}

      {/* Performance indicators (development only) */}
      {featureFlags.isDebugLoggingEnabled() && (
        <div className='fixed bottom-4 left-4 bg-black bg-opacity-75 text-white p-2 rounded text-xs'>
          Items: {filteredInventory.length} | Virtual:{' '}
          {enableVirtualization && filteredInventory.length > 12 ? 'ON' : 'OFF'} | Cols:{' '}
          {columnsCount}
        </div>
      )}
    </div>
  );
}
