'use client';

import { useState } from 'react';
import {
  AlertCircle,
  Building,
  Calendar,
  Camera,
  Check,
  Edit3,
  Globe,
  Mail,
  MapPin,
  Phone,
  Save,
  Upload,
  User,
  X,
} from 'lucide-react';
import { ProfileData } from '../types';

export interface ProfileSettingsProps {
  profileData: ProfileData;
  onUpdate: (data: Partial<ProfileData>) => void;
  onSave?: () => Promise<boolean>;
  isLoading?: boolean;
  readonly?: boolean;
  className?: string;
}

export function ProfileSettings({
  profileData,
  onUpdate,
  onSave,
  isLoading = false,
  readonly = false,
  className = '',
}: ProfileSettingsProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedData, setEditedData] = useState<ProfileData>(profileData);
  const [isSaving, setIsSaving] = useState(false);
  const [activeSection, setActiveSection] = useState<
    'personal' | 'contact' | 'preferences' | 'emergency'
  >('personal');

  const handleEdit = () => {
    setEditedData({ ...profileData });
    setIsEditing(true);
  };

  const handleCancel = () => {
    setEditedData({ ...profileData });
    setIsEditing(false);
  };

  const handleSave = async () => {
    setIsSaving(true);

    try {
      onUpdate(editedData);

      if (onSave) {
        const success = await onSave();
        if (success) {
          setIsEditing(false);
        }
      } else {
        // Simulate save delay
        await new Promise(resolve => setTimeout(resolve, 500));
        setIsEditing(false);
      }
    } catch (error) {
      console.error('Failed to save profile:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleInputChange = (field: string, value: string, section?: string) => {
    if (section) {
      setEditedData(prev => ({
        ...prev,
        [section]: {
          ...prev[section as keyof ProfileData],
          [field]: value,
        },
      }));
    } else {
      setEditedData(prev => ({
        ...prev,
        [field]: value,
      }));
    }
  };

  const handleAvatarUpload = () => {
    // In a real app, this would handle file upload
    console.log('Avatar upload triggered');
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  };

  const currentData = isEditing ? editedData : profileData;

  return (
    <div className={`bg-white rounded-lg border shadow-sm ${className}`}>
      <div className="p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">Profile Information</h2>
            <p className="mt-1 text-sm text-gray-500">
              Manage your personal information and account details
            </p>
          </div>
          {!readonly && (
            <div className="flex items-center space-x-2">
              {isEditing ? (
                <>
                  <button
                    onClick={handleCancel}
                    disabled={isSaving || isLoading}
                    className="rounded-lg border border-gray-300 px-4 py-2 text-gray-700 transition-colors hover:bg-gray-50 disabled:opacity-50"
                  >
                    <X className="mr-2 h-4 w-4" />
                    Cancel
                  </button>
                  <button
                    onClick={handleSave}
                    disabled={isSaving || isLoading}
                    className="rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700 disabled:opacity-50"
                  >
                    {isSaving || isLoading ? (
                      <div className="mr-2 h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                    ) : (
                      <Save className="mr-2 h-4 w-4" />
                    )}
                    {isSaving || isLoading ? 'Saving...' : 'Save Changes'}
                  </button>
                </>
              ) : (
                <button
                  onClick={handleEdit}
                  className="rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700"
                >
                  <Edit3 className="mr-2 h-4 w-4" />
                  Edit Profile
                </button>
              )}
            </div>
          )}
        </div>

        {/* Section Navigation */}
        <div className="mb-6 border-b border-gray-200">
          <nav className="-mb-px flex space-x-8">
            {[
              { id: 'personal', label: 'Personal Info', icon: User },
              { id: 'contact', label: 'Contact Details', icon: Mail },
              { id: 'preferences', label: 'Preferences', icon: Globe },
              { id: 'emergency', label: 'Emergency Contact', icon: AlertCircle },
            ].map(section => (
              <button
                key={section.id}
                onClick={() => setActiveSection(section.id as any)}
                className={`flex items-center border-b-2 px-1 py-2 text-sm font-medium ${
                  activeSection === section.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                }`}
              >
                <section.icon className="mr-2 h-4 w-4" />
                {section.label}
              </button>
            ))}
          </nav>
        </div>

        {/* Personal Information */}
        {activeSection === 'personal' && (
          <div className="space-y-6">
            {/* Avatar */}
            <div className="flex items-center space-x-6">
              <div className="relative">
                <div className="h-24 w-24 rounded-full bg-gray-200 flex items-center justify-center overflow-hidden">
                  {currentData.avatar ? (
                    <img
                      src={currentData.avatar}
                      alt="Profile"
                      className="h-full w-full object-cover"
                    />
                  ) : (
                    <User className="h-12 w-12 text-gray-400" />
                  )}
                </div>
                {isEditing && (
                  <button
                    onClick={handleAvatarUpload}
                    className="absolute -bottom-1 -right-1 rounded-full bg-blue-600 p-2 text-white hover:bg-blue-700 transition-colors"
                  >
                    <Camera className="h-4 w-4" />
                  </button>
                )}
              </div>
              <div>
                <h3 className="text-lg font-medium text-gray-900">
                  {currentData.firstName} {currentData.lastName}
                </h3>
                <p className="text-gray-600">{currentData.email}</p>
                {isEditing && (
                  <button
                    onClick={handleAvatarUpload}
                    className="mt-2 text-blue-600 hover:text-blue-800 text-sm font-medium"
                  >
                    <Upload className="mr-1 h-4 w-4 inline" />
                    Upload new photo
                  </button>
                )}
              </div>
            </div>

            {/* Name Fields */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">First Name</label>
                {isEditing ? (
                  <input
                    type="text"
                    value={currentData.firstName}
                    onChange={e => handleInputChange('firstName', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                ) : (
                  <p className="text-gray-900">{currentData.firstName}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Last Name</label>
                {isEditing ? (
                  <input
                    type="text"
                    value={currentData.lastName}
                    onChange={e => handleInputChange('lastName', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                ) : (
                  <p className="text-gray-900">{currentData.lastName}</p>
                )}
              </div>
            </div>

            {/* Date of Birth */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Date of Birth</label>
              {isEditing ? (
                <input
                  type="date"
                  value={currentData.dateOfBirth}
                  onChange={e => handleInputChange('dateOfBirth', e.target.value)}
                  className="w-full md:w-64 rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              ) : (
                <div className="flex items-center text-gray-900">
                  <Calendar className="mr-2 h-4 w-4 text-gray-400" />
                  {formatDate(currentData.dateOfBirth)}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Contact Details */}
        {activeSection === 'contact' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
                {isEditing ? (
                  <div className="relative">
                    <Mail className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                    <input
                      type="email"
                      value={currentData.email}
                      onChange={e => handleInputChange('email', e.target.value)}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 pl-10 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                ) : (
                  <div className="flex items-center text-gray-900">
                    <Mail className="mr-2 h-4 w-4 text-gray-400" />
                    {currentData.email}
                  </div>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Phone Number</label>
                {isEditing ? (
                  <div className="relative">
                    <Phone className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                    <input
                      type="tel"
                      value={currentData.phone}
                      onChange={e => handleInputChange('phone', e.target.value)}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 pl-10 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                ) : (
                  <div className="flex items-center text-gray-900">
                    <Phone className="mr-2 h-4 w-4 text-gray-400" />
                    {currentData.phone}
                  </div>
                )}
              </div>
            </div>

            {/* Address */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Address</label>
              {isEditing ? (
                <div className="space-y-4">
                  <input
                    type="text"
                    value={currentData.address.street}
                    onChange={e => handleInputChange('street', e.target.value, 'address')}
                    placeholder="Street Address"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <input
                      type="text"
                      value={currentData.address.city}
                      onChange={e => handleInputChange('city', e.target.value, 'address')}
                      placeholder="City"
                      className="col-span-2 rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                    <input
                      type="text"
                      value={currentData.address.state}
                      onChange={e => handleInputChange('state', e.target.value, 'address')}
                      placeholder="State"
                      className="rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                    <input
                      type="text"
                      value={currentData.address.zipCode}
                      onChange={e => handleInputChange('zipCode', e.target.value, 'address')}
                      placeholder="ZIP Code"
                      className="rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                </div>
              ) : (
                <div className="flex items-start text-gray-900">
                  <MapPin className="mr-2 h-4 w-4 text-gray-400 mt-1 flex-shrink-0" />
                  <div>
                    <p>{currentData.address.street}</p>
                    <p>
                      {currentData.address.city}, {currentData.address.state}{' '}
                      {currentData.address.zipCode}
                    </p>
                    <p>{currentData.address.country}</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Preferences */}
        {activeSection === 'preferences' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Language</label>
                {isEditing ? (
                  <select
                    value={currentData.preferences.language}
                    onChange={e => handleInputChange('language', e.target.value, 'preferences')}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="en-US">English (US)</option>
                    <option value="es-ES">Español</option>
                    <option value="fr-FR">Français</option>
                  </select>
                ) : (
                  <p className="text-gray-900">English (US)</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Timezone</label>
                {isEditing ? (
                  <select
                    value={currentData.preferences.timezone}
                    onChange={e => handleInputChange('timezone', e.target.value, 'preferences')}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="America/Los_Angeles">Pacific Time (PT)</option>
                    <option value="America/Denver">Mountain Time (MT)</option>
                    <option value="America/Chicago">Central Time (CT)</option>
                    <option value="America/New_York">Eastern Time (ET)</option>
                  </select>
                ) : (
                  <p className="text-gray-900">Pacific Time (PT)</p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Date Format</label>
                {isEditing ? (
                  <select
                    value={currentData.preferences.dateFormat}
                    onChange={e => handleInputChange('dateFormat', e.target.value, 'preferences')}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                    <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                    <option value="YYYY-MM-DD">YYYY-MM-DD</option>
                  </select>
                ) : (
                  <p className="text-gray-900">{currentData.preferences.dateFormat}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Currency</label>
                {isEditing ? (
                  <select
                    value={currentData.preferences.currency}
                    onChange={e => handleInputChange('currency', e.target.value, 'preferences')}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="USD">USD ($)</option>
                    <option value="EUR">EUR (€)</option>
                    <option value="GBP">GBP (£)</option>
                  </select>
                ) : (
                  <p className="text-gray-900">USD ($)</p>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Emergency Contact */}
        {activeSection === 'emergency' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Emergency Contact Name
                </label>
                {isEditing ? (
                  <input
                    type="text"
                    value={currentData.emergencyContact.name}
                    onChange={e => handleInputChange('name', e.target.value, 'emergencyContact')}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  />
                ) : (
                  <p className="text-gray-900">{currentData.emergencyContact.name}</p>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Relationship</label>
                {isEditing ? (
                  <select
                    value={currentData.emergencyContact.relationship}
                    onChange={e =>
                      handleInputChange('relationship', e.target.value, 'emergencyContact')
                    }
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                  >
                    <option value="Spouse">Spouse</option>
                    <option value="Parent">Parent</option>
                    <option value="Child">Child</option>
                    <option value="Sibling">Sibling</option>
                    <option value="Friend">Friend</option>
                    <option value="Other">Other</option>
                  </select>
                ) : (
                  <p className="text-gray-900">{currentData.emergencyContact.relationship}</p>
                )}
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Phone Number</label>
                {isEditing ? (
                  <div className="relative">
                    <Phone className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                    <input
                      type="tel"
                      value={currentData.emergencyContact.phone}
                      onChange={e => handleInputChange('phone', e.target.value, 'emergencyContact')}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 pl-10 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                ) : (
                  <div className="flex items-center text-gray-900">
                    <Phone className="mr-2 h-4 w-4 text-gray-400" />
                    {currentData.emergencyContact.phone}
                  </div>
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Email Address</label>
                {isEditing ? (
                  <div className="relative">
                    <Mail className="absolute left-3 top-2.5 h-4 w-4 text-gray-400" />
                    <input
                      type="email"
                      value={currentData.emergencyContact.email}
                      onChange={e => handleInputChange('email', e.target.value, 'emergencyContact')}
                      className="w-full rounded-lg border border-gray-300 px-3 py-2 pl-10 focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                ) : (
                  <div className="flex items-center text-gray-900">
                    <Mail className="mr-2 h-4 w-4 text-gray-400" />
                    {currentData.emergencyContact.email}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Last Updated */}
        <div className="mt-8 pt-6 border-t border-gray-200">
          <div className="flex items-center text-sm text-gray-500">
            <Check className="mr-2 h-4 w-4 text-green-600" />
            Last updated: {formatDate(profileData.lastUpdated)}
          </div>
        </div>
      </div>
    </div>
  );
}
