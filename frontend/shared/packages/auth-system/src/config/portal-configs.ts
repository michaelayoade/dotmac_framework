/**
 * Portal-specific configuration definitions
 * Defines authentication rules, branding, and features for each portal type
 */

import type { PortalConfig, PortalVariant, AuthThemeConfig } from '../types';

// Portal Theme Configurations
export const PORTAL_THEMES: Record<PortalVariant, AuthThemeConfig['colors']> = {
  'management-admin': {
    primary: '#4F46E5',
    secondary: '#6366F1',
    accent: '#8B5CF6',
    background: '#FFFFFF',
    foreground: '#1F2937',
    muted: '#F9FAFB',
    border: '#E5E7EB',
    input: '#F3F4F6',
    ring: '#4F46E5',
    destructive: '#EF4444',
    warning: '#F59E0B',
    success: '#10B981',
  },
  customer: {
    primary: '#059669',
    secondary: '#10B981',
    accent: '#34D399',
    background: '#FFFFFF',
    foreground: '#1F2937',
    muted: '#F0FDF4',
    border: '#D1FAE5',
    input: '#F0FDF4',
    ring: '#059669',
    destructive: '#EF4444',
    warning: '#F59E0B',
    success: '#10B981',
  },
  admin: {
    primary: '#7C3AED',
    secondary: '#8B5CF6',
    accent: '#A78BFA',
    background: '#FFFFFF',
    foreground: '#1F2937',
    muted: '#FAF5FF',
    border: '#E9D5FF',
    input: '#FAF5FF',
    ring: '#7C3AED',
    destructive: '#EF4444',
    warning: '#F59E0B',
    success: '#10B981',
  },
  reseller: {
    primary: '#DC2626',
    secondary: '#EF4444',
    accent: '#F87171',
    background: '#FFFFFF',
    foreground: '#1F2937',
    muted: '#FEF2F2',
    border: '#FECACA',
    input: '#FEF2F2',
    ring: '#DC2626',
    destructive: '#EF4444',
    warning: '#F59E0B',
    success: '#10B981',
  },
  technician: {
    primary: '#0891B2',
    secondary: '#06B6D4',
    accent: '#67E8F9',
    background: '#FFFFFF',
    foreground: '#1F2937',
    muted: '#F0F9FF',
    border: '#BAE6FD',
    input: '#F0F9FF',
    ring: '#0891B2',
    destructive: '#EF4444',
    warning: '#F59E0B',
    success: '#10B981',
  },
  'management-reseller': {
    primary: '#1D4ED8',
    secondary: '#2563EB',
    accent: '#60A5FA',
    background: '#FFFFFF',
    foreground: '#1F2937',
    muted: '#EFF6FF',
    border: '#BFDBFE',
    input: '#EFF6FF',
    ring: '#1D4ED8',
    destructive: '#EF4444',
    warning: '#F59E0B',
    success: '#10B981',
  },
  'tenant-portal': {
    primary: '#0D9488',
    secondary: '#14B8A6',
    accent: '#5EEAD4',
    background: '#FFFFFF',
    foreground: '#1F2937',
    muted: '#F0FDFA',
    border: '#CCFBF1',
    input: '#F0FDFA',
    ring: '#0D9488',
    destructive: '#EF4444',
    warning: '#F59E0B',
    success: '#10B981',
  },
};

// Default portal configurations
export const PORTAL_CONFIGS: Record<PortalVariant, PortalConfig> = {
  'management-admin': {
    id: 'management-admin',
    name: 'Management Admin Portal',
    type: 'management-admin',
    loginMethods: ['email'],
    features: {
      mfaRequired: true,
      mfaOptional: false,
      allowPortalIdLogin: false,
      allowAccountNumberLogin: false,
      ssoEnabled: true,
      passwordlessLogin: false,
      biometricLogin: false,
      rememberDevice: true,
      sessionTimeout: 480, // 8 hours
      maxConcurrentSessions: 3,
      requirePasswordChange: true,
      passwordChangeInterval: 90,
    },
    branding: {
      companyName: 'DotMac Management',
      loginTitle: 'Platform Administration',
      loginSubtitle: 'Manage multi-tenant ISP operations',
      primaryColor: '#4F46E5',
      secondaryColor: '#6366F1',
    },
    theme: PORTAL_THEMES['management-admin'],
    validation: {
      email: {
        required: true,
        // Allow all domains
      },
      password: {
        minLength: 12,
        maxLength: 128,
        requireUppercase: true,
        requireLowercase: true,
        requireNumbers: true,
        requireSymbols: true,
        historyLength: 12,
      },
      mfa: {
        grace_period: 7,
        methods: ['totp', 'sms'],
      },
    },
    security: {
      maxLoginAttempts: 3,
      lockoutDuration: 15,
      sessionTimeout: 480,
      csrfProtection: true,
      deviceFingerprinting: true,
      anomalyDetection: true,
    },
  },

  customer: {
    id: 'customer',
    name: 'Customer Portal',
    type: 'customer',
    loginMethods: ['email', 'portal_id', 'account_number'],
    features: {
      mfaRequired: false,
      mfaOptional: true,
      allowPortalIdLogin: true,
      allowAccountNumberLogin: true,
      ssoEnabled: false,
      passwordlessLogin: false,
      biometricLogin: true,
      rememberDevice: true,
      sessionTimeout: 60, // 1 hour
      maxConcurrentSessions: 5,
      requirePasswordChange: false,
      passwordChangeInterval: 180,
    },
    branding: {
      companyName: 'Customer Portal',
      loginTitle: 'Welcome Back',
      loginSubtitle: 'Access your account and manage services',
      primaryColor: '#059669',
      secondaryColor: '#10B981',
    },
    theme: PORTAL_THEMES['customer'],
    validation: {
      email: {
        required: false, // Can use Portal ID instead
      },
      portalId: {
        format: /^[A-Z0-9]{8}$/,
        length: 8,
        caseSensitive: false,
      },
      accountNumber: {
        format: /^\d{6,12}$/,
        length: { min: 6, max: 12 },
      },
      password: {
        minLength: 8,
        maxLength: 128,
        requireUppercase: false,
        requireLowercase: true,
        requireNumbers: true,
        requireSymbols: false,
        historyLength: 6,
      },
    },
    security: {
      maxLoginAttempts: 5,
      lockoutDuration: 10,
      sessionTimeout: 60,
      csrfProtection: true,
      deviceFingerprinting: false,
      anomalyDetection: false,
    },
  },

  admin: {
    id: 'admin',
    name: 'ISP Admin Portal',
    type: 'admin',
    loginMethods: ['email'],
    features: {
      mfaRequired: true,
      mfaOptional: false,
      allowPortalIdLogin: false,
      allowAccountNumberLogin: false,
      ssoEnabled: true,
      passwordlessLogin: false,
      biometricLogin: false,
      rememberDevice: true,
      sessionTimeout: 240, // 4 hours
      maxConcurrentSessions: 2,
      requirePasswordChange: true,
      passwordChangeInterval: 60,
    },
    branding: {
      companyName: 'ISP Administration',
      loginTitle: 'Admin Portal',
      loginSubtitle: 'Manage customers, network, and operations',
      primaryColor: '#7C3AED',
      secondaryColor: '#8B5CF6',
    },
    theme: PORTAL_THEMES['admin'],
    validation: {
      email: {
        required: true,
      },
      password: {
        minLength: 10,
        maxLength: 128,
        requireUppercase: true,
        requireLowercase: true,
        requireNumbers: true,
        requireSymbols: true,
        historyLength: 10,
      },
      mfa: {
        grace_period: 0, // Immediate MFA required
        methods: ['totp', 'sms'],
      },
    },
    security: {
      maxLoginAttempts: 3,
      lockoutDuration: 30,
      sessionTimeout: 240,
      csrfProtection: true,
      deviceFingerprinting: true,
      anomalyDetection: true,
    },
  },

  reseller: {
    id: 'reseller',
    name: 'Reseller Portal',
    type: 'reseller',
    loginMethods: ['email', 'partner_code'],
    features: {
      mfaRequired: false,
      mfaOptional: true,
      allowPortalIdLogin: false,
      allowAccountNumberLogin: false,
      ssoEnabled: false,
      passwordlessLogin: false,
      biometricLogin: false,
      rememberDevice: true,
      sessionTimeout: 120, // 2 hours
      maxConcurrentSessions: 3,
      requirePasswordChange: false,
      passwordChangeInterval: 90,
    },
    branding: {
      companyName: 'Partner Portal',
      loginTitle: 'Reseller Access',
      loginSubtitle: 'Manage your territory and customers',
      primaryColor: '#DC2626',
      secondaryColor: '#EF4444',
    },
    theme: PORTAL_THEMES['reseller'],
    validation: {
      email: {
        required: false,
      },
      password: {
        minLength: 8,
        maxLength: 128,
        requireUppercase: true,
        requireLowercase: true,
        requireNumbers: true,
        requireSymbols: false,
        historyLength: 8,
      },
    },
    security: {
      maxLoginAttempts: 5,
      lockoutDuration: 15,
      sessionTimeout: 120,
      csrfProtection: true,
      deviceFingerprinting: false,
      anomalyDetection: false,
    },
  },

  technician: {
    id: 'technician',
    name: 'Technician Portal',
    type: 'technician',
    loginMethods: ['email'],
    features: {
      mfaRequired: false,
      mfaOptional: true,
      allowPortalIdLogin: false,
      allowAccountNumberLogin: false,
      ssoEnabled: false,
      passwordlessLogin: false,
      biometricLogin: true, // Mobile-friendly
      rememberDevice: true,
      sessionTimeout: 480, // 8 hours for field work
      maxConcurrentSessions: 2,
      requirePasswordChange: false,
      passwordChangeInterval: 120,
    },
    branding: {
      companyName: 'Field Service',
      loginTitle: 'Technician Access',
      loginSubtitle: 'Mobile field service portal',
      primaryColor: '#0891B2',
      secondaryColor: '#06B6D4',
    },
    theme: PORTAL_THEMES['technician'],
    validation: {
      email: {
        required: true,
      },
      password: {
        minLength: 8,
        maxLength: 128,
        requireUppercase: false,
        requireLowercase: true,
        requireNumbers: true,
        requireSymbols: false,
        historyLength: 6,
      },
    },
    security: {
      maxLoginAttempts: 5,
      lockoutDuration: 10,
      sessionTimeout: 480,
      csrfProtection: true,
      deviceFingerprinting: false,
      anomalyDetection: false,
    },
  },

  'management-reseller': {
    id: 'management-reseller',
    name: 'Management Reseller Portal',
    type: 'management-reseller',
    loginMethods: ['email'],
    features: {
      mfaRequired: true,
      mfaOptional: false,
      allowPortalIdLogin: false,
      allowAccountNumberLogin: false,
      ssoEnabled: true,
      passwordlessLogin: false,
      biometricLogin: false,
      rememberDevice: true,
      sessionTimeout: 240, // 4 hours
      maxConcurrentSessions: 2,
      requirePasswordChange: true,
      passwordChangeInterval: 90,
    },
    branding: {
      companyName: 'Reseller Management',
      loginTitle: 'Partner Network',
      loginSubtitle: 'Manage reseller operations and analytics',
      primaryColor: '#1D4ED8',
      secondaryColor: '#2563EB',
    },
    theme: PORTAL_THEMES['management-reseller'],
    validation: {
      email: {
        required: true,
      },
      password: {
        minLength: 10,
        maxLength: 128,
        requireUppercase: true,
        requireLowercase: true,
        requireNumbers: true,
        requireSymbols: true,
        historyLength: 10,
      },
      mfa: {
        grace_period: 3,
        methods: ['totp', 'sms'],
      },
    },
    security: {
      maxLoginAttempts: 3,
      lockoutDuration: 20,
      sessionTimeout: 240,
      csrfProtection: true,
      deviceFingerprinting: true,
      anomalyDetection: true,
    },
  },

  'tenant-portal': {
    id: 'tenant-portal',
    name: 'Tenant Portal',
    type: 'tenant-portal',
    loginMethods: ['email'],
    features: {
      mfaRequired: false,
      mfaOptional: true,
      allowPortalIdLogin: false,
      allowAccountNumberLogin: false,
      ssoEnabled: true,
      passwordlessLogin: false,
      biometricLogin: false,
      rememberDevice: true,
      sessionTimeout: 120, // 2 hours
      maxConcurrentSessions: 3,
      requirePasswordChange: false,
      passwordChangeInterval: 90,
    },
    branding: {
      companyName: 'Tenant Portal',
      loginTitle: 'Multi-Tenant Access',
      loginSubtitle: 'Manage your organization settings',
      primaryColor: '#0D9488',
      secondaryColor: '#14B8A6',
    },
    theme: PORTAL_THEMES['tenant-portal'],
    validation: {
      email: {
        required: true,
      },
      password: {
        minLength: 8,
        maxLength: 128,
        requireUppercase: true,
        requireLowercase: true,
        requireNumbers: true,
        requireSymbols: false,
        historyLength: 8,
      },
    },
    security: {
      maxLoginAttempts: 5,
      lockoutDuration: 15,
      sessionTimeout: 120,
      csrfProtection: true,
      deviceFingerprinting: false,
      anomalyDetection: false,
    },
  },
};

/**
 * Get portal configuration by variant
 */
export function getPortalConfig(portalVariant: PortalVariant): PortalConfig {
  return PORTAL_CONFIGS[portalVariant];
}

/**
 * Get portal theme by variant
 */
export function getPortalTheme(portalVariant: PortalVariant): AuthThemeConfig['colors'] {
  return PORTAL_THEMES[portalVariant];
}

/**
 * Check if a portal supports a specific login method
 */
export function supportsLoginMethod(portalVariant: PortalVariant, method: string): boolean {
  return PORTAL_CONFIGS[portalVariant].loginMethods.includes(method as any);
}

/**
 * Get required password complexity for a portal
 */
export function getPasswordRequirements(portalVariant: PortalVariant) {
  return PORTAL_CONFIGS[portalVariant].validation.password;
}

/**
 * Check if MFA is required for a portal
 */
export function isMfaRequired(portalVariant: PortalVariant): boolean {
  return PORTAL_CONFIGS[portalVariant].features.mfaRequired;
}

/**
 * Get session timeout for a portal (in minutes)
 */
export function getSessionTimeout(portalVariant: PortalVariant): number {
  return PORTAL_CONFIGS[portalVariant].features.sessionTimeout;
}

/**
 * Get maximum concurrent sessions allowed for a portal
 */
export function getMaxConcurrentSessions(portalVariant: PortalVariant): number {
  return PORTAL_CONFIGS[portalVariant].features.maxConcurrentSessions;
}

/**
 * Portal-specific CSS custom properties for theming
 */
export function generatePortalCSS(portalVariant: PortalVariant): string {
  const theme = getPortalTheme(portalVariant);

  return `
    :root {
      --auth-primary: ${theme.primary};
      --auth-secondary: ${theme.secondary};
      --auth-accent: ${theme.accent};
      --auth-background: ${theme.background};
      --auth-foreground: ${theme.foreground};
      --auth-muted: ${theme.muted};
      --auth-border: ${theme.border};
      --auth-input: ${theme.input};
      --auth-ring: ${theme.ring};
      --auth-destructive: ${theme.destructive};
      --auth-warning: ${theme.warning};
      --auth-success: ${theme.success};
    }
  `;
}
