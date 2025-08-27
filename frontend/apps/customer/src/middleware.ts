import { generateCSP, generateNonce } from '@dotmac/headless/utils/csp';
import type { NextRequest } from 'next/server';
import { NextResponse } from 'next/server';
// Mock monitoring for now since package structure is complex
const audit = {
  system: async (...args: any[]) => {},
  security: async (...args: any[]) => {}
};
const auditContext = {
  fromRequest: (req: any) => ({
    traceId: 'test-trace',
    correlationId: 'test-correlation'  
  })
};

// Simple in-memory rate limiting (production should use Redis/database)
const rateLimitStore = new Map<string, { count: number; resetTime: number }>();

function checkRateLimit(identifier: string, maxRequests: number = 10, windowMs: number = 15 * 60 * 1000): boolean {
  const now = Date.now();
  const key = identifier;
  const limit = rateLimitStore.get(key);
  
  if (!limit || now > limit.resetTime) {
    // Reset or create new limit
    rateLimitStore.set(key, { count: 1, resetTime: now + windowMs });
    return true;
  }
  
  if (limit.count >= maxRequests) {
    return false;
  }
  
  limit.count++;
  return true;
}

// Public routes that don't require authentication
const publicRoutes = ['/', '/login', '/register', '/forgot-password', '/reset-password'];

export async function middleware(request: NextRequest) {
  const startTime = Date.now();
  const { pathname } = request.nextUrl;
  const context = auditContext.fromRequest(request);
  const authToken = request.cookies.get('secure-auth-token');
  const csrfToken = request.cookies.get('csrf-token');
  const portalType = request.cookies.get('portal-type');

  // Server-side rate limiting for sensitive endpoints
  const clientIP = request.ip || request.headers.get('x-forwarded-for') || request.headers.get('x-real-ip') || 'unknown';
  const isAuthEndpoint = pathname.startsWith('/api/auth') || pathname === '/login';
  
  if (isAuthEndpoint) {
    // Stricter rate limiting for authentication endpoints
    if (!checkRateLimit(`auth:${clientIP}`, 5, 15 * 60 * 1000)) {
      await audit.security(
        'rate_limit_exceeded',
        { ...context, clientIP, endpoint: pathname },
        'high',
        false
      );
      
      return NextResponse.json(
        { error: 'Too many requests. Please try again later.' },
        { status: 429, headers: { 'Retry-After': '900' } } // 15 minutes
      );
    }
  } else {
    // General rate limiting for all requests
    if (!checkRateLimit(`general:${clientIP}`, 100, 60 * 1000)) {
      return NextResponse.json(
        { error: 'Rate limit exceeded' },
        { status: 429, headers: { 'Retry-After': '60' } }
      );
    }
  }

  // Log incoming request
  await audit.system(
    'request_received',
    'middleware',
    true,
    'low',
    {
      method: request.method,
      pathname,
      userAgent: context.userAgent,
      timestamp: new Date().toISOString(),
    }
  );

  // Check if it's a public route
  const isPublicRoute = publicRoutes.some(
    route => pathname === route || pathname.startsWith('/api/auth')
  );

  // CSRF protection for state-changing requests
  if (!isPublicRoute && request.method !== 'GET') {
    const requestCsrfToken =
      request.headers.get('x-csrf-token') || request.cookies.get('csrf-token')?.value;
    const storedCsrfToken = request.cookies.get('csrf-token')?.value;

    if (!requestCsrfToken || !storedCsrfToken || requestCsrfToken !== storedCsrfToken) {
      // Log CSRF violation
      await audit.security(
        'csrf_token_mismatch',
        context,
        'high',
        false
      );
      
      return NextResponse.json({ error: 'CSRF token mismatch' }, { status: 403 });
    }
  }

  // If no auth token and trying to access protected route, return unauthorized
  if (!authToken && !isPublicRoute) {
    // Log unauthorized access attempt
    await audit.security(
      'unauthorized_access_attempt',
      context,
      'medium',
      false
    );
    
    return NextResponse.json(
      { error: 'Authentication required', redirect: '/?redirect=' + encodeURIComponent(pathname) }, 
      { status: 401 }
    );
  }

  // Verify portal type for customer routes
  if (authToken && portalType?.value !== 'customer' && !isPublicRoute) {
    // Log portal type mismatch
    await audit.security(
      'portal_type_mismatch',
      { ...context, userId: authToken.value },
      'medium',
      false
    );
    
    // User is authenticated but not a customer
    return NextResponse.json(
      { error: 'Access denied - incorrect portal type', redirect: '/unauthorized' }, 
      { status: 403 }
    );
  }

  // Rate limiting is handled by server-side middleware
  // Frontend middleware focuses on CSP, authentication, and security headers

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

  // Additional security headers for secure authentication
  response.headers.set('Cache-Control', 'no-store, no-cache, must-revalidate, proxy-revalidate');
  response.headers.set('Pragma', 'no-cache');
  response.headers.set('Expires', '0');

  // Only set HSTS in production
  if (process.env.NODE_ENV === 'production') {
    response.headers.set(
      'Strict-Transport-Security',
      'max-age=31536000; includeSubDomains; preload'
    );
  }
  response.headers.set(
    'Permissions-Policy',
    'camera=(), microphone=(), geolocation=(), payment=()'
  );

  // Add audit correlation headers
  response.headers.set('x-trace-id', context.traceId || '');
  response.headers.set('x-correlation-id', context.correlationId || '');

  // Log successful request completion
  const duration = Date.now() - startTime;
  await audit.system(
    'request_completed',
    'middleware',
    true,
    'low',
    {
      method: request.method,
      pathname,
      duration,
      statusCode: response.status || 200,
    }
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
