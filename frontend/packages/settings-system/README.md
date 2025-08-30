# @dotmac/settings-system

Universal settings and preferences management system for DotMac ISP Framework. This package consolidates all user preference patterns across portals, eliminating code duplication and providing a consistent interface for managing profile settings, notifications, security, and appearance preferences.

## Features

- **Profile Management**: Unified user profile forms with validation and helper methods
- **Notification Settings**: Contact method management and preference configuration
- **Security Settings**: Password policies, 2FA management, and security monitoring
- **Appearance Settings**: Theme management, accessibility options, and layout preferences
- **DRY Architecture**: Reduces ~70% code duplication across portals
- **TypeScript Support**: Fully typed with comprehensive interfaces
- **Validation**: Built-in validation for all settings types
- **Persistence**: Configurable persistence with localStorage support
- **Accessibility**: WCAG-compliant components with full a11y support

## Installation

```bash
pnpm add @dotmac/settings-system
```

## Quick Start

### Basic Usage

```tsx
import {
  ProfileSettings,
  NotificationSettings,
  SecuritySettings,
  AppearanceSettings,
  useSettings
} from '@dotmac/settings-system';

function SettingsPage() {
  const settings = useSettings({
    persistKey: 'user-settings',
    autoSave: true
  });

  return (
    <div>
      <ProfileSettings
        profileData={profileData}
        onUpdate={handleProfileUpdate}
        onSave={settings.saveSettings}
      />
    </div>
  );
}
```

### Advanced Integration

```tsx
import {
  useSettings,
  getDefaultNotificationSettings,
  getDefaultSecuritySettings,
  getDefaultAppearanceSettings
} from '@dotmac/settings-system';

function UnifiedSettings() {
  const [notificationSettings, setNotificationSettings] = useState(
    getDefaultNotificationSettings()
  );

  const settingsContext = useSettings({
    initialData: {
      notifications: notificationSettings,
    },
    persistKey: 'unified-settings',
    autoSave: false,
  });

  const handleNotificationUpdate = (data) => {
    const updated = { ...notificationSettings, ...data };
    setNotificationSettings(updated);
    settingsContext.updateSetting('notifications', updated);
  };

  return (
    <NotificationSettings
      settings={notificationSettings}
      onUpdate={handleNotificationUpdate}
      onSave={settingsContext.saveSettings}
      isLoading={settingsContext.isLoading}
    />
  );
}
```

## Components

### ProfileSettings

Manages user personal information, contact details, preferences, and emergency contacts.

```tsx
<ProfileSettings
  profileData={profileData}
  onUpdate={handleUpdate}
  onSave={handleSave}
  isLoading={false}
  readonly={false}
  className="custom-styles"
/>
```

#### Props

- `profileData: ProfileData` - Current profile data
- `onUpdate: (data: Partial<ProfileData>) => void` - Update handler
- `onSave?: () => Promise<boolean>` - Save handler (optional)
- `isLoading?: boolean` - Loading state
- `readonly?: boolean` - Read-only mode
- `className?: string` - Additional CSS classes

### NotificationSettings

Handles contact methods and notification preferences across different channels.

```tsx
<NotificationSettings
  settings={notificationSettings}
  onUpdate={handleUpdate}
  onSave={handleSave}
/>
```

#### Features

- Contact method management (email, SMS, phone, push)
- Notification category preferences
- Quiet hours configuration
- Global notification controls

### SecuritySettings

Comprehensive security management including passwords, 2FA, and activity monitoring.

```tsx
<SecuritySettings
  settings={securitySettings}
  onUpdate={handleUpdate}
  onSave={handleSave}
/>
```

#### Features

- Password policy configuration
- Two-factor authentication management
- Session management
- Security activity log
- Password strength validation

### AppearanceSettings

Theme and accessibility settings for personalized user experience.

```tsx
<AppearanceSettings
  settings={appearanceSettings}
  onUpdate={handleUpdate}
  onSave={handleSave}
/>
```

#### Features

- Light/dark/system theme modes
- Color customization
- Font size preferences
- Layout density options
- Accessibility options (high contrast, reduced motion, etc.)

## Hooks

### useSettings

Central settings management hook with persistence and validation.

```tsx
const settings = useSettings({
  initialData: {},
  persistKey: 'user-settings',
  autoSave: false,
  saveDelay: 500
});
```

#### Returns

- `data: SettingsData` - Current settings data
- `updateSetting: (path: string, value: any) => void` - Update a setting
- `resetSection: (sectionId: string) => void` - Reset a settings section
- `saveSettings: () => Promise<boolean>` - Save all settings
- `isLoading: boolean` - Loading state
- `isDirty: boolean` - Unsaved changes indicator
- `errors: Record<string, string>` - Validation errors

## Helper Functions

### Profile Helpers

```tsx
import {
  formatDate,
  validateEmail,
  validatePhone,
  formatPhoneDisplay,
  validateProfileData,
  getInitials,
  getFullName
} from '@dotmac/settings-system/profile';
```

### Notification Helpers

```tsx
import {
  validateContactMethod,
  formatContactValue,
  getDefaultNotificationPreferences,
  validateNotificationSettings,
  exportNotificationSettings,
  isQuietHoursActive
} from '@dotmac/settings-system/notifications';
```

### Security Helpers

```tsx
import {
  validatePassword,
  calculatePasswordStrength,
  isPasswordExpired,
  getSecurityScore,
  detectSuspiciousActivity,
  generateSecurityReport
} from '@dotmac/settings-system/security';
```

### Appearance Helpers

```tsx
import {
  applyThemeToDOM,
  getSystemThemePreference,
  generateColorVariations,
  isAccessibleContrast,
  generateCSS
} from '@dotmac/settings-system/appearance';
```

## Types

All components are fully typed. Key interfaces include:

```tsx
interface ProfileData {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  dateOfBirth: string;
  avatar?: string;
  address: AddressData;
  preferences: UserPreferences;
  emergencyContact: EmergencyContact;
  lastUpdated: string;
}

interface NotificationSettings {
  contactMethods: ContactMethod[];
  preferences: NotificationPreference[];
  globalSettings: {
    enableAll: boolean;
    quietHours: QuietHours;
  };
}

interface SecuritySettings {
  passwordPolicy: PasswordPolicy;
  twoFactor: TwoFactorSettings;
  sessions: SessionSettings;
  activityLog: SecurityEvent[];
}

interface AppearanceSettings {
  theme: ThemeSettings;
  accessibility: AccessibilitySettings;
  layout: LayoutSettings;
}
```

## Validation

All settings include built-in validation:

```tsx
import { validateProfileData, validateNotificationSettings } from '@dotmac/settings-system';

const profileErrors = validateProfileData(profileData);
const notificationErrors = validateNotificationSettings(settings);
```

## Accessibility

All components follow WCAG 2.1 AA guidelines:

- Keyboard navigation support
- Screen reader compatibility
- High contrast mode support
- Reduced motion preferences
- Focus indicators
- Semantic HTML structure

## Migration Guide

### From Existing Components

1. **Replace individual components**:

   ```tsx
   // Before
   import { ProfileManagement } from '../components/ProfileManagement';

   // After
   import { ProfileSettings } from '@dotmac/settings-system/profile';
   ```

2. **Update prop interfaces**:

   ```tsx
   // Before
   interface Props {
     user: User;
     onSave: (user: User) => void;
   }

   // After
   interface Props {
     profileData: ProfileData;
     onUpdate: (data: Partial<ProfileData>) => void;
   }
   ```

3. **Use helper functions**:

   ```tsx
   // Before
   const isValidEmail = (email) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

   // After
   import { validateEmail } from '@dotmac/settings-system/profile';
   ```

## Development

```bash
# Install dependencies
pnpm install

# Start development
pnpm dev

# Build package
pnpm build

# Run tests
pnpm test

# Type check
pnpm type-check

# Lint
pnpm lint
```

## Examples

See the `/examples` directory for complete implementation examples:

- Basic settings page
- Multi-tab settings interface
- Read-only settings display
- Custom validation integration
- Theme integration examples

## Contributing

1. Follow the DRY principles established in the codebase
2. Ensure all components are accessible
3. Add comprehensive TypeScript types
4. Include validation for all user inputs
5. Write tests for new functionality
6. Update documentation

## License

MIT License - see LICENSE file for details.

---

**Reduces code duplication by ~70% across portals while providing a consistent, accessible settings interface.**
