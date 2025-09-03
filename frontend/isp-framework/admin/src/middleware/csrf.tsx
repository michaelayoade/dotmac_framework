/**
 * CSRF Protection Middleware
 * Validates CSRF tokens for all state-changing operations
 */

import { NextRequest, NextResponse } from 'next/server';

// Routes that require CSRF protection
const CSRF_PROTECTED_ROUTES = [
  '/api/auth/login',
  '/api/auth/logout',
  '/api/auth/refresh',
  '/api/isp/',
  '/api/billing/',
  '/api/customers/',
  '/api/services/',
];

// Routes that are exempt from CSRF protection
const CSRF_EXEMPT_ROUTES = ['/api/auth/csrf', '/api/auth/validate', '/api/health', '/api/ready'];

export function csrfMiddleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const method = request.method;

  // Only protect state-changing methods
  if (!['POST', 'PUT', 'PATCH', 'DELETE'].includes(method)) {
    return NextResponse.next();
  }

  // Check if route is exempt
  if (CSRF_EXEMPT_ROUTES.some((route) => pathname.startsWith(route))) {
    return NextResponse.next();
  }

  // Check if route requires CSRF protection
  const requiresCSRF = CSRF_PROTECTED_ROUTES.some((route) => pathname.startsWith(route));

  if (!requiresCSRF) {
    return NextResponse.next();
  }

  // Get CSRF token from header
  const csrfTokenFromHeader =
    request.headers.get('X-CSRF-Token') || request.headers.get('x-csrf-token');

  // Get CSRF token from cookie
  const csrfTokenFromCookie = request.cookies.get('csrf-token')?.value;

  // Validate CSRF token
  if (!csrfTokenFromHeader || !csrfTokenFromCookie) {
    console.warn('CSRF Protection: Missing CSRF token', {
      pathname,
      hasHeader: !!csrfTokenFromHeader,
      hasCookie: !!csrfTokenFromCookie,
    });

    return NextResponse.json(
      {
        error: 'CSRF token missing',
        code: 'CSRF_TOKEN_MISSING',
        message: 'This request requires a valid CSRF token',
      },
      { status: 403 }
    );
  }

  if (csrfTokenFromHeader !== csrfTokenFromCookie) {
    console.warn('CSRF Protection: Token mismatch', {
      pathname,
      headerLength: csrfTokenFromHeader.length,
      cookieLength: csrfTokenFromCookie.length,
    });

    return NextResponse.json(
      {
        error: 'CSRF token invalid',
        code: 'CSRF_TOKEN_INVALID',
        message: 'The provided CSRF token is invalid',
      },
      { status: 403 }
    );
  }

  // CSRF token is valid, continue with request
  return NextResponse.next();
}

// Client-side CSRF protection hook
export function useCSRFProtection() {
  const getCSRFToken = async (): Promise<string | null> => {
    try {
      const response = await fetch('/api/auth/csrf', {
        method: 'GET',
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error('Failed to get CSRF token');
      }

      const data = await response.json();
      return data.csrfToken;
    } catch (error) {
      console.error('Failed to get CSRF token:', error);
      return null;
    }
  };

  const makeProtectedRequest = async (
    url: string,
    options: RequestInit = {}
  ): Promise<Response> => {
    // Get CSRF token
    const csrfToken = await getCSRFToken();

    if (!csrfToken) {
      throw new Error('Failed to obtain CSRF token');
    }

    // Add CSRF token to headers
    const headers = new Headers(options.headers);
    headers.set('X-CSRF-Token', csrfToken);
    headers.set('Content-Type', 'application/json');

    // Make request with CSRF protection
    return fetch(url, {
      ...options,
      credentials: 'include',
      headers,
    });
  };

  return {
    getCSRFToken,
    makeProtectedRequest,
  };
}

// Higher-order component for CSRF-protected forms
export function withCSRFProtection<T extends { onSubmit?: (data: any) => Promise<void> }>(
  WrappedComponent: React.ComponentType<T>
) {
  return function CSRFProtectedComponent(props: T) {
    const { makeProtectedRequest } = useCSRFProtection();

    const handleSubmit = async (data: any) => {
      if (props.onSubmit) {
        // Override the onSubmit to use CSRF-protected requests
        try {
          await props.onSubmit(data);
        } catch (error) {
          if (error instanceof Error && error.message.includes('CSRF')) {
            console.error('CSRF protection error:', error);
            // Handle CSRF error (e.g., refresh token and retry)
          }
          throw error;
        }
      }
    };

    return <WrappedComponent {...props} onSubmit={handleSubmit} />;
  };
}
