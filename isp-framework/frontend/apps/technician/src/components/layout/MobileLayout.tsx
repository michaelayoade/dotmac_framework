'use client';

import { ReactNode } from 'react';
import { MobileNavigation } from './MobileNavigation';
import { MobileHeader } from './MobileHeader';

interface MobileLayoutProps {
  children: ReactNode;
  showHeader?: boolean;
  showNavigation?: boolean;
  headerTitle?: string;
  className?: string;
}

export function MobileLayout({
  children,
  showHeader = true,
  showNavigation = true,
  headerTitle,
  className = '',
}: MobileLayoutProps) {
  return (
    <div className={`min-h-screen-safe flex flex-col bg-gray-50 ${className}`}>
      {/* Header */}
      {showHeader && (
        <div className='safe-area-inset-top'>
          <MobileHeader title={headerTitle} />
        </div>
      )}

      {/* Main Content */}
      <main className='flex-1 overflow-y-auto'>
        <div className='px-4 py-4 pb-20'>{children}</div>
      </main>

      {/* Bottom Navigation */}
      {showNavigation && (
        <div className='safe-area-inset-bottom'>
          <MobileNavigation />
        </div>
      )}
    </div>
  );
}
