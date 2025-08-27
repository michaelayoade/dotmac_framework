/**
 * Lazy-loaded Components
 * Pre-configured lazy components for optimal loading
 */

'use client';

import React, { Suspense } from 'react';
import { createLazyComponent, createSafeLazyComponent, getLoadingStrategy } from '@/lib/code-splitting';
import { AccessibleLoadingSpinner } from '@/components/ui/AccessibleForm';

// ============================================================================
// LOADING FALLBACKS
// ============================================================================

const PageLoadingFallback = () => (
  <div className="min-h-screen flex items-center justify-center bg-gray-50">
    <div className="text-center">
      <AccessibleLoadingSpinner size="lg" />
      <div className="mt-4 text-lg text-gray-600">Loading page...</div>
    </div>
  </div>
);

const SectionLoadingFallback = () => (
  <div className="flex items-center justify-center p-8">
    <div className="text-center">
      <AccessibleLoadingSpinner size="md" />
      <div className="mt-2 text-sm text-gray-600">Loading section...</div>
    </div>
  </div>
);

const ComponentLoadingFallback = () => (
  <div className="flex items-center justify-center p-4">
    <AccessibleLoadingSpinner size="sm" />
  </div>
);

// ============================================================================
// DASHBOARD COMPONENTS
// ============================================================================

export const LazyDashboardOverview = createSafeLazyComponent(
  () => import('@/components/dashboard/DashboardOverview'),
  { 
    preload: getLoadingStrategy() === 'aggressive',
    fallback: <SectionLoadingFallback />
  }
);

export const LazyDashboardStats = createSafeLazyComponent(
  () => import('@/components/dashboard/DashboardStats'),
  { 
    preload: true,
    fallback: <ComponentLoadingFallback />
  }
);

export const LazyDashboardCharts = createSafeLazyComponent(
  () => import('@/components/dashboard/DashboardCharts'),
  { 
    preload: getLoadingStrategy() !== 'minimal',
    fallback: <SectionLoadingFallback />
  }
);

// TODO: Component not yet implemented
// export const LazyRecentActivity = createSafeLazyComponent(
//   () => import('@/components/dashboard/RecentActivity'),
//   { 
//     fallback: <ComponentLoadingFallback />
//   }
// );

// ============================================================================
// TENANT MANAGEMENT COMPONENTS
// ============================================================================

// TODO: Component not yet implemented
// export const LazyTenantList = createSafeLazyComponent(
//   () => import('@/components/tenants/TenantList'),
//   { 
//     fallback: <SectionLoadingFallback />
//   }
// );

// TODO: Component not yet implemented
// export const LazyTenantForm = createSafeLazyComponent(
//   () => import('@/components/tenants/TenantForm'),
//   { 
//     fallback: <SectionLoadingFallback />
//   }
// );

// TODO: Component not yet implemented
// export const LazyTenantDetails = createSafeLazyComponent(
//   () => import('@/components/tenants/TenantDetails'),
//   { 
//     fallback: <SectionLoadingFallback />
//   }
// );

// TODO: Component not yet implemented
// export const LazyTenantSettings = createSafeLazyComponent(
//   () => import('@/components/tenants/TenantSettings'),
//   { 
//     fallback: <SectionLoadingFallback />
//   }
// );

// ============================================================================
// USER MANAGEMENT COMPONENTS
// ============================================================================

// TODO: Component not yet implemented
// export const LazyUserList = createSafeLazyComponent(
//   () => import('@/components/users/UserList'),
//   { 
//     fallback: <SectionLoadingFallback />
//   }
// );

// TODO: Component not yet implemented
// export const LazyUserForm = createSafeLazyComponent(
//   () => import('@/components/users/UserForm'),
//   { 
//     fallback: <SectionLoadingFallback />
//   }
// );

// TODO: Component not yet implemented
// export const LazyUserProfile = createSafeLazyComponent(
//   () => import('@/components/users/UserProfile'),
//   { 
//     preload: getLoadingStrategy() === 'aggressive',
//     fallback: <SectionLoadingFallback />
//   }
// );

// TODO: Component not yet implemented
// export const LazyUserPermissions = createSafeLazyComponent(
//   () => import('@/components/users/UserPermissions'),
//   { 
//     fallback: <SectionLoadingFallback />
//   }
// );

// ============================================================================
// SETTINGS COMPONENTS
// ============================================================================

// TODO: Component not yet implemented
// export const LazyGeneralSettings = createSafeLazyComponent(
//   () => import('@/components/settings/GeneralSettings'),
//   { 
//     fallback: <SectionLoadingFallback />
//   }
// );

// TODO: Component not yet implemented
// export const LazySecuritySettings = createSafeLazyComponent(
//   () => import('@/components/settings/SecuritySettings'),
//   { 
//     fallback: <SectionLoadingFallback />
//   }
// );

// TODO: Component not yet implemented
// export const LazyNotificationSettings = createSafeLazyComponent(
//   () => import('@/components/settings/NotificationSettings'),
//   { 
//     fallback: <SectionLoadingFallback />
//   }
// );

// TODO: Component not yet implemented
// export const LazyBillingSettings = createSafeLazyComponent(
//   () => import('@/components/settings/BillingSettings'),
//   { 
//     fallback: <SectionLoadingFallback />
//   }
// );

// ============================================================================
// ANALYTICS COMPONENTS
// ============================================================================

// TODO: Component not yet implemented
// export const LazyAnalyticsDashboard = createSafeLazyComponent(
//   () => import('@/components/analytics/AnalyticsDashboard'),
//   { 
//     preload: getLoadingStrategy() !== 'minimal',
//     fallback: <SectionLoadingFallback />
//   }
// );

// TODO: Component not yet implemented
// export const LazyUsageMetrics = createSafeLazyComponent(
//   () => import('@/components/analytics/UsageMetrics'),
//   { 
//     fallback: <SectionLoadingFallback />
//   }
// );

// TODO: Component not yet implemented
// export const LazyPerformanceMetrics = createSafeLazyComponent(
//   () => import('@/components/analytics/PerformanceMetrics'),
//   { 
//     fallback: <SectionLoadingFallback />
//   }
// );

// TODO: Component not yet implemented
// export const LazyReports = createSafeLazyComponent(
//   () => import('@/components/analytics/Reports'),
//   { 
//     fallback: <SectionLoadingFallback />
//   }
// );

// ============================================================================
// DEVELOPMENT COMPONENTS
// ============================================================================

export const LazyAccessibilityTester = createSafeLazyComponent(
  () => import('@/components/dev/AccessibilityTester'),
  { 
    preload: process.env.NODE_ENV === 'development',
    fallback: <ComponentLoadingFallback />
  }
);

export const LazyPerformanceMonitor = createSafeLazyComponent(
  () => import('@/components/dev/PerformanceMonitor'),
  { 
    preload: process.env.NODE_ENV === 'development',
    fallback: <ComponentLoadingFallback />
  }
);

// ============================================================================
// MODAL COMPONENTS
// ============================================================================

export const LazyConfirmationModal = createLazyComponent(
  () => import('@/components/modals/ConfirmationModal'),
  { 
    preload: getLoadingStrategy() === 'aggressive'
  }
);

export const LazyAlertModal = createLazyComponent(
  () => import('@/components/modals/AlertModal'),
  { 
    preload: true
  }
);

export const LazyFormModal = createLazyComponent(
  () => import('@/components/modals/FormModal'),
  { 
    preload: getLoadingStrategy() !== 'minimal'
  }
);

// ============================================================================
// CHART COMPONENTS (Heavy dependencies)
// ============================================================================

export const LazyChartComponent = createSafeLazyComponent(
  () => import('@/components/charts/ChartComponent'),
  { 
    preload: false,
    fallback: (
      <div className="flex items-center justify-center h-64 bg-gray-50 rounded-lg">
        <div className="text-center">
          <AccessibleLoadingSpinner size="md" />
          <div className="mt-2 text-sm text-gray-600">Loading chart...</div>
        </div>
      </div>
    )
  }
);

export const LazyDataVisualization = createSafeLazyComponent(
  () => import('@/components/charts/DataVisualization'),
  { 
    preload: false,
    fallback: (
      <div className="flex items-center justify-center h-80 bg-gray-50 rounded-lg">
        <div className="text-center">
          <AccessibleLoadingSpinner size="lg" />
          <div className="mt-2 text-sm text-gray-600">Loading visualization...</div>
        </div>
      </div>
    )
  }
);

// ============================================================================
// WRAPPER COMPONENTS
// ============================================================================

interface LazyWrapperProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
  name?: string;
}

export function LazyWrapper({ children, fallback, name }: LazyWrapperProps) {
  const defaultFallback = fallback || <ComponentLoadingFallback />;
  
  return (
    <Suspense fallback={defaultFallback}>
      {children}
    </Suspense>
  );
}

export function LazySection({ children, fallback, name }: LazyWrapperProps) {
  const defaultFallback = fallback || <SectionLoadingFallback />;
  
  return (
    <Suspense fallback={defaultFallback}>
      {children}
    </Suspense>
  );
}

export function LazyPage({ children, fallback, name }: LazyWrapperProps) {
  const defaultFallback = fallback || <PageLoadingFallback />;
  
  return (
    <Suspense fallback={defaultFallback}>
      {children}
    </Suspense>
  );
}

// ============================================================================
// UTILITY HOOKS
// ============================================================================

export function useLazyPreloading() {
  React.useEffect(() => {
    const strategy = getLoadingStrategy();
    
    if (strategy === 'aggressive') {
      // Preload commonly used components
      LazyDashboardOverview.preload();
      LazyUserProfile.preload();
      LazyConfirmationModal.preload();
      LazyAlertModal.preload();
    }
  }, []);
}