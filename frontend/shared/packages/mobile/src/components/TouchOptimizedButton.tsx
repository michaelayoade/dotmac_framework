import React, { useState, useCallback, useRef, useEffect } from 'react';
import { clsx } from 'clsx';
import { cva, type VariantProps } from 'class-variance-authority';
import { TouchOptimizedButtonProps } from './types';
import { TouchRipple } from './TouchRipple';

const buttonVariants = cva(
  [
    'relative',
    'inline-flex',
    'items-center',
    'justify-center',
    'rounded-lg',
    'font-medium',
    'transition-all',
    'duration-200',
    'select-none',
    'touch-manipulation',
    'active:scale-95',
    'disabled:opacity-50',
    'disabled:pointer-events-none',
    'focus-visible:outline-none',
    'focus-visible:ring-2',
    'focus-visible:ring-blue-500',
    'focus-visible:ring-offset-2',
  ],
  {
    variants: {
      variant: {
        primary: [
          'bg-blue-600',
          'text-white',
          'hover:bg-blue-700',
          'active:bg-blue-800',
          'shadow-md',
          'hover:shadow-lg',
        ],
        secondary: [
          'bg-gray-100',
          'text-gray-900',
          'hover:bg-gray-200',
          'active:bg-gray-300',
          'border',
          'border-gray-300',
        ],
        outline: [
          'bg-transparent',
          'text-blue-600',
          'border-2',
          'border-blue-600',
          'hover:bg-blue-50',
          'active:bg-blue-100',
        ],
        ghost: ['bg-transparent', 'text-gray-700', 'hover:bg-gray-100', 'active:bg-gray-200'],
      },
      size: {
        small: [
          'h-10',
          'min-h-[44px]', // iOS minimum touch target
          'px-3',
          'text-sm',
          'min-w-[44px]',
        ],
        medium: [
          'h-12',
          'min-h-[48px]', // Android minimum touch target
          'px-4',
          'text-base',
          'min-w-[48px]',
        ],
        large: [
          'h-14',
          'min-h-[56px]', // Large touch target
          'px-6',
          'text-lg',
          'min-w-[56px]',
        ],
      },
      fullWidth: {
        true: 'w-full',
      },
    },
    defaultVariants: {
      variant: 'primary',
      size: 'medium',
    },
  }
);

export function TouchOptimizedButton({
  children,
  variant = 'primary',
  size = 'medium',
  disabled = false,
  loading = false,
  fullWidth = false,
  ripple = true,
  haptic = true,
  onClick,
  className,
  ...props
}: TouchOptimizedButtonProps & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const [isPressed, setIsPressed] = useState(false);
  const [showRipple, setShowRipple] = useState(false);
  const [rippleCoords, setRippleCoords] = useState({ x: 0, y: 0 });
  const buttonRef = useRef<HTMLButtonElement>(null);
  const longPressTimeoutRef = useRef<NodeJS.Timeout>();

  // Haptic feedback helper
  const triggerHaptic = useCallback(
    (type: 'light' | 'medium' | 'heavy' = 'light') => {
      if (!haptic) return;

      if ('vibrate' in navigator) {
        const patterns = {
          light: [10],
          medium: [20],
          heavy: [30],
        };
        navigator.vibrate(patterns[type]);
      }
    },
    [haptic]
  );

  // Handle touch start
  const handleTouchStart = useCallback(
    (event: React.TouchEvent) => {
      if (disabled || loading) return;

      setIsPressed(true);
      triggerHaptic('light');

      // Calculate ripple position
      if (ripple && buttonRef.current) {
        const rect = buttonRef.current.getBoundingClientRect();
        const touch = event.touches[0];
        setRippleCoords({
          x: touch.clientX - rect.left,
          y: touch.clientY - rect.top,
        });
        setShowRipple(true);
      }

      // Long press detection
      longPressTimeoutRef.current = setTimeout(() => {
        triggerHaptic('medium');
      }, 500);
    },
    [disabled, loading, ripple, triggerHaptic]
  );

  // Handle touch end
  const handleTouchEnd = useCallback(() => {
    setIsPressed(false);

    if (longPressTimeoutRef.current) {
      clearTimeout(longPressTimeoutRef.current);
    }

    // Hide ripple after animation
    if (ripple) {
      setTimeout(() => setShowRipple(false), 300);
    }
  }, [ripple]);

  // Handle click
  const handleClick = useCallback(
    (event: React.MouseEvent<HTMLButtonElement>) => {
      if (disabled || loading) {
        event.preventDefault();
        return;
      }

      triggerHaptic('medium');
      onClick?.();
    },
    [disabled, loading, onClick, triggerHaptic]
  );

  // Handle mouse events for desktop
  const handleMouseDown = useCallback(
    (event: React.MouseEvent) => {
      if (disabled || loading) return;

      setIsPressed(true);

      // Calculate ripple position for mouse
      if (ripple && buttonRef.current) {
        const rect = buttonRef.current.getBoundingClientRect();
        setRippleCoords({
          x: event.clientX - rect.left,
          y: event.clientY - rect.top,
        });
        setShowRipple(true);
      }
    },
    [disabled, loading, ripple]
  );

  const handleMouseUp = useCallback(() => {
    setIsPressed(false);

    if (ripple) {
      setTimeout(() => setShowRipple(false), 300);
    }
  }, [ripple]);

  const handleMouseLeave = useCallback(() => {
    setIsPressed(false);
    setShowRipple(false);
  }, []);

  // Cleanup timeouts
  useEffect(() => {
    return () => {
      if (longPressTimeoutRef.current) {
        clearTimeout(longPressTimeoutRef.current);
      }
    };
  }, []);

  const buttonClasses = buttonVariants({
    variant,
    size,
    fullWidth: fullWidth ? true : undefined,
  });

  return (
    <button
      ref={buttonRef}
      className={clsx(
        buttonClasses,
        {
          'transform scale-95': isPressed,
          'cursor-not-allowed': disabled,
          'cursor-wait': loading,
        },
        className
      )}
      disabled={disabled || loading}
      onClick={handleClick}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onMouseDown={handleMouseDown}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseLeave}
      {...props}
    >
      {/* Ripple Effect */}
      {ripple && <TouchRipple show={showRipple} x={rippleCoords.x} y={rippleCoords.y} />}

      {/* Loading Spinner */}
      {loading && (
        <div className='absolute inset-0 flex items-center justify-center'>
          <div className='animate-spin rounded-full h-5 w-5 border-2 border-white border-t-transparent' />
        </div>
      )}

      {/* Button Content */}
      <span
        className={clsx('flex items-center justify-center gap-2', {
          'opacity-0': loading,
        })}
      >
        {children}
      </span>
    </button>
  );
}

// Add styles for enhanced touch experience
TouchOptimizedButton.styles = `
  .touch-optimized-button {
    /* Prevent text selection */
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
    user-select: none;

    /* Optimize for touch */
    -webkit-touch-callout: none;
    -webkit-tap-highlight-color: transparent;

    /* Better touch scrolling */
    touch-action: manipulation;

    /* Prevent zoom on double-tap */
    touch-action: manipulation;

    /* Hardware acceleration */
    transform: translateZ(0);
    will-change: transform;
  }

  /* High DPI displays */
  @media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
    .touch-optimized-button {
      border-width: 0.5px;
    }
  }

  /* Accessibility improvements */
  @media (prefers-reduced-motion: reduce) {
    .touch-optimized-button {
      transition: none;
    }

    .touch-optimized-button .animate-spin {
      animation: none;
    }
  }

  /* High contrast mode */
  @media (prefers-contrast: high) {
    .touch-optimized-button {
      border: 2px solid;
    }
  }
`;
