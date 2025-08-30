import type {
  GPSCoordinates,
  GPSLocation,
  LocationUpdate,
  GeoFence,
  GeoFenceEvent,
  LocationTrackingSettings,
  GPSPermissionStatus,
  LocationServiceStatus
} from './types';

export class LocationService {
  private watchId: number | null = null;
  private settings: LocationTrackingSettings;
  private geoFences: GeoFence[] = [];
  private lastKnownLocation: GPSLocation | null = null;
  private locationHistory: LocationUpdate[] = [];
  private eventListeners: Map<string, Function[]> = new Map();
  private isTracking = false;

  constructor(settings: LocationTrackingSettings) {
    this.settings = settings;
    this.initializeEventListeners();
  }

  private initializeEventListeners() {
    this.eventListeners.set('locationUpdate', []);
    this.eventListeners.set('geoFenceEnter', []);
    this.eventListeners.set('geoFenceExit', []);
    this.eventListeners.set('permissionChange', []);
    this.eventListeners.set('error', []);
  }

  // Event management
  addEventListener(event: string, callback: Function) {
    const listeners = this.eventListeners.get(event) || [];
    listeners.push(callback);
    this.eventListeners.set(event, listeners);
  }

  removeEventListener(event: string, callback: Function) {
    const listeners = this.eventListeners.get(event) || [];
    const index = listeners.indexOf(callback);
    if (index > -1) {
      listeners.splice(index, 1);
      this.eventListeners.set(event, listeners);
    }
  }

  private emit(event: string, data: any) {
    const listeners = this.eventListeners.get(event) || [];
    listeners.forEach(callback => callback(data));
  }

  // Permission management
  async checkPermissions(): Promise<GPSPermissionStatus> {
    if (!navigator.geolocation) {
      return { granted: false, status: 'unknown' };
    }

    try {
      const permission = await navigator.permissions.query({ name: 'geolocation' });

      return {
        granted: permission.state === 'granted',
        status: permission.state as 'granted' | 'denied' | 'prompt'
      };
    } catch (error) {
      console.warn('Permission API not supported, trying direct geolocation');

      return new Promise((resolve) => {
        navigator.geolocation.getCurrentPosition(
          () => resolve({ granted: true, status: 'granted' }),
          (error) => {
            if (error.code === error.PERMISSION_DENIED) {
              resolve({ granted: false, status: 'denied' });
            } else {
              resolve({ granted: false, status: 'unknown' });
            }
          },
          { timeout: 5000 }
        );
      });
    }
  }

  async requestPermissions(): Promise<GPSPermissionStatus> {
    const currentStatus = await this.checkPermissions();

    if (currentStatus.granted) {
      return currentStatus;
    }

    return new Promise((resolve) => {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const status: GPSPermissionStatus = { granted: true, status: 'granted' };
          this.emit('permissionChange', status);
          resolve(status);
        },
        (error) => {
          let status: GPSPermissionStatus;

          if (error.code === error.PERMISSION_DENIED) {
            status = { granted: false, status: 'denied' };
          } else {
            status = { granted: false, status: 'unknown' };
          }

          this.emit('permissionChange', status);
          this.emit('error', { type: 'permission', error });
          resolve(status);
        },
        {
          enableHighAccuracy: this.settings.accuracy === 'high',
          timeout: 10000,
          maximumAge: this.settings.maxLocationAge
        }
      );
    });
  }

  // Location tracking
  async startTracking(technicianId: string, workOrderId?: string): Promise<void> {
    if (this.isTracking) {
      console.warn('Location tracking already active');
      return;
    }

    if (!this.settings.enabled) {
      throw new Error('Location tracking is disabled');
    }

    const permissionStatus = await this.requestPermissions();
    if (!permissionStatus.granted) {
      throw new Error('Location permission not granted');
    }

    const options: PositionOptions = {
      enableHighAccuracy: this.settings.accuracy === 'high',
      maximumAge: this.settings.maxLocationAge,
      timeout: 15000
    };

    this.watchId = navigator.geolocation.watchPosition(
      (position) => this.handleLocationUpdate(position, technicianId, workOrderId),
      (error) => this.handleLocationError(error),
      options
    );

    this.isTracking = true;
    console.log('Location tracking started');
  }

  stopTracking(): void {
    if (this.watchId !== null) {
      navigator.geolocation.clearWatch(this.watchId);
      this.watchId = null;
    }

    this.isTracking = false;
    console.log('Location tracking stopped');
  }

  private handleLocationUpdate(
    position: GeolocationPosition,
    technicianId: string,
    workOrderId?: string
  ) {
    const location: GPSLocation = {
      latitude: position.coords.latitude,
      longitude: position.coords.longitude,
      accuracy: position.coords.accuracy,
      altitude: position.coords.altitude || undefined,
      heading: position.coords.heading || undefined,
      speed: position.coords.speed || undefined,
      timestamp: new Date().toISOString(),
      source: 'gps'
    };

    const locationUpdate: LocationUpdate = {
      id: `loc_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      technicianId,
      workOrderId,
      location,
      metadata: {
        isOnline: navigator.onLine,
        networkType: (navigator as any).connection?.effectiveType || 'unknown'
      }
    };

    this.lastKnownLocation = location;
    this.locationHistory.push(locationUpdate);

    // Check geofences
    this.checkGeoFences(locationUpdate);

    // Emit location update
    this.emit('locationUpdate', locationUpdate);

    // Limit history size for memory management
    if (this.locationHistory.length > 1000) {
      this.locationHistory = this.locationHistory.slice(-500);
    }
  }

  private handleLocationError(error: GeolocationPositionError) {
    const errorInfo = {
      type: 'location',
      code: error.code,
      message: error.message,
      timestamp: new Date().toISOString()
    };

    console.error('Location error:', errorInfo);
    this.emit('error', errorInfo);

    // Try to restart tracking after errors (except permission denied)
    if (error.code !== error.PERMISSION_DENIED && this.isTracking) {
      setTimeout(() => {
        if (this.isTracking && this.watchId !== null) {
          this.stopTracking();
          // Restart will be handled by the calling code
        }
      }, 5000);
    }
  }

  // Current location (one-time)
  async getCurrentLocation(): Promise<GPSLocation> {
    const permissionStatus = await this.checkPermissions();
    if (!permissionStatus.granted) {
      throw new Error('Location permission not granted');
    }

    return new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (position) => {
          const location: GPSLocation = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            accuracy: position.coords.accuracy,
            altitude: position.coords.altitude || undefined,
            heading: position.coords.heading || undefined,
            speed: position.coords.speed || undefined,
            timestamp: new Date().toISOString(),
            source: 'gps'
          };

          this.lastKnownLocation = location;
          resolve(location);
        },
        (error) => {
          this.handleLocationError(error);
          reject(error);
        },
        {
          enableHighAccuracy: this.settings.accuracy === 'high',
          timeout: 15000,
          maximumAge: this.settings.maxLocationAge
        }
      );
    });
  }

  // Geofence management
  addGeoFence(geoFence: GeoFence): void {
    this.geoFences.push(geoFence);
  }

  removeGeoFence(geoFenceId: string): void {
    this.geoFences = this.geoFences.filter(gf => gf.id !== geoFenceId);
  }

  getGeoFences(): GeoFence[] {
    return [...this.geoFences];
  }

  private checkGeoFences(locationUpdate: LocationUpdate) {
    this.geoFences.forEach(geoFence => {
      const distance = this.calculateDistance(
        locationUpdate.location,
        geoFence.center
      );

      const wasInside = this.wasInsideGeoFence(geoFence.id);
      const isInside = distance <= geoFence.radius;

      if (!wasInside && isInside) {
        // Entering geofence
        const event: GeoFenceEvent = {
          id: `gf_enter_${Date.now()}`,
          geoFenceId: geoFence.id,
          technicianId: locationUpdate.technicianId,
          workOrderId: locationUpdate.workOrderId,
          eventType: 'enter',
          location: locationUpdate.location,
          timestamp: new Date().toISOString()
        };

        this.emit('geoFenceEnter', event);
      } else if (wasInside && !isInside) {
        // Exiting geofence
        const event: GeoFenceEvent = {
          id: `gf_exit_${Date.now()}`,
          geoFenceId: geoFence.id,
          technicianId: locationUpdate.technicianId,
          workOrderId: locationUpdate.workOrderId,
          eventType: 'exit',
          location: locationUpdate.location,
          timestamp: new Date().toISOString()
        };

        this.emit('geoFenceExit', event);
      }
    });
  }

  private wasInsideGeoFence(geoFenceId: string): boolean {
    if (!this.lastKnownLocation || this.locationHistory.length < 2) {
      return false;
    }

    const geoFence = this.geoFences.find(gf => gf.id === geoFenceId);
    if (!geoFence) return false;

    const previousLocation = this.locationHistory[this.locationHistory.length - 2]?.location;
    if (!previousLocation) return false;

    const distance = this.calculateDistance(previousLocation, geoFence.center);
    return distance <= geoFence.radius;
  }

  // Utility methods
  private calculateDistance(coord1: GPSCoordinates, coord2: GPSCoordinates): number {
    const R = 6371e3; // Earth's radius in meters
    const φ1 = coord1.latitude * Math.PI/180;
    const φ2 = coord2.latitude * Math.PI/180;
    const Δφ = (coord2.latitude-coord1.latitude) * Math.PI/180;
    const Δλ = (coord2.longitude-coord1.longitude) * Math.PI/180;

    const a = Math.sin(Δφ/2) * Math.sin(Δφ/2) +
              Math.cos(φ1) * Math.cos(φ2) *
              Math.sin(Δλ/2) * Math.sin(Δλ/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));

    return R * c; // Distance in meters
  }

  calculateBearing(from: GPSCoordinates, to: GPSCoordinates): number {
    const φ1 = from.latitude * Math.PI/180;
    const φ2 = to.latitude * Math.PI/180;
    const Δλ = (to.longitude - from.longitude) * Math.PI/180;

    const y = Math.sin(Δλ) * Math.cos(φ2);
    const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);

    const θ = Math.atan2(y, x);
    return (θ * 180/Math.PI + 360) % 360; // Bearing in degrees
  }

  // Getters
  getLastKnownLocation(): GPSLocation | null {
    return this.lastKnownLocation;
  }

  getLocationHistory(): LocationUpdate[] {
    return [...this.locationHistory];
  }

  getServiceStatus(): LocationServiceStatus {
    return {
      available: 'geolocation' in navigator,
      enabled: this.settings.enabled && this.isTracking,
      accuracy: this.lastKnownLocation?.accuracy || 0,
      provider: 'browser_geolocation',
      lastUpdate: this.lastKnownLocation?.timestamp
    };
  }

  isTrackingActive(): boolean {
    return this.isTracking;
  }

  // Settings management
  updateSettings(newSettings: Partial<LocationTrackingSettings>): void {
    this.settings = { ...this.settings, ...newSettings };

    // Restart tracking if settings changed while tracking
    if (this.isTracking) {
      const technicianId = this.locationHistory[this.locationHistory.length - 1]?.technicianId;
      if (technicianId) {
        this.stopTracking();
        this.startTracking(technicianId);
      }
    }
  }

  getSettings(): LocationTrackingSettings {
    return { ...this.settings };
  }
}
