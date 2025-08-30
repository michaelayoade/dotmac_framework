/**
 * Token Management Service
 *
 * Secure handling of authentication tokens with automatic refresh,
 * secure storage, and cross-tab synchronization
 */

interface TokenPair {
  accessToken: string;
  refreshToken: string;
  expiresAt: number;
}

interface TokenStorage {
  getTokens(): Promise<TokenPair | null>;
  setTokens(tokens: TokenPair): Promise<void>;
  clearTokens(): Promise<void>;
}

/**
 * Secure token storage implementation
 * Uses multiple storage mechanisms for security and reliability
 */
class SecureTokenStorage implements TokenStorage {
  private readonly ACCESS_TOKEN_KEY = 'auth_access_token';
  private readonly REFRESH_TOKEN_KEY = 'auth_refresh_token';
  private readonly EXPIRES_AT_KEY = 'auth_expires_at';

  async getTokens(): Promise<TokenPair | null> {
    try {
      // Try to get from memory first (if available)
      if (this.memoryTokens) {
        return this.memoryTokens;
      }

      // Get from secure storage
      const accessToken = await this.getSecureItem(this.ACCESS_TOKEN_KEY);
      const refreshToken = await this.getSecureItem(this.REFRESH_TOKEN_KEY);
      const expiresAtStr = await this.getSecureItem(this.EXPIRES_AT_KEY);

      if (!accessToken || !refreshToken || !expiresAtStr) {
        return null;
      }

      const tokens: TokenPair = {
        accessToken,
        refreshToken,
        expiresAt: parseInt(expiresAtStr, 10),
      };

      // Store in memory for faster access
      this.memoryTokens = tokens;

      return tokens;
    } catch (error) {
      console.error('Failed to get tokens:', error);
      return null;
    }
  }

  async setTokens(tokens: TokenPair): Promise<void> {
    try {
      // Store in memory
      this.memoryTokens = tokens;

      // Store securely
      await Promise.all([
        this.setSecureItem(this.ACCESS_TOKEN_KEY, tokens.accessToken),
        this.setSecureItem(this.REFRESH_TOKEN_KEY, tokens.refreshToken),
        this.setSecureItem(this.EXPIRES_AT_KEY, tokens.expiresAt.toString()),
      ]);

      // Notify other tabs
      this.broadcastTokenUpdate(tokens);
    } catch (error) {
      console.error('Failed to set tokens:', error);
      throw new Error('Token storage failed');
    }
  }

  async clearTokens(): Promise<void> {
    try {
      // Clear memory
      this.memoryTokens = null;

      // Clear secure storage
      await Promise.all([
        this.removeSecureItem(this.ACCESS_TOKEN_KEY),
        this.removeSecureItem(this.REFRESH_TOKEN_KEY),
        this.removeSecureItem(this.EXPIRES_AT_KEY),
      ]);

      // Notify other tabs
      this.broadcastTokenClear();
    } catch (error) {
      console.error('Failed to clear tokens:', error);
    }
  }

  private memoryTokens: TokenPair | null = null;

  private async getSecureItem(key: string): Promise<string | null> {
    if (typeof window === 'undefined') return null;

    try {
      // Try sessionStorage first (more secure for tokens)
      let value = sessionStorage.getItem(key);

      // Fallback to localStorage if not in session storage
      if (!value) {
        value = localStorage.getItem(key);
      }

      if (!value) return null;

      // Simple obfuscation (in production, use proper encryption)
      return atob(value);
    } catch {
      return null;
    }
  }

  private async setSecureItem(key: string, value: string): Promise<void> {
    if (typeof window === 'undefined') return;

    try {
      // Simple obfuscation (in production, use proper encryption)
      const obfuscatedValue = btoa(value);

      // Store in sessionStorage (cleared when tab closes)
      sessionStorage.setItem(key, obfuscatedValue);

      // Also store in localStorage as backup (for remember me functionality)
      localStorage.setItem(key, obfuscatedValue);
    } catch (error) {
      console.error(`Failed to store ${key}:`, error);
    }
  }

  private async removeSecureItem(key: string): Promise<void> {
    if (typeof window === 'undefined') return;

    try {
      sessionStorage.removeItem(key);
      localStorage.removeItem(key);
    } catch (error) {
      console.error(`Failed to remove ${key}:`, error);
    }
  }

  private broadcastTokenUpdate(tokens: TokenPair) {
    if (typeof window === 'undefined') return;

    try {
      const event = new CustomEvent('auth-tokens-updated', {
        detail: { tokens },
      });
      window.dispatchEvent(event);
    } catch (error) {
      console.error('Failed to broadcast token update:', error);
    }
  }

  private broadcastTokenClear() {
    if (typeof window === 'undefined') return;

    try {
      const event = new CustomEvent('auth-tokens-cleared');
      window.dispatchEvent(event);
    } catch (error) {
      console.error('Failed to broadcast token clear:', error);
    }
  }
}

export class TokenManager {
  private storage: TokenStorage;
  private refreshTimeout: NodeJS.Timeout | null = null;
  private refreshPromise: Promise<void> | null = null;

  constructor(storage?: TokenStorage) {
    this.storage = storage || new SecureTokenStorage();
    this.setupCrossTabSync();
  }

  /**
   * Get current access token if valid, otherwise attempt refresh
   */
  async getValidToken(): Promise<string | null> {
    const tokens = await this.storage.getTokens();

    if (!tokens) {
      return null;
    }

    // Check if token is still valid (with 1 minute buffer)
    const expiresIn = tokens.expiresAt - Date.now();
    if (expiresIn > 60 * 1000) {
      return tokens.accessToken;
    }

    // Token is expired or expiring soon, try to refresh
    try {
      await this.refreshTokensIfNeeded();
      const refreshedTokens = await this.storage.getTokens();
      return refreshedTokens?.accessToken || null;
    } catch (error) {
      console.error('Token refresh failed:', error);
      await this.storage.clearTokens();
      return null;
    }
  }

  /**
   * Get refresh token
   */
  async getRefreshToken(): Promise<string | null> {
    const tokens = await this.storage.getTokens();
    return tokens?.refreshToken || null;
  }

  /**
   * Set token pair
   */
  async setTokens(tokens: TokenPair): Promise<void> {
    await this.storage.setTokens(tokens);
    this.scheduleRefresh(tokens.expiresAt);
  }

  /**
   * Clear all tokens
   */
  async clearTokens(): Promise<void> {
    await this.storage.clearTokens();
    this.clearRefreshTimeout();
  }

  /**
   * Check if tokens exist
   */
  async hasTokens(): Promise<boolean> {
    const tokens = await this.storage.getTokens();
    return !!tokens;
  }

  /**
   * Check if tokens are valid (not expired)
   */
  async hasValidTokens(): Promise<boolean> {
    const tokens = await this.storage.getTokens();
    if (!tokens) return false;

    return tokens.expiresAt > Date.now();
  }

  /**
   * Get token expiration time
   */
  async getTokenExpiration(): Promise<Date | null> {
    const tokens = await this.storage.getTokens();
    return tokens ? new Date(tokens.expiresAt) : null;
  }

  /**
   * Get time until token expires (in milliseconds)
   */
  async getTimeUntilExpiration(): Promise<number> {
    const tokens = await this.storage.getTokens();
    if (!tokens) return 0;

    return Math.max(0, tokens.expiresAt - Date.now());
  }

  /**
   * Setup automatic token refresh
   */
  setupAutoRefresh(refreshFunction: () => Promise<void>): () => void {
    const refreshTokensWithFunction = async () => {
      try {
        await refreshFunction();
      } catch (error) {
        console.error('Auto refresh failed:', error);
        await this.storage.clearTokens();
      }
    };

    // Set up initial refresh schedule
    this.scheduleAutoRefresh(refreshTokensWithFunction);

    // Return cleanup function
    return () => {
      this.clearRefreshTimeout();
    };
  }

  /**
   * Manually refresh tokens if needed
   */
  private async refreshTokensIfNeeded(): Promise<void> {
    // If already refreshing, wait for that to complete
    if (this.refreshPromise) {
      await this.refreshPromise;
      return;
    }

    const tokens = await this.storage.getTokens();
    if (!tokens) {
      throw new Error('No tokens to refresh');
    }

    const timeUntilExpiry = tokens.expiresAt - Date.now();

    // Only refresh if token expires within 5 minutes
    if (timeUntilExpiry > 5 * 60 * 1000) {
      return;
    }

    // Create refresh promise to prevent concurrent refreshes
    this.refreshPromise = this.performTokenRefresh(tokens.refreshToken);

    try {
      await this.refreshPromise;
    } finally {
      this.refreshPromise = null;
    }
  }

  private async performTokenRefresh(refreshToken: string): Promise<void> {
    // This would typically make an API call to refresh the token
    // For now, we'll simulate it
    const response = await fetch('/api/v1/auth/refresh', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refreshToken }),
    });

    if (!response.ok) {
      throw new Error('Token refresh failed');
    }

    const data = await response.json();

    const newTokens: TokenPair = {
      accessToken: data.tokens.accessToken,
      refreshToken: data.tokens.refreshToken,
      expiresAt: data.tokens.expiresAt,
    };

    await this.setTokens(newTokens);
  }

  private scheduleRefresh(expiresAt: number): void {
    this.clearRefreshTimeout();

    const timeUntilExpiry = expiresAt - Date.now();
    const refreshTime = Math.max(0, timeUntilExpiry - 5 * 60 * 1000); // Refresh 5 minutes before expiry

    if (refreshTime > 0) {
      this.refreshTimeout = setTimeout(() => {
        this.refreshTokensIfNeeded().catch(error => {
          console.error('Scheduled refresh failed:', error);
        });
      }, refreshTime);
    }
  }

  private scheduleAutoRefresh(refreshFunction: () => Promise<void>): void {
    this.clearRefreshTimeout();

    const checkAndRefresh = async () => {
      try {
        const tokens = await this.storage.getTokens();
        if (!tokens) return;

        const timeUntilExpiry = tokens.expiresAt - Date.now();

        // Refresh if token expires within 5 minutes
        if (timeUntilExpiry <= 5 * 60 * 1000 && timeUntilExpiry > 0) {
          await refreshFunction();
        }

        // Schedule next check
        const nextCheckTime = Math.min(60 * 1000, Math.max(10 * 1000, timeUntilExpiry / 2));
        this.refreshTimeout = setTimeout(checkAndRefresh, nextCheckTime);
      } catch (error) {
        console.error('Auto refresh check failed:', error);
      }
    };

    // Start checking
    checkAndRefresh();
  }

  private clearRefreshTimeout(): void {
    if (this.refreshTimeout) {
      clearTimeout(this.refreshTimeout);
      this.refreshTimeout = null;
    }
  }

  /**
   * Setup cross-tab synchronization
   */
  private setupCrossTabSync(): void {
    if (typeof window === 'undefined') return;

    // Listen for token updates from other tabs
    window.addEventListener('auth-tokens-updated', ((event: CustomEvent) => {
      if (event.detail?.tokens) {
        this.scheduleRefresh(event.detail.tokens.expiresAt);
      }
    }) as EventListener);

    // Listen for token clears from other tabs
    window.addEventListener('auth-tokens-cleared', () => {
      this.clearRefreshTimeout();
    });

    // Listen for storage changes (fallback)
    window.addEventListener('storage', (event) => {
      if (event.key?.startsWith('auth_')) {
        // Token storage changed in another tab
        if (!event.newValue) {
          // Token was cleared
          this.clearRefreshTimeout();
        } else {
          // Token was updated, reschedule refresh
          this.storage.getTokens().then(tokens => {
            if (tokens) {
              this.scheduleRefresh(tokens.expiresAt);
            }
          });
        }
      }
    });

    // Clear tokens when page is about to unload (security measure)
    window.addEventListener('beforeunload', () => {
      // Only clear session storage, keep localStorage for "remember me"
      try {
        sessionStorage.clear();
      } catch (error) {
        console.error('Failed to clear session storage on unload:', error);
      }
    });
  }

  /**
   * Export tokens for debugging (development only)
   */
  async debugTokens(): Promise<TokenPair | null> {
    if (process.env.NODE_ENV === 'production') {
      console.warn('Token debugging is disabled in production');
      return null;
    }

    return this.storage.getTokens();
  }

  /**
   * Get token info without exposing actual token values
   */
  async getTokenInfo(): Promise<{
    hasTokens: boolean;
    isValid: boolean;
    expiresAt: Date | null;
    timeUntilExpiration: number;
  }> {
    const tokens = await this.storage.getTokens();

    return {
      hasTokens: !!tokens,
      isValid: tokens ? tokens.expiresAt > Date.now() : false,
      expiresAt: tokens ? new Date(tokens.expiresAt) : null,
      timeUntilExpiration: tokens ? Math.max(0, tokens.expiresAt - Date.now()) : 0,
    };
  }
}
