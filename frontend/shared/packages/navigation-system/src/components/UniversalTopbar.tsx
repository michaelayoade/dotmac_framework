import { ChevronDown, LogOut, Menu, Settings, User } from 'lucide-react';
import { forwardRef, useState } from 'react';
import { useNavigationContext } from '../context';
import type { UniversalTopbarProps } from '../types';
import { cn, getVariantStyles } from '../utils';

export const UniversalTopbar = forwardRef<HTMLElement, UniversalTopbarProps>(
  (
    {
      items = [],
      activeItem,
      variant = 'admin',
      user,
      branding,
      tenant,
      actions,
      onNavigate,
      onLogout,
      className,
      ...props
    },
    ref
  ) => {
    const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
    const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
    const variantStyles = getVariantStyles(variant);
    const { onNavigate: contextOnNavigate } = useNavigationContext();

    const handleNavigate = onNavigate || contextOnNavigate;

    const renderNavigationItems = (mobile = false) => (
      <div className={cn('flex space-x-8', { 'flex-col space-x-0 space-y-1': mobile })}>
        {items.map((item) => {
          const isActive = activeItem === item.id;
          const Icon = item.icon;

          return (
            <button
              key={item.id}
              type='button'
              onClick={() => handleNavigate?.(item)}
              disabled={item.disabled}
              className={cn(
                'flex items-center px-3 py-2 text-sm font-medium transition-colors rounded-md',
                'hover:bg-gray-100 focus:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-offset-2',
                {
                  [variantStyles.primary]: isActive,
                  'text-gray-500 hover:text-gray-700': !isActive && !item.disabled,
                  'text-gray-300 cursor-not-allowed': item.disabled,
                  'justify-start w-full': mobile,
                }
              )}
              aria-current={isActive ? 'page' : undefined}
            >
              {Icon && <Icon className='mr-2 h-4 w-4' />}
              {item.label}
              {item.badge && (
                <span className='ml-2 inline-flex items-center justify-center rounded-full bg-red-100 px-2 py-1 text-xs font-bold text-red-600'>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    );

    return (
      <header
        ref={ref}
        className={cn('bg-white border-b border-gray-200 shadow-sm', className)}
        {...props}
      >
        <div className='mx-auto max-w-7xl px-4 sm:px-6 lg:px-8'>
          <div className='flex h-16 items-center justify-between'>
            {/* Left Section - Logo and Branding */}
            <div className='flex items-center'>
              {branding?.logo || branding?.logoUrl ? (
                <div className='mr-4 flex-shrink-0'>
                  {branding.logo ? (
                    branding.logo
                  ) : (
                    <img className='h-8 w-auto' src={branding.logoUrl} alt={branding.companyName} />
                  )}
                </div>
              ) : null}

              <div className='flex flex-col'>
                <h1 className='text-lg font-semibold text-gray-900'>
                  {branding?.companyName || 'Dashboard'}
                </h1>
                {tenant && <span className='text-sm text-gray-500'>{tenant.name}</span>}
              </div>
            </div>

            {/* Center Section - Desktop Navigation */}
            <div className='hidden md:block'>{renderNavigationItems()}</div>

            {/* Right Section - Actions and User Menu */}
            <div className='flex items-center space-x-4'>
              {/* Custom Actions */}
              {actions}

              {/* User Menu */}
              {user && (
                <div className='relative'>
                  <button
                    type='button'
                    onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                    className='flex items-center rounded-full bg-white p-1 text-sm focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2'
                    aria-expanded={isUserMenuOpen}
                    aria-haspopup='true'
                  >
                    <span className='sr-only'>Open user menu</span>
                    {user.avatar ? (
                      <img className='h-8 w-8 rounded-full' src={user.avatar} alt={user.name} />
                    ) : (
                      <div className='flex h-8 w-8 items-center justify-center rounded-full bg-gray-300'>
                        <User className='h-5 w-5 text-gray-600' />
                      </div>
                    )}
                    <div className='ml-2 hidden md:block'>
                      <div className='text-sm font-medium text-gray-700'>{user.name}</div>
                      {user.role && <div className='text-xs text-gray-500'>{user.role}</div>}
                    </div>
                    <ChevronDown className='ml-2 h-4 w-4 text-gray-400' />
                  </button>

                  {/* User Dropdown Menu */}
                  {isUserMenuOpen && (
                    <div className='absolute right-0 z-10 mt-2 w-48 origin-top-right rounded-md bg-white py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none'>
                      <div className='px-4 py-2 border-b border-gray-100'>
                        <div className='text-sm font-medium text-gray-900'>{user.name}</div>
                        <div className='text-sm text-gray-500'>{user.email}</div>
                      </div>

                      <button
                        type='button'
                        className='flex w-full items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100'
                        onClick={() => {
                          setIsUserMenuOpen(false);
                          // Handle settings navigation
                        }}
                      >
                        <Settings className='mr-3 h-4 w-4' />
                        Settings
                      </button>

                      {onLogout && (
                        <button
                          type='button'
                          onClick={() => {
                            setIsUserMenuOpen(false);
                            onLogout();
                          }}
                          className='flex w-full items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100'
                        >
                          <LogOut className='mr-3 h-4 w-4' />
                          Sign Out
                        </button>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Mobile Menu Button */}
              <div className='md:hidden'>
                <button
                  type='button'
                  onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                  className='inline-flex items-center justify-center rounded-md p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2'
                  aria-expanded={isMobileMenuOpen}
                >
                  <span className='sr-only'>Open main menu</span>
                  <Menu className='h-6 w-6' />
                </button>
              </div>
            </div>
          </div>

          {/* Mobile Menu */}
          {isMobileMenuOpen && (
            <div className='md:hidden border-t border-gray-200 pt-4 pb-3'>
              <div className='space-y-1'>{renderNavigationItems(true)}</div>
            </div>
          )}
        </div>
      </header>
    );
  }
);

UniversalTopbar.displayName = 'UniversalTopbar';
