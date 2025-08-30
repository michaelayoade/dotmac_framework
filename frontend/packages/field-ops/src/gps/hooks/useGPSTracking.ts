import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from '@dotmac/headless';
import { LocationService } from '../locationService';
import type {
  GPSLocation,
  LocationUpdate,
  GeoFence,
  GeoFenceEvent,
  LocationTrackingSettings,
  GPSPermissionStatus,
  LocationServiceStatus
} from '../types';

interface UseGPSTrackingOptions {
  settings?: Partial<LocationTrackingSettings>;
  autoStart?: boolean;
  workOrderId?: string;
}

interface UseGPSTrackingReturn {
  // Status
  isTracking: boolean;
  permissionStatus: GPSPermissionStatus | null;
  serviceStatus: LocationServiceStatus | null;
  error: string | null;

  // Location data
  currentLocation: GPSLocation | null;
  locationHistory: LocationUpdate[];
  lastUpdate: Date | null;

  // Controls
  startTracking: () => Promise<void>;
  stopTracking: () => void;
  getCurrentLocation: () => Promise<GPSLocation>;
  requestPermissions: () => Promise<GPSPermissionStatus>;

  // Settings
  updateSettings: (settings: Partial<LocationTrackingSettings>) => void;
  settings: LocationTrackingSettings;

  // Geofences
  geoFences: GeoFence[];
  addGeoFence: (geoFence: GeoFence) => void;
  removeGeoFence: (geoFenceId: string) => void;

  // Events
  onLocationUpdate: (callback: (location: LocationUpdate) => void) => () => void;
  onGeoFenceEnter: (callback: (event: GeoFenceEvent) => void) => () => void;
  onGeoFenceExit: (callback: (event: GeoFenceEvent) => void) => () => void;

  // Utilities
  calculateDistance: (coord1: GPSLocation, coord2: GPSLocation) => number;
  calculateBearing: (from: GPSLocation, to: GPSLocation) => number;
}

const DEFAULT_SETTINGS: LocationTrackingSettings = {
  enabled: true,
  accuracy: 'high',
  updateInterval: 5000,
  backgroundTracking: true,
  geoFenceRadius: 100,
  maxLocationAge: 60000
};

export function useGPSTracking(options: UseGPSTrackingOptions = {}): UseGPSTrackingReturn {
  const { settings: settingsOverride = {}, autoStart = false, workOrderId } = options;
  const { user } = useAuth();

  const [settings, setSettings] = useState<LocationTrackingSettings>({
    ...DEFAULT_SETTINGS,
    ...settingsOverride
  });

  const [isTracking, setIsTracking] = useState(false);
  const [permissionStatus, setPermissionStatus] = useState<GPSPermissionStatus | null>(null);
  const [serviceStatus, setServiceStatus] = useState<LocationServiceStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [currentLocation, setCurrentLocation] = useState<GPSLocation | null>(null);
  const [locationHistory, setLocationHistory] = useState<LocationUpdate[]>([]);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);
  const [geoFences, setGeoFences] = useState<GeoFence[]>([]);

  const locationServiceRef = useRef<LocationService | null>(null);

  // Initialize location service
  useEffect(() => {
    locationServiceRef.current = new LocationService(settings);

    // Setup event listeners
    const service = locationServiceRef.current;

    service.addEventListener('locationUpdate', (locationUpdate: LocationUpdate) => {
      setCurrentLocation(locationUpdate.location);
      setLocationHistory(prev => [...prev.slice(-999), locationUpdate]); // Keep last 1000 locations
      setLastUpdate(new Date());
      setError(null);
    });

    service.addEventListener('error', (errorData: any) => {
      setError(errorData.message || 'Location service error');
      console.error('GPS tracking error:', errorData);
    });

    service.addEventListener('permissionChange', (status: GPSPermissionStatus) => {
      setPermissionStatus(status);
    });

    service.addEventListener('geoFenceEnter', (event: GeoFenceEvent) => {
      console.log('Entered geofence:', event);
      // Trigger haptic feedback if available
      if ('vibrate' in navigator) {
        navigator.vibrate([200, 100, 200]);
      }
    });

    service.addEventListener('geoFenceExit', (event: GeoFenceEvent) => {
      console.log('Exited geofence:', event);
      if ('vibrate' in navigator) {
        navigator.vibrate(100);
      }
    });

    // Check initial permissions
    service.checkPermissions().then(setPermissionStatus);

    // Update service status
    const updateServiceStatus = () => {
      setServiceStatus(service.getServiceStatus());
    };

    updateServiceStatus();
    const statusInterval = setInterval(updateServiceStatus, 10000);

    return () => {
      service.stopTracking();
      clearInterval(statusInterval);
    };
  }, [settings]);

  // Auto-start tracking if enabled
  useEffect(() => {
    if (autoStart && user?.id && permissionStatus?.granted) {
      startTracking();
    }
  }, [autoStart, user?.id, permissionStatus]);

  // Control functions
  const startTracking = useCallback(async () => {
    if (!user?.id || !locationServiceRef.current) {
      throw new Error('User not authenticated or location service not initialized');
    }

    try {
      setError(null);
      await locationServiceRef.current.startTracking(user.id, workOrderId);
      setIsTracking(true);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start tracking';
      setError(errorMessage);
      throw err;
    }
  }, [user?.id, workOrderId]);

  const stopTracking = useCallback(() => {
    if (locationServiceRef.current) {
      locationServiceRef.current.stopTracking();
      setIsTracking(false);
    }
  }, []);

  const getCurrentLocation = useCallback(async (): Promise<GPSLocation> => {
    if (!locationServiceRef.current) {
      throw new Error('Location service not initialized');
    }

    try {
      setError(null);
      const location = await locationServiceRef.current.getCurrentLocation();
      setCurrentLocation(location);
      setLastUpdate(new Date());
      return location;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get current location';
      setError(errorMessage);
      throw err;
    }
  }, []);

  const requestPermissions = useCallback(async (): Promise<GPSPermissionStatus> => {
    if (!locationServiceRef.current) {
      throw new Error('Location service not initialized');
    }

    const status = await locationServiceRef.current.requestPermissions();
    setPermissionStatus(status);
    return status;
  }, []);

  // Settings management
  const updateSettings = useCallback((newSettings: Partial<LocationTrackingSettings>) => {
    setSettings(prev => {
      const updated = { ...prev, ...newSettings };
      if (locationServiceRef.current) {
        locationServiceRef.current.updateSettings(newSettings);
      }
      return updated;
    });
  }, []);

  // Geofence management
  const addGeoFence = useCallback((geoFence: GeoFence) => {
    if (locationServiceRef.current) {
      locationServiceRef.current.addGeoFence(geoFence);
      setGeoFences(locationServiceRef.current.getGeoFences());
    }
  }, []);

  const removeGeoFence = useCallback((geoFenceId: string) => {
    if (locationServiceRef.current) {
      locationServiceRef.current.removeGeoFence(geoFenceId);
      setGeoFences(locationServiceRef.current.getGeoFences());
    }
  }, []);

  // Event subscription helpers
  const onLocationUpdate = useCallback((callback: (location: LocationUpdate) => void) => {
    if (locationServiceRef.current) {
      locationServiceRef.current.addEventListener('locationUpdate', callback);

      return () => {
        if (locationServiceRef.current) {
          locationServiceRef.current.removeEventListener('locationUpdate', callback);
        }
      };
    }
    return () => {};
  }, []);

  const onGeoFenceEnter = useCallback((callback: (event: GeoFenceEvent) => void) => {
    if (locationServiceRef.current) {
      locationServiceRef.current.addEventListener('geoFenceEnter', callback);

      return () => {
        if (locationServiceRef.current) {
          locationServiceRef.current.removeEventListener('geoFenceEnter', callback);
        }
      };
    }
    return () => {};
  }, []);

  const onGeoFenceExit = useCallback((callback: (event: GeoFenceEvent) => void) => {
    if (locationServiceRef.current) {
      locationServiceRef.current.addEventListener('geoFenceExit', callback);

      return () => {
        if (locationServiceRef.current) {
          locationServiceRef.current.removeEventListener('geoFenceExit', callback);
        }
      };
    }
    return () => {};
  }, []);

  // Utility functions
  const calculateDistance = useCallback((coord1: GPSLocation, coord2: GPSLocation): number => {
    if (!locationServiceRef.current) return 0;
    return locationServiceRef.current.calculateDistance(coord1, coord2);
  }, []);

  const calculateBearing = useCallback((from: GPSLocation, to: GPSLocation): number => {
    if (!locationServiceRef.current) return 0;
    return locationServiceRef.current.calculateBearing(from, to);
  }, []);

  // Update tracking status based on service
  useEffect(() => {
    const checkTrackingStatus = () => {
      if (locationServiceRef.current) {
        setIsTracking(locationServiceRef.current.isTrackingActive());
      }
    };

    const interval = setInterval(checkTrackingStatus, 1000);
    return () => clearInterval(interval);
  }, []);

  return {
    // Status
    isTracking,
    permissionStatus,
    serviceStatus,
    error,

    // Location data
    currentLocation,
    locationHistory,
    lastUpdate,

    // Controls
    startTracking,
    stopTracking,
    getCurrentLocation,
    requestPermissions,

    // Settings
    updateSettings,
    settings,

    // Geofences
    geoFences,
    addGeoFence,
    removeGeoFence,

    // Events
    onLocationUpdate,
    onGeoFenceEnter,
    onGeoFenceExit,

    // Utilities
    calculateDistance,
    calculateBearing
  };
}
