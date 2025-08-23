'use client';

import { useAuth, useTenantStore } from '@dotmac/headless';
import { AdminButton as Button } from '@dotmac/styled-components/admin';

// Avatar is not currently available - using fallback
const Avatar = ({ initials }: { initials: string }) => (
  <div className='flex h-10 w-10 items-center justify-center rounded-full bg-gray-300 font-medium text-sm'>
    {initials}
  </div>
);

import { Bell, ChevronDown, LogOut, Settings, User } from 'lucide-react';
import { useState } from 'react';

export function AdminHeader() {
  const { user, logout } = useAuth();
  const { currentTenant } = useTenantStore();
  const [showUserMenu, setShowUserMenu] = useState(false);

  return (
    <header className='admin-header flex h-16 items-center justify-between px-6'>
      {/* Logo and Title */}
      <div className='flex items-center space-x-4'>
        <div className='flex items-center space-x-2'>
          <div className='flex h-8 w-8 items-center justify-center rounded-lg bg-primary'>
            <span className='font-bold text-sm text-white'>DM</span>
          </div>
          <h1 className='font-semibold text-gray-900 text-xl'>DotMac Admin</h1>
        </div>

        {currentTenant?.tenant ? (
          <div className='text-gray-500 text-sm'>{currentTenant.tenant.name}</div>
        ) : null}
      </div>

      {/* Header Actions */}
      <div className='flex items-center space-x-4'>
        {/* Notifications */}
        <Button variant='ghost' size='sm'>
          <Bell className='h-5 w-5' />
        </Button>

        {/* Settings */}
        <Button variant='ghost' size='sm'>
          <Settings className='h-5 w-5' />
        </Button>

        {/* User Menu */}
        <div className='relative'>
          <button
            type='button'
            onClick={() => setShowUserMenu(!showUserMenu)}
            className='flex items-center space-x-2 rounded-lg p-2 transition-colors hover:bg-gray-100'
          >
            <Avatar
              src={user?.avatar}
              alt={user?.name || 'User'}
              fallback={user?.name?.charAt(0) || 'U'}
              size='sm'
            />
            <div className='text-left'>
              <div className='font-medium text-gray-900 text-sm'>
                {user?.name || 'Unknown User'}
              </div>
              <div className='text-gray-500 text-xs'>{user?.role || 'Admin'}</div>
            </div>
            <ChevronDown className='h-4 w-4 text-gray-400' />
          </button>

          {showUserMenu ? (
            <div className='absolute right-0 z-50 mt-2 w-48 rounded-md border border-gray-200 bg-white py-1 shadow-lg'>
              <button
                type='button'
                className='flex w-full items-center px-4 py-2 text-left text-gray-700 text-sm hover:bg-gray-100'
              >
                <User className='mr-2 h-4 w-4' />
                Profile
              </button>
              <button
                type='button'
                className='flex w-full items-center px-4 py-2 text-left text-gray-700 text-sm hover:bg-gray-100'
              >
                <Settings className='mr-2 h-4 w-4' />
                Settings
              </button>
              <hr className='my-1' />
              <button
                type='button'
                onClick={logout}
                onKeyDown={(e) => e.key === 'Enter' && logout}
                className='flex w-full items-center px-4 py-2 text-gray-700 text-sm hover:bg-gray-100'
              >
                <LogOut className='mr-2 h-4 w-4' />
                Sign out
              </button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
}
