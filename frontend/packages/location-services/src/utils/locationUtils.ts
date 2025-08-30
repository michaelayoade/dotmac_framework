/**
 * Location utility functions
 */

import type { LocationData, LocationError } from '../types/location';

/**
 * Calculate the distance between two locations using the Haversine formula
 */
export function calculateDistance(
  location1: LocationData,
  location2: LocationData
): number {
  const R = 6371e3; // Earth's radius in meters

  const φ1 = (location1.latitude * Math.PI) / 180;
  const φ2 = (location2.latitude * Math.PI) / 180;
  const Δφ = ((location2.latitude - location1.latitude) * Math.PI) / 180;
  const Δλ = ((location2.longitude - location1.longitude) * Math.PI) / 180;

  const a =
    Math.sin(Δφ / 2) * Math.sin(Δφ / 2) +
    Math.cos(φ1) * Math.cos(φ2) * Math.sin(Δλ / 2) * Math.sin(Δλ / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));

  return R * c; // Distance in meters
}

/**
 * Calculate the bearing (direction) between two locations
 */
export function calculateBearing(
  from: LocationData,
  to: LocationData
): number {
  const φ1 = (from.latitude * Math.PI) / 180;
  const φ2 = (to.latitude * Math.PI) / 180;
  const Δλ = ((to.longitude - from.longitude) * Math.PI) / 180;

  const y = Math.sin(Δλ) * Math.cos(φ2);
  const x =
    Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);

  const θ = Math.atan2(y, x);
  return ((θ * 180) / Math.PI + 360) % 360; // Bearing in degrees
}

/**
 * Calculate the midpoint between two locations
 */
export function calculateMidpoint(
  location1: LocationData,
  location2: LocationData
): LocationData {
  const φ1 = (location1.latitude * Math.PI) / 180;
  const φ2 = (location2.latitude * Math.PI) / 180;
  const Δλ = ((location2.longitude - location1.longitude) * Math.PI) / 180;
  const λ1 = (location1.longitude * Math.PI) / 180;

  const Bx = Math.cos(φ2) * Math.cos(Δλ);
  const By = Math.cos(φ2) * Math.sin(Δλ);

  const φ3 = Math.atan2(
    Math.sin(φ1) + Math.sin(φ2),
    Math.sqrt((Math.cos(φ1) + Bx) * (Math.cos(φ1) + Bx) + By * By)
  );
  const λ3 = λ1 + Math.atan2(By, Math.cos(φ1) + Bx);

  return {
    latitude: (φ3 * 180) / Math.PI,
    longitude: (λ3 * 180) / Math.PI,
    timestamp: Date.now(),
  };
}

/**
 * Format coordinates as a human-readable string
 */
export function formatCoordinates(
  location: LocationData,
  precision: number = 6
): string {
  return `${location.latitude.toFixed(precision)}, ${location.longitude.toFixed(precision)}`;
}

/**
 * Parse coordinates from a string
 */
export function parseCoordinates(coordinateString: string): LocationData {
  const parts = coordinateString.split(',').map(s => parseFloat(s.trim()));

  if (parts.length !== 2 || parts.some(isNaN)) {
    throw new Error('Invalid coordinate string format. Expected "lat, lng"');
  }

  const [latitude, longitude] = parts;

  if (!validateCoordinates(latitude, longitude)) {
    throw new Error('Invalid coordinate values');
  }

  return {
    latitude,
    longitude,
    timestamp: Date.now(),
  };
}

/**
 * Validate if coordinates are within valid ranges
 */
export function validateCoordinates(latitude: number, longitude: number): boolean {
  return (
    !isNaN(latitude) &&
    !isNaN(longitude) &&
    latitude >= -90 &&
    latitude <= 90 &&
    longitude >= -180 &&
    longitude <= 180
  );
}

/**
 * Check if a location is within a specified radius of another location
 */
export function isWithinRadius(
  center: LocationData,
  location: LocationData,
  radiusMeters: number
): boolean {
  const distance = calculateDistance(center, location);
  return distance <= radiusMeters;
}

/**
 * Find the nearest location from an array of locations
 */
export function findNearestLocation(
  target: LocationData,
  locations: LocationData[]
): { location: LocationData; distance: number; index: number } | null {
  if (locations.length === 0) {
    return null;
  }

  let nearestIndex = 0;
  let nearestDistance = calculateDistance(target, locations[0]);

  for (let i = 1; i < locations.length; i++) {
    const distance = calculateDistance(target, locations[i]);
    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearestIndex = i;
    }
  }

  return {
    location: locations[nearestIndex],
    distance: nearestDistance,
    index: nearestIndex,
  };
}

/**
 * Filter locations within a specified radius
 */
export function getLocationsWithinRadius(
  center: LocationData,
  locations: LocationData[],
  radiusMeters: number
): Array<{ location: LocationData; distance: number; index: number }> {
  return locations
    .map((location, index) => ({
      location,
      distance: calculateDistance(center, location),
      index,
    }))
    .filter(item => item.distance <= radiusMeters)
    .sort((a, b) => a.distance - b.distance);
}

/**
 * Calculate the center point of multiple locations
 */
export function calculateCenterPoint(locations: LocationData[]): LocationData {
  if (locations.length === 0) {
    throw new Error('Cannot calculate center of empty locations array');
  }

  if (locations.length === 1) {
    return { ...locations[0] };
  }

  // Convert to Cartesian coordinates
  let x = 0;
  let y = 0;
  let z = 0;

  for (const location of locations) {
    const φ = (location.latitude * Math.PI) / 180;
    const λ = (location.longitude * Math.PI) / 180;

    x += Math.cos(φ) * Math.cos(λ);
    y += Math.cos(φ) * Math.sin(λ);
    z += Math.sin(φ);
  }

  const total = locations.length;
  x /= total;
  y /= total;
  z /= total;

  // Convert back to latitude/longitude
  const λ = Math.atan2(y, x);
  const φ = Math.atan2(z, Math.sqrt(x * x + y * y));

  return {
    latitude: (φ * 180) / Math.PI,
    longitude: (λ * 180) / Math.PI,
    timestamp: Date.now(),
  };
}

/**
 * Calculate bounding box for multiple locations
 */
export function calculateBoundingBox(locations: LocationData[]): {
  northeast: LocationData;
  southwest: LocationData;
} {
  if (locations.length === 0) {
    throw new Error('Cannot calculate bounding box of empty locations array');
  }

  let minLat = locations[0].latitude;
  let maxLat = locations[0].latitude;
  let minLng = locations[0].longitude;
  let maxLng = locations[0].longitude;

  for (const location of locations) {
    minLat = Math.min(minLat, location.latitude);
    maxLat = Math.max(maxLat, location.latitude);
    minLng = Math.min(minLng, location.longitude);
    maxLng = Math.max(maxLng, location.longitude);
  }

  return {
    northeast: {
      latitude: maxLat,
      longitude: maxLng,
      timestamp: Date.now(),
    },
    southwest: {
      latitude: minLat,
      longitude: minLng,
      timestamp: Date.now(),
    },
  };
}

/**
 * Convert bearing from degrees to cardinal direction
 */
export function bearingToCardinal(bearing: number): string {
  const cardinals = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];
  const index = Math.round(bearing / 22.5) % 16;
  return cardinals[index];
}

/**
 * Generate a random location within a radius of a center point
 */
export function generateRandomLocationWithinRadius(
  center: LocationData,
  radiusMeters: number
): LocationData {
  const earthRadius = 6371e3; // Earth's radius in meters

  // Random distance and angle
  const distance = Math.random() * radiusMeters;
  const angle = Math.random() * 2 * Math.PI;

  // Convert center to radians
  const φ1 = (center.latitude * Math.PI) / 180;
  const λ1 = (center.longitude * Math.PI) / 180;

  // Calculate new point
  const φ2 = Math.asin(
    Math.sin(φ1) * Math.cos(distance / earthRadius) +
    Math.cos(φ1) * Math.sin(distance / earthRadius) * Math.cos(angle)
  );

  const λ2 = λ1 + Math.atan2(
    Math.sin(angle) * Math.sin(distance / earthRadius) * Math.cos(φ1),
    Math.cos(distance / earthRadius) - Math.sin(φ1) * Math.sin(φ2)
  );

  return {
    latitude: (φ2 * 180) / Math.PI,
    longitude: (λ2 * 180) / Math.PI,
    timestamp: Date.now(),
  };
}

/**
 * Check if location data is valid and recent
 */
export function isLocationValid(
  location: LocationData,
  maxAgeMs: number = 60000
): boolean {
  if (!validateCoordinates(location.latitude, location.longitude)) {
    return false;
  }

  if (location.timestamp && (Date.now() - location.timestamp) > maxAgeMs) {
    return false;
  }

  return true;
}

/**
 * Get accuracy level description
 */
export function getAccuracyLevel(accuracy?: number): string {
  if (!accuracy) return 'Unknown';

  if (accuracy <= 5) return 'Excellent';
  if (accuracy <= 10) return 'Good';
  if (accuracy <= 50) return 'Fair';
  if (accuracy <= 100) return 'Poor';
  return 'Very Poor';
}

/**
 * Convert location error to user-friendly message
 */
export function getLocationErrorMessage(error: LocationError): string {
  switch (error.type) {
    case 'permission_denied':
      return 'Location access denied. Please enable location services.';
    case 'position_unavailable':
      return 'Location information is unavailable.';
    case 'timeout':
      return 'Location request timed out. Please try again.';
    default:
      return error.message || 'An unknown location error occurred.';
  }
}
