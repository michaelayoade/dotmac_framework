'use client';

import type { ReactNode } from 'react';

import { ResellerHeader } from './ResellerHeader';
import { ResellerNavigation } from './ResellerNavigation';

interface ResellerLayoutProps {
  children: ReactNode;
}

export function ResellerLayout({ children }: ResellerLayoutProps) {
  return (
    <div className='reseller-layout'>
      <ResellerHeader />
      <ResellerNavigation />
      <main className='reseller-content'>{children}</main>
    </div>
  );
}
