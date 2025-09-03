import React, { useState, useCallback, useRef, useEffect } from 'react';
import { clsx } from 'clsx';
import { PullToRefreshProps } from './types';

export function PullToRefresh({
  children,
  onRefresh,
  threshold = 80,
  loadingIndicator,
  className,
  disabled = false,
}: PullToRefreshProps) {
  const [pullDistance, setPullDistance] = useState(0);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [startY, setStartY] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const isAtTopRef = useRef(true);

  // Check if content is at top
  const checkIfAtTop = useCallback(() => {
    if (!containerRef.current) return false;
    const scrollTop = containerRef.current.scrollTop;
    isAtTopRef.current = scrollTop <= 1; // Allow 1px tolerance
    return isAtTopRef.current;
  }, []);

  // Handle scroll to check position
  const handleScroll = useCallback(() => {
    checkIfAtTop();
  }, [checkIfAtTop]);

  // Handle touch start
  const handleTouchStart = useCallback(
    (event: React.TouchEvent) => {
      if (disabled || isRefreshing) return;

      const touch = event.touches[0];
      setStartY(touch.clientY);
      checkIfAtTop();
    },
    [disabled, isRefreshing, checkIfAtTop]
  );

  // Handle touch move
  const handleTouchMove = useCallback(
    (event: React.TouchEvent) => {
      if (disabled || isRefreshing || !isAtTopRef.current) return;

      const touch = event.touches[0];
      const deltaY = touch.clientY - startY;

      // Only pull down
      if (deltaY > 0) {
        // Prevent default scrolling when pulling to refresh
        event.preventDefault();

        // Apply resistance curve
        const resistance = 0.5;
        const distance = Math.min(deltaY * resistance, threshold * 2);
        setPullDistance(distance);

        // Haptic feedback at threshold
        if (distance >= threshold && pullDistance < threshold) {
          if ('vibrate' in navigator) {
            navigator.vibrate([15]);
          }
        }
      }
    },
    [disabled, isRefreshing, startY, threshold, pullDistance]
  );

  // Handle touch end
  const handleTouchEnd = useCallback(async () => {
    if (disabled || isRefreshing) return;

    const shouldRefresh = pullDistance >= threshold;

    if (shouldRefresh) {
      setIsRefreshing(true);

      // Haptic feedback for refresh
      if ('vibrate' in navigator) {
        navigator.vibrate([20]);
      }

      try {
        await onRefresh();
      } catch (error) {
        console.warn('Refresh failed:', error);
      } finally {
        setIsRefreshing(false);
      }
    }

    setPullDistance(0);
  }, [disabled, isRefreshing, pullDistance, threshold, onRefresh]);

  // Reset on scroll away from top
  useEffect(() => {
    if (pullDistance > 0 && !isAtTopRef.current) {
      setPullDistance(0);
    }
  }, [pullDistance]);

  const pullPercentage = Math.min((pullDistance / threshold) * 100, 100);
  const shouldShowLoader = isRefreshing || pullDistance >= threshold;
  const loaderOpacity = Math.min(pullDistance / (threshold * 0.6), 1);

  return (
    <div className={clsx('pull-to-refresh-container', 'relative', className)}>
      {/* Pull indicator */}
      <div
        className={clsx(
          'absolute',
          'top-0',
          'left-0',
          'right-0',
          'flex',
          'items-center',
          'justify-center',
          'z-10',
          'transition-all',
          'duration-300',
          'ease-out'
        )}
        style={{
          height: Math.max(pullDistance, 0),
          opacity: loaderOpacity,
        }}
      >
        {loadingIndicator ? (
          loadingIndicator
        ) : (
          <div className='flex flex-col items-center justify-center space-y-2'>
            {/* Loading spinner or arrow */}
            {shouldShowLoader ? (
              <div
                className={clsx('w-6 h-6 border-2 border-blue-500 rounded-full', {
                  'animate-spin border-t-transparent': isRefreshing,
                  'border-t-transparent': !isRefreshing,
                })}
              />
            ) : (
              <div
                className={clsx('w-6 h-6 text-gray-400 transition-transform duration-200', {
                  'transform rotate-180': pullPercentage >= 100,
                })}
              >
                <svg viewBox='0 0 24 24' fill='none' stroke='currentColor' strokeWidth={2}>
                  <path d='M12 5v14M5 12l7-7 7 7' />
                </svg>
              </div>
            )}

            {/* Status text */}
            <div className='text-xs text-gray-500 font-medium'>
              {isRefreshing
                ? 'Refreshing...'
                : pullPercentage >= 100
                  ? 'Release to refresh'
                  : 'Pull to refresh'}
            </div>

            {/* Progress indicator */}
            <div className='w-8 h-1 bg-gray-200 rounded-full overflow-hidden'>
              <div
                className='h-full bg-blue-500 transition-all duration-100'
                style={{ width: `${pullPercentage}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Content container */}
      <div
        ref={containerRef}
        className={clsx(
          'pull-to-refresh-content',
          'overflow-auto',
          'transition-transform',
          'duration-300',
          'ease-out'
        )}
        style={{
          transform: `translateY(${pullDistance}px)`,
        }}
        onScroll={handleScroll}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {children}
      </div>
    </div>
  );
}

// Enhanced styles for pull-to-refresh
PullToRefresh.styles = `
  .pull-to-refresh-container {
    position: relative;
    height: 100%;
    overflow: hidden;
  }

  .pull-to-refresh-content {
    height: 100%;
    overflow: auto;
    -webkit-overflow-scrolling: touch;
    overscroll-behavior-y: contain;
  }

  /* Smooth pull animation */
  .pull-to-refresh-content {
    transition: transform 300ms ease-out;
  }

  /* Prevent text selection during pull */
  .pull-to-refresh-container {
    -webkit-user-select: none;
    -moz-user-select: none;
    user-select: none;
  }

  /* Loading animation */
  @keyframes spin {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  .animate-spin {
    animation: spin 1s linear infinite;
  }

  /* Reduced motion support */
  @media (prefers-reduced-motion: reduce) {
    .pull-to-refresh-content,
    .animate-spin {
      transition: none;
      animation: none;
    }
  }

  /* High contrast mode */
  @media (prefers-contrast: high) {
    .pull-to-refresh-container {
      border: 1px solid;
    }
  }

  /* Dark mode support */
  @media (prefers-color-scheme: dark) {
    .pull-to-refresh-container {
      background-color: #1f2937;
      color: #f9fafb;
    }
  }
`;
