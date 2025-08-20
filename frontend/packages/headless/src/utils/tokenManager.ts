/**
 * Secure JWT token management with validation and refresh logic
 */

import { secureStorage } from './secureStorage';

export interface TokenPayload {
  sub: string; // subject (user ID)
  iat: number; // issued at
  exp: number; // expiration
  aud: string; // audience
  iss: string; // issuer
  jti: string; // JWT ID
  portal: string; // portal type
  tenant: string; // tenant ID
  roles: string[];
  permissions: string[];
}

export interface TokenPair {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

class TokenManager {
  private readonly ACCESS_TOKEN_KEY = 'access_token';
  private readonly REFRESH_TOKEN_KEY = 'refresh_token';
  private readonly TOKEN_EXPIRY_KEY = 'token_expiry';
  private readonly CSRF_TOKEN_KEY = 'csrf_token';

  // Buffer time before token expiry to refresh (5 minutes)
  private readonly REFRESH_BUFFER = 5 * 60 * 1000;

  // Valid token signing algorithms (whitelist)
  private readonly VALID_ALGORITHMS = ['RS256', 'ES256', 'HS256'];

  private refreshPromise: Promise<TokenPair | null> | null = null;

  /**
   * Store token pair securely
   */
  setTokens(tokenPair: TokenPair, csrfToken?: string): void {
    try {
      // Store access token in memory/sessionStorage (shorter-lived)
      secureStorage.setItem(this.ACCESS_TOKEN_KEY, tokenPair.accessToken, {
        secure: true,
        maxAge: 15 * 60, // 15 minutes
      });

      // Store refresh token in httpOnly cookie (longer-lived, more secure)
      // Note: In a real implementation, this would be set by the server as httpOnly
      secureStorage.setItem(this.REFRESH_TOKEN_KEY, tokenPair.refreshToken, {
        secure: true,
        httpOnly: false, // Would be true if set by server
        maxAge: 7 * 24 * 60 * 60, // 7 days
      });

      // Store expiry timestamp
      secureStorage.setItem(this.TOKEN_EXPIRY_KEY, tokenPair.expiresAt.toString());

      // Store CSRF token if provided
      if (csrfToken) {
        secureStorage.setItem(this.CSRF_TOKEN_KEY, csrfToken, {
          secure: true,
          maxAge: 15 * 60, // 15 minutes
        });
      }
    } catch (_error) {
      throw new Error('Token storage failed');
    }
  }

  /**
   * Get access token with automatic validation
   */
  getAccessToken(): string | null {
    try {
      const token = secureStorage.getItem(this.ACCESS_TOKEN_KEY);

      if (!token) {
        return null;
      }

      // Validate token format and expiry
      if (!this.validateTokenFormat(token)) {
        this.clearTokens();
        return null;
      }

      // Check if token is expired or needs refresh
      if (this.isTokenExpired(token) || this.shouldRefreshToken()) {
        return null;
      }

      return token;
    } catch (_error) {
      return null;
    }
  }

  /**
   * Get refresh token
   */
  getRefreshToken(): string | null {
    return secureStorage.getItem(this.REFRESH_TOKEN_KEY);
  }

  /**
   * Get CSRF token
   */
  getCSRFToken(): string | null {
    return secureStorage.getItem(this.CSRF_TOKEN_KEY);
  }

  /**
   * Clear all tokens
   */
  clearTokens(): void {
    secureStorage.removeItem(this.ACCESS_TOKEN_KEY);
    secureStorage.removeItem(this.REFRESH_TOKEN_KEY);
    secureStorage.removeItem(this.TOKEN_EXPIRY_KEY);
    secureStorage.removeItem(this.CSRF_TOKEN_KEY);
  }

  /**
   * Decode JWT payload (without verification - for client-side use only)
   */
  decodeTokenPayload(token: string): TokenPayload | null {
    try {
      const parts = token.split('.');
      if (parts.length !== 3) {
        return null;
      }

      // Decode payload (base64url)
      const payload = parts[1];
      if (!payload) {
        return null;
      }
      const decoded = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
      return JSON.parse(decoded) as TokenPayload;
    } catch (_error) {
      return null;
    }
  }

  // Token validation composition helpers
  private static TokenValidationHelpers = {
    validateTokenParts: (token: string): boolean => {
      const parts = token.split('.');
      return parts.length === 3;
    },

    decodeTokenHeader: (token: string): { alg: string } | null => {
      try {
        const parts = token.split('.');
        const header = parts[0];
        if (!header) {
          return null;
        }
        const headerB64 = header.replace(/-/g, '+').replace(/_/g, '/');
        return JSON.parse(atob(headerB64));
      } catch {
        return null;
      }
    },

    validateAlgorithm: (algorithm: string, validAlgorithms: string[]): boolean => {
      if (!validAlgorithms.includes(algorithm)) {
        return false;
      }
      return true;
    },

    validateRequiredFields: (payload: TokenPayload): boolean => {
      const requiredFields = ['sub', 'iat', 'exp', 'aud', 'iss'];
      const hasAllFields = requiredFields.every((field) => payload[field as keyof TokenPayload]);

      if (!hasAllFields) {
        return false;
      }
      return true;
    },

    validateIssuer: (issuer: string): boolean => {
      const expectedIssuer = process.env.NEXT_PUBLIC_JWT_ISSUER || 'dotmac-platform';
      if (issuer !== expectedIssuer) {
        return false;
      }
      return true;
    },

    validateAudience: (audience: string): boolean => {
      const expectedAudience = process.env.NEXT_PUBLIC_JWT_AUDIENCE || 'dotmac-frontend';
      if (audience !== expectedAudience) {
        return false;
      }
      return true;
    },
  };

  /**
   * Validate token format and basic security checks
   */
  validateTokenFormat(token: string): boolean {
    try {
      // Validate token structure
      if (!TokenManager.TokenValidationHelpers.validateTokenParts(token)) {
        return false;
      }

      // Validate algorithm
      const header = TokenManager.TokenValidationHelpers.decodeTokenHeader(token);
      if (
        !header ||
        !TokenManager.TokenValidationHelpers.validateAlgorithm(header.alg, this.VALID_ALGORITHMS)
      ) {
        return false;
      }

      // Decode and validate payload
      const payload = this.decodeTokenPayload(token);
      if (!payload) {
        return false;
      }

      // Run all payload validations
      return (
        TokenManager.TokenValidationHelpers.validateRequiredFields(payload) &&
        TokenManager.TokenValidationHelpers.validateIssuer(payload.iss) &&
        TokenManager.TokenValidationHelpers.validateAudience(payload.aud)
      );
    } catch (_error) {
      return false;
    }
  }

  /**
   * Check if token is expired
   */
  isTokenExpired(token?: string): boolean {
    try {
      const tokenToCheck = token || this.getAccessToken();
      if (!tokenToCheck) {
        return true;
      }

      const payload = this.decodeTokenPayload(tokenToCheck);
      if (!payload) {
        return true;
      }

      // Check expiration with buffer
      const now = Math.floor(Date.now() / 1000);
      return payload.exp <= now;
    } catch (_error) {
      return true;
    }
  }

  /**
   * Check if token should be refreshed (before it expires)
   */
  shouldRefreshToken(): boolean {
    try {
      const expiryStr = secureStorage.getItem(this.TOKEN_EXPIRY_KEY);
      if (!expiryStr) {
        return true;
      }

      const expiry = parseInt(expiryStr, 10);
      const now = Date.now();

      // Refresh if within buffer time of expiry
      return expiry - now <= this.REFRESH_BUFFER;
    } catch (_error) {
      return true;
    }
  }

  /**
   * Refresh tokens with deduplication
   */
  async refreshTokens(
    apiRefreshFunction: (refreshToken: string) => Promise<TokenPair>
  ): Promise<TokenPair | null> {
    // Prevent multiple simultaneous refresh attempts
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = this.performTokenRefresh(apiRefreshFunction);

    try {
      return await this.refreshPromise;
    } finally {
      this.refreshPromise = null;
    }
  }

  /**
   * Perform the actual token refresh
   */
  private async performTokenRefresh(
    apiRefreshFunction: (refreshToken: string) => Promise<TokenPair>
  ): Promise<TokenPair | null> {
    try {
      const refreshToken = this.getRefreshToken();
      if (!refreshToken) {
        return null;
      }

      // Validate refresh token
      if (this.isTokenExpired(refreshToken)) {
        this.clearTokens();
        return null;
      }
      const newTokens = await apiRefreshFunction(refreshToken);

      // Store new tokens
      this.setTokens(newTokens);
      return newTokens;
    } catch (_error) {
      this.clearTokens();
      return null;
    }
  }

  /**
   * Get token info for debugging (non-sensitive data only)
   */
  getTokenInfo(): {
    hasAccessToken: boolean;
    hasRefreshToken: boolean;
    expiresAt: number | null;
    payload: Partial<TokenPayload> | null;
  } {
    const accessToken = this.getAccessToken();
    const refreshToken = this.getRefreshToken();
    const expiryStr = secureStorage.getItem(this.TOKEN_EXPIRY_KEY);

    let payload: Partial<TokenPayload> | null = null;
    if (accessToken) {
      const fullPayload = this.decodeTokenPayload(accessToken);
      if (fullPayload) {
        // Return only non-sensitive fields
        payload = {
          portal: fullPayload.portal,
          tenant: fullPayload.tenant,
          roles: fullPayload.roles,
          exp: fullPayload.exp,
          iat: fullPayload.iat,
        };
      }
    }

    return {
      hasAccessToken: !!accessToken,
      hasRefreshToken: !!refreshToken,
      expiresAt: expiryStr ? parseInt(expiryStr, 10) : null,
      payload,
    };
  }

  /**
   * Auto-refresh token setup
   */
  setupAutoRefresh(
    apiRefreshFunction: (refreshToken: string) => Promise<TokenPair>,
    onRefreshFailed?: () => void
  ): () => void {
    const checkAndRefresh = async () => {
      if (this.shouldRefreshToken() && this.getRefreshToken()) {
        const result = await this.refreshTokens(apiRefreshFunction);
        if (!result && onRefreshFailed) {
          onRefreshFailed();
        }
      }
    };

    // Check every minute
    const interval = setInterval(checkAndRefresh, 60 * 1000);

    // Initial check
    checkAndRefresh();

    // Return cleanup function
    return () => clearInterval(interval);
  }
}

// Export singleton instance
export const tokenManager = new TokenManager();
