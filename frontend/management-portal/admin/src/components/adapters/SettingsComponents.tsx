'use client'

import { ReactNode, ComponentType, useState } from 'react'
import { createAdaptiveComponent } from './ComponentLoader'
import { User, Bell, Shield, Palette } from 'lucide-react'

// Fallback types
export type ProfileData = {
  name: string
  email: string
  role: string
  avatar?: string
}

export type NotificationSettings = {
  email: boolean
  sms: boolean
  push: boolean
  marketing: boolean
}

export type SecuritySettings = {
  twoFactor: boolean
  sessionTimeout: number
  loginNotifications: boolean
}

export type AppearanceSettings = {
  theme: 'light' | 'dark' | 'auto'
  language: string
  timezone: string
}

// Fallback implementations
function FallbackProfileSettings({ profile, onUpdate, loading }: any) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Profile Information</h3>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Full Name</label>
            <input
              type="text"
              className="input"
              defaultValue={profile?.name || ''}
              placeholder="Enter your name"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
            <input
              type="email"
              className="input"
              defaultValue={profile?.email || ''}
              placeholder="Enter your email"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Role</label>
            <select className="input" defaultValue={profile?.role || 'admin'}>
              <option value="admin">Administrator</option>
              <option value="user">User</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}

function FallbackNotificationSettings({ settings, onUpdate, loading }: any) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Notification Preferences</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-medium text-gray-900">Email Notifications</h4>
              <p className="text-sm text-gray-500">Receive notifications via email</p>
            </div>
            <input 
              type="checkbox" 
              defaultChecked={settings?.email || true}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-medium text-gray-900">Push Notifications</h4>
              <p className="text-sm text-gray-500">Receive push notifications</p>
            </div>
            <input 
              type="checkbox" 
              defaultChecked={settings?.push || false}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function FallbackSecuritySettings({ settings, onUpdate, loading }: any) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Security Settings</h3>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-medium text-gray-900">Two-Factor Authentication</h4>
              <p className="text-sm text-gray-500">Add an extra layer of security</p>
            </div>
            <input 
              type="checkbox" 
              defaultChecked={settings?.twoFactor || false}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h4 className="text-sm font-medium text-gray-900">Login Notifications</h4>
              <p className="text-sm text-gray-500">Get notified of new logins</p>
            </div>
            <input 
              type="checkbox" 
              defaultChecked={settings?.loginNotifications || true}
              className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function FallbackAppearanceSettings({ settings, onUpdate, loading }: any) {
  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">Appearance Settings</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Theme</label>
            <select className="input" defaultValue={settings?.theme || 'light'}>
              <option value="light">Light</option>
              <option value="dark">Dark</option>
              <option value="auto">Auto</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Language</label>
            <select className="input" defaultValue={settings?.language || 'en'}>
              <option value="en">English</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  )
}

// Fallback hook
function fallbackUseSettings() {
  const [profile, setProfile] = useState<ProfileData>({
    name: 'Admin User',
    email: 'admin@example.com',
    role: 'admin'
  })
  
  return {
    profile,
    updateProfile: (data: ProfileData) => setProfile(data),
    loading: false,
    error: null
  }
}

// Default settings helpers
export const getDefaultNotificationSettings = () => ({
  email: true,
  sms: false,
  push: false,
  marketing: false
})

export const getDefaultSecuritySettings = () => ({
  twoFactor: false,
  sessionTimeout: 3600,
  loginNotifications: true
})

export const getDefaultAppearanceSettings = () => ({
  theme: 'light' as const,
  language: 'en',
  timezone: 'UTC'
})

// Create adaptive components
export const ProfileSettings = createAdaptiveComponent(
  '@dotmac/settings-system',
  'ProfileSettings',
  FallbackProfileSettings
)

export const NotificationSettings = createAdaptiveComponent(
  '@dotmac/settings-system',
  'NotificationSettings',
  FallbackNotificationSettings
)

export const SecuritySettings = createAdaptiveComponent(
  '@dotmac/settings-system',
  'SecuritySettings',
  FallbackSecuritySettings
)

export const AppearanceSettings = createAdaptiveComponent(
  '@dotmac/settings-system',
  'AppearanceSettings',
  FallbackAppearanceSettings
)

// Hook wrapper - this needs special handling since it's a hook
export const useSettings = fallbackUseSettings