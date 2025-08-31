/**
 * IPAM Detail Drawer Component
 * Displays detailed subnet information and IP allocations
 */

import React from 'react';
import { 
  Network, 
  Globe, 
  Activity, 
  Shield, 
  Server,
  MapPin,
  AlertTriangle,
  CheckCircle,
  X
} from 'lucide-react';

export interface IPAMDetailProps {
  subnet: {
    id: string;
    subnet: string;
    description: string;
    vlan_id?: number;
    utilization: number;
    total_ips: number;
    used_ips: number;
    available_ips: number;
    dhcp_enabled: boolean;
    gateway: string;
    dns_servers?: string[];
    location?: { id: string; name: string };
    subnet_type: string;
    ip_version: string;
    ip_allocations?: Array<{
      ip: string;
      status: string;
      description: string;
      device_id?: string;
    }>;
  };
  isOpen: boolean;
  onClose: () => void;
}

const StatusIcon = ({ status }: { status: string }) => {
  switch (status.toLowerCase()) {
    case 'allocated':
    case 'active':
      return <CheckCircle className="w-4 h-4 text-green-500" />;
    case 'reserved':
      return <Shield className="w-4 h-4 text-blue-500" />;
    case 'available':
    case 'free':
      return <Activity className="w-4 h-4 text-gray-400" />;
    default:
      return <AlertTriangle className="w-4 h-4 text-yellow-500" />;
  }
};

export const IPAMDetailDrawer: React.FC<IPAMDetailProps> = ({
  subnet,
  isOpen,
  onClose
}) => {
  if (!isOpen) return null;

  const utilizationColor = subnet.utilization > 80 
    ? 'bg-red-500' 
    : subnet.utilization > 60 
    ? 'bg-yellow-500' 
    : 'bg-green-500';

  return (
    <div className="fixed inset-0 z-50 overflow-hidden">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      
      {/* Drawer */}
      <div className="absolute right-0 top-0 h-full w-full max-w-3xl bg-white shadow-xl">
        <div className="flex flex-col h-full" data-testid="ipam-detail-drawer">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b">
            <div className="flex items-center gap-3">
              <Network className="w-6 h-6 text-blue-600" />
              <div>
                <h2 className="text-xl font-semibold">Subnet Details</h2>
                <p className="text-sm text-gray-600">{subnet.subnet}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6 space-y-6">
            {/* Utilization Overview */}
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-semibold">Utilization</h3>
                <span className="text-lg font-bold">{subnet.utilization.toFixed(1)}%</span>
              </div>
              
              <div className="w-full bg-gray-200 rounded-full h-4 mb-4">
                <div
                  className={`${utilizationColor} h-4 rounded-full transition-all`}
                  style={{ width: `${subnet.utilization}%` }}
                />
              </div>
              
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="text-center">
                  <div className="text-2xl font-bold text-gray-900">{subnet.total_ips.toLocaleString()}</div>
                  <div className="text-gray-600">Total IPs</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">{subnet.used_ips.toLocaleString()}</div>
                  <div className="text-gray-600">Used</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">{subnet.available_ips.toLocaleString()}</div>
                  <div className="text-gray-600">Available</div>
                </div>
              </div>
            </div>

            {/* Subnet Information */}
            <div>
              <h3 className="text-lg font-semibold mb-3">Subnet Information</h3>
              <div className="grid grid-cols-2 gap-6">
                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <Network className="w-4 h-4 text-gray-500" />
                    <div>
                      <span className="text-sm text-gray-600">CIDR</span>
                      <div className="font-medium">{subnet.subnet}</div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <Globe className="w-4 h-4 text-gray-500" />
                    <div>
                      <span className="text-sm text-gray-600">Gateway</span>
                      <div className="font-medium">{subnet.gateway}</div>
                    </div>
                  </div>

                  {subnet.vlan_id && (
                    <div className="flex items-center gap-3">
                      <Activity className="w-4 h-4 text-gray-500" />
                      <div>
                        <span className="text-sm text-gray-600">VLAN ID</span>
                        <div className="font-medium">VLAN {subnet.vlan_id}</div>
                      </div>
                    </div>
                  )}

                  <div className="flex items-center gap-3">
                    <Server className="w-4 h-4 text-gray-500" />
                    <div>
                      <span className="text-sm text-gray-600">Type</span>
                      <div className="font-medium capitalize">{subnet.subnet_type.replace('_', ' ')}</div>
                    </div>
                  </div>
                </div>

                <div className="space-y-3">
                  <div className="flex items-center gap-3">
                    <Activity className="w-4 h-4 text-gray-500" />
                    <div>
                      <span className="text-sm text-gray-600">DHCP</span>
                      <div className="flex items-center gap-2">
                        {subnet.dhcp_enabled ? (
                          <CheckCircle className="w-4 h-4 text-green-500" />
                        ) : (
                          <X className="w-4 h-4 text-red-500" />
                        )}
                        <span className="font-medium">
                          {subnet.dhcp_enabled ? 'Enabled' : 'Disabled'}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <Globe className="w-4 h-4 text-gray-500" />
                    <div>
                      <span className="text-sm text-gray-600">IP Version</span>
                      <div className="font-medium">IPv{subnet.ip_version}</div>
                    </div>
                  </div>

                  {subnet.location && (
                    <div className="flex items-center gap-3">
                      <MapPin className="w-4 h-4 text-gray-500" />
                      <div>
                        <span className="text-sm text-gray-600">Location</span>
                        <div className="font-medium">{subnet.location.name}</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* DNS Servers */}
              {subnet.dns_servers && subnet.dns_servers.length > 0 && (
                <div className="mt-4">
                  <span className="text-sm text-gray-600">DNS Servers</span>
                  <div className="flex flex-wrap gap-2 mt-1">
                    {subnet.dns_servers.map((dns, index) => (
                      <span key={index} className="px-3 py-1 bg-blue-100 text-blue-800 text-sm rounded-full">
                        {dns}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Description */}
              {subnet.description && (
                <div className="mt-4">
                  <span className="text-sm text-gray-600">Description</span>
                  <div className="font-medium mt-1">{subnet.description}</div>
                </div>
              )}
            </div>

            {/* IP Allocations */}
            {subnet.ip_allocations && subnet.ip_allocations.length > 0 && (
              <div>
                <h3 className="text-lg font-semibold mb-3">IP Allocations</h3>
                <div className="space-y-2">
                  {subnet.ip_allocations.map((allocation, index) => (
                    <div key={index} className="border rounded-lg p-3 hover:bg-gray-50 transition-colors">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <StatusIcon status={allocation.status} />
                          <div>
                            <div className="font-medium">{allocation.ip}</div>
                            <div className="text-sm text-gray-600">{allocation.description}</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-sm font-medium capitalize">{allocation.status}</div>
                          {allocation.device_id && (
                            <div className="text-xs text-gray-500">{allocation.device_id}</div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Show more allocations button if there are many */}
                {subnet.ip_allocations.length > 10 && (
                  <button className="w-full py-2 text-blue-600 hover:text-blue-800 text-sm font-medium">
                    Show all {subnet.used_ips} allocations
                  </button>
                )}
              </div>
            )}

            {/* Subnet Statistics */}
            <div>
              <h3 className="text-lg font-semibold mb-3">Statistics</h3>
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <div className="text-gray-600">Allocation Rate</div>
                    <div className="text-lg font-semibold">
                      {((subnet.used_ips / subnet.total_ips) * 100).toFixed(1)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-600">Available Capacity</div>
                    <div className="text-lg font-semibold">
                      {subnet.available_ips.toLocaleString()} IPs
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-600">Subnet Mask</div>
                    <div className="text-lg font-semibold">
                      /{subnet.subnet.split('/')[1]}
                    </div>
                  </div>
                  <div>
                    <div className="text-gray-600">Network Address</div>
                    <div className="text-lg font-semibold">
                      {subnet.subnet.split('/')[0]}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer Actions */}
          <div className="border-t px-6 py-4 bg-gray-50">
            <div className="flex justify-between">
              <div className="flex gap-2">
                <button className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors">
                  Export Allocations
                </button>
                <button className="px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors">
                  Scan Subnet
                </button>
              </div>
              <div className="flex gap-2">
                <button className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 transition-colors">
                  Reserve IP
                </button>
                <button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors">
                  Edit Subnet
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};