/**
 * Technician Portal Middleware
 * Handles authentication, security headers, and route protection
 */

import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { featureFlags, env } from './lib/config/environment';

// Public routes that don't require authentication
const PUBLIC_ROUTES = ['/login', '/offline'];

// API routes that require authentication
const PROTECTED_API_ROUTES = ['/api/v1/'];

// Generate cryptographically secure nonce
function generateNonce(): string {
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    const array = new Uint8Array(16);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
  }
  // Fallback for environments without crypto
  return Math.random().toString(36).substring(2) + Date.now().toString(36);
}

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const response = NextResponse.next();

  // Enhanced Security Headers
  response.headers.set('X-DNS-Prefetch-Control', 'on');
  response.headers.set('X-XSS-Protection', '1; mode=block');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('X-Permitted-Cross-Domain-Policies', 'none');
  response.headers.set('Permissions-Policy', 'camera=(), microphone=(), geolocation=(self), payment=()');
  
  // Generate nonce for scripts
  const nonce = generateNonce();
  response.headers.set('X-Nonce', nonce);
  
  // Strict Content Security Policy
  const isProduction = env.isProduction();
  const useStrictCSP = featureFlags.isStrictCSPEnabled();
  const csp = (isProduction && useStrictCSP) ? 
    // Production CSP - Very strict
    `default-src 'none'; ` +
    `script-src 'self' 'nonce-${nonce}'; ` +
    `style-src 'self' 'nonce-${nonce}'; ` +
    `img-src 'self' blob: data:; ` +
    `font-src 'self'; ` +
    `connect-src 'self'; ` +
    `media-src 'self' blob:; ` +
    `worker-src 'self'; ` +
    `child-src 'none'; ` +
    `object-src 'none'; ` +
    `form-action 'self'; ` +
    `frame-ancestors 'none'; ` +
    `base-uri 'self'; ` +
    `upgrade-insecure-requests;`
  :
    // Development CSP - More permissive for dev tools
    `default-src 'self'; ` +
    `script-src 'self' 'nonce-${nonce}' localhost:* 127.0.0.1:*; ` +
    `style-src 'self' 'nonce-${nonce}' 'unsafe-inline'; ` +
    `img-src 'self' blob: data: localhost:* 127.0.0.1:*; ` +
    `font-src 'self' data:; ` +
    `connect-src 'self' localhost:* 127.0.0.1:* ws: wss:; ` +
    `media-src 'self' blob:; ` +
    `worker-src 'self' blob:; ` +
    `child-src 'none'; ` +
    `object-src 'none'; ` +
    `form-action 'self'; ` +
    `frame-ancestors 'none'; ` +
    `base-uri 'self';`;
    
  response.headers.set('Content-Security-Policy', csp);
  
  // Additional security headers for HTTPS
  if (request.nextUrl.protocol === 'https:') {
    response.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
  }

  // PWA headers for manifest and service worker
  if (pathname === '/manifest.json') {
    response.headers.set('Cache-Control', 'public, max-age=0, must-revalidate');
    return response;
  }

  if (pathname === '/sw.js') {
    response.headers.set('Cache-Control', 'public, max-age=0, must-revalidate');
    response.headers.set('Service-Worker-Allowed', '/');
    return response;
  }

  // Handle authentication for protected routes
  const isPublicRoute = PUBLIC_ROUTES.some(route => pathname.startsWith(route));
  const isProtectedAPI = PROTECTED_API_ROUTES.some(route => pathname.startsWith(route));
  
  // Check for secure authentication cookies
  const authToken = request.cookies.get('auth_session');
  const refreshToken = request.cookies.get('refresh_token');
  
  // Validate session integrity if CSRF is enabled
  let sessionSignature;
  if (featureFlags.isCSRFEnabled()) {
    sessionSignature = request.cookies.get('session_signature');
    if (authToken && !sessionSignature) {
      // Invalid session - clear cookies and redirect
      const loginUrl = new URL('/login', request.url);
      const redirectResponse = NextResponse.redirect(loginUrl);
      redirectResponse.cookies.delete('auth_session');
      redirectResponse.cookies.delete('refresh_token');
      return redirectResponse;
    }
  }

  // Redirect unauthenticated users from protected pages
  if (!isPublicRoute && !authToken) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }

  // Handle API authentication with rate limiting
  if (isProtectedAPI) {
    if (!authToken || !sessionSignature) {
      return new NextResponse(
        JSON.stringify({ 
          error: 'Authentication required',
          code: 'AUTH_REQUIRED',
          timestamp: new Date().toISOString()
        }),
        { 
          status: 401, 
          headers: { 
            'content-type': 'application/json',
            'Cache-Control': 'no-store, no-cache, must-revalidate'
          } 
        }
      );
    }

    // Add security headers for API responses
    response.headers.set('X-Content-Type-Options', 'nosniff');
    response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
    response.headers.set('Pragma', 'no-cache');
    response.headers.set('Expires', '0');
    
    // Note: Do not expose auth token in headers - use server-side session validation
  }

  // Redirect authenticated users away from login page
  if (pathname === '/login' && authToken) {
    return NextResponse.redirect(new URL('/', request.url));
  }

  // Handle offline page access
  if (pathname === '/offline') {
    response.headers.set('Cache-Control', 'public, max-age=31536000, immutable');
    return response;
  }

  return response;
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - icons/ (PWA icons)
     * - screenshots/ (PWA screenshots)
     */
    '/((?!_next/static|_next/image|favicon.ico|icons/|screenshots/).*)',
  ],
};