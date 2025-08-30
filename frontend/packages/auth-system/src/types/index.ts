/**
 * Universal Authentication System Types
 *
 * Type definitions for all authentication-related functionality
 * across the DotMac Framework portal ecosystem
 */

// Portal Configuration Types
export type PortalVariant =
  | 'management-admin'
  | 'customer'
  | 'admin'
  | 'reseller'
  | 'technician'
  | 'management-reseller'
  | 'tenant-portal';

export interface PortalTheme {
  primary: string;
  secondary: string;
  accent: string;
  background: string;
  foreground: string;
  muted: string;
  border: string;
  input: string;
  ring: string;
  destructive: string;
  warning: string;
  success: string;
}

export interface PortalConfig {
  id: string;
  name: string;
  type: PortalVariant;
  tenantId?: string;
  loginMethods: LoginMethod[];
  features: PortalFeatures;
  branding: PortalBranding;
  theme: PortalTheme;
  validation: ValidationRules;
  security: SecurityConfig;
}

// Authentication Methods
export type LoginMethod =
  | 'email'
  | 'portal_id'
  | 'account_number'
  | 'partner_code'
  | 'sso'
  | 'api_key';

export interface PortalFeatures {
  mfaRequired: boolean;
  mfaOptional: boolean;
  allowPortalIdLogin: boolean;
  allowAccountNumberLogin: boolean;
  ssoEnabled: boolean;
  passwordlessLogin: boolean;
  biometricLogin: boolean;
  rememberDevice: boolean;
  sessionTimeout: number; // minutes
  maxConcurrentSessions: number;
  requirePasswordChange: boolean;
  passwordChangeInterval: number; // days
}

export interface PortalBranding {
  logo?: string;
  favicon?: string;
  companyName: string;
  loginTitle?: string;
  loginSubtitle?: string;
  primaryColor: string;
  secondaryColor: string;
  backgroundImage?: string;
  customCSS?: string;
}

// User Types
export interface BaseUser {
  id: string;
  email: string;
  name: string;
  firstName?: string;
  lastName?: string;
  avatar?: string;
  role: string;
  permissions: string[];
  tenantId?: string;
  portalAccess: PortalVariant[];
  isActive: boolean;
  lastLogin?: Date;
  createdAt: string;
  updatedAt: string;
}

// Portal-specific user extensions
export interface CustomerUser extends BaseUser {
  role: 'customer';
  portalId?: string;
  accountNumber?: string;
  serviceLevel: string;
  billingStatus: 'current' | 'past_due' | 'suspended';
  autoPayEnabled: boolean;
}

export interface AdminUser extends BaseUser {
  role: 'admin' | 'super_admin' | 'manager';
  department?: string;
  managesTenants?: string[];
  adminLevel: 'basic' | 'full' | 'super';
}

export interface ResellerUser extends BaseUser {
  role: 'reseller' | 'reseller_admin';
  territory: string[];
  commissionRate: number;
  partnerCode: string;
  resellerLevel: 'bronze' | 'silver' | 'gold' | 'platinum';
}

export interface TechnicianUser extends BaseUser {
  role: 'technician' | 'lead_technician';
  certifications: string[];
  serviceAreas: string[];
  mobileAccess: boolean;
  vehicleId?: string;
}

export type User = CustomerUser | AdminUser | ResellerUser | TechnicianUser | BaseUser;

// Authentication Flow Types
export interface LoginCredentials {
  // Common fields
  password: string;

  // Email login
  email?: string;

  // Portal ID login (customer)
  portalId?: string;

  // Account number login (customer)
  accountNumber?: string;

  // Partner code login (reseller)
  partnerCode?: string;

  // API key login
  apiKey?: string;

  // MFA
  mfaCode?: string;
  mfaMethod?: 'totp' | 'sms' | 'email' | 'backup_code';

  // Options
  rememberMe?: boolean;
  rememberDevice?: boolean;

  // Portal context
  portalType?: PortalVariant;
  tenantId?: string;
}

export interface LoginResponse {
  success: boolean;
  user: User;
  tokens: {
    accessToken: string;
    refreshToken: string;
    expiresIn: number;
    expiresAt: number;
  };
  session: {
    id: string;
    expiresAt: number;
    deviceId?: string;
    ipAddress?: string;
  };
  mfa?: {
    required: boolean;
    methods: string[];
    backupCodes?: number;
  };
  portal: PortalConfig;
  redirectUrl?: string;
  csrfToken: string;
}

export interface LoginError {
  code: string;
  message: string;
  field?: string;
  details?: Record<string, any>;
  lockedUntil?: Date;
  requiresMfa?: boolean;
  mfaMethods?: string[];
  retryAfter?: number;
}

// MFA Types
export interface MfaSetup {
  type: 'totp' | 'sms' | 'email';
  secret?: string;
  qrCode?: string;
  backupCodes: string[];
  enabled: boolean;
  verified: boolean;
}

export interface MfaVerification {
  code: string;
  method: 'totp' | 'sms' | 'email' | 'backup_code';
  rememberDevice?: boolean;
}

// Password Management
export interface PasswordRequirements {
  minLength: number;
  maxLength: number;
  requireUppercase: boolean;
  requireLowercase: boolean;
  requireNumbers: boolean;
  requireSymbols: boolean;
  bannedPasswords?: string[];
  historyLength: number; // How many previous passwords to remember
}

export interface PasswordChangeRequest {
  currentPassword: string;
  newPassword: string;
  confirmPassword: string;
}

export interface PasswordResetRequest {
  email?: string;
  portalId?: string;
  accountNumber?: string;
  token?: string;
  newPassword?: string;
}

// Session Management
export interface Session {
  id: string;
  userId: string;
  portalType: PortalVariant;
  deviceId?: string;
  deviceName?: string;
  ipAddress: string;
  userAgent: string;
  location?: {
    country?: string;
    city?: string;
  };
  createdAt: Date;
  lastActivity: Date;
  expiresAt: Date;
  metadata?: Record<string, any>;
  isActive: boolean;
  isCurrent?: boolean;
}

// Security & Validation
export interface ValidationRules {
  email?: {
    required: boolean;
    domains?: string[]; // Allowed email domains
    blockedDomains?: string[]; // Blocked email domains
  };
  portalId?: {
    format: RegExp;
    length: number;
    caseSensitive: boolean;
  };
  accountNumber?: {
    format: RegExp;
    length: { min: number; max: number };
  };
  password: PasswordRequirements;
  mfa?: {
    grace_period: number; // days before MFA is required
    methods: string[];
  };
}

export interface SecurityConfig {
  maxLoginAttempts: number;
  lockoutDuration: number; // minutes
  sessionTimeout: number; // minutes
  csrfProtection: boolean;
  ipWhitelist?: string[];
  geoBlocking?: {
    enabled: boolean;
    blockedCountries: string[];
    allowedCountries?: string[];
  };
  deviceFingerprinting: boolean;
  anomalyDetection: boolean;
}

// Rate Limiting
export interface RateLimitConfig {
  windowMs: number;
  maxAttempts: number;
  blockDuration: number;
  skipSuccessfulRequests: boolean;
}

export interface RateLimitStatus {
  allowed: boolean;
  limit: number;
  remaining: number;
  resetTime: Date;
  retryAfter?: number;
}

// Permission System
export interface Permission {
  id: string;
  name: string;
  resource: string;
  action: string;
  conditions?: Record<string, any>;
}

export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: string[];
  portal: PortalVariant;
  level: number;
}

// Event Types for Audit/Analytics
export type AuthEventType =
  | 'login_attempt'
  | 'login_success'
  | 'login_failure'
  | 'logout'
  | 'session_expired'
  | 'password_change'
  | 'password_reset'
  | 'mfa_setup'
  | 'mfa_verification'
  | 'account_locked'
  | 'account_unlocked'
  | 'suspicious_activity'
  | 'device_registered'
  | 'session_terminated';

export interface AuthEvent {
  id: string;
  type: AuthEventType;
  userId?: string;
  sessionId?: string;
  portalType: PortalVariant;
  ipAddress: string;
  userAgent: string;
  metadata?: Record<string, any>;
  timestamp: Date;
  success: boolean;
  errorCode?: string;
  riskScore?: number;
}

// React Component Props
export interface AuthProviderProps {
  children: React.ReactNode;
  portalVariant: PortalVariant;
  config?: Partial<PortalConfig>;
  onAuthStateChange?: (user: User | null, isAuthenticated: boolean) => void;
  onError?: (error: LoginError) => void;
}

export interface LoginFormProps {
  portalVariant: PortalVariant;
  onLogin: (user: User) => void;
  onError?: (error: LoginError) => void;
  className?: string;
  showRememberMe?: boolean;
  showForgotPassword?: boolean;
  redirectTo?: string;
  customFields?: {
    name: string;
    label: string;
    type: string;
    required: boolean;
  }[];
}

export interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermissions?: string[];
  requiredRole?: string | string[];
  fallback?: React.ReactNode;
  redirectTo?: string;
  portalVariant: PortalVariant;
}

// Hook Return Types
export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: LoginError | null;
  portal: PortalConfig | null;
  session: Session | null;
  permissions: string[];
  role: string | null;
}

export interface AuthActions {
  login: (credentials: LoginCredentials) => Promise<LoginResponse>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  updateUser: (updates: Partial<User>) => Promise<User>;
  changePassword: (request: PasswordChangeRequest) => Promise<void>;
  resetPassword: (request: PasswordResetRequest) => Promise<void>;
  setupMfa: (type: 'totp' | 'sms' | 'email') => Promise<MfaSetup>;
  verifyMfa: (verification: MfaVerification) => Promise<boolean>;
  getSessions: () => Promise<Session[]>;
  terminateSession: (sessionId: string) => Promise<void>;
  terminateAllSessions: () => Promise<void>;
}

export interface AuthHookReturn extends AuthState, AuthActions {
  // Permission helpers
  hasPermission: (permission: string) => boolean;
  hasRole: (role: string | string[]) => boolean;
  hasAnyRole: (roles: string[]) => boolean;

  // Portal helpers
  getPortalConfig: () => PortalConfig | null;
  getLoginMethods: () => LoginMethod[];
  isMfaRequired: () => boolean;
  canAccessPortal: (portalType: PortalVariant) => boolean;

  // Validation helpers
  validateCredentials: (credentials: LoginCredentials) => ValidationResult;
  validatePassword: (password: string) => ValidationResult;

  // Rate limiting
  getRateLimitStatus: () => RateLimitStatus | null;

  // Security
  getSecurityEvents: () => Promise<AuthEvent[]>;
  reportSuspiciousActivity: (details: Record<string, any>) => Promise<void>;
}

// Validation Result
export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings?: string[];
}

// Theme configuration
export interface AuthThemeConfig {
  portal: PortalVariant;
  colors: PortalTheme;
  borderRadius: string;
  fontFamily: string;
  shadows: {
    sm: string;
    md: string;
    lg: string;
  };
  spacing: Record<string, string>;
}

// API Response Types
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: {
    code: string;
    message: string;
    details?: any;
  };
  meta?: {
    pagination?: {
      page: number;
      limit: number;
      total: number;
    };
    rateLimit?: RateLimitStatus;
  };
}

// Context Types
export interface AuthContextValue extends AuthHookReturn {}

export interface PortalContextValue {
  config: PortalConfig;
  theme: AuthThemeConfig;
  updateConfig: (updates: Partial<PortalConfig>) => void;
  switchPortal: (portalType: PortalVariant) => Promise<void>;
}
