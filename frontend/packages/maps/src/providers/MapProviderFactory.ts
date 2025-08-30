/**
 * Map Provider Factory
 * Creates and manages different map provider instances
 */

import { MapProvider } from './MapProvider';
import { LeafletProvider } from './LeafletProvider';
import { MockProvider } from './MockProvider';
import type {
  MapConfig,
  MapProviderType,
  MapProviderConfig,
  PortalType,
  PortalContext
} from '../types';

export interface MapProviderFactoryConfig {
  defaultProvider: MapProviderType;
  fallbackProvider?: MapProviderType;
  apiKeys?: Record<string, string>;
  enableFallback?: boolean;
  cacheProviders?: boolean;
}

export class MapProviderFactory {
  private static instance: MapProviderFactory;
  private config: MapProviderFactoryConfig;
  private providerCache: Map<string, MapProvider> = new Map();

  private constructor(config: MapProviderFactoryConfig) {
    this.config = config;
  }

  /**
   * Get or create the factory instance
   */
  static getInstance(config?: MapProviderFactoryConfig): MapProviderFactory {
    if (!MapProviderFactory.instance) {
      if (!config) {
        throw new Error('MapProviderFactory requires initial configuration');
      }
      MapProviderFactory.instance = new MapProviderFactory(config);
    }
    return MapProviderFactory.instance;
  }

  /**
   * Create a map provider instance
   */
  async createProvider(
    providerConfig: MapProviderConfig,
    mapConfig: MapConfig,
    portalContext?: PortalContext
  ): Promise<MapProvider> {
    try {
      const cacheKey = this.generateCacheKey(providerConfig, mapConfig);

      // Return cached provider if caching is enabled
      if (this.config.cacheProviders && this.providerCache.has(cacheKey)) {
        const cachedProvider = this.providerCache.get(cacheKey)!;
        if (!cachedProvider.isDestroyed) {
          return cachedProvider;
        } else {
          this.providerCache.delete(cacheKey);
        }
      }

      // Create new provider
      let provider: MapProvider;

      switch (providerConfig.type) {
        case 'leaflet':
          provider = new LeafletProvider(mapConfig);
          break;

        case 'google':
          // GoogleMapsProvider would be implemented here
          throw new Error('Google Maps provider not yet implemented');

        case 'mapbox':
          // MapboxProvider would be implemented here
          throw new Error('Mapbox provider not yet implemented');

        case 'mock':
          provider = new MockProvider(mapConfig);
          break;

        default:
          throw new Error(`Unknown provider type: ${providerConfig.type}`);
      }

      // Apply portal-specific configurations
      if (portalContext) {
        this.configureForPortal(provider, portalContext);
      }

      // Cache the provider if enabled
      if (this.config.cacheProviders) {
        this.providerCache.set(cacheKey, provider);
      }

      return provider;

    } catch (error) {
      // Fallback to alternative provider if enabled
      if (this.config.enableFallback &&
          this.config.fallbackProvider &&
          providerConfig.type !== this.config.fallbackProvider) {

        console.warn(`Failed to create ${providerConfig.type} provider, falling back to ${this.config.fallbackProvider}:`, error);

        return this.createProvider(
          { ...providerConfig, type: this.config.fallbackProvider },
          mapConfig,
          portalContext
        );
      }

      throw new Error(`Failed to create map provider: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }

  /**
   * Create provider with default configuration for portal type
   */
  async createForPortal(
    portalType: PortalType,
    mapConfig: MapConfig,
    portalContext?: PortalContext
  ): Promise<MapProvider> {
    const providerConfig = this.getDefaultProviderConfig(portalType);
    return this.createProvider(providerConfig, mapConfig, portalContext);
  }

  /**
   * Get recommended provider configuration for portal type
   */
  getDefaultProviderConfig(portalType: PortalType): MapProviderConfig {
    // Different portals might have different provider preferences
    const portalProviderMap: Record<PortalType, MapProviderConfig> = {
      'management-admin': {
        type: this.config.defaultProvider,
        maxZoom: 18,
        retina: true,
        attribution: 'ISP Management Platform'
      },
      'admin': {
        type: this.config.defaultProvider,
        maxZoom: 18,
        retina: true,
        attribution: 'ISP Admin Portal'
      },
      'customer': {
        type: this.config.defaultProvider,
        maxZoom: 16, // Lower max zoom for customers
        retina: false, // Lower resource usage
        attribution: 'Customer Portal'
      },
      'reseller': {
        type: this.config.defaultProvider,
        maxZoom: 17,
        retina: true,
        attribution: 'Reseller Portal'
      },
      'technician': {
        type: this.config.defaultProvider,
        maxZoom: 20, // Highest detail for field work
        retina: true,
        attribution: 'Technician Portal'
      }
    };

    const baseConfig = portalProviderMap[portalType];

    // Add API key if available
    if (this.config.apiKeys?.[baseConfig.type]) {
      baseConfig.apiKey = this.config.apiKeys[baseConfig.type];
    }

    return baseConfig;
  }

  /**
   * Configure provider for specific portal requirements
   */
  private configureForPortal(provider: MapProvider, portalContext: PortalContext): void {
    // Portal-specific configurations
    switch (portalContext.portalType) {
      case 'management-admin':
        // Full administrative access
        provider.enableKeyboardNavigation();
        break;

      case 'admin':
        // ISP admin configurations
        provider.enableKeyboardNavigation();
        break;

      case 'customer':
        // Limited interaction for customers
        provider.setAriaLabel('Service coverage map');
        // Might disable certain interactions
        break;

      case 'reseller':
        // Territory-focused configurations
        provider.enableKeyboardNavigation();
        provider.setAriaLabel('Territory management map');
        break;

      case 'technician':
        // Field-work optimized configurations
        provider.enableKeyboardNavigation();
        provider.setAriaLabel('Work order and route map');
        // Enable GPS features if available
        break;
    }

    // Apply user preferences if available
    if (portalContext.preferences?.mapSettings) {
      const prefs = portalContext.preferences.mapSettings;

      if (prefs.keyboardNavigation === false) {
        provider.disableKeyboardNavigation();
      }
    }
  }

  /**
   * Generate cache key for provider instances
   */
  private generateCacheKey(providerConfig: MapProviderConfig, mapConfig: MapConfig): string {
    const configHash = {
      providerType: providerConfig.type,
      apiKey: providerConfig.apiKey ? 'hasKey' : 'noKey',
      maxZoom: providerConfig.maxZoom,
      retina: providerConfig.retina,
      zoom: mapConfig.zoom,
      centerLat: Math.round(mapConfig.center.lat * 1000), // Round to avoid cache misses
      centerLng: Math.round(mapConfig.center.lng * 1000)
    };

    return JSON.stringify(configHash);
  }

  /**
   * Clear provider cache
   */
  clearCache(): void {
    // Destroy cached providers
    this.providerCache.forEach(provider => {
      if (!provider.isDestroyed) {
        provider.destroy().catch(err =>
          console.warn('Error destroying cached provider:', err)
        );
      }
    });

    this.providerCache.clear();
  }

  /**
   * Get cache statistics
   */
  getCacheStats(): { size: number; activeProviders: number; destroyedProviders: number } {
    let activeProviders = 0;
    let destroyedProviders = 0;

    this.providerCache.forEach(provider => {
      if (provider.isDestroyed) {
        destroyedProviders++;
      } else {
        activeProviders++;
      }
    });

    return {
      size: this.providerCache.size,
      activeProviders,
      destroyedProviders
    };
  }

  /**
   * Update factory configuration
   */
  updateConfig(updates: Partial<MapProviderFactoryConfig>): void {
    this.config = { ...this.config, ...updates };
  }

  /**
   * Get current configuration
   */
  getConfig(): MapProviderFactoryConfig {
    return { ...this.config };
  }

  /**
   * Check if a provider type is available
   */
  isProviderAvailable(providerType: MapProviderType): boolean {
    switch (providerType) {
      case 'leaflet':
        return true; // Always available
      case 'mock':
        return true; // Always available
      case 'google':
        return !!this.config.apiKeys?.google;
      case 'mapbox':
        return !!this.config.apiKeys?.mapbox;
      default:
        return false;
    }
  }

  /**
   * Get list of available providers
   */
  getAvailableProviders(): MapProviderType[] {
    const allProviders: MapProviderType[] = ['leaflet', 'google', 'mapbox', 'mock'];
    return allProviders.filter(provider => this.isProviderAvailable(provider));
  }

  /**
   * Validate provider configuration
   */
  validateProviderConfig(config: MapProviderConfig): { valid: boolean; errors: string[] } {
    const errors: string[] = [];

    if (!config.type) {
      errors.push('Provider type is required');
    }

    if (!this.isProviderAvailable(config.type)) {
      errors.push(`Provider ${config.type} is not available`);
    }

    if (config.type === 'google' && !config.apiKey) {
      errors.push('Google Maps requires an API key');
    }

    if (config.type === 'mapbox' && !config.apiKey) {
      errors.push('Mapbox requires an API key');
    }

    if (config.maxZoom && (config.maxZoom < 1 || config.maxZoom > 25)) {
      errors.push('Max zoom must be between 1 and 25');
    }

    return {
      valid: errors.length === 0,
      errors
    };
  }

  /**
   * Test provider connectivity
   */
  async testProvider(providerType: MapProviderType): Promise<{ success: boolean; error?: string }> {
    try {
      const testConfig: MapConfig = {
        center: { lat: 37.7749, lng: -122.4194 },
        zoom: 10
      };

      const providerConfig = { type: providerType };
      const provider = await this.createProvider(providerConfig, testConfig);

      // Test basic functionality
      const center = provider.getCenter();
      const zoom = provider.getZoom();

      // Clean up test provider
      await provider.destroy();

      return { success: true };
    } catch (error) {
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * Destroy the factory and clean up resources
   */
  destroy(): void {
    this.clearCache();
    MapProviderFactory.instance = null as any;
  }
}
