/**
 * API Client for GIS Services
 * Production-ready API client with proper error handling and retries
 */

import { getConfig } from '../config/production';
import { logger } from '../utils/logger';
import type {
  Territory,
  ServiceArea,
  NetworkNode,
  TechnicianInfo,
  WorkOrderInfo,
  Coordinates,
  SearchResult,
} from '../types';

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  code?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

export class ApiClient {
  private config = getConfig();
  private baseUrl: string;
  private timeout: number;
  private retryAttempts: number;

  constructor(baseUrl?: string) {
    this.baseUrl = baseUrl || this.config.api.baseUrl;
    this.timeout = this.config.api.timeout;
    this.retryAttempts = this.config.api.retryAttempts;
  }

  private async makeRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`;
    let lastError: Error;

    for (let attempt = 0; attempt <= this.retryAttempts; attempt++) {
      try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.timeout);

        const response = await fetch(url, {
          ...options,
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
            ...options.headers,
          },
        });

        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();

        logger.debug('ApiClient', `Request successful: ${endpoint}`, {
          attempt: attempt + 1,
          status: response.status,
        });

        return { success: true, data };
      } catch (error) {
        lastError = error as Error;

        logger.warn('ApiClient', `Request failed: ${endpoint}`, {
          attempt: attempt + 1,
          error: lastError.message,
          willRetry: attempt < this.retryAttempts,
        });

        if (attempt < this.retryAttempts) {
          // Exponential backoff
          const delay = Math.pow(2, attempt) * 1000;
          await new Promise((resolve) => setTimeout(resolve, delay));
        }
      }
    }

    logger.error('ApiClient', `All retry attempts failed for: ${endpoint}`, lastError);

    return {
      success: false,
      error: 'Network request failed after retries',
      code: 'NETWORK_ERROR',
    };
  }

  // Territory APIs
  async getTerritories(params?: {
    page?: number;
    pageSize?: number;
    region?: string;
  }): Promise<ApiResponse<PaginatedResponse<Territory>>> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.pageSize) searchParams.set('pageSize', params.pageSize.toString());
    if (params?.region) searchParams.set('region', params.region);

    const endpoint = `/territories?${searchParams.toString()}`;
    return this.makeRequest<PaginatedResponse<Territory>>(endpoint);
  }

  async getTerritory(id: string): Promise<ApiResponse<Territory>> {
    return this.makeRequest<Territory>(`/territories/${id}`);
  }

  async createTerritory(territory: Omit<Territory, 'id'>): Promise<ApiResponse<Territory>> {
    return this.makeRequest<Territory>('/territories', {
      method: 'POST',
      body: JSON.stringify(territory),
    });
  }

  async updateTerritory(id: string, updates: Partial<Territory>): Promise<ApiResponse<Territory>> {
    return this.makeRequest<Territory>(`/territories/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  }

  // Service Area APIs
  async getServiceAreas(territoryId?: string): Promise<ApiResponse<ServiceArea[]>> {
    const endpoint = territoryId ? `/service-areas?territoryId=${territoryId}` : '/service-areas';
    return this.makeRequest<ServiceArea[]>(endpoint);
  }

  async createServiceArea(area: Omit<ServiceArea, 'id'>): Promise<ApiResponse<ServiceArea>> {
    return this.makeRequest<ServiceArea>('/service-areas', {
      method: 'POST',
      body: JSON.stringify(area),
    });
  }

  // Network Infrastructure APIs
  async getNetworkNodes(params?: {
    type?: NetworkNode['type'];
    status?: NetworkNode['status'];
    bounds?: { north: number; south: number; east: number; west: number };
  }): Promise<ApiResponse<NetworkNode[]>> {
    const searchParams = new URLSearchParams();
    if (params?.type) searchParams.set('type', params.type);
    if (params?.status) searchParams.set('status', params.status);
    if (params?.bounds) {
      searchParams.set('bounds', JSON.stringify(params.bounds));
    }

    const endpoint = `/network-nodes?${searchParams.toString()}`;
    return this.makeRequest<NetworkNode[]>(endpoint);
  }

  async updateNetworkNode(
    id: string,
    updates: Partial<NetworkNode>
  ): Promise<ApiResponse<NetworkNode>> {
    return this.makeRequest<NetworkNode>(`/network-nodes/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(updates),
    });
  }

  // Demographics and Coverage APIs
  async getDemographics(area: { coordinates: Coordinates[] }): Promise<
    ApiResponse<{
      population: number;
      households: number;
      businesses: number;
      medianIncome: number;
      internetAdoption: number;
    }>
  > {
    return this.makeRequest('/demographics', {
      method: 'POST',
      body: JSON.stringify({ area }),
    });
  }

  async analyzeCoverage(params: {
    area: { coordinates: Coordinates[] };
    serviceTypes: string[];
  }): Promise<
    ApiResponse<{
      coveragePercentage: number;
      gaps: Array<{
        polygon: { coordinates: Coordinates[] };
        severity: string;
        affectedCustomers: number;
      }>;
    }>
  > {
    return this.makeRequest('/coverage/analyze', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  // Route Optimization APIs
  async optimizeRoutes(params: {
    technicians: TechnicianInfo[];
    workOrders: WorkOrderInfo[];
    constraints: any;
  }): Promise<
    ApiResponse<{
      routes: Array<{
        technicianId: string;
        waypoints: Coordinates[];
        workOrders: string[];
        estimatedTime: number;
        distance: number;
      }>;
      unassigned: string[];
      savings: {
        timeReduction: number;
        fuelSavings: number;
      };
    }>
  > {
    return this.makeRequest('/routes/optimize', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async calculateRoute(waypoints: Coordinates[]): Promise<
    ApiResponse<{
      route: Coordinates[];
      distance: number;
      duration: number;
      instructions: string[];
    }>
  > {
    return this.makeRequest('/routes/calculate', {
      method: 'POST',
      body: JSON.stringify({ waypoints }),
    });
  }

  // Geocoding APIs
  async geocode(address: string): Promise<
    ApiResponse<{
      coordinates: Coordinates;
      formattedAddress: string;
      confidence: number;
    }>
  > {
    return this.makeRequest(`/geocoding/forward?address=${encodeURIComponent(address)}`);
  }

  async reverseGeocode(coordinates: Coordinates): Promise<
    ApiResponse<{
      address: string;
      components: {
        street?: string;
        city?: string;
        state?: string;
        country?: string;
        postalCode?: string;
      };
    }>
  > {
    const { lat, lng } = coordinates;
    return this.makeRequest(`/geocoding/reverse?lat=${lat}&lng=${lng}`);
  }

  // Search APIs
  async search(params: {
    query: string;
    type: 'address' | 'customer' | 'asset' | 'territory';
    bounds?: { north: number; south: number; east: number; west: number };
    limit?: number;
  }): Promise<ApiResponse<SearchResult[]>> {
    const searchParams = new URLSearchParams({
      query: params.query,
      type: params.type,
    });

    if (params.bounds) searchParams.set('bounds', JSON.stringify(params.bounds));
    if (params.limit) searchParams.set('limit', params.limit.toString());

    return this.makeRequest<SearchResult[]>(`/search?${searchParams.toString()}`);
  }

  // Customer APIs
  async getCustomersInArea(area: { coordinates: Coordinates[] }): Promise<
    ApiResponse<
      Array<{
        id: string;
        name: string;
        location: Coordinates;
        plan: string;
        status: string;
        revenue: number;
      }>
    >
  > {
    return this.makeRequest('/customers/in-area', {
      method: 'POST',
      body: JSON.stringify({ area }),
    });
  }

  // Competitor Analysis APIs
  async getCompetitorData(territoryId: string): Promise<
    ApiResponse<
      Array<{
        name: string;
        serviceTypes: string[];
        coverage: number;
        marketShare: number;
        strengths: string[];
        weaknesses: string[];
        pricing: {
          residential: { min: number; max: number };
          business: { min: number; max: number };
        };
      }>
    >
  > {
    return this.makeRequest(`/competitors?territoryId=${territoryId}`);
  }

  // Maintenance and Asset APIs
  async getMaintenanceAssets(params?: {
    type?: string;
    priority?: string;
    lastMaintenance?: string;
  }): Promise<
    ApiResponse<
      Array<{
        id: string;
        location: Coordinates;
        type: string;
        priority: number;
        lastMaintenance: string;
        nextScheduled?: string;
      }>
    >
  > {
    const searchParams = new URLSearchParams();
    if (params?.type) searchParams.set('type', params.type);
    if (params?.priority) searchParams.set('priority', params.priority);
    if (params?.lastMaintenance) searchParams.set('lastMaintenance', params.lastMaintenance);

    return this.makeRequest(`/maintenance/assets?${searchParams.toString()}`);
  }

  // Health check
  async healthCheck(): Promise<ApiResponse<{ status: string; timestamp: string }>> {
    return this.makeRequest('/health');
  }
}

// Export singleton instance
export const apiClient = new ApiClient();
