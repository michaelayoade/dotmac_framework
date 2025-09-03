/**
 * Health Check Page - Simple static page for testing startup
 */

export default function HealthPage() {
  return (
    <div className='flex items-center justify-center h-screen'>
      <div className='text-center'>
        <h1 className='text-2xl font-bold text-green-600 mb-4'>✅ Admin Portal Health Check</h1>
        <p className='text-gray-600'>The admin portal is running successfully.</p>
        <div className='mt-4 text-sm text-gray-500'>
          <p>Build Status: OK</p>
          <p>Timestamp: {new Date().toISOString()}</p>
        </div>
      </div>
    </div>
  );
}
