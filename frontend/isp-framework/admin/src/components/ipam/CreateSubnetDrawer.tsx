/**
 * Create Subnet Drawer Component
 * Form for creating new IP subnets
 */

import React, { useState } from 'react';
import { Network, X, Plus, AlertTriangle } from 'lucide-react';

export interface CreateSubnetDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (subnet: any) => void;
}

export const CreateSubnetDrawer: React.FC<CreateSubnetDrawerProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [formData, setFormData] = useState({
    subnet: '',
    description: '',
    vlan_id: '',
    dhcp_enabled: true,
    gateway: '',
    dns_servers: '',
    location_id: '',
    subnet_type: 'management',
    ip_version: '4',
  });

  const [errors, setErrors] = useState<Record<string, string>>({});

  const subnetTypes = [
    { value: 'management', label: 'Management' },
    { value: 'customer', label: 'Customer' },
    { value: 'infrastructure', label: 'Infrastructure' },
    { value: 'dmz', label: 'DMZ' },
    { value: 'guest', label: 'Guest' },
  ];

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.subnet.trim()) {
      newErrors.subnet = 'Subnet CIDR is required';
    } else if (!/^(?:[0-9]{1,3}\.){3}[0-9]{1,3}\/[0-9]{1,2}$/.test(formData.subnet)) {
      newErrors.subnet = 'Invalid CIDR format (e.g., 192.168.1.0/24)';
    }

    if (!formData.description.trim()) {
      newErrors.description = 'Description is required';
    }

    if (formData.vlan_id && (parseInt(formData.vlan_id) < 1 || parseInt(formData.vlan_id) > 4094)) {
      newErrors.vlan_id = 'VLAN ID must be between 1 and 4094';
    }

    if (!formData.gateway.trim()) {
      newErrors.gateway = 'Gateway IP is required';
    } else if (!/^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(formData.gateway)) {
      newErrors.gateway = 'Invalid IP address format';
    }

    // Validate DNS servers if provided
    if (formData.dns_servers.trim()) {
      const dnsServers = formData.dns_servers.split(',').map((s) => s.trim());
      const invalidDns = dnsServers.find((dns) => !/^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$/.test(dns));
      if (invalidDns) {
        newErrors.dns_servers = 'Invalid DNS server IP address format';
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const calculateSubnetInfo = (cidr: string) => {
    try {
      const [network, prefixLength] = cidr.split('/');
      const prefix = parseInt(prefixLength);
      const totalIps = Math.pow(2, 32 - prefix) - 2; // Subtract network and broadcast

      return {
        total_ips: totalIps,
        used_ips: 0,
        available_ips: totalIps,
        utilization: 0,
      };
    } catch {
      return {
        total_ips: 0,
        used_ips: 0,
        available_ips: 0,
        utilization: 0,
      };
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (validateForm()) {
      const subnetInfo = calculateSubnetInfo(formData.subnet);

      onSubmit({
        ...formData,
        id: `subnet-${Date.now()}`, // Temporary ID
        vlan_id: formData.vlan_id ? parseInt(formData.vlan_id) : null,
        dns_servers: formData.dns_servers
          ? formData.dns_servers.split(',').map((s) => s.trim())
          : [],
        location: formData.location_id
          ? { id: formData.location_id, name: 'Selected Location' }
          : null,
        ...subnetInfo,
      });

      // Reset form
      setFormData({
        subnet: '',
        description: '',
        vlan_id: '',
        dhcp_enabled: true,
        gateway: '',
        dns_servers: '',
        location_id: '',
        subnet_type: 'management',
        ip_version: '4',
      });

      onClose();
    }
  };

  const handleChange = (field: string, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: '' }));
    }
  };

  // Auto-suggest gateway based on subnet
  const handleSubnetChange = (value: string) => {
    handleChange('subnet', value);

    // Auto-suggest gateway (first usable IP)
    if (/^(?:[0-9]{1,3}\.){3}[0-9]{1,3}\/[0-9]{1,2}$/.test(value)) {
      const [network] = value.split('/');
      const parts = network.split('.');
      const suggestedGateway = `${parts[0]}.${parts[1]}.${parts[2]}.1`;
      if (!formData.gateway) {
        handleChange('gateway', suggestedGateway);
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div className='fixed inset-0 z-50 overflow-hidden'>
      {/* Backdrop */}
      <div className='absolute inset-0 bg-black/50' onClick={onClose} />

      {/* Drawer */}
      <div className='absolute right-0 top-0 h-full w-full max-w-lg bg-white shadow-xl'>
        <form
          onSubmit={handleSubmit}
          className='flex flex-col h-full'
          data-testid='create-subnet-drawer'
        >
          {/* Header */}
          <div className='flex items-center justify-between px-6 py-4 border-b'>
            <div className='flex items-center gap-3'>
              <Plus className='w-6 h-6 text-blue-600' />
              <div>
                <h2 className='text-xl font-semibold'>Create New Subnet</h2>
                <p className='text-sm text-gray-600'>Add a subnet to your network</p>
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
            {/* Network Configuration */}
            <div>
              <h3 className='text-lg font-semibold mb-4'>Network Configuration</h3>

              <div className='space-y-4'>
                <div>
                  <label className='block text-sm font-medium mb-2'>Subnet CIDR *</label>
                  <input
                    type='text'
                    value={formData.subnet}
                    onChange={(e) => handleSubnetChange(e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.subnet ? 'border-red-300' : 'border-gray-300'
                    }`}
                    placeholder='e.g., 192.168.1.0/24'
                    data-testid='subnet-cidr-input'
                  />
                  {errors.subnet && (
                    <div className='flex items-center gap-1 mt-1 text-sm text-red-600'>
                      <AlertTriangle className='w-4 h-4' />
                      {errors.subnet}
                    </div>
                  )}
                </div>

                <div>
                  <label className='block text-sm font-medium mb-2'>Description *</label>
                  <input
                    type='text'
                    value={formData.description}
                    onChange={(e) => handleChange('description', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.description ? 'border-red-300' : 'border-gray-300'
                    }`}
                    placeholder='e.g., Management Network'
                    data-testid='subnet-description-input'
                  />
                  {errors.description && (
                    <div className='flex items-center gap-1 mt-1 text-sm text-red-600'>
                      <AlertTriangle className='w-4 h-4' />
                      {errors.description}
                    </div>
                  )}
                </div>

                <div>
                  <label className='block text-sm font-medium mb-2'>Gateway IP *</label>
                  <input
                    type='text'
                    value={formData.gateway}
                    onChange={(e) => handleChange('gateway', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.gateway ? 'border-red-300' : 'border-gray-300'
                    }`}
                    placeholder='e.g., 192.168.1.1'
                    data-testid='gateway-input'
                  />
                  {errors.gateway && (
                    <div className='flex items-center gap-1 mt-1 text-sm text-red-600'>
                      <AlertTriangle className='w-4 h-4' />
                      {errors.gateway}
                    </div>
                  )}
                </div>

                <div>
                  <label className='block text-sm font-medium mb-2'>VLAN ID</label>
                  <input
                    type='number'
                    value={formData.vlan_id}
                    onChange={(e) => handleChange('vlan_id', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.vlan_id ? 'border-red-300' : 'border-gray-300'
                    }`}
                    placeholder='1-4094 (optional)'
                    min='1'
                    max='4094'
                    data-testid='vlan-input'
                  />
                  {errors.vlan_id && (
                    <div className='flex items-center gap-1 mt-1 text-sm text-red-600'>
                      <AlertTriangle className='w-4 h-4' />
                      {errors.vlan_id}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* DHCP Configuration */}
            <div>
              <h3 className='text-lg font-semibold mb-4'>DHCP Configuration</h3>

              <div className='space-y-4'>
                <div className='flex items-center gap-3'>
                  <input
                    type='checkbox'
                    id='dhcp-enabled'
                    checked={formData.dhcp_enabled}
                    onChange={(e) => handleChange('dhcp_enabled', e.target.checked)}
                    className='w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500'
                    data-testid='dhcp-checkbox'
                  />
                  <label htmlFor='dhcp-enabled' className='text-sm font-medium'>
                    Enable DHCP
                  </label>
                </div>

                <div>
                  <label className='block text-sm font-medium mb-2'>DNS Servers</label>
                  <input
                    type='text'
                    value={formData.dns_servers}
                    onChange={(e) => handleChange('dns_servers', e.target.value)}
                    className={`w-full px-3 py-2 border rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                      errors.dns_servers ? 'border-red-300' : 'border-gray-300'
                    }`}
                    placeholder='e.g., 8.8.8.8, 8.8.4.4'
                    data-testid='dns-servers-input'
                  />
                  <p className='text-xs text-gray-500 mt-1'>
                    Separate multiple DNS servers with commas
                  </p>
                  {errors.dns_servers && (
                    <div className='flex items-center gap-1 mt-1 text-sm text-red-600'>
                      <AlertTriangle className='w-4 h-4' />
                      {errors.dns_servers}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Subnet Classification */}
            <div>
              <h3 className='text-lg font-semibold mb-4'>Subnet Classification</h3>

              <div className='space-y-4'>
                <div>
                  <label className='block text-sm font-medium mb-2'>Subnet Type *</label>
                  <select
                    value={formData.subnet_type}
                    onChange={(e) => handleChange('subnet_type', e.target.value)}
                    className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                    data-testid='subnet-type-select'
                  >
                    {subnetTypes.map((type) => (
                      <option key={type.value} value={type.value}>
                        {type.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className='block text-sm font-medium mb-2'>IP Version</label>
                  <select
                    value={formData.ip_version}
                    onChange={(e) => handleChange('ip_version', e.target.value)}
                    className='w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent'
                    data-testid='ip-version-select'
                  >
                    <option value='4'>IPv4</option>
                    <option value='6'>IPv6</option>
                  </select>
                </div>

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
              </div>
            </div>

            {/* Subnet Preview */}
            {formData.subnet && (
              <div>
                <h3 className='text-lg font-semibold mb-4'>Subnet Preview</h3>
                <div className='bg-gray-50 rounded-lg p-4'>
                  {(() => {
                    const info = calculateSubnetInfo(formData.subnet);
                    return (
                      <div className='space-y-2 text-sm'>
                        <div className='flex justify-between'>
                          <span className='text-gray-600'>Network:</span>
                          <span className='font-medium'>{formData.subnet.split('/')[0]}</span>
                        </div>
                        <div className='flex justify-between'>
                          <span className='text-gray-600'>Subnet Mask:</span>
                          <span className='font-medium'>/{formData.subnet.split('/')[1]}</span>
                        </div>
                        <div className='flex justify-between'>
                          <span className='text-gray-600'>Available IPs:</span>
                          <span className='font-medium'>{info.total_ips.toLocaleString()}</span>
                        </div>
                        <div className='flex justify-between'>
                          <span className='text-gray-600'>Suggested Gateway:</span>
                          <span className='font-medium'>{formData.gateway}</span>
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </div>
            )}
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
                data-testid='create-subnet-submit'
              >
                <Network className='w-4 h-4' />
                Create Subnet
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
