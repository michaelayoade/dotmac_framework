/**
 * UI Event Tracker
 * Emit ui.page.view, ui.action.* events with performance marks
 */

export interface UIEvent {
  type: string;
  page?: string;
  component?: string;
  action?: string;
  properties?: Record<string, any>;
  timestamp: string;
  sessionId: string;
  userId?: string;
  portal?: string;
}

export interface PerformanceMark {
  name: string;
  timestamp: number;
  duration?: number;
  metadata?: Record<string, any>;
}

export class UIEventTracker {
  private sessionId: string;
  private userId?: string;
  private portal?: string;
  private eventBuffer: UIEvent[] = [];
  private performanceMarks: PerformanceMark[] = [];
  private flushInterval: number = 10000; // 10 seconds
  private maxBufferSize: number = 100;
  private flushTimer?: NodeJS.Timeout;

  constructor(options?: {
    userId?: string;
    portal?: string;
    flushInterval?: number;
    maxBufferSize?: number;
  }) {
    this.sessionId = this.generateSessionId();
    this.userId = options?.userId;
    this.portal = options?.portal;
    this.flushInterval = options?.flushInterval || this.flushInterval;
    this.maxBufferSize = options?.maxBufferSize || this.maxBufferSize;

    this.startFlushTimer();
    this.setupPageUnloadHandler();
  }

  /**
   * Track page view event
   */
  trackPageView(page: string, properties?: Record<string, any>): void {
    const event: UIEvent = {
      type: 'ui.page.view',
      page,
      properties: {
        ...properties,
        referrer: document.referrer,
        userAgent: navigator.userAgent,
        viewport: {
          width: window.innerWidth,
          height: window.innerHeight,
        },
        url: window.location.href,
      },
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId,
      userId: this.userId,
      portal: this.portal,
    };

    this.emitEvent(event);
    this.bufferEvent(event);

    // Add performance mark
    this.markPerformance(`page-view-${page}`, {
      page,
      portal: this.portal,
    });
  }

  /**
   * Track user action event
   */
  trackAction(action: string, component?: string, properties?: Record<string, any>): void {
    const event: UIEvent = {
      type: `ui.action.${action}`,
      action,
      component,
      properties,
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId,
      userId: this.userId,
      portal: this.portal,
    };

    this.emitEvent(event);
    this.bufferEvent(event);

    // Add performance mark for significant actions
    if (['click', 'submit', 'search', 'filter', 'export'].includes(action)) {
      this.markPerformance(`action-${action}`, {
        action,
        component,
        portal: this.portal,
      });
    }
  }

  /**
   * Track specific UI actions with predefined types
   */
  trackClick(element: string, properties?: Record<string, any>): void {
    this.trackAction('click', element, properties);
  }

  trackSubmit(form: string, properties?: Record<string, any>): void {
    this.trackAction('submit', form, properties);
  }

  trackSearch(query: string, component: string, properties?: Record<string, any>): void {
    this.trackAction('search', component, {
      ...properties,
      query: query.length > 100 ? `${query.substring(0, 100)}...` : query,
      queryLength: query.length,
    });
  }

  trackFilter(filter: string, value: any, component: string): void {
    this.trackAction('filter', component, {
      filter,
      value,
      filterType: typeof value,
    });
  }

  trackExport(format: string, component: string, recordCount?: number): void {
    this.trackAction('export', component, {
      format,
      recordCount,
      timestamp: new Date().toISOString(),
    });
  }

  trackNavigation(from: string, to: string, method: 'click' | 'programmatic' = 'click'): void {
    this.trackAction('navigation', 'router', {
      from,
      to,
      method,
    });
  }

  /**
   * Track form interactions
   */
  trackFormStart(formName: string): void {
    this.markPerformance(`form-start-${formName}`);
    this.trackAction('form-start', formName);
  }

  trackFormComplete(formName: string, duration?: number): void {
    this.markPerformance(`form-complete-${formName}`, { duration });
    this.trackAction('form-complete', formName, { duration });
  }

  trackFormError(formName: string, error: string): void {
    this.trackAction('form-error', formName, { error });
  }

  /**
   * Track performance events
   */
  markPerformance(name: string, metadata?: Record<string, any>): void {
    const timestamp = performance.now();

    // Use Performance API if available
    if (typeof performance !== 'undefined' && performance.mark) {
      performance.mark(name);
    }

    const mark: PerformanceMark = {
      name,
      timestamp,
      metadata,
    };

    this.performanceMarks.push(mark);

    // Emit performance event
    this.emitEvent({
      type: 'ui.performance.mark',
      properties: {
        markName: name,
        timestamp,
        ...metadata,
      },
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId,
      userId: this.userId,
      portal: this.portal,
    });
  }

  /**
   * Measure performance between two marks
   */
  measurePerformance(measureName: string, startMark: string, endMark?: string): number | null {
    try {
      if (typeof performance !== 'undefined' && performance.measure) {
        const measure = endMark
          ? performance.measure(measureName, startMark, endMark)
          : performance.measure(measureName, startMark);

        const duration = measure.duration;

        // Emit performance measurement
        this.emitEvent({
          type: 'ui.performance.measure',
          properties: {
            measureName,
            startMark,
            endMark,
            duration,
          },
          timestamp: new Date().toISOString(),
          sessionId: this.sessionId,
          userId: this.userId,
          portal: this.portal,
        });

        return duration;
      }
    } catch (error) {
      console.warn('Performance measurement failed:', error);
    }

    return null;
  }

  /**
   * Track API call performance
   */
  trackAPICall(endpoint: string, method: string, duration: number, status: number): void {
    this.emitEvent({
      type: 'ui.api.call',
      properties: {
        endpoint,
        method,
        duration,
        status,
        success: status >= 200 && status < 400,
      },
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId,
      userId: this.userId,
      portal: this.portal,
    });
  }

  /**
   * Track error events
   */
  trackError(error: Error | string, context?: Record<string, any>): void {
    const errorDetails =
      error instanceof Error
        ? {
            name: error.name,
            message: error.message,
            stack: error.stack,
          }
        : {
            message: error,
          };

    this.emitEvent({
      type: 'ui.error',
      properties: {
        ...errorDetails,
        context,
        url: window.location.href,
        userAgent: navigator.userAgent,
      },
      timestamp: new Date().toISOString(),
      sessionId: this.sessionId,
      userId: this.userId,
      portal: this.portal,
    });
  }

  /**
   * Emit event to monitoring system
   */
  private emitEvent(event: UIEvent): void {
    // Emit as custom DOM event for immediate listeners
    const customEvent = new CustomEvent(event.type, {
      detail: event,
    });
    window.dispatchEvent(customEvent);

    // If monitoring package is available, send to it
    if (typeof window !== 'undefined' && (window as any).monitoring) {
      (window as any).monitoring.track(event);
    }
  }

  /**
   * Buffer event for batch sending
   */
  private bufferEvent(event: UIEvent): void {
    this.eventBuffer.push(event);

    // Flush if buffer is full
    if (this.eventBuffer.length >= this.maxBufferSize) {
      this.flush();
    }
  }

  /**
   * Flush buffered events
   */
  flush(): void {
    if (this.eventBuffer.length === 0) return;

    const events = [...this.eventBuffer];
    this.eventBuffer = [];

    // Send to monitoring endpoint
    this.sendEvents(events);
  }

  /**
   * Send events to monitoring endpoint
   */
  private async sendEvents(events: UIEvent[]): Promise<void> {
    try {
      const response = await fetch('/api/monitoring/events', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          events,
          metadata: {
            sessionId: this.sessionId,
            portal: this.portal,
            timestamp: new Date().toISOString(),
          },
        }),
        // Use sendBeacon for page unload if available
        keepalive: true,
      });

      if (!response.ok) {
        console.warn('Failed to send UI events:', response.statusText);
      }
    } catch (error) {
      console.warn('Error sending UI events:', error);

      // Fallback: use sendBeacon if available
      if ('navigator' in window && 'sendBeacon' in navigator) {
        navigator.sendBeacon('/api/monitoring/events', JSON.stringify({ events }));
      }
    }
  }

  /**
   * Start automatic flush timer
   */
  private startFlushTimer(): void {
    this.flushTimer = setInterval(() => {
      this.flush();
    }, this.flushInterval);
  }

  /**
   * Setup page unload handler to flush remaining events
   */
  private setupPageUnloadHandler(): void {
    const handleUnload = () => {
      this.flush();
    };

    window.addEventListener('beforeunload', handleUnload);
    window.addEventListener('pagehide', handleUnload);
  }

  /**
   * Generate unique session ID
   */
  private generateSessionId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Update user ID
   */
  setUserId(userId: string): void {
    this.userId = userId;
  }

  /**
   * Get current session ID
   */
  getSessionId(): string {
    return this.sessionId;
  }

  /**
   * Get performance marks
   */
  getPerformanceMarks(): PerformanceMark[] {
    return [...this.performanceMarks];
  }

  /**
   * Clear performance marks
   */
  clearPerformanceMarks(): void {
    this.performanceMarks = [];

    if (typeof performance !== 'undefined' && performance.clearMarks) {
      performance.clearMarks();
    }
  }

  /**
   * Destroy tracker and clean up
   */
  destroy(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }

    this.flush(); // Final flush
    this.eventBuffer = [];
    this.performanceMarks = [];
  }
}

// Global tracker instance
let globalTracker: UIEventTracker | null = null;

/**
 * Get or create global UI event tracker
 */
export function getUIEventTracker(options?: {
  userId?: string;
  portal?: string;
  flushInterval?: number;
  maxBufferSize?: number;
}): UIEventTracker {
  if (!globalTracker) {
    globalTracker = new UIEventTracker(options);
  }

  return globalTracker;
}

/**
 * Convenience functions for common tracking patterns
 */
export const trackPageView = (page: string, properties?: Record<string, any>) => {
  getUIEventTracker().trackPageView(page, properties);
};

export const trackAction = (
  action: string,
  component?: string,
  properties?: Record<string, any>
) => {
  getUIEventTracker().trackAction(action, component, properties);
};

export const markPerformance = (name: string, metadata?: Record<string, any>) => {
  getUIEventTracker().markPerformance(name, metadata);
};

export const measurePerformance = (measureName: string, startMark: string, endMark?: string) => {
  return getUIEventTracker().measurePerformance(measureName, startMark, endMark);
};

export const trackError = (error: Error | string, context?: Record<string, any>) => {
  getUIEventTracker().trackError(error, context);
};
