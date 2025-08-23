export default function Loading() {
  return (
    <div className='flex items-center justify-center min-h-[60vh]'>
      <div className='relative'>
        <div className='animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600'></div>
        <div className='mt-4 text-sm text-gray-500'>Loading...</div>
      </div>
    </div>
  );
}
