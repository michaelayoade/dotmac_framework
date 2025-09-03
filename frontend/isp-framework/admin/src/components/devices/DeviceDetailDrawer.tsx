/**
 * Device Detail Drawer Component
 * Displays comprehensive device information in a side drawer
 */

import React from 'react';
import {
  Server,
  Activity,
  Cpu,
  MemoryStick,
  Network,
  Clock,
  MapPin,
  Tag,
  AlertTriangle,
  CheckCircle,
  X,
} from 'lucide-react';
import { formatBytes, formatDistance, formatDate } from '@dotmac/utils';

export interface DeviceDetailProps {
  device: {
    id: string;
    hostname: string;
    device_type: string;
    status: string;
    management_ip: string;
    location?: { id: string; name: string };
    uptime: number;
    cpu_usage: number;
    memory_usage: number;
    last_seen: string;
    vendor?: string;
    model?: string;
    firmware_version?: string;
    serial_number?: string;
    interfaces?: Array<{
      name: string;
      status: string;
      speed: string;
      utilization: number;
    }>;
    monitoring_data?: {
      cpu_history: number[];
      memory_history: number[];
    };
  };
  isOpen: boolean;
  onClose: () => void;
}

const StatusIcon = ({ status }: { status: string }) => {
  switch (status.toLowerCase()) {
    case 'online':
      return <CheckCircle className='w-5 h-5 text-green-500' />;
    case 'degraded':
    case 'warning':
      return <AlertTriangle className='w-5 h-5 text-yellow-500' />;
    case 'offline':
    case 'error':
      return <AlertTriangle className='w-5 h-5 text-red-500' />;
    default:
      return <Activity className='w-5 h-5 text-gray-500' />;
  }
};

export const DeviceDetailDrawer: React.FC<DeviceDetailProps> = ({ device, isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className='fixed inset-0 z-50 overflow-hidden'>
      {/* Backdrop */}
      <div className='absolute inset-0 bg-black/50' onClick={onClose} />

      {/* Drawer */}
      <div className='absolute right-0 top-0 h-full w-full max-w-2xl bg-white shadow-xl'>
        <div className='flex flex-col h-full' data-testid='device-detail-drawer'>
          {/* Header */}
          <div className='flex items-center justify-between px-6 py-4 border-b'>
            <div className='flex items-center gap-3'>
              <Server className='w-6 h-6 text-blue-600' />
              <div>
                <h2 className='text-xl font-semibold'>Device Details</h2>
                <p className='text-sm text-gray-600'>{device.hostname}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className='p-2 hover:bg-gray-100 rounded-full transition-colors'
            >
              <X className='w-5 h-5' />
            </button>
          </div>

          {/* Content */}
          <div className='flex-1 overflow-y-auto p-6 space-y-6'>
            {/* Status Overview */}
            <div className='bg-gray-50 rounded-lg p-4'>
              <div className='flex items-center gap-3 mb-3'>
                <StatusIcon status={device.status} />
                <span className='font-medium capitalize'>{device.status}</span>
                <span className='text-sm text-gray-500'>
                  Last seen {formatDate(device.last_seen)}
                </span>
              </div>

              <div className='grid grid-cols-2 gap-4 text-sm'>
                <div>
                  <span className='text-gray-600'>Uptime</span>
                  <div className='font-medium' data-testid='uptime'>
                    {formatDistance(device.uptime * 1000)}
                  </div>
                </div>
                <div>
                  <span className='text-gray-600'>Type</span>
                  <div className='font-medium capitalize'>
                    {device.device_type.replace('_', ' ')}
                  </div>
                </div>
              </div>
            </div>

            {/* Device Information */}
            <div>
              <h3 className='text-lg font-semibold mb-3'>Device Information</h3>
              <div className='space-y-3'>
                <div className='flex items-center gap-3'>
                  <Network className='w-4 h-4 text-gray-500' />
                  <div>
                    <span className='text-sm text-gray-600'>Management IP</span>
                    <div className='font-medium'>{device.management_ip}</div>
                  </div>
                </div>

                {device.location && (
                  <div className='flex items-center gap-3'>
                    <MapPin className='w-4 h-4 text-gray-500' />
                    <div>
                      <span className='text-sm text-gray-600'>Location</span>
                      <div className='font-medium'>{device.location.name}</div>
                    </div>
                  </div>
                )}

                {device.vendor && (
                  <div className='flex items-center gap-3'>
                    <Tag className='w-4 h-4 text-gray-500' />
                    <div>
                      <span className='text-sm text-gray-600'>Vendor</span>
                      <div className='font-medium'>{device.vendor}</div>
                    </div>
                  </div>
                )}

                {device.model && (
                  <div className='flex items-center gap-3'>
                    <Server className='w-4 h-4 text-gray-500' />
                    <div>
                      <span className='text-sm text-gray-600'>Model</span>
                      <div className='font-medium'>{device.model}</div>
                    </div>
                  </div>
                )}

                {device.serial_number && (
                  <div className='flex items-center gap-3'>
                    <Tag className='w-4 h-4 text-gray-500' />
                    <div>
                      <span className='text-sm text-gray-600'>Serial Number</span>
                      <div className='font-medium'>{device.serial_number}</div>
                    </div>
                  </div>
                )}

                {device.firmware_version && (
                  <div className='flex items-center gap-3'>
                    <Activity className='w-4 h-4 text-gray-500' />
                    <div>
                      <span className='text-sm text-gray-600'>Firmware Version</span>
                      <div className='font-medium'>{device.firmware_version}</div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Resource Usage */}
            <div>
              <h3 className='text-lg font-semibold mb-3'>Resource Usage</h3>
              <div className='space-y-4'>
                <div>
                  <div className='flex items-center justify-between mb-2'>
                    <div className='flex items-center gap-2'>
                      <Cpu className='w-4 h-4 text-blue-500' />
                      <span className='text-sm font-medium'>CPU Usage</span>
                    </div>
                    <span className='text-sm font-medium'>{device.cpu_usage.toFixed(1)}%</span>
                  </div>
                  <div className='w-full bg-gray-200 rounded-full h-2'>
                    <div
                      className='bg-blue-500 h-2 rounded-full transition-all'
                      style={{ width: `${device.cpu_usage}%` }}
                    />
                  </div>
                </div>

                <div>
                  <div className='flex items-center justify-between mb-2'>
                    <div className='flex items-center gap-2'>
                      <MemoryStick className='w-4 h-4 text-purple-500' />
                      <span className='text-sm font-medium'>Memory Usage</span>
                    </div>
                    <span className='text-sm font-medium'>{formatBytes(device.memory_usage)}</span>
                  </div>
                  <div className='w-full bg-gray-200 rounded-full h-2'>
                    <div
                      className='bg-purple-500 h-2 rounded-full transition-all'
                      style={{
                        width: `${Math.min((device.memory_usage / (4 * 1024 ** 3)) * 100, 100)}%`,
                      }}
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Interfaces */}
            {device.interfaces && device.interfaces.length > 0 && (
              <div>
                <h3 className='text-lg font-semibold mb-3'>Network Interfaces</h3>
                <div className='space-y-3'>
                  {device.interfaces.map((interface_, index) => (
                    <div key={index} className='border rounded-lg p-3'>
                      <div className='flex items-center justify-between mb-2'>
                        <div className='font-medium'>{interface_.name}</div>
                        <div className='flex items-center gap-2'>
                          <StatusIcon status={interface_.status} />
                          <span className='text-sm capitalize'>{interface_.status}</span>
                        </div>
                      </div>
                      <div className='text-sm text-gray-600 mb-2'>
                        Speed: {interface_.speed} | Utilization: {interface_.utilization}%
                      </div>
                      <div className='w-full bg-gray-200 rounded-full h-1'>
                        <div
                          className='bg-green-500 h-1 rounded-full'
                          style={{ width: `${interface_.utilization}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Monitoring History */}
            {device.monitoring_data && (
              <div>
                <h3 className='text-lg font-semibold mb-3'>Performance History</h3>
                <div className='bg-gray-50 rounded-lg p-4'>
                  <div className='text-sm text-gray-600 mb-2'>CPU Usage (Last 7 hours)</div>
                  <div className='flex items-end gap-1 h-16 mb-4'>
                    {device.monitoring_data.cpu_history.map((value, index) => (
                      <div
                        key={index}
                        className='bg-blue-500 w-4 rounded-t'
                        style={{ height: `${(value / 100) * 100}%` }}
                        title={`${value}%`}
                      />
                    ))}
                  </div>

                  <div className='text-sm text-gray-600 mb-2'>Memory Usage (Last 7 hours)</div>
                  <div className='flex items-end gap-1 h-16'>
                    {device.monitoring_data.memory_history.map((value, index) => (
                      <div
                        key={index}
                        className='bg-purple-500 w-4 rounded-t'
                        style={{ height: `${(value / 4) * 100}%` }}
                        title={`${value}GB`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className='border-t px-6 py-4 bg-gray-50'>
            <div className='flex justify-between'>
              <button className='px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors'>
                View Logs
              </button>
              <div className='flex gap-2'>
                <button className='px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600 transition-colors'>
                  Restart Device
                </button>
                <button className='px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors'>
                  Edit Device
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
