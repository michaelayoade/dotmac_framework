'use client';

import { lazy, Suspense } from 'react';
import { Loading } from '@dotmac/primitives';

// Lazy load heavy components for better performance
const PartnersPage = lazy(() =>
  import('@/app/(authenticated)/partners/page').then(module => ({
    default: module.default
  }))
);

const CommissionsPage = lazy(() =>
  import('@/app/(authenticated)/commissions/page').then(module => ({
    default: module.default
  }))
);

const OnboardingPage = lazy(() =>
  import('@/app/(authenticated)/partners/onboarding/page').then(module => ({
    default: module.default
  }))
);

const DashboardPage = lazy(() =>
  import('@/app/(authenticated)/dashboard/page').then(module => ({
    default: module.default
  }))
);

// HOC for lazy loading with loading state
export function withLazyLoading<P extends object>(
  Component: React.ComponentType<P>,
  loadingMessage?: string
) {
  return function LazyLoadedComponent(props: P) {
    return (
      <Suspense fallback={<Loading message={loadingMessage} />}>
        <Component {...props} />
      </Suspense>
    );
  };
}

// Pre-configured lazy components
export const LazyPartners = withLazyLoading(PartnersPage, 'Loading partners...');
export const LazyCommissions = withLazyLoading(CommissionsPage, 'Loading commissions...');
export const LazyOnboarding = withLazyLoading(OnboardingPage, 'Loading onboarding...');
export const LazyDashboard = withLazyLoading(DashboardPage, 'Loading dashboard...');

// Route-based code splitting utility
export function createLazyRoute(importFn: () => Promise<{ default: React.ComponentType }>, loadingMessage?: string) {
  const LazyComponent = lazy(importFn);

  return function LazyRoute(props: any) {
    return (
      <Suspense fallback={<Loading message={loadingMessage} />}>
        <LazyComponent {...props} />
      </Suspense>
    );
  };
}
