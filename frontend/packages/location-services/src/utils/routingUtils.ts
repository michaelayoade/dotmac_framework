/**
 * Routing utility functions
 */

import type {
  RouteConfig,
  RouteWaypoint,
  RoutingResult,
  RouteOptimization,
  TravelMode
} from '../types/routing';
import type { LocationData } from '../types/location';
import { calculateDistance, findNearestLocation } from './locationUtils';

/**
 * Calculate total distance for a route
 */
export function calculateRouteDistance(waypoints: LocationData[]): number {
  if (waypoints.length < 2) {
    return 0;
  }

  let totalDistance = 0;
  for (let i = 0; i < waypoints.length - 1; i++) {
    totalDistance += calculateDistance(waypoints[i], waypoints[i + 1]);
  }

  return totalDistance / 1000; // Convert to kilometers
}

/**
 * Estimate travel time based on distance and travel mode
 */
export function estimateTravelTime(
  distanceKm: number,
  travelMode: TravelMode = 'driving'
): number {
  const speedMap: Record<TravelMode, number> = {
    driving: 50, // km/h average city driving
    walking: 5,  // km/h
    cycling: 15, // km/h
    transit: 25, // km/h average including stops
  };

  const speed = speedMap[travelMode];
  const timeHours = distanceKm / speed;
  return Math.round(timeHours * 60); // Return minutes
}

/**
 * Optimize route using nearest neighbor algorithm
 */
export function optimizeRoute(waypoints: LocationData[]): {
  optimizedWaypoints: LocationData[];
  distanceSaved: number;
  timeSaved: number;
} {
  if (waypoints.length <= 2) {
    return {
      optimizedWaypoints: [...waypoints],
      distanceSaved: 0,
      timeSaved: 0,
    };
  }

  const originalDistance = calculateRouteDistance(waypoints);
  const optimized = nearestNeighborOptimization(waypoints);
  const optimizedDistance = calculateRouteDistance(optimized);

  const distanceSaved = originalDistance - optimizedDistance;
  const timeSaved = estimateTravelTime(distanceSaved);

  return {
    optimizedWaypoints: optimized,
    distanceSaved,
    timeSaved,
  };
}

/**
 * Nearest neighbor route optimization algorithm
 */
function nearestNeighborOptimization(waypoints: LocationData[]): LocationData[] {
  if (waypoints.length <= 2) {
    return [...waypoints];
  }

  const optimized: LocationData[] = [];
  const remaining = [...waypoints];

  // Start with the first waypoint
  let current = remaining.shift()!;
  optimized.push(current);

  while (remaining.length > 0) {
    const nearest = findNearestLocation(current, remaining);
    if (nearest) {
      current = remaining.splice(nearest.index, 1)[0];
      optimized.push(current);
    }
  }

  return optimized;
}

/**
 * Find shortest path using a simple greedy algorithm
 */
export function findShortestPath(
  start: LocationData,
  waypoints: LocationData[],
  end?: LocationData
): LocationData[] {
  const allWaypoints = [...waypoints];
  if (end) {
    allWaypoints.push(end);
  }

  const path = [start];
  const remaining = [...allWaypoints];
  let current = start;

  while (remaining.length > 0) {
    const nearest = findNearestLocation(current, remaining);
    if (nearest) {
      current = remaining.splice(nearest.index, 1)[0];
      path.push(current);
    }
  }

  return path;
}

/**
 * Calculate route statistics
 */
export function calculateRouteStats(waypoints: LocationData[], travelMode: TravelMode = 'driving'): {
  totalDistance: number;
  totalTime: number;
  segments: Array<{
    from: LocationData;
    to: LocationData;
    distance: number;
    time: number;
  }>;
} {
  const segments = [];
  let totalDistance = 0;
  let totalTime = 0;

  for (let i = 0; i < waypoints.length - 1; i++) {
    const from = waypoints[i];
    const to = waypoints[i + 1];
    const distance = calculateDistance(from, to) / 1000; // km
    const time = estimateTravelTime(distance, travelMode);

    segments.push({ from, to, distance, time });
    totalDistance += distance;
    totalTime += time;
  }

  return {
    totalDistance,
    totalTime,
    segments,
  };
}

/**
 * Generate route waypoints with timing information
 */
export function generateTimedWaypoints(
  waypoints: LocationData[],
  startTime: Date = new Date(),
  travelMode: TravelMode = 'driving'
): RouteWaypoint[] {
  const timedWaypoints: RouteWaypoint[] = [];
  let currentTime = new Date(startTime);

  for (let i = 0; i < waypoints.length; i++) {
    const waypoint = waypoints[i];

    timedWaypoints.push({
      id: `waypoint_${i}`,
      location: waypoint,
      name: `Stop ${i + 1}`,
      estimatedDuration: i === waypoints.length - 1 ? 0 : 30, // 30 minutes default stop time
    });

    // Calculate travel time to next waypoint
    if (i < waypoints.length - 1) {
      const distance = calculateDistance(waypoint, waypoints[i + 1]) / 1000;
      const travelTime = estimateTravelTime(distance, travelMode);
      const stopTime = 30; // minutes

      currentTime = new Date(currentTime.getTime() + (travelTime + stopTime) * 60000);
    }
  }

  return timedWaypoints;
}

/**
 * Calculate fuel consumption estimate
 */
export function estimateFuelConsumption(
  distanceKm: number,
  vehicleType: 'car' | 'truck' | 'van' | 'motorcycle' = 'car'
): number {
  const fuelEfficiencyMap = {
    car: 8.0,        // L/100km
    truck: 25.0,     // L/100km
    van: 12.0,       // L/100km
    motorcycle: 4.0, // L/100km
  };

  const efficiency = fuelEfficiencyMap[vehicleType];
  return (distanceKm * efficiency) / 100;
}

/**
 * Calculate route cost estimate
 */
export function estimateRouteCost(
  distanceKm: number,
  travelMode: TravelMode,
  options?: {
    fuelPricePerLiter?: number;
    vehicleType?: 'car' | 'truck' | 'van' | 'motorcycle';
    tollCosts?: number;
    parkingCosts?: number;
  }
): number {
  let totalCost = 0;

  if (travelMode === 'driving') {
    const fuelPricePerLiter = options?.fuelPricePerLiter || 1.50; // Default price
    const vehicleType = options?.vehicleType || 'car';

    const fuelConsumption = estimateFuelConsumption(distanceKm, vehicleType);
    const fuelCost = fuelConsumption * fuelPricePerLiter;

    totalCost += fuelCost;
    totalCost += options?.tollCosts || 0;
    totalCost += options?.parkingCosts || 0;
  } else if (travelMode === 'transit') {
    // Estimate transit costs (placeholder)
    totalCost = distanceKm * 0.20; // $0.20 per km
  } else if (travelMode === 'cycling' || travelMode === 'walking') {
    totalCost = 0; // Free!
  }

  return Math.round(totalCost * 100) / 100; // Round to 2 decimal places
}

/**
 * Compare two routes
 */
export function compareRoutes(
  route1: LocationData[],
  route2: LocationData[],
  travelMode: TravelMode = 'driving'
): {
  route1Stats: ReturnType<typeof calculateRouteStats>;
  route2Stats: ReturnType<typeof calculateRouteStats>;
  recommendation: 'route1' | 'route2';
  comparison: {
    distanceDifference: number;
    timeDifference: number;
    efficiencyGain: number;
  };
} {
  const route1Stats = calculateRouteStats(route1, travelMode);
  const route2Stats = calculateRouteStats(route2, travelMode);

  const distanceDifference = route1Stats.totalDistance - route2Stats.totalDistance;
  const timeDifference = route1Stats.totalTime - route2Stats.totalTime;

  // Recommend route2 if it's significantly better
  const recommendation = (distanceDifference > 0.5 || timeDifference > 5) ? 'route2' : 'route1';

  const efficiencyGain = recommendation === 'route2'
    ? ((distanceDifference / route1Stats.totalDistance) * 100)
    : ((Math.abs(distanceDifference) / route2Stats.totalDistance) * 100);

  return {
    route1Stats,
    route2Stats,
    recommendation,
    comparison: {
      distanceDifference,
      timeDifference,
      efficiencyGain,
    },
  };
}

/**
 * Generate alternative routes (simplified version)
 */
export function generateAlternativeRoutes(
  waypoints: LocationData[],
  count: number = 2
): LocationData[][] {
  if (waypoints.length < 3 || count < 1) {
    return [waypoints];
  }

  const routes: LocationData[][] = [];

  // Original route
  routes.push([...waypoints]);

  // Generate variations by reordering middle waypoints
  for (let i = 1; i < Math.min(count, 4); i++) {
    const variation = [...waypoints];

    // Simple variation: reverse middle section
    if (variation.length >= 4) {
      const middle = variation.slice(1, -1);
      middle.reverse();
      const variationRoute = [variation[0], ...middle, variation[variation.length - 1]];
      routes.push(variationRoute);
    }
  }

  return routes.slice(0, count + 1);
}

/**
 * Check if route is valid
 */
export function validateRoute(waypoints: LocationData[]): {
  isValid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  if (waypoints.length < 2) {
    errors.push('Route must have at least 2 waypoints');
  }

  waypoints.forEach((waypoint, index) => {
    if (!waypoint.latitude || !waypoint.longitude) {
      errors.push(`Waypoint ${index + 1} has invalid coordinates`);
    }

    if (waypoint.latitude < -90 || waypoint.latitude > 90) {
      errors.push(`Waypoint ${index + 1} has invalid latitude`);
    }

    if (waypoint.longitude < -180 || waypoint.longitude > 180) {
      errors.push(`Waypoint ${index + 1} has invalid longitude`);
    }
  });

  // Check for duplicate waypoints
  for (let i = 0; i < waypoints.length - 1; i++) {
    for (let j = i + 1; j < waypoints.length; j++) {
      if (calculateDistance(waypoints[i], waypoints[j]) < 10) { // 10 meters
        errors.push(`Waypoints ${i + 1} and ${j + 1} are too close together`);
      }
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}

/**
 * Split route into segments of maximum distance
 */
export function splitRouteByDistance(
  waypoints: LocationData[],
  maxSegmentDistance: number // in kilometers
): LocationData[][] {
  if (waypoints.length < 2) {
    return [waypoints];
  }

  const segments: LocationData[][] = [];
  let currentSegment: LocationData[] = [waypoints[0]];
  let currentDistance = 0;

  for (let i = 1; i < waypoints.length; i++) {
    const segmentDistance = calculateDistance(waypoints[i - 1], waypoints[i]);

    if (currentDistance + segmentDistance > maxSegmentDistance * 1000) {
      // Start new segment
      segments.push([...currentSegment]);
      currentSegment = [waypoints[i - 1], waypoints[i]];
      currentDistance = segmentDistance;
    } else {
      currentSegment.push(waypoints[i]);
      currentDistance += segmentDistance;
    }
  }

  // Add the last segment
  if (currentSegment.length > 1) {
    segments.push(currentSegment);
  }

  return segments;
}
