/**
 * @dotmac/location-services
 *
 * Comprehensive location services for the DotMac ISP platform.
 * Provides GPS tracking, geofencing, routing, and mapping utilities.
 */

// Core services
export { LocationManager } from './core/LocationManager';
export { GeofenceManager } from './core/GeofenceManager';
export { RoutingService } from './core/RoutingService';
export { GeocodingService } from './core/GeocodingService';

// Hooks
export { useLocation } from './hooks/useLocation';
export { useGeofence } from './hooks/useGeofence';
export { useRouting } from './hooks/useRouting';
export { useGeocoding } from './hooks/useGeocoding';
export { useLocationTracking } from './hooks/useLocationTracking';

// Utilities
export {
  calculateDistance,
  calculateBearing,
  calculateMidpoint,
  formatCoordinates,
  parseCoordinates,
  validateCoordinates,
  isWithinRadius,
  findNearestLocation,
} from './utils/locationUtils';

export {
  optimizeRoute,
  calculateRouteDistance,
  estimateTravelTime,
  findShortestPath,
} from './utils/routingUtils';

export { createGeofence, checkGeofenceEntry, validateGeofence } from './utils/geofenceUtils';

// Types
export type {
  LocationData,
  GeolocationOptions,
  LocationError,
  LocationUpdate,
  LocationPermissionStatus,
} from './types/location';

export type { GeofenceConfig, GeofenceEvent, GeofenceStatus, GeofenceType } from './types/geofence';

export type {
  RouteConfig,
  RouteWaypoint,
  RouteOptimization,
  RoutingResult,
  TravelMode,
} from './types/routing';

export type {
  GeocodingResult,
  ReverseGeocodingResult,
  AddressComponent,
  PlaceResult,
} from './types/geocoding';

// Components
export { LocationProvider } from './components/LocationProvider';
export { GeofenceVisualization } from './components/GeofenceVisualization';
export { RouteDisplay } from './components/RouteDisplay';

// Constants
export {
  DEFAULT_GEOLOCATION_OPTIONS,
  LOCATION_UPDATE_INTERVALS,
  GEOFENCE_DEFAULTS,
  ROUTING_DEFAULTS,
} from './constants';

// Re-export field-ops GPS types for compatibility
export type {
  GPSCoordinates,
  GPSLocation,
  LocationUpdate as GPSLocationUpdate,
  GeoFence,
  GeoFenceEvent,
  LocationTrackingSettings,
  GPSPermissionStatus,
  LocationServiceStatus,
} from '../../field-ops/src/gps/types';

// Re-export field-ops services for compatibility
export { LocationService as GPSLocationService } from '../../field-ops/src/gps/locationService';
export { useGPSTracking } from '../../field-ops/src/gps/hooks/useGPSTracking';
