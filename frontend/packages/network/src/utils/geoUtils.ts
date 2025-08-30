/**
 * Geographic utilities for network mapping
 * Helper functions for geographic calculations and mapping operations
 */

import type { NetworkNode, ServiceArea } from '../types';

export const geoUtils = {
  /**
   * Calculate distance between two geographic points (Haversine formula)
   */
  calculateDistance: (
    lat1: number,
    lon1: number,
    lat2: number,
    lon2: number
  ): number => {
    const R = 6371; // Earth's radius in kilometers
    const dLat = geoUtils.toRadians(lat2 - lat1);
    const dLon = geoUtils.toRadians(lon2 - lon1);

    const a =
      Math.sin(dLat / 2) * Math.sin(dLat / 2) +
      Math.cos(geoUtils.toRadians(lat1)) *
      Math.cos(geoUtils.toRadians(lat2)) *
      Math.sin(dLon / 2) * Math.sin(dLon / 2);

    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
  },

  /**
   * Convert degrees to radians
   */
  toRadians: (degrees: number): number => {
    return degrees * (Math.PI / 180);
  },

  /**
   * Calculate the center point of multiple coordinates
   */
  calculateCenter: (coordinates: { latitude: number; longitude: number }[]): {
    latitude: number;
    longitude: number;
  } => {
    if (coordinates.length === 0) {
      return { latitude: 0, longitude: 0 };
    }

    const totalLat = coordinates.reduce((sum, coord) => sum + coord.latitude, 0);
    const totalLon = coordinates.reduce((sum, coord) => sum + coord.longitude, 0);

    return {
      latitude: totalLat / coordinates.length,
      longitude: totalLon / coordinates.length
    };
  },

  /**
   * Calculate bounding box for a set of coordinates
   */
  calculateBounds: (coordinates: { latitude: number; longitude: number }[]): {
    north: number;
    south: number;
    east: number;
    west: number;
  } => {
    if (coordinates.length === 0) {
      return { north: 0, south: 0, east: 0, west: 0 };
    }

    const lats = coordinates.map(coord => coord.latitude);
    const lons = coordinates.map(coord => coord.longitude);

    return {
      north: Math.max(...lats),
      south: Math.min(...lats),
      east: Math.max(...lons),
      west: Math.min(...lons)
    };
  },

  /**
   * Check if a point is within a polygon (ray casting algorithm)
   */
  isPointInPolygon: (
    point: { latitude: number; longitude: number },
    polygon: { latitude: number; longitude: number }[]
  ): boolean => {
    const x = point.longitude;
    const y = point.latitude;
    let inside = false;

    for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
      const xi = polygon[i].longitude;
      const yi = polygon[i].latitude;
      const xj = polygon[j].longitude;
      const yj = polygon[j].latitude;

      if (((yi > y) !== (yj > y)) && (x < (xj - xi) * (y - yi) / (yj - yi) + xi)) {
        inside = !inside;
      }
    }

    return inside;
  },

  /**
   * Find nodes within a circular area
   */
  findNodesInRadius: (
    nodes: NetworkNode[],
    center: { latitude: number; longitude: number },
    radiusKm: number
  ): NetworkNode[] => {
    return nodes.filter(node => {
      if (!node.latitude || !node.longitude) return false;

      const distance = geoUtils.calculateDistance(
        center.latitude,
        center.longitude,
        node.latitude,
        node.longitude
      );

      return distance <= radiusKm;
    });
  },

  /**
   * Calculate coverage area for a wireless node
   */
  calculateCoverageArea: (
    node: NetworkNode,
    radiusKm: number
  ): { latitude: number; longitude: number }[] => {
    if (!node.latitude || !node.longitude) return [];

    const points: { latitude: number; longitude: number }[] = [];
    const segments = 32; // Number of points to create circle

    for (let i = 0; i < segments; i++) {
      const angle = (i / segments) * 2 * Math.PI;

      // Convert radius to degrees (approximate)
      const latOffset = (radiusKm / 111.32) * Math.cos(angle);
      const lonOffset = (radiusKm / (111.32 * Math.cos(geoUtils.toRadians(node.latitude)))) * Math.sin(angle);

      points.push({
        latitude: node.latitude + latOffset,
        longitude: node.longitude + lonOffset
      });
    }

    return points;
  },

  /**
   * Calculate optimal placement for new infrastructure
   */
  calculateOptimalPlacement: (
    existingNodes: NetworkNode[],
    serviceAreas: ServiceArea[],
    targetCoverage: number = 0.8
  ): { latitude: number; longitude: number; score: number }[] => {
    const candidates: { latitude: number; longitude: number; score: number }[] = [];

    serviceAreas.forEach(area => {
      if (!area.polygon_coordinates?.coordinates?.[0]) return;

      const center = geoUtils.calculateCenterFromPolygon(area.polygon_coordinates.coordinates[0]);

      // Calculate coverage score based on existing nodes
      const nearbyNodes = geoUtils.findNodesInRadius(existingNodes, center, 5); // 5km radius
      const currentCoverage = Math.min(nearbyNodes.length * 0.2, 1); // Simplified coverage calculation

      const score = (targetCoverage - currentCoverage) * area.population / 1000;

      if (score > 0) {
        candidates.push({
          ...center,
          score
        });
      }
    });

    return candidates.sort((a, b) => b.score - a.score);
  },

  /**
   * Calculate center from polygon coordinates
   */
  calculateCenterFromPolygon: (coordinates: [number, number][]): { latitude: number; longitude: number } => {
    const points = coordinates.map(coord => ({
      latitude: coord[1],
      longitude: coord[0]
    }));

    return geoUtils.calculateCenter(points);
  },

  /**
   * Convert between coordinate systems
   */
  convertCoordinates: {
    /**
     * Convert Web Mercator to WGS84
     */
    webMercatorToWGS84: (x: number, y: number): { latitude: number; longitude: number } => {
      const longitude = x / 20037508.34 * 180;
      let latitude = y / 20037508.34 * 180;
      latitude = 180 / Math.PI * (2 * Math.atan(Math.exp(latitude * Math.PI / 180)) - Math.PI / 2);

      return { latitude, longitude };
    },

    /**
     * Convert WGS84 to Web Mercator
     */
    WGS84ToWebMercator: (latitude: number, longitude: number): { x: number; y: number } => {
      const x = longitude * 20037508.34 / 180;
      let y = Math.log(Math.tan((90 + latitude) * Math.PI / 360)) / (Math.PI / 180);
      y = y * 20037508.34 / 180;

      return { x, y };
    }
  },

  /**
   * Validate geographic coordinates
   */
  validateCoordinates: (latitude: number, longitude: number): boolean => {
    return (
      latitude >= -90 && latitude <= 90 &&
      longitude >= -180 && longitude <= 180
    );
  },

  /**
   * Calculate signal strength based on distance and obstacles
   */
  calculateSignalStrength: (
    transmitter: NetworkNode,
    receiver: { latitude: number; longitude: number },
    frequency: number = 2400, // MHz
    txPower: number = 20 // dBm
  ): number => {
    if (!transmitter.latitude || !transmitter.longitude) return 0;

    const distance = geoUtils.calculateDistance(
      transmitter.latitude,
      transmitter.longitude,
      receiver.latitude,
      receiver.longitude
    );

    // Free space path loss calculation
    const fspl = 20 * Math.log10(distance * 1000) + 20 * Math.log10(frequency) + 32.45;
    const receivedPower = txPower - fspl;

    // Convert to signal strength percentage (simplified)
    const minSignal = -100; // dBm
    const maxSignal = -30;   // dBm

    const signalPercentage = Math.max(0, Math.min(100,
      ((receivedPower - minSignal) / (maxSignal - minSignal)) * 100
    ));

    return signalPercentage;
  }
};
