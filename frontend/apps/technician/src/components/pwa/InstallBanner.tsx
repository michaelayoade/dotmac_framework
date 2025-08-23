'use client';

import { X, Download } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useInstallBanner } from '../../hooks/usePWA';

export function InstallBanner() {
  const { showBanner, dismissBanner, installPWA } = useInstallBanner();

  if (!showBanner) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: -100 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -100 }}
        transition={{ type: 'spring', damping: 25, stiffness: 500 }}
        className='mx-4 mb-4'
      >
        <div className='bg-primary-500 text-white rounded-xl p-4 shadow-lg'>
          <div className='flex items-center justify-between'>
            <div className='flex items-center space-x-3'>
              <div className='w-10 h-10 bg-white bg-opacity-20 rounded-lg flex items-center justify-center'>
                <Download className='w-5 h-5 text-white' />
              </div>
              <div className='flex-1'>
                <h3 className='font-semibold text-sm'>Install App</h3>
                <p className='text-xs text-primary-100'>Add to home screen for better experience</p>
              </div>
            </div>
            <button
              onClick={dismissBanner}
              className='p-1 rounded-full hover:bg-white hover:bg-opacity-20 transition-colors'
              aria-label='Dismiss install banner'
            >
              <X className='w-4 h-4 text-white' />
            </button>
          </div>

          <div className='flex space-x-2 mt-3'>
            <button
              onClick={installPWA}
              className='flex-1 bg-white text-primary-600 py-2 px-4 rounded-lg font-medium text-sm touch-feedback'
            >
              Install
            </button>
            <button
              onClick={dismissBanner}
              className='px-4 py-2 rounded-lg font-medium text-sm text-primary-100 hover:text-white transition-colors'
            >
              Later
            </button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
