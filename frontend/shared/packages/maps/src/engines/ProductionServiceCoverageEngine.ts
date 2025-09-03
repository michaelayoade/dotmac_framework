/**
 * Production Service Coverage Analysis Engine
 * Real implementation with API integration
 */

import { ServiceCoverageEngine } from './ServiceCoverageEngine';
import { apiClient } from '../services/ApiClient';
import { logger } from '../utils/logger';
import { getConfig } from '../config/production';
import type {
  ServiceArea,
  CoverageResult,
  Gap,
  CoverageRecommendation,
  Polygon,
  PortalContext
} from '../types';

export class ProductionServiceCoverageEngine extends ServiceCoverageEngine {
  private config = getConfig();

  constructor(portalContext: PortalContext) {
    super(portalContext);
  }

  /**
   * Calculate comprehensive coverage analysis using real API data
   */
  async calculateCoverage(
    area: Polygon,
    serviceTypes: string[] = ['fiber', 'wireless'],
    constraints?: any
  ): Promise<CoverageResult> {
    try {
      this.validatePermissions('coverage:calculate');

      const startTime = performance.now();
      logger.info('ProductionServiceCoverageEngine', 'Starting coverage analysis', {
        area: area.coordinates.length,
        serviceTypes
      });

      // Get real demographic data from API
      const demographicsResponse = await apiClient.getDemographics({ coordinates: area.coordinates });

      if (!demographicsResponse.success || !demographicsResponse.data) {
        throw new Error('Failed to fetch demographic data');
      }

      const demographics = demographicsResponse.data;

      // Get real coverage analysis from API
      const coverageResponse = await apiClient.analyzeCoverage({
        area: { coordinates: area.coordinates },
        serviceTypes
      });

      if (!coverageResponse.success || !coverageResponse.data) {
        throw new Error('Failed to analyze coverage');
      }

      const coverageData = coverageResponse.data;

      // Calculate area size using Turf
      const areaSize = this.calculateAreaSize(area);

      // Transform API response to our format
      const gapPromises = coverageData.gaps.map(async (gap, index) => ({
        id: `gap_${Date.now()}_${index}`,
        polygon: {
          coordinates: gap.polygon.coordinates
        },
        type: gap.severity === 'critical' ? 'no_coverage' as const : 'poor_coverage' as const,
        severity: gap.severity as 'low' | 'medium' | 'high' | 'critical',
        affectedCustomers: gap.affectedCustomers,
        potentialRevenue: this.calculatePotentialRevenue(gap.affectedCustomers),
        buildoutCost: await this.estimateBuildoutCostFromAPI(gap.polygon),
        priority: this.calculateGapPriority(gap.severity as any, gap.affectedCustomers),
        recommendations: await this.generateGapRecommendationsFromAPI(gap)
      }));

      const gaps: Gap[] = await Promise.all(gapPromises);

      // Generate recommendations using AI/ML service
      const recommendations = await this.generateCoverageRecommendationsFromAPI(gaps);

      const result: CoverageResult = {
        area: areaSize,
        population: demographics.population,
        households: demographics.households,
        businesses: demographics.businesses,
        coveragePercentage: coverageData.coveragePercentage,
        serviceTypes,
        gaps,
        recommendations
      };

      const duration = performance.now() - startTime;
      logger.performance('ProductionServiceCoverageEngine', 'calculateCoverage', duration, {
        gaps: gaps.length,
        recommendations: recommendations.length,
        coverage: coverageData.coveragePercentage
      });

      return result;

    } catch (error) {
      logger.error('ProductionServiceCoverageEngine', 'Coverage calculation failed', error);

      // Fallback to mock data if configured
      if (this.config.api.enableMockData) {
        logger.warn('ProductionServiceCoverageEngine', 'Falling back to mock data');
        return super.calculateCoverage(area, serviceTypes, constraints);
      }

      throw this.handleError(error, 'calculateCoverage');
    }
  }

  // Private helper methods for production implementation

  private calculateAreaSize(area: Polygon): number {
    // Use proper geographic calculation
    try {
      const turfArea = require('@turf/area');
      const polygon = this.polygonToTurf(area);
      return turfArea(polygon) / 1000000; // Convert to km²
    } catch {
      // Fallback calculation
      return 0;
    }
  }

  private calculatePotentialRevenue(customers: number): number {
    // Get ARPU from configuration or API
    const avgMonthlyRevenue = this.portalContext.preferences?.avgRevenuePerCustomer || 75;
    return customers * avgMonthlyRevenue * 12; // Annual revenue
  }

  private calculateGapPriority(severity: string, affectedCustomers: number): number {
    const severityScore = {
      low: 1,
      medium: 2,
      high: 3,
      critical: 4
    }[severity as keyof typeof { low: 1, medium: 2, high: 3, critical: 4 }] || 1;

    const customerScore = Math.min(10, affectedCustomers / 100); // Scale customers to 0-10

    return severityScore * 10 + customerScore;
  }

  private async estimateBuildoutCostFromAPI(area: { coordinates: any[] }): Promise<number> {
    try {
      // Call cost estimation API
      const response = await fetch(`${this.config.api.baseUrl}/cost-estimation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ area })
      });

      if (response.ok) {
        const data = await response.json();
        return data.estimatedCost || 0;
      }
    } catch (error) {
      logger.warn('ProductionServiceCoverageEngine', 'Cost estimation API failed', error);
    }

    // Fallback calculation
    const areaSize = this.calculateAreaSize({ coordinates: area.coordinates.map((coord: any) => coord) });
    return areaSize * 50000; // $50k per km²
  }

  private async generateGapRecommendationsFromAPI(gap: any): Promise<string[]> {
    try {
      // Call AI recommendation service
      const response = await fetch(`${this.config.api.baseUrl}/recommendations/gaps`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(gap)
      });

      if (response.ok) {
        const data = await response.json();
        return data.recommendations || [];
      }
    } catch (error) {
      logger.warn('ProductionServiceCoverageEngine', 'Recommendations API failed', error);
    }

    // Fallback recommendations
    const recommendations = [];

    if (gap.affectedCustomers > 1000) {
      recommendations.push('High customer impact - prioritize for immediate buildout');
    }

    if (gap.severity === 'critical') {
      recommendations.push('Critical gap - consider emergency deployment options');
    }

    return recommendations;
  }

  private async generateCoverageRecommendationsFromAPI(gaps: Gap[]): Promise<CoverageRecommendation[]> {
    try {
      // Call ML-powered recommendation engine
      const response = await fetch(`${this.config.api.baseUrl}/recommendations/coverage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ gaps })
      });

      if (response.ok) {
        const data = await response.json();
        return data.recommendations || [];
      }
    } catch (error) {
      logger.warn('ProductionServiceCoverageEngine', 'Coverage recommendations API failed', error);
    }

    // Generate basic recommendations from gaps
    const recommendations: CoverageRecommendation[] = [];

    const highPriorityGaps = gaps.filter(g => g.priority > 30);
    if (highPriorityGaps.length > 0) {
      recommendations.push({
        id: `rec_${Date.now()}_1`,
        type: 'infrastructure',
        priority: 'high',
        description: `Deploy infrastructure to address ${highPriorityGaps.length} high-priority coverage gaps`,
        estimatedCost: highPriorityGaps.reduce((sum, gap) => sum + gap.buildoutCost, 0),
        estimatedRevenue: highPriorityGaps.reduce((sum, gap) => sum + gap.potentialRevenue, 0),
        timeframe: '6-12 months',
        requirements: ['Fiber deployment', 'Equipment installation', 'Permits']
      });
    }

    return recommendations;
  }

  private polygonToTurf(polygon: Polygon): any {
    const coordinates = polygon.coordinates.map(coord => [coord.lng, coord.lat]);
    // Close the polygon if not already closed
    if (coordinates[0] !== coordinates[coordinates.length - 1]) {
      coordinates.push(coordinates[0]);
    }

    return {
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [coordinates]
      }
    };
  }

  private handleError(error: any, context: string): Error {
    const message = error.message || 'Unknown error occurred';
    const productionError = new Error(`Coverage analysis failed: ${message}`);

    // Don't expose internal details in production
    if (this.config.logging.level === 'error') {
      return new Error('Coverage analysis temporarily unavailable');
    }

    return productionError;
  }
}
