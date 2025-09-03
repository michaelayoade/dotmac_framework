'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Bell, Menu, ChevronDown, LogOut } from 'lucide-react';
import { useManagementAuth } from '@/components/auth/ManagementAuthProvider';

interface TopNavigationProps {
  onMenuClick: () => void;
  pageTitle: string;
}

export function TopNavigation({ onMenuClick, pageTitle }: TopNavigationProps) {
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const { user, logout } = useManagementAuth();

  return (
    <div className='sticky top-0 z-40 flex h-16 shrink-0 items-center gap-x-4 border-b border-gray-200 bg-white px-4 shadow-sm sm:gap-x-6 sm:px-6 lg:px-8'>
      <button type='button' className='-m-2.5 p-2.5 text-gray-700 lg:hidden' onClick={onMenuClick}>
        <Menu className='h-6 w-6' />
      </button>

      <div className='flex flex-1 gap-x-4 self-stretch lg:gap-x-6'>
        <div className='flex flex-1 items-center'>
          <h1 className='text-xl font-semibold text-gray-900'>{pageTitle}</h1>
        </div>

        <div className='flex items-center gap-x-4 lg:gap-x-6'>
          {/* Notifications */}
          <button type='button' className='relative -m-2.5 p-2.5 text-gray-400 hover:text-gray-500'>
            <Bell className='h-6 w-6' />
            <span className='absolute -top-1 -right-1 h-4 w-4 rounded-full bg-red-500 text-xs text-white flex items-center justify-center'>
              5
            </span>
          </button>

          {/* User menu */}
          <div className='relative'>
            <button
              type='button'
              className='flex items-center gap-x-4 px-6 py-3 text-sm font-semibold text-gray-900 hover:bg-gray-50'
              onClick={() => setUserMenuOpen(!userMenuOpen)}
            >
              <div className='h-8 w-8 rounded-full bg-management-500 flex items-center justify-center text-white font-medium'>
                {user?.name?.charAt(0)?.toUpperCase() || 'U'}
              </div>
              <div className='hidden lg:flex lg:items-center'>
                <span>{user?.name}</span>
                <ChevronDown className='ml-2 h-5 w-5 text-gray-400' />
              </div>
            </button>

            {userMenuOpen && (
              <div className='absolute right-0 z-10 mt-2.5 w-56 origin-top-right rounded-md bg-white py-2 shadow-lg ring-1 ring-gray-900/5'>
                <div className='px-4 py-2 border-b border-gray-200'>
                  <p className='text-sm font-medium text-gray-900'>{user?.name}</p>
                  <p className='text-sm text-gray-500'>{user?.email}</p>
                  <p className='text-xs text-gray-400 mt-1 capitalize'>
                    {user?.role.replace('_', ' ').toLowerCase()}
                  </p>
                </div>
                <div className='px-4 py-2 border-b border-gray-200'>
                  <p className='text-xs text-gray-500 mb-1'>Departments</p>
                  {user?.departments.map((dept) => (
                    <p key={dept} className='text-xs text-gray-700'>
                      {dept}
                    </p>
                  ))}
                </div>
                <Link
                  href='/profile'
                  className='block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50'
                >
                  Profile Settings
                </Link>
                <button
                  onClick={logout}
                  className='w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-50'
                >
                  <LogOut className='inline h-4 w-4 mr-2' />
                  Sign out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
