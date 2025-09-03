/**
 * Leaflet Map Provider Implementation
 * Real map implementation using Leaflet.js
 */

import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { MapProvider } from './MapProvider';
import type {
  Coordinates,
  Bounds,
  MapConfig,
  MapMarker,
  ServiceArea,
  NetworkNode,
  Route,
  MapLayer,
  SearchCriteria,
  SearchResult,
  PerformanceMetrics,
  MapEvent,
  MarkerEvent,
} from '../types';

export class LeafletProvider extends MapProvider {
  private map: L.Map | null = null;
  private markerLayer: L.LayerGroup;
  private areaLayer: L.LayerGroup;
  private nodeLayer: L.LayerGroup;
  private routeLayer: L.LayerGroup;
  private clusterGroup: L.MarkerClusterGroup | null = null;
  private heatmapLayer: any = null; // HeatmapOverlay type
  private markerInstances: Map<string, L.Marker> = new Map();
  private areaInstances: Map<string, L.Polygon> = new Map();
  private nodeInstances: Map<string, L.CircleMarker> = new Map();
  private routeInstances: Map<string, L.Polyline> = new Map();
  private performanceStart: number = 0;

  constructor(config: MapConfig) {
    super(config);
    this.markerLayer = L.layerGroup();
    this.areaLayer = L.layerGroup();
    this.nodeLayer = L.layerGroup();
    this.routeLayer = L.layerGroup();
  }

  async initialize(container: HTMLElement): Promise<void> {
    try {
      this.performanceStart = performance.now();
      this.container = container;

      // Fix Leaflet default markers
      delete (L.Icon.Default.prototype as any)._getIconUrl;
      L.Icon.Default.mergeOptions({
        iconRetinaUrl: '/leaflet/marker-icon-2x.png',
        iconUrl: '/leaflet/marker-icon.png',
        shadowUrl: '/leaflet/marker-shadow.png',
      });

      // Create map instance
      this.map = L.map(container, {
        center: [this.config.center.lat, this.config.center.lng],
        zoom: this.config.zoom,
        minZoom: this.config.minZoom || 1,
        maxZoom: this.config.maxZoom || 18,
        scrollWheelZoom: this.config.scrollWheelZoom !== false,
        doubleClickZoom: this.config.doubleClickZoom !== false,
        dragging: this.config.dragging !== false,
        touchZoom: this.config.touchZoom !== false,
        zoomControl: this.config.zoomControl !== false,
        attributionControl: this.config.attributionControl !== false,
        maxBounds: this.config.maxBounds
          ? [
              [this.config.maxBounds.south, this.config.maxBounds.west],
              [this.config.maxBounds.north, this.config.maxBounds.east],
            ]
          : undefined,
      });

      // Add default tile layer
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution:
          '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19,
      }).addTo(this.map);

      // Add layer groups to map
      this.markerLayer.addTo(this.map);
      this.areaLayer.addTo(this.map);
      this.nodeLayer.addTo(this.map);
      this.routeLayer.addTo(this.map);

      // Set up event listeners
      this.setupEventListeners();

      this._isInitialized = true;

      // Emit initialization event
      this.emit('initialized', {
        type: 'initialized',
        coordinates: this.getCenter(),
        originalEvent: new Event('initialized'),
      } as MapEvent);
    } catch (error) {
      throw this.handleError(error, 'initialize');
    }
  }

  async destroy(): Promise<void> {
    try {
      if (this.map) {
        this.map.remove();
        this.map = null;
      }

      this.markerInstances.clear();
      this.areaInstances.clear();
      this.nodeInstances.clear();
      this.routeInstances.clear();
      this.eventHandlers.clear();

      this._isDestroyed = true;
    } catch (error) {
      throw this.handleError(error, 'destroy');
    }
  }

  resize(): void {
    if (this.map) {
      setTimeout(() => {
        this.map!.invalidateSize();
      }, 100);
    }
  }

  // Map manipulation methods
  setCenter(coordinates: Coordinates): void {
    if (this.map) {
      this.map.setView([coordinates.lat, coordinates.lng]);
    }
  }

  getCenter(): Coordinates {
    if (!this.map) throw new Error('Map not initialized');
    const center = this.map.getCenter();
    return { lat: center.lat, lng: center.lng };
  }

  setZoom(zoom: number): void {
    if (this.map) {
      this.map.setZoom(zoom);
    }
  }

  getZoom(): number {
    if (!this.map) throw new Error('Map not initialized');
    return this.map.getZoom();
  }

  setBounds(bounds: Bounds): void {
    if (this.map) {
      this.map.fitBounds([
        [bounds.south, bounds.west],
        [bounds.north, bounds.east],
      ]);
    }
  }

  getBounds(): Bounds {
    if (!this.map) throw new Error('Map not initialized');
    const bounds = this.map.getBounds();
    return {
      north: bounds.getNorth(),
      south: bounds.getSouth(),
      east: bounds.getEast(),
      west: bounds.getWest(),
    };
  }

  fitBounds(bounds: Bounds, padding = 20): void {
    if (this.map) {
      this.map.fitBounds(
        [
          [bounds.south, bounds.west],
          [bounds.north, bounds.east],
        ],
        { padding: [padding, padding] }
      );
    }
  }

  // Marker management
  addMarker(marker: MapMarker): void {
    try {
      const leafletMarker = L.marker([marker.position.lat, marker.position.lng], {
        title: marker.title,
        // Custom icon based on type and status
        icon: this.createMarkerIcon(marker),
        zIndexOffset: marker.zIndex || 0,
      });

      // Add popup if provided
      if (marker.popup) {
        leafletMarker.bindPopup(marker.popup.content as string, {
          maxWidth: marker.popup.maxWidth || 300,
          className: marker.popup.className || '',
        });
      }

      // Add click handler
      if (marker.onClick) {
        leafletMarker.on('click', (e) => {
          marker.onClick!(marker);
          this.emit<MarkerEvent>('markerClick', {
            type: 'click',
            coordinates: marker.position,
            originalEvent: e.originalEvent,
            marker,
          });
        });
      }

      // Store marker instance
      this.markerInstances.set(marker.id, leafletMarker);

      // Add to appropriate layer
      if (marker.cluster && this.clusterGroup) {
        this.clusterGroup.addLayer(leafletMarker);
      } else {
        this.markerLayer.addLayer(leafletMarker);
      }
    } catch (error) {
      this.handleError(error, `addMarker: ${marker.id}`);
    }
  }

  removeMarker(markerId: string): void {
    const marker = this.markerInstances.get(markerId);
    if (marker) {
      if (this.clusterGroup) {
        this.clusterGroup.removeLayer(marker);
      }
      this.markerLayer.removeLayer(marker);
      this.markerInstances.delete(markerId);
    }
  }

  updateMarker(markerId: string, updates: Partial<MapMarker>): void {
    const marker = this.markerInstances.get(markerId);
    if (marker) {
      // Remove and re-add with updates - simpler than updating in place
      this.removeMarker(markerId);
      // Would need the full marker object to re-add
      // This is a limitation of the current design
    }
  }

  addMarkers(markers: MapMarker[]): void {
    markers.forEach((marker) => this.addMarker(marker));
  }

  clearMarkers(): void {
    this.markerLayer.clearLayers();
    if (this.clusterGroup) {
      this.clusterGroup.clearLayers();
    }
    this.markerInstances.clear();
  }

  getMarkers(): MapMarker[] {
    // This would require storing the original marker data
    // Implementation would depend on whether we maintain that state
    return [];
  }

  // Service Areas (Polygons)
  addServiceArea(area: ServiceArea): void {
    try {
      const coordinates = area.polygon.coordinates.map(
        (coord) => [coord.lat, coord.lng] as [number, number]
      );

      const polygon = L.polygon(coordinates, {
        fillColor: area.color || '#3388ff',
        fillOpacity: area.fillOpacity || 0.3,
        color: area.color || '#3388ff',
        weight: area.strokeWeight || 2,
      });

      // Add popup with area info
      const popupContent = `
        <div class="service-area-popup">
          <h4>${area.name}</h4>
          <p>Type: ${area.type}</p>
          <p>Service Level: ${area.serviceLevel}</p>
          <p>Max Speed: ${area.maxSpeed} Mbps</p>
          <p>Coverage: ${area.coverage}%</p>
          ${area.customers ? `<p>Customers: ${area.customers}</p>` : ''}
        </div>
      `;
      polygon.bindPopup(popupContent);

      // Add click handler
      polygon.on('click', (e) => {
        this.emit('areaClick', {
          type: 'click',
          coordinates: { lat: e.latlng.lat, lng: e.latlng.lng },
          originalEvent: e.originalEvent,
          area,
        } as any);
      });

      this.areaInstances.set(area.id, polygon);
      this.areaLayer.addLayer(polygon);
    } catch (error) {
      this.handleError(error, `addServiceArea: ${area.id}`);
    }
  }

  removeServiceArea(areaId: string): void {
    const area = this.areaInstances.get(areaId);
    if (area) {
      this.areaLayer.removeLayer(area);
      this.areaInstances.delete(areaId);
    }
  }

  updateServiceArea(areaId: string, updates: Partial<ServiceArea>): void {
    // Similar to markers, would need to re-implement
    const area = this.areaInstances.get(areaId);
    if (area) {
      // Update styling if possible
      if (updates.color) {
        area.setStyle({ fillColor: updates.color, color: updates.color });
      }
    }
  }

  addServiceAreas(areas: ServiceArea[]): void {
    areas.forEach((area) => this.addServiceArea(area));
  }

  clearServiceAreas(): void {
    this.areaLayer.clearLayers();
    this.areaInstances.clear();
  }

  getServiceAreas(): ServiceArea[] {
    return [];
  }

  // Network Nodes
  addNetworkNode(node: NetworkNode): void {
    try {
      const color = this.getNodeStatusColor(node.status);
      const radius = this.getNodeRadius(node.type);

      const circleMarker = L.circleMarker([node.position.lat, node.position.lng], {
        radius,
        fillColor: color,
        color: color,
        weight: 2,
        opacity: 1,
        fillOpacity: 0.8,
      });

      // Add popup with node info
      const popupContent = `
        <div class="network-node-popup">
          <h4>${node.name}</h4>
          <p>Type: ${node.type}</p>
          <p>Status: ${node.status}</p>
          <p>Utilization: ${node.utilization}%</p>
          <p>Capacity: ${node.capacity}</p>
          ${
            node.metrics
              ? `
            <p>Latency: ${node.metrics.latency}ms</p>
            <p>Uptime: ${node.metrics.uptime}%</p>
          `
              : ''
          }
        </div>
      `;
      circleMarker.bindPopup(popupContent);

      // Add click handler
      circleMarker.on('click', (e) => {
        this.emit('nodeClick', {
          type: 'click',
          coordinates: node.position,
          originalEvent: e.originalEvent,
          node,
        } as any);
      });

      this.nodeInstances.set(node.id, circleMarker);
      this.nodeLayer.addLayer(circleMarker);
    } catch (error) {
      this.handleError(error, `addNetworkNode: ${node.id}`);
    }
  }

  removeNetworkNode(nodeId: string): void {
    const node = this.nodeInstances.get(nodeId);
    if (node) {
      this.nodeLayer.removeLayer(node);
      this.nodeInstances.delete(nodeId);
    }
  }

  updateNetworkNode(nodeId: string, updates: Partial<NetworkNode>): void {
    const node = this.nodeInstances.get(nodeId);
    if (node && updates.status) {
      const color = this.getNodeStatusColor(updates.status);
      node.setStyle({ fillColor: color, color });
    }
  }

  addNetworkNodes(nodes: NetworkNode[]): void {
    nodes.forEach((node) => this.addNetworkNode(node));
  }

  clearNetworkNodes(): void {
    this.nodeLayer.clearLayers();
    this.nodeInstances.clear();
  }

  getNetworkNodes(): NetworkNode[] {
    return [];
  }

  // Routes implementation
  addRoute(route: Route): void {
    try {
      const coordinates = route.waypoints.map(
        (coord) => [coord.lat, coord.lng] as [number, number]
      );
      const color = this.getRouteStatusColor(route.status);

      const polyline = L.polyline(coordinates, {
        color,
        weight: 4,
        opacity: 0.8,
        dashArray: route.status === 'planned' ? '10, 10' : undefined,
      });

      // Add popup with route info
      const popupContent = `
        <div class="route-popup">
          <h4>${route.name}</h4>
          <p>Type: ${route.type}</p>
          <p>Status: ${route.status}</p>
          <p>Priority: ${route.priority}</p>
          ${route.estimatedTime ? `<p>Est. Time: ${route.estimatedTime} min</p>` : ''}
          ${route.assignedTechnician ? `<p>Assigned: ${route.assignedTechnician}</p>` : ''}
        </div>
      `;
      polyline.bindPopup(popupContent);

      this.routeInstances.set(route.id, polyline);
      this.routeLayer.addLayer(polyline);
    } catch (error) {
      this.handleError(error, `addRoute: ${route.id}`);
    }
  }

  removeRoute(routeId: string): void {
    const route = this.routeInstances.get(routeId);
    if (route) {
      this.routeLayer.removeLayer(route);
      this.routeInstances.delete(routeId);
    }
  }

  updateRoute(routeId: string, updates: Partial<Route>): void {
    const route = this.routeInstances.get(routeId);
    if (route && updates.status) {
      const color = this.getRouteStatusColor(updates.status);
      route.setStyle({ color });
    }
  }

  addRoutes(routes: Route[]): void {
    routes.forEach((route) => this.addRoute(route));
  }

  clearRoutes(): void {
    this.routeLayer.clearLayers();
    this.routeInstances.clear();
  }

  getRoutes(): Route[] {
    return [];
  }

  // Layer management
  addLayer(layer: MapLayer): void {
    // Implementation depends on layer type
    this.layers.set(layer.id, layer);
  }

  removeLayer(layerId: string): void {
    this.layers.delete(layerId);
  }

  toggleLayer(layerId: string): void {
    const layer = this.layers.get(layerId);
    if (layer) {
      layer.visible = !layer.visible;
      this.setLayerVisibility(layerId, layer.visible);
    }
  }

  setLayerOpacity(layerId: string, opacity: number): void {
    const layer = this.layers.get(layerId);
    if (layer) {
      layer.opacity = opacity;
    }
  }

  setLayerVisibility(layerId: string, visible: boolean): void {
    const layer = this.layers.get(layerId);
    if (layer) {
      layer.visible = visible;
    }
  }

  // Clustering
  enableClustering(options: any = {}): void {
    if (!this.clusterGroup) {
      this.clusterGroup = L.markerClusterGroup(options);
      this.map?.addLayer(this.clusterGroup);
    }
  }

  disableClustering(): void {
    if (this.clusterGroup && this.map) {
      this.map.removeLayer(this.clusterGroup);
      this.clusterGroup = null;
    }
  }

  isClustering(): boolean {
    return this.clusterGroup !== null;
  }

  // Heatmaps
  addHeatmap(data: { coordinates: Coordinates; intensity: number }[]): void {
    // Would require leaflet-heatmap plugin
    console.warn('Heatmap functionality requires additional plugin');
  }

  removeHeatmap(): void {
    if (this.heatmapLayer && this.map) {
      this.map.removeLayer(this.heatmapLayer);
      this.heatmapLayer = null;
    }
  }

  updateHeatmap(data: { coordinates: Coordinates; intensity: number }[]): void {
    this.removeHeatmap();
    this.addHeatmap(data);
  }

  // Search and geocoding
  async search(criteria: SearchCriteria): Promise<SearchResult[]> {
    try {
      // Use Nominatim (OpenStreetMap) geocoding service
      const params = new URLSearchParams({
        q: criteria.query,
        format: 'json',
        limit: (criteria.maxResults || 10).toString(),
        addressdetails: '1',
      });

      if (criteria.bounds) {
        const { north, south, east, west } = criteria.bounds;
        params.set('bounded', '1');
        params.set('viewbox', `${west},${south},${east},${north}`);
      }

      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error('Geocoding service unavailable');
      }

      const data = await response.json();

      return data.map((item: any, index: number) => ({
        id: `search_${index}`,
        name: item.display_name,
        type: criteria.type,
        coordinates: {
          lat: parseFloat(item.lat),
          lng: parseFloat(item.lon),
        },
        address: item.display_name,
        relevance: 1 - index * 0.1, // Decrease relevance by position
        metadata: {
          place_id: item.place_id,
          osm_type: item.osm_type,
          osm_id: item.osm_id,
        },
      }));
    } catch (error) {
      this.handleError(error, 'search');
      return [];
    }
  }

  async geocode(address: string): Promise<Coordinates> {
    try {
      const params = new URLSearchParams({
        q: address,
        format: 'json',
        limit: '1',
      });

      const response = await fetch(
        `https://nominatim.openstreetmap.org/search?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error('Geocoding service unavailable');
      }

      const data = await response.json();

      if (data.length === 0) {
        throw new Error('Address not found');
      }

      return {
        lat: parseFloat(data[0].lat),
        lng: parseFloat(data[0].lon),
      };
    } catch (error) {
      throw this.handleError(error, 'geocode');
    }
  }

  async reverseGeocode(coordinates: Coordinates): Promise<string> {
    try {
      const params = new URLSearchParams({
        lat: coordinates.lat.toString(),
        lon: coordinates.lng.toString(),
        format: 'json',
      });

      const response = await fetch(
        `https://nominatim.openstreetmap.org/reverse?${params.toString()}`
      );

      if (!response.ok) {
        throw new Error('Reverse geocoding service unavailable');
      }

      const data = await response.json();

      return data.display_name || `${coordinates.lat.toFixed(4)}, ${coordinates.lng.toFixed(4)}`;
    } catch (error) {
      this.handleError(error, 'reverseGeocode');
      return `${coordinates.lat.toFixed(4)}, ${coordinates.lng.toFixed(4)}`;
    }
  }

  // Performance metrics
  getPerformanceMetrics(): PerformanceMetrics {
    const currentTime = performance.now();
    return {
      renderTime: currentTime - this.performanceStart,
      dataLoadTime: 0,
      interactionLatency: 0,
      memoryUsage: 0,
      tileLoadTime: 0,
    };
  }

  // Export functionality
  async exportImage(format: 'png' | 'jpg' = 'png'): Promise<string> {
    // Would use leaflet-image or similar plugin
    throw new Error('Image export not implemented');
  }

  async exportPDF(
    options: { pageSize: string; orientation: string } = {
      pageSize: 'A4',
      orientation: 'landscape',
    }
  ): Promise<Blob> {
    throw new Error('PDF export not implemented');
  }

  // Accessibility
  setAriaLabel(label: string): void {
    if (this.container) {
      this.container.setAttribute('aria-label', label);
    }
  }

  setTabIndex(index: number): void {
    if (this.container) {
      this.container.setAttribute('tabindex', index.toString());
    }
  }

  enableKeyboardNavigation(): void {
    if (this.map) {
      this.map.keyboard.enable();
    }
  }

  disableKeyboardNavigation(): void {
    if (this.map) {
      this.map.keyboard.disable();
    }
  }

  // Private helper methods
  private setupEventListeners(): void {
    if (!this.map) return;

    this.map.on('click', (e) => {
      this.emit('click', {
        type: 'click',
        coordinates: { lat: e.latlng.lat, lng: e.latlng.lng },
        originalEvent: e.originalEvent,
      });
    });

    this.map.on('moveend', () => {
      this.emit('move', {
        type: 'move',
        coordinates: this.getCenter(),
        originalEvent: new Event('moveend'),
      });
    });

    this.map.on('zoomend', () => {
      this.emit('zoom', {
        type: 'zoom',
        coordinates: this.getCenter(),
        originalEvent: new Event('zoomend'),
      });
    });
  }

  private createMarkerIcon(marker: MapMarker): L.Icon {
    const iconUrl = this.getMarkerIconUrl(marker.type, marker.status);
    const iconSize = this.getMarkerSize(marker.size || 'medium');

    return L.icon({
      iconUrl,
      iconSize: [iconSize, iconSize],
      iconAnchor: [iconSize / 2, iconSize],
      popupAnchor: [0, -iconSize],
    });
  }

  private getMarkerIconUrl(type: MapMarker['type'], status?: MapMarker['status']): string {
    // Return appropriate icon URL based on type and status
    return `/icons/markers/${type}-${status || 'default'}.png`;
  }

  private getMarkerSize(size: 'small' | 'medium' | 'large'): number {
    switch (size) {
      case 'small':
        return 16;
      case 'large':
        return 32;
      default:
        return 24;
    }
  }

  private getNodeStatusColor(status: NetworkNode['status']): string {
    switch (status) {
      case 'online':
        return '#10B981';
      case 'offline':
        return '#EF4444';
      case 'maintenance':
        return '#F59E0B';
      case 'error':
        return '#DC2626';
      case 'degraded':
        return '#F97316';
      default:
        return '#6B7280';
    }
  }

  private getNodeRadius(type: NetworkNode['type']): number {
    switch (type) {
      case 'core':
        return 12;
      case 'distribution':
        return 10;
      case 'access':
        return 8;
      case 'edge':
        return 6;
      case 'customer':
        return 4;
      default:
        return 8;
    }
  }

  private getRouteStatusColor(status: Route['status']): string {
    switch (status) {
      case 'planned':
        return '#8B5CF6';
      case 'in_progress':
        return '#3B82F6';
      case 'completed':
        return '#10B981';
      case 'cancelled':
        return '#EF4444';
      default:
        return '#6B7280';
    }
  }
}
