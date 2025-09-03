/**
 * Abstract Map Provider Interface
 * Unified interface for all map providers (Leaflet, Google Maps, Mapbox, etc.)
 */

import type {
  Coordinates,
  Bounds,
  MapConfig,
  MapMarker,
  ServiceArea,
  NetworkNode,
  Route,
  MapLayer,
  MapEvent,
  MapEventHandler,
  SearchCriteria,
  SearchResult,
  PerformanceMetrics,
  MapError,
} from '../types';
import { logger } from '../utils/logger';

export abstract class MapProvider {
  protected container: HTMLElement | null = null;
  protected config: MapConfig;
  protected layers: Map<string, MapLayer> = new Map();
  protected eventHandlers: Map<string, MapEventHandler[]> = new Map();
  protected _isInitialized = false;
  protected _isDestroyed = false;

  constructor(config: MapConfig) {
    this.config = config;
  }

  // Core lifecycle methods
  abstract initialize(container: HTMLElement): Promise<void>;
  abstract destroy(): Promise<void>;
  abstract resize(): void;

  // Map manipulation
  abstract setCenter(coordinates: Coordinates): void;
  abstract getCenter(): Coordinates;
  abstract setZoom(zoom: number): void;
  abstract getZoom(): number;
  abstract setBounds(bounds: Bounds): void;
  abstract getBounds(): Bounds;
  abstract fitBounds(bounds: Bounds, padding?: number): void;

  // Markers
  abstract addMarker(marker: MapMarker): void;
  abstract removeMarker(markerId: string): void;
  abstract updateMarker(markerId: string, updates: Partial<MapMarker>): void;
  abstract addMarkers(markers: MapMarker[]): void;
  abstract clearMarkers(): void;
  abstract getMarkers(): MapMarker[];

  // Service Areas (Polygons)
  abstract addServiceArea(area: ServiceArea): void;
  abstract removeServiceArea(areaId: string): void;
  abstract updateServiceArea(areaId: string, updates: Partial<ServiceArea>): void;
  abstract addServiceAreas(areas: ServiceArea[]): void;
  abstract clearServiceAreas(): void;
  abstract getServiceAreas(): ServiceArea[];

  // Network Nodes
  abstract addNetworkNode(node: NetworkNode): void;
  abstract removeNetworkNode(nodeId: string): void;
  abstract updateNetworkNode(nodeId: string, updates: Partial<NetworkNode>): void;
  abstract addNetworkNodes(nodes: NetworkNode[]): void;
  abstract clearNetworkNodes(): void;
  abstract getNetworkNodes(): NetworkNode[];

  // Routes/Polylines
  abstract addRoute(route: Route): void;
  abstract removeRoute(routeId: string): void;
  abstract updateRoute(routeId: string, updates: Partial<Route>): void;
  abstract addRoutes(routes: Route[]): void;
  abstract clearRoutes(): void;
  abstract getRoutes(): Route[];

  // Layers
  abstract addLayer(layer: MapLayer): void;
  abstract removeLayer(layerId: string): void;
  abstract toggleLayer(layerId: string): void;
  abstract setLayerOpacity(layerId: string, opacity: number): void;
  abstract setLayerVisibility(layerId: string, visible: boolean): void;

  // Clustering
  abstract enableClustering(options?: any): void;
  abstract disableClustering(): void;
  abstract isClustering(): boolean;

  // Heatmaps
  abstract addHeatmap(data: { coordinates: Coordinates; intensity: number }[]): void;
  abstract removeHeatmap(): void;
  abstract updateHeatmap(data: { coordinates: Coordinates; intensity: number }[]): void;

  // Search and Geocoding
  abstract search(criteria: SearchCriteria): Promise<SearchResult[]>;
  abstract geocode(address: string): Promise<Coordinates>;
  abstract reverseGeocode(coordinates: Coordinates): Promise<string>;

  // Event handling
  on<T extends MapEvent = MapEvent>(event: string, handler: MapEventHandler<T>): void {
    if (!this.eventHandlers.has(event)) {
      this.eventHandlers.set(event, []);
    }
    this.eventHandlers.get(event)!.push(handler as MapEventHandler);
  }

  off(event: string, handler?: MapEventHandler): void {
    const handlers = this.eventHandlers.get(event);
    if (!handlers) return;

    if (handler) {
      const index = handlers.indexOf(handler);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    } else {
      this.eventHandlers.set(event, []);
    }
  }

  protected emit<T extends MapEvent = MapEvent>(event: string, data: T): void {
    const handlers = this.eventHandlers.get(event);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(data);
        } catch (error) {
          logger.error('MapProvider', `Error in map event handler for ${event}`, error);
        }
      });
    }
  }

  // Utility methods
  calculateDistance(from: Coordinates, to: Coordinates): number {
    const R = 6371; // Earth's radius in km
    const dLat = this.toRad(to.lat - from.lat);
    const dLng = this.toRad(to.lng - from.lng);
    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(this.toRad(from.lat)) *
        Math.cos(this.toRad(to.lat)) *
        Math.sin(dLng / 2) *
        Math.sin(dLng / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  }

  private toRad(value: number): number {
    return (value * Math.PI) / 180;
  }

  calculateBounds(coordinates: Coordinates[]): Bounds {
    if (coordinates.length === 0) {
      throw new Error('Cannot calculate bounds for empty coordinates array');
    }

    let north = coordinates[0].lat;
    let south = coordinates[0].lat;
    let east = coordinates[0].lng;
    let west = coordinates[0].lng;

    coordinates.forEach((coord) => {
      north = Math.max(north, coord.lat);
      south = Math.min(south, coord.lat);
      east = Math.max(east, coord.lng);
      west = Math.min(west, coord.lng);
    });

    return { north, south, east, west };
  }

  isPointInBounds(point: Coordinates, bounds: Bounds): boolean {
    return (
      point.lat >= bounds.south &&
      point.lat <= bounds.north &&
      point.lng >= bounds.west &&
      point.lng <= bounds.east
    );
  }

  // Performance monitoring
  abstract getPerformanceMetrics(): PerformanceMetrics;

  // Error handling
  protected handleError(error: any, context: string): MapError {
    const mapError: MapError = {
      code: error.code || 'UNKNOWN_ERROR',
      message: error.message || 'An unknown error occurred',
      details: error,
      retryable: this.isRetryableError(error),
    };

    logger.error('MapProvider', `${context}: ${mapError.message}`, mapError);
    this.emit('error', { ...mapError, type: 'error' } as any);

    return mapError;
  }

  private isRetryableError(error: any): boolean {
    const retryableCodes = ['NETWORK_ERROR', 'TIMEOUT', 'RATE_LIMIT_EXCEEDED'];
    return retryableCodes.includes(error.code) || error.status >= 500;
  }

  // State management
  get isInitialized(): boolean {
    return this._isInitialized;
  }

  get isDestroyed(): boolean {
    return this._isDestroyed;
  }

  get configuration(): MapConfig {
    return { ...this.config };
  }

  updateConfiguration(updates: Partial<MapConfig>): void {
    this.config = { ...this.config, ...updates };
  }

  // Screenshot/Export
  abstract exportImage(format?: 'png' | 'jpg'): Promise<string>;
  abstract exportPDF(options?: { pageSize: string; orientation: string }): Promise<Blob>;

  // Accessibility
  abstract setAriaLabel(label: string): void;
  abstract setTabIndex(index: number): void;
  abstract enableKeyboardNavigation(): void;
  abstract disableKeyboardNavigation(): void;
}
