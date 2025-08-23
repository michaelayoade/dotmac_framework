'use client';

import { useState, useEffect } from 'react';
import {
  ClipboardList,
  Clock,
  MapPin,
  CheckCircle,
  AlertCircle,
  Package,
  Users,
  Navigation,
  Battery,
  Signal,
  Calendar,
  BookOpen,
} from 'lucide-react';
import { motion } from 'framer-motion';
import { db } from '../../lib/offline-db';
import type { WorkOrder, TechnicianProfile } from '../../lib/offline-db';
import { useEnhancedPWA } from '../../hooks/useEnhancedPWA';

interface DashboardStats {
  todayOrders: number;
  completedOrders: number;
  pendingOrders: number;
  totalCustomers: number;
  inventoryItems: number;
  nextAppointment: string | null;
}

export function TechnicianDashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    todayOrders: 0,
    completedOrders: 0,
    pendingOrders: 0,
    totalCustomers: 0,
    inventoryItems: 0,
    nextAppointment: null,
  });
  const [recentOrders, setRecentOrders] = useState<WorkOrder[]>([]);
  const [profile, setProfile] = useState<TechnicianProfile | null>(null);
  const [currentLocation, setCurrentLocation] = useState<{ lat: number; lng: number } | null>(null);
  const [batteryLevel, setBatteryLevel] = useState<number | null>(null);
  const {
    isOffline,
    networkQuality,
    syncStatus,
    pendingSyncCount,
    location: pwaLocation,
    capturePhoto,
    requestPermissions,
  } = useEnhancedPWA();

  // Load dashboard data
  useEffect(() => {
    const loadData = async () => {
      try {
        // Get profile
        const techProfile = await db.profile.orderBy('id').first();
        setProfile(techProfile || null);

        // Get today's date range
        const today = new Date();
        const startOfDay = new Date(today);
        startOfDay.setHours(0, 0, 0, 0);
        const endOfDay = new Date(today);
        endOfDay.setHours(23, 59, 59, 999);

        // Count statistics
        const [
          todayOrdersCount,
          completedOrdersCount,
          pendingOrdersCount,
          customersCount,
          inventoryCount,
          todayOrders,
        ] = await Promise.all([
          // Today's orders
          db.workOrders
            .where('scheduledDate')
            .between(startOfDay.toISOString(), endOfDay.toISOString())
            .count(),

          // Completed orders today
          db.workOrders
            .where('scheduledDate')
            .between(startOfDay.toISOString(), endOfDay.toISOString())
            .and((order) => order.status === 'completed')
            .count(),

          // Pending orders
          db.workOrders.where('status').equals('pending').count(),

          // Total customers
          db.customers.count(),

          // Inventory items
          db.inventory.count(),

          // Recent orders for display
          db.workOrders.orderBy('scheduledDate').reverse().limit(5).toArray(),
        ]);

        // Find next appointment
        const upcomingOrders = await db.workOrders
          .where('scheduledDate')
          .above(new Date().toISOString())
          .and((order) => order.status === 'pending' || order.status === 'in_progress')
          .limit(1)
          .toArray();

        setStats({
          todayOrders: todayOrdersCount,
          completedOrders: completedOrdersCount,
          pendingOrders: pendingOrdersCount,
          totalCustomers: customersCount,
          inventoryItems: inventoryCount,
          nextAppointment: upcomingOrders[0]?.scheduledDate || null,
        });

        setRecentOrders(todayOrders);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      }
    };

    loadData();
  }, []);

  // Use PWA location if available, otherwise fallback to manual geolocation
  useEffect(() => {
    if (pwaLocation) {
      setCurrentLocation({
        lat: pwaLocation.latitude,
        lng: pwaLocation.longitude,
      });
    } else if ('geolocation' in navigator) {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          setCurrentLocation({
            lat: position.coords.latitude,
            lng: position.coords.longitude,
          });
        },
        (error) => {
          console.log('Location access denied or unavailable:', error);
        },
        { enableHighAccuracy: false, timeout: 5000, maximumAge: 300000 }
      );
    }
  }, [pwaLocation]);

  // Get battery level
  useEffect(() => {
    const getBatteryLevel = async () => {
      try {
        if ('getBattery' in navigator) {
          const battery = await (navigator as any).getBattery();
          setBatteryLevel(Math.round(battery.level * 100));

          battery.addEventListener('levelchange', () => {
            setBatteryLevel(Math.round(battery.level * 100));
          });
        }
      } catch (error) {
        console.log('Battery API not available:', error);
      }
    };

    getBatteryLevel();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600 bg-green-100';
      case 'in_progress':
        return 'text-blue-600 bg-blue-100';
      case 'pending':
        return 'text-yellow-600 bg-yellow-100';
      case 'cancelled':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-gray-600 bg-gray-100';
    }
  };

  const getNetworkQualityColor = (quality: string) => {
    switch (quality) {
      case 'excellent':
        return 'text-green-600';
      case 'good':
        return 'text-blue-600';
      case 'poor':
        return 'text-yellow-600';
      case 'offline':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getSyncStatusIcon = () => {
    if (syncStatus === 'syncing') {
      return (
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
        >
          <Signal className='w-3 h-3' />
        </motion.div>
      );
    }
    if (pendingSyncCount > 0) {
      return <AlertCircle className='w-3 h-3 text-orange-500' />;
    }
    return <CheckCircle className='w-3 h-3 text-green-500' />;
  };

  const handleQuickCapture = async () => {
    try {
      await requestPermissions(['camera']);
      const photo = await capturePhoto('EQUIPMENT');
      if (photo) {
        console.log('Photo captured successfully');
      }
    } catch (error) {
      console.error('Failed to capture photo:', error);
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

  return (
    <div className='space-y-6'>
      {/* Welcome Section */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className='mobile-card bg-gradient-to-r from-primary-500 to-primary-600 text-white'
      >
        <div className='flex items-center justify-between'>
          <div className='flex-1'>
            <h1 className='text-lg font-bold mb-1'>
              Good{' '}
              {new Date().getHours() < 12
                ? 'Morning'
                : new Date().getHours() < 18
                  ? 'Afternoon'
                  : 'Evening'}
              !
            </h1>
            <p className='text-primary-100 text-sm'>{profile?.name || 'Technician'}</p>
            <div className='flex items-center mt-2 space-x-4'>
              {currentLocation && (
                <div className='flex items-center text-primary-100 text-xs'>
                  <MapPin className='w-3 h-3 mr-1' />
                  <span>Location tracking active</span>
                </div>
              )}
              {batteryLevel && (
                <div className='flex items-center text-primary-100 text-xs'>
                  <Battery className='w-3 h-3 mr-1' />
                  <span>{batteryLevel}%</span>
                </div>
              )}
              <div className='flex items-center text-primary-100 text-xs'>
                {getSyncStatusIcon()}
                <span className='ml-1'>
                  {isOffline
                    ? 'Offline'
                    : networkQuality.charAt(0).toUpperCase() + networkQuality.slice(1)}
                  {pendingSyncCount > 0 && ` (${pendingSyncCount} pending)`}
                </span>
              </div>
            </div>
          </div>

          {stats.nextAppointment && (
            <div className='text-right'>
              <div className='text-primary-100 text-xs'>Next appointment</div>
              <div className='font-bold text-sm'>{formatTime(stats.nextAppointment)}</div>
              <div className='text-primary-100 text-xs'>{formatDate(stats.nextAppointment)}</div>
            </div>
          )}
        </div>
      </motion.div>

      {/* Stats Grid */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className='grid grid-cols-2 gap-4'
      >
        <div className='mobile-card'>
          <div className='flex items-center space-x-3'>
            <div className='w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center'>
              <ClipboardList className='w-5 h-5 text-blue-600' />
            </div>
            <div>
              <div className='text-2xl font-bold text-gray-900'>{stats.todayOrders}</div>
              <div className='text-gray-600 text-sm'>Today's Orders</div>
            </div>
          </div>
        </div>

        <div className='mobile-card'>
          <div className='flex items-center space-x-3'>
            <div className='w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center'>
              <CheckCircle className='w-5 h-5 text-green-600' />
            </div>
            <div>
              <div className='text-2xl font-bold text-gray-900'>{stats.completedOrders}</div>
              <div className='text-gray-600 text-sm'>Completed</div>
            </div>
          </div>
        </div>

        <div className='mobile-card'>
          <div className='flex items-center space-x-3'>
            <div className='w-10 h-10 bg-yellow-100 rounded-lg flex items-center justify-center'>
              <Clock className='w-5 h-5 text-yellow-600' />
            </div>
            <div>
              <div className='text-2xl font-bold text-gray-900'>{stats.pendingOrders}</div>
              <div className='text-gray-600 text-sm'>Pending</div>
            </div>
          </div>
        </div>

        <div className='mobile-card'>
          <div className='flex items-center space-x-3'>
            <div className='w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center'>
              <Package className='w-5 h-5 text-purple-600' />
            </div>
            <div>
              <div className='text-2xl font-bold text-gray-900'>{stats.inventoryItems}</div>
              <div className='text-gray-600 text-sm'>Inventory</div>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Sync Status Section */}
      {(pendingSyncCount > 0 || syncStatus === 'syncing') && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.15 }}
          className='mobile-card bg-gradient-to-r from-orange-50 to-yellow-50 border-orange-200'
        >
          <div className='flex items-center justify-between'>
            <div className='flex items-center space-x-3'>
              <div className='w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center'>
                {getSyncStatusIcon()}
              </div>
              <div>
                <h3 className='font-semibold text-gray-900'>
                  {syncStatus === 'syncing'
                    ? 'Syncing Data...'
                    : `${pendingSyncCount} Items Pending`}
                </h3>
                <p className='text-orange-600 text-sm'>
                  {syncStatus === 'syncing'
                    ? 'Uploading work orders and photos'
                    : 'Will sync when connection improves'}
                </p>
              </div>
            </div>
            {networkQuality && (
              <div className={`text-sm font-medium ${getNetworkQualityColor(networkQuality)}`}>
                {networkQuality.charAt(0).toUpperCase() + networkQuality.slice(1)}
              </div>
            )}
          </div>
        </motion.div>
      )}

      {/* Quick Actions */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.2 }}
        className='mobile-card'
      >
        <h2 className='text-lg font-semibold text-gray-900 mb-4'>Quick Actions</h2>
        <div className='grid grid-cols-2 gap-3 mb-3'>
          <button 
            onClick={() => window.location.href = '/workflow-guide'}
            className='flex flex-col items-center p-4 bg-blue-50 border border-blue-200 rounded-lg touch-feedback'
          >
            <BookOpen className='w-6 h-6 text-blue-600 mb-2' />
            <span className='text-sm font-semibold text-blue-800'>Workflow Guide</span>
            <span className='text-xs text-blue-600 mt-1'>Works offline</span>
          </button>

          <button className='flex flex-col items-center p-4 bg-gray-50 rounded-lg touch-feedback'>
            <Navigation className='w-6 h-6 text-blue-600 mb-2' />
            <span className='text-sm text-gray-700'>Navigate</span>
            <span className='text-xs text-gray-500 mt-1'>GPS ready</span>
          </button>
        </div>
        
        <div className='grid grid-cols-2 gap-3'>
          <button
            className='flex flex-col items-center p-3 bg-gray-50 rounded-lg touch-feedback'
            onClick={handleQuickCapture}
          >
            <Package className='w-6 h-6 text-green-600 mb-2' />
            <span className='text-sm text-gray-700'>Quick Photo</span>
          </button>

          <button className='flex flex-col items-center p-3 bg-gray-50 rounded-lg touch-feedback'>
            <Users className='w-6 h-6 text-purple-600 mb-2' />
            <span className='text-sm text-gray-700'>Customer</span>
          </button>
        </div>
      </motion.div>

      {/* Recent Work Orders */}
      {recentOrders.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className='mobile-card'
        >
          <div className='flex items-center justify-between mb-4'>
            <h2 className='text-lg font-semibold text-gray-900'>Recent Orders</h2>
            <button className='text-primary-600 text-sm font-medium'>View All</button>
          </div>

          <div className='space-y-3'>
            {recentOrders.slice(0, 3).map((order) => (
              <motion.div
                key={order.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className='flex items-center space-x-3 p-3 bg-gray-50 rounded-lg'
              >
                <div
                  className={`w-2 h-12 rounded-full ${
                    order.priority === 'urgent'
                      ? 'bg-red-500'
                      : order.priority === 'high'
                        ? 'bg-orange-500'
                        : order.priority === 'medium'
                          ? 'bg-yellow-500'
                          : 'bg-green-500'
                  }`}
                />

                <div className='flex-1 min-w-0'>
                  <div className='flex items-center justify-between'>
                    <h3 className='font-medium text-gray-900 text-sm truncate'>{order.title}</h3>
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(order.status)}`}
                    >
                      {order.status.replace('_', ' ')}
                    </span>
                  </div>
                  <p className='text-gray-600 text-sm truncate mt-1'>
                    {order.customer.name} • {order.location.address}
                  </p>
                  <div className='flex items-center mt-1 text-gray-500 text-xs'>
                    <Calendar className='w-3 h-3 mr-1' />
                    <span>
                      {formatDate(order.scheduledDate)} at {formatTime(order.scheduledDate)}
                    </span>
                  </div>
                </div>

                <div className='flex flex-col items-center'>
                  <MapPin className='w-4 h-4 text-gray-400 mb-1' />
                  <span className='text-xs text-gray-500'>{order.priority}</span>
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Weather/Conditions (placeholder) */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
        className='mobile-card bg-gradient-to-r from-cyan-50 to-blue-50 border-cyan-200'
      >
        <div className='flex items-center justify-between'>
          <div>
            <h3 className='font-semibold text-gray-900 mb-1'>Field Conditions</h3>
            <p className='text-gray-600 text-sm'>Optimal for outdoor work</p>
          </div>
          <div className='text-right'>
            <div className='text-2xl font-bold text-gray-900'>72°F</div>
            <div className='text-gray-600 text-sm'>Partly cloudy</div>
          </div>
        </div>

        <div className='flex items-center justify-between mt-3 pt-3 border-t border-cyan-200'>
          <div className='text-center'>
            <div className='text-sm font-medium text-gray-900'>UV Index</div>
            <div className='text-xs text-gray-600'>Moderate</div>
          </div>
          <div className='text-center'>
            <div className='text-sm font-medium text-gray-900'>Wind</div>
            <div className='text-xs text-gray-600'>8 mph</div>
          </div>
          <div className='text-center'>
            <div className='text-sm font-medium text-gray-900'>Visibility</div>
            <div className='text-xs text-gray-600'>10 mi</div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
