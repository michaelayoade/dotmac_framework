/**
 * Next.js Middleware for Tenant Portal
 * Handles authentication, rate limiting, and security
 */

import { NextRequest, NextResponse } from 'next/server';
import { checkRateLimit, createRateLimitResponse, getRateLimitHeaders, checkSuspiciousActivity } from '@/lib/rate-limiting';

// Protected routes that require authentication
const PROTECTED_ROUTES = [
  '/dashboard',
  '/billing',
  '/settings',
  '/api/tenant',
];

// API routes that need rate limiting
const API_ROUTES = ['/api/'];

// Public routes that don't require authentication
const PUBLIC_ROUTES = [
  '/login',
  '/api/auth/login',
  '/api/auth/refresh',
  '/api/csp-report',
  '/api/health',
];

/**
 * Check if route is protected
 */
function isProtectedRoute(pathname: string): boolean {
  return PROTECTED_ROUTES.some(route => pathname.startsWith(route));
}

/**
 * Check if route is public
 */
function isPublicRoute(pathname: string): boolean {
  return PUBLIC_ROUTES.some(route => pathname.startsWith(route));
}

/**
 * Check if route is API
 */
function isAPIRoute(pathname: string): boolean {
  return API_ROUTES.some(route => pathname.startsWith(route));
}

/**
 * Validate authentication from cookies
 */
async function validateAuthentication(request: NextRequest): Promise<boolean> {
  const cookies = request.cookies;
  
  // Check for required authentication cookies
  const accessToken = cookies.get('tenant_access_token');
  const sessionId = cookies.get('tenant_session_id');
  const csrfToken = cookies.get('tenant_csrf_token');

  if (!accessToken || !sessionId || !csrfToken) {
    return false;
  }

  // Additional validation could be added here
  // For now, presence of cookies indicates authentication
  return true;
}

/**
 * Apply security headers
 */
function addSecurityHeaders(response: NextResponse, request: NextRequest): NextResponse {
  const isProduction = process.env.NODE_ENV === 'production';
  const managementApiUrl = process.env.NEXT_PUBLIC_MANAGEMENT_API_URL || 'http://localhost:8000';
  const apiDomain = new URL(managementApiUrl).hostname;

  // Content Security Policy
  const cspDirectives = [
    "default-src 'self'",
    isProduction 
      ? "script-src 'self' 'unsafe-eval'" 
      : "script-src 'self' 'unsafe-eval' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "img-src 'self' data: https:",
    "font-src 'self' https://fonts.gstatic.com",
    `connect-src 'self' ${managementApiUrl} wss://${apiDomain} ws://${apiDomain}`,
    "frame-src 'none'",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    ...(isProduction ? ["upgrade-insecure-requests"] : []),
  ];

  response.headers.set('Content-Security-Policy', cspDirectives.join('; '));
  
  // Security headers
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');
  response.headers.set('X-XSS-Protection', '1; mode=block');
  response.headers.set('X-DNS-Prefetch-Control', 'off');
  
  if (isProduction) {
    response.headers.set('Strict-Transport-Security', 'max-age=31536000; includeSubDomains; preload');
  }
  
  // Cross-Origin policies
  response.headers.set('Cross-Origin-Embedder-Policy', 'require-corp');
  response.headers.set('Cross-Origin-Opener-Policy', 'same-origin');
  response.headers.set('Cross-Origin-Resource-Policy', 'same-origin');
  
  // Permissions Policy
  const permissionsPolicies = [
    'camera=()',
    'microphone=()',
    'geolocation=()',
    'interest-cohort=()',
    'payment=()',
    'usb=()',
    'accelerometer=()',
    'gyroscope=()',
    'magnetometer=()',
  ];
  response.headers.set('Permissions-Policy', permissionsPolicies.join(', '));

  return response;
}

/**
 * Main middleware function
 */
export async function middleware(request: NextRequest): Promise<NextResponse> {
  const { pathname } = request.nextUrl;

  // Skip middleware for static files and Next.js internals
  if (
    pathname.startsWith('/_next/') ||
    pathname.startsWith('/favicon.ico') ||
    pathname.startsWith('/robots.txt') ||
    pathname.includes('.') // Skip files with extensions
  ) {
    return NextResponse.next();
  }

  // Check for suspicious activity first
  if (checkSuspiciousActivity(request)) {
    console.warn(`Suspicious activity detected from ${request.ip || 'unknown'}: ${request.headers.get('user-agent')}`);
    
    // Apply stricter rate limiting for suspicious requests
    const rateLimitResult = checkRateLimit(request, 'API');
    if (!rateLimitResult.success) {
      const rateLimitResponse = createRateLimitResponse(
        'Access temporarily restricted due to suspicious activity',
        rateLimitResult.resetTime
      );
      return new NextResponse(rateLimitResponse.body, {
        status: rateLimitResponse.status,
        headers: rateLimitResponse.headers,
      });
    }
  }

  // Apply rate limiting to API routes
  if (isAPIRoute(pathname)) {
    const rateLimitResult = checkRateLimit(request, 'API');
    
    if (!rateLimitResult.success) {
      const rateLimitResponse = createRateLimitResponse(
        'Too many API requests. Please try again later.',
        rateLimitResult.resetTime
      );
      return new NextResponse(rateLimitResponse.body, {
        status: rateLimitResponse.status,
        headers: rateLimitResponse.headers,
      });
    }
  }

  // Special rate limiting for login attempts
  if (pathname === '/api/auth/login' || pathname === '/login') {
    const rateLimitResult = checkRateLimit(request, 'LOGIN');
    
    if (!rateLimitResult.success) {
      const rateLimitResponse = createRateLimitResponse(
        'Too many login attempts. Please try again later.',
        rateLimitResult.resetTime
      );
      return new NextResponse(rateLimitResponse.body, {
        status: rateLimitResponse.status,
        headers: rateLimitResponse.headers,
      });
    }
  }

  let response = NextResponse.next();

  // Add rate limit headers to API responses
  if (isAPIRoute(pathname)) {
    const headers = getRateLimitHeaders(request, 'API');
    Object.entries(headers).forEach(([key, value]) => {
      response.headers.set(key, value);
    });
  }

  // Handle authentication for protected routes
  if (isProtectedRoute(pathname)) {
    const isAuthenticated = await validateAuthentication(request);
    
    if (!isAuthenticated) {
      // Redirect to login with return URL
      const loginUrl = new URL('/login', request.url);
      loginUrl.searchParams.set('returnTo', pathname);
      
      response = NextResponse.redirect(loginUrl);
    }
  }

  // Handle authenticated users accessing login page
  if (pathname === '/login') {
    const isAuthenticated = await validateAuthentication(request);
    
    if (isAuthenticated) {
      // Redirect to dashboard or return URL
      const returnTo = request.nextUrl.searchParams.get('returnTo') || '/dashboard';
      const redirectUrl = new URL(returnTo, request.url);
      
      response = NextResponse.redirect(redirectUrl);
    }
  }

  // Handle root path redirect
  if (pathname === '/') {
    const isAuthenticated = await validateAuthentication(request);
    const redirectPath = isAuthenticated ? '/dashboard' : '/login';
    
    response = NextResponse.redirect(new URL(redirectPath, request.url));
  }

  // Apply security headers to all responses
  response = addSecurityHeaders(response, request);

  return response;
}

/**
 * Configure which paths the middleware should run on
 */
export const config = {
  matcher: [
    /*
     * Match all request paths except:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, robots.txt, etc.
     */
    '/((?!_next/static|_next/image|favicon.ico|robots.txt|manifest.json).*)',
  ],
};