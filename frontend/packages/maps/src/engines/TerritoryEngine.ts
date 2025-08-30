/**
 * Territory Management Engine
 * Provides territory analysis, optimization, and management functionality
 */

import * as turf from '@turf/turf';
import type {
  Territory,
  PenetrationMetrics,
  CompetitorAnalysis,
  CompetitorInfo,
  OverlapArea,
  MarketingRecommendation,
  Polygon,
  Coordinates,
  PortalContext
} from '../types';

export interface ExpansionCriteria {
  maxDistance?: number; // km from existing territory
  minPopulation?: number;
  minBusinessDensity?: number;
  maxCompetitorPresence?: number; // percentage
  budgetConstraint?: number;
  timeframeMonths?: number;
  preferredServiceTypes?: string[];
  avoidAreas?: Polygon[];
  priorityZones?: Polygon[];
}

export interface TerritoryMetrics {
  id: string;
  efficiency: number; // 0-1 score
  profitability: number; // monthly profit
  marketShare: number; // percentage in territory
  customerSatisfaction: number; // 0-5 rating
  churnRate: number; // monthly percentage
  averageRevenue: number; // per customer
  competitiveThreats: string[];
  growthPotential: 'low' | 'medium' | 'high';
}

export interface TerritoryOptimization {
  originalTerritory: Territory;
  optimizedBoundary: Polygon;
  projectedImprovements: {
    revenueIncrease: number;
    customerIncrease: number;
    efficiencyGain: number;
    costReduction: number;
  };
  implementationPlan: {
    phase: string;
    duration: number;
    cost: number;
    requirements: string[];
  }[];
  riskFactors: string[];
}

export class TerritoryEngine {
  private portalContext: PortalContext;
  private territoryCache: Map<string, Territory> = new Map();
  private metricsCache: Map<string, TerritoryMetrics> = new Map();
  private competitorCache: Map<string, CompetitorInfo[]> = new Map();

  constructor(portalContext: PortalContext) {
    this.portalContext = portalContext;
  }

  /**
   * Calculate market penetration metrics for a territory
   */
  async calculateMarketPenetration(territory: Territory): Promise<PenetrationMetrics> {
    try {
      this.validatePermissions('territory:analyze');

      // Get demographic data for the territory
      const demographics = await this.getTerritoryDemographics(territory);

      // Get current customer data
      const customers = await this.getCustomersInTerritory(territory);

      // Get competitor information
      const competitors = await this.getCompetitorData(territory);

      // Calculate penetration rates
      const penetrationRates = this.calculatePenetrationRates(
        customers,
        demographics,
        competitors
      );

      // Calculate market potential
      const marketPotential = this.calculateMarketPotential(
        demographics,
        penetrationRates,
        competitors
      );

      return {
        territoryId: territory.id,
        totalHouseholds: demographics.households,
        totalBusinesses: demographics.businesses,
        currentCustomers: {
          residential: customers.residential,
          business: customers.business,
          enterprise: customers.enterprise
        },
        penetrationRates,
        marketPotential,
        competitorAnalysis: competitors
      };

    } catch (error) {
      throw this.handleError(error, 'calculateMarketPenetration');
    }
  }

  /**
   * Find competitor overlap areas and analyze competitive landscape
   */
  async findCompetitorOverlap(territories: Territory[]): Promise<CompetitorAnalysis> {
    try {
      this.validatePermissions('competitor:analyze');

      const overlapAreas: OverlapArea[] = [];
      const allCompetitors = new Set<string>();
      const competitiveAdvantages: string[] = [];
      const threats: string[] = [];
      const opportunities: string[] = [];

      for (const territory of territories) {
        // Get competitors in this territory
        const competitors = await this.getCompetitorData(territory);
        competitors.forEach(comp => allCompetitors.add(comp.name));

        // Find overlap areas
        const overlaps = await this.findTerritoryOverlaps(territory, competitors);
        overlapAreas.push(...overlaps);

        // Analyze competitive position
        const analysis = this.analyzeCompetitivePosition(territory, competitors);
        competitiveAdvantages.push(...analysis.advantages);
        threats.push(...analysis.threats);
        opportunities.push(...analysis.opportunities);
      }

      // Generate marketing recommendations
      const recommendations = this.generateMarketingRecommendations(
        overlapAreas,
        Array.from(allCompetitors)
      );

      return {
        territory: territories.map(t => t.name).join(', '),
        overlapAreas,
        competitiveAdvantages: [...new Set(competitiveAdvantages)],
        threats: [...new Set(threats)],
        opportunities: [...new Set(opportunities)],
        recommendations
      };

    } catch (error) {
      throw this.handleError(error, 'findCompetitorOverlap');
    }
  }

  /**
   * Suggest territory expansion opportunities
   */
  async suggestTerritoryExpansion(
    currentTerritory: Territory,
    criteria: ExpansionCriteria
  ): Promise<{
    expansionAreas: Polygon[];
    prioritizedTargets: {
      area: Polygon;
      score: number;
      reasoning: string[];
      estimatedCustomers: number;
      estimatedRevenue: number;
      buildoutCost: number;
      timeToBreakeven: number; // months
    }[];
    implementationRoadmap: {
      phase: number;
      areas: Polygon[];
      duration: number;
      cost: number;
      expectedROI: number;
    }[];
  }> {
    try {
      this.validatePermissions('territory:expand');

      // Find potential expansion areas around current territory
      const candidateAreas = await this.findExpansionCandidates(
        currentTerritory,
        criteria
      );

      // Score and prioritize each candidate area
      const prioritizedTargets = await Promise.all(
        candidateAreas.map(area => this.scoreExpansionArea(area, criteria))
      );

      // Sort by score
      prioritizedTargets.sort((a, b) => b.score - a.score);

      // Generate implementation roadmap
      const implementationRoadmap = this.generateExpansionRoadmap(
        prioritizedTargets,
        criteria
      );

      return {
        expansionAreas: candidateAreas,
        prioritizedTargets,
        implementationRoadmap
      };

    } catch (error) {
      throw this.handleError(error, 'suggestTerritoryExpansion');
    }
  }

  /**
   * Optimize territory boundaries for maximum efficiency
   */
  async optimizeTerritoryBoundaries(
    territories: Territory[],
    objectives: {
      maximizeRevenue?: boolean;
      minimizeOverlap?: boolean;
      balanceLoad?: boolean;
      improveServiceQuality?: boolean;
    } = {}
  ): Promise<TerritoryOptimization[]> {
    try {
      this.validatePermissions('territory:optimize');

      const optimizations: TerritoryOptimization[] = [];

      for (const territory of territories) {
        const optimization = await this.optimizeIndividualTerritory(
          territory,
          territories.filter(t => t.id !== territory.id),
          objectives
        );
        optimizations.push(optimization);
      }

      // Validate that optimizations don't conflict
      const validatedOptimizations = this.validateOptimizations(optimizations);

      return validatedOptimizations;

    } catch (error) {
      throw this.handleError(error, 'optimizeTerritoryBoundaries');
    }
  }

  /**
   * Analyze territory performance metrics
   */
  async analyzeTerritoryPerformance(territory: Territory): Promise<TerritoryMetrics> {
    try {
      this.validatePermissions('territory:analyze');

      const cacheKey = `${territory.id}_${Date.now()}`;
      if (this.metricsCache.has(cacheKey)) {
        return this.metricsCache.get(cacheKey)!;
      }

      // Get financial data
      const revenue = await this.getTerritoryRevenue(territory);
      const costs = await this.getTerritoryCosts(territory);
      const customers = await this.getCustomersInTerritory(territory);

      // Calculate efficiency metrics
      const efficiency = this.calculateTerritoryEfficiency(territory, customers);

      // Calculate profitability
      const profitability = revenue.monthly - costs.monthly;

      // Get market share data
      const marketShare = await this.calculateTerritoryMarketShare(territory);

      // Get customer satisfaction data
      const customerSatisfaction = await this.getCustomerSatisfaction(territory);

      // Calculate churn rate
      const churnRate = await this.calculateChurnRate(territory);

      // Calculate average revenue per customer
      const totalCustomers = customers.residential + customers.business + customers.enterprise;
      const averageRevenue = totalCustomers > 0 ? revenue.monthly / totalCustomers : 0;

      // Identify competitive threats
      const competitiveThreats = await this.identifyCompetitiveThreats(territory);

      // Assess growth potential
      const growthPotential = this.assessGrowthPotential(
        territory,
        customers,
        marketShare,
        competitiveThreats
      );

      const metrics: TerritoryMetrics = {
        id: territory.id,
        efficiency,
        profitability,
        marketShare,
        customerSatisfaction,
        churnRate,
        averageRevenue,
        competitiveThreats,
        growthPotential
      };

      this.metricsCache.set(cacheKey, metrics);
      return metrics;

    } catch (error) {
      throw this.handleError(error, 'analyzeTerritoryPerformance');
    }
  }

  /**
   * Compare territories and identify best practices
   */
  async compareTerritories(territories: Territory[]): Promise<{
    performanceRanking: {
      territory: Territory;
      metrics: TerritoryMetrics;
      rank: number;
    }[];
    bestPractices: {
      category: string;
      practice: string;
      territory: string;
      impact: string;
    }[];
    improvementOpportunities: {
      territory: Territory;
      opportunities: {
        area: string;
        currentValue: number;
        targetValue: number;
        potentialImpact: string;
        recommendations: string[];
      }[];
    }[];
  }> {
    try {
      this.validatePermissions('territory:compare');

      // Get metrics for all territories
      const allMetrics = await Promise.all(
        territories.map(async territory => ({
          territory,
          metrics: await this.analyzeTerritoryPerformance(territory)
        }))
      );

      // Rank territories by overall performance
      const performanceRanking = this.rankTerritories(allMetrics);

      // Identify best practices from top performers
      const bestPractices = this.identifyBestPractices(performanceRanking);

      // Find improvement opportunities for underperforming territories
      const improvementOpportunities = this.findImprovementOpportunities(
        performanceRanking
      );

      return {
        performanceRanking,
        bestPractices,
        improvementOpportunities
      };

    } catch (error) {
      throw this.handleError(error, 'compareTerritories');
    }
  }

  // Private helper methods

  private calculatePenetrationRates(
    customers: { residential: number; business: number; enterprise: number },
    demographics: { households: number; businesses: number },
    competitors: CompetitorInfo[]
  ) {
    const totalCustomers = customers.residential + customers.business + customers.enterprise;
    const totalMarket = demographics.households + demographics.businesses;

    // Calculate competitor market share
    const competitorShare = competitors.reduce((sum, comp) => sum + comp.marketShare, 0);
    const availableMarket = Math.max(0, 100 - competitorShare);

    return {
      overall: totalMarket > 0 ? (totalCustomers / totalMarket) * 100 : 0,
      residential: demographics.households > 0 ?
        (customers.residential / demographics.households) * 100 : 0,
      business: demographics.businesses > 0 ?
        (customers.business / demographics.businesses) * 100 : 0,
      enterprise: demographics.businesses > 0 ?
        (customers.enterprise / demographics.businesses) * 100 : 0
    };
  }

  private calculateMarketPotential(
    demographics: { households: number; businesses: number; medianIncome: number },
    penetrationRates: any,
    competitors: CompetitorInfo[]
  ) {
    const competitorShare = competitors.reduce((sum, comp) => sum + comp.marketShare, 0);
    const availableMarket = Math.max(0, 100 - competitorShare);

    // Estimate potential based on demographics and competition
    const householdPotential = Math.floor(
      demographics.households * (availableMarket / 100) * 0.8 // 80% addressable
    );

    const businessPotential = Math.floor(
      demographics.businesses * (availableMarket / 100) * 0.6 // 60% addressable
    );

    // Revenue estimation based on median income
    const avgMonthlyRevenue = Math.min(150, Math.max(50, demographics.medianIncome / 1000));
    const estimatedRevenue = (householdPotential + businessPotential) * avgMonthlyRevenue * 12;

    return {
      households: householdPotential,
      businesses: businessPotential,
      estimatedRevenue
    };
  }

  private async findTerritoryOverlaps(
    territory: Territory,
    competitors: CompetitorInfo[]
  ): Promise<OverlapArea[]> {
    const overlaps: OverlapArea[] = [];

    // Mock competitor coverage areas
    for (const competitor of competitors) {
      if (competitor.coverage > 0) {
        // Generate mock overlap area
        const overlapPolygon = this.generateMockOverlapArea(
          territory.polygon,
          competitor.coverage / 100
        );

        overlaps.push({
          polygon: overlapPolygon,
          competitors: [competitor.name],
          overlapType: competitor.coverage > 80 ? 'full' :
                      competitor.coverage > 40 ? 'partial' : 'planned',
          customerImpact: Math.floor(territory.totalCustomers * (competitor.coverage / 100)),
          revenueImpact: territory.monthlyRevenue * (competitor.coverage / 200) // 50% impact max
        });
      }
    }

    return overlaps;
  }

  private analyzeCompetitivePosition(
    territory: Territory,
    competitors: CompetitorInfo[]
  ): { advantages: string[]; threats: string[]; opportunities: string[] } {
    const advantages: string[] = [];
    const threats: string[] = [];
    const opportunities: string[] = [];

    // Analyze market position
    const totalCompetitorShare = competitors.reduce((sum, comp) => sum + comp.marketShare, 0);

    if (totalCompetitorShare < 50) {
      advantages.push('Market leadership position');
      opportunities.push('Expand market share in underserved segments');
    } else {
      threats.push('High competitive pressure');
    }

    // Analyze service advantages
    const fiberCompetitors = competitors.filter(comp =>
      comp.serviceTypes.includes('fiber')
    ).length;

    if (fiberCompetitors === 0) {
      advantages.push('Fiber technology advantage');
      opportunities.push('Premium service differentiation');
    } else {
      threats.push('Fiber competition present');
    }

    // Analyze pricing position
    const avgCompetitorPrice = competitors.reduce((sum, comp) =>
      sum + (comp.pricing.residential.min + comp.pricing.residential.max) / 2, 0
    ) / competitors.length;

    // Mock our pricing - would come from actual data
    const ourPrice = 75; // Mock price

    if (ourPrice < avgCompetitorPrice * 0.9) {
      advantages.push('Competitive pricing advantage');
    } else if (ourPrice > avgCompetitorPrice * 1.1) {
      threats.push('Price disadvantage vs competitors');
      opportunities.push('Premium positioning with superior service');
    }

    return { advantages, threats, opportunities };
  }

  private generateMarketingRecommendations(
    overlapAreas: OverlapArea[],
    competitors: string[]
  ): MarketingRecommendation[] {
    const recommendations: MarketingRecommendation[] = [];

    // High overlap areas - aggressive marketing
    const highOverlapAreas = overlapAreas.filter(area =>
      area.overlapType === 'full' || area.customerImpact > 1000
    );

    highOverlapAreas.forEach(area => {
      recommendations.push({
        type: 'promotion',
        description: `Aggressive promotional campaign in high-competition area`,
        targetArea: area.polygon,
        expectedImpact: 15, // 15% customer increase
        cost: area.revenueImpact * 0.3, // 30% of potential revenue
        timeline: '3 months'
      });
    });

    // Low competition areas - expansion focus
    const lowOverlapAreas = overlapAreas.filter(area =>
      area.overlapType === 'planned' && area.customerImpact < 500
    );

    lowOverlapAreas.forEach(area => {
      recommendations.push({
        type: 'service',
        description: 'Rapid service expansion in underserved area',
        targetArea: area.polygon,
        expectedImpact: 25, // 25% market capture
        cost: area.revenueImpact * 0.2, // 20% of potential revenue
        timeline: '6 months'
      });
    });

    return recommendations;
  }

  private async findExpansionCandidates(
    territory: Territory,
    criteria: ExpansionCriteria
  ): Promise<Polygon[]> {
    const candidates: Polygon[] = [];

    // Generate buffer areas around current territory
    const maxDistance = criteria.maxDistance || 5; // 5km default
    const territoryCenter = this.calculatePolygonCenter(territory.polygon);

    // Create expansion rings
    for (let distance = 1; distance <= maxDistance; distance++) {
      const expansionRing = this.createRingAroundPoint(
        territoryCenter,
        distance,
        distance + 0.5
      );

      // Filter out avoid areas
      const filteredRing = criteria.avoidAreas ?
        this.subtractPolygons(expansionRing, criteria.avoidAreas) : expansionRing;

      if (filteredRing) {
        candidates.push(filteredRing);
      }
    }

    return candidates;
  }

  private async scoreExpansionArea(
    area: Polygon,
    criteria: ExpansionCriteria
  ): Promise<{
    area: Polygon;
    score: number;
    reasoning: string[];
    estimatedCustomers: number;
    estimatedRevenue: number;
    buildoutCost: number;
    timeToBreakeven: number;
  }> {
    const reasoning: string[] = [];
    let score = 0;

    // Get area demographics
    const demographics = await this.getAreaDemographics(area);

    // Population score
    if (demographics.population >= (criteria.minPopulation || 1000)) {
      score += 25;
      reasoning.push('Meets minimum population requirement');
    } else {
      reasoning.push('Below minimum population threshold');
    }

    // Business density score
    const businessDensity = demographics.businesses / (turf.area(this.polygonToTurf(area)) / 1000000);
    if (businessDensity >= (criteria.minBusinessDensity || 50)) {
      score += 20;
      reasoning.push('High business density area');
    }

    // Competition score
    const competitorPresence = await this.getCompetitorPresenceInArea(area);
    if (competitorPresence <= (criteria.maxCompetitorPresence || 60)) {
      score += 30;
      reasoning.push('Low competitive pressure');
    } else {
      reasoning.push('High competitive pressure');
    }

    // Infrastructure availability score
    const infrastructureScore = await this.assessInfrastructureReadiness(area);
    score += Math.min(25, infrastructureScore);
    reasoning.push(`Infrastructure readiness: ${infrastructureScore}/25`);

    // Calculate financial metrics
    const estimatedCustomers = Math.floor(
      (demographics.households + demographics.businesses) * 0.15 // 15% penetration
    );

    const avgRevenue = 75; // Mock ARPU
    const estimatedRevenue = estimatedCustomers * avgRevenue * 12; // Annual

    const buildoutCost = this.estimateAreaBuildoutCost(area);
    const timeToBreakeven = buildoutCost > 0 ? Math.ceil(buildoutCost / (estimatedRevenue * 0.3)) : 0;

    return {
      area,
      score: Math.max(0, Math.min(100, score)),
      reasoning,
      estimatedCustomers,
      estimatedRevenue,
      buildoutCost,
      timeToBreakeven
    };
  }

  private generateExpansionRoadmap(
    targets: any[],
    criteria: ExpansionCriteria
  ): any[] {
    const phases: any[] = [];
    const budget = criteria.budgetConstraint || 1000000;
    const timeframe = criteria.timeframeMonths || 24;

    let remainingBudget = budget;
    let currentPhase = 1;
    let accumulatedCost = 0;

    // Group high-scoring targets into phases
    const highPriorityTargets = targets.filter(t => t.score >= 70);
    const mediumPriorityTargets = targets.filter(t => t.score >= 40 && t.score < 70);

    // Phase 1: High priority, quick wins
    const phase1Targets = highPriorityTargets
      .filter(t => t.timeToBreakeven <= 12)
      .slice(0, 3);

    if (phase1Targets.length > 0) {
      const phase1Cost = phase1Targets.reduce((sum, t) => sum + t.buildoutCost, 0);
      const phase1ROI = phase1Targets.reduce((sum, t) =>
        sum + (t.estimatedRevenue - t.buildoutCost) / t.buildoutCost, 0
      ) / phase1Targets.length;

      phases.push({
        phase: 1,
        areas: phase1Targets.map(t => t.area),
        duration: 6,
        cost: phase1Cost,
        expectedROI: phase1ROI
      });

      remainingBudget -= phase1Cost;
    }

    // Phase 2: Medium priority areas
    if (remainingBudget > 0 && mediumPriorityTargets.length > 0) {
      const affordableTargets = mediumPriorityTargets.filter(t =>
        t.buildoutCost <= remainingBudget / 2
      );

      if (affordableTargets.length > 0) {
        const phase2Cost = Math.min(remainingBudget,
          affordableTargets.reduce((sum, t) => sum + t.buildoutCost, 0)
        );

        phases.push({
          phase: 2,
          areas: affordableTargets.map(t => t.area),
          duration: 12,
          cost: phase2Cost,
          expectedROI: 0.15
        });
      }
    }

    return phases;
  }

  // Utility and mock data methods
  private polygonToTurf(polygon: Polygon): any {
    const coordinates = polygon.coordinates.map(coord => [coord.lng, coord.lat]);
    coordinates.push(coordinates[0]); // Close polygon
    return turf.polygon([coordinates]);
  }

  private calculatePolygonCenter(polygon: Polygon): Coordinates {
    const turfPolygon = this.polygonToTurf(polygon);
    const center = turf.centroid(turfPolygon);
    return {
      lat: center.geometry.coordinates[1],
      lng: center.geometry.coordinates[0]
    };
  }

  private createRingAroundPoint(
    center: Coordinates,
    innerRadius: number,
    outerRadius: number
  ): Polygon {
    const outerCircle = turf.buffer(
      turf.point([center.lng, center.lat]),
      outerRadius,
      { units: 'kilometers' }
    );

    const innerCircle = turf.buffer(
      turf.point([center.lng, center.lat]),
      innerRadius,
      { units: 'kilometers' }
    );

    const ring = turf.difference(outerCircle, innerCircle);

    if (!ring) {
      // Fallback to outer circle if difference fails
      const coords = outerCircle.geometry.coordinates[0];
      return {
        coordinates: coords.slice(0, -1).map((coord: number[]) => ({
          lat: coord[1],
          lng: coord[0]
        }))
      };
    }

    const coords = ring.geometry.coordinates[0];
    return {
      coordinates: coords.slice(0, -1).map((coord: number[]) => ({
        lat: coord[1],
        lng: coord[0]
      }))
    };
  }

  private subtractPolygons(minuend: Polygon, subtrahends: Polygon[]): Polygon | null {
    try {
      let result = this.polygonToTurf(minuend);

      for (const subtrahend of subtrahends) {
        const turfSubtrahend = this.polygonToTurf(subtrahend);
        const difference = turf.difference(result, turfSubtrahend);
        if (difference) {
          result = difference;
        } else {
          return null;
        }
      }

      const coords = result.geometry.coordinates[0];
      return {
        coordinates: coords.slice(0, -1).map((coord: number[]) => ({
          lat: coord[1],
          lng: coord[0]
        }))
      };
    } catch {
      return null;
    }
  }

  private generateMockOverlapArea(territoryPolygon: Polygon, coverage: number): Polygon {
    // Generate a simplified overlap area within territory
    const center = this.calculatePolygonCenter(territoryPolygon);
    const radius = Math.sqrt(coverage) * 2; // Rough radius based on coverage

    const circle = turf.buffer(
      turf.point([center.lng, center.lat]),
      radius,
      { units: 'kilometers' }
    );

    const coords = circle.geometry.coordinates[0];
    return {
      coordinates: coords.slice(0, -1).map((coord: number[]) => ({
        lat: coord[1],
        lng: coord[0]
      }))
    };
  }

  // Mock data methods (would be replaced with real API calls)
  private async getTerritoryDemographics(territory: Territory) {
    return {
      households: Math.floor(Math.random() * 20000) + 5000,
      businesses: Math.floor(Math.random() * 2000) + 500,
      medianIncome: Math.floor(Math.random() * 50000) + 50000,
      population: Math.floor(Math.random() * 50000) + 15000
    };
  }

  private async getCustomersInTerritory(territory: Territory) {
    return {
      residential: Math.floor(territory.totalCustomers * 0.8),
      business: Math.floor(territory.totalCustomers * 0.15),
      enterprise: Math.floor(territory.totalCustomers * 0.05)
    };
  }

  private async getCompetitorData(territory: Territory): Promise<CompetitorInfo[]> {
    const competitors: CompetitorInfo[] = [
      {
        name: 'CompetitorA',
        serviceTypes: ['fiber', 'cable'],
        coverage: Math.random() * 60 + 20,
        marketShare: Math.random() * 30 + 10,
        strengths: ['Established network', 'Brand recognition'],
        weaknesses: ['Higher prices', 'Poor customer service'],
        pricing: {
          residential: { min: 60, max: 120 },
          business: { min: 150, max: 500 }
        }
      }
    ];

    return competitors;
  }

  private async getAreaDemographics(area: Polygon) {
    return {
      population: Math.floor(Math.random() * 10000) + 2000,
      households: Math.floor(Math.random() * 4000) + 800,
      businesses: Math.floor(Math.random() * 400) + 50,
      medianIncome: Math.floor(Math.random() * 40000) + 60000
    };
  }

  private async getCompetitorPresenceInArea(area: Polygon): Promise<number> {
    return Math.random() * 80; // 0-80% competitor presence
  }

  private async assessInfrastructureReadiness(area: Polygon): Promise<number> {
    return Math.floor(Math.random() * 25); // 0-25 points
  }

  private estimateAreaBuildoutCost(area: Polygon): number {
    const areaSize = turf.area(this.polygonToTurf(area)) / 1000000; // km²
    return areaSize * 50000; // $50k per km²
  }

  // Stub implementations for complex methods
  private async optimizeIndividualTerritory(
    territory: Territory,
    otherTerritories: Territory[],
    objectives: any
  ): Promise<TerritoryOptimization> {
    return {
      originalTerritory: territory,
      optimizedBoundary: territory.polygon, // No change for now
      projectedImprovements: {
        revenueIncrease: 0,
        customerIncrease: 0,
        efficiencyGain: 0,
        costReduction: 0
      },
      implementationPlan: [],
      riskFactors: []
    };
  }

  private validateOptimizations(optimizations: TerritoryOptimization[]): TerritoryOptimization[] {
    return optimizations; // Pass through for now
  }

  private calculateTerritoryEfficiency(territory: Territory, customers: any): number {
    // Mock efficiency calculation
    return Math.min(1, (customers.residential + customers.business) / (territory.totalCustomers || 1));
  }

  private async getTerritoryRevenue(territory: Territory) {
    return { monthly: territory.monthlyRevenue };
  }

  private async getTerritoryCosts(territory: Territory) {
    return { monthly: territory.monthlyRevenue * 0.6 }; // 60% cost ratio
  }

  private async calculateTerritoryMarketShare(territory: Territory): Promise<number> {
    return territory.marketPenetration;
  }

  private async getCustomerSatisfaction(territory: Territory): Promise<number> {
    return Math.random() * 2 + 3; // 3-5 rating
  }

  private async calculateChurnRate(territory: Territory): Promise<number> {
    return Math.random() * 5 + 1; // 1-6% monthly churn
  }

  private async identifyCompetitiveThreats(territory: Territory): Promise<string[]> {
    return ['New fiber competitor', 'Price pressure'];
  }

  private assessGrowthPotential(
    territory: Territory,
    customers: any,
    marketShare: number,
    threats: string[]
  ): 'low' | 'medium' | 'high' {
    if (marketShare > 60 || threats.length > 3) return 'low';
    if (marketShare > 30 || threats.length > 1) return 'medium';
    return 'high';
  }

  private rankTerritories(allMetrics: any[]) {
    return allMetrics
      .map((item, index) => ({
        ...item,
        rank: index + 1
      }))
      .sort((a, b) =>
        (b.metrics.profitability + b.metrics.efficiency * 10000) -
        (a.metrics.profitability + a.metrics.efficiency * 10000)
      );
  }

  private identifyBestPractices(ranking: any[]) {
    return [
      {
        category: 'Customer Retention',
        practice: 'Proactive support outreach',
        territory: ranking[0]?.territory.name || 'Unknown',
        impact: 'Reduced churn by 2%'
      }
    ];
  }

  private findImprovementOpportunities(ranking: any[]) {
    return ranking.slice(-2).map(item => ({
      territory: item.territory,
      opportunities: [
        {
          area: 'Customer Satisfaction',
          currentValue: item.metrics.customerSatisfaction,
          targetValue: 4.5,
          potentialImpact: 'Reduce churn by 1%',
          recommendations: ['Improve response times', 'Enhance service quality']
        }
      ]
    }));
  }

  // Permission and error handling
  private validatePermissions(operation: string): void {
    const requiredPermissions: Record<string, string[]> = {
      'territory:analyze': ['territory_read', 'analysis_read'],
      'territory:expand': ['territory_write', 'planning_write'],
      'territory:optimize': ['territory_write', 'optimization_run'],
      'territory:compare': ['territory_read', 'analytics_read'],
      'competitor:analyze': ['competitor_analysis', 'market_read']
    };

    const required = requiredPermissions[operation] || [];
    const hasPermission = required.some(perm =>
      this.portalContext.permissions.includes(perm) ||
      this.portalContext.permissions.includes('admin')
    );

    if (!hasPermission) {
      throw new Error(`Insufficient permissions for ${operation}`);
    }
  }

  private handleError(error: any, context: string): Error {
    console.error(`Territory Engine Error (${context}):`, error);
    return new Error(`Territory analysis failed: ${error.message || 'Unknown error'}`);
  }
}
