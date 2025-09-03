/**
 * Enhanced Mobile Navigation Component
 * Modern mobile-first navigation with gestures and animations
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { clsx } from 'clsx';
import { useGestures } from '../gestures/useGestures';

export interface NavItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  activeIcon?: React.ReactNode;
  href?: string;
  onClick?: () => void;
  badge?: string | number;
  disabled?: boolean;
}

export interface MobileNavigationV2Props {
  items: NavItem[];
  activeItem?: string;
  onItemChange?: (itemId: string) => void;
  position?: 'bottom' | 'top';
  variant?: 'tabs' | 'pills' | 'floating';
  showLabels?: boolean;
  haptic?: boolean;
  swipeNavigation?: boolean;
  className?: string;
}

export function MobileNavigationV2({
  items,
  activeItem,
  onItemChange,
  position = 'bottom',
  variant = 'tabs',
  showLabels = true,
  haptic = true,
  swipeNavigation = true,
  className,
}: MobileNavigationV2Props) {
  const [currentActive, setCurrentActive] = useState(activeItem || items[0]?.id);
  const [swipeOffset, setSwipeOffset] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const navRef = useRef<HTMLDivElement>(null);

  const triggerHaptic = useCallback(
    (type: 'light' | 'medium' = 'light') => {
      if (!haptic) return;

      if ('vibrate' in navigator) {
        const patterns = { light: [10], medium: [15] };
        navigator.vibrate(patterns[type]);
      }
    },
    [haptic]
  );

  const handleItemClick = useCallback(
    (item: NavItem) => {
      if (item.disabled) return;

      triggerHaptic('light');
      setCurrentActive(item.id);
      onItemChange?.(item.id);

      if (item.onClick) {
        item.onClick();
      } else if (item.href) {
        window.location.href = item.href;
      }
    },
    [onItemChange, triggerHaptic]
  );

  const navigateToNext = useCallback(() => {
    const currentIndex = items.findIndex((item) => item.id === currentActive);
    const nextIndex = (currentIndex + 1) % items.length;
    const nextItem = items[nextIndex];

    if (nextItem && !nextItem.disabled) {
      handleItemClick(nextItem);
    }
  }, [items, currentActive, handleItemClick]);

  const navigateToPrev = useCallback(() => {
    const currentIndex = items.findIndex((item) => item.id === currentActive);
    const prevIndex = currentIndex === 0 ? items.length - 1 : currentIndex - 1;
    const prevItem = items[prevIndex];

    if (prevItem && !prevItem.disabled) {
      handleItemClick(prevItem);
    }
  }, [items, currentActive, handleItemClick]);

  // Gesture handling for swipe navigation
  const { ref: gestureRef } = useGestures(
    swipeNavigation
      ? {
          onSwipeLeft: () => navigateToNext(),
          onSwipeRight: () => navigateToPrev(),
        }
      : {}
  );

  // Update active item when prop changes
  useEffect(() => {
    if (activeItem && activeItem !== currentActive) {
      setCurrentActive(activeItem);
    }
  }, [activeItem, currentActive]);

  // Get variant-specific classes
  const getVariantClasses = () => {
    switch (variant) {
      case 'pills':
        return {
          container: 'bg-gray-100/80 backdrop-blur-sm rounded-full mx-4 my-2',
          item: 'rounded-full m-1',
          active: 'bg-white shadow-sm',
        };
      case 'floating':
        return {
          container: 'bg-white/90 backdrop-blur-sm rounded-2xl mx-4 my-2 shadow-lg',
          item: 'rounded-xl m-2',
          active: 'bg-blue-50 shadow-sm',
        };
      default: // tabs
        return {
          container: 'bg-white border-t border-gray-200',
          item: '',
          active: 'text-blue-600',
        };
    }
  };

  const variantClasses = getVariantClasses();
  const activeIndex = items.findIndex((item) => item.id === currentActive);

  return (
    <nav
      ref={(node) => {
        navRef.current = node;
        if (swipeNavigation) gestureRef(node);
      }}
      className={clsx(
        'fixed w-full z-30 transition-transform duration-300',
        {
          'bottom-0': position === 'bottom',
          'top-0': position === 'top',
        },
        variantClasses.container,
        className
      )}
      style={{
        transform: swipeOffset ? `translateX(${swipeOffset}px)` : undefined,
      }}
      role='navigation'
      aria-label='Main navigation'
    >
      {/* Active indicator for tabs variant */}
      {variant === 'tabs' && (
        <div
          className='absolute top-0 h-0.5 bg-blue-600 transition-all duration-300 ease-out'
          style={{
            width: `${100 / items.length}%`,
            left: `${(activeIndex * 100) / items.length}%`,
          }}
        />
      )}

      <div className='flex items-center justify-around'>
        {items.map((item, index) => {
          const isActive = item.id === currentActive;
          const Icon = isActive && item.activeIcon ? item.activeIcon : item.icon;

          return (
            <button
              key={item.id}
              onClick={() => handleItemClick(item)}
              disabled={item.disabled}
              className={clsx(
                'relative flex-1 flex flex-col items-center justify-center transition-all duration-200',
                'min-h-[60px] touch-manipulation select-none',
                'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2',
                'disabled:opacity-50 disabled:pointer-events-none',
                {
                  'py-2': variant === 'tabs',
                  'py-3': variant !== 'tabs',
                  'text-blue-600': isActive && variant === 'tabs',
                  'text-gray-600': !isActive || variant !== 'tabs',
                  'hover:text-gray-900': !isActive,
                  'active:scale-95': !item.disabled,
                },
                variantClasses.item,
                isActive ? variantClasses.active : ''
              )}
              aria-current={isActive ? 'page' : undefined}
              aria-label={item.label}
            >
              {/* Icon container with animation */}
              <div
                className={clsx(
                  'relative flex items-center justify-center mb-1 transition-transform duration-200',
                  {
                    'transform scale-110': isActive && variant !== 'tabs',
                    'transform scale-100': !isActive || variant === 'tabs',
                  }
                )}
              >
                {/* Icon */}
                <span className='w-6 h-6 flex items-center justify-center'>{Icon}</span>

                {/* Badge */}
                {item.badge && (
                  <span className='absolute -top-2 -right-2 bg-red-500 text-white text-xs rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1'>
                    {typeof item.badge === 'number' && item.badge > 99 ? '99+' : item.badge}
                  </span>
                )}

                {/* Active indicator for pills/floating variants */}
                {isActive && variant !== 'tabs' && (
                  <div className='absolute -bottom-1 w-1 h-1 bg-blue-600 rounded-full' />
                )}
              </div>

              {/* Label */}
              {showLabels && (
                <span
                  className={clsx('text-xs font-medium leading-none transition-all duration-200', {
                    'opacity-100': isActive || variant !== 'tabs',
                    'opacity-75': !isActive && variant === 'tabs',
                  })}
                >
                  {item.label}
                </span>
              )}

              {/* Ripple effect */}
              <div
                className={clsx(
                  'absolute inset-0 rounded-full transition-all duration-300 pointer-events-none',
                  {
                    'bg-blue-100/0 hover:bg-blue-100/50 active:bg-blue-100/75': !item.disabled,
                    'bg-transparent': item.disabled,
                  }
                )}
              />
            </button>
          );
        })}
      </div>

      {/* Swipe indicator */}
      {swipeNavigation && (
        <div className='absolute -top-3 left-1/2 transform -translate-x-1/2 w-8 h-1 bg-gray-300 rounded-full opacity-50' />
      )}

      {/* Safe area padding */}
      {position === 'bottom' && (
        <div
          className='h-0'
          style={{
            paddingBottom: 'env(safe-area-inset-bottom)',
          }}
        />
      )}
    </nav>
  );
}

// Navigation icons
export const NavIcons = {
  Home: (
    <svg className='w-full h-full' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
      <path
        strokeLinecap='round'
        strokeLinejoin='round'
        strokeWidth={2}
        d='M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6'
      />
    </svg>
  ),
  HomeFilled: (
    <svg className='w-full h-full' fill='currentColor' viewBox='0 0 24 24'>
      <path d='M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z' />
    </svg>
  ),
  Search: (
    <svg className='w-full h-full' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
      <path
        strokeLinecap='round'
        strokeLinejoin='round'
        strokeWidth={2}
        d='M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z'
      />
    </svg>
  ),
  User: (
    <svg className='w-full h-full' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
      <path
        strokeLinecap='round'
        strokeLinejoin='round'
        strokeWidth={2}
        d='M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z'
      />
    </svg>
  ),
  UserFilled: (
    <svg className='w-full h-full' fill='currentColor' viewBox='0 0 24 24'>
      <path
        fillRule='evenodd'
        d='M12 4a4 4 0 100 8 4 4 0 000-8zm-6 8a6 6 0 1112 0v1.7c0 2.5-2.1 4.3-4.6 4.3H10.6C8.1 18 6 16.2 6 13.7V12z'
        clipRule='evenodd'
      />
    </svg>
  ),
  Settings: (
    <svg className='w-full h-full' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
      <path
        strokeLinecap='round'
        strokeLinejoin='round'
        strokeWidth={2}
        d='M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z'
      />
      <path
        strokeLinecap='round'
        strokeLinejoin='round'
        strokeWidth={2}
        d='M15 12a3 3 0 11-6 0 3 3 0 016 0z'
      />
    </svg>
  ),
};

// Enhanced styles
MobileNavigationV2.styles = `
  .mobile-navigation {
    /* Hardware acceleration */
    transform: translateZ(0);
    will-change: transform;
    
    /* Touch optimization */
    -webkit-tap-highlight-color: transparent;
    touch-action: pan-x;
  }

  /* Smooth transitions */
  .mobile-navigation button {
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  }

  /* Safe area support */
  @supports (padding-bottom: env(safe-area-inset-bottom)) {
    .mobile-navigation.bottom {
      padding-bottom: env(safe-area-inset-bottom);
    }
  }

  /* Reduced motion support */
  @media (prefers-reduced-motion: reduce) {
    .mobile-navigation,
    .mobile-navigation button,
    .mobile-navigation .active-indicator {
      transition: none;
    }
  }

  /* High contrast mode */
  @media (prefers-contrast: high) {
    .mobile-navigation {
      border: 1px solid;
    }
    
    .mobile-navigation button {
      border: 1px solid transparent;
    }
    
    .mobile-navigation button[aria-current="page"] {
      border-color: currentColor;
    }
  }

  /* Dark mode support */
  @media (prefers-color-scheme: dark) {
    .mobile-navigation.tabs {
      background-color: #1f2937;
      border-color: #374151;
      color: #f9fafb;
    }
    
    .mobile-navigation.floating,
    .mobile-navigation.pills {
      background-color: rgba(31, 41, 55, 0.9);
    }
  }
`;
