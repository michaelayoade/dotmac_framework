/**
 * Routing and navigation type definitions
 */

import type { LocationData } from './location';

export type TravelMode = 'driving' | 'walking' | 'transit' | 'cycling';

export interface RouteWaypoint {
  id: string;
  location: LocationData;
  name?: string;
  address?: string;
  workOrderId?: string;
  estimatedDuration?: number; // minutes
  metadata?: Record<string, any>;
}

export interface RouteConfig {
  id: string;
  name: string;
  waypoints: RouteWaypoint[];
  travelMode: TravelMode;
  optimized: boolean;
  constraints?: RouteConstraints;
  metadata?: Record<string, any>;
  createdAt: Date;
}

export interface RouteConstraints {
  maxDistance?: number; // in kilometers
  maxDuration?: number; // in minutes
  avoidTolls?: boolean;
  avoidHighways?: boolean;
  avoidFerries?: boolean;
  departureTime?: Date;
  arrivalTime?: Date;
  vehicleType?: 'car' | 'truck' | 'motorcycle' | 'van';
  vehicleSpecs?: {
    height?: number; // meters
    width?: number; // meters
    weight?: number; // kg
    axleCount?: number;
  };
}

export interface RoutingResult {
  routeId: string;
  waypoints: RouteWaypoint[];
  totalDistance: number; // kilometers
  totalDuration: number; // minutes
  polyline: string; // encoded polyline
  bounds: {
    northeast: LocationData;
    southwest: LocationData;
  };
  legs: RouteLeg[];
  metadata?: Record<string, any>;
  calculatedAt: Date;
}

export interface RouteLeg {
  startLocation: LocationData;
  endLocation: LocationData;
  distance: number; // kilometers
  duration: number; // minutes
  instructions: RouteInstruction[];
  polyline: string;
}

export interface RouteInstruction {
  text: string;
  distance: number;
  duration: number;
  location: LocationData;
  maneuver?: string;
  turn?: 'left' | 'right' | 'straight' | 'u-turn';
}

export interface RouteOptimization {
  originalRoute: RouteConfig;
  optimizedRoute: RouteConfig;
  improvement: {
    distanceSaved: number; // kilometers
    timeSaved: number; // minutes
    fuelSaved?: number; // liters
    costSaved?: number; // currency units
    efficiencyGain: number; // percentage
  };
  optimizationMethod: string;
  calculatedAt: Date;
}

export interface TrafficInfo {
  routeId: string;
  segments: TrafficSegment[];
  updatedAt: Date;
  nextUpdate?: Date;
}

export interface TrafficSegment {
  startLocation: LocationData;
  endLocation: LocationData;
  congestionLevel: 'low' | 'moderate' | 'heavy' | 'severe';
  speed: number; // km/h
  delay: number; // minutes
  incidents?: TrafficIncident[];
}

export interface TrafficIncident {
  id: string;
  type: 'accident' | 'construction' | 'closure' | 'weather' | 'event';
  severity: 'minor' | 'moderate' | 'major';
  location: LocationData;
  description: string;
  estimatedClearTime?: Date;
}

export interface RouteAlternative {
  routeId: string;
  description: string;
  totalDistance: number;
  totalDuration: number;
  trafficDelay: number;
  advantage: string;
  polyline: string;
}

export interface RoutingPreferences {
  userId: string;
  defaultTravelMode: TravelMode;
  avoidTolls: boolean;
  avoidHighways: boolean;
  preferFastestRoute: boolean;
  fuelEfficiencyWeight: number; // 0-1
  trafficAwareness: boolean;
  autoReroute: boolean;
  voiceGuidance: boolean;
}
