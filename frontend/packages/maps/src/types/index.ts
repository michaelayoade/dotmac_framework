/**
 * Universal Map Types
 * Comprehensive type definitions for all GIS and mapping operations
 */

// Core Geographic Types
export interface Coordinates {
  lat: number;
  lng: number;
  elevation?: number;
}

export interface Bounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface Polygon {
  coordinates: Coordinates[];
  holes?: Coordinates[][];
}

export interface BoundingBox {
  min: Coordinates;
  max: Coordinates;
}

// Map Configuration
export interface MapConfig {
  center: Coordinates;
  zoom: number;
  minZoom?: number;
  maxZoom?: number;
  bounds?: Bounds;
  scrollWheelZoom?: boolean;
  doubleClickZoom?: boolean;
  dragging?: boolean;
  touchZoom?: boolean;
  zoomControl?: boolean;
  attributionControl?: boolean;
  maxBounds?: Bounds;
}

// Portal Context
export type PortalType = 'management-admin' | 'admin' | 'customer' | 'reseller' | 'technician';

export interface PortalContext {
  portalType: PortalType;
  userId: string;
  tenantId?: string;
  permissions: string[];
  preferences?: Record<string, any>;
}

// Map Providers
export type MapProviderType = 'leaflet' | 'google' | 'mapbox' | 'mock';

export interface MapProviderConfig {
  type: MapProviderType;
  apiKey?: string;
  styleUrl?: string;
  attribution?: string;
  maxZoom?: number;
  retina?: boolean;
}

// Map Features
export interface MapMarker {
  id: string;
  position: Coordinates;
  type: 'customer' | 'tower' | 'fiber' | 'technician' | 'issue' | 'poi' | 'asset' | 'competitor';
  status?: 'active' | 'inactive' | 'maintenance' | 'error' | 'warning' | 'planned';
  title: string;
  description?: string;
  icon?: string;
  color?: string;
  size?: 'small' | 'medium' | 'large';
  popup?: {
    content: string | React.ReactNode;
    maxWidth?: number;
    className?: string;
  };
  metadata?: Record<string, any>;
  onClick?: (marker: MapMarker) => void;
  zIndex?: number;
  cluster?: boolean;
}

export interface ServiceArea {
  id: string;
  name: string;
  type: 'fiber' | 'wireless' | 'cable' | 'dsl' | 'satellite' | 'hybrid';
  polygon: Polygon;
  serviceLevel: 'full' | 'limited' | 'planned' | 'unavailable';
  maxSpeed: number; // Mbps
  coverage: number; // percentage 0-100
  customers?: number;
  revenue?: number;
  color?: string;
  fillOpacity?: number;
  strokeWeight?: number;
  priority?: number;
  metadata?: {
    infrastructure?: string[];
    buildoutCost?: number;
    estimatedCustomers?: number;
    competitorPresence?: boolean;
  };
}

export interface NetworkNode {
  id: string;
  name: string;
  type: 'core' | 'distribution' | 'access' | 'edge' | 'customer' | 'tower' | 'fiber_node' | 'switch' | 'router';
  position: Coordinates;
  status: 'online' | 'offline' | 'maintenance' | 'error' | 'degraded';
  capacity: string;
  utilization: number; // percentage 0-100
  connections?: string[]; // IDs of connected nodes
  address?: string;
  territory?: string;
  metrics?: {
    uptime: number; // percentage
    latency: number; // ms
    packetLoss: number; // percentage
    bandwidth: number; // Mbps
    temperature?: number; // Celsius
    power?: number; // Watts
  };
  maintenance?: {
    lastMaintenance: Date;
    nextScheduled?: Date;
    maintenanceWindow?: string;
  };
  vendor?: string;
  model?: string;
  serialNumber?: string;
  installDate?: Date;
}

export interface Route {
  id: string;
  name: string;
  waypoints: Coordinates[];
  type: 'installation' | 'maintenance' | 'emergency' | 'inspection' | 'delivery';
  status: 'planned' | 'in_progress' | 'completed' | 'cancelled';
  assignedTechnician?: string;
  estimatedTime?: number; // minutes
  actualTime?: number; // minutes
  distance?: number; // meters
  priority: 'low' | 'medium' | 'high' | 'urgent';
  workOrders?: string[];
  metadata?: {
    vehicleType?: string;
    equipmentNeeded?: string[];
    specialInstructions?: string;
    customerContacts?: string[];
  };
}

// Territory Management
export interface Territory {
  id: string;
  name: string;
  region: string;
  polygon: Polygon;
  coordinates: Coordinates; // center point
  radius: number; // km
  totalCustomers: number;
  marketPenetration: number; // percentage
  monthlyRevenue: number;
  competition: 'low' | 'medium' | 'high';
  opportunities: {
    residential: number;
    business: number;
    enterprise: number;
    government: number;
  };
  demographics?: {
    population: number;
    medianIncome: number;
    householdDensity: number;
    businessDensity: number;
  };
  infrastructure?: {
    fiberCoverage: number; // percentage
    towerCoverage: number; // percentage
    competitorFiber: boolean;
    municipalFiber: boolean;
  };
}

// Coverage Analysis
export interface CoverageResult {
  area: number; // square km
  population: number;
  households: number;
  businesses: number;
  coveragePercentage: number;
  serviceTypes: string[];
  gaps: Gap[];
  recommendations: CoverageRecommendation[];
}

export interface Gap {
  id: string;
  polygon: Polygon;
  type: 'no_coverage' | 'poor_coverage' | 'limited_service';
  severity: 'low' | 'medium' | 'high' | 'critical';
  affectedCustomers: number;
  potentialRevenue: number;
  buildoutCost?: number;
  priority: number;
  recommendations: string[];
}

export interface CoverageRecommendation {
  id: string;
  type: 'infrastructure' | 'service' | 'marketing' | 'partnership';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  description: string;
  estimatedCost: number;
  estimatedRevenue: number;
  timeframe: string;
  requirements: string[];
}

// Route Optimization
export interface RouteOptimizationRequest {
  technicians: TechnicianInfo[];
  workOrders: WorkOrderInfo[];
  constraints: RouteConstraints;
  objectives: RouteObjective[];
}

export interface TechnicianInfo {
  id: string;
  name: string;
  location: Coordinates;
  skills: string[];
  availability: {
    start: Date;
    end: Date;
    breaks?: { start: Date; end: Date; }[];
  };
  vehicleType: string;
  maxWorkOrders: number;
  territory?: string;
}

export interface WorkOrderInfo {
  id: string;
  location: Coordinates;
  type: 'installation' | 'repair' | 'maintenance' | 'inspection';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  estimatedDuration: number; // minutes
  requiredSkills: string[];
  timeWindow?: {
    earliest: Date;
    latest: Date;
  };
  customerId: string;
  serviceAddress: string;
  specialInstructions?: string;
}

export interface RouteConstraints {
  maxTravelTime: number; // minutes
  maxWorkingHours: number; // hours per day
  lunchBreak: boolean;
  trafficConsideration: boolean;
  skillMatching: boolean;
  territoryRestrictions: boolean;
}

export interface RouteObjective {
  type: 'minimize_travel' | 'minimize_time' | 'maximize_completion' | 'balance_workload';
  weight: number; // 0-1
}

export interface OptimizedRoute extends Route {
  efficiency: number; // 0-1 score
  totalTravelTime: number; // minutes
  totalWorkTime: number; // minutes
  workOrderCount: number;
  savings: {
    timeReduction: number; // minutes
    fuelSavings: number; // dollars
    efficiencyGain: number; // percentage
  };
}

// Analytics and Metrics
export interface PenetrationMetrics {
  territoryId: string;
  totalHouseholds: number;
  totalBusinesses: number;
  currentCustomers: {
    residential: number;
    business: number;
    enterprise: number;
  };
  penetrationRates: {
    overall: number;
    residential: number;
    business: number;
    enterprise: number;
  };
  marketPotential: {
    households: number;
    businesses: number;
    estimatedRevenue: number;
  };
  competitorAnalysis: CompetitorInfo[];
}

export interface CompetitorInfo {
  name: string;
  serviceTypes: string[];
  coverage: number; // percentage
  marketShare: number; // percentage
  strengths: string[];
  weaknesses: string[];
  pricing: {
    residential: { min: number; max: number; };
    business: { min: number; max: number; };
  };
}

export interface CompetitorAnalysis {
  territory: string;
  overlapAreas: OverlapArea[];
  competitiveAdvantages: string[];
  threats: string[];
  opportunities: string[];
  recommendations: MarketingRecommendation[];
}

export interface OverlapArea {
  polygon: Polygon;
  competitors: string[];
  overlapType: 'full' | 'partial' | 'planned';
  customerImpact: number;
  revenueImpact: number;
}

export interface MarketingRecommendation {
  type: 'pricing' | 'service' | 'promotion' | 'partnership';
  description: string;
  targetArea: Polygon;
  expectedImpact: number; // percentage increase
  cost: number;
  timeline: string;
}

// Event Handling
export interface MapEvent {
  type: 'click' | 'dblclick' | 'contextmenu' | 'mouseover' | 'mouseout' | 'move' | 'zoom';
  coordinates: Coordinates;
  originalEvent: Event;
  target?: any;
}

export interface MarkerEvent extends MapEvent {
  marker: MapMarker;
}

export interface AreaEvent extends MapEvent {
  area: ServiceArea;
}

export interface NodeEvent extends MapEvent {
  node: NetworkNode;
}

// Map Layer Types
export interface MapLayer {
  id: string;
  name: string;
  type: 'markers' | 'polygons' | 'polylines' | 'heatmap' | 'cluster' | 'tile';
  visible: boolean;
  opacity?: number;
  zIndex?: number;
  data?: any[];
  style?: Record<string, any>;
  interactive?: boolean;
}

// Filter and Search
export interface MapFilter {
  markerTypes?: MapMarker['type'][];
  serviceTypes?: ServiceArea['type'][];
  nodeTypes?: NetworkNode['type'][];
  statusFilter?: string[];
  dateRange?: {
    start: Date;
    end: Date;
  };
  customFilters?: Record<string, any>;
}

export interface SearchCriteria {
  query: string;
  type: 'address' | 'customer' | 'asset' | 'territory';
  bounds?: Bounds;
  maxResults?: number;
}

export interface SearchResult {
  id: string;
  name: string;
  type: string;
  coordinates: Coordinates;
  address?: string;
  relevance: number; // 0-1
  metadata?: Record<string, any>;
}

// Map State
export interface MapState {
  center: Coordinates;
  zoom: number;
  bounds: Bounds;
  layers: MapLayer[];
  filters: MapFilter;
  selectedFeatures: string[];
  loading: boolean;
  error?: string;
}

// Performance and Caching
export interface MapCacheConfig {
  enabled: boolean;
  maxAge: number; // milliseconds
  maxSize: number; // MB
  strategy: 'memory' | 'localStorage' | 'indexedDB';
}

export interface PerformanceMetrics {
  renderTime: number; // ms
  dataLoadTime: number; // ms
  interactionLatency: number; // ms
  memoryUsage: number; // MB
  tileLoadTime: number; // ms
}

// Error Types
export interface MapError {
  code: string;
  message: string;
  details?: any;
  retryable: boolean;
}

// Configuration Types
export interface MapTheme {
  name: string;
  colors: {
    primary: string;
    secondary: string;
    accent: string;
    success: string;
    warning: string;
    error: string;
    background: string;
    text: string;
  };
  markers: {
    [key in MapMarker['type']]: {
      color: string;
      icon: string;
      size: number;
    };
  };
  areas: {
    [key in ServiceArea['type']]: {
      fillColor: string;
      strokeColor: string;
      fillOpacity: number;
      strokeWeight: number;
    };
  };
}

// Export utility types
export type MapEventHandler<T = MapEvent> = (event: T) => void;
export type AsyncMapOperation<T = any> = Promise<T>;
export type MapDataProvider<T = any> = () => Promise<T>;
