import type { Meta, StoryObj } from '@storybook/react';
import React from 'react';
import { PortalProviderFactory } from './PortalProviderFactory';

const meta: Meta<typeof PortalProviderFactory> = {
  title: 'Providers/PortalProviderFactory',
  component: PortalProviderFactory as any,
  parameters: {
    layout: 'fullscreen',
  },
  argTypes: {
    config: {
      control: 'object',
    },
  },
};

export default meta;
type Story = StoryObj<typeof meta>;

const DemoContent = () => (
  <div style={{ padding: 24 }}>
    <h2 style={{ marginBottom: 12 }}>Portal Layout Preview</h2>
    <p>Use controls to switch portal, density, and color scheme.</p>
    <div style={{ marginTop: 24, display: 'grid', gap: 12 }}>
      <button>Primary Action</button>
      <input placeholder='Search...' />
      <div
        style={{
          height: 120,
          border: '1px dashed #ccc',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        Table/Content Area
      </div>
      <div
        style={{
          height: 48,
          border: '1px solid var(--auth-border)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 12px',
        }}
      >
        Toolbar with filters
      </div>
    </div>
  </div>
);

export const DensityAndThemeMatrix: Story = {
  args: {
    config: {
      portal: 'admin',
      authVariant: 'enterprise',
      density: 'comfortable',
      colorScheme: 'system',
      features: { notifications: true, devtools: false },
    },
    customProviders: undefined,
  } as any,
  render: (args: any) => (
    <PortalProviderFactory {...args}>
      <DemoContent />
    </PortalProviderFactory>
  ),
  parameters: {
    docs: {
      description: {
        story:
          'Toggle density (compact/cozy/comfortable) and color scheme (light/dark/system) to validate design tokens across portals.',
      },
    },
  },
};

export const TechnicianCompactDark: Story = {
  args: {
    config: {
      portal: 'technician',
      authVariant: 'enterprise',
      density: 'compact',
      colorScheme: 'dark',
      features: { notifications: true },
    },
  } as any,
  render: (args: any) => (
    <PortalProviderFactory {...args}>
      <DemoContent />
    </PortalProviderFactory>
  ),
};

export const CustomerCozyLight: Story = {
  args: {
    config: {
      portal: 'customer',
      authVariant: 'customer',
      density: 'cozy',
      colorScheme: 'light',
      features: { notifications: true },
    },
  } as any,
  render: (args: any) => (
    <PortalProviderFactory {...args}>
      <DemoContent />
    </PortalProviderFactory>
  ),
};

export const ManagementAdminComfortableSystem: Story = {
  args: {
    config: {
      portal: 'management-admin',
      authVariant: 'enterprise',
      density: 'comfortable',
      colorScheme: 'system',
      features: { notifications: true, analytics: true },
    },
  } as any,
  render: (args: any) => (
    <PortalProviderFactory {...args}>
      <DemoContent />
    </PortalProviderFactory>
  ),
};
