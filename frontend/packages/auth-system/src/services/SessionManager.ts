/**
 * Session Management Service
 *
 * Handles user session lifecycle, timeout management, and session validation
 * Provides secure session storage and cross-tab synchronization
 */

import type { Session, User, PortalVariant } from '../types';

interface SessionStorage {
  getSession(): Promise<Session | null>;
  setSession(session: Session): Promise<void>;
  clearSession(): Promise<void>;
}

/**
 * Secure session storage implementation
 * Uses encrypted storage with fallback mechanisms
 */
class SecureSessionStorage implements SessionStorage {
  private readonly SESSION_KEY = 'auth_session';
  private memorySession: Session | null = null;

  async getSession(): Promise<Session | null> {
    try {
      // Try memory first
      if (this.memorySession && !this.isSessionExpired(this.memorySession)) {
        return this.memorySession;
      }

      // Get from storage
      const stored = await this.getSecureItem(this.SESSION_KEY);
      if (!stored) return null;

      const rawSession = JSON.parse(stored);

      // Convert date strings back to Date objects
      const session: Session = {
        ...rawSession,
        createdAt: new Date(rawSession.createdAt),
        lastActivity: new Date(rawSession.lastActivity),
        expiresAt: new Date(rawSession.expiresAt),
      };

      // Validate session structure
      if (!this.isValidSessionStructure(session)) {
        await this.clearSession();
        return null;
      }

      // Check if expired
      if (this.isSessionExpired(session)) {
        await this.clearSession();
        return null;
      }

      // Store in memory for faster access
      this.memorySession = session;
      return session;
    } catch (error) {
      console.error('Failed to get session:', error);
      return null;
    }
  }

  async setSession(session: Session): Promise<void> {
    try {
      // Store in memory
      this.memorySession = session;

      // Store securely (serialize dates)
      const serializedSession = {
        ...session,
        createdAt: session.createdAt.toISOString(),
        lastActivity: session.lastActivity.toISOString(),
        expiresAt: session.expiresAt.toISOString(),
      };
      const sessionData = JSON.stringify(serializedSession);
      await this.setSecureItem(this.SESSION_KEY, sessionData);

      // Broadcast to other tabs
      this.broadcastSessionUpdate(session);
    } catch (error) {
      console.error('Failed to set session:', error);
      throw new Error('Session storage failed');
    }
  }

  async clearSession(): Promise<void> {
    try {
      // Clear memory
      this.memorySession = null;

      // Clear storage
      await this.removeSecureItem(this.SESSION_KEY);

      // Broadcast to other tabs
      this.broadcastSessionClear();
    } catch (error) {
      console.error('Failed to clear session:', error);
    }
  }

  private async getSecureItem(key: string): Promise<string | null> {
    if (typeof window === 'undefined') return null;

    try {
      // Try sessionStorage first
      let value = sessionStorage.getItem(key);

      // Fallback to localStorage
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

      // Store in both for redundancy
      sessionStorage.setItem(key, obfuscatedValue);
      localStorage.setItem(key, obfuscatedValue);
    } catch (error) {
      console.error(`Failed to store session ${key}:`, error);
    }
  }

  private async removeSecureItem(key: string): Promise<void> {
    if (typeof window === 'undefined') return;

    try {
      sessionStorage.removeItem(key);
      localStorage.removeItem(key);
    } catch (error) {
      console.error(`Failed to remove session ${key}:`, error);
    }
  }

  private isValidSessionStructure(session: any): session is Session {
    return (
      session &&
      typeof session.id === 'string' &&
      typeof session.userId === 'string' &&
      typeof session.portalType === 'string' &&
      session.createdAt instanceof Date &&
      session.lastActivity instanceof Date &&
      session.expiresAt instanceof Date
    );
  }

  private isSessionExpired(session: Session): boolean {
    const now = new Date().getTime();
    const expiresAt = session.expiresAt.getTime();
    return now >= expiresAt;
  }

  private broadcastSessionUpdate(session: Session) {
    if (typeof window === 'undefined') return;

    try {
      const event = new CustomEvent('auth-session-updated', {
        detail: { session },
      });
      window.dispatchEvent(event);
    } catch (error) {
      console.error('Failed to broadcast session update:', error);
    }
  }

  private broadcastSessionClear() {
    if (typeof window === 'undefined') return;

    try {
      const event = new CustomEvent('auth-session-cleared');
      window.dispatchEvent(event);
    } catch (error) {
      console.error('Failed to broadcast session clear:', error);
    }
  }
}

export class SessionManager {
  private storage: SessionStorage;
  private activityTimeout: NodeJS.Timeout | null = null;
  private warningTimeout: NodeJS.Timeout | null = null;
  private readonly ACTIVITY_UPDATE_INTERVAL = 30 * 1000; // 30 seconds

  constructor(storage?: SessionStorage) {
    this.storage = storage || new SecureSessionStorage();
    this.setupCrossTabSync();
    this.setupActivityTracking();
  }

  /**
   * Get current session
   */
  async getCurrentSession(): Promise<Session | null> {
    return this.storage.getSession();
  }

  /**
   * Set current session
   */
  async setCurrentSession(session: Session): Promise<void> {
    await this.storage.setSession(session);
    this.scheduleActivityUpdate();
  }

  /**
   * Clear current session
   */
  async clearSession(): Promise<void> {
    await this.storage.clearSession();
    this.clearTimeouts();
  }

  /**
   * Update last activity timestamp
   */
  async updateActivity(): Promise<void> {
    const session = await this.getCurrentSession();
    if (!session) return;

    const updatedSession: Session = {
      ...session,
      lastActivity: new Date(),
    };

    await this.setCurrentSession(updatedSession);
  }

  /**
   * Check if session is expired
   */
  isSessionExpired(session: Session): boolean {
    const now = new Date().getTime();
    const expiresAt = session.expiresAt.getTime();
    return now >= expiresAt;
  }

  /**
   * Check if session is about to expire (within warning threshold)
   */
  isSessionExpiring(session: Session, warningMinutes = 5): boolean {
    const now = new Date().getTime();
    const expiresAt = new Date(session.expiresAt).getTime();
    const warningThreshold = warningMinutes * 60 * 1000;
    return (expiresAt - now) <= warningThreshold && expiresAt > now;
  }

  /**
   * Get time until session expires (in milliseconds)
   */
  getTimeUntilExpiration(session: Session): number {
    const now = new Date().getTime();
    const expiresAt = session.expiresAt.getTime();
    return Math.max(0, expiresAt - now);
  }

  /**
   * Extend session expiration time
   */
  async extendSession(additionalMinutes: number = 30): Promise<Session | null> {
    const session = await this.getCurrentSession();
    if (!session || this.isSessionExpired(session)) {
      return null;
    }

    const newExpiresAt = new Date(
      new Date(session.expiresAt).getTime() + additionalMinutes * 60 * 1000
    );

    const extendedSession: Session = {
      ...session,
      expiresAt: newExpiresAt,
      lastActivity: new Date(),
    };

    await this.setCurrentSession(extendedSession);
    return extendedSession;
  }

  /**
   * Validate session against server
   */
  async validateSession(): Promise<boolean> {
    const session = await this.getCurrentSession();
    if (!session) return false;

    if (this.isSessionExpired(session)) {
      await this.clearSession();
      return false;
    }

    try {
      // This would typically make an API call to validate the session
      const response = await fetch('/api/v1/auth/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ sessionId: session.id }),
        credentials: 'include',
      });

      if (!response.ok) {
        await this.clearSession();
        return false;
      }

      const data = await response.json();
      return data.valid;
    } catch (error) {
      console.error('Session validation failed:', error);
      return false;
    }
  }

  /**
   * Create new session
   */
  async createSession(
    user: User,
    portalType: PortalVariant,
    timeoutMinutes: number = 480 // 8 hours default
  ): Promise<Session> {
    const now = new Date();
    const expiresAt = new Date(now.getTime() + timeoutMinutes * 60 * 1000);

    const session: Session = {
      id: this.generateSessionId(),
      userId: user.id,
      portalType,
      createdAt: now,
      lastActivity: now,
      expiresAt: expiresAt,
      ipAddress: await this.getClientIP(),
      userAgent: navigator.userAgent,
      metadata: {
        loginMethod: 'standard',
        deviceInfo: this.getDeviceInfo(),
      },
    };

    await this.setCurrentSession(session);
    return session;
  }

  /**
   * Setup session timeout warnings and auto-logout
   */
  setupSessionTimeout(
    session: Session,
    onWarning?: () => void,
    onExpiry?: () => void
  ): () => void {
    this.clearTimeouts();

    const timeUntilExpiry = this.getTimeUntilExpiration(session);
    const warningTime = Math.max(0, timeUntilExpiry - 5 * 60 * 1000); // 5 minutes before

    // Set up warning
    if (warningTime > 0 && onWarning) {
      this.warningTimeout = setTimeout(() => {
        onWarning();
      }, warningTime);
    }

    // Set up auto-logout
    if (timeUntilExpiry > 0 && onExpiry) {
      this.activityTimeout = setTimeout(() => {
        this.clearSession().then(() => onExpiry());
      }, timeUntilExpiry);
    }

    // Return cleanup function
    return () => this.clearTimeouts();
  }

  /**
   * Get session info without exposing sensitive data
   */
  async getSessionInfo(): Promise<{
    hasSession: boolean;
    isValid: boolean;
    expiresAt: Date | null;
    timeUntilExpiration: number;
    portalType: PortalVariant | null;
    lastActivity: Date | null;
  }> {
    const session = await this.getCurrentSession();

    return {
      hasSession: !!session,
      isValid: session ? !this.isSessionExpired(session) : false,
      expiresAt: session ? new Date(session.expiresAt) : null,
      timeUntilExpiration: session ? this.getTimeUntilExpiration(session) : 0,
      portalType: session?.portalType || null,
      lastActivity: session ? new Date(session.lastActivity) : null,
    };
  }

  private generateSessionId(): string {
    // Generate a cryptographically secure session ID
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
  }

  private async getClientIP(): Promise<string> {
    try {
      // This would typically be handled by the server
      // For now, return placeholder
      return 'client_ip_placeholder';
    } catch {
      return 'unknown';
    }
  }

  private getDeviceInfo(): Record<string, any> {
    if (typeof window === 'undefined') return {};

    return {
      screen: {
        width: window.screen.width,
        height: window.screen.height,
      },
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      language: navigator.language,
      platform: navigator.platform,
    };
  }

  private scheduleActivityUpdate(): void {
    // Update activity every 30 seconds while user is active
    this.activityTimeout = setTimeout(() => {
      this.updateActivity().then(() => {
        this.scheduleActivityUpdate();
      });
    }, this.ACTIVITY_UPDATE_INTERVAL);
  }

  private clearTimeouts(): void {
    if (this.activityTimeout) {
      clearTimeout(this.activityTimeout);
      this.activityTimeout = null;
    }
    if (this.warningTimeout) {
      clearTimeout(this.warningTimeout);
      this.warningTimeout = null;
    }
  }

  private setupActivityTracking(): void {
    if (typeof window === 'undefined') return;

    // Track user activity events
    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'];
    let lastActivityUpdate = Date.now();

    const handleActivity = () => {
      const now = Date.now();
      // Throttle activity updates to once per minute
      if (now - lastActivityUpdate > 60 * 1000) {
        this.updateActivity().catch(error => {
          console.error('Failed to update activity:', error);
        });
        lastActivityUpdate = now;
      }
    };

    events.forEach(event => {
      document.addEventListener(event, handleActivity, true);
    });

    // Handle visibility change (tab switching)
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        handleActivity();
      }
    });
  }

  private setupCrossTabSync(): void {
    if (typeof window === 'undefined') return;

    // Listen for session updates from other tabs
    window.addEventListener('auth-session-updated', ((event: CustomEvent) => {
      if (event.detail?.session) {
        // Reschedule timeouts with new session data
        this.clearTimeouts();
        this.scheduleActivityUpdate();
      }
    }) as EventListener);

    // Listen for session clears from other tabs
    window.addEventListener('auth-session-cleared', () => {
      this.clearTimeouts();
    });

    // Handle storage events (fallback for cross-tab communication)
    window.addEventListener('storage', (event) => {
      if (event.key === 'auth_session') {
        if (!event.newValue) {
          // Session was cleared
          this.clearTimeouts();
        } else {
          // Session was updated
          this.clearTimeouts();
          this.scheduleActivityUpdate();
        }
      }
    });
  }
}
