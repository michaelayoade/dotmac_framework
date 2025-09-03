'use client';

import { useEffect } from 'react';

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Log the error to an error reporting service
    console.error('Route error:', error);
  }, [error]);

  return (
    <div className='flex flex-col items-center justify-center min-h-[60vh] px-4'>
      <div className='text-center'>
        <h2 className='text-2xl font-bold text-gray-900 mb-2'>Something went wrong!</h2>
        <p className='text-gray-600 mb-6'>
          {error.message || 'An unexpected error occurred while loading this page.'}
        </p>
        <div className='flex gap-4 justify-center'>
          <button
            onClick={() => reset()}
            className='px-4 py-2 bg-primary text-white rounded-md hover:bg-primary-dark transition-colors'
          >
            Try again
          </button>
          <button
            onClick={() => (window.location.href = '/')}
            className='px-4 py-2 bg-gray-200 text-gray-800 rounded-md hover:bg-gray-300 transition-colors'
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}
