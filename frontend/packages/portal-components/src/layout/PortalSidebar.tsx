'use client';

import { Fragment } from 'react';
import { usePathname } from 'next/navigation';
import Link from 'next/link';
import { Dialog, Transition } from '@headlessui/react';
import { X } from 'lucide-react';
import { useUniversalTheme, PortalBrand } from '@dotmac/primitives/themes';
import clsx from 'clsx';

export interface NavigationItem {
  name: string;
  href: string;
  icon: any;
  current?: boolean;
  badge?: string | number;
  children?: NavigationItem[];
}

export interface PortalSidebarProps {
  open: boolean;
  onClose: () => void;
  isMobile: boolean;
  navigation: NavigationItem[];
  branding: {
    title: string;
    subtitle?: string;
    version?: string;
  };
  footer?: React.ReactNode;
}

export function PortalSidebar({
  open,
  onClose,
  isMobile,
  navigation,
  branding,
  footer
}: PortalSidebarProps) {
  const pathname = usePathname();
  const { portalTheme, config } = useUniversalTheme();

  // Auto-determine current state based on pathname
  const navigationWithCurrent = navigation.map(item => ({
    ...item,
    current: item.current ?? pathname.startsWith(item.href),
    children: item.children?.map(child => ({
      ...child,
      current: child.current ?? pathname.startsWith(child.href)
    }))
  }));

  const SidebarContent = () => (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex items-center flex-shrink-0 px-4 py-4">
        <PortalBrand size="md" className="w-full" />
      </div>

      {/* Navigation */}
      <div className="flex-1 flex flex-col overflow-y-auto">
        <nav className="flex-1 px-2 py-4 bg-white space-y-1">
          {navigationWithCurrent.map((item) => {
            const Icon = item.icon;
            return (
              <div key={item.name}>
                <Link
                  href={item.href}
                  onClick={isMobile ? onClose : undefined}
                  className={clsx(
                    'group flex items-center px-2 py-2 text-sm font-medium rounded-md transition-all duration-200',
                    item.current
                      ? 'border-r-2'
                      : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                  )}
                  style={item.current ? {
                    backgroundColor: `${portalTheme.secondaryColor}`,
                    color: portalTheme.textColor,
                    borderRightColor: portalTheme.primaryColor
                  } : undefined}
                >
                  <Icon
                    className={clsx(
                      'mr-3 flex-shrink-0 h-6 w-6',
                      !item.current && 'text-gray-400 group-hover:text-gray-500'
                    )}
                    style={item.current ? { color: portalTheme.primaryColor } : undefined}
                  />
                  {item.name}
                  {item.badge && (
                    <span
                      className="ml-auto inline-block py-0.5 px-2 text-xs rounded-full"
                      style={{
                        backgroundColor: portalTheme.secondaryColor,
                        color: portalTheme.primaryColor
                      }}
                    >
                      {item.badge}
                    </span>
                  )}
                </Link>

                {/* Sub-navigation */}
                {item.children && item.children.length > 0 && (
                  <div className="ml-6 mt-1 space-y-1">
                    {item.children.map((child) => {
                      const ChildIcon = child.icon;
                      return (
                        <Link
                          key={child.name}
                          href={child.href}
                          onClick={isMobile ? onClose : undefined}
                          className={clsx(
                            'group flex items-center px-2 py-1 text-sm font-medium rounded-md',
                            child.current
                              ? 'bg-primary-50 text-primary-800'
                              : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                          )}
                        >
                          {ChildIcon && (
                            <ChildIcon
                              className={clsx(
                                'mr-2 flex-shrink-0 h-4 w-4',
                                child.current
                                  ? 'text-primary-400'
                                  : 'text-gray-400 group-hover:text-gray-500'
                              )}
                            />
                          )}
                          {child.name}
                          {child.badge && (
                            <span className="ml-auto inline-block py-0.5 px-2 text-xs rounded-full bg-primary-100 text-primary-600">
                              {child.badge}
                            </span>
                          )}
                        </Link>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </nav>
      </div>

      {/* Footer */}
      {(footer || branding.version) && (
        <div className="flex-shrink-0 p-4 border-t border-gray-200">
          {footer || (
            <div className="text-xs text-gray-500">
              <p>{branding.subtitle || 'Management Portal'}</p>
              {branding.version && <p className="mt-1">{branding.version}</p>}
            </div>
          )}
        </div>
      )}
    </div>
  );

  if (isMobile) {
    return (
      <Transition.Root show={open} as={Fragment}>
        <Dialog as="div" className="fixed inset-0 flex z-40 md:hidden" onClose={onClose}>
          <Transition.Child
            as={Fragment}
            enter="transition-opacity ease-linear duration-300"
            enterFrom="opacity-0"
            enterTo="opacity-100"
            leave="transition-opacity ease-linear duration-300"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Dialog.Overlay className="fixed inset-0 bg-gray-600 bg-opacity-75" />
          </Transition.Child>

          <Transition.Child
            as={Fragment}
            enter="transition ease-in-out duration-300 transform"
            enterFrom="-translate-x-full"
            enterTo="translate-x-0"
            leave="transition ease-in-out duration-300 transform"
            leaveFrom="translate-x-0"
            leaveTo="-translate-x-full"
          >
            <div className="relative flex-1 flex flex-col max-w-xs w-full pt-5 pb-4 bg-white">
              <Transition.Child
                as={Fragment}
                enter="ease-in-out duration-300"
                enterFrom="opacity-0"
                enterTo="opacity-100"
                leave="ease-in-out duration-300"
                leaveFrom="opacity-100"
                leaveTo="opacity-0"
              >
                <div className="absolute top-0 right-0 -mr-12 pt-2">
                  <button
                    type="button"
                    className="ml-1 flex items-center justify-center h-10 w-10 rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
                    onClick={onClose}
                  >
                    <X className="h-6 w-6 text-white" />
                  </button>
                </div>
              </Transition.Child>
              <SidebarContent />
            </div>
          </Transition.Child>
        </Dialog>
      </Transition.Root>
    );
  }

  return (
    <div className="hidden md:flex md:flex-shrink-0">
      <div className="flex flex-col w-64">
        <div className="flex flex-col h-0 flex-1 border-r border-gray-200 bg-white">
          <SidebarContent />
        </div>
      </div>
    </div>
  );
}
