'use client';

import type { ReactNode } from 'react';

import { CustomerHeader } from './CustomerHeader';
import { CustomerNavigation } from './CustomerNavigation';

interface CustomerLayoutProps {
  children: ReactNode;
}

export function CustomerLayout({ children }: CustomerLayoutProps) {
  return (
    <div className='customer-layout'>
      <CustomerHeader />
      <CustomerNavigation />
      <main className='customer-content'>{children}</main>
    </div>
  );
}
