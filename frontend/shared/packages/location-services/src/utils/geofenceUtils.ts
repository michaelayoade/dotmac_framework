/**
 * Geofence utility functions
 */

import type { GeofenceConfig, GeofenceEvent, GeofenceStatus } from '../types/geofence';
import type { LocationData } from '../types/location';
import { calculateDistance } from './locationUtils';

/**
 * Create a new geofence configuration
 */
export function createGeofence(config: Partial<GeofenceConfig>): GeofenceConfig {
  const now = new Date();

  return {
    id: config.id || generateGeofenceId(),
    name: config.name || 'Unnamed Geofence',
    type: config.type || 'work_site',
    center: config.center!,
    radius: config.radius || 100,
    active: config.active ?? true,
    workOrderId: config.workOrderId,
    customerId: config.customerId,
    description: config.description,
    metadata: config.metadata || {},
    createdAt: config.createdAt || now,
    updatedAt: now,
  };
}

/**
 * Generate a unique geofence ID
 */
function generateGeofenceId(): string {
  return `geofence_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Check if a location is within a geofence
 */
export function checkGeofenceEntry(location: LocationData, geofence: GeofenceConfig): boolean {
  if (!geofence.active) {
    return false;
  }

  const distance = calculateDistance(location, geofence.center);
  return distance <= geofence.radius;
}

/**
 * Check multiple geofences for a location
 */
export function checkMultipleGeofences(
  location: LocationData,
  geofences: GeofenceConfig[]
): Array<{ geofence: GeofenceConfig; isInside: boolean; distance: number }> {
  return geofences.map((geofence) => ({
    geofence,
    isInside: checkGeofenceEntry(location, geofence),
    distance: calculateDistance(location, geofence.center),
  }));
}

/**
 * Validate geofence configuration
 */
export function validateGeofence(geofence: Partial<GeofenceConfig>): {
  isValid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  if (!geofence.center) {
    errors.push('Geofence center is required');
  } else {
    if (
      !Number.isFinite(geofence.center.latitude) ||
      geofence.center.latitude < -90 ||
      geofence.center.latitude > 90
    ) {
      errors.push('Invalid latitude: must be between -90 and 90');
    }

    if (
      !Number.isFinite(geofence.center.longitude) ||
      geofence.center.longitude < -180 ||
      geofence.center.longitude > 180
    ) {
      errors.push('Invalid longitude: must be between -180 and 180');
    }
  }

  if (!geofence.radius || geofence.radius <= 0) {
    errors.push('Radius must be greater than 0');
  } else if (geofence.radius > 10000) {
    errors.push('Radius cannot exceed 10,000 meters');
  }

  if (!geofence.name || geofence.name.trim().length === 0) {
    errors.push('Geofence name is required');
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Calculate geofence coverage area in square meters
 */
export function calculateGeofenceArea(geofence: GeofenceConfig): number {
  return Math.PI * Math.pow(geofence.radius, 2);
}

/**
 * Check if two geofences overlap
 */
export function checkGeofenceOverlap(
  geofence1: GeofenceConfig,
  geofence2: GeofenceConfig
): boolean {
  const distance = calculateDistance(geofence1.center, geofence2.center);
  const combinedRadius = geofence1.radius + geofence2.radius;
  return distance < combinedRadius;
}

/**
 * Find overlapping geofences in a list
 */
export function findOverlappingGeofences(
  geofences: GeofenceConfig[]
): Array<{ geofence1: GeofenceConfig; geofence2: GeofenceConfig; overlap: number }> {
  const overlaps: Array<{ geofence1: GeofenceConfig; geofence2: GeofenceConfig; overlap: number }> =
    [];

  for (let i = 0; i < geofences.length; i++) {
    for (let j = i + 1; j < geofences.length; j++) {
      const geofence1 = geofences[i];
      const geofence2 = geofences[j];

      if (checkGeofenceOverlap(geofence1, geofence2)) {
        const distance = calculateDistance(geofence1.center, geofence2.center);
        const combinedRadius = geofence1.radius + geofence2.radius;
        const overlap = combinedRadius - distance;

        overlaps.push({ geofence1, geofence2, overlap });
      }
    }
  }

  return overlaps;
}

/**
 * Create a geofence event
 */
export function createGeofenceEvent(
  geofenceId: string,
  userId: string,
  eventType: 'enter' | 'exit' | 'dwell',
  location: LocationData,
  options?: {
    workOrderId?: string;
    duration?: number;
    metadata?: Record<string, any>;
  }
): GeofenceEvent {
  return {
    id: `event_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
    geofenceId,
    userId,
    workOrderId: options?.workOrderId,
    eventType,
    location,
    timestamp: new Date(),
    duration: options?.duration,
    metadata: options?.metadata || {},
  };
}

/**
 * Calculate dwell time for a user in a geofence
 */
export function calculateDwellTime(
  events: GeofenceEvent[],
  geofenceId: string,
  userId: string
): number {
  const relevantEvents = events
    .filter((event) => event.geofenceId === geofenceId && event.userId === userId)
    .sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());

  let totalDwellTime = 0;
  let entryTime: Date | null = null;

  for (const event of relevantEvents) {
    if (event.eventType === 'enter') {
      entryTime = event.timestamp;
    } else if (event.eventType === 'exit' && entryTime) {
      totalDwellTime += event.timestamp.getTime() - entryTime.getTime();
      entryTime = null;
    }
  }

  // If still inside (no exit event after last entry)
  if (entryTime) {
    totalDwellTime += Date.now() - entryTime.getTime();
  }

  return totalDwellTime; // in milliseconds
}

/**
 * Get geofences by type
 */
export function getGeofencesByType(
  geofences: GeofenceConfig[],
  type: GeofenceConfig['type']
): GeofenceConfig[] {
  return geofences.filter((geofence) => geofence.type === type);
}

/**
 * Get active geofences
 */
export function getActiveGeofences(geofences: GeofenceConfig[]): GeofenceConfig[] {
  return geofences.filter((geofence) => geofence.active);
}

/**
 * Sort geofences by distance from a location
 */
export function sortGeofencesByDistance(
  geofences: GeofenceConfig[],
  location: LocationData
): Array<{ geofence: GeofenceConfig; distance: number }> {
  return geofences
    .map((geofence) => ({
      geofence,
      distance: calculateDistance(location, geofence.center),
    }))
    .sort((a, b) => a.distance - b.distance);
}

/**
 * Find nearest geofence to a location
 */
export function findNearestGeofence(
  geofences: GeofenceConfig[],
  location: LocationData
): { geofence: GeofenceConfig; distance: number } | null {
  if (geofences.length === 0) {
    return null;
  }

  const sorted = sortGeofencesByDistance(geofences, location);
  return sorted[0];
}

/**
 * Check if a location is within any geofence from a list
 */
export function isLocationInAnyGeofence(
  location: LocationData,
  geofences: GeofenceConfig[]
): boolean {
  return geofences.some((geofence) => checkGeofenceEntry(location, geofence));
}

/**
 * Get all geofences containing a location
 */
export function getContainingGeofences(
  location: LocationData,
  geofences: GeofenceConfig[]
): GeofenceConfig[] {
  return geofences.filter((geofence) => checkGeofenceEntry(location, geofence));
}

/**
 * Create a buffer zone around a geofence
 */
export function createGeofenceBuffer(
  geofence: GeofenceConfig,
  bufferDistance: number
): GeofenceConfig {
  return createGeofence({
    ...geofence,
    id: `${geofence.id}_buffer`,
    name: `${geofence.name} (Buffer)`,
    radius: geofence.radius + bufferDistance,
    metadata: {
      ...geofence.metadata,
      isBuffer: true,
      originalGeofenceId: geofence.id,
      bufferDistance,
    },
  });
}

/**
 * Merge overlapping geofences into a single geofence
 */
export function mergeGeofences(
  geofences: GeofenceConfig[],
  name: string = 'Merged Geofence'
): GeofenceConfig {
  if (geofences.length === 0) {
    throw new Error('Cannot merge empty geofences array');
  }

  if (geofences.length === 1) {
    return { ...geofences[0] };
  }

  // Calculate center point
  const centerLat = geofences.reduce((sum, gf) => sum + gf.center.latitude, 0) / geofences.length;
  const centerLng = geofences.reduce((sum, gf) => sum + gf.center.longitude, 0) / geofences.length;

  const center: LocationData = {
    latitude: centerLat,
    longitude: centerLng,
    timestamp: Date.now(),
  };

  // Calculate radius to encompass all geofences
  const maxDistance = Math.max(
    ...geofences.map((gf) => calculateDistance(center, gf.center) + gf.radius)
  );

  return createGeofence({
    name,
    center,
    radius: maxDistance,
    type: 'service_area',
    metadata: {
      isMerged: true,
      originalGeofenceIds: geofences.map((gf) => gf.id),
      mergedCount: geofences.length,
    },
  });
}
