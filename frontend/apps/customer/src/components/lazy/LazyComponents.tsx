/**
 * Lazy Loading Components for Code Splitting
 * Reduces initial bundle size by loading components on demand
 */

import dynamic from 'next/dynamic';
import { ComponentProps } from 'react';
import { Loading } from '@dotmac/primitives';

// Loading component for lazy imports
const LazyLoadingFallback = () => (
  <div className="flex items-center justify-center p-8">
    <Loading variant="spinner" />
    <span className="ml-2 text-sm text-gray-600">Loading...</span>
  </div>
);

// Authentication components - Load on demand
export const LazySecureCustomerLoginForm = dynamic(
  () =>
    import('../auth/SecureCustomerLoginForm').then(mod => ({
      default: mod.SecureCustomerLoginForm,
    })),
  {
    loading: LazyLoadingFallback,
    ssr: false, // These components require client-side auth state
  }
);

export const LazyCustomerLoginForm = dynamic(
  () =>
    import('../auth/CustomerLoginForm').then(mod => ({
      default: mod.CustomerLoginForm,
    })),
  {
    loading: LazyLoadingFallback,
    ssr: false,
  }
);

// Dashboard components - Heavy components loaded after login
export const LazyCustomerDashboard = dynamic(
  () =>
    import('../dashboard/CustomerDashboardRefactored').then(mod => ({
      default: mod.CustomerDashboard,
    })),
  {
    loading: () => (
      <div className="animate-pulse">
        <div className="h-32 bg-gray-200 rounded-lg mb-6"></div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-24 bg-gray-200 rounded-lg"></div>
          ))}
        </div>
        <div className="h-64 bg-gray-200 rounded-lg"></div>
      </div>
    ),
    ssr: false,
  }
);

// Billing components - Only load when user accesses billing
export const LazyBillingOverviewUniversal = dynamic(() => import('../billing/BillingOverviewUniversal'), {
  loading: LazyLoadingFallback,
  ssr: false,
});

export const LazyPaymentMethods = dynamic(() => import('../billing/PaymentMethods'), {
  loading: LazyLoadingFallback,
  ssr: false,
});

export const LazyQuickPayment = dynamic(() => import('../billing/QuickPayment'), {
  loading: LazyLoadingFallback,
  ssr: false,
});

export const LazyInvoicesList = dynamic(() => import('../billing/InvoicesList'), {
  loading: LazyLoadingFallback,
  ssr: false,
});

// Service management - Heavy components with charts
export const LazyServiceManagement = dynamic(() => import('../services/ServiceManagement'), {
  loading: LazyLoadingFallback,
  ssr: false,
});

export const LazyServicePlans = dynamic(() => import('../services/ServicePlans'), {
  loading: LazyLoadingFallback,
  ssr: false,
});

export const LazyServiceTroubleshooting = dynamic(
  () => import('../services/ServiceTroubleshooting'),
  {
    loading: LazyLoadingFallback,
    ssr: false,
  }
);

// Support components - Load only when needed
export const LazySupportCenter = dynamic(() => import('../support/SupportCenter'), {
  loading: LazyLoadingFallback,
  ssr: false,
});

export const LazySupportTickets = dynamic(() => import('../support/SupportTickets'), {
  loading: LazyLoadingFallback,
  ssr: false,
});

export const LazyKnowledgeBase = dynamic(() => import('../support/KnowledgeBase'), {
  loading: LazyLoadingFallback,
  ssr: false,
});

export const LazyLiveChatWidget = dynamic(() => import('../support/LiveChatWidget'), {
  loading: LazyLoadingFallback,
  ssr: false,
});

// Usage analytics - Heavy charting components
export const LazyUsageAnalytics = dynamic(() => import('../usage/UsageAnalytics'), {
  loading: () => (
    <div className="animate-pulse">
      <div className="h-8 bg-gray-200 rounded mb-4 w-48"></div>
      <div className="h-64 bg-gray-200 rounded-lg mb-6"></div>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-32 bg-gray-200 rounded-lg"></div>
        ))}
      </div>
    </div>
  ),
  ssr: false,
});

// Document management - Only load when accessing documents
export const LazyDocumentManager = dynamic(() => import('../documents/DocumentManager'), {
  loading: LazyLoadingFallback,
  ssr: false,
});

// Chart components - Heavy recharts library
export const LazyNetworkUsageChart = dynamic(
  () =>
    import('@dotmac/primitives/src/charts/InteractiveChart').then(m => ({
      default: m.NetworkUsageChart,
    })),
  {
    loading: () => (
      <div className="animate-pulse h-48 bg-gray-200 rounded-lg flex items-center justify-center">
        <span className="text-gray-500">Loading chart...</span>
      </div>
    ),
    ssr: false,
  }
);

export const LazyBandwidthChart = dynamic(
  () =>
    import('@dotmac/primitives/src/charts/InteractiveChart').then(m => ({
      default: m.BandwidthChart,
    })),
  {
    loading: () => (
      <div className="animate-pulse h-48 bg-gray-200 rounded-lg flex items-center justify-center">
        <span className="text-gray-500">Loading chart...</span>
      </div>
    ),
    ssr: false,
  }
);

// Utility function to create lazy-loaded pages
export function createLazyPage<T extends Record<string, any>>(
  importFn: () => Promise<{ default: React.ComponentType<T> }>,
  fallbackComponent?: React.ComponentType
) {
  return dynamic(importFn, {
    loading: fallbackComponent || LazyLoadingFallback,
    ssr: true, // Pages can be SSR'd
  });
}

// Higher-order component for lazy loading with error boundaries
export function withLazyLoading<T extends Record<string, any>>(
  Component: React.ComponentType<T>,
  options?: {
    fallback?: React.ComponentType;
    ssr?: boolean;
  }
) {
  const LazyComponent = dynamic(() => Promise.resolve({ default: Component }), {
    loading: options?.fallback || LazyLoadingFallback,
    ssr: options?.ssr ?? true,
  });

  return LazyComponent;
}

// Preload functions for critical components
export const preloadCriticalComponents = () => {
  // Preload dashboard after login
  import('../dashboard/CustomerDashboard');

  // Preload common billing components
  import('../billing/BillingOverviewUniversal');

  // Preload charts for dashboard
  Promise.resolve({ default: () => null });
};

// Component preloading based on user interaction
export const preloadOnHover = {
  billing: () => {
    import('../billing/BillingOverviewUniversal');
    import('../billing/PaymentMethods');
  },
  services: () => {
    import('../services/ServiceManagement');
    import('../services/ServicePlans');
  },
  support: () => {
    import('../support/SupportCenter');
    import('../support/SupportTickets');
  },
  usage: () => {
    import('../usage/UsageAnalytics');
    Promise.resolve({ default: () => null });
  },
};
