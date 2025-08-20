import { useEffect, useCallback } from 'react';

interface AnalyticsEvent {
  name: string;
  properties?: Record<string, any>;
  timestamp?: number;
}

interface PageView {
  path: string;
  title?: string;
  referrer?: string;
}

export function useAnalytics() {
  const track = useCallback((event: AnalyticsEvent) => {
    // Add timestamp if not provided
    const eventWithTimestamp = {
      ...event,
      timestamp: event.timestamp || Date.now(),
    };

    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.log('[Analytics] Event:', eventWithTimestamp);
    }

    // Send to analytics service in production
    if (typeof window !== 'undefined' && window.gtag) {
      window.gtag('event', event.name, {
        event_category: 'engagement',
        ...event.properties,
      });
    }

    // Send to custom analytics endpoint
    if (process.env.NEXT_PUBLIC_ANALYTICS_ENDPOINT) {
      fetch(process.env.NEXT_PUBLIC_ANALYTICS_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(eventWithTimestamp),
      }).catch(console.error);
    }
  }, []);

  const pageView = useCallback((page: PageView) => {
    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.log('[Analytics] Page View:', page);
    }

    // Send to Google Analytics
    if (typeof window !== 'undefined' && window.gtag) {
      window.gtag('config', process.env.NEXT_PUBLIC_GA_ID, {
        page_path: page.path,
        page_title: page.title,
      });
    }
  }, []);

  const identify = useCallback((userId: string, traits?: Record<string, any>) => {
    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.log('[Analytics] Identify:', { userId, traits });
    }

    // Set user ID for Google Analytics
    if (typeof window !== 'undefined' && window.gtag) {
      window.gtag('config', process.env.NEXT_PUBLIC_GA_ID, {
        user_id: userId,
      });
    }

    // Store user traits for future events
    if (typeof window !== 'undefined') {
      window.localStorage.setItem('analytics_user_id', userId);
      if (traits) {
        window.localStorage.setItem('analytics_user_traits', JSON.stringify(traits));
      }
    }
  }, []);

  const timing = useCallback((category: string, variable: string, value: number, label?: string) => {
    // Log to console in development
    if (process.env.NODE_ENV === 'development') {
      console.log('[Analytics] Timing:', { category, variable, value, label });
    }

    // Send to Google Analytics
    if (typeof window !== 'undefined' && window.gtag) {
      window.gtag('event', 'timing_complete', {
        event_category: category,
        name: variable,
        value,
        event_label: label,
      });
    }
  }, []);

  // Auto-track page views
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const handleRouteChange = () => {
        pageView({
          path: window.location.pathname,
          title: document.title,
          referrer: document.referrer,
        });
      };

      // Track initial page view
      handleRouteChange();

      // Listen for route changes
      window.addEventListener('popstate', handleRouteChange);

      return () => {
        window.removeEventListener('popstate', handleRouteChange);
      };
    }
  }, [pageView]);

  return {
    track,
    pageView,
    identify,
    timing,
  };
}

// Web Vitals tracking
export function reportWebVitals(metric: any) {
  if (process.env.NODE_ENV === 'development') {
    console.log('[Web Vitals]', metric);
  }

  // Send to Google Analytics
  if (typeof window !== 'undefined' && window.gtag) {
    window.gtag('event', metric.name, {
      event_category: 'Web Vitals',
      event_label: metric.id,
      value: Math.round(metric.name === 'CLS' ? metric.value * 1000 : metric.value),
      non_interaction: true,
    });
  }

  // Send to custom endpoint
  if (process.env.NEXT_PUBLIC_VITALS_ENDPOINT) {
    fetch(process.env.NEXT_PUBLIC_VITALS_ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(metric),
    }).catch(console.error);
  }
}

// TypeScript declarations for window.gtag
declare global {
  interface Window {
    gtag?: (...args: any[]) => void;
  }
}