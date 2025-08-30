import { NotificationPreference, ContactMethod, NotificationSettings } from '../types';

export const validateContactMethod = (type: string, value: string): string | null => {
  switch (type) {
    case 'email':
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      return emailRegex.test(value) ? null : 'Please enter a valid email address';

    case 'sms':
    case 'phone':
      const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
      const cleanPhone = value.replace(/[\s\-\(\)]/g, '');
      return phoneRegex.test(cleanPhone) ? null : 'Please enter a valid phone number';

    case 'push':
      return value.length > 10 ? null : 'Invalid device token';

    default:
      return 'Invalid contact method type';
  }
};

export const formatContactValue = (type: string, value: string): string => {
  switch (type) {
    case 'sms':
    case 'phone':
      const cleaned = value.replace(/\D/g, '');
      if (cleaned.length === 10) {
        return `(${cleaned.slice(0, 3)}) ${cleaned.slice(3, 6)}-${cleaned.slice(6)}`;
      }
      if (cleaned.length === 11 && cleaned[0] === '1') {
        return `+1 (${cleaned.slice(1, 4)}) ${cleaned.slice(4, 7)}-${cleaned.slice(7)}`;
      }
      return value;

    case 'push':
      return value.length > 20 ? `${value.slice(0, 20)}...` : value;

    default:
      return value;
  }
};

export const getContactMethodLabel = (type: string): string => {
  const labels = {
    email: 'Email Address',
    sms: 'SMS Number',
    phone: 'Phone Number',
    push: 'Push Device',
  };
  return labels[type as keyof typeof labels] || type;
};

export const getContactMethodPlaceholder = (type: string): string => {
  const placeholders = {
    email: 'user@example.com',
    sms: '+1 (555) 123-4567',
    phone: '+1 (555) 123-4567',
    push: 'Device identifier',
  };
  return placeholders[type as keyof typeof placeholders] || '';
};

export const getDefaultNotificationPreferences = (): NotificationPreference[] => [
  {
    category: 'billing',
    label: 'Billing & Payments',
    description: 'Invoice notifications, payment confirmations, billing issues',
    email: true,
    sms: false,
    push: true,
  },
  {
    category: 'service',
    label: 'Service Updates',
    description: 'Outages, maintenance, service changes',
    email: true,
    sms: true,
    push: true,
  },
  {
    category: 'account',
    label: 'Account Security',
    description: 'Login alerts, security notifications, password changes',
    email: true,
    sms: true,
    push: true,
  },
  {
    category: 'support',
    label: 'Support Updates',
    description: 'Ticket updates, support case notifications',
    email: true,
    sms: false,
    push: true,
  },
  {
    category: 'marketing',
    label: 'Promotions & Offers',
    description: 'Special deals, new service announcements',
    email: false,
    sms: false,
    push: false,
  },
  {
    category: 'technical',
    label: 'Technical Notifications',
    description: 'System updates, maintenance windows, performance alerts',
    email: true,
    sms: false,
    push: true,
  },
];

export const getDefaultNotificationSettings = (): NotificationSettings => ({
  contactMethods: [],
  preferences: getDefaultNotificationPreferences(),
  globalSettings: {
    enableAll: true,
    quietHours: {
      enabled: false,
      start: '22:00',
      end: '08:00',
    },
  },
});

export const validateNotificationSettings = (settings: Partial<NotificationSettings>): Record<string, string> => {
  const errors: Record<string, string> = {};

  // Validate contact methods
  if (settings.contactMethods) {
    settings.contactMethods.forEach((method, index) => {
      const error = validateContactMethod(method.type, method.value);
      if (error) {
        errors[`contactMethod.${index}`] = error;
      }
    });

    // Check for primary contact method
    const hasPrimary = settings.contactMethods.some(method => method.primary);
    if (settings.contactMethods.length > 0 && !hasPrimary) {
      errors.contactMethods = 'At least one contact method must be set as primary';
    }
  }

  // Validate quiet hours
  if (settings.globalSettings?.quietHours?.enabled) {
    const start = settings.globalSettings.quietHours.start;
    const end = settings.globalSettings.quietHours.end;

    if (!start || !end) {
      errors.quietHours = 'Both start and end times are required for quiet hours';
    }
  }

  return errors;
};

export const getNotificationSummary = (settings: NotificationSettings): {
  totalMethods: number;
  verifiedMethods: number;
  enabledCategories: number;
  totalCategories: number;
} => {
  const totalMethods = settings.contactMethods.length;
  const verifiedMethods = settings.contactMethods.filter(method => method.verified).length;
  const enabledCategories = settings.preferences.filter(
    pref => pref.email || pref.sms || pref.push
  ).length;
  const totalCategories = settings.preferences.length;

  return {
    totalMethods,
    verifiedMethods,
    enabledCategories,
    totalCategories,
  };
};

export const exportNotificationSettings = (settings: NotificationSettings): string => {
  const exportData = {
    contactMethods: settings.contactMethods.map(method => ({
      type: method.type,
      value: method.value,
      primary: method.primary,
      verified: method.verified,
    })),
    preferences: settings.preferences.map(pref => ({
      category: pref.category,
      label: pref.label,
      email: pref.email,
      sms: pref.sms,
      push: pref.push,
    })),
    globalSettings: settings.globalSettings,
    exportedAt: new Date().toISOString(),
  };

  return JSON.stringify(exportData, null, 2);
};

export const importNotificationSettings = (jsonString: string): NotificationSettings | null => {
  try {
    const importData = JSON.parse(jsonString);

    // Validate structure
    if (!importData.contactMethods || !importData.preferences || !importData.globalSettings) {
      throw new Error('Invalid settings format');
    }

    return {
      contactMethods: importData.contactMethods.map((method: any) => ({
        ...method,
        verified: false, // Reset verification status on import
      })),
      preferences: importData.preferences,
      globalSettings: importData.globalSettings,
    };
  } catch (error) {
    console.error('Failed to import notification settings:', error);
    return null;
  }
};

export const isQuietHoursActive = (quietHours: { enabled: boolean; start: string; end: string }): boolean => {
  if (!quietHours.enabled) return false;

  const now = new Date();
  const currentTime = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`;

  const start = quietHours.start;
  const end = quietHours.end;

  // Handle case where quiet hours span midnight
  if (start > end) {
    return currentTime >= start || currentTime < end;
  } else {
    return currentTime >= start && currentTime < end;
  }
};

export const getContactMethodIcon = (type: string) => {
  const iconPaths = {
    email: 'M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207',
    sms: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
    phone: 'M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z',
    push: 'M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9',
  };

  return iconPaths[type as keyof typeof iconPaths] || iconPaths.email;
};
