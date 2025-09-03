/**
 * Advanced Gesture Manager
 * Handles complex touch gestures for mobile interactions
 */

export interface GestureState {
  startX: number;
  startY: number;
  currentX: number;
  currentY: number;
  deltaX: number;
  deltaY: number;
  distance: number;
  angle: number;
  velocity: number;
  timestamp: number;
}

export interface SwipeGestureOptions {
  threshold: number;
  velocity: number;
  maxAngle: number;
}

export interface PinchGestureOptions {
  threshold: number;
  minScale: number;
  maxScale: number;
}

export interface LongPressGestureOptions {
  duration: number;
  threshold: number;
}

export interface GestureCallbacks {
  onSwipeLeft?: (gesture: GestureState) => void;
  onSwipeRight?: (gesture: GestureState) => void;
  onSwipeUp?: (gesture: GestureState) => void;
  onSwipeDown?: (gesture: GestureState) => void;
  onPinchStart?: (gesture: GestureState) => void;
  onPinchMove?: (gesture: GestureState, scale: number) => void;
  onPinchEnd?: (gesture: GestureState, scale: number) => void;
  onLongPress?: (gesture: GestureState) => void;
  onTap?: (gesture: GestureState) => void;
  onDoubleTap?: (gesture: GestureState) => void;
}

export class GestureManager {
  private element: HTMLElement;
  private callbacks: GestureCallbacks = {};
  private options: {
    swipe: SwipeGestureOptions;
    pinch: PinchGestureOptions;
    longPress: LongPressGestureOptions;
  };

  private touches: Touch[] = [];
  private gestureState: GestureState | null = null;
  private longPressTimeout: NodeJS.Timeout | null = null;
  private lastTapTime = 0;
  private pinchStartDistance = 0;
  private currentScale = 1;

  constructor(
    element: HTMLElement,
    callbacks: GestureCallbacks = {},
    options: Partial<{
      swipe: SwipeGestureOptions;
      pinch: PinchGestureOptions;
      longPress: LongPressGestureOptions;
    }> = {}
  ) {
    this.element = element;
    this.callbacks = callbacks;
    this.options = {
      swipe: {
        threshold: 50,
        velocity: 0.3,
        maxAngle: 30,
        ...options.swipe,
      },
      pinch: {
        threshold: 10,
        minScale: 0.1,
        maxScale: 10,
        ...options.pinch,
      },
      longPress: {
        duration: 500,
        threshold: 10,
        ...options.longPress,
      },
    };

    this.initialize();
  }

  private initialize(): void {
    this.element.addEventListener('touchstart', this.handleTouchStart.bind(this), {
      passive: false,
    });
    this.element.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
    this.element.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: false });
    this.element.addEventListener('touchcancel', this.handleTouchCancel.bind(this), {
      passive: false,
    });

    // Prevent default touch behaviors
    this.element.style.touchAction = 'none';
    this.element.style.userSelect = 'none';
  }

  private handleTouchStart(event: TouchEvent): void {
    this.touches = Array.from(event.touches);
    const touch = this.touches[0];

    if (this.touches.length === 1) {
      // Single touch
      this.gestureState = {
        startX: touch.clientX,
        startY: touch.clientY,
        currentX: touch.clientX,
        currentY: touch.clientY,
        deltaX: 0,
        deltaY: 0,
        distance: 0,
        angle: 0,
        velocity: 0,
        timestamp: Date.now(),
      };

      // Start long press detection
      this.longPressTimeout = setTimeout(() => {
        if (this.gestureState && this.callbacks.onLongPress) {
          this.triggerHaptic('medium');
          this.callbacks.onLongPress(this.gestureState);
        }
      }, this.options.longPress.duration);
    } else if (this.touches.length === 2) {
      // Pinch gesture
      this.clearLongPressTimeout();
      this.pinchStartDistance = this.getDistance(this.touches[0], this.touches[1]);
      this.currentScale = 1;

      if (this.callbacks.onPinchStart && this.gestureState) {
        this.callbacks.onPinchStart(this.gestureState);
      }
    }
  }

  private handleTouchMove(event: TouchEvent): void {
    if (!this.gestureState) return;

    this.touches = Array.from(event.touches);

    if (this.touches.length === 1) {
      // Single touch move
      const touch = this.touches[0];
      const deltaX = touch.clientX - this.gestureState.startX;
      const deltaY = touch.clientY - this.gestureState.startY;
      const distance = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

      this.gestureState = {
        ...this.gestureState,
        currentX: touch.clientX,
        currentY: touch.clientY,
        deltaX,
        deltaY,
        distance,
        angle: Math.atan2(deltaY, deltaX) * (180 / Math.PI),
        velocity: distance / (Date.now() - this.gestureState.timestamp),
      };

      // Cancel long press if moved too much
      if (distance > this.options.longPress.threshold) {
        this.clearLongPressTimeout();
      }
    } else if (this.touches.length === 2) {
      // Pinch gesture
      const currentDistance = this.getDistance(this.touches[0], this.touches[1]);
      const scale = currentDistance / this.pinchStartDistance;

      this.currentScale = Math.max(
        this.options.pinch.minScale,
        Math.min(this.options.pinch.maxScale, scale)
      );

      if (this.callbacks.onPinchMove) {
        this.callbacks.onPinchMove(this.gestureState, this.currentScale);
      }

      // Prevent default pinch-to-zoom
      event.preventDefault();
    }
  }

  private handleTouchEnd(event: TouchEvent): void {
    if (!this.gestureState) return;

    this.clearLongPressTimeout();
    this.touches = Array.from(event.touches);

    if (this.touches.length === 0) {
      // All touches ended
      if (this.currentScale !== 1) {
        // End pinch gesture
        if (this.callbacks.onPinchEnd) {
          this.callbacks.onPinchEnd(this.gestureState, this.currentScale);
        }
        this.currentScale = 1;
      } else {
        // Check for swipe or tap
        this.handleGestureEnd();
      }

      this.gestureState = null;
    } else if (this.touches.length === 1) {
      // One finger lifted from pinch
      if (this.callbacks.onPinchEnd) {
        this.callbacks.onPinchEnd(this.gestureState, this.currentScale);
      }
    }
  }

  private handleTouchCancel(): void {
    this.clearLongPressTimeout();
    this.gestureState = null;
    this.currentScale = 1;
  }

  private handleGestureEnd(): void {
    if (!this.gestureState) return;

    const { distance, velocity, angle, deltaX, deltaY } = this.gestureState;

    // Check for swipe
    if (distance > this.options.swipe.threshold && velocity > this.options.swipe.velocity) {
      const absAngle = Math.abs(angle);

      if (
        absAngle <= this.options.swipe.maxAngle ||
        absAngle >= 180 - this.options.swipe.maxAngle
      ) {
        // Horizontal swipe
        if (deltaX > 0) {
          this.callbacks.onSwipeRight?.(this.gestureState);
        } else {
          this.callbacks.onSwipeLeft?.(this.gestureState);
        }
      } else if (
        absAngle >= 90 - this.options.swipe.maxAngle &&
        absAngle <= 90 + this.options.swipe.maxAngle
      ) {
        // Vertical swipe
        if (deltaY > 0) {
          this.callbacks.onSwipeDown?.(this.gestureState);
        } else {
          this.callbacks.onSwipeUp?.(this.gestureState);
        }
      }
    } else if (distance < 10) {
      // Tap gesture
      const currentTime = Date.now();
      const timeDiff = currentTime - this.lastTapTime;

      if (timeDiff < 300) {
        // Double tap
        this.callbacks.onDoubleTap?.(this.gestureState);
      } else {
        // Single tap
        setTimeout(() => {
          if (Date.now() - this.lastTapTime >= 300) {
            this.callbacks.onTap?.(this.gestureState);
          }
        }, 300);
      }

      this.lastTapTime = currentTime;
    }
  }

  private getDistance(touch1: Touch, touch2: Touch): number {
    const dx = touch1.clientX - touch2.clientX;
    const dy = touch1.clientY - touch2.clientY;
    return Math.sqrt(dx * dx + dy * dy);
  }

  private clearLongPressTimeout(): void {
    if (this.longPressTimeout) {
      clearTimeout(this.longPressTimeout);
      this.longPressTimeout = null;
    }
  }

  private triggerHaptic(type: 'light' | 'medium' | 'heavy'): void {
    if ('vibrate' in navigator) {
      const patterns = {
        light: [10],
        medium: [20],
        heavy: [30],
      };
      navigator.vibrate(patterns[type]);
    }
  }

  public destroy(): void {
    this.element.removeEventListener('touchstart', this.handleTouchStart.bind(this));
    this.element.removeEventListener('touchmove', this.handleTouchMove.bind(this));
    this.element.removeEventListener('touchend', this.handleTouchEnd.bind(this));
    this.element.removeEventListener('touchcancel', this.handleTouchCancel.bind(this));

    this.clearLongPressTimeout();
  }

  public updateCallbacks(callbacks: Partial<GestureCallbacks>): void {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }
}
