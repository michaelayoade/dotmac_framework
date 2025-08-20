/**
 * Analytics utility functions
 * Mock implementation for testing
 */

export interface AnalyticsEvent {
  event: string;
  properties?: Record<string, unknown>;
}

export interface AnalyticsUser {
  id: string;
  email?: string;
  name?: string;
  role?: string;
  tenant?: string;
}

export const analytics = {
  track: (event: string, properties?: Record<string, unknown>) => {
    // Mock implementation - would integrate with actual analytics service
    if (process.env.NODE_ENV === 'development') {
      console.log('Analytics Track:', event, properties);
    }
  },

  identify: (userId: string, traits?: AnalyticsUser) => {
    // Mock implementation - would integrate with actual analytics service
    if (process.env.NODE_ENV === 'development') {
      console.log('Analytics Identify:', userId, traits);
    }
  },

  page: (pageName?: string, properties?: Record<string, unknown>) => {
    // Mock implementation - would integrate with actual analytics service
    if (process.env.NODE_ENV === 'development') {
      console.log('Analytics Page:', pageName, properties);
    }
  },

  reset: () => {
    // Mock implementation - would clear user session
    if (process.env.NODE_ENV === 'development') {
      console.log('Analytics Reset');
    }
  },
};

// Export individual functions for convenience
export const { track, identify, page, _reset } = analytics;

export default analytics;
