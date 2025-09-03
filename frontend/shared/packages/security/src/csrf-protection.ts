/**
 * CSRF Protection Implementation for DotMac Portal Ecosystem
 *
 * This module provides Cross-Site Request Forgery (CSRF) protection
 * across all portals in the DotMac ISP management system.
 *
 * Usage:
 * - Server-side: Generate and validate CSRF tokens
 * - Client-side: Include tokens in forms and API requests
 *
 * Security features:
 * - Cryptographically secure token generation
 * - Time-based token expiration
 * - Double-submit cookie pattern
 * - SameSite cookie attributes
 */

import { createHash, randomBytes } from 'crypto';

export interface CSRFConfig {
  tokenLength: number;
  cookieName: string;
  headerName: string;
  maxAge: number; // in seconds
  sameSite: 'strict' | 'lax' | 'none';
  secure: boolean;
  httpOnly: boolean;
}

export interface CSRFToken {
  token: string;
  expires: number;
  hash: string;
}

export class CSRFProtection {
  private config: CSRFConfig;
  private secret: string;

  constructor(secret: string, config?: Partial<CSRFConfig>) {
    if (!secret || secret.length < 32) {
      throw new Error('CSRF secret must be at least 32 characters long');
    }

    this.secret = secret;
    this.config = {
      tokenLength: 32,
      cookieName: 'csrf-token',
      headerName: 'x-csrf-token',
      maxAge: 3600, // 1 hour
      sameSite: 'strict',
      secure: process.env.NODE_ENV === 'production',
      httpOnly: true,
      ...config,
    };
  }

  /**
   * Generate a new CSRF token
   */
  generateToken(): CSRFToken {
    const token = randomBytes(this.config.tokenLength).toString('hex');
    const expires = Date.now() + this.config.maxAge * 1000;
    const hash = this.createTokenHash(token, expires);

    return {
      token,
      expires,
      hash,
    };
  }

  /**
   * Validate a CSRF token
   */
  validateToken(token: string, cookieToken?: string): boolean {
    if (!token || !cookieToken) {
      return false;
    }

    // Implement double-submit cookie pattern
    if (token !== cookieToken) {
      return false;
    }

    // Parse token components
    try {
      const [tokenValue, expiresStr, hash] = token.split('.');
      const expires = parseInt(expiresStr, 10);

      // Check expiration
      if (Date.now() > expires) {
        return false;
      }

      // Verify token hash
      const expectedHash = this.createTokenHash(tokenValue, expires);
      return this.secureCompare(hash, expectedHash);
    } catch (error) {
      return false;
    }
  }

  /**
   * Create token hash for validation
   */
  private createTokenHash(token: string, expires: number): string {
    const data = `${token}.${expires}.${this.secret}`;
    return createHash('sha256').update(data).digest('hex');
  }

  /**
   * Secure string comparison to prevent timing attacks
   */
  private secureCompare(a: string, b: string): boolean {
    if (a.length !== b.length) {
      return false;
    }

    let result = 0;
    for (let i = 0; i < a.length; i++) {
      result |= a.charCodeAt(i) ^ b.charCodeAt(i);
    }

    return result === 0;
  }

  /**
   * Get cookie options for CSRF token
   */
  getCookieOptions(): {
    maxAge: number;
    httpOnly: boolean;
    secure: boolean;
    sameSite: 'strict' | 'lax' | 'none';
    path: string;
  } {
    return {
      maxAge: this.config.maxAge * 1000,
      httpOnly: this.config.httpOnly,
      secure: this.config.secure,
      sameSite: this.config.sameSite,
      path: '/',
    };
  }

  /**
   * Get header name for CSRF token
   */
  getHeaderName(): string {
    return this.config.headerName;
  }

  /**
   * Get cookie name for CSRF token
   */
  getCookieName(): string {
    return this.config.cookieName;
  }
}

/**
 * Next.js middleware helper for CSRF protection
 */
export function createCSRFMiddleware(csrfProtection: CSRFProtection) {
  return async (request: Request): Promise<Response | null> => {
    const url = new URL(request.url);

    // Skip CSRF protection for safe methods
    if (['GET', 'HEAD', 'OPTIONS'].includes(request.method)) {
      return null;
    }

    // Skip for API routes that use other authentication
    if (url.pathname.startsWith('/api/auth/')) {
      return null;
    }

    const cookieHeader = request.headers.get('cookie');
    const csrfHeader = request.headers.get(csrfProtection.getHeaderName());

    let cookieToken = '';
    if (cookieHeader) {
      const cookies = Object.fromEntries(
        cookieHeader.split('; ').map((c) => {
          const [key, ...v] = c.split('=');
          return [key, v.join('=')];
        })
      );
      cookieToken = cookies[csrfProtection.getCookieName()] || '';
    }

    if (!csrfProtection.validateToken(csrfHeader || '', cookieToken)) {
      return new Response(
        JSON.stringify({
          error: 'CSRF token validation failed',
          code: 'CSRF_INVALID',
        }),
        {
          status: 403,
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );
    }

    return null;
  };
}

/**
 * React hook for CSRF protection in forms
 */
export interface UseCSRFReturn {
  token: string;
  headers: Record<string, string>;
  formProps: Record<string, string>;
}

/**
 * Default CSRF protection instance
 * Uses environment variable for secret in production
 */
export const defaultCSRFProtection = new CSRFProtection(
  process.env.CSRF_SECRET || 'development-secret-change-in-production-minimum-32-chars'
);
