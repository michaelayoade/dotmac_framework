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
export declare class UIEventTracker {
  private sessionId;
  private userId?;
  private portal?;
  private eventBuffer;
  private performanceMarks;
  private flushInterval;
  private maxBufferSize;
  private flushTimer?;
  constructor(options?: {
    userId?: string;
    portal?: string;
    flushInterval?: number;
    maxBufferSize?: number;
  });
  /**
   * Track page view event
   */
  trackPageView(page: string, properties?: Record<string, any>): void;
  /**
   * Track user action event
   */
  trackAction(action: string, component?: string, properties?: Record<string, any>): void;
  /**
   * Track specific UI actions with predefined types
   */
  trackClick(element: string, properties?: Record<string, any>): void;
  trackSubmit(form: string, properties?: Record<string, any>): void;
  trackSearch(query: string, component: string, properties?: Record<string, any>): void;
  trackFilter(filter: string, value: any, component: string): void;
  trackExport(format: string, component: string, recordCount?: number): void;
  trackNavigation(from: string, to: string, method?: 'click' | 'programmatic'): void;
  /**
   * Track form interactions
   */
  trackFormStart(formName: string): void;
  trackFormComplete(formName: string, duration?: number): void;
  trackFormError(formName: string, error: string): void;
  /**
   * Track performance events
   */
  markPerformance(name: string, metadata?: Record<string, any>): void;
  /**
   * Measure performance between two marks
   */
  measurePerformance(measureName: string, startMark: string, endMark?: string): number | null;
  /**
   * Track API call performance
   */
  trackAPICall(endpoint: string, method: string, duration: number, status: number): void;
  /**
   * Track error events
   */
  trackError(error: Error | string, context?: Record<string, any>): void;
  /**
   * Emit event to monitoring system
   */
  private emitEvent;
  /**
   * Buffer event for batch sending
   */
  private bufferEvent;
  /**
   * Flush buffered events
   */
  flush(): void;
  /**
   * Send events to monitoring endpoint
   */
  private sendEvents;
  /**
   * Start automatic flush timer
   */
  private startFlushTimer;
  /**
   * Setup page unload handler to flush remaining events
   */
  private setupPageUnloadHandler;
  /**
   * Generate unique session ID
   */
  private generateSessionId;
  /**
   * Update user ID
   */
  setUserId(userId: string): void;
  /**
   * Get current session ID
   */
  getSessionId(): string;
  /**
   * Get performance marks
   */
  getPerformanceMarks(): PerformanceMark[];
  /**
   * Clear performance marks
   */
  clearPerformanceMarks(): void;
  /**
   * Destroy tracker and clean up
   */
  destroy(): void;
}
/**
 * Get or create global UI event tracker
 */
export declare function getUIEventTracker(options?: {
  userId?: string;
  portal?: string;
  flushInterval?: number;
  maxBufferSize?: number;
}): UIEventTracker;
/**
 * Convenience functions for common tracking patterns
 */
export declare const trackPageView: (page: string, properties?: Record<string, any>) => void;
export declare const trackAction: (
  action: string,
  component?: string,
  properties?: Record<string, any>
) => void;
export declare const markPerformance: (name: string, metadata?: Record<string, any>) => void;
export declare const measurePerformance: (
  measureName: string,
  startMark: string,
  endMark?: string
) => number | null;
export declare const trackError: (error: Error | string, context?: Record<string, any>) => void;
//# sourceMappingURL=UIEventTracker.d.ts.map
