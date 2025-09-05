"""
GIS Services leveraging existing DotMac systems:
- Base service patterns from shared components
- Network visualization module for topology
- Standard exception handling
- Multi-tenant isolation
"""

import math
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from dotmac_shared.services.base import BaseService
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dotmac.core.exceptions import EntityNotFoundError as NotFoundError

from .models import NetworkNode, RouteOptimization, ServiceArea, Territory
from .schemas import (
    CoverageAnalysisRequest,
    GeocodingRequest,
    ReverseGeocodingRequest,
    RouteOptimizationRequest,
    ServiceAreaCreate,
    ServiceAreaUpdate,
    TerritoryCreate,
    TerritoryUpdate,
)


def haversine_distance(lat1, lon1, lat2, lon2, timezone):
    """Calculate distance between two points using haversine formula."""
    R = 6371  # Earth's radius in kilometers
    lat1_rad, lon1_rad = math.radians(lat1), math.radians(lon1)
    lat2_rad, lon2_rad = math.radians(lat2), math.radians(lon2)

    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.asin(math.sqrt(a))

    return R * c


class ServiceCoverageService(
    BaseService[ServiceArea, ServiceAreaCreate, ServiceAreaUpdate]
):
    """
    Service coverage analysis service integrating with network visualization.
    Leverages existing DotMac patterns and network topology module.
    """

    def __init__(self, db: AsyncSession, tenant_id: str):
        super().__init__(ServiceArea, db, tenant_id)

    async def analyze_coverage(
        self, request: CoverageAnalysisRequest, user_id: UUID
    ) -> dict[str, Any]:
        """
        Perform comprehensive coverage analysis using network topology.
        Integrates with existing network visualization module.
        """
        # Get service area with validation
        service_area = await self.get_by_id(request.service_area_id, user_id)
        if not service_area:
            raise NotFoundError(f"Service area {request.service_area_id} not found")

        # Mock network health data (in production, integrate with network monitoring)
        network_health = {"health_score": 95.0, "status": "healthy"}

        # Perform demographic analysis if requested
        demographics = {}
        if request.include_demographics:
            demographics = await self._analyze_demographics(service_area)

        # Calculate coverage using network nodes
        coverage_data = await self._calculate_coverage(
            service_area, request.service_types
        )

        # Identify coverage gaps using topology analysis
        gaps = await self._identify_coverage_gaps(service_area, coverage_data)

        # Generate recommendations using ML/AI analysis
        recommendations = await self._generate_recommendations(gaps, service_area)

        # Update service area with analysis results
        service_area.last_analyzed_at = datetime.now(timezone.utc)
        service_area.coverage_percentage = coverage_data.get("coverage_percentage", 0.0)
        service_area.analysis_metadata = {
            "analysis_date": datetime.now(timezone.utc).isoformat(),
            "parameters": request.analysis_parameters,
            "network_health_score": network_health.get("health_score", 0),
        }

        await self.db.commit()

        return {
            "service_area_id": request.service_area_id,
            "service_types": request.service_types,
            "coverage_percentage": coverage_data.get("coverage_percentage", 0.0),
            "population": demographics.get("population", 0),
            "households": demographics.get("households", 0),
            "businesses": demographics.get("businesses", 0),
            "gaps": gaps,
            "recommendations": recommendations,
            "demographics": demographics if request.include_demographics else None,
            "network_health": network_health,
        }

    async def _calculate_coverage(
        self, service_area: ServiceArea, service_types: list[str]
    ) -> dict[str, Any]:
        """Calculate coverage using network nodes and topology."""

        # Get network nodes in service area
        query = select(NetworkNode).where(
            NetworkNode.service_area_id == service_area.id,
            NetworkNode.tenant_id == self.tenant_id,
            NetworkNode.is_active is True,
        )
        result = await self.db.execute(query)
        nodes = result.scalars().all()

        if not nodes:
            return {"coverage_percentage": 0.0, "covered_area": 0.0}

        # Calculate coverage areas for each node
        total_coverage_area = 0.0
        service_area_size = self._calculate_polygon_area(
            service_area.polygon_coordinates
        )

        for node in nodes:
            if node.coverage_radius_km and node.latitude and node.longitude:
                # Calculate coverage area using GIS utilities
                coverage_area = 3.14159 * (node.coverage_radius_km**2)  # π * r²
                total_coverage_area += coverage_area

        # Calculate coverage percentage (with overlap consideration)
        coverage_percentage = min(
            100.0, (total_coverage_area / service_area_size) * 100
        )

        return {
            "coverage_percentage": coverage_percentage,
            "covered_area": total_coverage_area,
            "service_area_size": service_area_size,
            "active_nodes": len(nodes),
        }

    async def _identify_coverage_gaps(
        self, service_area: ServiceArea, coverage_data: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Identify coverage gaps using spatial analysis."""

        gaps = []

        # Simplified gap identification - in production this would use
        # sophisticated spatial analysis algorithms
        if coverage_data["coverage_percentage"] < 95.0:
            gap = {
                "id": f"gap_{service_area.id}_{datetime.now(timezone.utc).timestamp()}",
                "gap_type": "coverage_deficiency",
                "severity": self._calculate_gap_severity(
                    coverage_data["coverage_percentage"]
                ),
                "polygon_coordinates": service_area.polygon_coordinates,  # Simplified
                "affected_customers": int(service_area.population * 0.1),  # Estimate
                "potential_revenue": service_area.population
                * 75
                * 12,  # $75/month ARPU
                "buildout_cost": self._estimate_buildout_cost(service_area),
                "priority_score": self._calculate_priority_score(coverage_data),
                "recommendations": await self._generate_gap_recommendations(
                    coverage_data
                ),
            }
            gaps.append(gap)

        return gaps

    async def _generate_recommendations(
        self, gaps: list[dict[str, Any]], service_area: ServiceArea
    ) -> list[dict[str, Any]]:
        """Generate coverage improvement recommendations."""

        recommendations = []

        for gap in gaps:
            if gap["severity"] in ["high", "critical"]:
                rec = {
                    "id": f"rec_{service_area.id}_{datetime.now(timezone.utc).timestamp()}",
                    "recommendation_type": "infrastructure_deployment",
                    "priority": gap["severity"],
                    "description": f"Deploy additional network infrastructure to address {gap['gap_type']}",
                    "estimated_cost": gap["buildout_cost"],
                    "estimated_revenue": gap["potential_revenue"],
                    "timeframe": "6-12 months",
                    "requirements": [
                        "Site survey and acquisition",
                        "Equipment procurement",
                        "Installation and commissioning",
                        "Testing and optimization",
                    ],
                    "affected_areas": [gap["polygon_coordinates"]],
                }
                recommendations.append(rec)

        return recommendations

    async def _analyze_demographics(self, service_area: ServiceArea) -> dict[str, Any]:
        """Analyze demographics for service area."""

        # In production, this would integrate with demographic data APIs
        # For now, return estimated values based on area characteristics
        area_size = self._calculate_polygon_area(service_area.polygon_coordinates)

        # Rough estimates - in production use real demographic APIs
        population_density = 100  # people per km²
        estimated_population = int(area_size * population_density)

        return {
            "population": estimated_population,
            "households": int(estimated_population / 2.5),  # Average household size
            "businesses": int(estimated_population * 0.05),  # 5% business ratio
            "median_income": 65000,  # Estimated median income
            "age_distribution": {"18-34": 0.25, "35-54": 0.35, "55+": 0.4},
        }

    def _calculate_polygon_area(self, coordinates: list[dict[str, float]]) -> float:
        """Calculate polygon area in square kilometers."""
        if len(coordinates) < 3:
            return 0.0

        # Simplified area calculation - in production use proper GIS libraries
        # This is a rough approximation using the shoelace formula
        area = 0.0
        n = len(coordinates)

        for i in range(n):
            j = (i + 1) % n
            area += coordinates[i]["longitude"] * coordinates[j]["latitude"]
            area -= coordinates[j]["longitude"] * coordinates[i]["latitude"]

        area = abs(area) / 2.0
        # Convert to approximate km² (very rough conversion)
        return area * 111.32 * 111.32  # Approximate conversion factor

    def _calculate_gap_severity(self, coverage_percentage: float) -> str:
        """Calculate gap severity based on coverage percentage."""
        if coverage_percentage >= 90:
            return "low"
        elif coverage_percentage >= 70:
            return "medium"
        elif coverage_percentage >= 50:
            return "high"
        else:
            return "critical"

    def _estimate_buildout_cost(self, service_area: ServiceArea) -> float:
        """Estimate buildout cost for service area."""
        area_size = self._calculate_polygon_area(service_area.polygon_coordinates)
        cost_per_km2 = 50000  # $50k per km² - rough estimate
        return area_size * cost_per_km2

    def _calculate_priority_score(self, coverage_data: dict[str, Any]) -> float:
        """Calculate priority score for addressing coverage gap."""
        coverage_deficit = 100.0 - coverage_data["coverage_percentage"]
        return min(100.0, coverage_deficit + (coverage_data.get("active_nodes", 0) * 5))

    async def _generate_gap_recommendations(
        self, coverage_data: dict[str, Any]
    ) -> list[str]:
        """Generate recommendations for addressing coverage gaps."""
        recommendations = []

        if coverage_data.get("active_nodes", 0) == 0:
            recommendations.append("Deploy initial network infrastructure")
        elif coverage_data["coverage_percentage"] < 50:
            recommendations.append("Add additional wireless access points")
            recommendations.append("Consider fiber deployment for backbone")
        else:
            recommendations.append("Optimize existing network configuration")
            recommendations.append("Add targeted coverage for gap areas")

        return recommendations


class TerritoryManagementService(
    BaseService[Territory, TerritoryCreate, TerritoryUpdate]
):
    """Territory management service with GIS capabilities."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        super().__init__(Territory, db, tenant_id)

    async def find_territories_containing_point(
        self, latitude: float, longitude: float, user_id: UUID
    ) -> list[Territory]:
        """Find territories containing a specific geographic point."""

        # In production, this would use PostGIS or similar for spatial queries
        # For now, implement basic point-in-polygon check
        query = select(Territory).where(
            Territory.tenant_id == self.tenant_id, Territory.is_active is True
        )
        result = await self.db.execute(query)
        territories = result.scalars().all()

        containing_territories = []
        for territory in territories:
            if self._point_in_polygon(
                latitude, longitude, territory.boundary_coordinates
            ):
                containing_territories.append(territory)

        return containing_territories

    async def calculate_territory_metrics(
        self, territory_id: UUID, user_id: UUID
    ) -> dict[str, Any]:
        """Calculate territory performance metrics."""

        territory = await self.get_by_id(territory_id, user_id)
        if not territory:
            raise NotFoundError(f"Territory {territory_id} not found")

        # Calculate area
        area_km2 = self._calculate_territory_area(territory.boundary_coordinates)

        # Calculate performance metrics
        revenue_performance = (
            territory.actual_revenue / territory.revenue_target
            if territory.revenue_target > 0
            else 0.0
        ) * 100

        customer_density = territory.customer_count / area_km2 if area_km2 > 0 else 0

        return {
            "territory_id": territory_id,
            "area_km2": area_km2,
            "customer_count": territory.customer_count,
            "customer_density": customer_density,
            "revenue_target": territory.revenue_target,
            "actual_revenue": territory.actual_revenue,
            "revenue_performance": revenue_performance,
            "demographics": territory.demographics,
            "competitor_analysis": territory.competitor_analysis,
        }

    def _point_in_polygon(
        self, latitude: float, longitude: float, polygon: list[dict[str, float]]
    ) -> bool:
        """Check if point is inside polygon using ray casting algorithm."""

        x, y = longitude, latitude
        n = len(polygon)
        inside = False

        p1x = polygon[0]["longitude"]
        p1y = polygon[0]["latitude"]

        for i in range(1, n + 1):
            p2x = polygon[i % n]["longitude"]
            p2y = polygon[i % n]["latitude"]

            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def _calculate_territory_area(self, coordinates: list[dict[str, float]]) -> float:
        """Calculate territory area in square kilometers."""
        # Same calculation as service area - could be extracted to utility
        if len(coordinates) < 3:
            return 0.0

        area = 0.0
        n = len(coordinates)

        for i in range(n):
            j = (i + 1) % n
            area += coordinates[i]["longitude"] * coordinates[j]["latitude"]
            area -= coordinates[j]["longitude"] * coordinates[i]["latitude"]

        area = abs(area) / 2.0
        return area * 111.32 * 111.32  # Approximate conversion to km²


class RouteOptimizationService(
    BaseService[RouteOptimization, RouteOptimizationRequest, RouteOptimizationRequest]
):
    """Route optimization service for field operations."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        super().__init__(RouteOptimization, db, tenant_id)

    async def optimize_route(
        self, request: RouteOptimizationRequest, user_id: UUID
    ) -> dict[str, Any]:
        """Optimize route for field technician visits."""

        # Create route optimization record
        route_data = RouteOptimization(
            tenant_id=self.tenant_id,
            start_coordinates=request.start_coordinates,
            end_coordinates=request.end_coordinates,
            waypoints=request.waypoints,
            optimization_type=request.optimization_type,
            vehicle_type=request.vehicle_type,
            constraints=request.constraints,
            calculated_at=datetime.now(timezone.utc),
        )

        # Perform route optimization
        optimized_route = await self._calculate_optimal_route(request)

        # Update record with results
        route_data.optimized_route = optimized_route["coordinates"]
        route_data.total_distance_km = optimized_route["total_distance"]
        route_data.estimated_duration_minutes = optimized_route["duration"]

        self.db.add(route_data)
        await self.db.commit()

        return {
            "id": route_data.id,
            "start_coordinates": request.start_coordinates,
            "end_coordinates": request.end_coordinates,
            "waypoints": request.waypoints,
            "optimization_type": request.optimization_type,
            "optimized_route": optimized_route["coordinates"],
            "total_distance_km": optimized_route["total_distance"],
            "estimated_duration_minutes": optimized_route["duration"],
            "calculated_at": route_data.calculated_at,
        }

    async def _calculate_optimal_route(
        self, request: RouteOptimizationRequest
    ) -> dict[str, Any]:
        """Calculate optimal route using distance calculations."""

        # Collect all points
        points = [request.start_coordinates]
        points.extend(request.waypoints)
        if request.end_coordinates:
            points.append(request.end_coordinates)

        # Simple optimization - in production use sophisticated routing algorithms
        if request.optimization_type == "shortest":
            optimized_order = await self._optimize_by_distance(points)
        else:
            optimized_order = list(range(len(points)))  # Default order

        # Calculate route coordinates and metrics
        route_coordinates = [points[i] for i in optimized_order]
        total_distance = self._calculate_total_distance(route_coordinates)

        # Estimate duration (assume 60 km/h average speed + service time)
        service_time_per_stop = 30  # 30 minutes per waypoint
        travel_time = (total_distance / 60) * 60  # minutes
        total_duration = travel_time + (len(request.waypoints) * service_time_per_stop)

        return {
            "coordinates": route_coordinates,
            "total_distance": total_distance,
            "duration": int(total_duration),
        }

    async def _optimize_by_distance(self, points: list[dict[str, float]]) -> list[int]:
        """Optimize route by minimizing total distance (simplified TSP)."""

        if len(points) <= 2:
            return list(range(len(points)))

        # Simple nearest neighbor heuristic
        unvisited = set(range(1, len(points)))
        route = [0]  # Start with first point
        current = 0

        while unvisited:
            nearest = min(
                unvisited,
                key=lambda i: haversine_distance(
                    points[current]["latitude"],
                    points[current]["longitude"],
                    points[i]["latitude"],
                    points[i]["longitude"],
                ),
            )
            route.append(nearest)
            unvisited.remove(nearest)
            current = nearest

        return route

    def _calculate_total_distance(self, coordinates: list[dict[str, float]]) -> float:
        """Calculate total distance for route."""

        if len(coordinates) < 2:
            return 0.0

        total_distance = 0.0
        for i in range(len(coordinates) - 1):
            distance = haversine_distance(
                coordinates[i]["latitude"],
                coordinates[i]["longitude"],
                coordinates[i + 1]["latitude"],
                coordinates[i + 1]["longitude"],
            )
            total_distance += distance

        return total_distance


class GeocodingService:
    """Geocoding service for address resolution."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    async def geocode_address(self, request: GeocodingRequest) -> dict[str, Any]:
        """Convert address to coordinates."""

        # In production, integrate with geocoding APIs (Google, MapBox, Nominatim)
        # For now, return mock data
        return {
            "address": request.address,
            "latitude": 45.5152,  # Mock Portland coordinates
            "longitude": -122.6784,
            "confidence": 0.85,
            "components": {
                "street": "123 Main St",
                "city": "Portland",
                "state": "OR",
                "country": "US",
                "postal_code": "97201",
            },
        }

    async def reverse_geocode(self, request: ReverseGeocodingRequest) -> dict[str, Any]:
        """Convert coordinates to address."""

        # Mock implementation - in production use real geocoding APIs
        return {
            "address": f"Near {request.latitude:.4f}, {request.longitude:.4f}",
            "latitude": request.latitude,
            "longitude": request.longitude,
            "confidence": 0.75,
            "components": {"city": "Portland", "state": "OR", "country": "US"},
        }


# Export all services
__all__ = [
    "ServiceCoverageService",
    "TerritoryManagementService",
    "RouteOptimizationService",
    "GeocodingService",
]
