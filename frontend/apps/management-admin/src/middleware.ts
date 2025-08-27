import { NextRequest, NextResponse } from 'next/server';
import { generateNonce } from '@/lib/csp-utils';

// Public routes that don't require authentication
const publicRoutes = ['/', '/login'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // Check if it's a public route
  const isPublicRoute = publicRoutes.some(
    (route) => pathname === route || pathname.startsWith('/api/auth')
  );

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

  // Generate CSP with nonce for management platform
  const csp = generateManagementCSP(nonce, process.env.NODE_ENV === 'development');

  // Add comprehensive security headers
  response.headers.set('Content-Security-Policy', csp);
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('X-XSS-Protection', '1; mode=block');
  
  // Only set HSTS in production
  if (process.env.NODE_ENV === 'production') {
    response.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
  }
  
  // Management platform specific security headers
  response.headers.set(
    'Permissions-Policy',
    'camera=(), microphone=(), geolocation=(), payment=(), usb=()'
  );

  // Add CSRF protection header
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Permitted-Cross-Domain-Policies', 'none');

  return response;
}

/**
 * Generate CSP policy specifically for management platform
 */
function generateManagementCSP(nonce: string, isDevelopment = false): string {
  const policies = [
    "default-src 'self'",
    
    // Scripts: Use nonce, allow webpack in dev
    isDevelopment 
      ? `script-src 'self' 'nonce-${nonce}' 'unsafe-eval'` 
      : `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,
    
    // Styles: Use nonce, allow Google Fonts
    isDevelopment
      ? `style-src 'self' 'unsafe-inline' https://fonts.googleapis.com`
      : `style-src 'self' 'nonce-${nonce}' https://fonts.googleapis.com`,
    
    // Images: Self, data URLs, and HTTPS
    "img-src 'self' data: https:",
    
    // Fonts: Self and Google Fonts
    "font-src 'self' https://fonts.gstatic.com data:",
    
    // Connections: Management API and development
    isDevelopment
      ? `connect-src 'self' ${process.env.NEXT_PUBLIC_MANAGEMENT_API_URL || 'http://localhost:8000'} http://localhost:* ws://localhost:* wss://localhost:*`
      : `connect-src 'self' ${process.env.NEXT_PUBLIC_MANAGEMENT_API_URL || 'https://api.management.dotmac.com'}`,
    
    // Security directives
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",
    
    // Enable upgrade insecure requests in production
    ...(isDevelopment ? [] : ["upgrade-insecure-requests"]),
    
    // Management platform specific
    "worker-src 'self' blob:",
    "manifest-src 'self'",
    "media-src 'self'",
  ];

  return policies.join('; ');
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!_next/static|_next/image|favicon.ico).*)',
  ],
};