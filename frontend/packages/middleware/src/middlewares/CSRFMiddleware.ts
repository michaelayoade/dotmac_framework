/**
 * CSRF Protection Middleware
 * Handles CSRF token validation for state-changing requests
 */

import { NextResponse } from 'next/server';
import type { MiddlewareFunction, MiddlewareContext, CSRFConfig } from '../types';
import { isPublicRoute } from '../utils';

/**
 * Default CSRF configuration
 */
const DEFAULT_CSRF_CONFIG: CSRFConfig = {
  cookieName: 'csrf-token',
  headerName: 'x-csrf-token',
  excludePaths: ['/api/auth', '/api/health'],
  excludeMethods: ['GET', 'HEAD', 'OPTIONS']
};

/**
 * CSRF middleware factory
 */
export function createCSRFMiddleware(
  publicRoutes: string[],
  config: Partial<CSRFConfig> = {}
): MiddlewareFunction {
  const csrfConfig = { ...DEFAULT_CSRF_CONFIG, ...config };

  return async (context: MiddlewareContext) => {
    const { request, pathname } = context;
    const { method } = request;

    // Skip CSRF for safe methods
    if (csrfConfig.excludeMethods.includes(method)) {
      return null;
    }

    // Skip CSRF for public routes
    if (isPublicRoute(pathname, publicRoutes)) {
      return null;
    }

    // Skip CSRF for excluded paths
    if (csrfConfig.excludePaths.some(path => pathname.startsWith(path))) {
      return null;
    }

    // Get CSRF tokens
    const requestCsrfToken = 
      request.headers.get(csrfConfig.headerName) ||
      context.csrfToken;

    const storedCsrfToken = context.csrfToken;

    // Validate CSRF token
    if (!requestCsrfToken || !storedCsrfToken || requestCsrfToken !== storedCsrfToken) {
      return NextResponse.json(
        { 
          error: 'CSRF token mismatch',
          message: 'Invalid or missing CSRF token. Please refresh the page and try again.'
        },
        { 
          status: 403,
          headers: {
            'Cache-Control': 'no-store'
          }
        }
      );
    }

    // Continue to next middleware
    return null;
  };
}

/**
 * CSRF token generator middleware
 * Ensures CSRF tokens are available for client-side requests
 */
export function createCSRFTokenMiddleware(
  cookieName: string = 'csrf-token'
): MiddlewareFunction {
  return (context: MiddlewareContext) => {
    const { request } = context;
    
    // Check if CSRF token exists
    const existingToken = request.cookies.get(cookieName)?.value;
    
    if (existingToken) {
      return null; // Token exists, continue
    }

    // Generate new CSRF token
    const csrfToken = generateCSRFToken();
    
    // Create response with CSRF token cookie
    const response = NextResponse.next();
    
    response.cookies.set(cookieName, csrfToken, {
      httpOnly: false, // Allow JavaScript access for CSRF token
      secure: process.env.NODE_ENV === 'production',
      sameSite: 'strict',
      maxAge: 60 * 60 * 24, // 24 hours
      path: '/'
    });

    return response;
  };
}

/**
 * Generate secure CSRF token
 */
function generateCSRFToken(): string {
  const array = new Uint8Array(32);
  
  if (typeof crypto !== 'undefined' && crypto.getRandomValues) {
    crypto.getRandomValues(array);
  } else {
    // Fallback for environments without crypto
    for (let i = 0; i < array.length; i++) {
      array[i] = Math.floor(Math.random() * 256);
    }
  }
  
  return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
}