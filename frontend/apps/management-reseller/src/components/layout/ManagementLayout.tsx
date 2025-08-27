'use client';

import { useState } from 'react';
import { usePathname } from 'next/navigation';
import { X } from 'lucide-react';
import { useManagementAuth } from '@/components/auth/ManagementAuthProvider';
import { navigationConfig, getCurrentPageTitle } from './NavigationConfig';
import { Sidebar } from './Sidebar';
import { TopNavigation } from './TopNavigation';
import { RouteErrorBoundary, ComponentErrorBoundary } from '@/components/error/ErrorBoundary';
import { useFilteredNavigation } from '@/hooks/usePermissions';

interface ManagementLayoutProps {
  children: React.ReactNode;
}

export function ManagementLayout({ children }: ManagementLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const pathname = usePathname();
  const { isLoading } = useManagementAuth();
  
  // Filter navigation based on permissions using centralized system
  const filteredNavigation = useFilteredNavigation(navigationConfig);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-management-600" />
      </div>
    );
  }

  const pageTitle = getCurrentPageTitle(filteredNavigation, pathname || '/');

  return (
    <RouteErrorBoundary routeName="management-layout">
      <div className="min-h-screen bg-gray-50">
        {/* Mobile sidebar */}
        <div className={`fixed inset-0 z-50 lg:hidden ${sidebarOpen ? 'block' : 'hidden'}`}>
          <div className="fixed inset-0 bg-gray-600 bg-opacity-75" onClick={() => setSidebarOpen(false)} />
          <div className="relative flex w-full max-w-xs flex-col bg-white">
            <div className="absolute right-0 top-0 -mr-12 pt-2">
              <button
                type="button"
                className="ml-1 flex h-10 w-10 items-center justify-center rounded-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-white"
                onClick={() => setSidebarOpen(false)}
              >
                <X className="h-6 w-6 text-white" />
              </button>
            </div>
            <ComponentErrorBoundary componentName="Mobile Sidebar">
              <Sidebar filteredNavigation={filteredNavigation} />
            </ComponentErrorBoundary>
          </div>
        </div>

        {/* Desktop sidebar */}
        <div className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
          <ComponentErrorBoundary componentName="Desktop Sidebar">
            <Sidebar filteredNavigation={filteredNavigation} />
          </ComponentErrorBoundary>
        </div>

        {/* Main content */}
        <div className="lg:pl-64">
          {/* Top navigation */}
          <ComponentErrorBoundary componentName="Top Navigation">
            <TopNavigation 
              onMenuClick={() => setSidebarOpen(true)}
              pageTitle={pageTitle}
            />
          </ComponentErrorBoundary>

          {/* Page content */}
          <main className="py-8">
            <div className="px-4 sm:px-6 lg:px-8">
              <RouteErrorBoundary routeName={`page-${pathname?.split('/')[1] || 'unknown'}`}>
                {children}
              </RouteErrorBoundary>
            </div>
          </main>
        </div>
      </div>
    </RouteErrorBoundary>
  );
}