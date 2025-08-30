/**
 * Universal GIS/Mapping System
 * Main entry point for the maps package
 */

// Types
export * from './types';

// Map Providers
export { MapProvider } from './providers/MapProvider';
export { LeafletProvider } from './providers/LeafletProvider';
export { MockProvider } from './providers/MockProvider';
export { MapProviderFactory } from './providers/MapProviderFactory';

// GIS Business Logic Engines
export { ServiceCoverageEngine } from './engines/ServiceCoverageEngine';
export { ProductionServiceCoverageEngine } from './engines/ProductionServiceCoverageEngine';
export { TerritoryEngine } from './engines/TerritoryEngine';
export { RouteOptimizationEngine } from './engines/RouteOptimizationEngine';

// Production utilities
export { logger } from './utils/logger';
export { apiClient } from './services/ApiClient';
export { getConfig, PRODUCTION_CONFIG, DEVELOPMENT_CONFIG } from './config/production';

// Import for internal use
import { ServiceCoverageEngine } from './engines/ServiceCoverageEngine';
import { ProductionServiceCoverageEngine } from './engines/ProductionServiceCoverageEngine';
import { TerritoryEngine } from './engines/TerritoryEngine';
import { RouteOptimizationEngine } from './engines/RouteOptimizationEngine';
import { getConfig } from './config/production';

// Main Map Factory class for easy integration
export class UniversalMappingSystem {
  private static instance: UniversalMappingSystem;
  private providerFactory: MapProviderFactory;

  private constructor() {
    // Initialize with sensible defaults
    this.providerFactory = MapProviderFactory.getInstance({
      defaultProvider: 'leaflet',
      fallbackProvider: 'mock',
      enableFallback: true,
      cacheProviders: true
    });
  }

  /**
   * Get the singleton instance
   */
  static getInstance(): UniversalMappingSystem {
    if (!UniversalMappingSystem.instance) {
      UniversalMappingSystem.instance = new UniversalMappingSystem();
    }
    return UniversalMappingSystem.instance;
  }

  /**
   * Get the map provider factory
   */
  getProviderFactory(): MapProviderFactory {
    return this.providerFactory;
  }

  /**
   * Quick method to create a map provider for a specific portal
   */
  async createMapForPortal(
    portalType: import('./types').PortalType,
    container: HTMLElement,
    config?: Partial<import('./types').MapConfig>
  ) {
    const defaultConfig: import('./types').MapConfig = {
      center: { lat: 37.7749, lng: -122.4194 },
      zoom: 10,
      scrollWheelZoom: true,
      dragging: true,
      zoomControl: true,
      ...config
    };

    const provider = await this.providerFactory.createForPortal(
      portalType,
      defaultConfig
    );

    await provider.initialize(container);
    return provider;
  }

  /**
   * Create GIS business logic engines (production-ready)
   */
  createEngines(portalContext: import('./types').PortalContext) {
    const config = getConfig();

    return {
      serviceCoverage: config.api.enableMockData ?
        new ServiceCoverageEngine(portalContext) :
        new ProductionServiceCoverageEngine(portalContext),
      territory: new TerritoryEngine(portalContext),
      routeOptimization: new RouteOptimizationEngine(portalContext)
    };
  }

  /**
   * Clean up all resources
   */
  destroy() {
    this.providerFactory.destroy();
    UniversalMappingSystem.instance = null as any;
  }
}

// Export the singleton for easy access
export const mappingSystem = UniversalMappingSystem.getInstance();
