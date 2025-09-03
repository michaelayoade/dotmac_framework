/**
 * Edit Device Drawer Component
 * Form for editing existing network devices
 */

import React, { useState, useEffect } from 'react';
import { Server, X, Save, AlertTriangle } from 'lucide-react';

export interface EditDeviceDrawerProps {
  device?: {
    id: string;
    hostname: string;
    device_type: string;
    management_ip: string;
    vendor?: string;
    model?: string;
    serial_number?: string;
    location?: { id: string; name: string };
    description?: string;
  };
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (device: any) => void;
}

export const EditDeviceDrawer: React.FC<EditDeviceDrawerProps> = ({
  device,
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [formData, setFormData] = useState({
    hostname: '',
    device_type: 'router',
    management_ip: '',
    vendor: '',
    model: '',
    serial_number: '',
    location_id: '',
    description: '',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  // Update form data when device prop changes
  useEffect(() => {
    if (device) {
      setFormData({
        hostname: device.hostname || '',
        device_type: device.device_type || 'router',
        management_ip: device.management_ip || '',
        vendor: device.vendor || '',
        model: device.model || '',
        serial_number: device.serial_number || '',
        location_id: device.location?.id || '',
        description: device.description || '',
      });
    }
  }, [device]);

  const deviceTypes = [
    { value: 'router', label: 'Router' },
    { value: 'switch', label: 'Switch' },
    { value: 'access_point', label: 'Access Point' },
    { value: 'firewall', label: 'Firewall' },
    { value: 'load_balancer', label: 'Load Balancer' },
    { value: 'ont', label: 'ONT' },
    { value: 'server', label: 'Server' },
  ];

  const vendors = [
    { value: 'cisco', label: 'Cisco' },
    { value: 'juniper', label: 'Juniper' },
    { value: 'ubiquiti', label: 'Ubiquiti' },
    { value: 'hpe', label: 'HPE' },
    { value: 'dell', label: 'Dell' },
    { value: 'mikrotik', label: 'Mikrotik' },
    { value: 'adtran', label: 'Adtran' },
  ];

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.hostname.trim()) {
      newErrors.hostname = 'Hostname is required';
    }

    if (!formData.management_ip.trim()) {
      newErrors.management_ip = 'Management IP is required';
    } else if (!/^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(formData.management_ip)) {
      newErrors.management_ip = 'Invalid IP address format';
    }

    if (!formData.vendor) {
      newErrors.vendor = 'Vendor is required';
    }

    if (!formData.model.trim()) {
      newErrors.model = 'Model is required';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (validateForm() && device) {
      onSubmit({
        ...device,
        ...formData,
        location: formData.location_id
          ? { id: formData.location_id, name: 'Updated Location' }
          : device.location,
      });

      onClose();
    }
  };

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: '' }));
    }
  };

  if (!isOpen || !device) return null;

  return (
    <div className='fixed inset-0 z-50 overflow-hidden'>
      {/* Backdrop */}
      <div className='absolute inset-0 bg-black/50' onClick={onClose} />

      {/* Drawer */}
      <div className='absolute right-0 top-0 h-full w-full max-w-lg bg-white shadow-xl'>
        <form
          onSubmit={handleSubmit}
          className='flex flex-col h-full'
          data-testid='edit-device-drawer'
        >
          {/* Header */}
          <div className='flex items-center justify-between px-6 py-4 border-b'>
            <div className='flex items-center gap-3'>
              <Save className='w-6 h-6 text-blue-600' />
              <div>
                <h2 className='text-xl font-semibold'>Edit Device</h2>
                <p className='text-sm text-gray-600'>{device.hostname}</p>
              </div>
            </div>
            <button
              type='button'
              onClick={onClose}
              className='p-2 hover:bg-gray-100 rounded-full transition-colors'
            >
              <X className='w-5 h-5' />
            </button>
          </div>

          {/* Form Content */}
          <div className='flex-1 overflow-y-auto p-6 space-y-6'>
            {/* Basic Information */}
            <div>
              <h3 className='text-lg font-semibold mb-4'>Basic Information</h3>

              <div className='space-y-4'>
                <div>
                  <label className='block text-sm font-medium mb-2'>Hostname *</label>
                  <input
                    type='text'
                    value={formData.hostname}
                    onChange={(e) => handleChange('hostname', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.hostname ? 'border-red-300' : 'border-gray-300'
                    }`}
                    placeholder='e.g., core-router-01'
                    data-testid='hostname-input'
                  />
                  {errors.hostname && (
                    <div className='flex items-center gap-1 mt-1 text-sm text-red-600'>
                      <AlertTriangle className='w-4 h-4' />
                      {errors.hostname}
                    </div>
                  )}
                </div>

                <div>
                  <label className='block text-sm font-medium mb-2'>Device Type *</label>
                  <select
                    value={formData.device_type}
                    onChange={(e) => handleChange('device_type', e.target.value)}
                    className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                    data-testid='device-type-select'
                  >
                    {deviceTypes.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className='block text-sm font-medium mb-2'>Management IP Address *</label>
                  <input
                    type='text'
                    value={formData.management_ip}
                    onChange={(e) => handleChange('management_ip', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.management_ip ? 'border-red-300' : 'border-gray-300'
                    }`}
                    placeholder='e.g., 192.168.1.1'
                    data-testid='management-ip-input'
                  />
                  {errors.management_ip && (
                    <div className='flex items-center gap-1 mt-1 text-sm text-red-600'>
                      <AlertTriangle className='w-4 h-4' />
                      {errors.management_ip}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Hardware Information */}
            <div>
              <h3 className='text-lg font-semibold mb-4'>Hardware Information</h3>

              <div className='space-y-4'>
                <div>
                  <label className='block text-sm font-medium mb-2'>Vendor *</label>
                  <select
                    value={formData.vendor}
                    onChange={(e) => handleChange('vendor', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.vendor ? 'border-red-300' : 'border-gray-300'
                    }`}
                    data-testid='vendor-select'
                  >
                    <option value=''>Select Vendor</option>
                    {vendors.map((vendor) => (
                      <option key={vendor.value} value={vendor.value}>
                        {vendor.label}
                      </option>
                    ))}
                  </select>
                  {errors.vendor && (
                    <div className='flex items-center gap-1 mt-1 text-sm text-red-600'>
                      <AlertTriangle className='w-4 h-4' />
                      {errors.vendor}
                    </div>
                  )}
                </div>

                <div>
                  <label className='block text-sm font-medium mb-2'>Model *</label>
                  <input
                    type='text'
                    value={formData.model}
                    onChange={(e) => handleChange('model', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.model ? 'border-red-300' : 'border-gray-300'
                    }`}
                    placeholder='e.g., ASR-1006-X'
                    data-testid='model-input'
                  />
                  {errors.model && (
                    <div className='flex items-center gap-1 mt-1 text-sm text-red-600'>
                      <AlertTriangle className='w-4 h-4' />
                      {errors.model}
                    </div>
                  )}
                </div>

                <div>
                  <label className='block text-sm font-medium mb-2'>Serial Number</label>
                  <input
                    type='text'
                    value={formData.serial_number}
                    onChange={(e) => handleChange('serial_number', e.target.value)}
                    className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                    placeholder='e.g., CSR1006X001'
                    data-testid='serial-number-input'
                  />
                </div>
              </div>
            </div>

            {/* Additional Information */}
            <div>
              <h3 className='text-lg font-semibold mb-4'>Additional Information</h3>

              <div className='space-y-4'>
                <div>
                  <label className='block text-sm font-medium mb-2'>Location</label>
                  <select
                    value={formData.location_id}
                    onChange={(e) => handleChange('location_id', e.target.value)}
                    className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                    data-testid='location-select'
                  >
                    <option value=''>Select Location</option>
                    <option value='loc-001'>Seattle Data Center</option>
                    <option value='loc-002'>Bellevue Distribution</option>
                    <option value='loc-003'>Office Building A</option>
                  </select>
                </div>

                <div>
                  <label className='block text-sm font-medium mb-2'>Description</label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => handleChange('description', e.target.value)}
                    className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                    rows={3}
                    placeholder='Optional description or notes'
                    data-testid='description-input'
                  />
                </div>
              </div>
            </div>

            {/* Device Status Information (Read-only) */}
            <div>
              <h3 className='text-lg font-semibold mb-4'>Device Status (Read-only)</h3>

              <div className='bg-gray-50 rounded-lg p-4 space-y-3'>
                <div className='flex justify-between'>
                  <span className='text-sm font-medium'>Device ID:</span>
                  <span className='text-sm text-gray-600'>{device.id}</span>
                </div>

                {device.serial_number && (
                  <div className='flex justify-between'>
                    <span className='text-sm font-medium'>Current Serial:</span>
                    <span className='text-sm text-gray-600'>{device.serial_number}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Footer Actions */}
          <div className='border-t px-6 py-4 bg-gray-50'>
            <div className='flex justify-end gap-3'>
              <button
                type='button'
                onClick={onClose}
                className='px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors'
              >
                Cancel
              </button>
              <button
                type='submit'
                className='px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors flex items-center gap-2'
                data-testid='update-device-submit'
              >
                <Save className='w-4 h-4' />
                Update Device
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
