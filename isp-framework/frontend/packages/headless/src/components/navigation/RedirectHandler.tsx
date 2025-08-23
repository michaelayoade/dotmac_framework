/**
 * Advanced redirect handling for ISP platform
 */

import { useRouter, useSearchParams } from 'next/navigation';
import { useEffect, useCallback, useState } from 'react';

import { usePortalAuth } from '../../hooks/usePortalAuth';
import { usePermissions } from '../../hooks/usePermissions';

export interface RedirectRule {
  from: string | RegExp;
  to: string | ((match: string) => string);
  condition?: () => boolean;
  requiredRoles?: string[];
  requiredPermissions?: string[];
  preserveQuery?: boolean;
  exact?: boolean;
}

interface RedirectHandlerProps {
  rules: RedirectRule[];
  fallbackRoute?: string;
  onRedirect?: (from: string, to: string) => void;
}

// Default redirect rules for different portals
const DEFAULT_PORTAL_REDIRECTS: Record<string, RedirectRule[]> = {
  admin: [
    {
      from: '/',
      to: '/admin/dashboard',
      condition: () => true,
    },
    {
      from: '/login',
      to: '/admin/dashboard',
      condition: () => true, // Will be checked with auth state
    },
    {
      from: '/unauthorized',
      to: '/admin/dashboard',
      requiredRoles: ['super-admin', 'tenant-admin'],
    },
  ],
  customer: [
    {
      from: '/admin',
      to: '/',
      condition: () => true,
    },
    {
      from: '/login',
      to: '/',
      condition: () => true,
    },
  ],
  reseller: [
    {
      from: '/admin',
      to: '/',
      condition: () => true,
    },
    {
      from: '/login',
      to: '/',
      condition: () => true,
    },
  ],
};

export function RedirectHandler({
  rules = [],
  fallbackRoute = '/',
  onRedirect,
}: RedirectHandlerProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { currentPortal, user, isLoading } = usePortalAuth();
  const { checkAnyRole, hasAnyPermission } = usePermissions();

  const [hasProcessedRedirect, setHasProcessedRedirect] = useState(false);

  const processRedirect = useCallback((currentPath: string): string | null => {
    // Combine custom rules with portal-specific rules
    const portalRules = currentPortal ? DEFAULT_PORTAL_REDIRECTS[currentPortal.type] || [] : [];
    const allRules = [...rules, ...portalRules];

    for (const rule of allRules) {
      let matches = false;
      let matchResult: string = '';

      // Check if rule matches current path
      if (typeof rule.from === 'string') {
        if (rule.exact) {
          matches = currentPath === rule.from;
        } else {
          matches = currentPath.startsWith(rule.from);
        }
        matchResult = currentPath;
      } else if (rule.from instanceof RegExp) {
        const regexMatch = currentPath.match(rule.from);
        matches = !!regexMatch;
        matchResult = regexMatch?.[0] || '';
      }

      if (!matches) continue;

      // Check conditions
      if (rule.condition && !rule.condition()) continue;

      // Check role requirements
      if (rule.requiredRoles && !checkAnyRole(rule.requiredRoles)) continue;

      // Check permission requirements
      if (rule.requiredPermissions && !hasAnyPermission(rule.requiredPermissions)) continue;

      // Calculate redirect target
      let target: string;
      if (typeof rule.to === 'function') {
        target = rule.to(matchResult);
      } else {
        target = rule.to;
      }

      // Preserve query parameters if requested
      if (rule.preserveQuery && searchParams.toString()) {
        const separator = target.includes('?') ? '&' : '?';
        target = `${target}${separator}${searchParams.toString()}`;
      }

      return target;
    }

    return null;
  }, [rules, currentPortal, checkAnyRole, hasAnyPermission, searchParams]);

  const handleRedirect = useCallback((targetPath: string) => {
    const currentPath = window.location.pathname;
    
    if (currentPath === targetPath) return; // Avoid infinite redirects

    if (onRedirect) {
      onRedirect(currentPath, targetPath);
    }

    router.push(targetPath);
    setHasProcessedRedirect(true);
  }, [router, onRedirect]);

  useEffect(() => {
    // Don't process redirects while loading or if already processed
    if (isLoading || hasProcessedRedirect) return;

    // Only process redirects if we have auth state (either authenticated or confirmed unauthenticated)
    if (user === undefined && !isLoading) return;

    const currentPath = window.location.pathname;
    const redirectTarget = processRedirect(currentPath);

    if (redirectTarget) {
      handleRedirect(redirectTarget);
    } else if (currentPath !== fallbackRoute) {
      // Check if current path is accessible, otherwise redirect to fallback
      const isAccessible = checkPathAccessibility(currentPath);
      if (!isAccessible) {
        handleRedirect(fallbackRoute);
      }
    }
  }, [
    isLoading,
    user,
    processRedirect,
    handleRedirect,
    fallbackRoute,
    hasProcessedRedirect,
  ]);

  const checkPathAccessibility = (path: string): boolean => {
    // Simple accessibility check - this could be expanded
    if (!user && !isPublicPath(path)) {
      return false;
    }

    if (currentPortal) {
      // Check if path is appropriate for current portal
      const portalPrefixes = {
        admin: ['/admin'],
        customer: ['/services', '/billing', '/support', '/usage', '/documents'],
        reseller: ['/customers', '/sales', '/commissions', '/territory'],
      };

      const allowedPrefixes = portalPrefixes[currentPortal.type] || [];
      return allowedPrefixes.some(prefix => path.startsWith(prefix)) || path === '/';
    }

    return true;
  };

  const isPublicPath = (path: string): boolean => {
    const publicPaths = [
      '/',
      '/login',
      '/forgot-password',
      '/reset-password',
      '/unauthorized',
      '/terms',
      '/privacy',
    ];
    return publicPaths.includes(path);
  };

  return null; // This component doesn't render anything
}

// Hook for programmatic redirects
export function useRedirect() {
  const router = useRouter();
  const { currentPortal } = usePortalAuth();
  const { checkAnyRole, hasAnyPermission } = usePermissions();

  const redirectTo = useCallback((
    path: string,
    options?: {
      replace?: boolean;
      preserveQuery?: boolean;
      checkPermissions?: boolean;
      requiredRoles?: string[];
      requiredPermissions?: string[];
    }
  ) => {
    const {
      replace = false,
      preserveQuery = false,
      checkPermissions = true,
      requiredRoles,
      requiredPermissions,
    } = options || {};

    // Check permissions if required
    if (checkPermissions) {
      if (requiredRoles && !checkAnyRole(requiredRoles)) {
        console.warn('Redirect blocked: insufficient roles');
        return false;
      }

      if (requiredPermissions && !hasAnyPermission(requiredPermissions)) {
        console.warn('Redirect blocked: insufficient permissions');
        return false;
      }
    }

    let targetPath = path;

    // Preserve query parameters if requested
    if (preserveQuery) {
      const currentQuery = window.location.search;
      if (currentQuery) {
        const separator = targetPath.includes('?') ? '&' : '?';
        targetPath = `${targetPath}${separator}${currentQuery.substring(1)}`;
      }
    }

    if (replace) {
      router.replace(targetPath);
    } else {
      router.push(targetPath);
    }

    return true;
  }, [router, checkAnyRole, hasAnyPermission]);

  const redirectToPortalDefault = useCallback(() => {
    const defaultPaths = {
      admin: '/admin/dashboard',
      customer: '/',
      reseller: '/',
    };

    const targetPath = currentPortal ? defaultPaths[currentPortal.type] : '/';
    return redirectTo(targetPath);
  }, [currentPortal, redirectTo]);

  const redirectWithFallback = useCallback((
    primaryPath: string,
    fallbackPath: string,
    options?: Parameters<typeof redirectTo>[1]
  ) => {
    const success = redirectTo(primaryPath, { ...options, checkPermissions: true });
    if (!success) {
      return redirectTo(fallbackPath, { ...options, checkPermissions: false });
    }
    return success;
  }, [redirectTo]);

  return {
    redirectTo,
    redirectToPortalDefault,
    redirectWithFallback,
  };
}

// Component to handle login redirects
export function LoginRedirectHandler() {
  const { user, isLoading } = usePortalAuth();
  const searchParams = useSearchParams();
  const { redirectTo } = useRedirect();

  useEffect(() => {
    if (isLoading || !user) return;

    // Get redirect parameter from URL
    const redirectParam = searchParams.get('redirect');
    const returnTo = searchParams.get('returnTo');
    
    const targetPath = redirectParam || returnTo;

    if (targetPath) {
      redirectTo(targetPath, { replace: true });
    }
  }, [user, isLoading, searchParams, redirectTo]);

  return null;
}