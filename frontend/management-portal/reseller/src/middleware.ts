import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { rateLimit } from './lib/rate-limit';
import { environmentConfig } from './lib/config/environment';

// JWT token validation interface
interface TokenValidation {
  isValid: boolean;
  expiresIn: number; // seconds until expiration
  payload?: any;
  error?: string;
}

// CSRF token validation
function validateCSRFToken(request: NextRequest): boolean {
  const token = request.headers.get('x-csrf-token');
  const cookieToken = request.cookies.get('csrf-token')?.value;

  if (!token || !cookieToken || token !== cookieToken) {
    return false;
  }

  return true;
}

// Server-side JWT token validation function
async function validateJWTTokenServerSide(token: string): Promise<TokenValidation> {
  try {
    // Call our secure validation endpoint
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3004'}/api/auth/validate-token`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token }),
      }
    );

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      return {
        isValid: false,
        expiresIn: 0,
        error: errorData.error || 'Token validation failed',
      };
    }

    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Token validation error:', error);
    return {
      isValid: false,
      expiresIn: 0,
      error: 'Token validation service unavailable',
    };
  }
}

// Fallback client-side validation for development/offline scenarios
function validateJWTTokenFallback(token: string): TokenValidation {
  try {
    // Basic JWT structure validation only
    const parts = token.split('.');
    if (parts.length !== 3) {
      return { isValid: false, expiresIn: 0, error: 'Invalid token structure' };
    }

    // Decode payload (base64url) - but don't trust it completely
    let payload;
    try {
      const base64Url = parts[1].replace(/-/g, '+').replace(/_/g, '/');
      const decodedBytes = Buffer.from(base64Url, 'base64');
      payload = JSON.parse(decodedBytes.toString());
    } catch (decodeError) {
      return { isValid: false, expiresIn: 0, error: 'Invalid token encoding' };
    }

    const now = Math.floor(Date.now() / 1000);
    const expiresIn = payload.exp ? payload.exp - now : 0;

    // Only check basic expiration - signature verification happens server-side
    if (expiresIn <= 0) {
      return { isValid: false, expiresIn: 0, error: 'Token expired' };
    }

    // Note: This is fallback validation only - don't fully trust client-side validation
    return { isValid: true, expiresIn, payload };
  } catch (error) {
    return { isValid: false, expiresIn: 0, error: 'Token parsing failed' };
  }
}

// Handle unauthenticated requests
function handleUnauthenticated(request: NextRequest, pathname: string): NextResponse {
  if (pathname.startsWith('/api/')) {
    return new NextResponse(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  } else {
    // Redirect to login for page routes
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return NextResponse.redirect(loginUrl);
  }
}

// Rate limiting configuration
const authEndpointLimiter = rateLimit({
  interval: 15 * 60 * 1000, // 15 minutes
  uniqueTokenPerInterval: 100,
});

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // Rate limiting for auth endpoints
  if (pathname.startsWith('/api/auth/')) {
    try {
      const identifier = request.ip ?? request.headers.get('x-forwarded-for') ?? 'unknown';
      await authEndpointLimiter.check(5, identifier); // 5 requests per 15 minutes per IP
    } catch {
      return new NextResponse(JSON.stringify({ error: 'Too many requests' }), {
        status: 429,
        headers: {
          'Content-Type': 'application/json',
          'Retry-After': '900', // 15 minutes
        },
      });
    }
  }

  // CSRF protection for state-changing operations
  if (
    pathname.startsWith('/api/') &&
    (request.method === 'POST' || request.method === 'PUT' || request.method === 'DELETE')
  ) {
    // Skip CSRF for auth endpoints (they have their own protection)
    if (!pathname.startsWith('/api/auth/')) {
      if (!validateCSRFToken(request)) {
        return new NextResponse(JSON.stringify({ error: 'Invalid CSRF token' }), {
          status: 403,
          headers: {
            'Content-Type': 'application/json',
          },
        });
      }
    }
  }

  // Authentication check for protected routes
  if (
    pathname.startsWith('/(authenticated)') ||
    (pathname.startsWith('/api/') && !pathname.startsWith('/api/auth/'))
  ) {
    const token = request.cookies.get('access_token')?.value;

    if (!token) {
      return handleUnauthenticated(request, pathname);
    }

    // Validate token with proper server-side verification
    const tokenValidation = await validateJWTTokenServerSide(token);
    if (!tokenValidation.isValid) {
      // If server-side validation fails, try fallback for development
      const fallbackValidation = validateJWTTokenFallback(token);
      if (!fallbackValidation.isValid || process.env.NODE_ENV === 'production') {
        // Clear invalid token
        const response = handleUnauthenticated(request, pathname);
        response.cookies.delete('access_token');
        response.cookies.delete('refresh_token');
        return response;
      }
      // Use fallback validation results
      tokenValidation.isValid = fallbackValidation.isValid;
      tokenValidation.expiresIn = fallbackValidation.expiresIn;
    }

    // Check if token is close to expiration (refresh if < 5 minutes left)
    if (tokenValidation.expiresIn < 300) {
      // 5 minutes in seconds
      // Add header to trigger client-side refresh
      const response = NextResponse.next();
      response.headers.set('X-Token-Refresh-Required', 'true');
      return response;
    }
  }

  // Security headers
  const response = NextResponse.next();

  response.headers.set('X-DNS-Prefetch-Control', 'on');
  response.headers.set('X-XSS-Protection', '1; mode=block');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');

  // Strict Transport Security for production and staging
  if (environmentConfig.isProduction || environmentConfig.isStaging) {
    response.headers.set(
      'Strict-Transport-Security',
      'max-age=31536000; includeSubDomains; preload'
    );
  }

  // Content Security Policy
  const csp = `
    default-src 'self';
    script-src 'self' ${environmentConfig.isDevelopment ? "'unsafe-eval'" : ''};
    style-src 'self' 'unsafe-inline';
    img-src 'self' data: https:;
    font-src 'self';
    connect-src 'self' ${environmentConfig.apiUrl};
    frame-ancestors 'none';
    base-uri 'self';
    form-action 'self';
  `
    .replace(/\s+/g, ' ')
    .trim();

  response.headers.set('Content-Security-Policy', csp);

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
