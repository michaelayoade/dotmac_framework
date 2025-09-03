import React, { useState, useEffect } from 'react';
import { WifiOff, Wifi } from 'lucide-react';
import { clsx } from 'clsx';

interface OfflineDetectorProps {
  showStatus?: boolean;
  showToast?: boolean;
  position?: 'top' | 'bottom';
  onOnline?: () => void;
  onOffline?: () => void;
  className?: string;
}

export const OfflineDetector: React.FC<OfflineDetectorProps> = ({
  showStatus = true,
  showToast = true,
  position = 'top',
  onOnline,
  onOffline,
  className
}) => {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );
  const [showNotification, setShowNotification] = useState(false);

  useEffect(() => {
    const handleOnline = () => {
      setIsOnline(true);
      onOnline?.();
      if (showToast) {
        setShowNotification(true);
        setTimeout(() => setShowNotification(false), 3000);
      }
    };

    const handleOffline = () => {
      setIsOnline(false);
      onOffline?.();
      if (showToast) {
        setShowNotification(true);
      }
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, [onOnline, onOffline, showToast]);

  if (!showStatus && !showToast) return null;

  return (
    <>
      {/* Status Indicator */}
      {showStatus && (
        <div 
          className={clsx(
            'fixed z-50 flex items-center gap-2 px-3 py-1 text-sm rounded-full',
            position === 'top' ? 'top-4 right-4' : 'bottom-4 right-4',
            isOnline 
              ? 'bg-green-100 text-green-800 border border-green-200' 
              : 'bg-red-100 text-red-800 border border-red-200',
            className
          )}
        >
          {isOnline ? (
            <Wifi className="w-4 h-4" />
          ) : (
            <WifiOff className="w-4 h-4" />
          )}
          <span>{isOnline ? 'Online' : 'Offline'}</span>
        </div>
      )}

      {/* Toast Notification */}
      {showToast && showNotification && (
        <div
          className={clsx(
            'fixed z-50 flex items-center gap-3 px-4 py-3 bg-white border rounded-lg shadow-lg transition-all duration-300',
            position === 'top' ? 'top-4 left-1/2 -translate-x-1/2' : 'bottom-4 left-1/2 -translate-x-1/2',
            isOnline ? 'border-green-200' : 'border-red-200'
          )}
          role="alert"
        >
          {isOnline ? (
            <Wifi className="w-5 h-5 text-green-600" />
          ) : (
            <WifiOff className="w-5 h-5 text-red-600" />
          )}
          <div>
            <p className={clsx('font-medium', isOnline ? 'text-green-900' : 'text-red-900')}>
              {isOnline ? 'Back Online' : 'Connection Lost'}
            </p>
            <p className="text-sm text-gray-600">
              {isOnline 
                ? 'Your internet connection has been restored'
                : 'Please check your internet connection'
              }
            </p>
          </div>
          {isOnline && (
            <button
              onClick={() => setShowNotification(false)}
              className="ml-2 text-green-600 hover:text-green-800"
              aria-label="Dismiss"
            >
              ×
            </button>
          )}
        </div>
      )}
    </>
  );
};

// Hook for using offline status
export const useOnlineStatus = () => {
  const [isOnline, setIsOnline] = useState(
    typeof navigator !== 'undefined' ? navigator.onLine : true
  );

  useEffect(() => {
    const handleOnline = () => setIsOnline(true);
    const handleOffline = () => setIsOnline(false);

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);

    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
    };
  }, []);

  return isOnline;
};