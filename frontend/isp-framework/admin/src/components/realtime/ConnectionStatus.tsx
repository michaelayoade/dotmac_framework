/**
 * Connection Status Component - Real-time connection indicator
 * Shows WebSocket connection status and provides reconnection controls
 */

'use client';

import React from 'react';
import { WifiIcon, WifiOffIcon, RefreshCwIcon, AlertCircleIcon } from 'lucide-react';
import { useRealtimeSync, ConnectionStatus as ConnectionStatusType } from '../../lib/realtime-sync';

interface ConnectionStatusProps {
  showDetails?: boolean;
  className?: string;
}

export function ConnectionStatus({ showDetails = false, className = '' }: ConnectionStatusProps) {
  const { status, reconnect } = useRealtimeSync();

  const getStatusColor = (status: ConnectionStatusType): string => {
    if (status.connected) return 'text-green-600 bg-green-50';
    if (status.reconnecting) return 'text-yellow-600 bg-yellow-50';
    return 'text-red-600 bg-red-50';
  };

  const getStatusIcon = (status: ConnectionStatusType) => {
    if (status.connected) return WifiIcon;
    if (status.reconnecting) return RefreshCwIcon;
    return WifiOffIcon;
  };

  const getStatusText = (status: ConnectionStatusType): string => {
    if (status.connected) return 'Connected';
    if (status.reconnecting) return 'Reconnecting...';
    return 'Disconnected';
  };

  const StatusIcon = getStatusIcon(status);

  if (!showDetails) {
    // Compact indicator
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <div
          className={`flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(status)}`}
        >
          <StatusIcon className={`w-3 h-3 ${status.reconnecting ? 'animate-spin' : ''}`} />
          <span>{getStatusText(status)}</span>
        </div>
      </div>
    );
  }

  // Detailed status panel
  return (
    <div className={`bg-white rounded-lg border border-gray-200 p-4 ${className}`}>
      <div className='flex items-center justify-between mb-3'>
        <div className='flex items-center space-x-2'>
          <StatusIcon
            className={`w-5 h-5 ${getStatusColor(status)} ${status.reconnecting ? 'animate-spin' : ''}`}
          />
          <h3 className='text-sm font-medium text-gray-900'>Real-time Connection</h3>
        </div>

        {!status.connected && !status.reconnecting && (
          <button
            onClick={reconnect}
            className='text-sm text-blue-600 hover:text-blue-800 font-medium'
          >
            Reconnect
          </button>
        )}
      </div>

      <div className='space-y-2'>
        <div className='flex justify-between text-sm'>
          <span className='text-gray-600'>Status:</span>
          <span
            className={`font-medium ${
              status.connected
                ? 'text-green-600'
                : status.reconnecting
                  ? 'text-yellow-600'
                  : 'text-red-600'
            }`}
          >
            {getStatusText(status)}
          </span>
        </div>

        {status.lastConnected && (
          <div className='flex justify-between text-sm'>
            <span className='text-gray-600'>Last Connected:</span>
            <span className='text-gray-900'>{status.lastConnected.toLocaleTimeString()}</span>
          </div>
        )}

        {status.connectionAttempts > 0 && (
          <div className='flex justify-between text-sm'>
            <span className='text-gray-600'>Attempts:</span>
            <span className='text-gray-900'>{status.connectionAttempts}</span>
          </div>
        )}

        {status.lastError && (
          <div className='flex items-start space-x-2 text-sm'>
            <AlertCircleIcon className='w-4 h-4 text-red-500 mt-0.5 flex-shrink-0' />
            <div>
              <span className='text-gray-600'>Error:</span>
              <p className='text-red-600 text-xs mt-1'>{status.lastError}</p>
            </div>
          </div>
        )}
      </div>

      {status.connected && (
        <div className='mt-3 pt-3 border-t border-gray-100'>
          <div className='flex items-center space-x-2 text-xs text-green-600'>
            <div className='w-2 h-2 bg-green-500 rounded-full animate-pulse'></div>
            <span>Live updates active</span>
          </div>
        </div>
      )}
    </div>
  );
}

// Real-time notification listener component
export function RealtimeNotifications() {
  React.useEffect(() => {
    const handleNotification = (event: CustomEvent) => {
      const { message, type } = event.detail;

      // You can integrate this with your notification system
      console.log(`[${type.toUpperCase()}] ${message}`);

      // Example: Show toast notification
      // toast[type](message);
    };

    window.addEventListener('billing-notification', handleNotification as EventListener);

    return () => {
      window.removeEventListener('billing-notification', handleNotification as EventListener);
    };
  }, []);

  return null; // This component doesn't render anything
}
