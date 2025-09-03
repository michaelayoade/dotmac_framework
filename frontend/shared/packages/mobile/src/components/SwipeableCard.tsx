/**
 * Swipeable Card Component
 * Card with swipe actions for mobile interfaces
 */

import React, { useState, useCallback, useRef } from 'react';
import { clsx } from 'clsx';
import { useGestures } from '../gestures/useGestures';
import { useVibration } from '../hardware/useDevice';

export interface SwipeAction {
  id: string;
  label: string;
  icon: React.ReactNode;
  color: 'red' | 'green' | 'blue' | 'orange' | 'gray';
  onClick: () => void;
}

export interface SwipeableCardProps {
  children: React.ReactNode;
  leftActions?: SwipeAction[];
  rightActions?: SwipeAction[];
  onSwipeThreshold?: number;
  haptic?: boolean;
  disabled?: boolean;
  className?: string;
}

export function SwipeableCard({
  children,
  leftActions = [],
  rightActions = [],
  onSwipeThreshold = 80,
  haptic = true,
  disabled = false,
  className,
}: SwipeableCardProps) {
  const [swipeOffset, setSwipeOffset] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const [revealedActions, setRevealedActions] = useState<'left' | 'right' | null>(null);
  const cardRef = useRef<HTMLDivElement>(null);
  const { vibrate } = useVibration();

  const triggerHaptic = useCallback(
    (type: 'light' | 'medium' = 'light') => {
      if (!haptic) return;
      vibrate(type === 'light' ? [10] : [20]);
    },
    [haptic, vibrate]
  );

  const resetCard = useCallback(() => {
    setIsAnimating(true);
    setSwipeOffset(0);
    setRevealedActions(null);
    setTimeout(() => setIsAnimating(false), 300);
  }, []);

  const executeAction = useCallback(
    (action: SwipeAction) => {
      triggerHaptic('medium');
      action.onClick();
      resetCard();
    },
    [triggerHaptic, resetCard]
  );

  const { ref: gestureRef } = useGestures({
    onSwipeLeft: (gesture) => {
      if (disabled || rightActions.length === 0) return;

      if (gesture.distance > onSwipeThreshold) {
        setRevealedActions('right');
        setSwipeOffset(-120);
        triggerHaptic('light');
      }
    },
    onSwipeRight: (gesture) => {
      if (disabled || leftActions.length === 0) return;

      if (gesture.distance > onSwipeThreshold) {
        setRevealedActions('left');
        setSwipeOffset(120);
        triggerHaptic('light');
      }
    },
    onTap: () => {
      if (revealedActions) {
        resetCard();
      }
    },
  });

  const getActionColor = (color: string) => {
    const colors = {
      red: 'bg-red-500 text-white',
      green: 'bg-green-500 text-white',
      blue: 'bg-blue-500 text-white',
      orange: 'bg-orange-500 text-white',
      gray: 'bg-gray-500 text-white',
    };
    return colors[color as keyof typeof colors] || colors.gray;
  };

  return (
    <div
      className={clsx(
        'swipeable-card-container',
        'relative overflow-hidden bg-white rounded-lg shadow-sm',
        'touch-manipulation select-none',
        className
      )}
    >
      {/* Left Actions */}
      {leftActions.length > 0 && (
        <div className='absolute left-0 top-0 bottom-0 flex items-stretch'>
          {leftActions.map((action, index) => (
            <button
              key={action.id}
              onClick={() => executeAction(action)}
              className={clsx(
                'flex flex-col items-center justify-center px-4 min-w-[80px]',
                'transition-all duration-200 hover:brightness-110 active:scale-95',
                'touch-manipulation',
                getActionColor(action.color)
              )}
              style={{
                transform: `translateX(${Math.min(0, swipeOffset - 120)}px)`,
              }}
              aria-label={action.label}
            >
              <div className='w-6 h-6 mb-1'>{action.icon}</div>
              <span className='text-xs font-medium'>{action.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Right Actions */}
      {rightActions.length > 0 && (
        <div className='absolute right-0 top-0 bottom-0 flex items-stretch'>
          {rightActions.map((action, index) => (
            <button
              key={action.id}
              onClick={() => executeAction(action)}
              className={clsx(
                'flex flex-col items-center justify-center px-4 min-w-[80px]',
                'transition-all duration-200 hover:brightness-110 active:scale-95',
                'touch-manipulation',
                getActionColor(action.color)
              )}
              style={{
                transform: `translateX(${Math.max(0, swipeOffset + 120)}px)`,
              }}
              aria-label={action.label}
            >
              <div className='w-6 h-6 mb-1'>{action.icon}</div>
              <span className='text-xs font-medium'>{action.label}</span>
            </button>
          ))}
        </div>
      )}

      {/* Card Content */}
      <div
        ref={(node) => {
          cardRef.current = node;
          gestureRef(node);
        }}
        className={clsx('relative z-10 bg-white transition-transform', {
          'duration-300 ease-out': isAnimating,
          'duration-75': !isAnimating,
        })}
        style={{
          transform: `translateX(${swipeOffset}px)`,
        }}
      >
        {children}
      </div>

      {/* Swipe Indicators */}
      {(leftActions.length > 0 || rightActions.length > 0) && !revealedActions && (
        <div className='absolute bottom-2 left-1/2 transform -translate-x-1/2 flex space-x-1 pointer-events-none'>
          {leftActions.length > 0 && <div className='w-1 h-1 bg-gray-300 rounded-full' />}
          {rightActions.length > 0 && <div className='w-1 h-1 bg-gray-300 rounded-full' />}
        </div>
      )}
    </div>
  );
}

// Common swipe action icons
export const SwipeActionIcons = {
  Delete: (
    <svg className='w-full h-full' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
      <path
        strokeLinecap='round'
        strokeLinejoin='round'
        strokeWidth={2}
        d='M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16'
      />
    </svg>
  ),
  Edit: (
    <svg className='w-full h-full' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
      <path
        strokeLinecap='round'
        strokeLinejoin='round'
        strokeWidth={2}
        d='M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z'
      />
    </svg>
  ),
  Archive: (
    <svg className='w-full h-full' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
      <path
        strokeLinecap='round'
        strokeLinejoin='round'
        strokeWidth={2}
        d='M5 8l4 4 4-4m0 8l-4-4-4 4'
      />
    </svg>
  ),
  Share: (
    <svg className='w-full h-full' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
      <path
        strokeLinecap='round'
        strokeLinejoin='round'
        strokeWidth={2}
        d='M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z'
      />
    </svg>
  ),
  Star: (
    <svg className='w-full h-full' fill='none' stroke='currentColor' viewBox='0 0 24 24'>
      <path
        strokeLinecap='round'
        strokeLinejoin='round'
        strokeWidth={2}
        d='M11.049 2.927c.3-.921 1.603-.921 1.902 0l1.519 4.674a1 1 0 00.95.69h4.915c.969 0 1.371 1.24.588 1.81l-3.976 2.888a1 1 0 00-.363 1.118l1.518 4.674c.3.922-.755 1.688-1.538 1.118l-3.976-2.888a1 1 0 00-1.176 0l-3.976 2.888c-.783.57-1.838-.197-1.538-1.118l1.518-4.674a1 1 0 00-.363-1.118l-3.976-2.888c-.784-.57-.38-1.81.588-1.81h4.914a1 1 0 00.951-.69l1.519-4.674z'
      />
    </svg>
  ),
};

// Enhanced styles
SwipeableCard.styles = `
  .swipeable-card-container {
    /* Hardware acceleration */
    transform: translateZ(0);
    will-change: transform;
    
    /* Touch optimization */
    -webkit-tap-highlight-color: transparent;
    touch-action: pan-x;
  }

  /* Smooth animations */
  .swipeable-card-container > div {
    backface-visibility: hidden;
    perspective: 1000px;
  }

  /* Reduced motion support */
  @media (prefers-reduced-motion: reduce) {
    .swipeable-card-container,
    .swipeable-card-container * {
      transition: none;
    }
  }

  /* High contrast mode */
  @media (prefers-contrast: high) {
    .swipeable-card-container {
      border: 1px solid;
    }
  }
`;
