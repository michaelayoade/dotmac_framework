'use client';

import React, { useState, useEffect, useMemo } from 'react';
import {
  MapPin,
  Clock,
  Phone,
  Navigation,
  CheckCircle,
  AlertCircle,
  Calendar,
  User,
  Filter,
  Search,
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { VirtualList } from '../../lib/performance/virtual-scrolling';
import { performanceMonitor } from '../../lib/performance/performance-monitor';
import { db } from '../../lib/offline-db';
import { technicianApiClient } from '../../lib/api/technician-client';
import { featureFlags } from '../../lib/config/environment';
import type { WorkOrder } from '../../lib/offline-db';

interface WorkOrderListProps {
  onWorkOrderSelect?: (workOrder: WorkOrder) => void;
  maxItems?: number;
  enableVirtualization?: boolean;
}

export function WorkOrdersVirtualList({
  onWorkOrderSelect,
  maxItems = 1000,
  enableVirtualization = true,
}: WorkOrderListProps) {
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [filteredOrders, setFilteredOrders] = useState<WorkOrder[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  // Performance monitoring
  React.useEffect(() => {
    performanceMonitor.markStart('work_orders_load');
  }, []);

  useEffect(() => {
    loadWorkOrders();
  }, []);

  useEffect(() => {
    performanceMonitor.markStart('work_orders_filter');

    let filtered = workOrders;

    // Search filter
    if (searchTerm.trim()) {
      filtered = filtered.filter(
        (order) =>
          order.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
          order.customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          order.location.address.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter((order) => order.status === statusFilter);
    }

    // Limit items for performance
    if (filtered.length > maxItems) {
      filtered = filtered.slice(0, maxItems);
      console.warn(`WorkOrdersList: Truncated to ${maxItems} items for performance`);
    }

    setFilteredOrders(filtered);

    const filterTime = performanceMonitor.markEnd('work_orders_filter');
    if (filterTime && filterTime > 100) {
      console.warn(`Work orders filtering took ${filterTime}ms`);
    }
  }, [workOrders, searchTerm, statusFilter, maxItems]);

  const loadWorkOrders = async () => {
    performanceMonitor.markStart('work_orders_db_load');

    try {
      // Load from IndexedDB first (fast)
      const localOrders = await db.workOrders.orderBy('scheduledDate').toArray();
      setWorkOrders(localOrders);
      setLoading(false);

      performanceMonitor.markEnd('work_orders_db_load');
      performanceMonitor.markEnd('work_orders_load');

      // Background sync with server
      syncWorkOrders();
    } catch (error) {
      console.error('Failed to load work orders from local DB:', error);
      setLoading(false);
    }
  };

  const syncWorkOrders = async () => {
    if (!navigator.onLine) return;

    try {
      performanceMonitor.markStart('work_orders_api_sync');

      const apiResponse = await technicianApiClient.getWorkOrders();

      if (apiResponse.success && apiResponse.data && apiResponse.data.length > 0) {
        // Batch update for better performance
        await db.transaction('rw', db.workOrders, async () => {
          await db.workOrders.clear();
          await db.workOrders.bulkAdd(apiResponse.data!);
        });

        setWorkOrders(apiResponse.data);
        console.log('Work orders synced from server');
      }

      performanceMonitor.markEnd('work_orders_api_sync');
    } catch (error) {
      console.error('Failed to sync work orders:', error);
    }
  };

  // Memoized work order item renderer for virtual scrolling
  const renderWorkOrderItem = React.useCallback(
    (workOrder: WorkOrder, index: number, style: React.CSSProperties) => {
      const getPriorityColor = (priority: WorkOrder['priority']) => {
        switch (priority) {
          case 'urgent':
            return 'text-red-600 bg-red-50';
          case 'high':
            return 'text-orange-600 bg-orange-50';
          case 'medium':
            return 'text-yellow-600 bg-yellow-50';
          case 'low':
            return 'text-green-600 bg-green-50';
          default:
            return 'text-gray-600 bg-gray-50';
        }
      };

      const getStatusIcon = (status: WorkOrder['status']) => {
        switch (status) {
          case 'completed':
            return <CheckCircle className='w-5 h-5 text-green-600' />;
          case 'in_progress':
            return <Clock className='w-5 h-5 text-blue-600' />;
          case 'pending':
            return <AlertCircle className='w-5 h-5 text-orange-600' />;
          default:
            return <Clock className='w-5 h-5 text-gray-600' />;
        }
      };

      const formatDate = (dateString: string) => {
        const date = new Date(dateString);
        return date.toLocaleDateString('en-US', {
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
        });
      };

      return (
        <div style={style}>
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.2, delay: index * 0.02 }}
            className='bg-white rounded-xl shadow-sm border border-gray-200 p-4 mx-4 mb-3 
                     hover:shadow-md hover:border-blue-200 transition-all duration-200 cursor-pointer'
            onClick={() => onWorkOrderSelect?.(workOrder)}
          >
            {/* Header */}
            <div className='flex items-start justify-between mb-3'>
              <div className='flex-1 min-w-0'>
                <div className='flex items-center space-x-2 mb-1'>
                  <span className='text-xs font-semibold text-gray-500'>#{workOrder.id}</span>
                  <span
                    className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${getPriorityColor(workOrder.priority)}`}
                  >
                    {workOrder.priority}
                  </span>
                  <div className='flex items-center text-gray-400'>
                    {getStatusIcon(workOrder.status)}
                  </div>
                </div>
                <h3 className='text-base font-semibold text-gray-900 truncate'>
                  {workOrder.title}
                </h3>
                <p className='text-sm text-gray-600 truncate mt-1'>{workOrder.description}</p>
              </div>
            </div>

            {/* Details Grid */}
            <div className='grid grid-cols-1 md:grid-cols-2 gap-3'>
              {/* Customer */}
              <div className='flex items-center space-x-2'>
                <User className='w-4 h-4 text-gray-400 flex-shrink-0' />
                <div className='min-w-0 flex-1'>
                  <p className='text-sm font-medium text-gray-900 truncate'>
                    {workOrder.customer.name}
                  </p>
                </div>
              </div>

              {/* Phone */}
              <div className='flex items-center space-x-2'>
                <Phone className='w-4 h-4 text-gray-400 flex-shrink-0' />
                <div className='min-w-0 flex-1'>
                  <p className='text-sm text-gray-600 truncate'>{workOrder.customer.phone}</p>
                </div>
              </div>

              {/* Location */}
              <div className='flex items-center space-x-2'>
                <MapPin className='w-4 h-4 text-gray-400 flex-shrink-0' />
                <div className='min-w-0 flex-1'>
                  <p className='text-sm text-gray-600 truncate'>{workOrder.location.address}</p>
                </div>
              </div>

              {/* Scheduled Date */}
              <div className='flex items-center space-x-2'>
                <Calendar className='w-4 h-4 text-gray-400 flex-shrink-0' />
                <div className='min-w-0 flex-1'>
                  <p className='text-sm text-gray-600 truncate'>
                    {formatDate(workOrder.scheduledDate)}
                  </p>
                </div>
              </div>
            </div>

            {/* Progress Indicators */}
            {workOrder.checklist.length > 0 && (
              <div className='mt-3 pt-3 border-t border-gray-100'>
                <div className='flex items-center justify-between text-xs text-gray-500'>
                  <span>
                    Checklist: {workOrder.checklist.filter((item) => item.completed).length} /{' '}
                    {workOrder.checklist.length}
                  </span>
                  <div className='flex space-x-1'>
                    {workOrder.photos.length > 0 && (
                      <span className='bg-blue-100 text-blue-600 px-2 py-1 rounded-full'>
                        {workOrder.photos.length} photos
                      </span>
                    )}
                    {workOrder.syncStatus !== 'synced' && (
                      <span className='bg-orange-100 text-orange-600 px-2 py-1 rounded-full'>
                        Pending sync
                      </span>
                    )}
                  </div>
                </div>
              </div>
            )}
          </motion.div>
        </div>
      );
    },
    [onWorkOrderSelect]
  );

  // Virtual list configuration
  const virtualListProps = useMemo(
    () => ({
      items: filteredOrders,
      itemHeight: 200, // Approximate height per work order item
      containerHeight: 600, // Container height
      renderItem: renderWorkOrderItem,
      overscan: 5,
      className: 'work-orders-virtual-list',
      onItemsRendered: (startIndex: number, endIndex: number) => {
        performanceMonitor.recordCustomMetric(
          'work_orders_visible_range',
          endIndex - startIndex + 1
        );
      },
      emptyComponent: (
        <div className='flex flex-col items-center justify-center py-12'>
          <AlertCircle className='w-12 h-12 text-gray-400 mb-4' />
          <p className='text-lg font-medium text-gray-600 mb-2'>No work orders found</p>
          <p className='text-sm text-gray-500 text-center max-w-md'>
            {searchTerm || statusFilter !== 'all'
              ? 'Try adjusting your filters to see more results'
              : 'Work orders will appear here once they are assigned to you'}
          </p>
        </div>
      ),
      loadingComponent: (
        <div className='flex items-center justify-center py-12'>
          <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600' />
          <span className='ml-3 text-gray-600'>Loading work orders...</span>
        </div>
      ),
    }),
    [filteredOrders, renderWorkOrderItem, searchTerm, statusFilter]
  );

  if (loading) {
    return (
      <div className='flex items-center justify-center py-12'>
        <div className='animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600' />
        <span className='ml-3 text-gray-600'>Loading work orders...</span>
      </div>
    );
  }

  return (
    <div className='w-full'>
      {/* Filters */}
      <div className='p-4 bg-gray-50 border-b'>
        <div className='flex flex-col sm:flex-row gap-3'>
          {/* Search */}
          <div className='flex-1 relative'>
            <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5' />
            <input
              type='text'
              placeholder='Search work orders...'
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className='w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent'
            />
          </div>

          {/* Status Filter */}
          <div className='relative'>
            <Filter className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5' />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className='pl-10 pr-8 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent appearance-none bg-white min-w-32'
            >
              <option value='all'>All Status</option>
              <option value='pending'>Pending</option>
              <option value='in_progress'>In Progress</option>
              <option value='completed'>Completed</option>
              <option value='cancelled'>Cancelled</option>
            </select>
          </div>
        </div>

        {/* Results count */}
        <div className='mt-3 text-sm text-gray-600'>
          {filteredOrders.length === maxItems && workOrders.length > maxItems ? (
            <span className='text-orange-600'>
              Showing first {filteredOrders.length} of {workOrders.length} work orders
            </span>
          ) : (
            <span>
              {filteredOrders.length} work order{filteredOrders.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>

      {/* Virtual List */}
      {enableVirtualization && filteredOrders.length > 20 ? (
        <VirtualList {...virtualListProps} />
      ) : (
        // Fallback to regular rendering for small lists
        <div className='max-h-96 overflow-y-auto'>
          {filteredOrders.map((workOrder, index) => (
            <div key={workOrder.id}>{renderWorkOrderItem(workOrder, index, {})}</div>
          ))}
        </div>
      )}

      {/* Performance indicators (development only) */}
      {featureFlags.isDebugLoggingEnabled() && (
        <div className='fixed bottom-4 right-4 bg-black bg-opacity-75 text-white p-2 rounded text-xs'>
          Items: {filteredOrders.length} | Virtual:{' '}
          {enableVirtualization && filteredOrders.length > 20 ? 'ON' : 'OFF'}
        </div>
      )}
    </div>
  );
}
