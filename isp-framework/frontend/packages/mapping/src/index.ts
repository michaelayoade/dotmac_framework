// Core mapping components
export { BaseMap, withMapFeatures } from './components/BaseMap';

// Network and infrastructure mapping
export { NetworkTopologyMap } from './components/NetworkTopologyMap';
export { NetworkMonitoringMap } from './components/NetworkMonitoringMap';

// Service and coverage mapping
export { ServiceCoverageMap } from './components/ServiceCoverageMap';
export { CustomerDensityHeatmap } from './components/CustomerDensityHeatmap';

// Field operations mapping
export { TechnicianLocationTracker } from './components/TechnicianLocationTracker';
export { WorkOrderRoutingMap } from './components/WorkOrderRoutingMap';

// Types and interfaces
export * from './types';

// Utility components (to be implemented)
export type {
  // Placeholder for future utility components
  MapLegendProps,
  LayerToggleProps,
} from './types';
