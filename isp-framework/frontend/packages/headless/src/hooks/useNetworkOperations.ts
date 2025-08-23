/**
 * Network Operations Hook
 * Complete network infrastructure management for ISP operations
 */

import { useCallback, useState, useEffect } from 'react';
import { getApiClient } from '../api/client';
import { useAuthStore } from '../stores/authStore';
import { useTenantStore } from '../stores/tenantStore';
import { useStandardErrorHandler } from './useStandardErrorHandler';
import { useRealTimeSync } from './useRealTimeSync';

// Network device types
export interface NetworkDevice {
  id: string;
  name: string;
  type: 'router' | 'switch' | 'modem' | 'access_point' | 'olt' | 'onu' | 'firewall' | 'load_balancer';
  vendor: string;
  model: string;
  firmwareVersion: string;
  serialNumber: string;
  
  // Network configuration
  ipAddress: string;
  macAddress?: string;
  subnetMask?: string;
  gateway?: string;
  vlan?: number;
  
  // Physical location
  location: {
    site: string;
    building?: string;
    floor?: string;
    rack?: string;
    position?: string;
    latitude?: number;
    longitude?: number;
  };
  
  // Status and monitoring
  status: 'online' | 'offline' | 'warning' | 'critical' | 'maintenance';
  lastSeen: string;
  uptime: number; // seconds
  
  // Performance metrics
  metrics: {
    cpuUsage: number; // percentage
    memoryUsage: number; // percentage
    temperature?: number; // celsius
    powerLevel?: number; // dBm for optical devices
    rxPower?: number; // dBm
    txPower?: number; // dBm
    bandwidthUtilization: number; // percentage
    packetLoss: number; // percentage
    latency: number; // milliseconds
    errorRate: number; // percentage
  };
  
  // Port information
  ports: Array<{
    id: string;
    name: string;
    type: 'ethernet' | 'fiber' | 'coax' | 'wireless';
    speed: string; // e.g., "1Gbps", "10Gbps"
    status: 'up' | 'down' | 'disabled' | 'error';
    utilization: number; // percentage
    connectedDevice?: string;
    vlan?: number;
    errors: number;
    collisions: number;
  }>;
  
  // Configuration
  configuration: {
    snmpCommunity?: string;
    managementProtocol: 'snmp' | 'ssh' | 'telnet' | 'http' | 'https';
    monitoringEnabled: boolean;
    alertsEnabled: boolean;
    backupSchedule?: string;
  };
  
  // Metadata
  createdAt: string;
  updatedAt: string;
  tags: string[];
  notes?: string;
}

// Network topology
export interface NetworkTopology {
  nodes: Array<{
    id: string;
    deviceId: string;
    name: string;
    type: NetworkDevice['type'];
    status: NetworkDevice['status'];
    position: { x: number; y: number };
    metadata: Record<string, any>;
  }>;
  
  links: Array<{
    id: string;
    source: string; // node id
    target: string; // node id
    type: 'ethernet' | 'fiber' | 'wireless' | 'virtual';
    bandwidth: string;
    status: 'active' | 'inactive' | 'error';
    utilization: number;
    metadata: Record<string, any>;
  }>;
  
  subnets: Array<{
    id: string;
    network: string; // CIDR notation
    name: string;
    vlan?: number;
    devices: string[]; // device ids
    gateway: string;
  }>;
}

// Network incidents and maintenance
export interface NetworkIncident {
  id: string;
  title: string;
  description: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  category: 'outage' | 'performance' | 'security' | 'maintenance' | 'hardware';
  status: 'open' | 'investigating' | 'identified' | 'monitoring' | 'resolved' | 'closed';
  
  // Affected infrastructure
  affectedDevices: string[];
  affectedServices: string[];
  affectedCustomers: number;
  affectedAreas: string[];
  
  // Timeline
  startTime: string;
  detectedTime: string;
  acknowledgedTime?: string;
  resolvedTime?: string;
  estimatedResolution?: string;
  
  // Impact assessment
  impact: {
    customersAffected: number;
    revenueImpact?: number;
    slaBreaches: number;
  };
  
  // Communication
  updates: Array<{
    id: string;
    timestamp: string;
    message: string;
    author: string;
    isPublic: boolean;
  }>;
  
  // Resolution
  rootCause?: string;
  resolution?: string;
  preventiveMeasures?: string[];
  
  // Metadata
  createdBy: string;
  assignedTo?: string;
  tags: string[];
}

// Network configuration templates
export interface ConfigurationTemplate {
  id: string;
  name: string;
  description: string;
  deviceType: NetworkDevice['type'];
  vendor?: string;
  model?: string;
  
  template: {
    snmp?: {
      community: string;
      version: '2c' | '3';
      port: number;
    };
    interfaces?: Array<{
      name: string;
      type: string;
      configuration: Record<string, any>;
    }>;
    routing?: {
      protocol: 'static' | 'ospf' | 'bgp';
      configuration: Record<string, any>;
    };
    security?: {
      accessLists: Array<Record<string, any>>;
      firewallRules: Array<Record<string, any>>;
    };
    qos?: {
      policies: Array<Record<string, any>>;
    };
  };
  
  variables: Array<{
    name: string;
    type: 'string' | 'number' | 'boolean' | 'select';
    required: boolean;
    defaultValue?: any;
    options?: any[];
    description: string;
  }>;
  
  createdAt: string;
  updatedAt: string;
  version: string;
}

export function useNetworkOperations() {
  const { user } = useAuthStore();
  const { currentTenant } = useTenantStore();
  const { handleError, withErrorHandling } = useStandardErrorHandler({
    context: 'Network Operations',
    enableRetry: true,
    maxRetries: 3
  });
  const { emit, subscribe } = useRealTimeSync();

  const [devices, setDevices] = useState<NetworkDevice[]>([]);
  const [topology, setTopology] = useState<NetworkTopology | null>(null);
  const [incidents, setIncidents] = useState<NetworkIncident[]>([]);
  const [configTemplates, setConfigTemplates] = useState<ConfigurationTemplate[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedDevice, setSelectedDevice] = useState<NetworkDevice | null>(null);

  // Load network devices with filtering
  const loadDevices = useCallback(async (filters: {
    type?: NetworkDevice['type'][];
    status?: NetworkDevice['status'][];
    location?: string;
    tags?: string[];
  } = {}): Promise<void> => {
    if (!currentTenant?.tenant?.id) return;

    return withErrorHandling(async () => {
      setIsLoading(true);
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/network/devices', {
        params: {
          tenantId: currentTenant.tenant.id,
          ...filters
        }
      });

      setDevices(response.data.devices || []);
    });
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  // Discover network devices via SNMP
  const discoverDevices = useCallback(async (
    networkRange: string, // CIDR notation
    credentials: {
      snmpCommunity?: string;
      snmpVersion?: '2c' | '3';
      sshUsername?: string;
      sshPassword?: string;
    }
  ): Promise<{ discovered: number; failed: number }> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/network/discovery', {
        method: 'POST',
        body: {
          networkRange,
          credentials,
          tenantId: currentTenant?.tenant?.id,
          discoveredBy: user?.id
        }
      });

      const { discovered, failed, devices: newDevices } = response.data;
      
      // Add discovered devices to state
      if (newDevices && newDevices.length > 0) {
        setDevices(prev => [...prev, ...newDevices]);
        emit('network:devices_discovered', { count: discovered, devices: newDevices });
      }

      return { discovered, failed };
    }) || { discovered: 0, failed: 0 };
  }, [currentTenant?.tenant?.id, user?.id, withErrorHandling, emit]);

  // Add device manually
  const addDevice = useCallback(async (deviceData: Omit<NetworkDevice, 'id' | 'createdAt' | 'updatedAt'>): Promise<string | null> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/network/devices', {
        method: 'POST',
        body: {
          ...deviceData,
          tenantId: currentTenant?.tenant?.id,
          createdBy: user?.id
        }
      });

      const newDevice = response.data.device;
      setDevices(prev => [...prev, newDevice]);
      
      emit('network:device_added', { deviceId: newDevice.id });
      return newDevice.id;
    });
  }, [currentTenant?.tenant?.id, user?.id, withErrorHandling, emit]);

  // Update device configuration
  const updateDevice = useCallback(async (
    deviceId: string,
    updates: Partial<NetworkDevice>
  ): Promise<boolean> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      await apiClient.request(`/api/v1/network/devices/${deviceId}`, {
        method: 'PUT',
        body: {
          ...updates,
          updatedBy: user?.id
        }
      });

      setDevices(prev => prev.map(device =>
        device.id === deviceId
          ? { ...device, ...updates, updatedAt: new Date().toISOString() }
          : device
      ));

      if (selectedDevice?.id === deviceId) {
        setSelectedDevice(prev => prev ? { ...prev, ...updates } : null);
      }

      emit('network:device_updated', { deviceId, updates });
      return true;
    }) || false;
  }, [user?.id, selectedDevice?.id, withErrorHandling, emit]);

  // Execute device command (SSH/SNMP)
  const executeDeviceCommand = useCallback(async (
    deviceId: string,
    command: string,
    protocol: 'ssh' | 'snmp' = 'ssh'
  ): Promise<{ output: string; success: boolean; error?: string }> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request(`/api/v1/network/devices/${deviceId}/execute`, {
        method: 'POST',
        body: {
          command,
          protocol,
          executedBy: user?.id
        }
      });

      const result = response.data;
      
      // Log command execution
      emit('network:command_executed', { deviceId, command, protocol, success: result.success });
      
      return result;
    }) || { output: '', success: false, error: 'Command execution failed' };
  }, [user?.id, withErrorHandling, emit]);

  // Load network topology
  const loadTopology = useCallback(async (): Promise<void> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/network/topology', {
        params: {
          tenantId: currentTenant?.tenant?.id
        }
      });

      setTopology(response.data.topology);
    });
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  // Generate network topology automatically
  const generateTopology = useCallback(async (): Promise<boolean> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/network/topology/generate', {
        method: 'POST',
        body: {
          tenantId: currentTenant?.tenant?.id,
          generatedBy: user?.id
        }
      });

      setTopology(response.data.topology);
      emit('network:topology_generated', { nodeCount: response.data.topology.nodes.length });
      
      return true;
    }) || false;
  }, [currentTenant?.tenant?.id, user?.id, withErrorHandling, emit]);

  // Load network incidents
  const loadIncidents = useCallback(async (filters: {
    status?: NetworkIncident['status'][];
    severity?: NetworkIncident['severity'][];
    category?: NetworkIncident['category'][];
    assignedTo?: string;
    dateFrom?: string;
    dateTo?: string;
  } = {}): Promise<void> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/network/incidents', {
        params: {
          tenantId: currentTenant?.tenant?.id,
          ...filters
        }
      });

      setIncidents(response.data.incidents || []);
    });
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  // Create network incident
  const createIncident = useCallback(async (incidentData: {
    title: string;
    description: string;
    severity: NetworkIncident['severity'];
    category: NetworkIncident['category'];
    affectedDevices?: string[];
    estimatedResolution?: string;
  }): Promise<string | null> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/network/incidents', {
        method: 'POST',
        body: {
          ...incidentData,
          tenantId: currentTenant?.tenant?.id,
          createdBy: user?.id,
          startTime: new Date().toISOString(),
          detectedTime: new Date().toISOString()
        }
      });

      const newIncident = response.data.incident;
      setIncidents(prev => [newIncident, ...prev]);
      
      emit('network:incident_created', { incidentId: newIncident.id, severity: newIncident.severity });
      return newIncident.id;
    });
  }, [currentTenant?.tenant?.id, user?.id, withErrorHandling, emit]);

  // Update incident status
  const updateIncidentStatus = useCallback(async (
    incidentId: string,
    status: NetworkIncident['status'],
    update?: string
  ): Promise<boolean> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      await apiClient.request(`/api/v1/network/incidents/${incidentId}/status`, {
        method: 'PUT',
        body: {
          status,
          update: update ? {
            message: update,
            author: user?.name || user?.email || 'Unknown',
            isPublic: true
          } : undefined,
          updatedBy: user?.id
        }
      });

      setIncidents(prev => prev.map(incident => {
        if (incident.id === incidentId) {
          const updatedIncident = {
            ...incident,
            status,
            ...(status === 'resolved' && { resolvedTime: new Date().toISOString() })
          };
          
          if (update) {
            updatedIncident.updates = [
              ...incident.updates,
              {
                id: Date.now().toString(),
                timestamp: new Date().toISOString(),
                message: update,
                author: user?.name || user?.email || 'Unknown',
                isPublic: true
              }
            ];
          }
          
          return updatedIncident;
        }
        return incident;
      }));

      emit('network:incident_updated', { incidentId, status });
      return true;
    }) || false;
  }, [user?.id, user?.name, user?.email, withErrorHandling, emit]);

  // Load configuration templates
  const loadConfigTemplates = useCallback(async (): Promise<void> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request('/api/v1/network/config-templates', {
        params: {
          tenantId: currentTenant?.tenant?.id
        }
      });

      setConfigTemplates(response.data.templates || []);
    });
  }, [currentTenant?.tenant?.id, withErrorHandling]);

  // Apply configuration template to device
  const applyConfigTemplate = useCallback(async (
    deviceId: string,
    templateId: string,
    variables: Record<string, any>
  ): Promise<boolean> => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      await apiClient.request(`/api/v1/network/devices/${deviceId}/apply-config`, {
        method: 'POST',
        body: {
          templateId,
          variables,
          appliedBy: user?.id
        }
      });

      emit('network:config_applied', { deviceId, templateId });
      return true;
    }) || false;
  }, [user?.id, withErrorHandling, emit]);

  // Get device performance metrics
  const getDeviceMetrics = useCallback(async (
    deviceId: string,
    timeRange: { start: string; end: string },
    metrics: string[] = ['cpu', 'memory', 'bandwidth']
  ) => {
    return withErrorHandling(async () => {
      const apiClient = getApiClient();
      
      const response = await apiClient.request(`/api/v1/network/devices/${deviceId}/metrics`, {
        params: {
          startTime: timeRange.start,
          endTime: timeRange.end,
          metrics: metrics.join(',')
        }
      });

      return response.data.metrics;
    });
  }, [withErrorHandling]);

  // Real-time network updates
  useEffect(() => {
    return subscribe('network:*', (event) => {
      switch (event.type) {
        case 'network:device:status':
          if (event.data && typeof event.data === 'object') {
            const { deviceId, status, metrics } = event.data as any;
            setDevices(prev => prev.map(device =>
              device.id === deviceId
                ? { ...device, status, metrics: { ...device.metrics, ...metrics }, lastSeen: new Date().toISOString() }
                : device
            ));
          }
          break;
        case 'network:device:metrics':
          if (event.data && typeof event.data === 'object') {
            const { deviceId, metrics } = event.data as any;
            setDevices(prev => prev.map(device =>
              device.id === deviceId
                ? { ...device, metrics: { ...device.metrics, ...metrics } }
                : device
            ));
          }
          break;
        case 'network:incident:created':
          if (event.data && typeof event.data === 'object') {
            loadIncidents();
          }
          break;
      }
    });
  }, [subscribe, loadIncidents]);

  // Load initial data
  useEffect(() => {
    if (currentTenant?.tenant?.id) {
      loadDevices();
      loadTopology();
      loadIncidents();
      loadConfigTemplates();
    }
  }, [currentTenant?.tenant?.id, loadDevices, loadTopology, loadIncidents, loadConfigTemplates]);

  return {
    // State
    devices,
    topology,
    incidents,
    configTemplates,
    isLoading,
    selectedDevice,

    // Device operations
    loadDevices,
    discoverDevices,
    addDevice,
    updateDevice,
    executeDeviceCommand,
    getDeviceMetrics,
    setSelectedDevice,

    // Topology operations
    loadTopology,
    generateTopology,

    // Incident management
    loadIncidents,
    createIncident,
    updateIncidentStatus,

    // Configuration management
    loadConfigTemplates,
    applyConfigTemplate,

    // Computed values
    onlineDevices: devices.filter(d => d.status === 'online'),
    offlineDevices: devices.filter(d => d.status === 'offline'),
    criticalDevices: devices.filter(d => d.status === 'critical'),
    warningDevices: devices.filter(d => d.status === 'warning'),
    
    openIncidents: incidents.filter(i => ['open', 'investigating', 'identified'].includes(i.status)),
    criticalIncidents: incidents.filter(i => i.severity === 'critical' && i.status !== 'resolved'),
    
    networkHealth: {
      totalDevices: devices.length,
      onlinePercentage: devices.length > 0 ? (devices.filter(d => d.status === 'online').length / devices.length) * 100 : 0,
      criticalIssues: incidents.filter(i => i.severity === 'critical' && i.status !== 'resolved').length,
      avgLatency: devices.length > 0 ? devices.reduce((sum, d) => sum + d.metrics.latency, 0) / devices.length : 0
    }
  };
}

export type { NetworkDevice, NetworkTopology, NetworkIncident, ConfigurationTemplate };