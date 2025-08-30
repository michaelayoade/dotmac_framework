# @dotmac/navigation-system

A comprehensive, universal navigation system for the DotMac ISP Framework that consolidates all navigation patterns across different portal types.

## Features

- **Universal Components**: Single set of navigation components that adapt to different portal variants (admin, customer, reseller, technician, management)
- **Flexible Layouts**: Support for sidebar, topbar, and hybrid navigation layouts
- **Mobile Optimized**: Responsive navigation with drawer, tabs, and bottom-sheet variants
- **Accessibility**: Full keyboard navigation, ARIA compliance, and screen reader support
- **Theme Variants**: Built-in styling for different portal types with customizable branding
- **TypeScript**: Full TypeScript support with comprehensive type definitions
- **Composable**: Modular components that can be used independently or together

## Installation

```bash
npm install @dotmac/navigation-system
# or
pnpm add @dotmac/navigation-system
# or
yarn add @dotmac/navigation-system
```

## Quick Start

```tsx
import { UniversalNavigation } from '@dotmac/navigation-system';
import { Home, Users, Settings, BarChart } from 'lucide-react';

const navigationItems = [
  { id: 'dashboard', label: 'Dashboard', icon: Home, href: '/dashboard' },
  { id: 'users', label: 'Users', icon: Users, href: '/users' },
  { id: 'analytics', label: 'Analytics', icon: BarChart, href: '/analytics' },
  { id: 'settings', label: 'Settings', icon: Settings, href: '/settings' },
];

function App() {
  return (
    <UniversalNavigation
      items={navigationItems}
      variant="admin"
      layoutType="sidebar"
      user={{
        id: 'user-1',
        name: 'John Doe',
        email: 'john@example.com',
        role: 'Administrator'
      }}
      branding={{
        companyName: 'My ISP Portal',
        primaryColor: '#3B82F6'
      }}
      onNavigate={(item) => {
        // Handle navigation
        window.location.href = item.href;
      }}
    >
      {/* Your main content */}
      <div className="p-6">
        <h1>Welcome to your dashboard!</h1>
      </div>
    </UniversalNavigation>
  );
}
```

## Components

### UniversalNavigation

The main navigation wrapper that provides complete navigation functionality.

```tsx
<UniversalNavigation
  items={navigationItems}
  variant="admin" // admin | customer | reseller | technician | management
  layoutType="sidebar" // sidebar | topbar | hybrid
  user={userInfo}
  branding={brandingConfig}
  onNavigate={handleNavigate}
  onLogout={handleLogout}
>
  {children}
</UniversalNavigation>
```

### UniversalSidebar

Standalone sidebar component for custom layouts.

```tsx
<UniversalSidebar
  items={navigationItems}
  variant="admin"
  collapsed={false}
  collapsible={true}
  onCollapsedChange={setCollapsed}
  onNavigate={handleNavigate}
/>
```

### UniversalTopbar

Header/topbar component with navigation and user menu.

```tsx
<UniversalTopbar
  items={navigationItems}
  variant="customer"
  user={userInfo}
  branding={brandingConfig}
  onNavigate={handleNavigate}
  onLogout={handleLogout}
/>
```

### UniversalMobileNavigation

Mobile-optimized navigation with drawer, tabs, or bottom-sheet variants.

```tsx
<UniversalMobileNavigation
  items={navigationItems}
  variant="drawer" // drawer | tabs | bottom-sheet
  onNavigate={handleNavigate}
/>
```

### UniversalBreadcrumb

Breadcrumb navigation for showing current location hierarchy.

```tsx
<UniversalBreadcrumb
  items={breadcrumbItems}
  showHome={true}
  maxItems={5}
  onNavigate={handleNavigate}
/>
```

### UniversalTabNavigation

Tab-based navigation for section switching.

```tsx
<UniversalTabNavigation
  items={tabItems}
  variant="default" // default | pills | underline | cards
  size="md" // sm | md | lg
  orientation="horizontal" // horizontal | vertical
  onNavigate={handleNavigate}
/>
```

## Hooks

### useNavigationState

Manage navigation state with URL synchronization.

```tsx
import { useNavigationState } from '@dotmac/navigation-system';

function MyComponent() {
  const {
    activeItem,
    expandedItems,
    collapsed,
    handleNavigate,
    toggleExpanded,
    toggleCollapsed,
    isActive,
    isExpanded,
  } = useNavigationState({
    items: navigationItems,
    syncWithUrl: true,
    onNavigate: (item) => {
      // Custom navigation logic
    }
  });
}
```

### useKeyboardNavigation

Add keyboard navigation support to custom components.

```tsx
import { useKeyboardNavigation } from '@dotmac/navigation-system';

function MyNavigation() {
  const { containerRef } = useKeyboardNavigation({
    items: navigationItems,
    activeItem: currentActiveItem,
    onNavigate: handleNavigate,
    enabled: true,
  });

  return (
    <nav ref={containerRef}>
      {/* Navigation items */}
    </nav>
  );
}
```

## Portal Variants

The navigation system supports different portal types with appropriate styling:

- **admin**: Blue theme for administrative interfaces
- **customer**: Green theme for customer portals
- **reseller**: Purple theme for reseller interfaces
- **technician**: Orange theme for field technician apps
- **management**: Gray theme for management portals

## Layout Types

### Sidebar Layout (Default)

- Collapsible sidebar navigation
- Main content area
- Mobile drawer for small screens

### Topbar Layout

- Header-based navigation
- Full-width content
- Mobile tabs or drawer

### Hybrid Layout

- Header with sidebar
- Best of both worlds
- Flexible content organization

## Customization

### Custom Styling

The components use Tailwind CSS classes and can be customized using the `className` prop:

```tsx
<UniversalNavigation
  className="custom-navigation-styles"
  items={items}
  variant="admin"
/>
```

### Custom Branding

```tsx
const branding = {
  logo: <CustomLogo />,
  logoUrl: '/path/to/logo.png',
  companyName: 'My ISP Company',
  primaryColor: '#3B82F6',
  secondaryColor: '#1E40AF',
};

<UniversalNavigation branding={branding} />
```

## Navigation Items Structure

```tsx
interface NavigationItem {
  id: string;
  label: string;
  href: string;
  icon?: LucideIcon;
  badge?: string | number;
  description?: string;
  disabled?: boolean;
  children?: NavigationItem[]; // For nested navigation
}
```

## Accessibility

- Full keyboard navigation (Arrow keys, Enter, Space, Home, End)
- ARIA labels and roles
- Screen reader support
- Focus management
- High contrast support

## TypeScript Support

The package includes comprehensive TypeScript definitions:

```tsx
import type {
  NavigationItem,
  NavigationUser,
  NavigationBranding,
  NavigationVariant,
  LayoutType,
} from '@dotmac/navigation-system';
```

## Migration Guide

### From Existing Components

Replace existing navigation components:

```tsx
// Before
import { AdminLayout } from './components/layout/AdminLayout';
import { AdminSidebar } from './components/layout/AdminSidebar';
import { AdminHeader } from './components/layout/AdminHeader';

// After
import { UniversalNavigation } from '@dotmac/navigation-system';
```

### DRY Benefits

This package consolidates:

- 5 sidebar variations → 1 universal component
- 7 header implementations → 1 universal component
- 4+ breadcrumb systems → 1 universal component
- 3+ mobile navigation approaches → 1 universal component
- 5+ tab implementations → 1 universal component

**Code reduction: ~60%**

## Contributing

Please refer to the main DotMac Framework contributing guidelines.

## License

MIT License - see the main framework license for details.
