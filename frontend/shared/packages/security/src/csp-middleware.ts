/**
 * Centralized CSP Middleware
 * Provides consistent, secure CSP implementation across all applications
 */

import { NextRequest, NextResponse } from 'next/server';
import { generateNonce } from '../utils/nonce';

export interface CSPConfig {
  enableStrictCSP: boolean;
  allowedScriptSources: string[];
  allowedStyleSources: string[];
  allowedImageSources: string[];
  allowedConnectSources: string[];
  isDevelopment: boolean;
}

const DEFAULT_CONFIG: CSPConfig = {
  enableStrictCSP: true,
  allowedScriptSources: [],
  allowedStyleSources: ['https://fonts.googleapis.com'],
  allowedImageSources: ['data:', 'https:'],
  allowedConnectSources: ['https://api.dotmac.dev', 'wss://api.dotmac.dev'],
  isDevelopment: process.env.NODE_ENV === 'development',
};

export function createCSPMiddleware(config: Partial<CSPConfig> = {}) {
  const finalConfig = { ...DEFAULT_CONFIG, ...config };

  return function cspMiddleware(request: NextRequest) {
    const response = NextResponse.next();

    // Generate nonce for this request
    const nonce = generateNonce();

    // Set nonce in request headers for use in components
    response.headers.set('x-nonce', nonce);

    // Generate and set CSP header
    const csp = generateSecureCSP(nonce, finalConfig);
    response.headers.set('Content-Security-Policy', csp);

    // Add security headers
    setSecurityHeaders(response);

    return response;
  };
}

function generateSecureCSP(nonce: string, config: CSPConfig): string {
  const isDev = config.isDevelopment;

  const policies = [
    "default-src 'self'",

    // Scripts: Use nonce in production, allow eval in development only
    isDev
      ? `script-src 'self' 'nonce-${nonce}' 'unsafe-eval'`
      : `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'`,

    // Styles: Use nonce in production, allow unsafe-inline in development only
    isDev
      ? `style-src 'self' 'unsafe-inline' ${config.allowedStyleSources.join(' ')}`
      : `style-src 'self' 'nonce-${nonce}' ${config.allowedStyleSources.join(' ')}`,

    // Images
    `img-src 'self' ${config.allowedImageSources.join(' ')}`,

    // Fonts
    "font-src 'self' https://fonts.gstatic.com data:",

    // Connections
    isDev
      ? `connect-src 'self' ${config.allowedConnectSources.join(' ')} http://localhost:* ws://localhost:* wss://localhost:*`
      : `connect-src 'self' ${config.allowedConnectSources.join(' ')}`,

    // Security directives
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "object-src 'none'",

    // Enable upgrade insecure requests in production
    ...(isDev ? [] : ['upgrade-insecure-requests']),
  ];

  return policies.join('; ');
}

function setSecurityHeaders(response: NextResponse): void {
  // Strict Transport Security
  if (process.env.NODE_ENV === 'production') {
    response.headers.set(
      'Strict-Transport-Security',
      'max-age=31536000; includeSubDomains; preload'
    );
  }

  // Prevent clickjacking
  response.headers.set('X-Frame-Options', 'DENY');

  // Prevent MIME type sniffing
  response.headers.set('X-Content-Type-Options', 'nosniff');

  // Referrer policy
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin');

  // XSS protection (legacy but still useful)
  response.headers.set('X-XSS-Protection', '1; mode=block');

  // Permissions policy
  response.headers.set(
    'Permissions-Policy',
    'geolocation=(self), microphone=(), camera=(), payment=()'
  );
}

// Utility to extract nonce from request
export function getNonceFromRequest(request: NextRequest): string | null {
  return request.headers.get('x-nonce') ?? null;
}

// Hook for React components to get nonce
export function useNonce(): string | null {
  if (typeof window !== 'undefined') {
    // Client-side: try to get nonce from meta tag or script tag
    const metaCSP = document.querySelector('meta[http-equiv="Content-Security-Policy"]');
    if (metaCSP) {
      const content = metaCSP.getAttribute('content');
      if (content) {
        const match = content.match(/'nonce-([^']+)'/);
        return match ? match[1] || null : null;
      }
    }
  }
  return null;
}
