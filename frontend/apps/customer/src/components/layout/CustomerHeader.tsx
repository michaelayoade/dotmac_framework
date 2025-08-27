'use client';

import React, { useState } from 'react';
import { usePortalAuth } from '@dotmac/headless';
import { OptimizedImage } from '@dotmac/primitives';
import { Avatar, Button } from '@dotmac/styled-components/customer';
import { Bell, ChevronDown, HelpCircle, LogOut, Settings, User } from 'lucide-react';

export function CustomerHeader() {
  const { user, _currentPortal, _getPortalBranding } = usePortalAuth();
  const [showUserMenu, setShowUserMenu] = useState(false);

  const branding = _getPortalBranding();

  const handleLogout = () => {
    // Implement logout logic
    // Debug: 'Logging out...'
  };

  const handleUserMenuToggle = () => {
    setShowUserMenu(!showUserMenu);
  };

  return (
    <header className='customer-header flex h-16 items-center justify-between px-6'>
      {/* Logo and Company Name */}
      <div className='flex items-center space-x-4'>
        <div className='flex items-center space-x-3'>
          {branding?.logo ? (
            <OptimizedImage src={branding.logo} alt={branding.companyName} className='h-8' />
          ) : (
            <div
              className='flex h-8 w-8 items-center justify-center rounded-lg'
              style={{ backgroundColor: branding?.primaryColor }}
            >
              <span className='font-bold text-sm text-white'>
                {branding?.companyName?.charAt(0) || 'D'}
              </span>
            </div>
          )}
          <h1 className='font-semibold text-gray-900 text-xl'>
            {branding?.companyName || 'Customer Portal'}
          </h1>
        </div>
      </div>

      {/* Header Actions */}
      <div className='flex items-center space-x-4'>
        {/* Help/Support */}
        <Button variant='ghost' size='sm' className='text-gray-600 hover:text-gray-900'>
          <HelpCircle className='h-5 w-5' />
          <span className='ml-2 hidden sm:inline'>Help</span>
        </Button>

        {/* Notifications */}
        <Button variant='ghost' size='sm' className='relative text-gray-600 hover:text-gray-900'>
          <Bell className='h-5 w-5' />
          {/* Notification badge */}
          <span className='-top-1 -right-1 absolute flex h-5 w-5 items-center justify-center rounded-full bg-red-500 text-white text-xs'>
            2
          </span>
        </Button>

        {/* User Menu */}
        <div className='relative'>
          <button
            type='button'
            onClick={handleUserMenuToggle}
            onKeyDown={(e) => e.key === 'Enter' && handleUserMenuToggle}
            className='flex items-center space-x-2 rounded-lg p-2 transition-colors hover:bg-gray-100'
          >
            <Avatar
              src={user?.avatar}
              alt={user?.name || 'User'}
              fallback={user?.name?.charAt(0) || 'U'}
              size='sm'
            />
            <div className='hidden text-left sm:block'>
              <div className='font-medium text-gray-900 text-sm'>{user?.name || 'Customer'}</div>
              <div className='text-gray-500 text-xs'>{user?.email || 'customer@example.com'}</div>
            </div>
            <ChevronDown className='h-4 w-4 text-gray-400' />
          </button>

          {showUserMenu ? (
            <div className='absolute right-0 z-50 mt-2 w-48 rounded-md border border-gray-200 bg-white py-1 shadow-lg'>
              <button
                type='button'
                onClick={() => {
                  // Navigate to profile
                }}
                className='flex w-full items-center px-4 py-2 text-left text-gray-700 text-sm hover:bg-gray-100'
              >
                <User className='mr-2 h-4 w-4' />
                My Profile
              </button>
              <button
                type='button'
                onClick={() => {
                  // Navigate to settings
                }}
                className='flex w-full items-center px-4 py-2 text-left text-gray-700 text-sm hover:bg-gray-100'
              >
                <Settings className='mr-2 h-4 w-4' />
                Account Settings
              </button>
              <hr className='my-1' />
              <button
                type='button'
                onClick={handleLogout}
                onKeyDown={(e) => e.key === 'Enter' && handleLogout}
                className='flex w-full items-center px-4 py-2 text-gray-700 text-sm hover:bg-gray-100'
              >
                <LogOut className='mr-2 h-4 w-4' />
                Sign Out
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
