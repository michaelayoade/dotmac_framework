/**
 * Security Middleware
 * Handles CSP, security headers, and nonce generation
 */

import { NextResponse } from 'next/server';
import { generateNonce, generateCSP } from '@dotmac/headless/utils/csp';
import type { MiddlewareFunction, MiddlewareContext, SecurityLevel } from '../types';

/**
 * Generate security headers based on security level
 */
function getSecurityHeaders(securityLevel: SecurityLevel, nonce: string, development: boolean) {
  const csp = generateCSP(nonce, development);

  const baseHeaders = {
    'Content-Security-Policy': csp,
    'X-Frame-Options': 'DENY',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'X-XSS-Protection': '1; mode=block',
  };

  // Add production-only headers
  if (!development) {
    (baseHeaders as any)['Strict-Transport-Security'] =
      'max-age=31536000; includeSubDomains; preload';
  }

  // Security level specific headers
  switch (securityLevel) {
    case 'maximum':
      return {
        ...baseHeaders,
        'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=(), usb=()',
        'Cross-Origin-Embedder-Policy': 'require-corp',
        'Cross-Origin-Opener-Policy': 'same-origin',
        'Cross-Origin-Resource-Policy': 'same-origin',
        'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
        Pragma: 'no-cache',
        Expires: '0',
      };

    case 'high':
      return {
        ...baseHeaders,
        'Permissions-Policy': 'camera=(), microphone=(), geolocation=(), payment=()',
        'Cache-Control': 'no-store, no-cache, must-revalidate',
        Pragma: 'no-cache',
      };

    case 'medium':
      return {
        ...baseHeaders,
        'Permissions-Policy': 'camera=(), microphone=()',
        'Cache-Control': 'private, max-age=0',
      };

    case 'low':
    default:
      return {
        ...baseHeaders,
        'Cache-Control': 'private, max-age=300',
      };
  }
}

/**
 * Security middleware factory
 */
export function createSecurityMiddleware(
  securityLevel: SecurityLevel = 'medium',
  development: boolean = false,
  customHeaders: Record<string, string> = {}
): MiddlewareFunction {
  return (context: MiddlewareContext) => {
    // Generate nonce for this request
    const nonce = generateNonce();
    context.nonce = nonce;

    // Add nonce to request headers
    const requestHeaders = new Headers(context.request.headers);
    requestHeaders.set('x-nonce', nonce);

    // Create response
    const response = NextResponse.next({
      request: {
        headers: requestHeaders,
      },
    });

    // Add security headers
    const securityHeaders = getSecurityHeaders(securityLevel, nonce, development);

    Object.entries(securityHeaders).forEach(([key, value]) => {
      response.headers.set(key, value);
    });

    // Add custom headers
    Object.entries(customHeaders).forEach(([key, value]) => {
      response.headers.set(key, value);
    });

    // Add trace headers
    response.headers.set('x-trace-id', context.traceId);
    response.headers.set('x-correlation-id', context.correlationId);

    return response;
  };
}
