/**
 * Location service type definitions
 */

export interface LocationData {
  latitude: number;
  longitude: number;
  accuracy?: number;
  altitude?: number;
  altitudeAccuracy?: number;
  heading?: number;
  speed?: number;
  timestamp: number;
}

export interface GeolocationOptions {
  enableHighAccuracy?: boolean;
  timeout?: number;
  maximumAge?: number;
  watchPosition?: boolean;
  updateInterval?: number;
}

export interface LocationError {
  code: number;
  message: string;
  type: 'permission_denied' | 'position_unavailable' | 'timeout' | 'unknown';
}

export interface LocationUpdate {
  id: string;
  userId: string;
  workOrderId?: string;
  location: LocationData;
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface LocationPermissionStatus {
  state: 'granted' | 'denied' | 'prompt';
  available: boolean;
  accuracyAuthorization?: 'full' | 'reduced';
}

export interface LocationServiceConfig {
  enableHighAccuracy: boolean;
  timeout: number;
  maximumAge: number;
  updateInterval: number;
  backgroundTracking: boolean;
  persistLocation: boolean;
  autoStart: boolean;
}

export interface LocationBounds {
  northeast: LocationData;
  southwest: LocationData;
}

export interface LocationHistory {
  userId: string;
  locations: LocationUpdate[];
  totalDistance: number;
  startTime: Date;
  endTime: Date;
}

export type LocationSource = 'gps' | 'network' | 'passive' | 'manual';
