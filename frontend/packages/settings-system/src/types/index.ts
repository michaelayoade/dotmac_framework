// Core settings types
export interface SettingsData {
  [key: string]: any;
}

export interface SettingsSection {
  id: string;
  label: string;
  description?: string;
  icon?: React.ComponentType<any>;
  component: React.ComponentType<any>;
}

export interface SettingsContext {
  data: SettingsData;
  updateSetting: (path: string, value: any) => void;
  resetSection: (sectionId: string) => void;
  saveSettings: () => Promise<boolean>;
  isLoading: boolean;
  isDirty: boolean;
  errors: Record<string, string>;
}

// Profile types
export interface ProfileData {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  dateOfBirth: string;
  avatar?: string;
  address: {
    street: string;
    city: string;
    state: string;
    zipCode: string;
    country: string;
  };
  preferences: {
    language: string;
    timezone: string;
    dateFormat: string;
    currency: string;
  };
  emergencyContact: {
    name: string;
    relationship: string;
    phone: string;
    email: string;
  };
  lastUpdated: string;
}

// Notification types
export interface ContactMethod {
  type: 'email' | 'sms' | 'phone' | 'push';
  value: string;
  verified: boolean;
  primary: boolean;
}

export interface NotificationPreference {
  category: string;
  label: string;
  description: string;
  email: boolean;
  sms: boolean;
  push: boolean;
}

export interface NotificationSettings {
  contactMethods: ContactMethod[];
  preferences: NotificationPreference[];
  globalSettings: {
    enableAll: boolean;
    quietHours: {
      enabled: boolean;
      start: string;
      end: string;
    };
  };
}

// Security types
export interface SecurityEvent {
  id: string;
  type: 'login' | 'password_change' | 'device_added' | 'suspicious_activity';
  description: string;
  timestamp: string;
  location: string;
  device: string;
  ipAddress: string;
  success: boolean;
}

export interface TwoFactorMethod {
  id: string;
  type: 'sms' | 'authenticator' | 'email';
  label: string;
  identifier: string;
  isEnabled: boolean;
  isPrimary: boolean;
  addedDate: string;
}

export interface SecuritySettings {
  passwordPolicy: {
    minLength: number;
    requireUppercase: boolean;
    requireLowercase: boolean;
    requireNumbers: boolean;
    requireSpecialChars: boolean;
    expiryDays: number;
  };
  twoFactor: {
    methods: TwoFactorMethod[];
    required: boolean;
  };
  sessions: {
    maxConcurrent: number;
    timeoutMinutes: number;
  };
  activityLog: SecurityEvent[];
}

// Appearance types
export interface ThemeSettings {
  mode: 'light' | 'dark' | 'system';
  primaryColor: string;
  accentColor: string;
  fontSize: 'small' | 'medium' | 'large';
  compactMode: boolean;
  animations: boolean;
}

export interface AccessibilitySettings {
  highContrast: boolean;
  reducedMotion: boolean;
  screenReader: boolean;
  keyboardNavigation: boolean;
  focusIndicators: boolean;
}

export interface AppearanceSettings {
  theme: ThemeSettings;
  accessibility: AccessibilitySettings;
  layout: {
    sidebarCollapsed: boolean;
    density: 'comfortable' | 'compact' | 'spacious';
    showTooltips: boolean;
  };
}
