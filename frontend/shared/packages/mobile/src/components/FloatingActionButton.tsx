/**
 * Floating Action Button (FAB)
 * Mobile-optimized primary action button
 */

import React, { useState, useCallback } from 'react';
import { clsx } from 'clsx';
import { cva, type VariantProps } from 'class-variance-authority';

interface FABAction {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}

const fabVariants = cva(
  [
    'fixed',
    'z-40',
    'flex',
    'items-center',
    'justify-center',
    'rounded-full',
    'shadow-lg',
    'transition-all',
    'duration-300',
    'ease-out',
    'touch-manipulation',
    'select-none',
    'active:scale-90',
    'focus:outline-none',
    'focus:ring-2',
    'focus:ring-offset-2',
    'disabled:opacity-50',
    'disabled:pointer-events-none',
  ],
  {
    variants: {
      size: {
        small: ['w-12', 'h-12', 'text-sm'],
        medium: ['w-14', 'h-14', 'text-base'],
        large: ['w-16', 'h-16', 'text-lg'],
      },
      variant: {
        primary: [
          'bg-blue-600',
          'text-white',
          'hover:bg-blue-700',
          'focus:ring-blue-500',
          'shadow-blue-500/25',
        ],
        secondary: [
          'bg-gray-600',
          'text-white',
          'hover:bg-gray-700',
          'focus:ring-gray-500',
          'shadow-gray-500/25',
        ],
        success: [
          'bg-green-600',
          'text-white',
          'hover:bg-green-700',
          'focus:ring-green-500',
          'shadow-green-500/25',
        ],
        danger: [
          'bg-red-600',
          'text-white',
          'hover:bg-red-700',
          'focus:ring-red-500',
          'shadow-red-500/25',
        ],
      },
      position: {
        'bottom-right': ['bottom-6', 'right-6'],
        'bottom-left': ['bottom-6', 'left-6'],
        'bottom-center': ['bottom-6', 'left-1/2', 'transform', '-translate-x-1/2'],
        'top-right': ['top-6', 'right-6'],
        'top-left': ['top-6', 'left-6'],
      },
    },
    defaultVariants: {
      size: 'medium',
      variant: 'primary',
      position: 'bottom-right',
    },
  }
);

export interface FloatingActionButtonProps extends VariantProps<typeof fabVariants> {
  icon?: React.ReactNode;
  label?: string;
  onClick?: () => void;
  disabled?: boolean;
  loading?: boolean;
  actions?: FABAction[];
  extended?: boolean;
  className?: string;
  haptic?: boolean;
}

export function FloatingActionButton({
  icon,
  label,
  onClick,
  disabled = false,
  loading = false,
  actions = [],
  extended = false,
  size = 'medium',
  variant = 'primary',
  position = 'bottom-right',
  className,
  haptic = true,
}: FloatingActionButtonProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isPressed, setIsPressed] = useState(false);

  const hasActions = actions.length > 0;
  const isExtended = extended && label;

  const triggerHaptic = useCallback(
    (type: 'light' | 'medium' = 'light') => {
      if (!haptic) return;

      if ('vibrate' in navigator) {
        const patterns = { light: [10], medium: [20] };
        navigator.vibrate(patterns[type]);
      }
    },
    [haptic]
  );

  const handleClick = useCallback(() => {
    if (disabled || loading) return;

    triggerHaptic('medium');

    if (hasActions) {
      setIsExpanded(!isExpanded);
    } else {
      onClick?.();
    }
  }, [disabled, loading, hasActions, isExpanded, onClick, triggerHaptic]);

  const handleActionClick = useCallback(
    (action: FABAction) => {
      if (action.disabled) return;

      triggerHaptic('light');
      action.onClick();
      setIsExpanded(false);
    },
    [triggerHaptic]
  );

  const fabClasses = fabVariants({ size, variant, position });

  return (
    <>
      {/* Background overlay when expanded */}
      {isExpanded && hasActions && (
        <div
          className='fixed inset-0 bg-black/20 z-30 transition-opacity duration-300'
          onClick={() => setIsExpanded(false)}
        />
      )}

      {/* Action items */}
      {hasActions && isExpanded && (
        <div
          className={clsx('fixed z-35 flex flex-col space-y-3', {
            'bottom-24 right-6': position === 'bottom-right',
            'bottom-24 left-6': position === 'bottom-left',
            'bottom-24 left-1/2 transform -translate-x-1/2': position === 'bottom-center',
            'top-24 right-6': position === 'top-right',
            'top-24 left-6': position === 'top-left',
          })}
        >
          {actions.map((action, index) => (
            <div
              key={index}
              className={clsx(
                'flex items-center space-x-3 animate-in slide-in-from-bottom-2 duration-300',
                {
                  'flex-row-reverse space-x-reverse': position?.includes('right'),
                }
              )}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              {/* Action label */}
              <div className='bg-gray-900 text-white px-3 py-1 rounded-full text-sm font-medium shadow-lg whitespace-nowrap'>
                {action.label}
              </div>

              {/* Action button */}
              <button
                onClick={() => handleActionClick(action)}
                disabled={action.disabled}
                className={clsx(
                  'w-12 h-12 rounded-full bg-white shadow-lg flex items-center justify-center',
                  'transition-all duration-200 hover:scale-110 active:scale-95',
                  'disabled:opacity-50 disabled:pointer-events-none',
                  'text-gray-700 hover:text-gray-900'
                )}
              >
                {action.icon}
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Main FAB */}
      <button
        onClick={handleClick}
        disabled={disabled || loading}
        className={clsx(
          fabClasses,
          {
            'scale-95': isPressed,
            'w-auto px-4 min-w-[3.5rem]': isExtended && size === 'medium',
            'w-auto px-5 min-w-[4rem]': isExtended && size === 'large',
            'w-auto px-3 min-w-[3rem]': isExtended && size === 'small',
            'rotate-45': isExpanded && hasActions,
          },
          className
        )}
        onTouchStart={() => setIsPressed(true)}
        onTouchEnd={() => setIsPressed(false)}
        onMouseDown={() => setIsPressed(true)}
        onMouseUp={() => setIsPressed(false)}
        onMouseLeave={() => setIsPressed(false)}
        aria-label={label || 'Floating action button'}
        aria-expanded={hasActions ? isExpanded : undefined}
      >
        {/* Loading spinner */}
        {loading && (
          <div className='animate-spin rounded-full border-2 border-white border-t-transparent w-5 h-5' />
        )}

        {/* Icon and label */}
        {!loading && (
          <div className='flex items-center space-x-2'>
            {icon && (
              <span
                className={clsx(
                  'flex items-center justify-center',
                  isExtended
                    ? 'text-base'
                    : size === 'small'
                      ? 'text-sm'
                      : size === 'large'
                        ? 'text-lg'
                        : 'text-base'
                )}
              >
                {icon}
              </span>
            )}

            {isExtended && label && <span className='font-medium whitespace-nowrap'>{label}</span>}
          </div>
        )}
      </button>

      {/* Safe area spacing */}
      <style jsx>{`
        @supports (padding-bottom: env(safe-area-inset-bottom)) {
          .fab-bottom {
            padding-bottom: calc(1.5rem + env(safe-area-inset-bottom));
          }
        }
      `}</style>
    </>
  );
}

// Default icons
export const FABIcons = {
  Plus: (
    <svg className='w-6 h-6' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
      <path strokeLinecap='round' strokeLinejoin='round' strokeWidth={2} d='M12 4v16m8-8H4' />
    </svg>
  ),
  Edit: (
    <svg className='w-5 h-5' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
      <path
        strokeLinecap='round'
        strokeLinejoin='round'
        strokeWidth={2}
        d='M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z'
      />
    </svg>
  ),
  Message: (
    <svg className='w-5 h-5' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
      <path
        strokeLinecap='round'
        strokeLinejoin='round'
        strokeWidth={2}
        d='M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z'
      />
    </svg>
  ),
  Phone: (
    <svg className='w-5 h-5' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
      <path
        strokeLinecap='round'
        strokeLinejoin='round'
        strokeWidth={2}
        d='M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z'
      />
    </svg>
  ),
  Share: (
    <svg className='w-5 h-5' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
      <path
        strokeLinecap='round'
        strokeLinejoin='round'
        strokeWidth={2}
        d='M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z'
      />
    </svg>
  ),
};

// Enhanced styles
FloatingActionButton.styles = `
  .fab {
    /* Hardware acceleration */
    transform: translateZ(0);
    will-change: transform;
    
    /* Touch optimization */
    -webkit-tap-highlight-color: transparent;
    touch-action: manipulation;
  }

  /* Animation improvements */
  @keyframes fab-in {
    from {
      transform: scale(0) rotate(0deg);
      opacity: 0;
    }
    to {
      transform: scale(1) rotate(0deg);
      opacity: 1;
    }
  }

  .fab {
    animation: fab-in 0.3s ease-out;
  }

  /* Reduced motion support */
  @media (prefers-reduced-motion: reduce) {
    .fab {
      animation: none;
      transition: none;
    }
  }

  /* Safe area support */
  @supports (padding-bottom: env(safe-area-inset-bottom)) {
    .fab[class*="bottom-"] {
      bottom: calc(1.5rem + env(safe-area-inset-bottom));
    }
  }

  /* High contrast mode */
  @media (prefers-contrast: high) {
    .fab {
      border: 2px solid;
    }
  }
`;
