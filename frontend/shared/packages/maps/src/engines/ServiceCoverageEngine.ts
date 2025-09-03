/**
 * Service Coverage Analysis Engine
 * Provides comprehensive service coverage calculations and analysis
 */

import * as turf from '@turf/turf';
import type {
  ServiceArea,
  Territory,
  CoverageResult,
  Gap,
  CoverageRecommendation,
  Coordinates,
  Polygon,
  PortalContext,
} from '../types';

export interface CoverageConstraints {
  maxBuildoutCost?: number;
  minExpectedCustomers?: number;
  maxTimeframe?: number; // months
  priorityAreas?: string[];
  excludeAreas?: string[];
  serviceTypes?: string[];
  coverageThreshold?: number; // minimum acceptable coverage percentage
}

export interface DemographicData {
  area: Polygon;
  population: number;
  households: number;
  businesses: number;
  medianIncome: number;
  internetAdoption: number; // percentage
  competitorPresence: boolean;
  existingInfrastructure: {
    fiber: boolean;
    cable: boolean;
    wireless: boolean;
  };
}

export interface InfrastructureAsset {
  id: string;
  type: 'fiber_node' | 'tower' | 'cabinet' | 'splice_point' | 'headend';
  position: Coordinates;
  capacity: number;
  utilization: number;
  serviceRadius: number; // meters
  status: 'active' | 'planned' | 'maintenance' | 'decommissioned';
  technologies: string[];
}

export class ServiceCoverageEngine {
  private portalContext: PortalContext;
  private demographicCache: Map<string, DemographicData> = new Map();
  private infrastructureCache: Map<string, InfrastructureAsset[]> = new Map();

  constructor(portalContext: PortalContext) {
    this.portalContext = portalContext;
  }

  /**
   * Calculate comprehensive coverage analysis for a given area
   */
  async calculateCoverage(
    area: Polygon,
    serviceTypes: string[] = ['fiber', 'wireless'],
    constraints?: CoverageConstraints
  ): Promise<CoverageResult> {
    try {
      // Validate permissions
      this.validatePermissions('coverage:calculate');

      // Get demographic data for the area
      const demographics = await this.getDemographicData(area);

      // Get existing infrastructure in the area
      const infrastructure = await this.getInfrastructureInArea(area);

      // Calculate current coverage
      const currentCoverage = this.calculateCurrentCoverage(area, infrastructure, serviceTypes);

      // Identify coverage gaps
      const gaps = this.identifyCoverageGaps(area, currentCoverage, demographics, constraints);

      // Generate recommendations
      const recommendations = await this.generateCoverageRecommendations(
        gaps,
        infrastructure,
        demographics,
        constraints
      );

      // Calculate metrics
      const areaSize = turf.area(this.polygonToTurf(area)) / 1000000; // km²
      const coveragePercentage = this.calculateCoveragePercentage(area, currentCoverage);

      return {
        area: areaSize,
        population: demographics.population,
        households: demographics.households,
        businesses: demographics.businesses,
        coveragePercentage,
        serviceTypes,
        gaps,
        recommendations,
      };
    } catch (error) {
      throw this.handleError(error, 'calculateCoverage');
    }
  }

  /**
   * Find service gaps across multiple territories
   */
  async findServiceGaps(territories: Territory[]): Promise<Gap[]> {
    try {
      this.validatePermissions('gaps:analyze');

      const allGaps: Gap[] = [];

      for (const territory of territories) {
        const coverage = await this.calculateCoverage(territory.polygon);
        allGaps.push(...coverage.gaps);
      }

      // Sort gaps by priority and potential impact
      return allGaps.sort((a, b) => {
        // Primary sort: severity
        const severityWeight = { critical: 4, high: 3, medium: 2, low: 1 };
        const severityDiff = severityWeight[b.severity] - severityWeight[a.severity];
        if (severityDiff !== 0) return severityDiff;

        // Secondary sort: affected customers
        return b.affectedCustomers - a.affectedCustomers;
      });
    } catch (error) {
      throw this.handleError(error, 'findServiceGaps');
    }
  }

  /**
   * Optimize service areas based on constraints and objectives
   */
  async optimizeServiceAreas(
    currentAreas: ServiceArea[],
    constraints: CoverageConstraints
  ): Promise<ServiceArea[]> {
    try {
      this.validatePermissions('optimization:run');

      // Analyze current performance
      const currentMetrics = await this.analyzeCurrentAreas(currentAreas);

      // Identify optimization opportunities
      const opportunities = this.identifyOptimizationOpportunities(
        currentAreas,
        currentMetrics,
        constraints
      );

      // Generate optimized areas
      const optimizedAreas = await this.generateOptimizedAreas(
        currentAreas,
        opportunities,
        constraints
      );

      // Validate optimizations
      const validatedAreas = this.validateOptimizations(optimizedAreas, constraints);

      return validatedAreas;
    } catch (error) {
      throw this.handleError(error, 'optimizeServiceAreas');
    }
  }

  /**
   * Calculate buildout cost for expanding coverage to specific areas
   */
  async calculateBuildoutCost(
    targetAreas: Polygon[],
    serviceType: string = 'fiber'
  ): Promise<{
    totalCost: number;
    costPerArea: { area: Polygon; cost: number; details: any }[];
    timeline: { phase: string; duration: number; cost: number }[];
  }> {
    try {
      this.validatePermissions('cost:calculate');

      const costPerArea: { area: Polygon; cost: number; details: any }[] = [];
      let totalCost = 0;

      for (const area of targetAreas) {
        const areaCost = await this.calculateAreaBuildoutCost(area, serviceType);
        costPerArea.push(areaCost);
        totalCost += areaCost.cost;
      }

      // Generate timeline
      const timeline = this.generateBuildoutTimeline(costPerArea, serviceType);

      return {
        totalCost,
        costPerArea,
        timeline,
      };
    } catch (error) {
      throw this.handleError(error, 'calculateBuildoutCost');
    }
  }

  /**
   * Analyze competitive landscape in coverage areas
   */
  async analyzeCompetitorCoverage(
    areas: Polygon[],
    competitors: string[] = []
  ): Promise<{
    overlapAnalysis: {
      area: Polygon;
      competitors: string[];
      overlapPercentage: number;
      competitiveAdvantage: string[];
    }[];
    marketOpportunities: {
      area: Polygon;
      opportunity: string;
      priority: 'low' | 'medium' | 'high';
      estimatedCustomers: number;
    }[];
  }> {
    try {
      this.validatePermissions('competitor:analyze');

      const overlapAnalysis = await Promise.all(
        areas.map((area) => this.analyzeAreaCompetition(area, competitors))
      );

      const marketOpportunities = this.identifyMarketOpportunities(overlapAnalysis);

      return {
        overlapAnalysis,
        marketOpportunities,
      };
    } catch (error) {
      throw this.handleError(error, 'analyzeCompetitorCoverage');
    }
  }

  // Private helper methods

  private calculateCurrentCoverage(
    area: Polygon,
    infrastructure: InfrastructureAsset[],
    serviceTypes: string[]
  ): Polygon[] {
    const coverageAreas: Polygon[] = [];

    infrastructure.forEach((asset) => {
      if (
        asset.status === 'active' &&
        asset.technologies.some((tech) => serviceTypes.includes(tech))
      ) {
        // Create service area around infrastructure asset
        const serviceArea = this.createServiceArea(asset);

        // Clip to the analysis area
        const clippedArea = this.clipPolygon(serviceArea, area);
        if (clippedArea) {
          coverageAreas.push(clippedArea);
        }
      }
    });

    // Merge overlapping coverage areas
    return this.mergePolygons(coverageAreas);
  }

  private identifyCoverageGaps(
    area: Polygon,
    currentCoverage: Polygon[],
    demographics: DemographicData,
    constraints?: CoverageConstraints
  ): Gap[] {
    const gaps: Gap[] = [];

    // Calculate uncovered area
    const uncoveredArea = this.subtractPolygons(area, currentCoverage);

    if (!uncoveredArea || uncoveredArea.coordinates.length === 0) {
      return gaps;
    }

    // Analyze uncovered areas
    const gapId = `gap_${Date.now()}`;
    const affectedCustomers = this.estimateCustomersInArea(uncoveredArea, demographics);
    const potentialRevenue = this.calculatePotentialRevenue(affectedCustomers);
    const buildoutCost = this.estimateBuildoutCost(uncoveredArea);

    const severity = this.calculateGapSeverity(affectedCustomers, potentialRevenue, buildoutCost);

    gaps.push({
      id: gapId,
      polygon: uncoveredArea,
      type: 'no_coverage',
      severity,
      affectedCustomers,
      potentialRevenue,
      buildoutCost,
      priority: this.calculateGapPriority(severity, potentialRevenue, buildoutCost),
      recommendations: this.generateGapRecommendations(uncoveredArea, demographics),
    });

    return gaps;
  }

  private async generateCoverageRecommendations(
    gaps: Gap[],
    infrastructure: InfrastructureAsset[],
    demographics: DemographicData,
    constraints?: CoverageConstraints
  ): Promise<CoverageRecommendation[]> {
    const recommendations: CoverageRecommendation[] = [];

    for (const gap of gaps) {
      // Infrastructure recommendations
      const infraRecommendations = this.generateInfrastructureRecommendations(gap, infrastructure);
      recommendations.push(...infraRecommendations);

      // Service recommendations
      const serviceRecommendations = this.generateServiceRecommendations(gap, demographics);
      recommendations.push(...serviceRecommendations);

      // Marketing recommendations
      const marketingRecommendations = this.generateMarketingRecommendations(gap, demographics);
      recommendations.push(...marketingRecommendations);

      // Partnership recommendations
      const partnershipRecommendations = this.generatePartnershipRecommendations(gap, demographics);
      recommendations.push(...partnershipRecommendations);
    }

    // Filter and prioritize recommendations based on constraints
    return this.filterRecommendationsByConstraints(recommendations, constraints);
  }

  private createServiceArea(asset: InfrastructureAsset): Polygon {
    // Create circular service area around infrastructure asset
    const center = turf.point([asset.position.lng, asset.position.lat]);
    const radius = asset.serviceRadius / 1000; // Convert to km
    const circle = turf.buffer(center, radius, { units: 'kilometers' });

    return this.turfToPolygon(circle);
  }

  private clipPolygon(polygon1: Polygon, polygon2: Polygon): Polygon | null {
    try {
      const turf1 = this.polygonToTurf(polygon1);
      const turf2 = this.polygonToTurf(polygon2);
      const intersection = turf.intersect(turf1, turf2);

      return intersection ? this.turfToPolygon(intersection) : null;
    } catch {
      return null;
    }
  }

  private mergePolygons(polygons: Polygon[]): Polygon[] {
    if (polygons.length === 0) return [];
    if (polygons.length === 1) return polygons;

    try {
      let union = this.polygonToTurf(polygons[0]);

      for (let i = 1; i < polygons.length; i++) {
        const nextPolygon = this.polygonToTurf(polygons[i]);
        const merged = turf.union(union, nextPolygon);
        if (merged) {
          union = merged;
        }
      }

      return [this.turfToPolygon(union)];
    } catch {
      // Fallback: return original polygons if union fails
      return polygons;
    }
  }

  private subtractPolygons(minuend: Polygon, subtrahends: Polygon[]): Polygon | null {
    if (subtrahends.length === 0) return minuend;

    try {
      let result = this.polygonToTurf(minuend);

      for (const subtrahend of subtrahends) {
        const turfSubtrahend = this.polygonToTurf(subtrahend);
        const difference = turf.difference(result, turfSubtrahend);
        if (difference) {
          result = difference;
        } else {
          return null; // Complete subtraction
        }
      }

      return this.turfToPolygon(result);
    } catch {
      return null;
    }
  }

  private calculateCoveragePercentage(totalArea: Polygon, coveredAreas: Polygon[]): number {
    try {
      const totalAreaSize = turf.area(this.polygonToTurf(totalArea));

      if (totalAreaSize === 0) return 0;

      let coveredAreaSize = 0;
      for (const covered of coveredAreas) {
        coveredAreaSize += turf.area(this.polygonToTurf(covered));
      }

      return Math.min(100, (coveredAreaSize / totalAreaSize) * 100);
    } catch {
      return 0;
    }
  }

  private estimateCustomersInArea(area: Polygon, demographics: DemographicData): number {
    try {
      const areaSize = turf.area(this.polygonToTurf(area)) / 1000000; // km²
      const totalAreaSize = turf.area(this.polygonToTurf(demographics.area)) / 1000000; // km²

      const proportion = areaSize / totalAreaSize;
      return Math.round((demographics.households + demographics.businesses) * proportion);
    } catch {
      return 0;
    }
  }

  private calculatePotentialRevenue(customers: number): number {
    // Average monthly revenue per customer (configurable)
    const avgMonthlyRevenue = this.portalContext.preferences?.avgRevenuePerCustomer || 75;
    return customers * avgMonthlyRevenue * 12; // Annual revenue
  }

  private estimateBuildoutCost(area: Polygon): number {
    try {
      const areaSize = turf.area(this.polygonToTurf(area)) / 1000000; // km²
      // Cost per km² (configurable)
      const costPerKm2 = this.portalContext.preferences?.buildoutCostPerKm2 || 50000;
      return areaSize * costPerKm2;
    } catch {
      return 0;
    }
  }

  private calculateGapSeverity(
    affectedCustomers: number,
    potentialRevenue: number,
    buildoutCost: number
  ): 'low' | 'medium' | 'high' | 'critical' {
    const roi = potentialRevenue > 0 ? (potentialRevenue - buildoutCost) / buildoutCost : -1;

    if (affectedCustomers >= 1000 && roi > 0.5) return 'critical';
    if (affectedCustomers >= 500 && roi > 0.25) return 'high';
    if (affectedCustomers >= 100 && roi > 0) return 'medium';
    return 'low';
  }

  private calculateGapPriority(
    severity: 'low' | 'medium' | 'high' | 'critical',
    potentialRevenue: number,
    buildoutCost: number
  ): number {
    const severityScore = { low: 1, medium: 2, high: 3, critical: 4 };
    const roi = potentialRevenue > 0 ? (potentialRevenue - buildoutCost) / buildoutCost : -1;

    return severityScore[severity] * 10 + Math.min(10, Math.max(0, roi * 10));
  }

  private generateGapRecommendations(area: Polygon, demographics: DemographicData): string[] {
    const recommendations: string[] = [];

    if (demographics.population > 10000) {
      recommendations.push('High density area - prioritize fiber deployment');
    }

    if (demographics.businesses > 100) {
      recommendations.push('Business concentration - consider dedicated business services');
    }

    if (demographics.medianIncome > 75000) {
      recommendations.push('High income area - premium service tier opportunity');
    }

    if (!demographics.competitorPresence) {
      recommendations.push('First-mover advantage - accelerate deployment');
    }

    return recommendations;
  }

  // Utility methods for geometric operations
  private polygonToTurf(polygon: Polygon): any {
    const coordinates = polygon.coordinates.map((coord) => [coord.lng, coord.lat]);
    // Close the polygon if not already closed
    if (coordinates[0] !== coordinates[coordinates.length - 1]) {
      coordinates.push(coordinates[0]);
    }
    return turf.polygon([coordinates]);
  }

  private turfToPolygon(turfGeometry: any): Polygon {
    const coordinates = turfGeometry.geometry.coordinates[0];
    return {
      coordinates: coordinates.slice(0, -1).map((coord: number[]) => ({
        lat: coord[1],
        lng: coord[0],
      })),
    };
  }

  // Mock data methods (would be replaced with real API calls)
  private async getDemographicData(area: Polygon): Promise<DemographicData> {
    const cacheKey = JSON.stringify(area);

    if (this.demographicCache.has(cacheKey)) {
      return this.demographicCache.get(cacheKey)!;
    }

    // Mock demographic data
    const data: DemographicData = {
      area,
      population: Math.floor(Math.random() * 50000) + 10000,
      households: Math.floor(Math.random() * 20000) + 5000,
      businesses: Math.floor(Math.random() * 1000) + 100,
      medianIncome: Math.floor(Math.random() * 50000) + 50000,
      internetAdoption: Math.random() * 30 + 70, // 70-100%
      competitorPresence: Math.random() > 0.6,
      existingInfrastructure: {
        fiber: Math.random() > 0.7,
        cable: Math.random() > 0.3,
        wireless: Math.random() > 0.5,
      },
    };

    this.demographicCache.set(cacheKey, data);
    return data;
  }

  private async getInfrastructureInArea(area: Polygon): Promise<InfrastructureAsset[]> {
    // Mock infrastructure data
    const assets: InfrastructureAsset[] = [];
    const numAssets = Math.floor(Math.random() * 10) + 5;

    for (let i = 0; i < numAssets; i++) {
      // Generate random point within area bounds
      const bounds = this.calculatePolygonBounds(area);
      const lat = bounds.south + Math.random() * (bounds.north - bounds.south);
      const lng = bounds.west + Math.random() * (bounds.east - bounds.west);

      assets.push({
        id: `asset_${i}`,
        type: ['fiber_node', 'tower', 'cabinet'][Math.floor(Math.random() * 3)] as any,
        position: { lat, lng },
        capacity: Math.floor(Math.random() * 1000) + 100,
        utilization: Math.random() * 100,
        serviceRadius: Math.floor(Math.random() * 2000) + 500,
        status: ['active', 'planned'][Math.floor(Math.random() * 2)] as any,
        technologies: ['fiber', 'wireless', 'cable'].filter(() => Math.random() > 0.5),
      });
    }

    return assets;
  }

  private calculatePolygonBounds(polygon: Polygon) {
    let north = -90,
      south = 90,
      east = -180,
      west = 180;

    polygon.coordinates.forEach((coord) => {
      north = Math.max(north, coord.lat);
      south = Math.min(south, coord.lat);
      east = Math.max(east, coord.lng);
      west = Math.min(west, coord.lng);
    });

    return { north, south, east, west };
  }

  // Stub methods for complex analysis operations
  private async analyzeCurrentAreas(areas: ServiceArea[]): Promise<any> {
    return { efficiency: 0.8, coverage: 0.75, utilization: 0.65 };
  }

  private identifyOptimizationOpportunities(
    areas: ServiceArea[],
    metrics: any,
    constraints: CoverageConstraints
  ): any[] {
    return [];
  }

  private async generateOptimizedAreas(
    areas: ServiceArea[],
    opportunities: any[],
    constraints: CoverageConstraints
  ): Promise<ServiceArea[]> {
    return areas; // Placeholder
  }

  private validateOptimizations(
    areas: ServiceArea[],
    constraints: CoverageConstraints
  ): ServiceArea[] {
    return areas; // Placeholder
  }

  private async calculateAreaBuildoutCost(area: Polygon, serviceType: string): Promise<any> {
    return { area, cost: this.estimateBuildoutCost(area), details: {} };
  }

  private generateBuildoutTimeline(costPerArea: any[], serviceType: string): any[] {
    return [];
  }

  private async analyzeAreaCompetition(area: Polygon, competitors: string[]): Promise<any> {
    return {
      area,
      competitors: competitors.filter(() => Math.random() > 0.5),
      overlapPercentage: Math.random() * 100,
      competitiveAdvantage: [],
    };
  }

  private identifyMarketOpportunities(overlapAnalysis: any[]): any[] {
    return [];
  }

  private generateInfrastructureRecommendations(
    gap: Gap,
    infrastructure: InfrastructureAsset[]
  ): CoverageRecommendation[] {
    return [];
  }

  private generateServiceRecommendations(
    gap: Gap,
    demographics: DemographicData
  ): CoverageRecommendation[] {
    return [];
  }

  private generateMarketingRecommendations(
    gap: Gap,
    demographics: DemographicData
  ): CoverageRecommendation[] {
    return [];
  }

  private generatePartnershipRecommendations(
    gap: Gap,
    demographics: DemographicData
  ): CoverageRecommendation[] {
    return [];
  }

  private filterRecommendationsByConstraints(
    recommendations: CoverageRecommendation[],
    constraints?: CoverageConstraints
  ): CoverageRecommendation[] {
    if (!constraints) return recommendations;

    return recommendations.filter((rec) => {
      if (constraints.maxBuildoutCost && rec.estimatedCost > constraints.maxBuildoutCost) {
        return false;
      }
      return true;
    });
  }

  // Permission and error handling
  private validatePermissions(operation: string): void {
    const requiredPermissions: Record<string, string[]> = {
      'coverage:calculate': ['coverage_read', 'analysis_read'],
      'gaps:analyze': ['gap_analysis', 'coverage_read'],
      'optimization:run': ['optimization_run', 'coverage_write'],
      'cost:calculate': ['cost_analysis', 'financial_read'],
      'competitor:analyze': ['competitor_analysis', 'market_read'],
    };

    const required = requiredPermissions[operation] || [];
    const hasPermission = required.some(
      (perm) =>
        this.portalContext.permissions.includes(perm) ||
        this.portalContext.permissions.includes('admin')
    );

    if (!hasPermission) {
      throw new Error(`Insufficient permissions for ${operation}`);
    }
  }

  private handleError(error: any, context: string): Error {
    console.error(`Service Coverage Engine Error (${context}):`, error);
    return new Error(`Coverage analysis failed: ${error.message || 'Unknown error'}`);
  }
}
