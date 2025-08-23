import { LoginForm } from '../../components/auth/LoginForm';

export default function LoginPage() {
  return (
    <div className='min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex flex-col justify-center py-12 sm:px-6 lg:px-8'>
      <div className='sm:mx-auto sm:w-full sm:max-w-md'>
        <div className='flex justify-center'>
          <div className='flex items-center space-x-2'>
            <div className='h-8 w-8 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-lg flex items-center justify-center'>
              <span className='text-white font-bold text-lg'>D</span>
            </div>
            <span className='text-2xl font-bold text-gray-900'>DotMac</span>
          </div>
        </div>
        <h1 className='mt-6 text-center text-3xl font-bold tracking-tight text-gray-900'>
          Admin Portal
        </h1>
        <h2 className='mt-2 text-center text-lg text-gray-600'>
          Sign in to your administrative account
        </h2>
      </div>

      <div className='mt-8 sm:mx-auto sm:w-full sm:max-w-md'>
        <div className='bg-white py-8 px-4 shadow-lg sm:rounded-lg sm:px-10 border border-gray-200'>
          <LoginForm />
        </div>

        <div className='mt-6'>
          <div className='relative'>
            <div className='absolute inset-0 flex items-center'>
              <div className='w-full border-t border-gray-300' />
            </div>
            <div className='relative flex justify-center text-sm'>
              <span className='bg-gradient-to-br from-blue-50 to-indigo-100 px-2 text-gray-500'>
                Secure ISP Management Platform
              </span>
            </div>
          </div>
        </div>

        <div className='mt-6 text-center'>
          <p className='text-xs text-gray-500'>
            © 2024 DotMac ISP Framework. All rights reserved.
          </p>
          <div className='mt-2 flex justify-center space-x-4 text-xs text-gray-400'>
            <a href='#' className='hover:text-gray-600'>
              Privacy Policy
            </a>
            <span>•</span>
            <a href='#' className='hover:text-gray-600'>
              Terms of Service
            </a>
            <span>•</span>
            <a href='#' className='hover:text-gray-600'>
              Support
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
