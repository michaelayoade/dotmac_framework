/**
 * Constants and default configurations for location services
 */

import type { GeolocationOptions, LocationServiceConfig } from './types/location';
import type { GeofenceConfig } from './types/geofence';

/**
 * Default geolocation options
 */
export const DEFAULT_GEOLOCATION_OPTIONS: GeolocationOptions = {
  enableHighAccuracy: true,
  timeout: 15000, // 15 seconds
  maximumAge: 60000, // 1 minute
  watchPosition: false,
  updateInterval: 5000, // 5 seconds
};

/**
 * Location update intervals (in milliseconds)
 */
export const LOCATION_UPDATE_INTERVALS = {
  REAL_TIME: 1000, // 1 second
  FREQUENT: 5000, // 5 seconds
  NORMAL: 15000, // 15 seconds
  BATTERY_SAVER: 60000, // 1 minute
  BACKGROUND: 300000, // 5 minutes
} as const;

/**
 * Geofence default configurations
 */
export const GEOFENCE_DEFAULTS = {
  RADIUS: 100, // meters
  DWELL_TIME: 30000, // 30 seconds
  MIN_RADIUS: 10, // meters
  MAX_RADIUS: 10000, // 10 km
  DEFAULT_TYPE: 'work_site' as const,
  BUFFER_DISTANCE: 50, // meters
};

/**
 * Routing default configurations
 */
export const ROUTING_DEFAULTS = {
  TRAVEL_MODE: 'driving' as const,
  OPTIMIZATION_ENABLED: true,
  MAX_WAYPOINTS: 25,
  ROUTE_TIMEOUT: 30000, // 30 seconds
  ALTERNATIVE_ROUTES: 2,
};

/**
 * Default location service configuration
 */
export const DEFAULT_LOCATION_SERVICE_CONFIG: LocationServiceConfig = {
  enableHighAccuracy: true,
  timeout: 15000,
  maximumAge: 60000,
  updateInterval: LOCATION_UPDATE_INTERVALS.NORMAL,
  backgroundTracking: false,
  persistLocation: true,
  autoStart: false,
};

/**
 * Location accuracy thresholds (in meters)
 */
export const ACCURACY_THRESHOLDS = {
  EXCELLENT: 5,
  GOOD: 10,
  FAIR: 50,
  POOR: 100,
} as const;

/**
 * Distance calculation constants
 */
export const DISTANCE_CONSTANTS = {
  EARTH_RADIUS_M: 6371000, // Earth radius in meters
  EARTH_RADIUS_KM: 6371, // Earth radius in kilometers
  METERS_PER_KM: 1000,
  FEET_PER_METER: 3.28084,
  MILES_PER_KM: 0.621371,
} as const;

/**
 * Travel speed constants (km/h)
 */
export const TRAVEL_SPEEDS = {
  WALKING: 5,
  CYCLING: 15,
  DRIVING_CITY: 30,
  DRIVING_HIGHWAY: 80,
  TRANSIT: 25,
} as const;

/**
 * Geofence event types
 */
export const GEOFENCE_EVENT_TYPES = {
  ENTER: 'enter',
  EXIT: 'exit',
  DWELL: 'dwell',
} as const;

/**
 * Location permission states
 */
export const PERMISSION_STATES = {
  GRANTED: 'granted',
  DENIED: 'denied',
  PROMPT: 'prompt',
} as const;

/**
 * Error codes for location services
 */
export const LOCATION_ERROR_CODES = {
  PERMISSION_DENIED: 1,
  POSITION_UNAVAILABLE: 2,
  TIMEOUT: 3,
} as const;

/**
 * Cache settings
 */
export const CACHE_SETTINGS = {
  LOCATION_TTL: 300000, // 5 minutes
  GEOCODING_TTL: 3600000, // 1 hour
  ROUTING_TTL: 1800000, // 30 minutes
  MAX_CACHE_SIZE: 1000, // Maximum number of cached items
} as const;

/**
 * API rate limiting settings
 */
export const RATE_LIMITS = {
  GEOCODING_PER_MINUTE: 50,
  ROUTING_PER_MINUTE: 20,
  LOCATION_UPDATES_PER_MINUTE: 120,
} as const;

/**
 * Map service providers
 */
export const MAP_PROVIDERS = {
  GOOGLE_MAPS: 'google',
  MAPBOX: 'mapbox',
  OPENSTREETMAP: 'osm',
  LEAFLET: 'leaflet',
} as const;

/**
 * Service area types for ISPs
 */
export const SERVICE_AREA_TYPES = {
  FIBER: 'fiber',
  WIRELESS: 'wireless',
  DSL: 'dsl',
  CABLE: 'cable',
  SATELLITE: 'satellite',
} as const;

/**
 * Coverage levels
 */
export const COVERAGE_LEVELS = {
  FULL: 'full',
  PARTIAL: 'partial',
  PLANNED: 'planned',
  NO_COVERAGE: 'none',
} as const;

/**
 * Default work order types for geofencing
 */
export const WORK_ORDER_TYPES = {
  INSTALLATION: 'installation',
  MAINTENANCE: 'maintenance',
  REPAIR: 'repair',
  INSPECTION: 'inspection',
  UPGRADE: 'upgrade',
} as const;

/**
 * Priority levels
 */
export const PRIORITY_LEVELS = {
  CRITICAL: 'critical',
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
} as const;

/**
 * Notification settings
 */
export const NOTIFICATION_SETTINGS = {
  GEOFENCE_ENTER: true,
  GEOFENCE_EXIT: true,
  ROUTE_OPTIMIZATION: true,
  LOCATION_PERMISSION: true,
  GPS_ACCURACY_WARNING: true,
} as const;
