'use client';

import { useState } from 'react';
import {
  Monitor,
  Moon,
  Sun,
  Eye,
  Zap,
  Layout,
  Type,
  Palette,
  Settings,
  Check,
  MousePointer,
} from 'lucide-react';
import { AppearanceSettings as AppearanceSettingsType } from '../types';

export interface AppearanceSettingsProps {
  settings: AppearanceSettingsType;
  onUpdate: (settings: Partial<AppearanceSettingsType>) => void;
  onSave?: () => Promise<boolean>;
  isLoading?: boolean;
  readonly?: boolean;
  className?: string;
}

export function AppearanceSettings({
  settings,
  onUpdate,
  onSave,
  isLoading = false,
  readonly = false,
  className = '',
}: AppearanceSettingsProps) {
  const [previewMode, setPreviewMode] = useState<'light' | 'dark' | null>(null);

  const updateTheme = (key: keyof AppearanceSettingsType['theme'], value: any) => {
    onUpdate({
      theme: {
        ...settings.theme,
        [key]: value,
      },
    });
  };

  const updateAccessibility = (
    key: keyof AppearanceSettingsType['accessibility'],
    value: boolean
  ) => {
    onUpdate({
      accessibility: {
        ...settings.accessibility,
        [key]: value,
      },
    });
  };

  const updateLayout = (key: keyof AppearanceSettingsType['layout'], value: any) => {
    onUpdate({
      layout: {
        ...settings.layout,
        [key]: value,
      },
    });
  };

  const getThemeIcon = (mode: string) => {
    switch (mode) {
      case 'light':
        return <Sun className='h-5 w-5' />;
      case 'dark':
        return <Moon className='h-5 w-5' />;
      case 'system':
        return <Monitor className='h-5 w-5' />;
      default:
        return <Monitor className='h-5 w-5' />;
    }
  };

  const getThemeDescription = (mode: string) => {
    switch (mode) {
      case 'light':
        return 'Always use light theme';
      case 'dark':
        return 'Always use dark theme';
      case 'system':
        return 'Follow system preference';
      default:
        return 'Follow system preference';
    }
  };

  const primaryColors = [
    { name: 'Blue', value: '#3b82f6', class: 'bg-blue-500' },
    { name: 'Purple', value: '#8b5cf6', class: 'bg-purple-500' },
    { name: 'Green', value: '#10b981', class: 'bg-green-500' },
    { name: 'Red', value: '#ef4444', class: 'bg-red-500' },
    { name: 'Orange', value: '#f97316', class: 'bg-orange-500' },
    { name: 'Pink', value: '#ec4899', class: 'bg-pink-500' },
    { name: 'Teal', value: '#14b8a6', class: 'bg-teal-500' },
    { name: 'Indigo', value: '#6366f1', class: 'bg-indigo-500' },
  ];

  const fontSizes = [
    { name: 'Small', value: 'small', description: '14px base size' },
    { name: 'Medium', value: 'medium', description: '16px base size' },
    { name: 'Large', value: 'large', description: '18px base size' },
  ];

  const densityOptions = [
    { name: 'Compact', value: 'compact', description: 'More content, less spacing' },
    { name: 'Comfortable', value: 'comfortable', description: 'Balanced spacing' },
    { name: 'Spacious', value: 'spacious', description: 'More spacing, less content' },
  ];

  return (
    <div className={`bg-white rounded-lg border shadow-sm ${className}`}>
      <div className='p-6'>
        <div className='mb-6'>
          <h2 className='text-xl font-semibold text-gray-900'>Appearance Settings</h2>
          <p className='mt-1 text-sm text-gray-500'>
            Customize the look and feel of your interface
          </p>
        </div>

        {/* Theme Settings */}
        <div className='mb-8'>
          <h3 className='text-lg font-medium text-gray-900 mb-4 flex items-center'>
            <Palette className='h-5 w-5 mr-2' />
            Theme Preferences
          </h3>

          {/* Theme Mode */}
          <div className='mb-6'>
            <label className='block text-sm font-medium text-gray-700 mb-3'>Theme Mode</label>
            <div className='grid grid-cols-1 sm:grid-cols-3 gap-3'>
              {['light', 'dark', 'system'].map((mode) => (
                <button
                  key={mode}
                  onClick={() => updateTheme('mode', mode)}
                  disabled={readonly || isLoading}
                  className={`p-4 border rounded-lg text-left transition-all ${
                    settings.theme.mode === mode
                      ? 'border-blue-500 bg-blue-50 text-blue-900'
                      : 'border-gray-300 hover:border-gray-400'
                  } ${readonly || isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                >
                  <div className='flex items-center mb-2'>
                    {getThemeIcon(mode)}
                    <span className='ml-2 font-medium capitalize'>{mode}</span>
                    {settings.theme.mode === mode && (
                      <Check className='ml-auto h-4 w-4 text-blue-600' />
                    )}
                  </div>
                  <p className='text-sm text-gray-600'>{getThemeDescription(mode)}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Primary Color */}
          <div className='mb-6'>
            <label className='block text-sm font-medium text-gray-700 mb-3'>Primary Color</label>
            <div className='grid grid-cols-4 sm:grid-cols-8 gap-3'>
              {primaryColors.map((color) => (
                <button
                  key={color.value}
                  onClick={() => updateTheme('primaryColor', color.value)}
                  disabled={readonly || isLoading}
                  className={`relative w-12 h-12 rounded-lg ${color.class} transition-transform ${
                    readonly || isLoading
                      ? 'opacity-50 cursor-not-allowed'
                      : 'hover:scale-110 cursor-pointer'
                  }`}
                  title={color.name}
                >
                  {settings.theme.primaryColor === color.value && (
                    <div className='absolute inset-0 flex items-center justify-center'>
                      <Check className='h-6 w-6 text-white drop-shadow-lg' />
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Font Size */}
          <div className='mb-6'>
            <label className='block text-sm font-medium text-gray-700 mb-3'>Font Size</label>
            <div className='grid grid-cols-1 sm:grid-cols-3 gap-3'>
              {fontSizes.map((size) => (
                <button
                  key={size.value}
                  onClick={() => updateTheme('fontSize', size.value)}
                  disabled={readonly || isLoading}
                  className={`p-3 border rounded-lg text-left transition-all ${
                    settings.theme.fontSize === size.value
                      ? 'border-blue-500 bg-blue-50 text-blue-900'
                      : 'border-gray-300 hover:border-gray-400'
                  } ${readonly || isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                >
                  <div className='flex items-center justify-between mb-1'>
                    <span className='font-medium'>{size.name}</span>
                    {settings.theme.fontSize === size.value && (
                      <Check className='h-4 w-4 text-blue-600' />
                    )}
                  </div>
                  <p className='text-xs text-gray-600'>{size.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Other Theme Options */}
          <div className='space-y-4'>
            <div className='flex items-center justify-between'>
              <div>
                <h4 className='text-sm font-medium text-gray-900'>Compact Mode</h4>
                <p className='text-sm text-gray-500'>Reduce spacing and padding</p>
              </div>
              <button
                onClick={() => updateTheme('compactMode', !settings.theme.compactMode)}
                disabled={readonly || isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.theme.compactMode ? 'bg-blue-600' : 'bg-gray-200'
                } ${readonly || isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.theme.compactMode ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className='flex items-center justify-between'>
              <div>
                <h4 className='text-sm font-medium text-gray-900'>Animations</h4>
                <p className='text-sm text-gray-500'>Enable smooth transitions and animations</p>
              </div>
              <button
                onClick={() => updateTheme('animations', !settings.theme.animations)}
                disabled={readonly || isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.theme.animations ? 'bg-blue-600' : 'bg-gray-200'
                } ${readonly || isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.theme.animations ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Layout Settings */}
        <div className='mb-8'>
          <h3 className='text-lg font-medium text-gray-900 mb-4 flex items-center'>
            <Layout className='h-5 w-5 mr-2' />
            Layout Preferences
          </h3>

          {/* Density */}
          <div className='mb-6'>
            <label className='block text-sm font-medium text-gray-700 mb-3'>Layout Density</label>
            <div className='grid grid-cols-1 sm:grid-cols-3 gap-3'>
              {densityOptions.map((density) => (
                <button
                  key={density.value}
                  onClick={() => updateLayout('density', density.value)}
                  disabled={readonly || isLoading}
                  className={`p-3 border rounded-lg text-left transition-all ${
                    settings.layout.density === density.value
                      ? 'border-blue-500 bg-blue-50 text-blue-900'
                      : 'border-gray-300 hover:border-gray-400'
                  } ${readonly || isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                >
                  <div className='flex items-center justify-between mb-1'>
                    <span className='font-medium'>{density.name}</span>
                    {settings.layout.density === density.value && (
                      <Check className='h-4 w-4 text-blue-600' />
                    )}
                  </div>
                  <p className='text-xs text-gray-600'>{density.description}</p>
                </button>
              ))}
            </div>
          </div>

          {/* Other Layout Options */}
          <div className='space-y-4'>
            <div className='flex items-center justify-between'>
              <div>
                <h4 className='text-sm font-medium text-gray-900'>Sidebar Collapsed</h4>
                <p className='text-sm text-gray-500'>Start with sidebar in collapsed state</p>
              </div>
              <button
                onClick={() => updateLayout('sidebarCollapsed', !settings.layout.sidebarCollapsed)}
                disabled={readonly || isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.layout.sidebarCollapsed ? 'bg-blue-600' : 'bg-gray-200'
                } ${readonly || isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.layout.sidebarCollapsed ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className='flex items-center justify-between'>
              <div>
                <h4 className='text-sm font-medium text-gray-900'>Show Tooltips</h4>
                <p className='text-sm text-gray-500'>Display helpful tooltips on hover</p>
              </div>
              <button
                onClick={() => updateLayout('showTooltips', !settings.layout.showTooltips)}
                disabled={readonly || isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.layout.showTooltips ? 'bg-blue-600' : 'bg-gray-200'
                } ${readonly || isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.layout.showTooltips ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Accessibility Settings */}
        <div className='mb-8'>
          <h3 className='text-lg font-medium text-gray-900 mb-4 flex items-center'>
            <Eye className='h-5 w-5 mr-2' />
            Accessibility Options
          </h3>

          <div className='space-y-4'>
            <div className='flex items-center justify-between'>
              <div>
                <h4 className='text-sm font-medium text-gray-900'>High Contrast</h4>
                <p className='text-sm text-gray-500'>Increase contrast for better visibility</p>
              </div>
              <button
                onClick={() =>
                  updateAccessibility('highContrast', !settings.accessibility.highContrast)
                }
                disabled={readonly || isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.accessibility.highContrast ? 'bg-blue-600' : 'bg-gray-200'
                } ${readonly || isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.accessibility.highContrast ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className='flex items-center justify-between'>
              <div>
                <h4 className='text-sm font-medium text-gray-900'>Reduced Motion</h4>
                <p className='text-sm text-gray-500'>Minimize animations and transitions</p>
              </div>
              <button
                onClick={() =>
                  updateAccessibility('reducedMotion', !settings.accessibility.reducedMotion)
                }
                disabled={readonly || isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.accessibility.reducedMotion ? 'bg-blue-600' : 'bg-gray-200'
                } ${readonly || isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.accessibility.reducedMotion ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className='flex items-center justify-between'>
              <div>
                <h4 className='text-sm font-medium text-gray-900'>Enhanced Focus Indicators</h4>
                <p className='text-sm text-gray-500'>
                  More visible focus outlines for keyboard navigation
                </p>
              </div>
              <button
                onClick={() =>
                  updateAccessibility('focusIndicators', !settings.accessibility.focusIndicators)
                }
                disabled={readonly || isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.accessibility.focusIndicators ? 'bg-blue-600' : 'bg-gray-200'
                } ${readonly || isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.accessibility.focusIndicators ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className='flex items-center justify-between'>
              <div>
                <h4 className='text-sm font-medium text-gray-900'>Keyboard Navigation</h4>
                <p className='text-sm text-gray-500'>Enhanced keyboard shortcuts and navigation</p>
              </div>
              <button
                onClick={() =>
                  updateAccessibility(
                    'keyboardNavigation',
                    !settings.accessibility.keyboardNavigation
                  )
                }
                disabled={readonly || isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.accessibility.keyboardNavigation ? 'bg-blue-600' : 'bg-gray-200'
                } ${readonly || isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.accessibility.keyboardNavigation ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>

            <div className='flex items-center justify-between'>
              <div>
                <h4 className='text-sm font-medium text-gray-900'>Screen Reader Support</h4>
                <p className='text-sm text-gray-500'>
                  Enhanced labels and descriptions for screen readers
                </p>
              </div>
              <button
                onClick={() =>
                  updateAccessibility('screenReader', !settings.accessibility.screenReader)
                }
                disabled={readonly || isLoading}
                className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                  settings.accessibility.screenReader ? 'bg-blue-600' : 'bg-gray-200'
                } ${readonly || isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
              >
                <span
                  className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                    settings.accessibility.screenReader ? 'translate-x-6' : 'translate-x-1'
                  }`}
                />
              </button>
            </div>
          </div>
        </div>

        {/* Save Button */}
        {!readonly && onSave && (
          <div className='pt-4 border-t'>
            <button
              onClick={onSave}
              disabled={isLoading}
              className='w-full sm:w-auto px-6 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed'
            >
              {isLoading ? (
                <div className='flex items-center'>
                  <div className='mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent' />
                  Saving...
                </div>
              ) : (
                'Save Appearance Settings'
              )}
            </button>
          </div>
        )}

        {/* Preview Info */}
        <div className='mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg'>
          <div className='flex items-start'>
            <Settings className='h-5 w-5 text-blue-600 mt-0.5 flex-shrink-0' />
            <div className='ml-3'>
              <h4 className='font-medium text-blue-900'>Appearance Tips</h4>
              <div className='mt-1 text-sm text-blue-700'>
                <ul className='list-disc pl-5 space-y-1'>
                  <li>
                    System theme automatically switches between light and dark based on your OS
                    settings
                  </li>
                  <li>High contrast mode improves visibility for users with vision difficulties</li>
                  <li>Reduced motion helps users who are sensitive to movement and animations</li>
                  <li>Changes apply immediately without requiring a page refresh</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
