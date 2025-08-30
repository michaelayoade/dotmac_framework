/**
 * Network topology visualization and management types
 * Comprehensive type definitions for advanced network visualization
 */

import type { User, APIResponse } from '@dotmac/headless';
import type { GeoJSON } from 'geojson';

// Base network entity types
export interface NetworkEntity {
  id: string;
  tenant_id: string;
  created_at: string;
  updated_at: string;
  name: string;
  description?: string;
  metadata?: Record<string, any>;
}

// Network node types and enums
export enum NodeType {
  CORE_ROUTER = 'core_router',
  DISTRIBUTION_ROUTER = 'distribution_router',
  ACCESS_SWITCH = 'access_switch',
  WIFI_AP = 'wifi_ap',
  CELL_TOWER = 'cell_tower',
  FIBER_SPLICE = 'fiber_splice',
  POP = 'pop',
  CUSTOMER_PREMISES = 'customer_premises',
  DATA_CENTER = 'data_center'
}

export enum LinkType {
  FIBER = 'fiber',
  ETHERNET = 'ethernet',
  WIRELESS = 'wireless',
  COPPER = 'copper',
  VIRTUAL = 'virtual'
}

export enum NodeStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  MAINTENANCE = 'maintenance',
  FAILED = 'failed',
  UNKNOWN = 'unknown'
}

// Network topology entities
export interface NetworkNode extends NetworkEntity {
  node_id: string;
  node_type: NodeType;
  device_id?: string;
  site_id?: string;

  // Geographic coordinates
  latitude?: number;
  longitude?: number;
  elevation?: number;
  x_coordinate?: number;
  y_coordinate?: number;
  z_coordinate?: number;

  // Device properties
  ip_address?: string;
  mac_address?: string;
  hostname?: string;
  manufacturer?: string;
  model?: string;
  firmware_version?: string;

  // Network properties
  bandwidth_mbps?: number;
  coverage_radius_km?: number;
  port_count?: number;

  // Operational data
  status: NodeStatus;
  last_seen_at?: string;
  uptime_percentage?: number;

  // Performance metrics
  cpu_usage?: number;
  memory_usage?: number;
  temperature?: number;
  power_consumption?: number;

  // Connectivity
  connected_links: string[];
  neighbor_count: number;

  // Visual properties
  color?: string;
  size?: number;
  icon?: string;
  label_visible?: boolean;
}

export interface NetworkLink extends NetworkEntity {
  link_id: string;
  source_node_id: string;
  target_node_id: string;

  // Link properties
  link_type: LinkType;
  source_port?: string;
  target_port?: string;

  // Physical properties
  bandwidth_mbps?: number;
  latency_ms?: number;
  length_km?: number;
  cost: number;

  // Performance metrics
  utilization_percentage?: number;
  packet_loss?: number;
  error_rate?: number;

  // Status
  status: NodeStatus;
  operational_status?: string;

  // Visual properties
  color?: string;
  width?: number;
  style?: 'solid' | 'dashed' | 'dotted';
  arrow_style?: string;
}

// Legacy device interface for backward compatibility
export interface NetworkDevice {
  id: string;
  name: string;
  type: DeviceType;
  status: DeviceStatus;
  ip_address: string;
  mac_address?: string;
  location?: string;
  vendor: string;
  model: string;
  firmware_version?: string;
  serial_number?: string;
  last_seen?: Date;
  uptime?: number;
  capabilities: DeviceCapability[];
  interfaces: NetworkInterface[];
  metrics?: DeviceMetrics;
  configuration?: DeviceConfiguration;
}

export interface NetworkInterface {
  id: string;
  name: string;
  type: InterfaceType;
  status: InterfaceStatus;
  speed?: number; // Mbps
  duplex?: 'full' | 'half' | 'auto';
  mtu?: number;
  vlan_id?: number;
  ip_address?: string;
  subnet_mask?: string;
  mac_address?: string;
  traffic_stats?: InterfaceStats;
}

export interface InterfaceStats {
  bytes_in: number;
  bytes_out: number;
  packets_in: number;
  packets_out: number;
  errors_in: number;
  errors_out: number;
  drops_in: number;
  drops_out: number;
  utilization_in: number; // Percentage
  utilization_out: number; // Percentage
  last_updated: Date;
}

export interface DeviceMetrics {
  cpu_usage: number; // Percentage
  memory_usage: number; // Percentage
  temperature?: number; // Celsius
  power_consumption?: number; // Watts
  fan_speeds?: number[];
  disk_usage?: DiskUsage[];
  network_utilization: number; // Percentage
  error_rate: number; // Percentage
  latency?: number; // Milliseconds
  packet_loss?: number; // Percentage
  last_updated: Date;
}

export interface DiskUsage {
  partition: string;
  used: number; // Bytes
  total: number; // Bytes
  percentage: number;
}

export interface DeviceConfigurationType {
  snmp_enabled: boolean;
  snmp_community?: string;
  ssh_enabled: boolean;
  telnet_enabled: boolean;
  web_management_enabled: boolean;
  management_vlan?: number;
  ntp_servers: string[];
  dns_servers: string[];
  syslog_servers: string[];
  backup_frequency: BackupFrequency;
  last_backup?: Date;
  config_version?: string;
}

export interface NetworkTopology {
  id: string;
  name: string;
  description?: string;
  nodes: TopologyNode[];
  edges: TopologyEdge[];
  layout: TopologyLayout;
  metadata: TopologyMetadata;
}

export interface TopologyNode {
  id: string;
  device_id: string;
  position: Position;
  size: Size;
  label: string;
  type: NodeType;
  status: DeviceStatus;
  metadata?: Record<string, any>;
}

export interface TopologyEdge {
  id: string;
  source: string;
  target: string;
  type: ConnectionType;
  status: ConnectionStatus;
  bandwidth?: number; // Mbps
  latency?: number; // Milliseconds
  utilization?: number; // Percentage
  metadata?: Record<string, any>;
}

export interface Position {
  x: number;
  y: number;
}

export interface Size {
  width: number;
  height: number;
}

export interface TopologyLayout {
  type: LayoutType;
  settings: Record<string, any>;
}

export interface TopologyMetadata {
  created_at: Date;
  updated_at: Date;
  created_by: string;
  version: number;
  auto_layout: boolean;
  show_labels: boolean;
  show_metrics: boolean;
}

export interface NetworkAlert {
  id: string;
  device_id: string;
  interface_id?: string;
  type: AlertType;
  severity: AlertSeverity;
  title: string;
  message: string;
  status: AlertStatus;
  created_at: Date;
  updated_at?: Date;
  acknowledged_at?: Date;
  acknowledged_by?: string;
  resolved_at?: Date;
  resolved_by?: string;
  metadata?: Record<string, any>;
}

export interface MonitoringRule {
  id: string;
  name: string;
  description?: string;
  enabled: boolean;
  device_filter: DeviceFilter;
  metric_type: MetricType;
  condition: AlertCondition;
  threshold_value: number;
  comparison: ComparisonOperator;
  duration: number; // Seconds
  severity: AlertSeverity;
  notification_channels: string[];
  created_at: Date;
  updated_at: Date;
}

export interface DeviceFilter {
  device_types?: DeviceType[];
  locations?: string[];
  vendors?: string[];
  tags?: string[];
}

export interface AlertCondition {
  metric: string;
  operator: ComparisonOperator;
  value: number;
  duration?: number; // Seconds
}

// Enums
export enum DeviceType {
  ROUTER = 'router',
  SWITCH = 'switch',
  FIREWALL = 'firewall',
  ACCESS_POINT = 'access_point',
  MODEM = 'modem',
  ONT = 'ont',
  OLT = 'olt',
  SERVER = 'server',
  UPS = 'ups',
  PDU = 'pdu',
  OTHER = 'other'
}

export enum DeviceStatus {
  ONLINE = 'online',
  OFFLINE = 'offline',
  WARNING = 'warning',
  CRITICAL = 'critical',
  MAINTENANCE = 'maintenance',
  UNKNOWN = 'unknown'
}

export enum InterfaceType {
  ETHERNET = 'ethernet',
  FIBER = 'fiber',
  WIRELESS = 'wireless',
  SERIAL = 'serial',
  USB = 'usb',
  OTHER = 'other'
}

export enum InterfaceStatus {
  UP = 'up',
  DOWN = 'down',
  DISABLED = 'disabled',
  ERROR = 'error'
}

export enum DeviceCapability {
  SNMP = 'snmp',
  SSH = 'ssh',
  TELNET = 'telnet',
  HTTP = 'http',
  HTTPS = 'https',
  NETCONF = 'netconf',
  RESTCONF = 'restconf'
}

export enum BackupFrequency {
  NEVER = 'never',
  DAILY = 'daily',
  WEEKLY = 'weekly',
  MONTHLY = 'monthly',
  ON_CHANGE = 'on_change'
}

// Legacy node types - use main NodeType enum instead
export enum LegacyNodeType {
  DEVICE = 'device',
  SUBNET = 'subnet',
  CLOUD = 'cloud',
  INTERNET = 'internet'
}

export enum ConnectionType {
  ETHERNET = 'ethernet',
  FIBER = 'fiber',
  WIRELESS = 'wireless',
  VIRTUAL = 'virtual'
}

export enum ConnectionStatus {
  ACTIVE = 'active',
  INACTIVE = 'inactive',
  ERROR = 'error'
}

export enum LayoutType {
  FORCE = 'force',
  HIERARCHICAL = 'hierarchical',
  GRID = 'grid',
  CIRCULAR = 'circular',
  MANUAL = 'manual'
}

export enum AlertType {
  DEVICE_DOWN = 'device_down',
  INTERFACE_DOWN = 'interface_down',
  HIGH_CPU = 'high_cpu',
  HIGH_MEMORY = 'high_memory',
  HIGH_TEMPERATURE = 'high_temperature',
  HIGH_BANDWIDTH = 'high_bandwidth',
  HIGH_ERROR_RATE = 'high_error_rate',
  CONFIGURATION_CHANGE = 'configuration_change',
  BACKUP_FAILED = 'backup_failed'
}

export enum AlertSeverity {
  INFO = 'info',
  WARNING = 'warning',
  CRITICAL = 'critical',
  EMERGENCY = 'emergency'
}

export enum AlertStatus {
  ACTIVE = 'active',
  ACKNOWLEDGED = 'acknowledged',
  RESOLVED = 'resolved',
  SUPPRESSED = 'suppressed'
}

export enum MetricType {
  CPU_USAGE = 'cpu_usage',
  MEMORY_USAGE = 'memory_usage',
  INTERFACE_UTILIZATION = 'interface_utilization',
  ERROR_RATE = 'error_rate',
  TEMPERATURE = 'temperature',
  POWER_CONSUMPTION = 'power_consumption'
}

export enum ComparisonOperator {
  GREATER_THAN = 'gt',
  GREATER_THAN_EQUAL = 'gte',
  LESS_THAN = 'lt',
  LESS_THAN_EQUAL = 'lte',
  EQUAL = 'eq',
  NOT_EQUAL = 'neq'
}

// API Request/Response Types
export interface CreateDeviceRequest {
  name: string;
  type: DeviceType;
  ip_address: string;
  vendor: string;
  model: string;
  location?: string;
  mac_address?: string;
  serial_number?: string;
  capabilities?: DeviceCapability[];
}

export interface UpdateDeviceRequest {
  name?: string;
  type?: DeviceType;
  ip_address?: string;
  location?: string;
  vendor?: string;
  model?: string;
  firmware_version?: string;
  serial_number?: string;
  capabilities?: DeviceCapability[];
}

export interface DeviceListResponse {
  devices: NetworkDevice[];
  total: number;
  page: number;
  per_page: number;
}

export interface CreateTopologyRequest {
  name: string;
  description?: string;
  layout?: TopologyLayout;
}

export interface UpdateTopologyRequest {
  name?: string;
  description?: string;
  nodes?: TopologyNode[];
  edges?: TopologyEdge[];
  layout?: TopologyLayout;
  metadata?: Partial<TopologyMetadata>;
}

export interface TopologyListResponse {
  topologies: NetworkTopology[];
  total: number;
  page: number;
  per_page: number;
}

export interface AlertListResponse {
  alerts: NetworkAlert[];
  total: number;
  page: number;
  per_page: number;
}

export interface CreateMonitoringRuleRequest {
  name: string;
  description?: string;
  device_filter: DeviceFilter;
  metric_type: MetricType;
  condition: AlertCondition;
  threshold_value: number;
  comparison: ComparisonOperator;
  duration: number;
  severity: AlertSeverity;
  notification_channels: string[];
}

export interface UpdateMonitoringRuleRequest {
  name?: string;
  description?: string;
  enabled?: boolean;
  device_filter?: DeviceFilter;
  condition?: AlertCondition;
  threshold_value?: number;
  comparison?: ComparisonOperator;
  duration?: number;
  severity?: AlertSeverity;
  notification_channels?: string[];
}

// Component Props Types
export interface DeviceListProps {
  devices?: NetworkDevice[];
  loading?: boolean;
  onDeviceSelect?: (device: NetworkDevice) => void;
  onDeviceEdit?: (device: NetworkDevice) => void;
  onDeviceDelete?: (deviceId: string) => void;
  onRefresh?: () => void;
}

export interface TopologyViewerProps {
  topology: NetworkTopology;
  editable?: boolean;
  showMetrics?: boolean;
  onNodeSelect?: (node: TopologyNode) => void;
  onNodeMove?: (nodeId: string, position: Position) => void;
  onEdgeSelect?: (edge: TopologyEdge) => void;
  onLayoutChange?: (layout: TopologyLayout) => void;
}

export interface DeviceMetricsProps {
  deviceId: string;
  timeRange?: TimeRange;
  metrics?: DeviceMetrics;
  onRefresh?: () => void;
}

export interface AlertListProps {
  alerts?: NetworkAlert[];
  loading?: boolean;
  onAlertAcknowledge?: (alertId: string) => void;
  onAlertResolve?: (alertId: string) => void;
  onRefresh?: () => void;
}

export interface TimeRange {
  start: Date;
  end: Date;
}

// Configuration Types
export interface NetworkConfig {
  api_endpoint: string;
  websocket_endpoint?: string;
  refresh_interval: number; // Seconds
  max_devices_per_topology: number;
  default_layout: LayoutType;
  enable_auto_discovery: boolean;
  snmp_timeout: number; // Seconds
  ssh_timeout: number; // Seconds
}

// Advanced Topology Visualization Types
export interface AdvancedTopologyConfig {
  render_engine: TopologyRenderEngine;
  physics_enabled: boolean;
  clustering_enabled: boolean;
  max_nodes_for_physics: number;
  auto_fit: boolean;
  smooth_animations: boolean;
  interaction_config: InteractionConfig;
  visual_config: VisualConfig;
}

export interface InteractionConfig {
  drag_nodes: boolean;
  zoom_enabled: boolean;
  pan_enabled: boolean;
  select_enabled: boolean;
  hover_enabled: boolean;
  keyboard_shortcuts: boolean;
  context_menu: boolean;
  multi_select: boolean;
}

export interface VisualConfig {
  node_styles: NodeStyleConfig;
  edge_styles: EdgeStyleConfig;
  theme: TopologyTheme;
  show_labels: boolean;
  show_metrics_overlay: boolean;
  show_status_indicators: boolean;
  animation_duration: number;
}

export interface NodeStyleConfig {
  default_size: number;
  size_by_metric?: MetricType;
  color_by_status: boolean;
  shape_by_type: boolean;
  custom_icons: boolean;
  glow_effects: boolean;
  label_position: LabelPosition;
}

export interface EdgeStyleConfig {
  default_width: number;
  width_by_bandwidth: boolean;
  color_by_utilization: boolean;
  show_direction: boolean;
  curved_edges: boolean;
  animated_traffic: boolean;
  dashed_inactive: boolean;
}

export interface TopologyCluster {
  id: string;
  name: string;
  nodes: string[];
  color?: string;
  collapsed: boolean;
  position?: Position;
  metadata?: Record<string, any>;
}

export interface TopologyFilter {
  device_types: DeviceType[];
  status_filter: DeviceStatus[];
  location_filter: string[];
  vendor_filter: string[];
  search_query?: string;
  metric_threshold?: MetricThreshold;
}

export interface MetricThreshold {
  metric: MetricType;
  operator: ComparisonOperator;
  value: number;
}

export interface NetworkPath {
  id: string;
  source: string;
  target: string;
  path: string[];
  hops: number;
  total_latency: number;
  bottleneck_link?: string;
  redundant_paths: string[][];
}

export interface NetworkFlowData {
  source_ip: string;
  destination_ip: string;
  protocol: string;
  port: number;
  bytes_per_second: number;
  packets_per_second: number;
  flow_duration: number;
  application?: string;
}

export interface TopologyAnimation {
  id: string;
  type: AnimationType;
  duration: number;
  easing: EasingFunction;
  target_nodes?: string[];
  target_edges?: string[];
  properties: Record<string, any>;
}

export interface TopologyLayer {
  id: string;
  name: string;
  visible: boolean;
  opacity: number;
  z_index: number;
  nodes: string[];
  edges: string[];
  metadata?: Record<string, any>;
}

export interface NetworkDiscoveryConfig {
  enabled: boolean;
  scan_subnets: string[];
  scan_interval: number; // Minutes
  discovery_methods: DiscoveryMethod[];
  auto_add_devices: boolean;
  notification_on_new_device: boolean;
}

export interface DeviceGroup {
  id: string;
  name: string;
  description?: string;
  color: string;
  devices: string[];
  created_at: Date;
  updated_at: Date;
}

export interface TopologySnapshot {
  id: string;
  name: string;
  topology_id: string;
  snapshot_data: NetworkTopology;
  created_at: Date;
  created_by: string;
  description?: string;
}

export interface NetworkCapacityAnalysis {
  device_id: string;
  current_utilization: number;
  predicted_utilization: number;
  capacity_threshold: number;
  time_to_threshold?: number; // Days
  recommendations: string[];
}

// Enhanced Enums
export enum TopologyRenderEngine {
  D3 = 'd3',
  CYTOSCAPE = 'cytoscape',
  VIS = 'vis',
  REACT_FLOW = 'react-flow',
  THREE_JS = 'three-js'
}

export enum TopologyTheme {
  LIGHT = 'light',
  DARK = 'dark',
  HIGH_CONTRAST = 'high-contrast',
  COLORBLIND_FRIENDLY = 'colorblind-friendly',
  CUSTOM = 'custom'
}

export enum LabelPosition {
  TOP = 'top',
  BOTTOM = 'bottom',
  LEFT = 'left',
  RIGHT = 'right',
  CENTER = 'center',
  AUTO = 'auto'
}

export enum AnimationType {
  FADE_IN = 'fade-in',
  FADE_OUT = 'fade-out',
  SLIDE = 'slide',
  SCALE = 'scale',
  PULSE = 'pulse',
  FLOW = 'flow',
  HIGHLIGHT = 'highlight'
}

export enum EasingFunction {
  LINEAR = 'linear',
  EASE_IN = 'ease-in',
  EASE_OUT = 'ease-out',
  EASE_IN_OUT = 'ease-in-out',
  BOUNCE = 'bounce',
  ELASTIC = 'elastic'
}

export enum DiscoveryMethod {
  PING = 'ping',
  ARP = 'arp',
  SNMP = 'snmp',
  CDP = 'cdp',
  LLDP = 'lldp',
  TRACEROUTE = 'traceroute'
}

// Advanced Component Props
export interface AdvancedTopologyViewerProps extends TopologyViewerProps {
  config: AdvancedTopologyConfig;
  filters?: TopologyFilter;
  clusters?: TopologyCluster[];
  layers?: TopologyLayer[];
  animations?: TopologyAnimation[];
  onNodeDoubleClick?: (node: TopologyNode) => void;
  onEdgeDoubleClick?: (edge: TopologyEdge) => void;
  onBackgroundClick?: () => void;
  onSelectionChange?: (selectedNodes: string[], selectedEdges: string[]) => void;
  onViewportChange?: (viewport: ViewportState) => void;
}

export interface ViewportState {
  zoom: number;
  center: Position;
  bounds: {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
  };
}

export interface TopologyToolbarProps {
  onLayoutChange: (layout: LayoutType) => void;
  onZoomIn: () => void;
  onZoomOut: () => void;
  onFitToView: () => void;
  onTogglePhysics: () => void;
  onToggleClustering: () => void;
  onExportImage: () => void;
  onSaveSnapshot: () => void;
  currentLayout: LayoutType;
  zoomLevel: number;
  physicsEnabled: boolean;
  clusteringEnabled: boolean;
}

export interface NetworkFlowVisualizationProps {
  flows: NetworkFlowData[];
  timeRange: TimeRange;
  aggregation_level: 'second' | 'minute' | 'hour';
  show_protocols: boolean;
  show_applications: boolean;
  onFlowSelect?: (flow: NetworkFlowData) => void;
}

export interface NetworkPathAnalysisProps {
  source_device: string;
  target_device: string;
  paths: NetworkPath[];
  selected_path?: string;
  onPathSelect: (pathId: string) => void;
  onRunTraceroute: () => void;
}
