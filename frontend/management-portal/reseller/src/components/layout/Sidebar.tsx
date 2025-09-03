'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ChevronDown } from 'lucide-react';
import { useManagementAuth } from '@/components/auth/ManagementAuthProvider';
import { navigationConfig, type NavigationItem } from './NavigationConfig';

interface SidebarProps {
  filteredNavigation: NavigationItem[];
}

export function Sidebar({ filteredNavigation }: SidebarProps) {
  const [expandedMenus, setExpandedMenus] = useState<string[]>([]);
  const pathname = usePathname();
  const { user } = useManagementAuth();

  const toggleMenu = (menuName: string) => {
    setExpandedMenus((prev) =>
      prev.includes(menuName) ? prev.filter((name) => name !== menuName) : [...prev, menuName]
    );
  };

  return (
    <div className='flex grow flex-col gap-y-5 overflow-y-auto bg-white border-r border-gray-200'>
      {/* Logo */}
      <div className='flex h-16 shrink-0 items-center px-6 border-b border-gray-200'>
        <div className='flex items-center gap-x-3'>
          <div className='h-8 w-8 rounded bg-gradient-to-br from-management-600 to-reseller-600 flex items-center justify-center text-white font-bold text-sm'>
            R
          </div>
          <div className='min-w-0 flex-1'>
            <p className='text-sm font-semibold text-gray-900 truncate'>Reseller Management</p>
            <p className='text-xs text-gray-500'>Channel Operations</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className='flex flex-1 flex-col px-3'>
        <ul role='list' className='space-y-1'>
          {filteredNavigation.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.children && item.children.some((child) => pathname === child.href));
            const isExpanded = expandedMenus.includes(item.name);

            return (
              <li key={item.name}>
                {item.children ? (
                  // Parent menu with children
                  <div>
                    <button
                      onClick={() => toggleMenu(item.name)}
                      className={`management-nav-item w-full ${isActive ? 'active' : ''}`}
                    >
                      <item.icon className='mr-3 h-5 w-5 flex-shrink-0' />
                      {item.name}
                      {item.badge && (
                        <span className='ml-auto inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800'>
                          {item.badge}
                        </span>
                      )}
                      <ChevronDown
                        className={`ml-2 h-4 w-4 transition-transform ${
                          isExpanded ? 'rotate-180' : ''
                        }`}
                      />
                    </button>

                    {isExpanded && (
                      <ul className='mt-1 space-y-1 pl-6'>
                        {item.children.map((child) => (
                          <li key={child.href}>
                            <Link
                              href={child.href}
                              className={`management-nav-item ${pathname === child.href ? 'active' : ''}`}
                            >
                              <child.icon className='mr-3 h-4 w-4 flex-shrink-0' />
                              {child.name}
                              {child.badge && (
                                <span className='ml-auto inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800'>
                                  {child.badge}
                                </span>
                              )}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ) : (
                  // Simple menu item
                  <Link
                    href={item.href}
                    className={`management-nav-item ${isActive ? 'active' : ''}`}
                  >
                    <item.icon className='mr-3 h-5 w-5 flex-shrink-0' />
                    {item.name}
                    {item.badge && (
                      <span className='ml-auto inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800'>
                        {item.badge}
                      </span>
                    )}
                  </Link>
                )}
              </li>
            );
          })}
        </ul>

        {/* User info at bottom */}
        <div className='mt-auto p-4 border-t border-gray-200'>
          <div className='flex items-center gap-x-3'>
            <div className='h-8 w-8 rounded-full bg-management-500 flex items-center justify-center text-white font-medium text-sm'>
              {user?.name?.charAt(0)?.toUpperCase() || 'U'}
            </div>
            <div className='min-w-0 flex-1'>
              <p className='text-xs font-medium text-gray-900 truncate'>{user?.name}</p>
              <p className='text-xs text-gray-500 capitalize'>
                {user?.role.replace('_', ' ').toLowerCase()}
              </p>
            </div>
          </div>
        </div>
      </nav>
    </div>
  );
}
