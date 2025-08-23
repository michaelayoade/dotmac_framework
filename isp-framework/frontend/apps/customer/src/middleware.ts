import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// Simple CSP utilities
function generateNonce(): string {
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    const array = new Uint8Array(16);
    crypto.getRandomValues(array);
    return btoa(String.fromCharCode(...array));
  }
  return 'fallback-nonce';
}

function generateCSP(nonce: string, isDev = false): string {
  const baseCSP = {
    'default-src': "'self'",
    'script-src': `'self' 'nonce-${nonce}' 'strict-dynamic'${isDev ? " 'unsafe-eval'" : ''}`,
    'style-src': "'self' 'unsafe-inline' fonts.googleapis.com",
    'font-src': "'self' fonts.gstatic.com data:",
    'img-src': "'self' data: blob: https:",
    'connect-src': "'self' ws: wss: https:",
    'frame-ancestors': "'none'",
    'base-uri': "'self'",
    'form-action': "'self'",
    'object-src': "'none'",
    'upgrade-insecure-requests': '',
  };

  return Object.entries(baseCSP)
    .map(([key, value]) => `${key} ${value}`)
    .join('; ');
}

// Public routes that don't require authentication
const publicRoutes = ['/', '/login', '/register', '/forgot-password', '/reset-password'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const authToken = request.cookies.get('auth-token');
  const portalType = request.cookies.get('portal-type');

  // Check if it's a public route
  const isPublicRoute = publicRoutes.some(
    (route) => pathname === route || pathname.startsWith('/api/auth')
  );

  // If no auth token and trying to access protected route, redirect to login
  if (!authToken && !isPublicRoute) {
    const loginUrl = new URL('/', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Verify portal type for customer routes
  if (authToken && portalType?.value !== 'customer' && !isPublicRoute) {
    // User is authenticated but not a customer
    return NextResponse.redirect(new URL('/unauthorized', request.url));
  }

  // Generate a unique nonce for this request
  const nonce = generateNonce();

  // Clone the request headers and add nonce
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-nonce', nonce);

  // Create response with modified request
  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  });

  // Generate CSP with nonce
  const csp = generateCSP(nonce, process.env.NODE_ENV === 'development');

  // Add security headers including CSP with nonce
  response.headers.set('Content-Security-Policy', csp);
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('X-XSS-Protection', '1; mode=block');
  response.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
  response.headers.set(
    'Permissions-Policy',
    'camera=(), microphone=(), geolocation=(), payment=()'
  );

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - public folder
     */
    '/((?!_next/static|_next/image|favicon.ico|public).*)',
  ],
};
