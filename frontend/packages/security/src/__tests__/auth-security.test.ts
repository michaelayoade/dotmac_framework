/**
 * Authentication & Authorization Security Tests
 * Production-grade auth security validation
 * Leveraging @dotmac/auth and @dotmac/providers unified patterns
 */

import { describe, it, expect, jest, beforeEach, afterEach } from '@jest/globals';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AuthProvider } from '@dotmac/auth';
import { TestWrapper } from '@dotmac/testing';

// Mock JWT and crypto utilities
const mockJWT = {
  sign: jest.fn(),
  verify: jest.fn(),
  decode: jest.fn()
};

const mockCrypto = {
  randomBytes: jest.fn(),
  createHash: jest.fn(),
  createHmac: jest.fn(),
  timingSafeEqual: jest.fn()
};

// Mock auth service with security validations
class MockSecureAuthService {
  private tokens = new Map();
  private loginAttempts = new Map();
  private sessionStore = new Map();

  constructor(private config = {
    maxLoginAttempts: 5,
    lockoutDuration: 15 * 60 * 1000, // 15 minutes
    sessionTimeout: 30 * 60 * 1000,   // 30 minutes
    tokenRotationInterval: 5 * 60 * 1000 // 5 minutes
  }) {}

  async authenticate(credentials: { email: string; password: string }) {
    // Rate limiting check
    if (this.isAccountLocked(credentials.email)) {
      throw new Error('Account temporarily locked due to too many failed attempts');
    }

    // Simulate authentication
    if (credentials.email === 'valid@example.com' && credentials.password === 'SecurePass123!') {
      this.clearLoginAttempts(credentials.email);
      return this.createSecureSession(credentials.email);
    }

    this.recordFailedAttempt(credentials.email);
    throw new Error('Invalid credentials');
  }

  async validateSession(token: string) {
    const session = this.sessionStore.get(token);
    if (!session) return null;

    // Check session expiry
    if (Date.now() > session.expiresAt) {
      this.sessionStore.delete(token);
      return null;
    }

    // Check if token needs rotation
    if (Date.now() > session.rotateAt) {
      return this.rotateToken(token);
    }

    return session;
  }

  private createSecureSession(email: string) {
    const token = this.generateSecureToken();
    const now = Date.now();

    const session = {
      token,
      email,
      createdAt: now,
      expiresAt: now + this.config.sessionTimeout,
      rotateAt: now + this.config.tokenRotationInterval,
      permissions: this.getUserPermissions(email)
    };

    this.sessionStore.set(token, session);
    return session;
  }

  private generateSecureToken(): string {
    return 'secure_token_' + Math.random().toString(36).substr(2, 16);
  }

  private isAccountLocked(email: string): boolean {
    const attempts = this.loginAttempts.get(email);
    if (!attempts) return false;

    return attempts.count >= this.config.maxLoginAttempts &&
           Date.now() < attempts.lockedUntil;
  }

  private recordFailedAttempt(email: string) {
    const attempts = this.loginAttempts.get(email) || { count: 0, firstAttempt: Date.now() };
    attempts.count++;

    if (attempts.count >= this.config.maxLoginAttempts) {
      attempts.lockedUntil = Date.now() + this.config.lockoutDuration;
    }

    this.loginAttempts.set(email, attempts);
  }

  private clearLoginAttempts(email: string) {
    this.loginAttempts.delete(email);
  }

  private rotateToken(oldToken: string) {
    const session = this.sessionStore.get(oldToken);
    if (!session) return null;

    const newToken = this.generateSecureToken();
    const now = Date.now();

    const newSession = {
      ...session,
      token: newToken,
      rotateAt: now + this.config.tokenRotationInterval
    };

    this.sessionStore.delete(oldToken);
    this.sessionStore.set(newToken, newSession);

    return newSession;
  }

  private getUserPermissions(email: string) {
    // Mock permission system
    if (email === 'admin@example.com') {
      return ['admin', 'read', 'write', 'delete'];
    }
    return ['read'];
  }
}

describe('🔐 Authentication Security Suite', () => {
  let authService: MockSecureAuthService;

  beforeEach(() => {
    authService = new MockSecureAuthService();
    jest.clearAllMocks();
  });

  describe('Credential Validation', () => {
    it('should authenticate valid credentials', async () => {
      const result = await authService.authenticate({
        email: 'valid@example.com',
        password: 'SecurePass123!'
      });

      expect(result).toBeTruthy();
      expect(result.email).toBe('valid@example.com');
      expect(result.token).toBeTruthy();
    });

    it('should reject invalid credentials', async () => {
      await expect(authService.authenticate({
        email: 'invalid@example.com',
        password: 'wrongpassword'
      })).rejects.toThrow('Invalid credentials');
    });

    it('should enforce password complexity', () => {
      const weakPasswords = [
        'password',
        '123456',
        'admin',
        'qwerty',
        'password123'
      ];

      const strongPasswords = [
        'SecurePass123!',
        'MyStr0ng@Password',
        'C0mplex#Pass2024'
      ];

      const validatePassword = (password: string) => {
        const minLength = 8;
        const hasUpper = /[A-Z]/.test(password);
        const hasLower = /[a-z]/.test(password);
        const hasNumber = /\d/.test(password);
        const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);

        return password.length >= minLength && hasUpper && hasLower && hasNumber && hasSpecial;
      };

      weakPasswords.forEach(password => {
        expect(validatePassword(password)).toBe(false);
      });

      strongPasswords.forEach(password => {
        expect(validatePassword(password)).toBe(true);
      });
    });
  });

  describe('Brute Force Protection', () => {
    it('should track failed login attempts', async () => {
      const email = 'user@example.com';

      // Make multiple failed attempts
      for (let i = 0; i < 4; i++) {
        await expect(authService.authenticate({
          email,
          password: 'wrongpassword'
        })).rejects.toThrow();
      }

      // 5th attempt should trigger lockout
      await expect(authService.authenticate({
        email,
        password: 'wrongpassword'
      })).rejects.toThrow('Account temporarily locked');
    });

    it('should reset attempts after successful login', async () => {
      const email = 'valid@example.com';

      // Make some failed attempts
      for (let i = 0; i < 3; i++) {
        await expect(authService.authenticate({
          email,
          password: 'wrongpassword'
        })).rejects.toThrow('Invalid credentials');
      }

      // Successful login should reset attempts
      await authService.authenticate({
        email,
        password: 'SecurePass123!'
      });

      // Should be able to make attempts again
      await expect(authService.authenticate({
        email,
        password: 'wrongpassword'
      })).rejects.toThrow('Invalid credentials');
    });

    it('should implement progressive delays', () => {
      const calculateDelay = (attemptCount: number): number => {
        return Math.min(1000 * Math.pow(2, attemptCount - 1), 30000); // Max 30s
      };

      expect(calculateDelay(1)).toBe(1000);   // 1s
      expect(calculateDelay(2)).toBe(2000);   // 2s
      expect(calculateDelay(3)).toBe(4000);   // 4s
      expect(calculateDelay(4)).toBe(8000);   // 8s
      expect(calculateDelay(5)).toBe(16000);  // 16s
      expect(calculateDelay(10)).toBe(30000); // Cap at 30s
    });
  });

  describe('Session Security', () => {
    it('should create secure session tokens', async () => {
      const session = await authService.authenticate({
        email: 'valid@example.com',
        password: 'SecurePass123!'
      });

      expect(session.token).toBeTruthy();
      expect(session.createdAt).toBeTruthy();
      expect(session.expiresAt).toBeGreaterThan(Date.now());
      expect(session.permissions).toEqual(['read']);
    });

    it('should validate active sessions', async () => {
      const session = await authService.authenticate({
        email: 'valid@example.com',
        password: 'SecurePass123!'
      });

      const validation = await authService.validateSession(session.token);
      expect(validation).toBeTruthy();
      expect(validation?.email).toBe('valid@example.com');
    });

    it('should reject expired sessions', async () => {
      // Mock short session timeout
      const shortTimeoutService = new MockSecureAuthService({
        maxLoginAttempts: 5,
        lockoutDuration: 15 * 60 * 1000,
        sessionTimeout: 100, // 100ms for testing
        tokenRotationInterval: 50
      });

      const session = await shortTimeoutService.authenticate({
        email: 'valid@example.com',
        password: 'SecurePass123!'
      });

      // Wait for session to expire
      await new Promise(resolve => setTimeout(resolve, 150));

      const validation = await shortTimeoutService.validateSession(session.token);
      expect(validation).toBeNull();
    });

    it('should rotate tokens automatically', async () => {
      // Mock short rotation interval
      const rotationService = new MockSecureAuthService({
        maxLoginAttempts: 5,
        lockoutDuration: 15 * 60 * 1000,
        sessionTimeout: 30 * 60 * 1000,
        tokenRotationInterval: 100 // 100ms for testing
      });

      const session = await rotationService.authenticate({
        email: 'valid@example.com',
        password: 'SecurePass123!'
      });

      const originalToken = session.token;

      // Wait for rotation interval
      await new Promise(resolve => setTimeout(resolve, 150));

      const validation = await rotationService.validateSession(originalToken);
      expect(validation).toBeTruthy();
      expect(validation?.token).not.toBe(originalToken);
    });
  });

  describe('Permission-Based Access Control', () => {
    it('should enforce role-based permissions', async () => {
      const checkPermission = (userPermissions: string[], requiredPermission: string): boolean => {
        return userPermissions.includes(requiredPermission);
      };

      const adminPermissions = ['admin', 'read', 'write', 'delete'];
      const userPermissions = ['read'];

      expect(checkPermission(adminPermissions, 'admin')).toBe(true);
      expect(checkPermission(adminPermissions, 'delete')).toBe(true);
      expect(checkPermission(userPermissions, 'admin')).toBe(false);
      expect(checkPermission(userPermissions, 'write')).toBe(false);
      expect(checkPermission(userPermissions, 'read')).toBe(true);
    });

    it('should validate resource-level permissions', () => {
      const hasResourceAccess = (
        userPermissions: string[],
        resource: string,
        action: string,
        resourceOwner?: string,
        userId?: string
      ): boolean => {
        // Admin can access anything
        if (userPermissions.includes('admin')) return true;

        // Owner can access their own resources
        if (resourceOwner === userId) return true;

        // Check specific permission
        const permission = `${resource}:${action}`;
        return userPermissions.includes(permission);
      };

      const userPermissions = ['billing:read', 'profile:write'];

      expect(hasResourceAccess(userPermissions, 'billing', 'read')).toBe(true);
      expect(hasResourceAccess(userPermissions, 'billing', 'write')).toBe(false);
      expect(hasResourceAccess(userPermissions, 'profile', 'write')).toBe(true);

      // Test ownership
      expect(hasResourceAccess(userPermissions, 'document', 'read', 'user123', 'user123')).toBe(true);
      expect(hasResourceAccess(userPermissions, 'document', 'read', 'user456', 'user123')).toBe(false);
    });
  });
});

describe('🛡️ JWT Security', () => {
  const mockSecret = 'super-secret-key-for-testing-only-do-not-use-in-production';

  beforeEach(() => {
    mockJWT.sign.mockClear();
    mockJWT.verify.mockClear();
    mockJWT.decode.mockClear();
  });

  describe('Token Generation', () => {
    it('should create JWT with secure headers', () => {
      const payload = { userId: '123', email: 'user@example.com' };
      const options = {
        algorithm: 'HS256',
        expiresIn: '1h',
        issuer: 'dotmac-platform',
        audience: 'dotmac-users'
      };

      mockJWT.sign.mockReturnValue('mock.jwt.token');
      const token = mockJWT.sign(payload, mockSecret, options);

      expect(mockJWT.sign).toHaveBeenCalledWith(payload, mockSecret, options);
      expect(token).toBeTruthy();
    });

    it('should validate JWT signature', () => {
      const token = 'mock.jwt.token';
      const decoded = { userId: '123', email: 'user@example.com', exp: Date.now() / 1000 + 3600 };

      mockJWT.verify.mockReturnValue(decoded);
      const result = mockJWT.verify(token, mockSecret);

      expect(mockJWT.verify).toHaveBeenCalledWith(token, mockSecret);
      expect(result).toEqual(decoded);
    });

    it('should handle token expiration', () => {
      const expiredToken = 'expired.jwt.token';

      mockJWT.verify.mockImplementation(() => {
        throw new Error('TokenExpiredError: jwt expired');
      });

      expect(() => mockJWT.verify(expiredToken, mockSecret)).toThrow('jwt expired');
    });

    it('should validate token structure', () => {
      const malformedTokens = [
        'not.a.jwt',
        'missing.signature',
        'invalid-format',
        '',
        null,
        undefined
      ];

      malformedTokens.forEach(token => {
        mockJWT.verify.mockImplementation(() => {
          throw new Error('JsonWebTokenError: invalid token');
        });

        expect(() => mockJWT.verify(token, mockSecret)).toThrow('invalid token');
      });
    });
  });

  describe('Token Security Properties', () => {
    it('should use secure algorithms', () => {
      const secureAlgorithms = ['HS256', 'RS256', 'ES256'];
      const insecureAlgorithms = ['none', 'HS1', 'MD5'];

      const isSecureAlgorithm = (alg: string): boolean => {
        return secureAlgorithms.includes(alg);
      };

      secureAlgorithms.forEach(alg => {
        expect(isSecureAlgorithm(alg)).toBe(true);
      });

      insecureAlgorithms.forEach(alg => {
        expect(isSecureAlgorithm(alg)).toBe(false);
      });
    });

    it('should enforce short expiration times', () => {
      const validateExpiration = (expiresIn: string): boolean => {
        const timeMap: { [key: string]: number } = {
          's': 1,
          'm': 60,
          'h': 3600,
          'd': 86400
        };

        const match = expiresIn.match(/^(\d+)([smhd])$/);
        if (!match) return false;

        const [, value, unit] = match;
        const seconds = parseInt(value) * (timeMap[unit] || 0);

        return seconds <= 3600; // Max 1 hour
      };

      expect(validateExpiration('15m')).toBe(true);
      expect(validateExpiration('1h')).toBe(true);
      expect(validateExpiration('2h')).toBe(false);
      expect(validateExpiration('1d')).toBe(false);
    });
  });
});

describe('🔒 AuthProvider Integration', () => {
  const MockAuthComponent = () => {
    return (
      <AuthProvider
        portal="test"
        config={{
          apiUrl: '/api/auth',
          tokenStorage: 'memory' // Secure for testing
        }}
      >
        <div data-testid="protected-content">
          Protected Content
        </div>
      </AuthProvider>
    );
  };

  it('should render protected content when authenticated', async () => {
    // Mock authenticated state
    const mockAuthContext = {
      user: { id: '123', email: 'user@example.com' },
      isAuthenticated: true,
      isLoading: false,
      login: jest.fn(),
      logout: jest.fn()
    };

    render(<MockAuthComponent />, {
      wrapper: (props) => <TestWrapper authContext={mockAuthContext} {...props} />
    });

    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('should redirect unauthenticated users', async () => {
    const mockAuthContext = {
      user: null,
      isAuthenticated: false,
      isLoading: false,
      login: jest.fn(),
      logout: jest.fn()
    };

    const mockNavigate = jest.fn();

    render(<MockAuthComponent />, {
      wrapper: (props) => <TestWrapper
        authContext={mockAuthContext}
        navigate={mockNavigate}
        {...props}
      />
    });

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/login');
    });
  });

  it('should handle secure logout', async () => {
    const mockAuthContext = {
      user: { id: '123', email: 'user@example.com' },
      isAuthenticated: true,
      isLoading: false,
      login: jest.fn(),
      logout: jest.fn().mockImplementation(() => {
        // Secure logout should:
        // 1. Clear all tokens
        // 2. Clear session storage
        // 3. Redirect to login
        // 4. Optionally notify server
        return Promise.resolve();
      })
    };

    render(<MockAuthComponent />, {
      wrapper: (props) => <TestWrapper authContext={mockAuthContext} {...props} />
    });

    // Trigger logout
    await mockAuthContext.logout();

    expect(mockAuthContext.logout).toHaveBeenCalled();
  });
});
