/**
 * Geofence type definitions
 */

import type { LocationData } from './location';

export type GeofenceType =
  | 'work_site'
  | 'service_area'
  | 'customer_location'
  | 'office'
  | 'warehouse'
  | 'restricted_area'
  | 'safety_zone';

export interface GeofenceConfig {
  id: string;
  name: string;
  type: GeofenceType;
  center: LocationData;
  radius: number; // in meters
  active: boolean;
  workOrderId?: string;
  customerId?: string;
  description?: string;
  metadata?: Record<string, any>;
  createdAt: Date;
  updatedAt?: Date;
}

export interface GeofenceEvent {
  id: string;
  geofenceId: string;
  userId: string;
  workOrderId?: string;
  eventType: 'enter' | 'exit' | 'dwell';
  location: LocationData;
  timestamp: Date;
  duration?: number; // for dwell events, in milliseconds
  metadata?: Record<string, any>;
}

export interface GeofenceStatus {
  geofenceId: string;
  userId: string;
  isInside: boolean;
  enteredAt?: Date;
  lastUpdate: Date;
  dwellTime?: number; // in milliseconds
}

export interface GeofenceRule {
  id: string;
  geofenceId: string;
  eventType: 'enter' | 'exit' | 'dwell';
  condition?: {
    minDwellTime?: number;
    userRoles?: string[];
    workOrderTypes?: string[];
    timeWindows?: {
      start: string; // HH:mm format
      end: string;
      days: number[]; // 0-6 (Sun-Sat)
    }[];
  };
  actions: GeofenceAction[];
  active: boolean;
}

export interface GeofenceAction {
  type: 'notification' | 'webhook' | 'email' | 'log' | 'workflow';
  config: Record<string, any>;
}

export interface GeofenceAnalytics {
  geofenceId: string;
  period: {
    start: Date;
    end: Date;
  };
  metrics: {
    totalEntries: number;
    totalExits: number;
    uniqueUsers: number;
    averageDwellTime: number;
    peakHours: number[];
    userActivity: {
      userId: string;
      entries: number;
      totalDwellTime: number;
    }[];
  };
}

export interface GeofenceBatch {
  geofences: GeofenceConfig[];
  userId: string;
  location: LocationData;
  results: {
    geofenceId: string;
    isInside: boolean;
    distance: number;
  }[];
}
