import React, { useEffect, useRef } from 'react';
import { clsx } from 'clsx';
import { MobileLayoutProps } from './types';

export function MobileLayout({
  children,
  showHeader = true,
  showNavigation = true,
  navigationPosition = 'bottom',
  safeArea = true,
  fullScreen = false,
  backgroundColor = 'bg-white',
  header,
  navigation,
  className
}: MobileLayoutProps) {
  const layoutRef = useRef<HTMLDivElement>(null);

  // Handle viewport meta tag for proper mobile rendering
  useEffect(() => {
    const viewport = document.querySelector('meta[name="viewport"]');
    if (!viewport) {
      const meta = document.createElement('meta');
      meta.name = 'viewport';
      meta.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover';
      document.head.appendChild(meta);
    }

    // Handle full screen mode
    if (fullScreen && 'standalone' in window.navigator) {
      document.body.classList.add('fullscreen-mode');
    }

    return () => {
      document.body.classList.remove('fullscreen-mode');
    };
  }, [fullScreen]);

  // Handle safe area CSS variables
  useEffect(() => {
    if (safeArea && CSS.supports('padding-top: env(safe-area-inset-top)')) {
      document.documentElement.style.setProperty('--safe-area-top', 'env(safe-area-inset-top)');
      document.documentElement.style.setProperty('--safe-area-bottom', 'env(safe-area-inset-bottom)');
      document.documentElement.style.setProperty('--safe-area-left', 'env(safe-area-inset-left)');
      document.documentElement.style.setProperty('--safe-area-right', 'env(safe-area-inset-right)');
    }
  }, [safeArea]);

  const layoutClasses = clsx(
    'mobile-layout',
    'flex',
    'flex-col',
    'h-screen',
    'overflow-hidden',
    backgroundColor,
    {
      'safe-area': safeArea,
      'fullscreen': fullScreen,
      'with-header': showHeader,
      'with-navigation': showNavigation,
      [`nav-${navigationPosition}`]: showNavigation
    },
    className
  );

  const contentClasses = clsx(
    'mobile-content',
    'flex-1',
    'overflow-auto',
    'relative',
    {
      'pb-safe': safeArea && navigationPosition === 'bottom',
      'pt-safe': safeArea && navigationPosition === 'top'
    }
  );

  return (
    <div
      ref={layoutRef}
      className={layoutClasses}
      style={{
        ['--header-height' as any]: showHeader ? '56px' : '0px',
        ['--navigation-height' as any]: showNavigation ? '60px' : '0px'
      }}
    >
      {/* Header */}
      {showHeader && (
        <div className={clsx(
          'mobile-header',
          'flex-shrink-0',
          'z-40',
          {
            'pt-safe': safeArea
          }
        )}>
          {header}
        </div>
      )}

      {/* Navigation - Top */}
      {showNavigation && navigationPosition === 'top' && (
        <div className={clsx(
          'mobile-navigation',
          'mobile-navigation-top',
          'flex-shrink-0',
          'z-30'
        )}>
          {navigation}
        </div>
      )}

      {/* Main Content */}
      <main className={contentClasses}>
        {children}
      </main>

      {/* Navigation - Bottom */}
      {showNavigation && navigationPosition === 'bottom' && (
        <div className={clsx(
          'mobile-navigation',
          'mobile-navigation-bottom',
          'flex-shrink-0',
          'z-30',
          {
            'pb-safe': safeArea
          }
        )}>
          {navigation}
        </div>
      )}
    </div>
  );
}

// CSS-in-JS styles for complex mobile layouts
MobileLayout.styles = `
  .mobile-layout {
    position: relative;
    width: 100%;
    height: 100vh;
    height: calc(var(--vh, 1vh) * 100); /* Handle mobile viewport issues */
    overflow: hidden;
  }

  .mobile-layout.safe-area {
    padding-top: var(--safe-area-top, 0px);
    padding-bottom: var(--safe-area-bottom, 0px);
    padding-left: var(--safe-area-left, 0px);
    padding-right: var(--safe-area-right, 0px);
  }

  .mobile-header {
    height: var(--header-height);
    min-height: var(--header-height);
  }

  .mobile-navigation {
    height: var(--navigation-height);
    min-height: var(--navigation-height);
  }

  .mobile-content {
    flex: 1;
    overflow: auto;
    -webkit-overflow-scrolling: touch;
    overscroll-behavior: contain;
  }

  /* Handle notch/safe areas */
  .pt-safe {
    padding-top: var(--safe-area-top, 0px);
  }

  .pb-safe {
    padding-bottom: var(--safe-area-bottom, 0px);
  }

  .pl-safe {
    padding-left: var(--safe-area-left, 0px);
  }

  .pr-safe {
    padding-right: var(--safe-area-right, 0px);
  }

  /* Fullscreen mode */
  body.fullscreen-mode {
    margin: 0;
    padding: 0;
    overflow: hidden;
  }

  /* Mobile viewport height fix */
  @media screen and (max-width: 768px) {
    .mobile-layout {
      height: 100vh;
      height: -webkit-fill-available;
    }
  }

  /* Prevent overscroll bounce on iOS */
  .mobile-layout,
  .mobile-content {
    overscroll-behavior-y: contain;
  }

  /* Smooth scrolling for better mobile experience */
  .mobile-content {
    scroll-behavior: smooth;
    scroll-snap-type: y proximity;
  }

  /* Hide scrollbars on mobile while keeping functionality */
  @media (max-width: 768px) {
    .mobile-content {
      scrollbar-width: none;
      -ms-overflow-style: none;
    }

    .mobile-content::-webkit-scrollbar {
      display: none;
    }
  }

  /* Focus styles for accessibility */
  .mobile-layout *:focus {
    outline: 2px solid #3b82f6;
    outline-offset: 2px;
  }

  /* High contrast mode support */
  @media (prefers-contrast: high) {
    .mobile-layout {
      border: 1px solid;
    }
  }

  /* Reduced motion support */
  @media (prefers-reduced-motion: reduce) {
    .mobile-content {
      scroll-behavior: auto;
    }
  }
`;
