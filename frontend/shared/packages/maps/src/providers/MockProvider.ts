/**
 * Mock Map Provider Implementation
 * Development and testing map provider with simulated functionality
 */

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
} from '../types';

export class MockProvider extends MapProvider {
  private canvas: HTMLCanvasElement | null = null;
  private ctx: CanvasRenderingContext2D | null = null;
  private markers: MapMarker[] = [];
  private areas: ServiceArea[] = [];
  private nodes: NetworkNode[] = [];
  private routes: Route[] = [];
  private currentCenter: Coordinates;
  private currentZoom: number;
  private isClusteringEnabled = false;
  private animationFrame: number | null = null;

  constructor(config: MapConfig) {
    super(config);
    this.currentCenter = config.center;
    this.currentZoom = config.zoom;
  }

  async initialize(container: HTMLElement): Promise<void> {
    try {
      this.container = container;

      // Create canvas element
      this.canvas = document.createElement('canvas');
      this.canvas.style.width = '100%';
      this.canvas.style.height = '100%';
      this.canvas.style.position = 'relative';
      this.canvas.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';

      // Set canvas size
      const rect = container.getBoundingClientRect();
      this.canvas.width = rect.width;
      this.canvas.height = rect.height;

      this.ctx = this.canvas.getContext('2d');
      if (!this.ctx) {
        throw new Error('Could not get 2D context from canvas');
      }

      container.appendChild(this.canvas);

      // Set up event listeners
      this.setupEventListeners();

      // Start rendering loop
      this.startRenderLoop();

      this._isInitialized = true;

      // Emit initialization event
      this.emit('initialized', {
        type: 'initialized',
        coordinates: this.currentCenter,
        originalEvent: new Event('initialized'),
      });
    } catch (error) {
      throw this.handleError(error, 'initialize');
    }
  }

  async destroy(): Promise<void> {
    try {
      if (this.animationFrame) {
        cancelAnimationFrame(this.animationFrame);
      }

      if (this.canvas && this.container) {
        this.container.removeChild(this.canvas);
      }

      this.canvas = null;
      this.ctx = null;
      this.markers = [];
      this.areas = [];
      this.nodes = [];
      this.routes = [];
      this.eventHandlers.clear();

      this._isDestroyed = true;
    } catch (error) {
      throw this.handleError(error, 'destroy');
    }
  }

  resize(): void {
    if (this.canvas && this.container) {
      const rect = this.container.getBoundingClientRect();
      this.canvas.width = rect.width;
      this.canvas.height = rect.height;
      this.render();
    }
  }

  // Map manipulation methods
  setCenter(coordinates: Coordinates): void {
    this.currentCenter = coordinates;
    this.render();

    this.emit('move', {
      type: 'move',
      coordinates: this.currentCenter,
      originalEvent: new Event('move'),
    });
  }

  getCenter(): Coordinates {
    return { ...this.currentCenter };
  }

  setZoom(zoom: number): void {
    this.currentZoom = Math.max(1, Math.min(20, zoom));
    this.render();

    this.emit('zoom', {
      type: 'zoom',
      coordinates: this.currentCenter,
      originalEvent: new Event('zoom'),
    });
  }

  getZoom(): number {
    return this.currentZoom;
  }

  setBounds(bounds: Bounds): void {
    // Calculate center and zoom from bounds
    const centerLat = (bounds.north + bounds.south) / 2;
    const centerLng = (bounds.east + bounds.west) / 2;
    this.currentCenter = { lat: centerLat, lng: centerLng };

    // Rough zoom calculation
    const latDiff = bounds.north - bounds.south;
    const lngDiff = bounds.east - bounds.west;
    const maxDiff = Math.max(latDiff, lngDiff);
    this.currentZoom = Math.max(1, Math.min(20, 15 - Math.log2(maxDiff * 100)));

    this.render();
  }

  getBounds(): Bounds {
    const zoomFactor = Math.pow(2, 15 - this.currentZoom) / 100;
    return {
      north: this.currentCenter.lat + zoomFactor,
      south: this.currentCenter.lat - zoomFactor,
      east: this.currentCenter.lng + zoomFactor,
      west: this.currentCenter.lng - zoomFactor,
    };
  }

  fitBounds(bounds: Bounds, padding = 20): void {
    this.setBounds(bounds);
  }

  // Marker management
  addMarker(marker: MapMarker): void {
    this.markers.push(marker);
    this.render();
  }

  removeMarker(markerId: string): void {
    this.markers = this.markers.filter((m) => m.id !== markerId);
    this.render();
  }

  updateMarker(markerId: string, updates: Partial<MapMarker>): void {
    const markerIndex = this.markers.findIndex((m) => m.id === markerId);
    if (markerIndex > -1) {
      this.markers[markerIndex] = { ...this.markers[markerIndex], ...updates };
      this.render();
    }
  }

  addMarkers(markers: MapMarker[]): void {
    this.markers.push(...markers);
    this.render();
  }

  clearMarkers(): void {
    this.markers = [];
    this.render();
  }

  getMarkers(): MapMarker[] {
    return [...this.markers];
  }

  // Service Areas
  addServiceArea(area: ServiceArea): void {
    this.areas.push(area);
    this.render();
  }

  removeServiceArea(areaId: string): void {
    this.areas = this.areas.filter((a) => a.id !== areaId);
    this.render();
  }

  updateServiceArea(areaId: string, updates: Partial<ServiceArea>): void {
    const areaIndex = this.areas.findIndex((a) => a.id === areaId);
    if (areaIndex > -1) {
      this.areas[areaIndex] = { ...this.areas[areaIndex], ...updates };
      this.render();
    }
  }

  addServiceAreas(areas: ServiceArea[]): void {
    this.areas.push(...areas);
    this.render();
  }

  clearServiceAreas(): void {
    this.areas = [];
    this.render();
  }

  getServiceAreas(): ServiceArea[] {
    return [...this.areas];
  }

  // Network Nodes
  addNetworkNode(node: NetworkNode): void {
    this.nodes.push(node);
    this.render();
  }

  removeNetworkNode(nodeId: string): void {
    this.nodes = this.nodes.filter((n) => n.id !== nodeId);
    this.render();
  }

  updateNetworkNode(nodeId: string, updates: Partial<NetworkNode>): void {
    const nodeIndex = this.nodes.findIndex((n) => n.id === nodeId);
    if (nodeIndex > -1) {
      this.nodes[nodeIndex] = { ...this.nodes[nodeIndex], ...updates };
      this.render();
    }
  }

  addNetworkNodes(nodes: NetworkNode[]): void {
    this.nodes.push(...nodes);
    this.render();
  }

  clearNetworkNodes(): void {
    this.nodes = [];
    this.render();
  }

  getNetworkNodes(): NetworkNode[] {
    return [...this.nodes];
  }

  // Routes
  addRoute(route: Route): void {
    this.routes.push(route);
    this.render();
  }

  removeRoute(routeId: string): void {
    this.routes = this.routes.filter((r) => r.id !== routeId);
    this.render();
  }

  updateRoute(routeId: string, updates: Partial<Route>): void {
    const routeIndex = this.routes.findIndex((r) => r.id === routeId);
    if (routeIndex > -1) {
      this.routes[routeIndex] = { ...this.routes[routeIndex], ...updates };
      this.render();
    }
  }

  addRoutes(routes: Route[]): void {
    this.routes.push(...routes);
    this.render();
  }

  clearRoutes(): void {
    this.routes = [];
    this.render();
  }

  getRoutes(): Route[] {
    return [...this.routes];
  }

  // Layer management
  addLayer(layer: MapLayer): void {
    this.layers.set(layer.id, layer);
    this.render();
  }

  removeLayer(layerId: string): void {
    this.layers.delete(layerId);
    this.render();
  }

  toggleLayer(layerId: string): void {
    const layer = this.layers.get(layerId);
    if (layer) {
      layer.visible = !layer.visible;
      this.render();
    }
  }

  setLayerOpacity(layerId: string, opacity: number): void {
    const layer = this.layers.get(layerId);
    if (layer) {
      layer.opacity = opacity;
      this.render();
    }
  }

  setLayerVisibility(layerId: string, visible: boolean): void {
    const layer = this.layers.get(layerId);
    if (layer) {
      layer.visible = visible;
      this.render();
    }
  }

  // Clustering
  enableClustering(): void {
    this.isClusteringEnabled = true;
    this.render();
  }

  disableClustering(): void {
    this.isClusteringEnabled = false;
    this.render();
  }

  isClustering(): boolean {
    return this.isClusteringEnabled;
  }

  // Heatmaps
  addHeatmap(data: { coordinates: Coordinates; intensity: number }[]): void {
    // Mock heatmap visualization
    this.render();
  }

  removeHeatmap(): void {
    this.render();
  }

  updateHeatmap(data: { coordinates: Coordinates; intensity: number }[]): void {
    this.render();
  }

  // Search and geocoding
  async search(criteria: SearchCriteria): Promise<SearchResult[]> {
    // Mock search results
    const mockResults: SearchResult[] = [
      {
        id: '1',
        name: `Mock result for "${criteria.query}"`,
        type: criteria.type,
        coordinates: { lat: 37.7749, lng: -122.4194 },
        address: '123 Mock Street, Mock City',
        relevance: 0.95,
        metadata: { source: 'mock' },
      },
    ];

    // Simulate API delay
    await new Promise((resolve) => setTimeout(resolve, 300));
    return mockResults;
  }

  async geocode(address: string): Promise<Coordinates> {
    // Mock geocoding
    await new Promise((resolve) => setTimeout(resolve, 200));
    return { lat: 37.7749, lng: -122.4194 };
  }

  async reverseGeocode(coordinates: Coordinates): Promise<string> {
    // Mock reverse geocoding
    await new Promise((resolve) => setTimeout(resolve, 200));
    return `Mock Address at ${coordinates.lat.toFixed(4)}, ${coordinates.lng.toFixed(4)}`;
  }

  // Performance metrics
  getPerformanceMetrics(): PerformanceMetrics {
    return {
      renderTime: Math.random() * 10 + 5, // 5-15ms
      dataLoadTime: Math.random() * 50 + 10, // 10-60ms
      interactionLatency: Math.random() * 5 + 1, // 1-6ms
      memoryUsage: Math.random() * 10 + 20, // 20-30MB
      tileLoadTime: Math.random() * 100 + 50, // 50-150ms
    };
  }

  // Export functionality
  async exportImage(format: 'png' | 'jpg' = 'png'): Promise<string> {
    if (!this.canvas) throw new Error('Canvas not available');
    return this.canvas.toDataURL(`image/${format}`);
  }

  async exportPDF(): Promise<Blob> {
    // Mock PDF generation
    const canvas = await this.exportImage();
    return new Blob([canvas], { type: 'application/pdf' });
  }

  // Accessibility
  setAriaLabel(label: string): void {
    if (this.canvas) {
      this.canvas.setAttribute('aria-label', label);
    }
  }

  setTabIndex(index: number): void {
    if (this.canvas) {
      this.canvas.setAttribute('tabindex', index.toString());
    }
  }

  enableKeyboardNavigation(): void {
    // Mock keyboard navigation
    this.setupKeyboardListeners();
  }

  disableKeyboardNavigation(): void {
    // Remove keyboard listeners
  }

  // Private rendering methods
  private startRenderLoop(): void {
    const animate = () => {
      this.render();
      this.animationFrame = requestAnimationFrame(animate);
    };
    animate();
  }

  private render(): void {
    if (!this.ctx || !this.canvas) return;

    const width = this.canvas.width;
    const height = this.canvas.height;

    // Clear canvas
    this.ctx.clearRect(0, 0, width, height);

    // Draw background grid
    this.drawGrid();

    // Draw service areas
    this.drawServiceAreas();

    // Draw routes
    this.drawRoutes();

    // Draw network nodes
    this.drawNetworkNodes();

    // Draw markers
    this.drawMarkers();

    // Draw UI elements
    this.drawUI();
  }

  private drawGrid(): void {
    if (!this.ctx || !this.canvas) return;

    this.ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
    this.ctx.lineWidth = 1;

    const gridSize = 50 / this.currentZoom;
    const width = this.canvas.width;
    const height = this.canvas.height;

    for (let x = 0; x < width; x += gridSize) {
      this.ctx.beginPath();
      this.ctx.moveTo(x, 0);
      this.ctx.lineTo(x, height);
      this.ctx.stroke();
    }

    for (let y = 0; y < height; y += gridSize) {
      this.ctx.beginPath();
      this.ctx.moveTo(0, y);
      this.ctx.lineTo(width, y);
      this.ctx.stroke();
    }
  }

  private drawServiceAreas(): void {
    if (!this.ctx) return;

    this.areas.forEach((area, index) => {
      const { x, y } = this.coordinateToPixel(area.polygon.coordinates[0]);

      this.ctx!.fillStyle =
        area.color || `rgba(${100 + index * 50}, ${150 + index * 30}, 255, 0.3)`;
      this.ctx!.beginPath();
      this.ctx!.arc(x, y, 60, 0, 2 * Math.PI);
      this.ctx!.fill();

      // Area label
      this.ctx!.fillStyle = 'white';
      this.ctx!.font = '12px Arial';
      this.ctx!.textAlign = 'center';
      this.ctx!.fillText(area.name, x, y + 4);
    });
  }

  private drawRoutes(): void {
    if (!this.ctx) return;

    this.routes.forEach((route) => {
      const color = this.getRouteColor(route.status);
      this.ctx!.strokeStyle = color;
      this.ctx!.lineWidth = 3;
      this.ctx!.setLineDash(route.status === 'planned' ? [5, 5] : []);

      this.ctx!.beginPath();
      route.waypoints.forEach((waypoint, index) => {
        const { x, y } = this.coordinateToPixel(waypoint);
        if (index === 0) {
          this.ctx!.moveTo(x, y);
        } else {
          this.ctx!.lineTo(x, y);
        }
      });
      this.ctx!.stroke();
      this.ctx!.setLineDash([]);
    });
  }

  private drawNetworkNodes(): void {
    if (!this.ctx) return;

    this.nodes.forEach((node) => {
      const { x, y } = this.coordinateToPixel(node.position);
      const color = this.getNodeColor(node.status);
      const radius = this.getNodeRadius(node.type);

      this.ctx!.fillStyle = color;
      this.ctx!.beginPath();
      this.ctx!.arc(x, y, radius, 0, 2 * Math.PI);
      this.ctx!.fill();

      this.ctx!.strokeStyle = 'white';
      this.ctx!.lineWidth = 2;
      this.ctx!.stroke();
    });
  }

  private drawMarkers(): void {
    if (!this.ctx) return;

    // Group markers for clustering if enabled
    const markersToRender = this.isClusteringEnabled ? this.clusterMarkers() : this.markers;

    markersToRender.forEach((marker) => {
      const { x, y } = this.coordinateToPixel(marker.position);
      const color = this.getMarkerColor(marker.type, marker.status);

      // Draw marker
      this.ctx!.fillStyle = color;
      this.ctx!.beginPath();
      this.ctx!.arc(x, y, 8, 0, 2 * Math.PI);
      this.ctx!.fill();

      this.ctx!.strokeStyle = 'white';
      this.ctx!.lineWidth = 2;
      this.ctx!.stroke();

      // Draw marker icon/label
      this.ctx!.fillStyle = 'white';
      this.ctx!.font = '10px Arial';
      this.ctx!.textAlign = 'center';
      this.ctx!.fillText(marker.type.charAt(0).toUpperCase(), x, y + 3);
    });
  }

  private drawUI(): void {
    if (!this.ctx || !this.canvas) return;

    // Draw zoom level
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    this.ctx.fillRect(10, 10, 100, 30);
    this.ctx.fillStyle = 'white';
    this.ctx.font = '12px Arial';
    this.ctx.textAlign = 'left';
    this.ctx.fillText(`Zoom: ${this.currentZoom}`, 15, 28);

    // Draw coordinate info
    this.ctx.fillStyle = 'rgba(0, 0, 0, 0.7)';
    this.ctx.fillRect(10, this.canvas.height - 40, 200, 30);
    this.ctx.fillStyle = 'white';
    this.ctx.fillText(
      `${this.currentCenter.lat.toFixed(4)}, ${this.currentCenter.lng.toFixed(4)}`,
      15,
      this.canvas.height - 22
    );
  }

  private coordinateToPixel(coord: Coordinates): { x: number; y: number } {
    if (!this.canvas) return { x: 0, y: 0 };

    const width = this.canvas.width;
    const height = this.canvas.height;

    // Simple projection - in real implementation would use proper map projection
    const scale = Math.pow(2, this.currentZoom) / 100;
    const x = width / 2 + (coord.lng - this.currentCenter.lng) * scale * width;
    const y = height / 2 - (coord.lat - this.currentCenter.lat) * scale * height;

    return { x, y };
  }

  private clusterMarkers(): MapMarker[] {
    // Simple clustering algorithm
    const clusters: MapMarker[] = [];
    const clustered = new Set<string>();
    const clusterRadius = 50;

    this.markers.forEach((marker) => {
      if (clustered.has(marker.id)) return;

      const { x, y } = this.coordinateToPixel(marker.position);
      const nearbyMarkers = this.markers.filter((other) => {
        if (other.id === marker.id || clustered.has(other.id)) return false;
        const { x: otherX, y: otherY } = this.coordinateToPixel(other.position);
        const distance = Math.sqrt((x - otherX) ** 2 + (y - otherY) ** 2);
        return distance < clusterRadius;
      });

      if (nearbyMarkers.length > 0) {
        // Create cluster marker
        clustered.add(marker.id);
        nearbyMarkers.forEach((m) => clustered.add(m.id));

        clusters.push({
          ...marker,
          title: `Cluster (${nearbyMarkers.length + 1})`,
          type: 'poi',
        });
      } else {
        clusters.push(marker);
      }
    });

    return clusters;
  }

  private setupEventListeners(): void {
    if (!this.canvas) return;

    this.canvas.addEventListener('click', (e) => {
      const rect = this.canvas!.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const coordinates = this.pixelToCoordinate({ x, y });

      this.emit('click', {
        type: 'click',
        coordinates,
        originalEvent: e,
      });
    });

    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const zoomDelta = e.deltaY > 0 ? -1 : 1;
      this.setZoom(this.currentZoom + zoomDelta);
    });

    let isDragging = false;
    let lastMousePos = { x: 0, y: 0 };

    this.canvas.addEventListener('mousedown', (e) => {
      isDragging = true;
      lastMousePos = { x: e.clientX, y: e.clientY };
    });

    this.canvas.addEventListener('mousemove', (e) => {
      if (!isDragging) return;

      const deltaX = e.clientX - lastMousePos.x;
      const deltaY = e.clientY - lastMousePos.y;

      const scale = Math.pow(2, this.currentZoom) / 100;
      const newCenter = {
        lat: this.currentCenter.lat + deltaY / (scale * this.canvas!.height),
        lng: this.currentCenter.lng - deltaX / (scale * this.canvas!.width),
      };

      this.setCenter(newCenter);
      lastMousePos = { x: e.clientX, y: e.clientY };
    });

    this.canvas.addEventListener('mouseup', () => {
      isDragging = false;
    });
  }

  private setupKeyboardListeners(): void {
    if (!this.canvas) return;

    this.canvas.addEventListener('keydown', (e) => {
      switch (e.key) {
        case 'ArrowUp':
          this.setCenter({ lat: this.currentCenter.lat + 0.1, lng: this.currentCenter.lng });
          break;
        case 'ArrowDown':
          this.setCenter({ lat: this.currentCenter.lat - 0.1, lng: this.currentCenter.lng });
          break;
        case 'ArrowLeft':
          this.setCenter({ lat: this.currentCenter.lat, lng: this.currentCenter.lng - 0.1 });
          break;
        case 'ArrowRight':
          this.setCenter({ lat: this.currentCenter.lat, lng: this.currentCenter.lng + 0.1 });
          break;
        case '+':
        case '=':
          this.setZoom(this.currentZoom + 1);
          break;
        case '-':
          this.setZoom(this.currentZoom - 1);
          break;
      }
    });
  }

  private pixelToCoordinate(pixel: { x: number; y: number }): Coordinates {
    if (!this.canvas) return this.currentCenter;

    const width = this.canvas.width;
    const height = this.canvas.height;
    const scale = Math.pow(2, this.currentZoom) / 100;

    const lat = this.currentCenter.lat - (pixel.y - height / 2) / (scale * height);
    const lng = this.currentCenter.lng + (pixel.x - width / 2) / (scale * width);

    return { lat, lng };
  }

  private getMarkerColor(type: MapMarker['type'], status?: MapMarker['status']): string {
    const statusColors = {
      active: '#10B981',
      inactive: '#6B7280',
      maintenance: '#F59E0B',
      error: '#EF4444',
      warning: '#F97316',
      planned: '#8B5CF6',
    };

    return statusColors[status || 'active'];
  }

  private getNodeColor(status: NetworkNode['status']): string {
    const colors = {
      online: '#10B981',
      offline: '#EF4444',
      maintenance: '#F59E0B',
      error: '#DC2626',
      degraded: '#F97316',
    };

    return colors[status] || '#6B7280';
  }

  private getNodeRadius(type: NetworkNode['type']): number {
    const sizes = {
      core: 12,
      distribution: 10,
      access: 8,
      edge: 6,
      customer: 4,
    };

    return sizes[type] || 8;
  }

  private getRouteColor(status: Route['status']): string {
    const colors = {
      planned: '#8B5CF6',
      in_progress: '#3B82F6',
      completed: '#10B981',
      cancelled: '#EF4444',
    };

    return colors[status] || '#6B7280';
  }
}
