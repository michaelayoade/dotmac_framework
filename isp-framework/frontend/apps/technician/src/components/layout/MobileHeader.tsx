'use client';

import { Bell, Menu, Wifi, WifiOff } from 'lucide-react';
import { usePWA } from '../../hooks/usePWA';
import { useOfflineSync } from '../../hooks/useOfflineSync';

interface MobileHeaderProps {
  title?: string;
  onMenuClick?: () => void;
  showNotifications?: boolean;
}

export function MobileHeader({
  title = 'DotMac Technician',
  onMenuClick,
  showNotifications = true,
}: MobileHeaderProps) {
  const { isOffline } = usePWA();
  const { syncState } = useOfflineSync();

  const handleMenuClick = () => {
    if (onMenuClick) {
      onMenuClick();
    }

    // Haptic feedback on supported devices
    if ('vibrate' in navigator) {
      navigator.vibrate(10);
    }
  };

  const handleNotificationClick = () => {
    // Handle notification click
    if ('vibrate' in navigator) {
      navigator.vibrate(10);
    }
  };

  return (
    <header className='bg-white border-b border-gray-200 px-4 py-3'>
      <div className='flex items-center justify-between'>
        {/* Left section */}
        <div className='flex items-center space-x-3'>
          <button
            onClick={handleMenuClick}
            className='p-2 -ml-2 rounded-lg active:bg-gray-100 touch-feedback'
            aria-label='Open menu'
          >
            <Menu className='w-5 h-5 text-gray-600' />
          </button>

          <div>
            <h1 className='text-lg font-semibold text-gray-900 truncate'>{title}</h1>
            {syncState.pendingItems > 0 && (
              <p className='text-xs text-orange-600'>{syncState.pendingItems} pending sync</p>
            )}
          </div>
        </div>

        {/* Right section */}
        <div className='flex items-center space-x-2'>
          {/* Connection status */}
          <div className='flex items-center'>
            {isOffline ? (
              <div className='flex items-center text-red-600'>
                <WifiOff className='w-4 h-4 mr-1' />
                <span className='text-xs font-medium'>Offline</span>
              </div>
            ) : (
              <div className='flex items-center text-green-600'>
                <Wifi className='w-4 h-4 mr-1' />
                <span className='text-xs font-medium'>Online</span>
              </div>
            )}
          </div>

          {/* Sync status indicator */}
          {syncState.status === 'syncing' && (
            <div className='flex items-center'>
              <div className='w-3 h-3 bg-blue-500 rounded-full animate-pulse'></div>
              <span className='text-xs text-gray-600 ml-1'>Sync</span>
            </div>
          )}

          {/* Notifications */}
          {showNotifications && (
            <button
              onClick={handleNotificationClick}
              className='relative p-2 rounded-lg active:bg-gray-100 touch-feedback'
              aria-label='Notifications'
            >
              <Bell className='w-5 h-5 text-gray-600' />
              {/* Notification badge */}
              <div className='absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full flex items-center justify-center'>
                <span className='text-white text-xs font-bold'>2</span>
              </div>
            </button>
          )}
        </div>
      </div>

      {/* Sync progress bar */}
      {syncState.status === 'syncing' && (
        <div className='mt-2'>
          <div className='w-full bg-gray-200 rounded-full h-1.5'>
            <div
              className='bg-primary-500 h-1.5 rounded-full transition-all duration-300'
              style={{ width: `${syncState.progress}%` }}
            />
          </div>
          <div className='flex justify-between text-xs text-gray-600 mt-1'>
            <span>Syncing...</span>
            <span>
              {syncState.currentItem}/{syncState.totalItems}
            </span>
          </div>
        </div>
      )}
    </header>
  );
}
