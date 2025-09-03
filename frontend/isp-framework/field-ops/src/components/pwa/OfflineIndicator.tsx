'use client';

import { Wifi, WifiOff, RefreshCw, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { usePWA } from '../../hooks/usePWA';
import { useOfflineSync } from '../../hooks/useOfflineSync';

export function OfflineIndicator() {
  const { isOffline } = usePWA();
  const { syncState, forceSync } = useOfflineSync();

  const handleSync = () => {
    if ('vibrate' in navigator) {
      navigator.vibrate(20);
    }
    forceSync();
  };

  return (
    <AnimatePresence>
      {(isOffline || syncState.pendingItems > 0) && (
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.9 }}
          transition={{ type: 'spring', damping: 25, stiffness: 500 }}
          className='mx-4 mb-4'
        >
          <div
            className={`rounded-xl p-4 shadow-sm border ${
              isOffline ? 'bg-red-50 border-red-200' : 'bg-yellow-50 border-yellow-200'
            }`}
          >
            <div className='flex items-center justify-between'>
              <div className='flex items-center space-x-3'>
                <div
                  className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                    isOffline ? 'bg-red-100 text-red-600' : 'bg-yellow-100 text-yellow-600'
                  }`}
                >
                  {isOffline ? (
                    <WifiOff className='w-5 h-5' />
                  ) : syncState.pendingItems > 0 ? (
                    <AlertCircle className='w-5 h-5' />
                  ) : (
                    <Wifi className='w-5 h-5' />
                  )}
                </div>

                <div className='flex-1'>
                  <h3
                    className={`font-semibold text-sm ${
                      isOffline ? 'text-red-900' : 'text-yellow-900'
                    }`}
                  >
                    {isOffline ? 'Working Offline' : 'Sync Pending'}
                  </h3>
                  <p className={`text-xs ${isOffline ? 'text-red-700' : 'text-yellow-700'}`}>
                    {isOffline
                      ? 'Changes will sync when online'
                      : `${syncState.pendingItems} items waiting to sync`}
                  </p>
                </div>
              </div>

              {/* Sync button - only show when online and has pending items */}
              {!isOffline && syncState.pendingItems > 0 && (
                <button
                  onClick={handleSync}
                  disabled={syncState.status === 'syncing'}
                  className='flex items-center space-x-1 bg-yellow-600 text-white px-3 py-1.5 rounded-lg font-medium text-sm touch-feedback disabled:opacity-50 disabled:cursor-not-allowed'
                >
                  <RefreshCw
                    className={`w-4 h-4 ${syncState.status === 'syncing' ? 'animate-spin' : ''}`}
                  />
                  <span>Sync</span>
                </button>
              )}
            </div>

            {/* Sync progress */}
            {syncState.status === 'syncing' && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className='mt-3 pt-3 border-t border-yellow-200'
              >
                <div className='flex justify-between items-center mb-2'>
                  <span className='text-xs text-yellow-700'>
                    Syncing {syncState.currentItem} of {syncState.totalItems}
                  </span>
                  <span className='text-xs text-yellow-700 font-medium'>{syncState.progress}%</span>
                </div>
                <div className='w-full bg-yellow-200 rounded-full h-1.5'>
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${syncState.progress}%` }}
                    transition={{ duration: 0.3 }}
                    className='bg-yellow-600 h-1.5 rounded-full'
                  />
                </div>
              </motion.div>
            )}

            {/* Error state */}
            {syncState.status === 'error' && syncState.error && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                className='mt-3 pt-3 border-t border-red-200'
              >
                <div className='flex items-center space-x-2'>
                  <AlertCircle className='w-4 h-4 text-red-600 flex-shrink-0' />
                  <p className='text-xs text-red-700'>{syncState.error}</p>
                </div>
              </motion.div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
