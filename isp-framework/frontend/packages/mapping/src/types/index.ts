import type { LatLngTuple } from 'leaflet';

// Geographic and location types
export interface Coordinates {
  latitude: number;
  longitude: number;
}

export interface GeoBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

// Network infrastructure types
export interface NetworkDevice {
  id: string;
  name: string;
  type: 'router' | 'switch' | 'fiber-node' | 'tower' | 'pop' | 'core';
  coordinates: Coordinates;
  status: 'online' | 'offline' | 'warning' | 'critical';
  capacity: number;
  utilization: number;
  connections: string[]; // Device IDs this device connects to
  properties: Record<string, any>;
  lastUpdate: Date;
}

export interface NetworkLink {
  id: string;
  source: string;
  target: string;
  type: 'fiber' | 'wireless' | 'copper';
  capacity: number;
  utilization: number;
  status: 'active' | 'inactive' | 'degraded';
  distance?: number;
  coordinates?: Coordinates[];
}

// Service coverage types
export interface ServiceArea {
  id: string;
  name: string;
  type: 'fiber' | 'cable' | 'dsl' | 'wireless';
  polygon: Coordinates[];
  serviceLevel: 'full' | 'partial' | 'planned';
  maxSpeed: number;
  population: number;
  households: number;
  coverage: number; // percentage
}

export interface Customer {
  id: string;
  name: string;
  coordinates: Coordinates;
  serviceType: 'residential' | 'business' | 'enterprise';
  plan: string;
  speed: number;
  monthlyRevenue: number;
  installDate: Date;
  status: 'active' | 'suspended' | 'cancelled';
  satisfaction?: number;
}

// Territory and reseller types
export interface Territory {
  id: string;
  name: string;
  resellerId: string;
  polygon: Coordinates[];
  demographics: {
    population: number;
    households: number;
    averageIncome: number;
    residential: number;
    business: number;
    enterprise: number;
  };
  competition: 'low' | 'medium' | 'high';
  marketPenetration: number;
  totalCustomers: number;
  monthlyRevenue: number;
  growthRate: number;
  opportunities: {
    newDevelopments: number;
    businessDistrict: boolean;
    schools: number;
    hospitals: number;
  };
}

// Field operations types
export interface Technician {
  id: string;
  name: string;
  coordinates: Coordinates;
  status: 'available' | 'on-job' | 'break' | 'offline';
  currentWorkOrder?: string;
  route?: Coordinates[];
  skills: string[];
  territory?: string;
}

export interface WorkOrder {
  id: string;
  type: 'installation' | 'repair' | 'maintenance' | 'survey';
  priority: 'low' | 'medium' | 'high' | 'critical';
  coordinates: Coordinates;
  address: string;
  customerId?: string;
  technicianId?: string;
  estimatedDuration: number;
  scheduledTime?: Date;
  status: 'pending' | 'assigned' | 'in-progress' | 'completed' | 'cancelled';
  description: string;
}

// Asset tracking types
export interface Asset {
  id: string;
  name: string;
  type: 'equipment' | 'vehicle' | 'inventory';
  coordinates: Coordinates;
  status: 'active' | 'maintenance' | 'storage' | 'disposed';
  assignedTo?: string;
  lastMaintenance?: Date;
  value: number;
  condition: 'excellent' | 'good' | 'fair' | 'poor';
}

// Incident and outage types
export interface Incident {
  id: string;
  type: 'outage' | 'degradation' | 'security' | 'maintenance';
  severity: 'low' | 'medium' | 'high' | 'critical';
  coordinates: Coordinates;
  affectedArea: Coordinates[];
  affectedCustomers: number;
  estimatedRevenueLoss: number;
  startTime: Date;
  endTime?: Date;
  cause?: string;
  resolution?: string;
  status: 'active' | 'investigating' | 'resolved';
}

// Analytics and metrics types
export interface HeatmapPoint {
  coordinates: Coordinates;
  value: number;
  weight?: number;
  metadata?: Record<string, any>;
}

export interface MarketAnalysis {
  territoryId: string;
  competitorData: {
    name: string;
    marketShare: number;
    pricing: number[];
    coordinates: Coordinates;
  }[];
  growthProjection: number;
  saturationLevel: number;
  recommendedActions: string[];
}

// Map configuration types
export interface MapTheme {
  primary: string;
  secondary: string;
  success: string;
  warning: string;
  error: string;
  info: string;
  background: string;
  text: string;
}

export interface MapConfig {
  defaultCenter: Coordinates;
  defaultZoom: number;
  minZoom: number;
  maxZoom: number;
  theme: MapTheme;
  tileLayerUrl?: string;
  attribution?: string;
}

// Component prop types
export interface BaseMapProps {
  className?: string;
  config?: Partial<MapConfig>;
  onMapReady?: (map: any) => void;
  children?: React.ReactNode;
}

export interface LayerToggleProps {
  layers: {
    id: string;
    name: string;
    visible: boolean;
    color?: string;
  }[];
  onToggle: (layerId: string, visible: boolean) => void;
}

export interface MapLegendProps {
  items: {
    color: string;
    label: string;
    value?: string | number;
  }[];
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
}

// Data visualization types
export interface ChartData {
  label: string;
  value: number;
  color?: string;
  metadata?: Record<string, any>;
}

export interface TimeSeriesData {
  timestamp: Date;
  value: number;
  category?: string;
}

// Performance and monitoring
export interface PerformanceMetrics {
  renderTime: number;
  dataPoints: number;
  memoryUsage: number;
  frameRate: number;
}

// Export utility types
export type MapEventHandler<T = any> = (event: T) => void;
export type CoordinateArray = LatLngTuple[];
export type DeviceStatus = NetworkDevice['status'];
export type ServiceType = Customer['serviceType'];
export type IncidentType = Incident['type'];
export type TechnicianStatus = Technician['status'];
export type WorkOrderStatus = WorkOrder['status'];
