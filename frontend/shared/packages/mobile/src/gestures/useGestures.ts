/**
 * React Hook for Gesture Management
 */

import { useEffect, useRef, useCallback } from 'react';
import { GestureManager, GestureCallbacks } from './GestureManager';

export interface UseGesturesOptions {
  swipe?: {
    threshold?: number;
    velocity?: number;
    maxAngle?: number;
  };
  pinch?: {
    threshold?: number;
    minScale?: number;
    maxScale?: number;
  };
  longPress?: {
    duration?: number;
    threshold?: number;
  };
}

export function useGestures(callbacks: GestureCallbacks, options: UseGesturesOptions = {}) {
  const gestureManagerRef = useRef<GestureManager | null>(null);
  const elementRef = useRef<HTMLElement | null>(null);

  const attachToElement = useCallback(
    (element: HTMLElement | null) => {
      if (gestureManagerRef.current) {
        gestureManagerRef.current.destroy();
        gestureManagerRef.current = null;
      }

      if (element) {
        elementRef.current = element;
        gestureManagerRef.current = new GestureManager(element, callbacks, options);
      }
    },
    [callbacks, options]
  );

  const updateCallbacks = useCallback((newCallbacks: Partial<GestureCallbacks>) => {
    if (gestureManagerRef.current) {
      gestureManagerRef.current.updateCallbacks(newCallbacks);
    }
  }, []);

  useEffect(() => {
    return () => {
      if (gestureManagerRef.current) {
        gestureManagerRef.current.destroy();
      }
    };
  }, []);

  return {
    attachToElement,
    updateCallbacks,
    ref: attachToElement,
  };
}
