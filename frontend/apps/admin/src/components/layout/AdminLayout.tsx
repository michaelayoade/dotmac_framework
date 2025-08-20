'use client';

import { ErrorBoundary } from '@dotmac/primitives/error';
import type { ReactNode } from 'react';

import { AdminHeader } from './AdminHeader';
import { AdminSidebar } from './AdminSidebar';

interface AdminLayoutProps {
  children: ReactNode;
}

export function AdminLayout({ children }: AdminLayoutProps) {
  return (
    <div className='admin-layout'>
      <ErrorBoundary level='section'>
        <AdminHeader />
      </ErrorBoundary>
      <div className='flex h-[calc(100vh-64px)]'>
        <ErrorBoundary level='section'>
          <AdminSidebar />
        </ErrorBoundary>
        <main className='admin-content'>
          <ErrorBoundary level='section'>{children}</ErrorBoundary>
        </main>
      </div>
    </div>
  );
}
