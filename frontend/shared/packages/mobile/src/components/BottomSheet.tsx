/**
 * Bottom Sheet Modal Component
 * Mobile-first modal that slides up from bottom
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { createPortal } from 'react-dom';
import { clsx } from 'clsx';
import { useGestures } from '../gestures/useGestures';

export interface BottomSheetProps {
  isOpen: boolean;
  onClose: () => void;
  children: React.ReactNode;
  title?: string;
  snapPoints?: number[];
  initialSnap?: number;
  backdrop?: boolean;
  closeOnBackdrop?: boolean;
  dragHandle?: boolean;
  maxHeight?: string | number;
  className?: string;
}

export function BottomSheet({
  isOpen,
  onClose,
  children,
  title,
  snapPoints = [0.3, 0.9],
  initialSnap = 0,
  backdrop = true,
  closeOnBackdrop = true,
  dragHandle = true,
  maxHeight = '90vh',
  className,
}: BottomSheetProps) {
  const [currentSnap, setCurrentSnap] = useState(initialSnap);
  const [isAnimating, setIsAnimating] = useState(false);
  const [dragOffset, setDragOffset] = useState(0);
  const sheetRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  // Calculate height based on snap point
  const getHeightFromSnap = useCallback(
    (snapIndex: number) => {
      const snapPoint = snapPoints[snapIndex] || snapPoints[0];
      if (typeof maxHeight === 'string' && maxHeight.includes('vh')) {
        const vhValue = parseInt(maxHeight);
        return `${vhValue * snapPoint}vh`;
      }
      return `${snapPoint * 100}%`;
    },
    [snapPoints, maxHeight]
  );

  // Handle gestures for drag-to-close and snap
  const { ref: gestureRef } = useGestures({
    onSwipeDown: (gesture) => {
      const velocity = gesture.velocity;
      const distance = gesture.distance;

      if (velocity > 0.5 || distance > 100) {
        // Fast swipe down or long drag - close or snap to lower position
        if (currentSnap === 0 || snapPoints.length === 1) {
          onClose();
        } else {
          setCurrentSnap(Math.max(0, currentSnap - 1));
        }
      }
    },
    onSwipeUp: (gesture) => {
      const velocity = gesture.velocity;
      const distance = gesture.distance;

      if (velocity > 0.5 || distance > 100) {
        // Fast swipe up or long drag - snap to higher position
        if (currentSnap < snapPoints.length - 1) {
          setCurrentSnap(currentSnap + 1);
        }
      }
    },
  });

  // Handle backdrop click
  const handleBackdropClick = useCallback(() => {
    if (closeOnBackdrop) {
      onClose();
    }
  }, [closeOnBackdrop, onClose]);

  // Handle escape key
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
      // Prevent body scroll
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  // Animation effect
  useEffect(() => {
    if (isOpen) {
      setIsAnimating(true);
      const timer = setTimeout(() => setIsAnimating(false), 300);
      return () => clearTimeout(timer);
    }
  }, [isOpen, currentSnap]);

  // Reset snap on open
  useEffect(() => {
    if (isOpen) {
      setCurrentSnap(initialSnap);
      setDragOffset(0);
    }
  }, [isOpen, initialSnap]);

  if (!isOpen) return null;

  const currentHeight = getHeightFromSnap(currentSnap);

  return createPortal(
    <div className='fixed inset-0 z-50 flex items-end'>
      {/* Backdrop */}
      {backdrop && (
        <div
          className={clsx(
            'absolute inset-0 bg-black transition-opacity duration-300',
            isAnimating ? 'opacity-0' : 'opacity-50'
          )}
          onClick={handleBackdropClick}
        />
      )}

      {/* Bottom Sheet */}
      <div
        ref={(node) => {
          sheetRef.current = node;
          gestureRef(node);
        }}
        className={clsx(
          'relative w-full bg-white rounded-t-xl shadow-2xl transition-transform duration-300 ease-out',
          {
            'transform translate-y-full': isAnimating && isOpen,
            'transform translate-y-0': !isAnimating && isOpen,
          },
          className
        )}
        style={{
          height: currentHeight,
          transform: dragOffset ? `translateY(${dragOffset}px)` : undefined,
          maxHeight,
        }}
      >
        {/* Drag Handle */}
        {dragHandle && (
          <div className='flex justify-center pt-3 pb-2'>
            <div className='w-8 h-1 bg-gray-300 rounded-full' />
          </div>
        )}

        {/* Header */}
        {title && (
          <div className='flex items-center justify-between px-4 py-3 border-b'>
            <h2 className='text-lg font-semibold text-gray-900'>{title}</h2>
            <button
              onClick={onClose}
              className='p-1 rounded-full hover:bg-gray-100 transition-colors'
              aria-label='Close'
            >
              <svg
                className='w-5 h-5 text-gray-500'
                fill='none'
                stroke='currentColor'
                viewBox='0 0 24 24'
              >
                <path
                  strokeLinecap='round'
                  strokeLinejoin='round'
                  strokeWidth={2}
                  d='M6 18L18 6M6 6l12 12'
                />
              </svg>
            </button>
          </div>
        )}

        {/* Content */}
        <div
          ref={contentRef}
          className='flex-1 overflow-y-auto overscroll-contain'
          style={{
            height: title ? 'calc(100% - 60px)' : dragHandle ? 'calc(100% - 20px)' : '100%',
          }}
        >
          {children}
        </div>

        {/* Snap Indicators */}
        {snapPoints.length > 1 && (
          <div className='absolute right-4 top-1/2 transform -translate-y-1/2 flex flex-col space-y-1'>
            {snapPoints.map((_, index) => (
              <button
                key={index}
                onClick={() => setCurrentSnap(index)}
                className={clsx(
                  'w-2 h-2 rounded-full transition-colors',
                  index === currentSnap ? 'bg-blue-500' : 'bg-gray-300'
                )}
                aria-label={`Snap to position ${index + 1}`}
              />
            ))}
          </div>
        )}
      </div>
    </div>,
    document.body
  );
}

// Enhanced styles for better mobile experience
BottomSheet.styles = `
  .bottom-sheet {
    /* Hardware acceleration */
    transform: translateZ(0);
    will-change: transform;
    
    /* Touch optimization */
    touch-action: pan-y;
    
    /* Smooth scrolling */
    -webkit-overflow-scrolling: touch;
    overscroll-behavior: contain;
  }

  /* Safe area support */
  @supports (padding-bottom: env(safe-area-inset-bottom)) {
    .bottom-sheet {
      padding-bottom: env(safe-area-inset-bottom);
    }
  }

  /* Reduced motion support */
  @media (prefers-reduced-motion: reduce) {
    .bottom-sheet {
      transition: none;
    }
  }

  /* High contrast mode */
  @media (prefers-contrast: high) {
    .bottom-sheet {
      border: 2px solid;
    }
  }

  /* Dark mode support */
  @media (prefers-color-scheme: dark) {
    .bottom-sheet {
      background-color: #1f2937;
      color: #f9fafb;
    }
  }
`;
