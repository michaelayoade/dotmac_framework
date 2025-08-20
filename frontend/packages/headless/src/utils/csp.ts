/**
 * Content Security Policy utilities for nonce generation and management
 */

import { randomBytes } from 'crypto';

/**
 * Generate a cryptographically secure nonce for CSP
 */
export function generateNonce(): string {
  return randomBytes(16).toString('base64');
}

/**
 * Generate CSP header with nonce support
 */
export function generateCSP(nonce: string, isDevelopment = false): string {
  const policies = [
    `default-src 'self'`,
    // Use nonce for scripts instead of unsafe-inline
    `script-src 'self' 'nonce-${nonce}'${isDevelopment ? " 'unsafe-eval'" : ''}`,
    // Keep unsafe-inline for styles until we migrate to CSS modules/styled-components
    `style-src 'self' 'unsafe-inline' fonts.googleapis.com`,
    `font-src 'self' fonts.gstatic.com data:`,
    `img-src 'self' data: blob: https:`,
    `connect-src 'self' ws: wss: https:`,
    `frame-ancestors 'none'`,
    `base-uri 'self'`,
    `form-action 'self'`,
    `object-src 'none'`,
    `upgrade-insecure-requests`,
  ];

  return policies.join('; ');
}

/**
 * Generate CSP meta tag for client-side enforcement
 */
export function generateCSPMeta(nonce: string): string {
  const csp = generateCSP(nonce, process.env.NODE_ENV === 'development');
  return `<meta http-equiv="Content-Security-Policy" content="${csp}">`;
}

/**
 * Extract nonce from CSP header
 */
export function extractNonce(cspHeader: string): string | null {
  const match = cspHeader.match(/'nonce-([^']+)'/);
  return match ? match[1] : null;
}

/**
 * Validate nonce format
 */
export function isValidNonce(nonce: string): boolean {
  // Base64 encoded 16 bytes = 24 chars (with padding)
  return /^[A-Za-z0-9+/]{22}==$/.test(nonce);
}