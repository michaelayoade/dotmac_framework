/**
 * Route Optimization Engine
 * Provides advanced route planning and optimization for field operations
 */

import type {
  RouteOptimizationRequest,
  TechnicianInfo,
  WorkOrderInfo,
  RouteConstraints,
  RouteObjective,
  OptimizedRoute,
  Coordinates,
  Route,
  PortalContext,
} from '../types';

export interface RouteOptimizationResult {
  routes: OptimizedRoute[];
  unassignedWorkOrders: WorkOrderInfo[];
  optimizationStats: {
    totalDistance: number;
    totalTime: number;
    utilizationRate: number;
    improvementPercentage: number;
    fuelSavings: number;
    costSavings: number;
  };
  recommendations: string[];
}

export interface TrafficData {
  route: Coordinates[];
  travelTimeMinutes: number;
  distance: number;
  congestionLevel: 'low' | 'medium' | 'high';
  alternativeRoutes?: {
    route: Coordinates[];
    travelTimeMinutes: number;
    distance: number;
  }[];
}

export class RouteOptimizationEngine {
  private portalContext: PortalContext;
  private distanceCache: Map<string, number> = new Map();
  private trafficCache: Map<string, TrafficData> = new Map();

  constructor(portalContext: PortalContext) {
    this.portalContext = portalContext;
  }

  /**
   * Optimize routes for multiple technicians and work orders
   */
  async optimizeRoutes(request: RouteOptimizationRequest): Promise<RouteOptimizationResult> {
    try {
      this.validatePermissions('route:optimize');

      // Pre-process work orders (clustering, priority sorting)
      const processedWorkOrders = await this.preprocessWorkOrders(
        request.workOrders,
        request.constraints
      );

      // Calculate distance matrix between all locations
      const distanceMatrix = await this.calculateDistanceMatrix([
        ...request.technicians.map((t) => t.location),
        ...processedWorkOrders.map((wo) => wo.location),
      ]);

      // Run optimization algorithm
      const optimizedRoutes = await this.runOptimizationAlgorithm(
        request.technicians,
        processedWorkOrders,
        distanceMatrix,
        request.constraints,
        request.objectives
      );

      // Post-process routes (traffic optimization, time windows)
      const finalRoutes = await this.postprocessRoutes(optimizedRoutes, request.constraints);

      // Calculate unassigned work orders
      const assignedWorkOrderIds = new Set(finalRoutes.flatMap((route) => route.workOrders || []));
      const unassignedWorkOrders = request.workOrders.filter(
        (wo) => !assignedWorkOrderIds.has(wo.id)
      );

      // Calculate optimization statistics
      const optimizationStats = this.calculateOptimizationStats(finalRoutes, request.workOrders);

      // Generate recommendations
      const recommendations = this.generateOptimizationRecommendations(
        finalRoutes,
        unassignedWorkOrders,
        optimizationStats
      );

      return {
        routes: finalRoutes,
        unassignedWorkOrders,
        optimizationStats,
        recommendations,
      };
    } catch (error) {
      throw this.handleError(error, 'optimizeRoutes');
    }
  }

  /**
   * Calculate optimal route between waypoints considering traffic
   */
  async calculateOptimalRoute(
    waypoints: Coordinates[],
    options: {
      avoidTolls?: boolean;
      avoidHighways?: boolean;
      considerTraffic?: boolean;
      departureTime?: Date;
    } = {}
  ): Promise<{
    route: Coordinates[];
    distance: number;
    duration: number;
    trafficDuration: number;
    instructions: string[];
  }> {
    try {
      this.validatePermissions('route:calculate');

      if (waypoints.length < 2) {
        throw new Error('At least 2 waypoints required for route calculation');
      }

      // Get traffic data if requested
      let trafficData: TrafficData | undefined;
      if (options.considerTraffic) {
        trafficData = await this.getTrafficData(waypoints, options.departureTime);
      }

      // Calculate base route
      const baseRoute = await this.calculateBaseRoute(waypoints);

      // Apply traffic adjustments
      const trafficAdjustedDuration = trafficData
        ? trafficData.travelTimeMinutes
        : baseRoute.duration;

      // Generate turn-by-turn instructions
      const instructions = this.generateRouteInstructions(baseRoute.route);

      return {
        route: baseRoute.route,
        distance: baseRoute.distance,
        duration: baseRoute.duration,
        trafficDuration: trafficAdjustedDuration,
        instructions,
      };
    } catch (error) {
      throw this.handleError(error, 'calculateOptimalRoute');
    }
  }

  /**
   * Estimate travel time between two points
   */
  async estimateTravelTime(
    from: Coordinates,
    to: Coordinates,
    options: {
      mode?: 'driving' | 'walking' | 'cycling';
      departureTime?: Date;
      considerTraffic?: boolean;
    } = {}
  ): Promise<{
    distance: number;
    duration: number;
    trafficDuration?: number;
  }> {
    try {
      const cacheKey = `${from.lat},${from.lng}-${to.lat},${to.lng}-${options.mode || 'driving'}`;

      // Check cache first
      if (this.distanceCache.has(cacheKey)) {
        const cachedDistance = this.distanceCache.get(cacheKey)!;
        const baseDuration = this.distanceToTime(cachedDistance, options.mode);

        return {
          distance: cachedDistance,
          duration: baseDuration,
          trafficDuration: options.considerTraffic
            ? baseDuration * (1 + Math.random() * 0.5)
            : undefined, // Mock traffic
        };
      }

      // Calculate new distance
      const distance = this.calculateHaversineDistance(from, to);
      this.distanceCache.set(cacheKey, distance);

      const baseDuration = this.distanceToTime(distance, options.mode);

      return {
        distance,
        duration: baseDuration,
        trafficDuration: options.considerTraffic
          ? baseDuration * (1 + Math.random() * 0.5)
          : undefined,
      };
    } catch (error) {
      throw this.handleError(error, 'estimateTravelTime');
    }
  }

  /**
   * Suggest maintenance routes for network assets
   */
  async suggestMaintenanceRoutes(
    assets: { id: string; location: Coordinates; priority: number; lastMaintenance: Date }[],
    technicians: TechnicianInfo[],
    constraints: RouteConstraints
  ): Promise<{
    routes: OptimizedRoute[];
    schedule: {
      date: Date;
      routes: string[];
      estimatedCompletion: Date;
    }[];
    recommendations: {
      type: 'schedule' | 'resource' | 'efficiency';
      description: string;
      impact: string;
    }[];
  }> {
    try {
      this.validatePermissions('maintenance:plan');

      // Convert assets to work orders
      const maintenanceWorkOrders: WorkOrderInfo[] = assets.map((asset) => ({
        id: `maint_${asset.id}`,
        location: asset.location,
        type: 'maintenance',
        priority:
          asset.priority > 80
            ? 'urgent'
            : asset.priority > 60
              ? 'high'
              : asset.priority > 30
                ? 'medium'
                : 'low',
        estimatedDuration: 60, // 1 hour default
        requiredSkills: ['maintenance'],
        customerId: asset.id,
        serviceAddress: `Asset ${asset.id}`,
        specialInstructions: `Last maintenance: ${asset.lastMaintenance.toDateString()}`,
      }));

      // Optimize routes for maintenance
      const optimizationRequest: RouteOptimizationRequest = {
        technicians,
        workOrders: maintenanceWorkOrders,
        constraints,
        objectives: [
          { type: 'minimize_travel', weight: 0.4 },
          { type: 'maximize_completion', weight: 0.6 },
        ],
      };

      const result = await this.optimizeRoutes(optimizationRequest);

      // Generate maintenance schedule
      const schedule = this.generateMaintenanceSchedule(result.routes);

      // Generate maintenance-specific recommendations
      const recommendations = this.generateMaintenanceRecommendations(
        assets,
        result.routes,
        result.optimizationStats
      );

      return {
        routes: result.routes,
        schedule,
        recommendations,
      };
    } catch (error) {
      throw this.handleError(error, 'suggestMaintenanceRoutes');
    }
  }

  // Private helper methods

  private async preprocessWorkOrders(
    workOrders: WorkOrderInfo[],
    constraints: RouteConstraints
  ): Promise<WorkOrderInfo[]> {
    // Sort by priority
    const sortedOrders = [...workOrders].sort((a, b) => {
      const priorityOrder = { urgent: 4, high: 3, medium: 2, low: 1 };
      return priorityOrder[b.priority] - priorityOrder[a.priority];
    });

    // Filter by time windows if constraints require it
    if (constraints.skillMatching) {
      // Would implement skill matching logic here
    }

    return sortedOrders;
  }

  private async calculateDistanceMatrix(locations: Coordinates[]): Promise<number[][]> {
    const matrix: number[][] = [];

    for (let i = 0; i < locations.length; i++) {
      matrix[i] = [];
      for (let j = 0; j < locations.length; j++) {
        if (i === j) {
          matrix[i][j] = 0;
        } else {
          matrix[i][j] = this.calculateHaversineDistance(locations[i], locations[j]);
        }
      }
    }

    return matrix;
  }

  private async runOptimizationAlgorithm(
    technicians: TechnicianInfo[],
    workOrders: WorkOrderInfo[],
    distanceMatrix: number[][],
    constraints: RouteConstraints,
    objectives: RouteObjective[]
  ): Promise<OptimizedRoute[]> {
    const routes: OptimizedRoute[] = [];

    // Simple greedy algorithm (would be replaced with more sophisticated optimization)
    for (const technician of technicians) {
      const route = await this.createRouteForTechnician(
        technician,
        workOrders,
        distanceMatrix,
        constraints
      );

      if (route.workOrderCount > 0) {
        routes.push(route);
      }
    }

    return routes;
  }

  private async createRouteForTechnician(
    technician: TechnicianInfo,
    availableWorkOrders: WorkOrderInfo[],
    distanceMatrix: number[][],
    constraints: RouteConstraints
  ): Promise<OptimizedRoute> {
    const assignedWorkOrders: string[] = [];
    const waypoints: Coordinates[] = [technician.location];
    let totalTime = 0;
    let totalDistance = 0;

    // Filter work orders by technician skills
    const suitableWorkOrders = constraints.skillMatching
      ? availableWorkOrders.filter((wo) =>
          wo.requiredSkills.every((skill) => technician.skills.includes(skill))
        )
      : availableWorkOrders;

    // Greedy selection of work orders
    let currentLocation = technician.location;
    const maxWorkingMinutes = constraints.maxWorkingHours * 60;

    for (const workOrder of suitableWorkOrders) {
      if (assignedWorkOrders.length >= technician.maxWorkOrders) break;
      if (totalTime + workOrder.estimatedDuration > maxWorkingMinutes) break;

      const travelTime = await this.estimateTravelTime(currentLocation, workOrder.location);

      if (totalTime + travelTime.duration + workOrder.estimatedDuration <= maxWorkingMinutes) {
        assignedWorkOrders.push(workOrder.id);
        waypoints.push(workOrder.location);
        totalTime += travelTime.duration + workOrder.estimatedDuration;
        totalDistance += travelTime.distance;
        currentLocation = workOrder.location;
      }
    }

    // Calculate efficiency score
    const efficiency = totalTime > 0 ? (assignedWorkOrders.length * 60) / totalTime : 0; // Work orders per hour

    return {
      id: `route_${technician.id}`,
      name: `Route for ${technician.name}`,
      waypoints,
      type: 'maintenance',
      status: 'planned',
      assignedTechnician: technician.id,
      estimatedTime: totalTime,
      distance: totalDistance,
      priority: 'medium',
      workOrders: assignedWorkOrders,
      efficiency,
      totalTravelTime: totalTime - assignedWorkOrders.length * 60, // Subtract work time
      totalWorkTime: assignedWorkOrders.length * 60,
      workOrderCount: assignedWorkOrders.length,
      savings: {
        timeReduction: 0, // Would calculate vs unoptimized route
        fuelSavings: 0,
        efficiencyGain: 0,
      },
    };
  }

  private async postprocessRoutes(
    routes: OptimizedRoute[],
    constraints: RouteConstraints
  ): Promise<OptimizedRoute[]> {
    // Apply traffic optimization if requested
    if (constraints.trafficConsideration) {
      for (const route of routes) {
        const trafficOptimizedRoute = await this.optimizeForTraffic(route);
        Object.assign(route, trafficOptimizedRoute);
      }
    }

    return routes;
  }

  private async optimizeForTraffic(route: OptimizedRoute): Promise<Partial<OptimizedRoute>> {
    // Mock traffic optimization
    const trafficDelay = Math.random() * 0.3; // 0-30% delay
    return {
      totalTravelTime: route.totalTravelTime * (1 + trafficDelay),
      estimatedTime: route.estimatedTime ? route.estimatedTime * (1 + trafficDelay) : undefined,
    };
  }

  private calculateOptimizationStats(
    routes: OptimizedRoute[],
    originalWorkOrders: WorkOrderInfo[]
  ) {
    const totalDistance = routes.reduce((sum, route) => sum + (route.distance || 0), 0);
    const totalTime = routes.reduce((sum, route) => sum + route.totalTravelTime, 0);
    const assignedOrders = routes.reduce((sum, route) => sum + route.workOrderCount, 0);
    const utilizationRate =
      originalWorkOrders.length > 0 ? assignedOrders / originalWorkOrders.length : 0;

    // Mock improvements (would compare to unoptimized baseline)
    const improvementPercentage = Math.random() * 30 + 15; // 15-45%
    const fuelSavings = totalDistance * 0.1 * 3.5; // $3.50 per gallon, 10% savings
    const costSavings = (totalTime / 60) * 25 * 0.2; // $25/hour, 20% savings

    return {
      totalDistance,
      totalTime,
      utilizationRate,
      improvementPercentage,
      fuelSavings,
      costSavings,
    };
  }

  private generateOptimizationRecommendations(
    routes: OptimizedRoute[],
    unassignedWorkOrders: WorkOrderInfo[],
    stats: any
  ): string[] {
    const recommendations: string[] = [];

    if (unassignedWorkOrders.length > 0) {
      recommendations.push(
        `${unassignedWorkOrders.length} work orders could not be assigned. Consider adding more technicians or extending work hours.`
      );
    }

    if (stats.utilizationRate < 0.8) {
      recommendations.push(
        'Low utilization rate detected. Consider consolidating routes or reallocating resources.'
      );
    }

    const underutilizedRoutes = routes.filter((r) => r.efficiency < 0.5);
    if (underutilizedRoutes.length > 0) {
      recommendations.push(
        `${underutilizedRoutes.length} routes are underutilized. Consider rebalancing work assignments.`
      );
    }

    if (stats.improvementPercentage > 30) {
      recommendations.push(
        'Significant optimization achieved. Consider implementing this route plan immediately.'
      );
    }

    return recommendations;
  }

  private generateMaintenanceSchedule(routes: OptimizedRoute[]) {
    const schedule = [];
    const today = new Date();

    for (let day = 0; day < 7; day++) {
      const scheduleDate = new Date(today);
      scheduleDate.setDate(today.getDate() + day);

      const dayRoutes = routes.filter((_, index) => index % 7 === day);

      if (dayRoutes.length > 0) {
        const maxDuration = Math.max(...dayRoutes.map((r) => r.estimatedTime || 0));
        const completionDate = new Date(scheduleDate);
        completionDate.setMinutes(completionDate.getMinutes() + maxDuration);

        schedule.push({
          date: scheduleDate,
          routes: dayRoutes.map((r) => r.id),
          estimatedCompletion: completionDate,
        });
      }
    }

    return schedule;
  }

  private generateMaintenanceRecommendations(assets: any[], routes: OptimizedRoute[], stats: any) {
    const recommendations = [];

    // Schedule recommendation
    const highPriorityAssets = assets.filter((a) => a.priority > 80);
    if (highPriorityAssets.length > 0) {
      recommendations.push({
        type: 'schedule' as const,
        description: `${highPriorityAssets.length} high-priority assets need immediate attention`,
        impact: 'Prevents potential service outages',
      });
    }

    // Resource recommendation
    if (stats.utilizationRate < 0.7) {
      recommendations.push({
        type: 'resource' as const,
        description: 'Consider reducing maintenance crew size or reassigning resources',
        impact: `Potential cost savings of $${Math.round(stats.costSavings)}`,
      });
    }

    // Efficiency recommendation
    if (stats.improvementPercentage > 25) {
      recommendations.push({
        type: 'efficiency' as const,
        description: 'Route optimization shows significant efficiency gains',
        impact: `${Math.round(stats.improvementPercentage)}% improvement in operational efficiency`,
      });
    }

    return recommendations;
  }

  // Utility methods

  private calculateHaversineDistance(from: Coordinates, to: Coordinates): number {
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

  private distanceToTime(distance: number, mode = 'driving'): number {
    // Convert distance to time based on mode
    const speeds = {
      driving: 50, // km/h average city driving
      walking: 5, // km/h
      cycling: 15, // km/h
    };

    const speed = speeds[mode as keyof typeof speeds] || speeds.driving;
    return (distance / speed) * 60; // Convert to minutes
  }

  private async getTrafficData(
    waypoints: Coordinates[],
    departureTime?: Date
  ): Promise<TrafficData> {
    // Mock traffic data
    const totalDistance = waypoints.reduce((sum, waypoint, index) => {
      if (index === 0) return 0;
      return sum + this.calculateHaversineDistance(waypoints[index - 1], waypoint);
    }, 0);

    const baseTime = this.distanceToTime(totalDistance);
    const trafficMultiplier = 1 + Math.random() * 0.5; // 0-50% traffic delay

    return {
      route: waypoints,
      travelTimeMinutes: baseTime * trafficMultiplier,
      distance: totalDistance,
      congestionLevel:
        trafficMultiplier > 1.3 ? 'high' : trafficMultiplier > 1.1 ? 'medium' : 'low',
    };
  }

  private async calculateBaseRoute(waypoints: Coordinates[]) {
    const totalDistance = waypoints.reduce((sum, waypoint, index) => {
      if (index === 0) return 0;
      return sum + this.calculateHaversineDistance(waypoints[index - 1], waypoint);
    }, 0);

    return {
      route: waypoints,
      distance: totalDistance,
      duration: this.distanceToTime(totalDistance),
    };
  }

  private generateRouteInstructions(route: Coordinates[]): string[] {
    const instructions = ['Start at your current location'];

    for (let i = 1; i < route.length; i++) {
      const bearing = this.calculateBearing(route[i - 1], route[i]);
      const direction = this.bearingToDirection(bearing);
      instructions.push(`Head ${direction} to next location`);
    }

    instructions.push('Arrive at destination');
    return instructions;
  }

  private calculateBearing(from: Coordinates, to: Coordinates): number {
    const dLng = this.toRad(to.lng - from.lng);
    const lat1 = this.toRad(from.lat);
    const lat2 = this.toRad(to.lat);

    const y = Math.sin(dLng) * Math.cos(lat2);
    const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLng);

    return ((Math.atan2(y, x) * 180) / Math.PI + 360) % 360;
  }

  private bearingToDirection(bearing: number): string {
    const directions = [
      'north',
      'northeast',
      'east',
      'southeast',
      'south',
      'southwest',
      'west',
      'northwest',
    ];
    const index = Math.round(bearing / 45) % 8;
    return directions[index];
  }

  // Permission and error handling
  private validatePermissions(operation: string): void {
    const requiredPermissions: Record<string, string[]> = {
      'route:optimize': ['route_optimization', 'field_ops_write'],
      'route:calculate': ['route_calculation', 'field_ops_read'],
      'maintenance:plan': ['maintenance_planning', 'asset_management'],
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
    console.error(`Route Optimization Engine Error (${context}):`, error);
    return new Error(`Route optimization failed: ${error.message || 'Unknown error'}`);
  }
}
