import { SecuritySettings, SecurityEvent, TwoFactorMethod } from '../types';

export const getDefaultSecuritySettings = (): SecuritySettings => ({
  passwordPolicy: {
    minLength: 8,
    requireUppercase: true,
    requireLowercase: true,
    requireNumbers: true,
    requireSpecialChars: true,
    expiryDays: 90,
  },
  twoFactor: {
    methods: [
      {
        id: '1',
        type: 'authenticator',
        label: 'Authenticator App',
        identifier: 'Google Authenticator',
        isEnabled: true,
        isPrimary: true,
        addedDate: new Date().toISOString(),
      },
      {
        id: '2',
        type: 'sms',
        label: 'SMS Text Message',
        identifier: '+1 (555) ***-4567',
        isEnabled: false,
        isPrimary: false,
        addedDate: new Date().toISOString(),
      },
      {
        id: '3',
        type: 'email',
        label: 'Email Verification',
        identifier: 'user@example.com',
        isEnabled: false,
        isPrimary: false,
        addedDate: new Date().toISOString(),
      },
    ],
    required: false,
  },
  sessions: {
    maxConcurrent: 3,
    timeoutMinutes: 120,
  },
  activityLog: [],
});

export const validatePassword = (
  password: string,
  policy: SecuritySettings['passwordPolicy']
): { isValid: boolean; errors: string[] } => {
  const errors: string[] = [];

  if (password.length < policy.minLength) {
    errors.push(`Password must be at least ${policy.minLength} characters long`);
  }

  if (policy.requireUppercase && !/[A-Z]/.test(password)) {
    errors.push('Password must contain at least one uppercase letter');
  }

  if (policy.requireLowercase && !/[a-z]/.test(password)) {
    errors.push('Password must contain at least one lowercase letter');
  }

  if (policy.requireNumbers && !/[0-9]/.test(password)) {
    errors.push('Password must contain at least one number');
  }

  if (policy.requireSpecialChars && !/[^A-Za-z0-9]/.test(password)) {
    errors.push('Password must contain at least one special character');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
};

export const calculatePasswordStrength = (password: string): {
  score: number;
  label: string;
  color: string;
  suggestions: string[];
} => {
  let score = 0;
  const suggestions: string[] = [];

  // Length check
  if (password.length >= 8) score += 1;
  else suggestions.push('Use at least 8 characters');

  if (password.length >= 12) score += 1;
  else if (password.length >= 8) suggestions.push('Consider using 12+ characters for better security');

  // Character variety
  if (/[A-Z]/.test(password)) score += 1;
  else suggestions.push('Add uppercase letters');

  if (/[a-z]/.test(password)) score += 1;
  else suggestions.push('Add lowercase letters');

  if (/[0-9]/.test(password)) score += 1;
  else suggestions.push('Add numbers');

  if (/[^A-Za-z0-9]/.test(password)) score += 1;
  else suggestions.push('Add special characters');

  // Additional complexity checks
  if (password.length >= 16) score += 1;
  if (/[!@#$%^&*(),.?":{}|<>]/.test(password)) score += 1;

  const finalScore = Math.min(score, 5);

  const getLabel = (s: number) => {
    if (s <= 1) return 'Very Weak';
    if (s <= 2) return 'Weak';
    if (s <= 3) return 'Fair';
    if (s <= 4) return 'Good';
    return 'Strong';
  };

  const getColor = (s: number) => {
    if (s <= 1) return 'text-red-600';
    if (s <= 2) return 'text-orange-600';
    if (s <= 3) return 'text-yellow-600';
    if (s <= 4) return 'text-blue-600';
    return 'text-green-600';
  };

  return {
    score: finalScore,
    label: getLabel(finalScore),
    color: getColor(finalScore),
    suggestions: suggestions.slice(0, 3), // Limit to most important suggestions
  };
};

export const isPasswordExpired = (
  lastChangeDate: string,
  expiryDays: number
): boolean => {
  const lastChange = new Date(lastChangeDate);
  const now = new Date();
  const daysDiff = Math.floor((now.getTime() - lastChange.getTime()) / (1000 * 60 * 60 * 24));
  return daysDiff >= expiryDays;
};

export const getDaysUntilPasswordExpiry = (
  lastChangeDate: string,
  expiryDays: number
): number => {
  const lastChange = new Date(lastChangeDate);
  const now = new Date();
  const daysDiff = Math.floor((now.getTime() - lastChange.getTime()) / (1000 * 60 * 60 * 24));
  return Math.max(0, expiryDays - daysDiff);
};

export const validateSecuritySettings = (settings: Partial<SecuritySettings>): Record<string, string> => {
  const errors: Record<string, string> = {};

  // Validate password policy
  if (settings.passwordPolicy) {
    const policy = settings.passwordPolicy;

    if (policy.minLength && (policy.minLength < 6 || policy.minLength > 128)) {
      errors['passwordPolicy.minLength'] = 'Minimum length must be between 6 and 128 characters';
    }

    if (policy.expiryDays && (policy.expiryDays < 30 || policy.expiryDays > 365)) {
      errors['passwordPolicy.expiryDays'] = 'Expiry days must be between 30 and 365';
    }
  }

  // Validate 2FA settings
  if (settings.twoFactor?.methods) {
    const enabledMethods = settings.twoFactor.methods.filter(method => method.isEnabled);
    const primaryMethods = enabledMethods.filter(method => method.isPrimary);

    if (enabledMethods.length > 0 && primaryMethods.length === 0) {
      errors['twoFactor.methods'] = 'At least one enabled 2FA method must be set as primary';
    }

    if (primaryMethods.length > 1) {
      errors['twoFactor.methods'] = 'Only one 2FA method can be set as primary';
    }
  }

  // Validate session settings
  if (settings.sessions) {
    if (settings.sessions.maxConcurrent && (settings.sessions.maxConcurrent < 1 || settings.sessions.maxConcurrent > 10)) {
      errors['sessions.maxConcurrent'] = 'Maximum concurrent sessions must be between 1 and 10';
    }

    if (settings.sessions.timeoutMinutes && (settings.sessions.timeoutMinutes < 15 || settings.sessions.timeoutMinutes > 1440)) {
      errors['sessions.timeoutMinutes'] = 'Session timeout must be between 15 minutes and 24 hours';
    }
  }

  return errors;
};

export const formatSecurityEventType = (type: string): string => {
  const typeLabels = {
    login: 'Login',
    password_change: 'Password Change',
    device_added: 'Device Added',
    suspicious_activity: 'Suspicious Activity',
    two_factor_enabled: '2FA Enabled',
    two_factor_disabled: '2FA Disabled',
    session_terminated: 'Session Terminated',
  };

  return typeLabels[type as keyof typeof typeLabels] || type;
};

export const getSecurityScore = (settings: SecuritySettings): {
  score: number;
  maxScore: number;
  percentage: number;
  recommendations: string[];
} => {
  let score = 0;
  const maxScore = 10;
  const recommendations: string[] = [];

  // Password policy score (3 points)
  if (settings.passwordPolicy.minLength >= 12) score += 1;
  else recommendations.push('Increase minimum password length to 12+ characters');

  if (settings.passwordPolicy.requireUppercase &&
      settings.passwordPolicy.requireLowercase &&
      settings.passwordPolicy.requireNumbers &&
      settings.passwordPolicy.requireSpecialChars) {
    score += 2;
  } else {
    recommendations.push('Require all character types in passwords');
  }

  // 2FA score (4 points)
  const enabledMethods = settings.twoFactor.methods.filter(method => method.isEnabled);

  if (enabledMethods.length >= 1) score += 2;
  else recommendations.push('Enable at least one two-factor authentication method');

  if (enabledMethods.length >= 2) score += 1;
  else if (enabledMethods.length === 1) recommendations.push('Enable a second 2FA method for backup');

  if (settings.twoFactor.required) score += 1;
  else recommendations.push('Make two-factor authentication required');

  // Session management score (2 points)
  if (settings.sessions.maxConcurrent <= 3) score += 1;
  else recommendations.push('Limit concurrent sessions to 3 or fewer');

  if (settings.sessions.timeoutMinutes <= 120) score += 1;
  else recommendations.push('Set session timeout to 2 hours or less');

  // Recent activity score (1 point)
  const recentSuspiciousActivity = settings.activityLog
    .filter(event => !event.success)
    .filter(event => {
      const eventDate = new Date(event.timestamp);
      const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
      return eventDate > weekAgo;
    });

  if (recentSuspiciousActivity.length === 0) score += 1;
  else recommendations.push('Review recent suspicious activity');

  return {
    score,
    maxScore,
    percentage: Math.round((score / maxScore) * 100),
    recommendations: recommendations.slice(0, 5), // Top 5 recommendations
  };
};

export const exportSecurityAuditLog = (events: SecurityEvent[]): string => {
  const csvHeader = 'Timestamp,Type,Description,Location,Device,IP Address,Success\n';
  const csvRows = events.map(event =>
    `${event.timestamp},${formatSecurityEventType(event.type)},"${event.description}","${event.location}","${event.device}",${event.ipAddress},${event.success ? 'Yes' : 'No'}`
  ).join('\n');

  return csvHeader + csvRows;
};

export const detectSuspiciousActivity = (events: SecurityEvent[]): SecurityEvent[] => {
  const suspicious: SecurityEvent[] = [];

  // Check for failed login attempts
  const failedLogins = events
    .filter(event => event.type === 'login' && !event.success)
    .filter(event => {
      const eventDate = new Date(event.timestamp);
      const hourAgo = new Date(Date.now() - 60 * 60 * 1000);
      return eventDate > hourAgo;
    });

  if (failedLogins.length >= 3) {
    suspicious.push(...failedLogins);
  }

  // Check for logins from new locations
  const uniqueLocations = new Set(events.filter(e => e.type === 'login' && e.success).map(e => e.location));
  const recentLogins = events
    .filter(event => event.type === 'login' && event.success)
    .filter(event => {
      const eventDate = new Date(event.timestamp);
      const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
      return eventDate > weekAgo;
    });

  recentLogins.forEach(login => {
    const locationCount = events.filter(e =>
      e.type === 'login' &&
      e.success &&
      e.location === login.location
    ).length;

    if (locationCount === 1) {
      suspicious.push(login);
    }
  });

  return suspicious;
};

export const generateSecurityReport = (settings: SecuritySettings): {
  summary: string;
  score: ReturnType<typeof getSecurityScore>;
  suspiciousActivity: SecurityEvent[];
  recommendations: string[];
} => {
  const score = getSecurityScore(settings);
  const suspiciousActivity = detectSuspiciousActivity(settings.activityLog);

  let summary = `Security score: ${score.percentage}% (${score.score}/${score.maxScore})`;

  if (suspiciousActivity.length > 0) {
    summary += `. ${suspiciousActivity.length} suspicious activities detected.`;
  }

  const recommendations = [
    ...score.recommendations,
    ...(suspiciousActivity.length > 0 ? ['Review and address suspicious activities'] : []),
  ];

  return {
    summary,
    score,
    suspiciousActivity,
    recommendations: [...new Set(recommendations)], // Remove duplicates
  };
};
