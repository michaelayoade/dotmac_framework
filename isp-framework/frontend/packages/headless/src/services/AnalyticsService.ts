/**
 * User Analytics Integration Service
 * 
 * Comprehensive analytics tracking for user behavior, business metrics,
 * and ISP-specific insights across multiple analytics platforms
 */

import { errorTracker } from './ErrorTrackingService';

export interface AnalyticsEvent {
  name: string;
  properties?: Record<string, any>;
  timestamp?: Date;
  userId?: string;
  sessionId?: string;
  tenantId?: string;
  category?: string;
  value?: number;
  currency?: string;
}

export interface UserProfile {
  userId: string;
  tenantId?: string;
  email?: string;
  role?: 'admin' | 'customer' | 'reseller' | 'technician';
  subscriptionPlan?: string;
  accountType?: 'business' | 'residential';
  joinDate?: Date;
  lastLoginDate?: Date;
  totalRevenue?: number;
  serviceCount?: number;
  supportTickets?: number;
  customProperties?: Record<string, any>;
}

export interface BusinessMetrics {
  // Customer metrics
  customerAcquisition?: number;
  customerChurn?: number;
  customerLifetimeValue?: number;
  monthlyRecurringRevenue?: number;
  
  // Service metrics
  serviceUptime?: number;
  serviceActivations?: number;
  serviceDeactivations?: number;
  averageSpeed?: number;
  
  // Support metrics
  supportTicketsCreated?: number;
  supportTicketsResolved?: number;
  averageResolutionTime?: number;
  customerSatisfactionScore?: number;
  
  // Network metrics
  networkUtilization?: number;
  networkOutages?: number;
  maintenanceEvents?: number;
}

export interface PageView {
  path: string;
  title?: string;
  referrer?: string;
  search?: string;
  hash?: string;
  timestamp?: Date;
  loadTime?: number;
  userId?: string;
  tenantId?: string;
  sessionId?: string;
}

export interface AnalyticsConfig {
  // Platform configurations
  googleAnalytics?: {
    measurementId: string;
    enabled: boolean;
  };
  mixpanel?: {
    token: string;
    enabled: boolean;
  };
  amplitude?: {
    apiKey: string;
    enabled: boolean;
  };
  customAnalytics?: {
    endpoint: string;
    apiKey: string;
    enabled: boolean;
  };
  
  // General settings
  enableAutoPageTracking: boolean;
  enablePerformanceTracking: boolean;
  enableErrorTracking: boolean;
  enableBusinessMetrics: boolean;
  enableUserProfiling: boolean;
  samplingRate: number;
  batchSize: number;
  flushInterval: number; // milliseconds
  
  // Privacy settings
  respectDoNotTrack: boolean;
  anonymizeIP: boolean;
  cookieConsent: boolean;
  
  // ISP-specific settings
  trackBandwidthUsage: boolean;
  trackServiceQuality: boolean;
  trackNetworkEvents: boolean;
  trackBillingEvents: boolean;
}

class AnalyticsService {
  private config: AnalyticsConfig;
  private eventQueue: AnalyticsEvent[] = [];
  private userProfile: UserProfile | null = null;
  private sessionId: string;
  private isInitialized = false;
  private flushTimer?: NodeJS.Timeout;
  private pageViewStartTime = 0;

  constructor(config: Partial<AnalyticsConfig> = {}) {
    this.sessionId = this.generateSessionId();
    
    this.config = {
      enableAutoPageTracking: true,
      enablePerformanceTracking: true,
      enableErrorTracking: true,
      enableBusinessMetrics: true,
      enableUserProfiling: true,
      samplingRate: 1.0,
      batchSize: 10,
      flushInterval: 30000, // 30 seconds
      respectDoNotTrack: true,
      anonymizeIP: true,
      cookieConsent: false,
      trackBandwidthUsage: true,
      trackServiceQuality: true,
      trackNetworkEvents: true,
      trackBillingEvents: true,
      ...config,
    };
  }

  async initialize() {
    if (this.isInitialized) return;
    
    // Check if tracking is allowed
    if (!this.isTrackingAllowed()) {
      console.info('Analytics tracking disabled due to privacy settings');
      return;
    }

    // Initialize analytics platforms
    await this.initializeGoogleAnalytics();
    await this.initializeMixpanel();
    await this.initializeAmplitude();

    // Setup auto-tracking
    this.setupAutoPageTracking();
    this.setupPerformanceTracking();
    this.setupErrorTracking();
    this.setupNetworkTracking();
    
    // Start flush timer
    this.startFlushTimer();

    // Track initialization
    this.track('Analytics Initialized', {
      version: '1.0.0',
      platform: 'web',
      userAgent: navigator.userAgent,
    });

    this.isInitialized = true;
  }

  private generateSessionId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  private isTrackingAllowed(): boolean {
    // Check Do Not Track header
    if (this.config.respectDoNotTrack && navigator.doNotTrack === '1') {
      return false;
    }

    // Check cookie consent
    if (this.config.cookieConsent) {
      const consent = localStorage.getItem('analytics_consent');
      return consent === 'true';
    }

    return true;
  }

  private async initializeGoogleAnalytics() {
    const ga = this.config.googleAnalytics;
    if (!ga?.enabled || !ga.measurementId) return;

    try {
      // Load Google Analytics
      const script = document.createElement('script');
      script.async = true;
      script.src = `https://www.googletagmanager.com/gtag/js?id=${ga.measurementId}`;
      document.head.appendChild(script);

      // Initialize gtag
      (window as any).dataLayer = (window as any).dataLayer || [];
      const gtag = (...args: any[]) => (window as any).dataLayer.push(args);
      (window as any).gtag = gtag;

      gtag('js', new Date());
      gtag('config', ga.measurementId, {
        anonymize_ip: this.config.anonymizeIP,
        cookie_flags: 'SameSite=Strict;Secure',
      });
    } catch (error) {
      errorTracker.captureError({
        message: 'Failed to initialize Google Analytics',
        stack: (error as Error).stack,
        severity: 'medium',
      });
    }
  }

  private async initializeMixpanel() {
    const mixpanel = this.config.mixpanel;
    if (!mixpanel?.enabled || !mixpanel.token) return;

    try {
      // Load Mixpanel
      const script = document.createElement('script');
      script.async = true;
      script.src = 'https://cdn.mxpnl.com/libs/mixpanel-2-latest.min.js';
      
      script.onload = () => {
        (window as any).mixpanel.init(mixpanel.token, {
          debug: process.env.NODE_ENV === 'development',
          track_pageview: false, // We handle this manually
          persistence: 'localStorage',
          ip: !this.config.anonymizeIP,
        });
      };

      document.head.appendChild(script);
    } catch (error) {
      errorTracker.captureError({
        message: 'Failed to initialize Mixpanel',
        stack: (error as Error).stack,
        severity: 'medium',
      });
    }
  }

  private async initializeAmplitude() {
    const amplitude = this.config.amplitude;
    if (!amplitude?.enabled || !amplitude.apiKey) return;

    try {
      // Load Amplitude
      const script = document.createElement('script');
      script.async = true;
      script.src = 'https://cdn.amplitude.com/libs/amplitude-8.21.9-min.gz.js';
      
      script.onload = () => {
        (window as any).amplitude.getInstance().init(amplitude.apiKey, undefined, {
          includeGclid: true,
          includeReferrer: true,
          includeUtm: true,
          trackingOptions: {
            ipAddress: !this.config.anonymizeIP,
          },
        });
      };

      document.head.appendChild(script);
    } catch (error) {
      errorTracker.captureError({
        message: 'Failed to initialize Amplitude',
        stack: (error as Error).stack,
        severity: 'medium',
      });
    }
  }

  private setupAutoPageTracking() {
    if (!this.config.enableAutoPageTracking) return;

    // Track initial page view
    this.trackPageView({
      path: window.location.pathname,
      title: document.title,
      referrer: document.referrer,
      search: window.location.search,
      hash: window.location.hash,
    });

    // Track navigation events (for SPAs)
    let lastPath = window.location.pathname;
    
    const trackNavigation = () => {
      const currentPath = window.location.pathname;
      if (currentPath !== lastPath) {
        this.trackPageView({
          path: currentPath,
          title: document.title,
          search: window.location.search,
          hash: window.location.hash,
        });
        lastPath = currentPath;
      }
    };

    // Listen to history changes
    const originalPushState = history.pushState;
    const originalReplaceState = history.replaceState;

    history.pushState = function(...args) {
      originalPushState.apply(history, args);
      setTimeout(trackNavigation, 0);
    };

    history.replaceState = function(...args) {
      originalReplaceState.apply(history, args);
      setTimeout(trackNavigation, 0);
    };

    window.addEventListener('popstate', trackNavigation);
  }

  private setupPerformanceTracking() {
    if (!this.config.enablePerformanceTracking) return;

    // Track page load performance
    window.addEventListener('load', () => {
      setTimeout(() => {
        const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
        
        if (navigation) {
          this.track('Page Performance', {
            loadTime: navigation.loadEventEnd - navigation.fetchStart,
            domContentLoadedTime: navigation.domContentLoadedEventEnd - navigation.fetchStart,
            firstPaint: this.getFirstPaint(),
            firstContentfulPaint: this.getFirstContentfulPaint(),
            timeToInteractive: this.getTimeToInteractive(),
          });
        }
      }, 1000);
    });

    // Track resource performance
    this.trackResourcePerformance();
  }

  private setupErrorTracking() {
    if (!this.config.enableErrorTracking) return;

    // Integration with error tracker
    errorTracker.updateConfig({
      onError: (error) => {
        this.track('Error Occurred', {
          errorType: error.type,
          errorMessage: error.message,
          errorSeverity: error.severity,
          errorFingerprint: error.fingerprint,
          errorCount: error.count,
        });
      },
    });
  }

  private setupNetworkTracking() {
    if (!this.config.trackNetworkEvents) return;

    // Track network status
    const updateNetworkStatus = () => {
      this.track('Network Status', {
        online: navigator.onLine,
        connectionType: (navigator as any).connection?.effectiveType,
        downlink: (navigator as any).connection?.downlink,
        rtt: (navigator as any).connection?.rtt,
      });
    };

    window.addEventListener('online', updateNetworkStatus);
    window.addEventListener('offline', updateNetworkStatus);

    // Initial network status
    updateNetworkStatus();
  }

  private getFirstPaint(): number | undefined {
    const entries = performance.getEntriesByType('paint');
    const fpEntry = entries.find(entry => entry.name === 'first-paint');
    return fpEntry?.startTime;
  }

  private getFirstContentfulPaint(): number | undefined {
    const entries = performance.getEntriesByType('paint');
    const fcpEntry = entries.find(entry => entry.name === 'first-contentful-paint');
    return fcpEntry?.startTime;
  }

  private getTimeToInteractive(): number | undefined {
    // This is a simplified TTI calculation
    // In production, you might want to use a more sophisticated library
    const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
    return navigation ? navigation.domInteractive - navigation.fetchStart : undefined;
  }

  private trackResourcePerformance() {
    const resources = performance.getEntriesByType('resource') as PerformanceResourceTiming[];
    
    resources.forEach(resource => {
      // Track slow loading resources
      if (resource.duration > 1000) { // More than 1 second
        this.track('Slow Resource', {
          resourceName: resource.name,
          resourceType: resource.initiatorType,
          duration: resource.duration,
          size: resource.transferSize,
        });
      }
    });
  }

  track(eventName: string, properties: Record<string, any> = {}) {
    if (!this.isTrackingAllowed() || Math.random() > this.config.samplingRate) {
      return;
    }

    const event: AnalyticsEvent = {
      name: eventName,
      properties: {
        ...properties,
        sessionId: this.sessionId,
        timestamp: new Date().toISOString(),
        userAgent: navigator.userAgent,
        url: window.location.href,
        referrer: document.referrer,
        ...(this.userProfile && {
          userId: this.userProfile.userId,
          tenantId: this.userProfile.tenantId,
          userRole: this.userProfile.role,
        }),
      },
      timestamp: new Date(),
    };

    // Add to queue
    this.eventQueue.push(event);

    // Send to platforms immediately for high-priority events
    const highPriorityEvents = ['Error Occurred', 'Payment Completed', 'Service Activated'];
    if (highPriorityEvents.includes(eventName)) {
      this.sendToAnalyticsPlatforms(event);
    }

    // Flush queue if it's full
    if (this.eventQueue.length >= this.config.batchSize) {
      this.flush();
    }
  }

  trackPageView(pageView: Omit<PageView, 'timestamp' | 'userId' | 'tenantId' | 'sessionId'>) {
    const loadTime = this.pageViewStartTime ? Date.now() - this.pageViewStartTime : undefined;
    this.pageViewStartTime = Date.now();

    const fullPageView: PageView = {
      ...pageView,
      timestamp: new Date(),
      loadTime,
      userId: this.userProfile?.userId,
      tenantId: this.userProfile?.tenantId,
      sessionId: this.sessionId,
    };

    // Send page view to all platforms
    this.sendPageViewToAnalyticsPlatforms(fullPageView);

    // Also track as regular event
    this.track('Page Viewed', {
      path: pageView.path,
      title: pageView.title,
      referrer: pageView.referrer,
      search: pageView.search,
      hash: pageView.hash,
      loadTime,
    });
  }

  identify(userProfile: UserProfile) {
    this.userProfile = userProfile;

    // Send to analytics platforms
    if ((window as any).gtag) {
      (window as any).gtag('config', this.config.googleAnalytics?.measurementId, {
        user_id: userProfile.userId,
        custom_map: {
          custom_dimension_1: userProfile.tenantId,
          custom_dimension_2: userProfile.role,
        },
      });
    }

    if ((window as any).mixpanel) {
      (window as any).mixpanel.identify(userProfile.userId);
      (window as any).mixpanel.people.set({
        $email: userProfile.email,
        $created: userProfile.joinDate,
        tenant_id: userProfile.tenantId,
        role: userProfile.role,
        subscription_plan: userProfile.subscriptionPlan,
        account_type: userProfile.accountType,
        ...userProfile.customProperties,
      });
    }

    if ((window as any).amplitude) {
      (window as any).amplitude.getInstance().setUserId(userProfile.userId);
      (window as any).amplitude.getInstance().identify(
        new (window as any).amplitude.Identify()
          .set('email', userProfile.email)
          .set('tenant_id', userProfile.tenantId)
          .set('role', userProfile.role)
          .set('subscription_plan', userProfile.subscriptionPlan)
          .set('account_type', userProfile.accountType)
      );
    }

    this.track('User Identified', {
      userId: userProfile.userId,
      role: userProfile.role,
      accountType: userProfile.accountType,
    });
  }

  trackBusinessMetrics(metrics: BusinessMetrics) {
    if (!this.config.enableBusinessMetrics) return;

    Object.entries(metrics).forEach(([metric, value]) => {
      if (value !== undefined && value !== null) {
        this.track('Business Metric', {
          metric,
          value,
          timestamp: new Date().toISOString(),
        });
      }
    });
  }

  // ISP-specific tracking methods
  trackServiceEvent(eventType: 'activation' | 'deactivation' | 'upgrade' | 'downgrade', serviceData: any) {
    this.track(`Service ${eventType.charAt(0).toUpperCase() + eventType.slice(1)}`, {
      serviceType: serviceData.type,
      servicePlan: serviceData.plan,
      bandwidth: serviceData.bandwidth,
      monthlyFee: serviceData.monthlyFee,
      ...serviceData,
    });
  }

  trackBillingEvent(eventType: 'invoice_created' | 'payment_received' | 'payment_failed' | 'service_suspended', data: any) {
    if (!this.config.trackBillingEvents) return;

    this.track(`Billing ${eventType.replace('_', ' ')}`, {
      amount: data.amount,
      currency: data.currency,
      paymentMethod: data.paymentMethod,
      ...data,
    });
  }

  trackNetworkEvent(eventType: 'outage' | 'maintenance' | 'speed_test' | 'quality_issue', data: any) {
    if (!this.config.trackNetworkEvents) return;

    this.track(`Network ${eventType.replace('_', ' ')}`, {
      duration: data.duration,
      affectedServices: data.affectedServices,
      region: data.region,
      severity: data.severity,
      ...data,
    });
  }

  trackSupportEvent(eventType: 'ticket_created' | 'ticket_resolved' | 'chat_started' | 'call_initiated', data: any) {
    this.track(`Support ${eventType.replace('_', ' ')}`, {
      category: data.category,
      priority: data.priority,
      channel: data.channel,
      resolutionTime: data.resolutionTime,
      satisfaction: data.satisfaction,
      ...data,
    });
  }

  private sendToAnalyticsPlatforms(event: AnalyticsEvent) {
    // Google Analytics
    if ((window as any).gtag) {
      (window as any).gtag('event', event.name, {
        ...event.properties,
        value: event.value,
      });
    }

    // Mixpanel
    if ((window as any).mixpanel) {
      (window as any).mixpanel.track(event.name, event.properties);
    }

    // Amplitude
    if ((window as any).amplitude) {
      (window as any).amplitude.getInstance().logEvent(event.name, event.properties);
    }

    // Custom analytics
    if (this.config.customAnalytics?.enabled) {
      this.sendToCustomAnalytics(event);
    }
  }

  private sendPageViewToAnalyticsPlatforms(pageView: PageView) {
    // Google Analytics
    if ((window as any).gtag) {
      (window as any).gtag('config', this.config.googleAnalytics?.measurementId, {
        page_path: pageView.path,
        page_title: pageView.title,
      });
    }

    // Mixpanel
    if ((window as any).mixpanel) {
      (window as any).mixpanel.track_pageview({
        path: pageView.path,
        title: pageView.title,
        referrer: pageView.referrer,
      });
    }

    // Amplitude
    if ((window as any).amplitude) {
      (window as any).amplitude.getInstance().logEvent('Page Viewed', {
        path: pageView.path,
        title: pageView.title,
        referrer: pageView.referrer,
        loadTime: pageView.loadTime,
      });
    }
  }

  private async sendToCustomAnalytics(event: AnalyticsEvent) {
    if (!this.config.customAnalytics?.endpoint) return;

    try {
      await fetch(this.config.customAnalytics.endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.config.customAnalytics.apiKey}`,
        },
        body: JSON.stringify(event),
      });
    } catch (error) {
      errorTracker.captureError({
        message: 'Failed to send analytics event to custom endpoint',
        stack: (error as Error).stack,
        severity: 'low',
      });
    }
  }

  private startFlushTimer() {
    this.flushTimer = setInterval(() => {
      this.flush();
    }, this.config.flushInterval);
  }

  flush() {
    if (this.eventQueue.length === 0) return;

    const events = [...this.eventQueue];
    this.eventQueue = [];

    // Send events to all platforms
    events.forEach(event => {
      this.sendToAnalyticsPlatforms(event);
    });
  }

  setConsent(hasConsent: boolean) {
    try {
      localStorage.setItem('analytics_consent', hasConsent.toString());
      
      if (hasConsent && !this.isInitialized) {
        this.initialize();
      } else if (!hasConsent && this.isInitialized) {
        this.destroy();
      }
    } catch (error) {
      // Storage might not be available
    }
  }

  destroy() {
    // Clear timers
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }

    // Flush remaining events
    this.flush();

    // Reset state
    this.eventQueue = [];
    this.userProfile = null;
    this.isInitialized = false;
  }
}

// Global analytics service instance
export const analytics = new AnalyticsService();

// React hook for analytics
export function useAnalytics() {
  const track = (eventName: string, properties?: Record<string, any>) => {
    analytics.track(eventName, properties);
  };

  const identify = (userProfile: UserProfile) => {
    analytics.identify(userProfile);
  };

  const trackPageView = (path?: string) => {
    analytics.trackPageView({
      path: path || window.location.pathname,
      title: document.title,
      referrer: document.referrer,
      search: window.location.search,
      hash: window.location.hash,
    });
  };

  return {
    track,
    identify,
    trackPageView,
    analytics,
  };
}

export default AnalyticsService;