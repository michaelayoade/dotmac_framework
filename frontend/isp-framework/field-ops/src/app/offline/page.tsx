'use client';

import { WifiOff, RefreshCw, Home, Database } from 'lucide-react';
import Link from 'next/link';
import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { OfflineStorage } from '../../lib/offline-db';

export default function OfflinePage() {
  const [isOnline, setIsOnline] = useState(false);
  const [storageStats, setStorageStats] = useState({
    total: 0,
    workOrders: 0,
    customers: 0,
    inventory: 0,
  });

  useEffect(() => {
    // Check online status
    setIsOnline(navigator.onLine);

    // Listen for online/offline events
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    // Load storage stats
    OfflineStorage.getStorageSize().then(setStorageStats);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  const handleRefresh = () => {
    if (isOnline) {
      window.location.reload();
    } else {
      // Haptic feedback
      if ('vibrate' in navigator) {
        navigator.vibrate([50, 100, 50]);
      }
    }
  };

  return (
    <div className='min-h-screen bg-gray-50 flex items-center justify-center p-4'>
      <div className='max-w-md w-full'>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className='text-center'
        >
          {/* Offline Icon */}
          <div className='w-20 h-20 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-6'>
            <WifiOff className='w-10 h-10 text-gray-500' />
          </div>

          {/* Main Message */}
          <h1 className='text-2xl font-bold text-gray-900 mb-2'>You're Offline</h1>
          <p className='text-gray-600 mb-8'>
            {isOnline
              ? 'Connection restored! You can now access online features.'
              : "No internet connection. You can still use offline features and your data will sync when you're back online."}
          </p>

          {/* Status Indicator */}
          <motion.div
            animate={{ scale: isOnline ? 1 : 0.95 }}
            transition={{ repeat: isOnline ? 0 : Infinity, repeatType: 'reverse', duration: 2 }}
            className={`inline-flex items-center px-4 py-2 rounded-full text-sm font-medium mb-8 ${
              isOnline ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}
          >
            <div
              className={`w-2 h-2 rounded-full mr-2 ${isOnline ? 'bg-green-500' : 'bg-red-500'}`}
            />
            {isOnline ? 'Back Online' : 'Offline Mode'}
          </motion.div>

          {/* Offline Storage Info */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className='bg-white rounded-lg p-6 shadow-sm border border-gray-200 mb-8'
          >
            <div className='flex items-center mb-4'>
              <Database className='w-5 h-5 text-blue-600 mr-2' />
              <h2 className='text-lg font-semibold text-gray-900'>Offline Data Available</h2>
            </div>

            <div className='grid grid-cols-2 gap-4'>
              <div className='text-center'>
                <div className='text-2xl font-bold text-blue-600'>{storageStats.workOrders}</div>
                <div className='text-sm text-gray-600'>Work Orders</div>
              </div>
              <div className='text-center'>
                <div className='text-2xl font-bold text-green-600'>{storageStats.customers}</div>
                <div className='text-sm text-gray-600'>Customers</div>
              </div>
              <div className='text-center'>
                <div className='text-2xl font-bold text-purple-600'>{storageStats.inventory}</div>
                <div className='text-sm text-gray-600'>Inventory Items</div>
              </div>
              <div className='text-center'>
                <div className='text-2xl font-bold text-gray-900'>{storageStats.total}</div>
                <div className='text-sm text-gray-600'>Total Items</div>
              </div>
            </div>
          </motion.div>

          {/* Action Buttons */}
          <div className='space-y-3'>
            <button
              onClick={handleRefresh}
              disabled={!isOnline}
              className={`w-full flex items-center justify-center space-x-2 py-3 px-6 rounded-lg font-medium transition-colors ${
                isOnline
                  ? 'bg-primary-500 text-white hover:bg-primary-600'
                  : 'bg-gray-200 text-gray-500 cursor-not-allowed'
              }`}
            >
              <RefreshCw className={`w-5 h-5 ${!isOnline ? 'animate-pulse' : ''}`} />
              <span>{isOnline ? 'Refresh Page' : 'Waiting for Connection...'}</span>
            </button>

            <Link
              href='/'
              className='w-full flex items-center justify-center space-x-2 py-3 px-6 bg-white border border-gray-300 text-gray-700 rounded-lg font-medium hover:bg-gray-50 transition-colors'
            >
              <Home className='w-5 h-5' />
              <span>Go to Dashboard</span>
            </Link>
          </div>

          {/* Feature List */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.5 }}
            className='mt-8 text-left'
          >
            <h3 className='text-sm font-semibold text-gray-900 mb-3'>Available Offline:</h3>
            <ul className='text-sm text-gray-600 space-y-1'>
              <li>• View work orders and customer information</li>
              <li>• Update work order status and notes</li>
              <li>• Take photos and capture signatures</li>
              <li>• Manage inventory items</li>
              <li>• Fill out service forms</li>
            </ul>

            <p className='text-xs text-gray-500 mt-4'>
              All changes will be automatically synced when you're back online.
            </p>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
}
