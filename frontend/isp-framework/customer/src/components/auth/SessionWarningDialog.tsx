'use client';

import { AlertTriangle, Clock } from 'lucide-react';
import { useEffect, useState } from 'react';

interface SessionWarningDialogProps {
  isOpen: boolean;
  timeLeft: number; // in milliseconds
  onExtend: () => void;
  onLogout: () => void;
}

export function SessionWarningDialog({
  isOpen,
  timeLeft,
  onExtend,
  onLogout,
}: SessionWarningDialogProps) {
  const [countdown, setCountdown] = useState(Math.ceil(timeLeft / 1000));

  useEffect(() => {
    if (!isOpen) return;

    setCountdown(Math.ceil(timeLeft / 1000));

    const interval = setInterval(() => {
      setCountdown((prev) => {
        const newCount = prev - 1;
        if (newCount <= 0) {
          clearInterval(interval);
          onLogout();
          return 0;
        }
        return newCount;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isOpen, timeLeft, onLogout]);

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };

  if (!isOpen) {
    return null;
  }

  return (
    <div className='fixed inset-0 z-50 flex items-center justify-center'>
      {/* Backdrop */}
      <div
        className='absolute inset-0 bg-black bg-opacity-50'
        onClick={(e) => e.preventDefault()}
      />

      {/* Dialog */}
      <div className='relative bg-white rounded-lg shadow-xl max-w-md w-full mx-4 p-6'>
        <div className='flex items-center justify-center mb-4'>
          <div className='flex-shrink-0'>
            <AlertTriangle className='h-12 w-12 text-orange-500' />
          </div>
        </div>

        <div className='text-center'>
          <h3 className='text-lg font-semibold text-gray-900 mb-2'>Session Expiring Soon</h3>

          <p className='text-sm text-gray-600 mb-4'>
            Your session will expire due to inactivity. You will be automatically logged out for
            security reasons.
          </p>

          <div className='flex items-center justify-center mb-6 p-4 bg-orange-50 rounded-lg border border-orange-200'>
            <Clock className='h-5 w-5 text-orange-600 mr-2' />
            <span className='text-lg font-mono font-semibold text-orange-800'>
              {formatTime(countdown)}
            </span>
          </div>

          <div className='flex flex-col sm:flex-row gap-3 justify-center'>
            <button
              onClick={onExtend}
              type='button'
              className='w-full sm:w-auto inline-flex justify-center items-center px-6 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
            >
              Continue Session
            </button>

            <button
              onClick={onLogout}
              type='button'
              className='w-full sm:w-auto inline-flex justify-center items-center px-6 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500'
            >
              Logout Now
            </button>
          </div>

          <p className='mt-4 text-xs text-gray-500'>
            Click "Continue Session" to stay logged in or "Logout Now" to end your session
            immediately.
          </p>
        </div>
      </div>
    </div>
  );
}
