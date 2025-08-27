/**
 * Next.js Middleware for CSRF Protection
 * 
 * This middleware integrates CSRF protection into Next.js applications
 * across the DotMac portal ecosystem.
 */

import { NextRequest, NextResponse } from 'next/server';
import { CSRFProtection } from '../csrf-protection';

export interface CSRFMiddlewareConfig {
  excludePaths?: string[];
  includePaths?: string[];
  safeMethods?: string[];
  cookieName?: string;
  headerName?: string;
}

export class CSRFMiddleware {
  private csrfProtection: CSRFProtection;
  private config: Required<CSRFMiddlewareConfig>;

  constructor(secret: string, config?: CSRFMiddlewareConfig) {
    this.csrfProtection = new CSRFProtection(secret);
    this.config = {
      excludePaths: [
        '/api/auth/',
        '/api/health/',
        '/_next/',
        '/favicon.ico',
        '/public/',
        ...(config?.excludePaths || [])
      ],
      includePaths: config?.includePaths || ['/api/', '/'],
      safeMethods: config?.safeMethods || ['GET', 'HEAD', 'OPTIONS'],
      cookieName: config?.cookieName || 'csrf-token',
      headerName: config?.headerName || 'x-csrf-token',
    };
  }

  /**
   * Main middleware function for Next.js
   */
  middleware = (request: NextRequest): NextResponse | Promise<NextResponse> => {
    const { pathname } = request.nextUrl;
    const method = request.method;

    // Skip CSRF protection for excluded paths
    if (this.shouldExclude(pathname)) {
      return NextResponse.next();
    }

    // Skip for safe methods
    if (this.config.safeMethods.includes(method)) {
      return this.handleSafeRequest(request);
    }

    // Validate CSRF token for unsafe methods
    return this.validateCSRFToken(request);
  };

  /**
   * Handle safe HTTP methods (GET, HEAD, OPTIONS)
   * Generate and set CSRF token cookie if not present
   */
  private handleSafeRequest(request: NextRequest): NextResponse {
    const response = NextResponse.next();
    const existingToken = request.cookies.get(this.config.cookieName);

    // Generate new token if none exists or expired
    if (!existingToken || !this.isTokenValid(existingToken.value)) {
      const { token } = this.csrfProtection.generateToken();
      const cookieOptions = this.csrfProtection.getCookieOptions();

      response.cookies.set(this.config.cookieName, token, cookieOptions);
      
      // Add token to response headers for client-side access
      response.headers.set('x-csrf-token-generated', token);
    }

    return response;
  }

  /**
   * Validate CSRF token for unsafe methods
   */
  private validateCSRFToken(request: NextRequest): NextResponse {
    const cookieToken = request.cookies.get(this.config.cookieName)?.value;
    const headerToken = request.headers.get(this.config.headerName);

    // Check if tokens are present
    if (!cookieToken || !headerToken) {
      return this.createCSRFErrorResponse('CSRF token missing');
    }

    // Validate token
    if (!this.csrfProtection.validateToken(headerToken, cookieToken)) {
      return this.createCSRFErrorResponse('CSRF token invalid');
    }

    return NextResponse.next();
  }

  /**
   * Check if path should be excluded from CSRF protection
   */
  private shouldExclude(pathname: string): boolean {
    return this.config.excludePaths.some(path => pathname.startsWith(path));
  }

  /**
   * Check if token is valid (basic check)
   */
  private isTokenValid(token: string): boolean {
    return token && token.length > 0;
  }

  /**
   * Create error response for CSRF failures
   */
  private createCSRFErrorResponse(message: string): NextResponse {
    const isApiRequest = this.isApiRequest();
    
    if (isApiRequest) {
      return NextResponse.json(
        {
          error: 'CSRF Protection',
          message,
          code: 'CSRF_INVALID',
        },
        { status: 403 }
      );
    }

    // For non-API requests, redirect to error page
    return NextResponse.redirect(new URL('/security-error', process.env.NEXTAUTH_URL || 'http://localhost:3000'));
  }

  /**
   * Check if current request is an API request
   */
  private isApiRequest(): boolean {
    return typeof window === 'undefined'; // Server-side check
  }
}

/**
 * Factory function to create CSRF middleware
 */
export function createCSRFMiddleware(secret?: string, config?: CSRFMiddlewareConfig): CSRFMiddleware {
  const csrfSecret = secret || process.env.CSRF_SECRET || 'development-csrf-secret-change-in-production-min-32-chars';
  
  if (!csrfSecret || csrfSecret.length < 32) {
    throw new Error('CSRF secret must be at least 32 characters long');
  }

  return new CSRFMiddleware(csrfSecret, config);
}

/**
 * Utility function to get CSRF token from cookies (client-side)
 */
export function getCSRFToken(): string | null {
  if (typeof document === 'undefined') {
    return null;
  }

  const cookies = document.cookie.split(';');
  for (const cookie of cookies) {
    const [name, value] = cookie.trim().split('=');
    if (name === 'csrf-token') {
      return decodeURIComponent(value);
    }
  }
  
  return null;
}

/**
 * Utility function to add CSRF token to fetch requests
 */
export function addCSRFToken(init: RequestInit = {}): RequestInit {
  const token = getCSRFToken();
  
  if (!token) {
    console.warn('CSRF token not found. Request may fail.');
    return init;
  }

  return {
    ...init,
    headers: {
      ...init.headers,
      'x-csrf-token': token,
    },
  };
}

/**
 * Enhanced fetch wrapper with CSRF protection
 */
export async function secureCSRFFetch(
  input: RequestInfo | URL,
  init?: RequestInit
): Promise<Response> {
  const enhancedInit = addCSRFToken(init);
  return fetch(input, enhancedInit);
}