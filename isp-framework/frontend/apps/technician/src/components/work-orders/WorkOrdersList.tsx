'use client';

import { useState, useEffect } from 'react';
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
import { motion } from 'framer-motion';
import { db, SyncManager } from '../../lib/offline-db';
import type { WorkOrder } from '../../lib/offline-db';

const mockWorkOrders: WorkOrder[] = [
  {
    id: 'WO-001',
    customerId: 'CUST-001',
    technicianId: 'TECH-001',
    title: 'Fiber Installation - Residential',
    description: 'Install fiber optic internet service for residential customer',
    priority: 'high',
    status: 'pending',
    scheduledDate: new Date().toISOString(),
    assignedAt: new Date().toISOString(),
    location: {
      address: '123 Main St, Seattle, WA 98101',
      coordinates: [47.6062, -122.3321],
      apartment: 'Apt 2B',
      accessNotes: 'Use side entrance, ring doorbell twice',
    },
    customer: {
      name: 'John Smith',
      phone: '+1 (555) 123-4567',
      email: 'john@example.com',
      serviceId: 'SRV-001',
    },
    equipment: {
      type: 'fiber_modem',
      model: 'Nokia 7368 ISAM',
      required: ['Fiber ONT', 'Ethernet Cable', 'Power Adapter'],
    },
    checklist: [
      { id: 'check-1', text: 'Verify service location', completed: false, required: true },
      { id: 'check-2', text: 'Install ONT device', completed: false, required: true },
      { id: 'check-3', text: 'Connect and test internet', completed: false, required: true },
      { id: 'check-4', text: 'Customer walkthrough', completed: false, required: true },
    ],
    photos: [],
    notes: '',
    syncStatus: 'synced',
    lastModified: new Date().toISOString(),
  },
  {
    id: 'WO-002',
    customerId: 'CUST-002',
    technicianId: 'TECH-001',
    title: 'Service Repair - Connection Issues',
    description: 'Customer reporting intermittent connection drops',
    priority: 'medium',
    status: 'in_progress',
    scheduledDate: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(), // 2 hours from now
    assignedAt: new Date().toISOString(),
    location: {
      address: '456 Oak Ave, Bellevue, WA 98004',
      coordinates: [47.6101, -122.2015],
      accessNotes: 'Equipment in basement',
    },
    customer: {
      name: 'Sarah Johnson',
      phone: '+1 (555) 987-6543',
      email: 'sarah@example.com',
      serviceId: 'SRV-002',
    },
    equipment: {
      type: 'cable_modem',
      model: 'ARRIS SURFboard',
      required: ['Coax Cable', 'Signal Meter'],
    },
    checklist: [
      { id: 'check-1', text: 'Test signal strength', completed: true, required: true },
      { id: 'check-2', text: 'Check cable connections', completed: true, required: true },
      { id: 'check-3', text: 'Replace faulty equipment', completed: false, required: true },
      { id: 'check-4', text: 'Verify stable connection', completed: false, required: true },
    ],
    photos: [],
    notes: 'Found loose coax connection in basement. Signal levels normal after tightening.',
    syncStatus: 'pending',
    lastModified: new Date().toISOString(),
  },
];

export function WorkOrdersList() {
  const [workOrders, setWorkOrders] = useState<WorkOrder[]>([]);
  const [filteredOrders, setFilteredOrders] = useState<WorkOrder[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadWorkOrders();
  }, []);

  useEffect(() => {
    // Initialize with mock data if no orders exist
    const initializeMockData = async () => {
      try {
        const existingOrders = await db.workOrders.toArray();
        if (existingOrders.length === 0) {
          await db.workOrders.bulkAdd(mockWorkOrders);
          console.log('Mock work orders initialized');
        }
      } catch (error) {
        console.error('Failed to initialize mock data:', error);
      }
    };

    initializeMockData();
  }, []);

  useEffect(() => {
    filterOrders();
  }, [workOrders, searchTerm, statusFilter]);

  const loadWorkOrders = async () => {
    try {
      setLoading(true);
      const orders = await db.workOrders.orderBy('scheduledDate').toArray();
      setWorkOrders(orders);
    } catch (error) {
      console.error('Failed to load work orders:', error);
    } finally {
      setLoading(false);
    }
  };

  const filterOrders = () => {
    let filtered = workOrders;

    // Filter by status
    if (statusFilter !== 'all') {
      filtered = filtered.filter((order) => order.status === statusFilter);
    }

    // Filter by search term
    if (searchTerm) {
      filtered = filtered.filter(
        (order) =>
          order.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
          order.customer.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
          order.location.address.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    setFilteredOrders(filtered);
  };

  const updateOrderStatus = async (orderId: string, newStatus: WorkOrder['status']) => {
    try {
      await db.workOrders.update(orderId, {
        status: newStatus,
        completedAt: newStatus === 'completed' ? new Date().toISOString() : undefined,
        syncStatus: 'pending',
      });

      // Add to sync queue
      const order = await db.workOrders.get(orderId);
      if (order) {
        await SyncManager.addToSyncQueue('work_order', 'update', order, 1);
      }

      await loadWorkOrders();

      // Haptic feedback
      if ('vibrate' in navigator) {
        navigator.vibrate(50);
      }
    } catch (error) {
      console.error('Failed to update order status:', error);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-700 bg-green-100 border-green-200';
      case 'in_progress':
        return 'text-blue-700 bg-blue-100 border-blue-200';
      case 'pending':
        return 'text-yellow-700 bg-yellow-100 border-yellow-200';
      case 'cancelled':
        return 'text-red-700 bg-red-100 border-red-200';
      default:
        return 'text-gray-700 bg-gray-100 border-gray-200';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'bg-red-500';
      case 'high':
        return 'bg-orange-500';
      case 'medium':
        return 'bg-yellow-500';
      case 'low':
        return 'bg-green-500';
      default:
        return 'bg-gray-500';
    }
  };

  const formatTime = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleTimeString('en-US', {
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);

    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === tomorrow.toDateString()) {
      return 'Tomorrow';
    } else {
      return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric',
      });
    }
  };

  const openMaps = (address: string) => {
    const encodedAddress = encodeURIComponent(address);
    const mapsUrl = `https://www.google.com/maps?q=${encodedAddress}`;
    window.open(mapsUrl, '_blank');
  };

  const callCustomer = (phone: string) => {
    window.location.href = `tel:${phone}`;
  };

  if (loading) {
    return (
      <div className='space-y-4'>
        {[...Array(3)].map((_, i) => (
          <div key={i} className='mobile-card animate-pulse'>
            <div className='flex space-x-3'>
              <div className='w-2 h-16 bg-gray-200 rounded-full'></div>
              <div className='flex-1 space-y-2'>
                <div className='h-4 bg-gray-200 rounded w-3/4'></div>
                <div className='h-3 bg-gray-200 rounded w-1/2'></div>
                <div className='h-3 bg-gray-200 rounded w-2/3'></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className='space-y-4'>
      {/* Search and Filter */}
      <div className='mobile-card'>
        <div className='space-y-3'>
          <div className='relative'>
            <Search className='absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4' />
            <input
              type='text'
              placeholder='Search work orders...'
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className='mobile-input pl-10'
            />
          </div>

          <div className='flex items-center space-x-2'>
            <Filter className='w-4 h-4 text-gray-400' />
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className='mobile-input flex-1'
            >
              <option value='all'>All Status</option>
              <option value='pending'>Pending</option>
              <option value='in_progress'>In Progress</option>
              <option value='completed'>Completed</option>
              <option value='cancelled'>Cancelled</option>
            </select>
          </div>
        </div>
      </div>

      {/* Work Orders List */}
      <div className='space-y-3'>
        {filteredOrders.map((order, index) => (
          <motion.div
            key={order.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
            className='mobile-card'
          >
            <div className='flex space-x-3'>
              {/* Priority Indicator */}
              <div className={`w-2 h-full rounded-full ${getPriorityColor(order.priority)}`} />

              <div className='flex-1 min-w-0'>
                {/* Header */}
                <div className='flex items-start justify-between mb-2'>
                  <div className='flex-1 min-w-0'>
                    <h3 className='font-semibold text-gray-900 text-sm truncate'>{order.title}</h3>
                    <p className='text-gray-600 text-xs truncate'>Order #{order.id}</p>
                  </div>
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(order.status)}`}
                  >
                    {order.status.replace('_', ' ')}
                  </span>
                </div>

                {/* Customer Info */}
                <div className='flex items-center space-x-4 mb-2'>
                  <div className='flex items-center text-gray-600 text-sm'>
                    <User className='w-3 h-3 mr-1' />
                    <span className='truncate'>{order.customer.name}</span>
                  </div>
                  <button
                    onClick={() => callCustomer(order.customer.phone)}
                    className='flex items-center text-blue-600 text-sm hover:text-blue-700 touch-feedback'
                  >
                    <Phone className='w-3 h-3 mr-1' />
                    <span>Call</span>
                  </button>
                </div>

                {/* Location */}
                <div className='flex items-start justify-between mb-3'>
                  <div className='flex items-start space-x-1 flex-1 min-w-0'>
                    <MapPin className='w-3 h-3 text-gray-400 mt-0.5 flex-shrink-0' />
                    <span className='text-gray-600 text-sm'>{order.location.address}</span>
                  </div>
                  <button
                    onClick={() => openMaps(order.location.address)}
                    className='flex items-center text-blue-600 text-sm hover:text-blue-700 ml-2 flex-shrink-0 touch-feedback'
                  >
                    <Navigation className='w-3 h-3 mr-1' />
                    <span>Navigate</span>
                  </button>
                </div>

                {/* Schedule */}
                <div className='flex items-center justify-between mb-3'>
                  <div className='flex items-center text-gray-600 text-sm'>
                    <Calendar className='w-3 h-3 mr-1' />
                    <span>
                      {formatDate(order.scheduledDate)} at {formatTime(order.scheduledDate)}
                    </span>
                  </div>
                  <div className='flex items-center text-gray-500 text-xs'>
                    <Clock className='w-3 h-3 mr-1' />
                    <span className='capitalize'>{order.priority} priority</span>
                  </div>
                </div>

                {/* Checklist Progress */}
                <div className='mb-3'>
                  <div className='flex items-center justify-between text-sm mb-1'>
                    <span className='text-gray-600'>Progress</span>
                    <span className='text-gray-900 font-medium'>
                      {order.checklist.filter((item) => item.completed).length}/
                      {order.checklist.length}
                    </span>
                  </div>
                  <div className='w-full bg-gray-200 rounded-full h-1.5'>
                    <div
                      className='bg-primary-500 h-1.5 rounded-full transition-all duration-300'
                      style={{
                        width: `${(order.checklist.filter((item) => item.completed).length / order.checklist.length) * 100}%`,
                      }}
                    />
                  </div>
                </div>

                {/* Action Buttons */}
                <div className='flex space-x-2'>
                  {order.status === 'pending' && (
                    <button
                      onClick={() => updateOrderStatus(order.id, 'in_progress')}
                      className='flex-1 bg-primary-500 text-white py-2 px-3 rounded-lg font-medium text-sm touch-feedback'
                    >
                      Start Work
                    </button>
                  )}

                  {order.status === 'in_progress' && (
                    <button
                      onClick={() => updateOrderStatus(order.id, 'completed')}
                      className='flex-1 bg-green-600 text-white py-2 px-3 rounded-lg font-medium text-sm touch-feedback'
                    >
                      Complete
                    </button>
                  )}

                  <button className='mobile-button-secondary text-sm py-2 px-3'>
                    View Details
                  </button>
                </div>

                {/* Sync Status */}
                {order.syncStatus === 'pending' && (
                  <div className='mt-2 flex items-center text-orange-600 text-xs'>
                    <AlertCircle className='w-3 h-3 mr-1' />
                    <span>Pending sync</span>
                  </div>
                )}

                {order.syncStatus === 'synced' && order.status === 'completed' && (
                  <div className='mt-2 flex items-center text-green-600 text-xs'>
                    <CheckCircle className='w-3 h-3 mr-1' />
                    <span>Synced</span>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {filteredOrders.length === 0 && !loading && (
        <div className='text-center py-8'>
          <ClipboardList className='w-12 h-12 text-gray-400 mx-auto mb-4' />
          <h3 className='font-medium text-gray-900 mb-2'>No Work Orders</h3>
          <p className='text-gray-600 text-sm'>
            {searchTerm || statusFilter !== 'all'
              ? 'No work orders match your criteria'
              : 'No work orders assigned yet'}
          </p>
        </div>
      )}
    </div>
  );
}
