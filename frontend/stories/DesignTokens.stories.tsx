import type { Meta, StoryObj } from '@storybook/react';

const meta: Meta = {
  title: 'Design System/Design Tokens',
  parameters: {
    layout: 'fullscreen',
    docs: {
      description: {
        component:
          'Design tokens define the visual foundation of the DotMac platform including colors, typography, spacing, and more.',
      },
    },
  },
};

export default meta;

const ColorPalette = () => {
  const colors = {
    primary: { 50: '#eff6ff', 100: '#dbeafe', 500: '#3b82f6', 900: '#1e3a8a' },
    success: { 50: '#f0fdf4', 100: '#dcfce7', 500: '#22c55e', 900: '#14532d' },
    warning: { 50: '#fffbeb', 100: '#fef3c7', 500: '#f59e0b', 900: '#78350f' },
    error: { 50: '#fef2f2', 100: '#fee2e2', 500: '#ef4444', 900: '#7f1d1d' },
    gray: { 50: '#f9fafb', 100: '#f3f4f6', 500: '#6b7280', 900: '#111827' },
  };

  return (
    <div className='p-6'>
      <h2 className='text-2xl font-bold mb-6'>Color Palette</h2>
      {Object.entries(colors).map(([name, shades]) => (
        <div key={name} className='mb-8'>
          <h3 className='text-lg font-semibold mb-4 capitalize'>{name}</h3>
          <div className='flex gap-2'>
            {Object.entries(shades).map(([shade, hex]) => (
              <div key={shade} className='text-center'>
                <div
                  className='w-20 h-20 rounded-lg shadow-md mb-2'
                  style={{ backgroundColor: hex }}
                />
                <div className='text-xs font-mono'>{shade}</div>
                <div className='text-xs text-gray-500'>{hex}</div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
};

export const Colors = {
  render: () => <ColorPalette />,
  parameters: {
    docs: {
      description: {
        story: 'Complete color palette with semantic color assignments for different UI states.',
      },
    },
  },
};

const TypographyScale = () => {
  const typeScale = [
    { name: 'Display Large', class: 'text-6xl font-bold', sample: 'The quick brown fox' },
    { name: 'Display Medium', class: 'text-5xl font-bold', sample: 'The quick brown fox' },
    { name: 'Display Small', class: 'text-4xl font-bold', sample: 'The quick brown fox' },
    {
      name: 'Headline Large',
      class: 'text-3xl font-semibold',
      sample: 'The quick brown fox jumps',
    },
    {
      name: 'Headline Medium',
      class: 'text-2xl font-semibold',
      sample: 'The quick brown fox jumps over',
    },
    {
      name: 'Headline Small',
      class: 'text-xl font-semibold',
      sample: 'The quick brown fox jumps over the lazy dog',
    },
    {
      name: 'Title Large',
      class: 'text-lg font-medium',
      sample: 'The quick brown fox jumps over the lazy dog',
    },
    {
      name: 'Title Medium',
      class: 'text-base font-medium',
      sample: 'The quick brown fox jumps over the lazy dog',
    },
    {
      name: 'Body Large',
      class: 'text-base',
      sample:
        'The quick brown fox jumps over the lazy dog and continues running through the forest.',
    },
    {
      name: 'Body Medium',
      class: 'text-sm',
      sample:
        'The quick brown fox jumps over the lazy dog and continues running through the forest with great speed.',
    },
    {
      name: 'Body Small',
      class: 'text-xs',
      sample:
        'The quick brown fox jumps over the lazy dog and continues running through the forest with great speed and agility.',
    },
  ];

  return (
    <div className='p-6'>
      <h2 className='text-2xl font-bold mb-6'>Typography Scale</h2>
      <div className='space-y-6'>
        {typeScale.map((type, index) => (
          <div key={index} className='border-b border-gray-200 pb-4'>
            <div className='flex items-baseline justify-between mb-2'>
              <span className='text-sm font-medium text-gray-600'>{type.name}</span>
              <code className='text-xs text-gray-500'>{type.class}</code>
            </div>
            <p className={type.class}>{type.sample}</p>
          </div>
        ))}
      </div>
    </div>
  );
};

export const Typography = {
  render: () => <TypographyScale />,
  parameters: {
    docs: {
      description: {
        story: 'Typography scale showing all text styles used in the design system.',
      },
    },
  },
};

const SpacingSystem = () => {
  const spacing = [
    { name: 'xs', value: '0.25rem', pixels: '4px' },
    { name: 'sm', value: '0.5rem', pixels: '8px' },
    { name: 'md', value: '1rem', pixels: '16px' },
    { name: 'lg', value: '1.5rem', pixels: '24px' },
    { name: 'xl', value: '2rem', pixels: '32px' },
    { name: '2xl', value: '2.5rem', pixels: '40px' },
    { name: '3xl', value: '3rem', pixels: '48px' },
  ];

  return (
    <div className='p-6'>
      <h2 className='text-2xl font-bold mb-6'>Spacing System</h2>
      <div className='space-y-4'>
        {spacing.map((space) => (
          <div key={space.name} className='flex items-center gap-4'>
            <div className='w-16 text-sm font-medium'>{space.name}</div>
            <div className='w-20 text-xs text-gray-600'>{space.value}</div>
            <div className='w-16 text-xs text-gray-500'>({space.pixels})</div>
            <div className='bg-blue-500 h-4' style={{ width: space.value }} />
          </div>
        ))}
      </div>
    </div>
  );
};

export const Spacing = {
  render: () => <SpacingSystem />,
  parameters: {
    docs: {
      description: {
        story: 'Spacing scale used for margins, padding, and layout consistency.',
      },
    },
  },
};
