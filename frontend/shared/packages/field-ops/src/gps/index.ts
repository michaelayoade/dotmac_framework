// GPS Service
export { LocationService } from './locationService';

// GPS Hooks
export { useGPSTracking } from './hooks/useGPSTracking';

// GPS Types
export type {
  GPSCoordinates,
  GPSLocation,
  LocationUpdate,
  GeoFence,
  GeoFenceEvent,
  LocationTrackingSettings,
  GPSPermissionStatus,
  LocationServiceStatus,
  RouteOptimization,
  LocationHistory,
} from './types';
