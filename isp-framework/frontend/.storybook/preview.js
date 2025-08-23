import React from 'react';
import { themes } from '@storybook/theming';
import '../apps/admin/src/app/globals.css';

// Import security provider for all stories
import { SecurityProvider } from '@dotmac/security';

/** @type {import('@storybook/react').Preview} */
const preview = {
  // Global parameters
  parameters: {
    // Actions
    actions: { argTypesRegex: '^on[A-Z].*' },

    // Controls
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/,
      },
      expanded: true,
    },

    // Docs configuration
    docs: {
      theme: themes.light,
      canvas: {
        sourceState: 'shown',
      },
    },

    // Accessibility testing
    a11y: {
      element: '#storybook-root',
      config: {
        rules: [
          // Enable all WCAG 2.1 AA rules
          {
            id: 'color-contrast',
            enabled: true,
          },
          {
            id: 'landmark-one-main',
            enabled: false, // Disable for component stories
          },
          {
            id: 'page-has-heading-one',
            enabled: false, // Disable for component stories
          },
          {
            id: 'region',
            enabled: false, // Disable for component stories
          },
        ],
      },
      options: {
        checks: { 'color-contrast': { options: { noScroll: true } } },
        restoreScroll: true,
      },
    },

    // Viewport configuration
    viewport: {
      viewports: {
        mobile: {
          name: 'Mobile',
          styles: {
            width: '375px',
            height: '667px',
          },
        },
        tablet: {
          name: 'Tablet',
          styles: {
            width: '768px',
            height: '1024px',
          },
        },
        desktop: {
          name: 'Desktop',
          styles: {
            width: '1200px',
            height: '800px',
          },
        },
        wide: {
          name: 'Wide Screen',
          styles: {
            width: '1440px',
            height: '900px',
          },
        },
      },
    },

    // Background configuration
    backgrounds: {
      default: 'light',
      values: [
        {
          name: 'light',
          value: '#ffffff',
        },
        {
          name: 'dark',
          value: '#1a1a1a',
        },
        {
          name: 'admin',
          value: '#f8fafc',
        },
        {
          name: 'customer',
          value: '#f0f9ff',
        },
        {
          name: 'reseller',
          value: '#fefce8',
        },
      ],
    },

    // Layout configuration
    layout: 'padded',

    // Performance monitoring
    performance: {
      allowedGroups: ['paint', 'interaction', 'measure', 'navigation'],
    },
  },

  // Global arg types
  argTypes: {
    // Common props for all components
    className: {
      control: 'text',
      description: 'Additional CSS classes',
      table: {
        type: { summary: 'string' },
        defaultValue: { summary: 'undefined' },
      },
    },

    // Accessibility props
    'aria-label': {
      control: 'text',
      description: 'Accessible label for screen readers',
      table: {
        category: 'Accessibility',
        type: { summary: 'string' },
      },
    },

    'aria-describedby': {
      control: 'text',
      description: 'ID of element that describes this component',
      table: {
        category: 'Accessibility',
        type: { summary: 'string' },
      },
    },

    // Security props
    sanitize: {
      control: 'boolean',
      description: 'Whether to sanitize input/content',
      table: {
        category: 'Security',
        type: { summary: 'boolean' },
        defaultValue: { summary: 'true' },
      },
    },
  },

  // Global decorators
  decorators: [
    // Security Provider decorator
    (Story, context) => {
      const { parameters } = context;
      const securityConfig = parameters.security || {};

      return (
        <SecurityProvider
          enableValidation={securityConfig.enableValidation !== false}
          enableSanitization={securityConfig.enableSanitization !== false}
          logSecurityEvents={securityConfig.logSecurityEvents || false}
        >
          <Story />
        </SecurityProvider>
      );
    },

    // Theme decorator
    (Story, context) => {
      const { parameters, globals } = context;
      const theme = globals.theme || parameters.theme || 'light';

      return (
        <div
          data-theme={theme}
          className={`storybook-theme storybook-theme--${theme}`}
          style={{
            minHeight: '100vh',
            padding: '1rem',
          }}
        >
          <Story />
        </div>
      );
    },

    // Portal context decorator
    (Story, context) => {
      const { parameters } = context;
      const portal = parameters.portal || 'admin';

      return (
        <div data-portal={portal} className={`portal-${portal}`}>
          <Story />
        </div>
      );
    },

    // Performance monitoring decorator
    (Story, context) => {
      React.useEffect(() => {
        const startTime = performance.now();

        return () => {
          const endTime = performance.now();
          const renderTime = endTime - startTime;

          if (renderTime > 16) {
            // More than one frame
            console.warn(`Story "${context.title}" rendered slowly: ${renderTime.toFixed(2)}ms`);
          }
        };
      }, [context.title]);

      return <Story />;
    },
  ],

  // Global types for toolbar
  globalTypes: {
    theme: {
      name: 'Theme',
      description: 'Global theme for components',
      defaultValue: 'light',
      toolbar: {
        icon: 'mirror',
        items: [
          { value: 'light', title: 'Light', icon: 'sun' },
          { value: 'dark', title: 'Dark', icon: 'moon' },
        ],
      },
    },

    portal: {
      name: 'Portal',
      description: 'Portal context for components',
      defaultValue: 'admin',
      toolbar: {
        icon: 'user',
        items: [
          { value: 'admin', title: 'Admin Portal' },
          { value: 'customer', title: 'Customer Portal' },
          { value: 'reseller', title: 'Reseller Portal' },
          { value: 'shared', title: 'Shared Components' },
        ],
      },
    },

    a11y: {
      name: 'Accessibility',
      description: 'Accessibility testing mode',
      defaultValue: 'enabled',
      toolbar: {
        icon: 'accessibility',
        items: [
          { value: 'enabled', title: 'Enabled' },
          { value: 'disabled', title: 'Disabled' },
        ],
      },
    },
  },

  // Tags for organizing stories
  tags: ['autodocs'],
};

export default preview;
