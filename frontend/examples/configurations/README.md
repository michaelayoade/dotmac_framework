# DotMac Framework Configuration Examples

This directory contains example configurations showing how different types of
ISPs can customize the DotMac Framework for their specific needs.

## Configuration Architecture

The DotMac Framework uses a composition-based configuration system that allows
ISPs to:

- **Customize currencies and locales** for international operations
- **Define business-specific plan types and pricing**
- **Configure branding and theming** for white-label deployments
- **Enable/disable features** based on operational needs
- **Set up monitoring and analytics** endpoints

## Example Configurations

### 1. European ISP (`european-isp.config.ts`)

**Use Case:** Multi-national European ISP operating in Germany, France, UK,
Spain, and Italy

**Key Features:**

- Multi-locale support (German primary, 5 supported languages)
- Euro currency with European formatting (€ after amount, comma decimal
  separator)
- German business terminology and plan names
- Advanced features enabled (white-label, custom domains, SSO)
- External analytics endpoint

**Business Logic:**

- Symmetric business plans (common in Europe)
- Detailed SLA specifications
- Partner program with percentage-based commissions

### 2. Small Town ISP (`small-town-isp.config.ts`)

**Use Case:** Local ISP serving a small American town

**Key Features:**

- Single locale (US English only)
- USD currency with standard US formatting
- Simplified plan structure focused on residential service
- Basic feature set (no advanced analytics, API access, or SSO)
- Local support emphasis

**Business Logic:**

- Asymmetric residential plans (common in US)
- Simple referral-based partner program
- Focus on community relationships

## Using Configurations

### 1. Framework-wide Configuration

```tsx
import { ConfigProvider } from '@dotmac/headless';
import { europeanISPConfig } from './configurations/european-isp.config';

function App() {
  return (
    <ConfigProvider initialConfig={europeanISPConfig}>
      <YourApp />
    </ConfigProvider>
  );
}
```

### 2. Portal-specific Theming

```tsx
import { ThemeProvider } from '@dotmac/headless';

function CustomerPortal() {
  return (
    <ThemeProvider portalType='customer'>
      <CustomerApp />
    </ThemeProvider>
  );
}
```

### 3. Runtime Configuration Loading

```tsx
function App() {
  return (
    <ConfigProvider configEndpoint='/api/config'>
      <YourApp />
    </ConfigProvider>
  );
}
```

## Configuration Sections

### Locale Configuration

- Primary and supported languages
- Date/time formatting preferences
- Number formatting conventions

### Currency Configuration

- Primary currency code
- Symbol and positioning
- Decimal/thousands separators
- Precision settings

### Business Configuration

- Plan types and categories
- Status definitions and colors
- Partner tier structures
- Business units (bandwidth, data, currency)

### Branding Configuration

- Company information
- Logo and favicon paths
- Portal-specific names and themes
- Brand color palette

### Feature Flags

- Enable/disable advanced features
- Control access to premium functionality
- Manage deployment complexity

### API Configuration

- Base URL and version
- Timeout and retry settings
- Authentication endpoints

### Monitoring Configuration

- Analytics and error reporting
- Performance monitoring
- Custom endpoint URLs

## Creating Custom Configurations

1. **Start with a base configuration** that matches your region/size
2. **Modify business logic** (plans, statuses, tiers) for your offerings
3. **Update branding** with your company information
4. **Set feature flags** based on your operational capabilities
5. **Configure localization** for your target markets
6. **Test with formatting hooks** to ensure proper display

## Best Practices

1. **Use TypeScript** for configuration files to catch errors early
2. **Validate configurations** before deployment
3. **Version control** configuration changes
4. **Test localization** with actual data in all supported locales
5. **Document custom configurations** for your team
6. **Use environment variables** for sensitive settings (API keys, endpoints)

## Advanced Customization

For advanced customization beyond configuration:

1. **Custom themes** - Extend the theme system with your brand colors
2. **Custom hooks** - Create business-specific formatting and logic hooks
3. **Custom components** - Build portal-specific UI components
4. **Custom workflows** - Implement ISP-specific business processes

See the main documentation for more details on extending the framework.
