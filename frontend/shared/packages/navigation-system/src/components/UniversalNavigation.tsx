import { forwardRef, useState } from 'react';
import { NavigationProvider } from '../context';
import type { UniversalNavigationProps } from '../types';
import { cn, findActiveNavigationItem } from '../utils';
import { UniversalMobileNavigation } from './UniversalMobileNavigation';
import { UniversalSidebar } from './UniversalSidebar';
import { UniversalTopbar } from './UniversalTopbar';

export const UniversalNavigation = forwardRef<HTMLDivElement, UniversalNavigationProps>(
  (
    {
      items,
      activeItem,
      variant = 'admin',
      layoutType = 'sidebar',
      user,
      branding,
      tenant,
      onNavigate,
      onLogout,
      className,
      children,
      ...props
    },
    ref
  ) => {
    const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

    // Find current active item if not explicitly provided
    const currentActiveItem =
      activeItem || findActiveNavigationItem(items, window?.location?.pathname || '')?.id;

    const handleNavigate = (item: (typeof items)[0]) => {
      onNavigate?.(item);

      // Basic client-side navigation fallback
      if (!onNavigate && item.href) {
        window.location.href = item.href;
      }
    };

    const contextValue = {
      activeItem: currentActiveItem,
      onNavigate: handleNavigate,
      collapsed: sidebarCollapsed,
      variant,
      layoutType,
    };

    if (layoutType === 'topbar') {
      return (
        <NavigationProvider value={contextValue}>
          <div
            ref={ref}
            className={cn('universal-navigation min-h-screen bg-gray-50', className)}
            {...props}
          >
            <UniversalTopbar
              items={items}
              activeItem={currentActiveItem}
              variant={variant}
              user={user}
              branding={branding}
              tenant={tenant}
              onNavigate={handleNavigate}
              onLogout={onLogout}
            />

            <main className='flex-1'>{children}</main>

            {/* Mobile Navigation */}
            <div className='md:hidden'>
              <UniversalMobileNavigation
                items={items}
                activeItem={currentActiveItem}
                onNavigate={handleNavigate}
              />
            </div>
          </div>
        </NavigationProvider>
      );
    }

    if (layoutType === 'hybrid') {
      return (
        <NavigationProvider value={contextValue}>
          <div
            ref={ref}
            className={cn('universal-navigation min-h-screen bg-gray-50', className)}
            {...props}
          >
            <UniversalTopbar
              variant={variant}
              user={user}
              branding={branding}
              tenant={tenant}
              onLogout={onLogout}
            />

            <div className='flex h-[calc(100vh-4rem)]'>
              <UniversalSidebar
                items={items}
                activeItem={currentActiveItem}
                variant={variant}
                collapsed={sidebarCollapsed}
                collapsible
                onCollapsedChange={setSidebarCollapsed}
                onNavigate={handleNavigate}
                className='hidden md:flex'
              />

              <main
                className={cn('flex-1 overflow-auto', {
                  'ml-16': sidebarCollapsed,
                  'ml-64': !sidebarCollapsed,
                })}
              >
                {children}
              </main>
            </div>

            {/* Mobile Navigation */}
            <div className='md:hidden'>
              <UniversalMobileNavigation
                items={items}
                activeItem={currentActiveItem}
                onNavigate={handleNavigate}
              />
            </div>
          </div>
        </NavigationProvider>
      );
    }

    // Default: sidebar layout
    return (
      <NavigationProvider value={contextValue}>
        <div
          ref={ref}
          className={cn('universal-navigation flex min-h-screen bg-gray-50', className)}
          {...props}
        >
          {/* Desktop Sidebar */}
          <UniversalSidebar
            items={items}
            activeItem={currentActiveItem}
            variant={variant}
            collapsed={sidebarCollapsed}
            collapsible
            onCollapsedChange={setSidebarCollapsed}
            onNavigate={handleNavigate}
            className='hidden md:flex'
            header={
              <div className='flex items-center'>
                {branding?.logo && <div className='mr-3 flex-shrink-0'>{branding.logo}</div>}
                <div className='flex flex-col min-w-0'>
                  <h1 className='text-lg font-semibold text-gray-900 truncate'>
                    {branding?.companyName || 'Dashboard'}
                  </h1>
                  {tenant && <span className='text-sm text-gray-500 truncate'>{tenant.name}</span>}
                </div>
              </div>
            }
            footer={
              user && (
                <div className='flex items-center space-x-3'>
                  {user.avatar ? (
                    <img className='h-8 w-8 rounded-full' src={user.avatar} alt={user.name} />
                  ) : (
                    <div className='h-8 w-8 rounded-full bg-gray-300' />
                  )}
                  <div className='flex-1 min-w-0'>
                    <p className='text-sm font-medium text-gray-900 truncate'>{user.name}</p>
                    {user.role && <p className='text-xs text-gray-500 truncate'>{user.role}</p>}
                  </div>
                  {onLogout && (
                    <button
                      type='button'
                      onClick={onLogout}
                      className='text-gray-400 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 rounded'
                      aria-label='Sign out'
                    >
                      <svg
                        className='h-5 w-5'
                        fill='none'
                        viewBox='0 0 24 24'
                        stroke='currentColor'
                      >
                        <path
                          strokeLinecap='round'
                          strokeLinejoin='round'
                          strokeWidth={2}
                          d='M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1'
                        />
                      </svg>
                    </button>
                  )}
                </div>
              )
            }
          />

          {/* Main Content */}
          <main
            className={cn('flex-1 overflow-auto transition-all duration-300', {
              'md:ml-16': sidebarCollapsed,
              'md:ml-64': !sidebarCollapsed,
            })}
          >
            {children}
          </main>

          {/* Mobile Navigation */}
          <div className='md:hidden fixed bottom-4 left-4 z-50'>
            <UniversalMobileNavigation
              items={items}
              activeItem={currentActiveItem}
              onNavigate={handleNavigate}
            />
          </div>
        </div>
      </NavigationProvider>
    );
  }
);

UniversalNavigation.displayName = 'UniversalNavigation';
