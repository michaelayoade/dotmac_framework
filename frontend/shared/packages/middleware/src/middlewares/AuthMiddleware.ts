/**
 * Authentication Middleware
 * Handles authentication checks and portal type validation
 */

import { NextResponse } from 'next/server';
import type { MiddlewareFunction, MiddlewareContext, PortalType } from '../types';
import { isPublicRoute } from '../utils';

/**
 * Authentication middleware factory
 */
export function createAuthMiddleware(
  portal: PortalType,
  publicRoutes: string[],
  authRequired: boolean = true
): MiddlewareFunction {
  return async (context: MiddlewareContext) => {
    const { pathname, authToken, portalType } = context;

    // Skip auth check for public routes
    if (isPublicRoute(pathname, publicRoutes)) {
      return null; // Continue to next middleware
    }

    // If authentication is not required for this portal, continue
    if (!authRequired) {
      return null;
    }

    // Check for auth token
    if (!authToken) {
      return createUnauthorizedResponse(pathname);
    }

    // Verify portal type matches
    if (portalType && portalType !== portal) {
      return createForbiddenResponse(portal, portalType);
    }

    // Continue to next middleware
    return null;
  };
}

/**
 * Create unauthorized response
 */
function createUnauthorizedResponse(pathname: string): NextResponse {
  const loginUrl = new URL('/', 'http://localhost');
  loginUrl.searchParams.set('redirect', pathname);

  return NextResponse.redirect(loginUrl, {
    status: 307,
    headers: {
      'Set-Cookie':
        'redirect_after_login=' +
        encodeURIComponent(pathname) +
        '; Path=/; HttpOnly; SameSite=Strict',
    },
  });
}

/**
 * Create forbidden response for wrong portal type
 */
function createForbiddenResponse(expectedPortal: PortalType, actualPortal: string): NextResponse {
  return NextResponse.json(
    {
      error: 'Access denied',
      message: `This portal is for ${expectedPortal} users only. You are authenticated as ${actualPortal}.`,
      redirect: '/unauthorized',
    },
    {
      status: 403,
      headers: {
        'Cache-Control': 'no-store',
      },
    }
  );
}

/**
 * Role-based access control middleware
 */
export function createRBACMiddleware(
  roleChecker: (authToken: string, pathname: string) => Promise<boolean>
): MiddlewareFunction {
  return async (context: MiddlewareContext) => {
    const { pathname, authToken } = context;

    if (!authToken) {
      return null; // Let auth middleware handle this
    }

    // Check role permissions
    const hasAccess = await roleChecker(authToken, pathname);

    if (!hasAccess) {
      return NextResponse.json(
        {
          error: 'Insufficient permissions',
          message: 'You do not have permission to access this resource.',
        },
        { status: 403 }
      );
    }

    return null;
  };
}
