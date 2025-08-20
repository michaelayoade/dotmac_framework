'use client';

import { Clock, Shield, Wifi } from 'lucide-react';

import { CustomerLoginForm } from './CustomerLoginForm';

export function CustomerLogin() {
  return (
    <div className='min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100'>
      {/* Header */}
      <header className='bg-white shadow-sm'>
        <div className='container mx-auto px-4 py-4'>
          <div className='flex items-center space-x-2'>
            <div className='flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600'>
              <span className='font-bold text-sm text-white'>DM</span>
            </div>
            <h1 className='font-semibold text-gray-900 text-xl'>DotMac</h1>
          </div>
        </div>
      </header>

      <div className='container mx-auto px-4 py-16'>
        <div className='mx-auto max-w-6xl'>
          <div className='grid grid-cols-1 items-center gap-12 lg:grid-cols-2'>
            {/* Left side - Marketing content */}
            <div>
              <h1 className='mb-6 font-bold text-4xl text-gray-900'>
                Welcome to Your Customer Portal
              </h1>
              <p className='mb-8 text-gray-600 text-xl'>
                Manage your internet service, view bills, and get support all in one place.
              </p>

              <div className='space-y-6'>
                <div className='flex items-start space-x-4'>
                  <div className='rounded-lg bg-blue-100 p-3'>
                    <Wifi className='h-6 w-6 text-blue-600' />
                  </div>
                  <div>
                    <h3 className='font-semibold text-gray-900'>Service Management</h3>
                    <p className='text-gray-600'>
                      Monitor your internet usage, speed, and connection status in real-time
                    </p>
                  </div>
                </div>

                <div className='flex items-start space-x-4'>
                  <div className='rounded-lg bg-green-100 p-3'>
                    <Shield className='h-6 w-6 text-green-600' />
                  </div>
                  <div>
                    <h3 className='font-semibold text-gray-900'>Secure Billing</h3>
                    <p className='text-gray-600'>
                      View and pay your bills online with secure payment processing
                    </p>
                  </div>
                </div>

                <div className='flex items-start space-x-4'>
                  <div className='rounded-lg bg-purple-100 p-3'>
                    <Clock className='h-6 w-6 text-purple-600' />
                  </div>
                  <div>
                    <h3 className='font-semibold text-gray-900'>24/7 Support</h3>
                    <p className='text-gray-600'>
                      Get help when you need it with our round-the-clock support team
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Right side - Login form */}
            <div>
              <CustomerLoginForm />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
