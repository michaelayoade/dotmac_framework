/**
 * Network API mocks for testing
 * Provides mock data and API responses for network topology, geographic data, and monitoring
 */

import type {
  NetworkNode,
  NetworkLink,
  ServiceArea,
  CoverageGap,
  PerformanceMetric,
  NetworkAlert,
  TopologyMetrics,
  CriticalNode,
  PathAnalysis,
  NodeType,
  NodeStatus,
  LinkType
} from '../../types';

// Mock network topology data
export const mockNetworkNodes: NetworkNode[] = [
  {
    node_id: "core-01",
    node_type: NodeType.CORE_ROUTER,
    device_id: "device-001",
    site_id: "site-downtown",
    latitude: 40.7128,
    longitude: -74.0060,
    elevation: 50,
    ip_address: "192.168.1.1",
    mac_address: "00:1B:44:11:3A:B7",
    hostname: "core-router-01.dotmac.local",
    manufacturer: "Cisco",
    model: "ASR 9000",
    firmware_version: "7.5.2",
    bandwidth_mbps: 10000,
    port_count: 48,
    status: NodeStatus.ACTIVE,
    last_seen_at: new Date(Date.now() - 5000).toISOString(),
    uptime_percentage: 99.8,
    cpu_usage: 45,
    memory_usage: 67,
    temperature: 42,
    power_consumption: 850,
    connected_links: ["link-01", "link-02", "link-03"],
    neighbor_count: 3
  },
  {
    node_id: "dist-01",
    node_type: NodeType.DISTRIBUTION_SWITCH,
    device_id: "device-002",
    site_id: "site-midtown",
    latitude: 40.7589,
    longitude: -73.9851,
    elevation: 45,
    ip_address: "192.168.2.1",
    mac_address: "00:1B:44:11:3A:B8",
    hostname: "dist-switch-01.dotmac.local",
    manufacturer: "Juniper",
    model: "EX4650",
    firmware_version: "20.4R3",
    bandwidth_mbps: 1000,
    port_count: 24,
    status: NodeStatus.ACTIVE,
    last_seen_at: new Date(Date.now() - 2000).toISOString(),
    uptime_percentage: 98.5,
    cpu_usage: 23,
    memory_usage: 34,
    temperature: 38,
    power_consumption: 120,
    connected_links: ["link-01", "link-04"],
    neighbor_count: 2
  },
  {
    node_id: "access-01",
    node_type: NodeType.ACCESS_SWITCH,
    device_id: "device-003",
    site_id: "site-residential-a",
    latitude: 40.7505,
    longitude: -73.9934,
    elevation: 35,
    ip_address: "192.168.3.1",
    mac_address: "00:1B:44:11:3A:B9",
    hostname: "access-switch-01.dotmac.local",
    manufacturer: "Cisco",
    model: "Catalyst 2960",
    firmware_version: "15.2(7)E",
    bandwidth_mbps: 100,
    port_count: 48,
    status: NodeStatus.MAINTENANCE,
    last_seen_at: new Date(Date.now() - 30000).toISOString(),
    uptime_percentage: 95.2,
    cpu_usage: 78,
    memory_usage: 89,
    temperature: 55,
    power_consumption: 85,
    connected_links: ["link-04"],
    neighbor_count: 1
  },
  {
    node_id: "wifi-ap-01",
    node_type: NodeType.WIFI_ACCESS_POINT,
    device_id: "device-004",
    site_id: "site-residential-a",
    latitude: 40.7506,
    longitude: -73.9935,
    elevation: 12,
    ip_address: "192.168.4.1",
    mac_address: "00:1B:44:11:3A:BA",
    hostname: "wifi-ap-01.dotmac.local",
    manufacturer: "Ubiquiti",
    model: "UniFi AP AC Pro",
    firmware_version: "4.3.28",
    bandwidth_mbps: 867,
    coverage_radius_km: 0.1,
    status: NodeStatus.ACTIVE,
    last_seen_at: new Date(Date.now() - 1000).toISOString(),
    uptime_percentage: 97.8,
    cpu_usage: 12,
    memory_usage: 45,
    temperature: 32,
    power_consumption: 8.5,
    connected_links: [],
    neighbor_count: 0
  }
];

export const mockNetworkLinks: NetworkLink[] = [
  {
    link_id: "link-01",
    source_node_id: "core-01",
    target_node_id: "dist-01",
    link_type: LinkType.FIBER,
    source_port: "GigabitEthernet0/0/1",
    target_port: "xe-0/0/0",
    bandwidth_mbps: 1000,
    latency_ms: 2.5,
    length_km: 15.2,
    cost: 10,
    utilization_percentage: 45,
    packet_loss: 0.01,
    error_rate: 0.0001,
    status: NodeStatus.ACTIVE,
    operational_status: "up/up"
  },
  {
    link_id: "link-02",
    source_node_id: "core-01",
    target_node_id: "core-02",
    link_type: LinkType.FIBER,
    source_port: "GigabitEthernet0/0/2",
    target_port: "GigabitEthernet0/0/1",
    bandwidth_mbps: 10000,
    latency_ms: 1.2,
    length_km: 8.7,
    cost: 5,
    utilization_percentage: 23,
    packet_loss: 0.005,
    error_rate: 0.00005,
    status: NodeStatus.ACTIVE,
    operational_status: "up/up"
  },
  {
    link_id: "link-04",
    source_node_id: "dist-01",
    target_node_id: "access-01",
    link_type: LinkType.ETHERNET,
    source_port: "xe-0/0/12",
    target_port: "GigabitEthernet0/1",
    bandwidth_mbps: 100,
    latency_ms: 5.8,
    length_km: 2.1,
    cost: 20,
    utilization_percentage: 67,
    packet_loss: 0.02,
    error_rate: 0.0003,
    status: NodeStatus.ACTIVE,
    operational_status: "up/up"
  }
];

export const mockServiceAreas: ServiceArea[] = [
  {
    id: "area-downtown",
    tenant_id: "tenant-001",
    name: "Downtown Business District",
    polygon_coordinates: {
      type: "Polygon",
      coordinates: [[
        [-74.015, 40.705], [-74.005, 40.705], [-74.005, 40.715], [-74.015, 40.715], [-74.015, 40.705]
      ]]
    },
    population: 25000,
    households: 8500,
    businesses: 1200,
    coverage_percentage: 95,
    service_types: ["fiber", "wireless", "business"],
    created_at: "2024-01-15T10:30:00Z",
    updated_at: "2024-08-20T14:22:00Z"
  },
  {
    id: "area-residential-north",
    tenant_id: "tenant-001",
    name: "North Residential Zone",
    polygon_coordinates: {
      type: "Polygon",
      coordinates: [[
        [-73.995, 40.750], [-73.985, 40.750], [-73.985, 40.765], [-73.995, 40.765], [-73.995, 40.750]
      ]]
    },
    population: 45000,
    households: 18000,
    businesses: 150,
    coverage_percentage: 78,
    service_types: ["fiber", "wireless"],
    created_at: "2024-02-01T09:15:00Z",
    updated_at: "2024-08-18T11:45:00Z"
  }
];

export const mockCoverageGaps: CoverageGap[] = [
  {
    id: "gap-rural-001",
    tenant_id: "tenant-001",
    polygon_coordinates: {
      type: "Polygon",
      coordinates: [[
        [-74.025, 40.695], [-74.015, 40.695], [-74.015, 40.700], [-74.025, 40.700], [-74.025, 40.695]
      ]]
    },
    gap_type: "rural_underserved",
    severity: "high",
    affected_customers: 850,
    potential_revenue: 420000,
    buildout_cost: 750000,
    priority_score: 78,
    recommendations: [
      "Deploy fiber infrastructure along Highway 23",
      "Partner with local utility company for pole access",
      "Consider wireless backhaul for immediate coverage"
    ],
    status: "analysis_complete",
    created_at: "2024-06-15T16:20:00Z"
  },
  {
    id: "gap-dead-zone-002",
    tenant_id: "tenant-001",
    polygon_coordinates: {
      type: "Polygon",
      coordinates: [[
        [-73.988, 40.742], [-73.983, 40.742], [-73.983, 40.745], [-73.988, 40.745], [-73.988, 40.742]
      ]]
    },
    gap_type: "signal_dead_zone",
    severity: "critical",
    affected_customers: 1200,
    potential_revenue: 680000,
    buildout_cost: 125000,
    priority_score: 92,
    recommendations: [
      "Install additional wireless access point",
      "Optimize antenna positioning on existing towers"
    ],
    status: "pending_approval",
    created_at: "2024-07-22T13:10:00Z"
  }
];

export const mockPerformanceMetrics: PerformanceMetric[] = [
  {
    timestamp: new Date(Date.now() - 300000).toISOString(),
    metric_name: "cpu_usage",
    entity_id: "core-01",
    entity_type: "node",
    value: 45,
    unit: "percentage"
  },
  {
    timestamp: new Date(Date.now() - 240000).toISOString(),
    metric_name: "cpu_usage",
    entity_id: "core-01",
    entity_type: "node",
    value: 48,
    unit: "percentage"
  },
  {
    timestamp: new Date(Date.now() - 180000).toISOString(),
    metric_name: "memory_usage",
    entity_id: "core-01",
    entity_type: "node",
    value: 67,
    unit: "percentage"
  },
  {
    timestamp: new Date(Date.now() - 120000).toISOString(),
    metric_name: "link_utilization",
    entity_id: "link-01",
    entity_type: "link",
    value: 45,
    unit: "percentage"
  },
  {
    timestamp: new Date(Date.now() - 60000).toISOString(),
    metric_name: "link_utilization",
    entity_id: "link-01",
    entity_type: "link",
    value: 52,
    unit: "percentage"
  }
];

export const mockNetworkAlerts: NetworkAlert[] = [
  {
    id: "alert-001",
    device_id: "device-003",
    interface_id: "GigabitEthernet0/1",
    type: "high_cpu",
    severity: "warning",
    title: "High CPU Usage Detected",
    message: "CPU usage on access-switch-01 has exceeded 75% for 5 minutes",
    status: "active",
    created_at: new Date(Date.now() - 600000).toISOString(),
    updated_at: new Date(Date.now() - 300000).toISOString()
  },
  {
    id: "alert-002",
    device_id: "device-002",
    type: "link_down",
    severity: "critical",
    title: "Link Failure",
    message: "Primary uplink on dist-switch-01 is down",
    status: "acknowledged",
    created_at: new Date(Date.now() - 1200000).toISOString(),
    updated_at: new Date(Date.now() - 900000).toISOString(),
    acknowledged_at: new Date(Date.now() - 900000).toISOString(),
    acknowledged_by: "network-admin"
  },
  {
    id: "alert-003",
    device_id: "device-001",
    type: "high_temperature",
    severity: "info",
    title: "Temperature Alert",
    message: "Core router temperature is approaching warning threshold",
    status: "active",
    created_at: new Date(Date.now() - 180000).toISOString()
  }
];

export const mockTopologyMetrics: TopologyMetrics = {
  total_nodes: 4,
  total_links: 3,
  network_diameter: 3,
  average_path_length: 2.1,
  clustering_coefficient: 0.45,
  redundancy_score: 0.67
};

export const mockCriticalNodes: CriticalNode[] = [
  {
    node_id: "core-01",
    criticality_score: 95,
    impact_analysis: "Primary core router serving downtown area. Failure would affect 3 distribution nodes and 12,000 customers.",
    redundancy_paths: 2,
    dependent_devices: ["dist-01", "dist-02", "dist-03"]
  },
  {
    node_id: "dist-01",
    criticality_score: 78,
    impact_analysis: "Key distribution switch for midtown residential area. Serves 4,500 customers.",
    redundancy_paths: 1,
    dependent_devices: ["access-01", "access-02"]
  }
];

export const mockPathAnalysis: PathAnalysis = {
  path_id: "path-core01-access01",
  source_node: "core-01",
  target_node: "access-01",
  hop_count: 2,
  total_latency_ms: 8.3,
  total_bandwidth_mbps: 100,
  path_nodes: ["core-01", "dist-01", "access-01"],
  path_links: ["link-01", "link-04"],
  bottleneck_links: ["link-04"],
  redundant_paths: []
};

// Mock API response functions
export const networkApiMocks = {
  // Topology endpoints
  getTopologyNodes: () => Promise.resolve({ data: mockNetworkNodes }),
  getTopologyLinks: () => Promise.resolve({ data: mockNetworkLinks }),
  getTopologyMetrics: () => Promise.resolve({ data: mockTopologyMetrics }),
  getCriticalNodes: () => Promise.resolve({ data: mockCriticalNodes }),
  
  // Path analysis
  analyzeNetworkPath: (source: string, target: string) => 
    Promise.resolve({ 
      data: {
        ...mockPathAnalysis,
        source_node: source,
        target_node: target,
        path_id: `path-${source}-${target}`
      }
    }),
  
  getNodeConnectivity: (nodeId: string) =>
    Promise.resolve({
      data: {
        node_id: nodeId,
        connected_links: mockNetworkNodes.find(n => n.node_id === nodeId)?.connected_links || [],
        neighbor_nodes: ["dist-01", "core-02"],
        connectivity_status: "fully_connected"
      }
    }),

  // Geographic endpoints
  getServiceAreas: () => Promise.resolve({ data: mockServiceAreas }),
  getCoverageGaps: () => Promise.resolve({ data: mockCoverageGaps }),
  
  analyzeCoverage: () =>
    Promise.resolve({
      data: {
        total_coverage_percentage: 87.5,
        gaps_identified: mockCoverageGaps.length,
        priority_gaps: mockCoverageGaps.filter(g => g.priority_score > 80).length,
        buildout_recommendations: ["Deploy 3 additional access points", "Extend fiber to rural areas"]
      }
    }),

  optimizeRoute: (data: any) =>
    Promise.resolve({
      data: {
        optimized_route: {
          distance_km: 25.7,
          estimated_time_minutes: 42,
          waypoints: data.waypoints,
          route_coordinates: [
            [data.start_coordinates.longitude, data.start_coordinates.latitude],
            ...data.waypoints.map((wp: any) => [wp.longitude, wp.latitude]),
            [data.end_coordinates.longitude, data.end_coordinates.latitude]
          ]
        }
      }
    }),

  // Monitoring endpoints
  getNetworkAlerts: () => Promise.resolve({ data: mockNetworkAlerts }),
  getPerformanceData: () => Promise.resolve({ data: mockPerformanceMetrics }),
  
  updateAlert: (alertId: string, updates: any) =>
    Promise.resolve({
      data: {
        ...mockNetworkAlerts.find(a => a.id === alertId),
        ...updates,
        updated_at: new Date().toISOString()
      }
    }),

  getEntityMetrics: (entityId: string, entityType: string, metricName?: string) =>
    Promise.resolve({
      data: mockPerformanceMetrics.filter(m => 
        m.entity_id === entityId && 
        m.entity_type === entityType &&
        (metricName ? m.metric_name === metricName : true)
      )
    })
};

// Mock WebSocket events for real-time updates
export const mockWebSocketEvents = {
  // Network topology events
  'node_updated': (nodeId: string) => ({
    node_id: nodeId,
    status: NodeStatus.MAINTENANCE,
    cpu_usage: Math.floor(Math.random() * 100),
    memory_usage: Math.floor(Math.random() * 100),
    timestamp: new Date().toISOString()
  }),
  
  'link_updated': (linkId: string) => ({
    link_id: linkId,
    utilization_percentage: Math.floor(Math.random() * 100),
    latency_ms: Math.random() * 10,
    timestamp: new Date().toISOString()
  }),

  'node_added': () => ({
    node_id: `node-${Date.now()}`,
    node_type: NodeType.ACCESS_SWITCH,
    status: NodeStatus.ACTIVE,
    latitude: 40.7 + Math.random() * 0.1,
    longitude: -74.0 + Math.random() * 0.1,
    timestamp: new Date().toISOString()
  }),

  'node_removed': () => 'access-01',

  'link_added': () => ({
    link_id: `link-${Date.now()}`,
    source_node_id: 'core-01',
    target_node_id: `node-${Date.now()}`,
    link_type: LinkType.ETHERNET,
    status: NodeStatus.ACTIVE,
    timestamp: new Date().toISOString()
  }),

  'link_removed': () => 'link-04',

  // Monitoring events
  'alert_created': () => ({
    id: `alert-${Date.now()}`,
    type: 'high_cpu',
    severity: 'warning',
    title: 'CPU Usage Alert',
    message: 'CPU usage above threshold',
    device_id: 'device-001',
    status: 'active',
    created_at: new Date().toISOString()
  }),

  'alert_updated': (alertId: string) => ({
    id: alertId,
    status: 'acknowledged',
    acknowledged_at: new Date().toISOString(),
    acknowledged_by: 'test-user'
  }),

  'alert_resolved': () => 'alert-001',

  'performance_data': () => [
    {
      timestamp: new Date().toISOString(),
      metric_name: 'cpu_usage',
      entity_id: 'core-01',
      entity_type: 'node',
      value: Math.floor(Math.random() * 100),
      unit: 'percentage'
    },
    {
      timestamp: new Date().toISOString(),
      metric_name: 'link_utilization',
      entity_id: 'link-01',
      entity_type: 'link',
      value: Math.floor(Math.random() * 100),
      unit: 'percentage'
    }
  ],

  'node_status_changed': (nodeId: string) => ({
    node_id: nodeId,
    status: Math.random() > 0.5 ? 'active' : 'inactive',
    timestamp: new Date().toISOString()
  }),

  'link_utilization_updated': (linkId: string) => ({
    link_id: linkId,
    utilization: Math.floor(Math.random() * 100),
    timestamp: new Date().toISOString()
  })
};