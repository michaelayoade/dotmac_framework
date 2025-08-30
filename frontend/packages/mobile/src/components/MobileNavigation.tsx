import React, { useCallback } from 'react';
import { clsx } from 'clsx';
import { MobileNavigationProps, NavigationItem } from './types';

export function MobileNavigation({
  items,
  activeItem,
  position = 'bottom',
  showLabels = true,
  badges = {},
  className,
  onItemClick
}: MobileNavigationProps) {

  const handleItemClick = useCallback((item: NavigationItem) => {
    if (item.disabled) return;

    // Haptic feedback
    if ('vibrate' in navigator) {
      navigator.vibrate([10]);
    }

    onItemClick?.(item);
  }, [onItemClick]);

  const navigationClasses = clsx(
    'mobile-navigation-container',
    'flex',
    'items-center',
    'justify-around',
    'bg-white',
    'border-t',
    'border-gray-200',
    {
      'fixed top-0 left-0 right-0 z-50': position === 'top',
      'fixed bottom-0 left-0 right-0 z-50': position === 'bottom',
      'shadow-lg': position === 'top',
      'shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)]': position === 'bottom'
    },
    className
  );

  return (
    <nav
      className={navigationClasses}
      style={{
        height: '60px',
        minHeight: '60px',
        paddingBottom: position === 'bottom' ? 'env(safe-area-inset-bottom)' : '0'
      }}
      role="tablist"
      aria-orientation="horizontal"
    >
      {items.map((item) => {
        const isActive = activeItem === item.id;
        const badgeCount = badges[item.id] || item.badge;

        return (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-label={item.label}
            disabled={item.disabled}
            className={clsx(
              'nav-item',
              'relative',
              'flex',
              'flex-col',
              'items-center',
              'justify-center',
              'min-w-[44px]', // Minimum touch target
              'min-h-[44px]',
              'flex-1',
              'p-2',
              'transition-all',
              'duration-200',
              'touch-manipulation',
              'select-none',
              {
                'text-blue-600': isActive && !item.disabled,
                'text-gray-600': !isActive && !item.disabled,
                'text-gray-300': item.disabled,
                'cursor-pointer': !item.disabled,
                'cursor-not-allowed': item.disabled,
                'active:scale-95': !item.disabled,
                'hover:bg-gray-50': !item.disabled && !isActive,
                'bg-blue-50': isActive && !item.disabled
              }
            )}
            onClick={() => handleItemClick(item)}
          >
            {/* Icon Container */}
            <div className={clsx(
              'icon-container',
              'relative',
              'flex',
              'items-center',
              'justify-center',
              'w-6',
              'h-6',
              'mb-1',
              {
                'transform scale-110': isActive,
                'opacity-50': item.disabled
              }
            )}>
              {item.icon}

              {/* Badge */}
              {badgeCount && badgeCount > 0 && (
                <span
                  className={clsx(
                    'absolute',
                    '-top-1',
                    '-right-1',
                    'min-w-[18px]',
                    'h-[18px]',
                    'flex',
                    'items-center',
                    'justify-center',
                    'text-xs',
                    'font-semibold',
                    'text-white',
                    'bg-red-500',
                    'rounded-full',
                    'px-1',
                    {
                      'animate-pulse': badgeCount > 99
                    }
                  )}
                  aria-label={`${badgeCount} notifications`}
                >
                  {badgeCount > 99 ? '99+' : badgeCount}
                </span>
              )}
            </div>

            {/* Label */}
            {showLabels && (
              <span
                className={clsx(
                  'text-xs',
                  'font-medium',
                  'leading-tight',
                  'text-center',
                  'max-w-full',
                  'truncate',
                  {
                    'opacity-50': item.disabled
                  }
                )}
              >
                {item.label}
              </span>
            )}

            {/* Active Indicator */}
            {isActive && (
              <div
                className={clsx(
                  'absolute',
                  position === 'bottom' ? 'top-0' : 'bottom-0',
                  'left-1/2',
                  'transform',
                  '-translate-x-1/2',
                  'w-8',
                  'h-0.5',
                  'bg-blue-600',
                  'rounded-full'
                )}
              />
            )}

            {/* Touch Ripple Effect */}
            <div className="absolute inset-0 rounded-lg overflow-hidden">
              <div className="ripple-effect" />
            </div>
          </button>
        );
      })}
    </nav>
  );
}

// Enhanced styles for mobile navigation
MobileNavigation.styles = `
  .mobile-navigation-container {
    /* Ensure navigation is above content */
    z-index: 50;

    /* Prevent overscroll */
    overscroll-behavior: contain;

    /* Hardware acceleration */
    transform: translateZ(0);
    will-change: transform;

    /* Better touch handling */
    -webkit-touch-callout: none;
    -webkit-tap-highlight-color: transparent;
  }

  .nav-item {
    /* Optimize for touch */
    touch-action: manipulation;
    -webkit-user-select: none;
    -moz-user-select: none;
    user-select: none;

    /* Smooth transitions */
    transition: all 200ms ease;
  }

  .nav-item:active {
    transform: scale(0.95);
  }

  /* Ripple effect on touch */
  .nav-item:active .ripple-effect {
    background: radial-gradient(circle, rgba(0,0,0,0.1) 1%, transparent 1%);
    background-size: 15000%;
    animation: ripple-nav 0.3s ease-out;
  }

  @keyframes ripple-nav {
    0% {
      background-size: 0%;
    }
    100% {
      background-size: 15000%;
    }
  }

  /* Badge animation */
  .nav-item .animate-pulse {
    animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
  }

  /* Accessibility improvements */
  .nav-item:focus-visible {
    outline: 2px solid #3b82f6;
    outline-offset: 2px;
    border-radius: 8px;
  }

  /* High contrast mode */
  @media (prefers-contrast: high) {
    .mobile-navigation-container {
      border-top: 2px solid;
    }

    .nav-item {
      border: 1px solid transparent;
    }

    .nav-item[aria-selected="true"] {
      border-color: currentColor;
    }
  }

  /* Reduced motion */
  @media (prefers-reduced-motion: reduce) {
    .nav-item,
    .icon-container {
      transition: none;
    }

    .nav-item:active {
      transform: none;
    }

    .animate-pulse {
      animation: none;
    }
  }

  /* Dark mode support */
  @media (prefers-color-scheme: dark) {
    .mobile-navigation-container {
      background-color: #1f2937;
      border-top-color: #374151;
    }

    .nav-item:not([aria-selected="true"]) {
      color: #9ca3af;
    }

    .nav-item:hover:not([disabled]) {
      background-color: #374151;
    }

    .nav-item[aria-selected="true"] {
      background-color: #1e3a8a;
      color: #60a5fa;
    }
  }

  /* Safe area handling */
  @supports (padding-bottom: env(safe-area-inset-bottom)) {
    .mobile-navigation-container {
      padding-bottom: env(safe-area-inset-bottom);
    }
  }
`;
