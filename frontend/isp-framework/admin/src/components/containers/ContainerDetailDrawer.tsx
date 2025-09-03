/**
 * Container Detail Drawer Component
 * Displays comprehensive container information including logs and metrics
 */

import React, { useState } from 'react';
import {
  Container,
  Activity,
  Cpu,
  MemoryStick,
  Network,
  Clock,
  Server,
  RefreshCw,
  AlertTriangle,
  CheckCircle,
  Play,
  Square,
  RotateCcw,
  X,
} from 'lucide-react';
import { formatBytes, formatDistance } from '@dotmac/utils';

export interface ContainerDetailProps {
  container: {
    id: string;
    name: string;
    image: string;
    status: string;
    uptime: number;
    cpu_usage: number;
    memory_usage: number;
    memory_limit: number;
    network_io: { rx: number; tx: number };
    restart_count: number;
    health_status: string;
    node: string;
    service_name: string;
    environment?: Record<string, string>;
    volumes?: Array<{
      source: string;
      destination: string;
      mode: string;
    }>;
    ports?: Array<{
      host_port: number;
      container_port: number;
      protocol: string;
    }>;
    logs?: Array<{
      timestamp: string;
      level: string;
      message: string;
    }>;
  };
  isOpen: boolean;
  onClose: () => void;
}

const StatusIcon = ({ status }: { status: string }) => {
  switch (status.toLowerCase()) {
    case 'running':
      return <CheckCircle className='w-4 h-4 text-green-500' />;
    case 'restarting':
      return <RefreshCw className='w-4 h-4 text-yellow-500 animate-spin' />;
    case 'stopped':
    case 'dead':
      return <Square className='w-4 h-4 text-red-500' />;
    case 'paused':
      return <Play className='w-4 h-4 text-blue-500' />;
    default:
      return <AlertTriangle className='w-4 h-4 text-gray-500' />;
  }
};

const HealthIcon = ({ health }: { health: string }) => {
  switch (health.toLowerCase()) {
    case 'healthy':
      return <CheckCircle className='w-4 h-4 text-green-500' />;
    case 'unhealthy':
      return <AlertTriangle className='w-4 h-4 text-red-500' />;
    case 'starting':
      return <RefreshCw className='w-4 h-4 text-blue-500 animate-spin' />;
    default:
      return <AlertTriangle className='w-4 h-4 text-gray-500' />;
  }
};

export const ContainerDetailDrawer: React.FC<ContainerDetailProps> = ({
  container,
  isOpen,
  onClose,
}) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'logs' | 'environment' | 'network'>(
    'overview'
  );

  if (!isOpen) return null;

  const memoryUsagePercent = (container.memory_usage / 100) * 100; // Assuming memory_usage is already percentage

  return (
    <div className='fixed inset-0 z-50 overflow-hidden'>
      {/* Backdrop */}
      <div className='absolute inset-0 bg-black/50' onClick={onClose} />

      {/* Drawer */}
      <div className='absolute right-0 top-0 h-full w-full max-w-4xl bg-white shadow-xl'>
        <div className='flex flex-col h-full' data-testid='container-detail-drawer'>
          {/* Header */}
          <div className='flex items-center justify-between px-6 py-4 border-b'>
            <div className='flex items-center gap-3'>
              <Container className='w-6 h-6 text-blue-600' />
              <div>
                <h2 className='text-xl font-semibold'>Container Details</h2>
                <p className='text-sm text-gray-600'>{container.name}</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className='p-2 hover:bg-gray-100 rounded-full transition-colors'
            >
              <X className='w-5 h-5' />
            </button>
          </div>

          {/* Tabs */}
          <div className='border-b'>
            <nav className='flex px-6'>
              <button
                onClick={() => setActiveTab('overview')}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'overview'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => setActiveTab('logs')}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'logs'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
                data-testid='logs-tab'
              >
                Logs
              </button>
              <button
                onClick={() => setActiveTab('environment')}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'environment'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Environment
              </button>
              <button
                onClick={() => setActiveTab('network')}
                className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === 'network'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Network
              </button>
            </nav>
          </div>

          {/* Tab Content */}
          <div className='flex-1 overflow-y-auto p-6'>
            {activeTab === 'overview' && (
              <div className='space-y-6'>
                {/* Status Overview */}
                <div className='bg-gray-50 rounded-lg p-4'>
                  <div className='flex items-center justify-between mb-4'>
                    <div className='flex items-center gap-3'>
                      <StatusIcon status={container.status} />
                      <span className='font-medium capitalize'>{container.status}</span>
                      <div className='flex items-center gap-2'>
                        <HealthIcon health={container.health_status} />
                        <span className='text-sm capitalize'>{container.health_status}</span>
                      </div>
                    </div>
                    <div className='text-right'>
                      <div className='text-sm text-gray-600'>Uptime</div>
                      <div className='font-medium' data-testid='uptime'>
                        {formatDistance(container.uptime * 1000)}
                      </div>
                    </div>
                  </div>

                  <div className='grid grid-cols-3 gap-4 text-sm'>
                    <div>
                      <span className='text-gray-600'>Restarts</span>
                      <div className='font-medium'>{container.restart_count}</div>
                    </div>
                    <div>
                      <span className='text-gray-600'>Service</span>
                      <div className='font-medium'>{container.service_name}</div>
                    </div>
                    <div>
                      <span className='text-gray-600'>Node</span>
                      <div className='font-medium'>{container.node}</div>
                    </div>
                  </div>
                </div>

                {/* Container Information */}
                <div>
                  <h3 className='text-lg font-semibold mb-3'>Container Information</h3>
                  <div className='space-y-3'>
                    <div className='flex items-center gap-3'>
                      <Container className='w-4 h-4 text-gray-500' />
                      <div>
                        <span className='text-sm text-gray-600'>Container Name</span>
                        <div className='font-medium'>{container.name}</div>
                      </div>
                    </div>

                    <div className='flex items-center gap-3'>
                      <Server className='w-4 h-4 text-gray-500' />
                      <div>
                        <span className='text-sm text-gray-600'>Image</span>
                        <div className='font-medium'>{container.image}</div>
                      </div>
                    </div>

                    <div className='flex items-center gap-3'>
                      <Activity className='w-4 h-4 text-gray-500' />
                      <div>
                        <span className='text-sm text-gray-600'>Service Name</span>
                        <div className='font-medium'>{container.service_name}</div>
                      </div>
                    </div>

                    <div className='flex items-center gap-3'>
                      <Server className='w-4 h-4 text-gray-500' />
                      <div>
                        <span className='text-sm text-gray-600'>Node</span>
                        <div className='font-medium'>{container.node}</div>
                      </div>
                    </div>
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
                        <span className='text-sm font-medium'>
                          {container.cpu_usage.toFixed(1)}%
                        </span>
                      </div>
                      <div className='w-full bg-gray-200 rounded-full h-2'>
                        <div
                          className='bg-blue-500 h-2 rounded-full transition-all'
                          style={{ width: `${Math.min(container.cpu_usage, 100)}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className='flex items-center justify-between mb-2'>
                        <div className='flex items-center gap-2'>
                          <MemoryStick className='w-4 h-4 text-purple-500' />
                          <span className='text-sm font-medium'>Memory Usage</span>
                        </div>
                        <div className='text-right text-sm'>
                          <div className='font-medium'>{container.memory_usage.toFixed(1)}%</div>
                          <div className='text-gray-600'>{formatBytes(container.memory_limit)}</div>
                        </div>
                      </div>
                      <div className='w-full bg-gray-200 rounded-full h-2'>
                        <div
                          className='bg-purple-500 h-2 rounded-full transition-all'
                          style={{ width: `${Math.min(container.memory_usage, 100)}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className='flex items-center justify-between mb-2'>
                        <div className='flex items-center gap-2'>
                          <Network className='w-4 h-4 text-green-500' />
                          <span className='text-sm font-medium'>Network I/O</span>
                        </div>
                        <div className='text-right text-sm'>
                          <div className='font-medium'>
                            ↓ {formatBytes(container.network_io.rx)} / ↑{' '}
                            {formatBytes(container.network_io.tx)}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Port Mappings */}
                {container.ports && container.ports.length > 0 && (
                  <div>
                    <h3 className='text-lg font-semibold mb-3'>Port Mappings</h3>
                    <div className='space-y-2'>
                      {container.ports.map((port, index) => (
                        <div
                          key={index}
                          className='flex items-center justify-between p-3 bg-gray-50 rounded-lg'
                        >
                          <div className='font-medium'>
                            {port.host_port}:{port.container_port}
                          </div>
                          <div className='text-sm text-gray-600 uppercase'>{port.protocol}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Volumes */}
                {container.volumes && container.volumes.length > 0 && (
                  <div>
                    <h3 className='text-lg font-semibold mb-3'>Volume Mounts</h3>
                    <div className='space-y-2'>
                      {container.volumes.map((volume, index) => (
                        <div key={index} className='p-3 bg-gray-50 rounded-lg'>
                          <div className='flex items-center justify-between mb-1'>
                            <div className='font-medium'>{volume.source}</div>
                            <div className='text-sm text-gray-600 uppercase'>{volume.mode}</div>
                          </div>
                          <div className='text-sm text-gray-600'>→ {volume.destination}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'logs' && (
              <div className='space-y-4' data-testid='container-logs'>
                <div className='flex items-center justify-between'>
                  <h3 className='text-lg font-semibold'>Container Logs</h3>
                  <div className='flex gap-2'>
                    <button className='px-3 py-1 text-sm bg-gray-100 rounded hover:bg-gray-200 transition-colors'>
                      Refresh
                    </button>
                    <button className='px-3 py-1 text-sm bg-blue-100 text-blue-800 rounded hover:bg-blue-200 transition-colors'>
                      Download
                    </button>
                  </div>
                </div>

                <div className='bg-gray-900 rounded-lg p-4 font-mono text-sm max-h-96 overflow-y-auto'>
                  {container.logs && container.logs.length > 0 ? (
                    <div className='space-y-1'>
                      {container.logs.map((log, index) => (
                        <div key={index} className='flex gap-2'>
                          <span className='text-gray-400 shrink-0'>
                            {new Date(log.timestamp).toLocaleTimeString()}
                          </span>
                          <span
                            className={`shrink-0 uppercase text-xs px-1 rounded ${
                              log.level === 'error'
                                ? 'bg-red-500 text-white'
                                : log.level === 'warn'
                                  ? 'bg-yellow-500 text-white'
                                  : log.level === 'info'
                                    ? 'bg-blue-500 text-white'
                                    : 'bg-gray-500 text-white'
                            }`}
                          >
                            {log.level}
                          </span>
                          <span className='text-gray-300'>{log.message}</span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className='text-gray-400 text-center py-8'>No logs available</div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'environment' && (
              <div className='space-y-4'>
                <h3 className='text-lg font-semibold'>Environment Variables</h3>

                {container.environment && Object.keys(container.environment).length > 0 ? (
                  <div className='space-y-2'>
                    {Object.entries(container.environment).map(([key, value]) => (
                      <div
                        key={key}
                        className='flex items-center justify-between p-3 bg-gray-50 rounded-lg'
                      >
                        <div className='font-medium font-mono text-sm'>{key}</div>
                        <div className='text-sm text-gray-600 font-mono max-w-xs truncate'>
                          {value}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className='text-gray-500 text-center py-8'>
                    No environment variables configured
                  </div>
                )}
              </div>
            )}

            {activeTab === 'network' && (
              <div className='space-y-6'>
                <h3 className='text-lg font-semibold'>Network Configuration</h3>

                <div>
                  <h4 className='font-medium mb-3'>Network Statistics</h4>
                  <div className='grid grid-cols-2 gap-4'>
                    <div className='p-4 bg-green-50 rounded-lg'>
                      <div className='text-sm text-green-600 mb-1'>Bytes Received</div>
                      <div className='text-xl font-bold text-green-800'>
                        {formatBytes(container.network_io.rx)}
                      </div>
                    </div>
                    <div className='p-4 bg-blue-50 rounded-lg'>
                      <div className='text-sm text-blue-600 mb-1'>Bytes Transmitted</div>
                      <div className='text-xl font-bold text-blue-800'>
                        {formatBytes(container.network_io.tx)}
                      </div>
                    </div>
                  </div>
                </div>

                {container.ports && container.ports.length > 0 && (
                  <div>
                    <h4 className='font-medium mb-3'>Exposed Ports</h4>
                    <div className='space-y-2'>
                      {container.ports.map((port, index) => (
                        <div
                          key={index}
                          className='flex items-center justify-between p-3 border rounded-lg'
                        >
                          <div>
                            <div className='font-medium'>Port {port.container_port}</div>
                            <div className='text-sm text-gray-600'>Container port</div>
                          </div>
                          <div className='text-center'>
                            <div className='text-sm text-gray-400'>→</div>
                          </div>
                          <div className='text-right'>
                            <div className='font-medium'>Port {port.host_port}</div>
                            <div className='text-sm text-gray-600'>
                              Host port ({port.protocol.toUpperCase()})
                            </div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Footer Actions */}
          <div className='border-t px-6 py-4 bg-gray-50'>
            <div className='flex justify-between'>
              <div className='flex gap-2'>
                <button className='px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors flex items-center gap-2'>
                  <RefreshCw className='w-4 h-4' />
                  Refresh Data
                </button>
                <button className='px-4 py-2 text-gray-600 hover:text-gray-800 transition-colors'>
                  Export Logs
                </button>
              </div>
              <div className='flex gap-2'>
                <button className='px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600 transition-colors flex items-center gap-2'>
                  <RotateCcw className='w-4 h-4' />
                  Restart Container
                </button>
                <button className='px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors flex items-center gap-2'>
                  <Square className='w-4 h-4' />
                  Stop Container
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
