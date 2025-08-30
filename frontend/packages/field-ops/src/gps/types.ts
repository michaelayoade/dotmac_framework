export interface GPSCoordinates {
  latitude: number;
  longitude: number;
  accuracy: number;
  altitude?: number;
  heading?: number;
  speed?: number;
}

export interface GPSLocation extends GPSCoordinates {
  timestamp: string;
  source: 'gps' | 'network' | 'passive';
}

export interface LocationUpdate {
  id: string;
  workOrderId?: string;
  technicianId: string;
  location: GPSLocation;
  address?: string;
  metadata?: {
    batteryLevel?: number;
    networkType?: string;
    isOnline?: boolean;
  };
}

export interface GeoFence {
  id: string;
  name: string;
  center: GPSCoordinates;
  radius: number; // meters
  type: 'work_site' | 'office' | 'warehouse' | 'restricted';
  workOrderId?: string;
}

export interface GeoFenceEvent {
  id: string;
  geoFenceId: string;
  technicianId: string;
  workOrderId?: string;
  eventType: 'enter' | 'exit';
  location: GPSLocation;
  timestamp: string;
}

export interface LocationTrackingSettings {
  enabled: boolean;
  accuracy: 'low' | 'medium' | 'high';
  updateInterval: number; // milliseconds
  backgroundTracking: boolean;
  geoFenceRadius: number; // default radius for work sites
  maxLocationAge: number; // milliseconds
}

export interface GPSPermissionStatus {
  granted: boolean;
  status: 'granted' | 'denied' | 'prompt' | 'unknown';
  accuracyAuthorization?: 'full' | 'reduced';
}

export interface LocationServiceStatus {
  available: boolean;
  enabled: boolean;
  accuracy: number;
  provider: string;
  lastUpdate?: string;
}

export interface RouteOptimization {
  workOrderIds: string[];
  startLocation?: GPSCoordinates;
  optimizedRoute: {
    workOrderId: string;
    location: GPSCoordinates;
    estimatedArrival: string;
    travelTime: number;
    distance: number;
  }[];
  totalDistance: number;
  totalTime: number;
  optimizedAt: string;
}

export interface LocationHistory {
  technicianId: string;
  date: string;
  locations: LocationUpdate[];
  totalDistance: number;
  workSites: string[];
  timeOnSite: Record<string, number>; // workOrderId -> minutes
}
