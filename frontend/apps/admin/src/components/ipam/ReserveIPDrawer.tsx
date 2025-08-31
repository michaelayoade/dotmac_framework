/**
 * Reserve IP Drawer Component
 * Form for reserving IP addresses within subnets
 */

import React, { useState } from 'react';
import { Shield, X, Plus, AlertTriangle } from 'lucide-react';

export interface ReserveIPDrawerProps {
  subnet?: {
    id: string;
    subnet: string;
    description: string;
    available_ips: number;
  };
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (reservation: any) => void;
}

export const ReserveIPDrawer: React.FC<ReserveIPDrawerProps> = ({
  subnet,
  isOpen,
  onClose,
  onSubmit
}) => {
  const [formData, setFormData] = useState({
    ip_address: '',
    description: '',
    device_id: '',
    reservation_type: 'static',
    duration: '',
    notes: ''
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const reservationTypes = [
    { value: 'static', label: 'Static Assignment' },
    { value: 'dhcp_reservation', label: 'DHCP Reservation' },
    { value: 'temporary', label: 'Temporary Reserve' },
    { value: 'infrastructure', label: 'Infrastructure' }
  ];

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.ip_address.trim()) {
      newErrors.ip_address = 'IP address is required';
    } else if (!/^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(formData.ip_address)) {
      newErrors.ip_address = 'Invalid IP address format';
    } else if (subnet) {
      // Basic check if IP is within subnet range
      const [network] = subnet.subnet.split('/');
      const networkParts = network.split('.').map(n => parseInt(n));
      const ipParts = formData.ip_address.split('.').map(n => parseInt(n));
      
      // Simple subnet validation (for /24 subnets)
      if (networkParts[0] !== ipParts[0] || 
          networkParts[1] !== ipParts[1] || 
          networkParts[2] !== ipParts[2]) {
        newErrors.ip_address = `IP address must be within ${subnet.subnet}`;
      }
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    }

    if (formData.reservation_type === 'temporary' && !formData.duration) {
      newErrors.duration = 'Duration is required for temporary reservations';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (validateForm() && subnet) {
      onSubmit({
        ...formData,
        id: `reservation-${Date.now()}`, // Temporary ID
        subnet_id: subnet.id,
        status: 'reserved',
        created_at: new Date().toISOString(),
        expires_at: formData.reservation_type === 'temporary' && formData.duration
          ? new Date(Date.now() + parseInt(formData.duration) * 24 * 60 * 60 * 1000).toISOString()
          : null
      });
      
      // Reset form
      setFormData({
        ip_address: '',
        description: '',
        device_id: '',
        reservation_type: 'static',
        duration: '',
        notes: ''
      });
      
      onClose();
    }
  };

  const handleChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  // Auto-suggest next available IP
  const suggestNextIP = () => {
    if (subnet) {
      const [network] = subnet.subnet.split('/');
      const parts = network.split('.');
      // Simple suggestion: increment last octet
      const suggested = `${parts[0]}.${parts[1]}.${parts[2]}.${parseInt(parts[3]) + 10}`;
      handleChange('ip_address', suggested);
    }
  };

  if (!isOpen || !subnet) return null;

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      
      {/* Drawer */}
      <div className="absolute right-0 top-0 h-full w-full max-w-lg bg-white shadow-xl">
        <form onSubmit={handleSubmit} className="flex flex-col h-full" data-testid="reserve-ip-drawer">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b">
            <div className="flex items-center gap-3">
              <Shield className="w-6 h-6 text-blue-600" />
              <div>
                <h2 className="text-xl font-semibold">Reserve IP Address</h2>
                <p className="text-sm text-gray-600">Reserve IP in {subnet.subnet}</p>
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Form Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Subnet Information */}
            <div className="bg-blue-50 rounded-lg p-4">
              <h3 className="font-semibold text-blue-900 mb-2">Target Subnet</h3>
              <div className="text-sm text-blue-800 space-y-1">
                <div><strong>CIDR:</strong> {subnet.subnet}</div>
                <div><strong>Description:</strong> {subnet.description}</div>
                <div><strong>Available IPs:</strong> {subnet.available_ips.toLocaleString()}</div>
              </div>
            </div>

            {/* IP Address Configuration */}
            <div>
              <h3 className="text-lg font-semibold mb-4">IP Address Configuration</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    IP Address *
                  </label>
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={formData.ip_address}
                      onChange={(e) => handleChange('ip_address', e.target.value)}
                      className={`flex-1 px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                        errors.ip_address ? 'border-red-300' : 'border-gray-300'
                      }`}
                      placeholder="e.g., 192.168.1.100"
                      data-testid="ip-address-input"
                    />
                    <button
                      type="button"
                      onClick={suggestNextIP}
                      className="px-3 py-2 bg-gray-100 text-gray-700 rounded hover:bg-gray-200 transition-colors text-sm"
                    >
                      Suggest
                    </button>
                  </div>
                  {errors.ip_address && (
                    <div className="flex items-center gap-1 mt-1 text-sm text-red-600">
                      <AlertTriangle className="w-4 h-4" />
                      {errors.ip_address}
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Reservation Type *
                  </label>
                  <select
                    value={formData.reservation_type}
                    onChange={(e) => handleChange('reservation_type', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    data-testid="reservation-type-select"
                  >
                    {reservationTypes.map(type => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                {formData.reservation_type === 'temporary' && (
                  <div>
                    <label className="block text-sm font-medium mb-2">
                      Duration (days) *
                    </label>
                    <input
                      type="number"
                      value={formData.duration}
                      onChange={(e) => handleChange('duration', e.target.value)}
                      className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                        errors.duration ? 'border-red-300' : 'border-gray-300'
                      }`}
                      placeholder="e.g., 30"
                      min="1"
                      max="365"
                      data-testid="duration-input"
                    />
                    {errors.duration && (
                      <div className="flex items-center gap-1 mt-1 text-sm text-red-600">
                        <AlertTriangle className="w-4 h-4" />
                        {errors.duration}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Assignment Details */}
            <div>
              <h3 className="text-lg font-semibold mb-4">Assignment Details</h3>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium mb-2">
                    Description *
                  </label>
                  <input
                    type="text"
                    value={formData.description}
                    onChange={(e) => handleChange('description', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.description ? 'border-red-300' : 'border-gray-300'
                    }`}
                    placeholder="e.g., Core Router Management Interface"
                    data-testid="description-input"
                  />
                  {errors.description && (
                    <div className="flex items-center gap-1 mt-1 text-sm text-red-600">
                      <AlertTriangle className="w-4 h-4" />
                      {errors.description}
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Device ID
                  </label>
                  <input
                    type="text"
                    value={formData.device_id}
                    onChange={(e) => handleChange('device_id', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="e.g., dev-core-001 (optional)"
                    data-testid="device-id-input"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Link this IP to a specific device
                  </p>
                </div>

                <div>
                  <label className="block text-sm font-medium mb-2">
                    Additional Notes
                  </label>
                  <textarea
                    value={formData.notes}
                    onChange={(e) => handleChange('notes', e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    rows={3}
                    placeholder="Optional notes about this reservation"
                    data-testid="notes-input"
                  />
                </div>
              </div>
            </div>

            {/* Reservation Summary */}
            {formData.ip_address && formData.reservation_type && (
              <div>
                <h3 className="text-lg font-semibold mb-4">Reservation Summary</h3>
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">IP Address:</span>
                      <span className="font-medium">{formData.ip_address}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Type:</span>
                      <span className="font-medium capitalize">
                        {formData.reservation_type.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Subnet:</span>
                      <span className="font-medium">{subnet.subnet}</span>
                    </div>
                    {formData.reservation_type === 'temporary' && formData.duration && (
                      <div className="flex justify-between">
                        <span className="text-gray-600">Expires:</span>
                        <span className="font-medium">
                          {new Date(Date.now() + parseInt(formData.duration) * 24 * 60 * 60 * 1000).toLocaleDateString()}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className="border-t px-6 py-4 bg-gray-50">
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors flex items-center gap-2"
                data-testid="reserve-ip-submit"
              >
                <Shield className="w-4 h-4" />
                Reserve IP
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};