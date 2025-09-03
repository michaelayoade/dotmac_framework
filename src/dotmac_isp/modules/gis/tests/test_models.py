"""
Unit tests for GIS models.
Tests model creation, validation, and relationships.
"""

from datetime import datetime
from uuid import uuid4

import pytest

from dotmac_isp.modules.gis.models import (
    CoverageGap,
    CoverageStatusEnum,
    NetworkNode,
    NetworkNodeTypeEnum,
    RouteOptimization,
    ServiceArea,
    ServiceTypeEnum,
    Territory,
)


class TestServiceArea:
    """Test ServiceArea model."""

    def test_create_service_area(self):
        """Test creating a service area."""
        tenant_id = uuid4()
        polygon_coords = [
            {"latitude": 45.5, "longitude": -122.6},
            {"latitude": 45.6, "longitude": -122.6},
            {"latitude": 45.6, "longitude": -122.5},
            {"latitude": 45.5, "longitude": -122.5},
        ]

        area = ServiceArea(
            tenant_id=tenant_id,
            name="Test Service Area",
            description="Test area for coverage",
            polygon_coordinates=polygon_coords,
            service_types=["fiber", "wireless"],
            population=5000,
            households=2000,
            businesses=100,
            coverage_percentage=85.0,
        )

        assert area.name == "Test Service Area"
        assert area.tenant_id == tenant_id
        assert len(area.polygon_coordinates) == 4
        assert area.coverage_percentage == 85.0
        assert "fiber" in area.service_types
        assert "wireless" in area.service_types

    def test_service_area_validation(self):
        """Test service area field validation."""
        # Coverage percentage should be valid
        area = ServiceArea(
            tenant_id=uuid4(),
            name="Test Area",
            polygon_coordinates=[
                {"latitude": 45.5, "longitude": -122.6},
                {"latitude": 45.6, "longitude": -122.6},
                {"latitude": 45.5, "longitude": -122.5},
            ],
            service_types=["fiber"],
            coverage_percentage=95.0,
        )

        assert 0 <= area.coverage_percentage <= 100


class TestNetworkNode:
    """Test NetworkNode model."""

    def test_create_network_node(self):
        """Test creating a network node."""
        tenant_id = uuid4()
        service_area_id = uuid4()

        node = NetworkNode(
            tenant_id=tenant_id,
            service_area_id=service_area_id,
            name="Test Router",
            description="Core router node",
            node_type=NetworkNodeTypeEnum.CORE_ROUTER,
            latitude=45.5152,
            longitude=-122.6784,
            ip_address="192.168.1.1",
            mac_address="AA:BB:CC:DD:EE:FF",
            bandwidth_mbps=10000,
            coverage_radius_km=5.0,
            operational_status="active",
            manufacturer="Cisco",
            model="ISR4331",
        )

        assert node.name == "Test Router"
        assert node.node_type == NetworkNodeTypeEnum.CORE_ROUTER
        assert node.latitude == 45.5152
        assert node.longitude == -122.6784
        assert node.bandwidth_mbps == 10000
        assert node.coverage_radius_km == 5.0

    def test_node_type_enum(self):
        """Test NetworkNodeTypeEnum values."""
        assert NetworkNodeTypeEnum.CORE_ROUTER == "core_router"
        assert NetworkNodeTypeEnum.WIFI_AP == "wifi_ap"
        assert NetworkNodeTypeEnum.CELL_TOWER == "cell_tower"

    def test_wireless_node_with_coverage(self):
        """Test wireless node with coverage radius."""
        node = NetworkNode(
            tenant_id=uuid4(),
            name="WiFi AP",
            node_type=NetworkNodeTypeEnum.WIFI_AP,
            latitude=45.5,
            longitude=-122.6,
            coverage_radius_km=0.5,  # 500m coverage
            bandwidth_mbps=100,
        )

        assert node.node_type == NetworkNodeTypeEnum.WIFI_AP
        assert node.coverage_radius_km == 0.5


class TestCoverageGap:
    """Test CoverageGap model."""

    def test_create_coverage_gap(self):
        """Test creating a coverage gap."""
        service_area_id = uuid4()
        tenant_id = uuid4()

        gap_coords = [
            {"latitude": 45.51, "longitude": -122.67},
            {"latitude": 45.52, "longitude": -122.67},
            {"latitude": 45.52, "longitude": -122.66},
        ]

        gap = CoverageGap(
            tenant_id=tenant_id,
            service_area_id=service_area_id,
            name="Coverage Gap 1",
            description="No fiber coverage area",
            gap_type="no_coverage",
            severity="high",
            polygon_coordinates=gap_coords,
            affected_customers=150,
            potential_revenue=135000.0,  # 150 customers * $75/month * 12 months
            buildout_cost=250000.0,
            priority_score=85.0,
            recommendations=[
                "Deploy fiber infrastructure",
                "Consider wireless alternative",
            ],
        )

        assert gap.gap_type == "no_coverage"
        assert gap.severity == "high"
        assert gap.affected_customers == 150
        assert gap.potential_revenue == 135000.0
        assert len(gap.recommendations) == 2


class TestTerritory:
    """Test Territory model."""

    def test_create_territory(self):
        """Test creating a sales territory."""
        tenant_id = uuid4()
        assigned_user_id = uuid4()

        boundary = [
            {"latitude": 45.4, "longitude": -122.8},
            {"latitude": 45.6, "longitude": -122.8},
            {"latitude": 45.6, "longitude": -122.4},
            {"latitude": 45.4, "longitude": -122.4},
        ]

        territory = Territory(
            tenant_id=tenant_id,
            name="Northwest Territory",
            description="Sales territory for NW Portland",
            boundary_coordinates=boundary,
            territory_type="sales",
            color="#FF5733",
            assigned_user_id=assigned_user_id,
            assigned_team="Sales Team A",
            customer_count=1250,
            revenue_target=750000.0,
            actual_revenue=680000.0,
        )

        assert territory.name == "Northwest Territory"
        assert territory.territory_type == "sales"
        assert territory.color == "#FF5733"
        assert territory.customer_count == 1250
        assert territory.revenue_target == 750000.0
        assert territory.actual_revenue == 680000.0

    def test_territory_performance_calculation(self):
        """Test territory performance metrics."""
        territory = Territory(
            tenant_id=uuid4(),
            name="Test Territory",
            boundary_coordinates=[],
            revenue_target=100000.0,
            actual_revenue=85000.0,
        )

        # Performance would be calculated in service layer
        performance = (territory.actual_revenue / territory.revenue_target) * 100
        assert performance == 85.0


class TestRouteOptimization:
    """Test RouteOptimization model."""

    def test_create_route_optimization(self):
        """Test creating a route optimization record."""
        tenant_id = uuid4()

        start_coords = {"latitude": 45.5152, "longitude": -122.6784}
        end_coords = {"latitude": 45.5200, "longitude": -122.6700}
        waypoints = [
            {"latitude": 45.5175, "longitude": -122.6750},
            {"latitude": 45.5180, "longitude": -122.6720},
        ]

        optimized_route = [start_coords, waypoints[0], waypoints[1], end_coords]

        route = RouteOptimization(
            tenant_id=tenant_id,
            name="Field Service Route",
            description="Technician service calls",
            start_coordinates=start_coords,
            end_coordinates=end_coords,
            waypoints=waypoints,
            optimization_type="shortest",
            vehicle_type="truck",
            constraints={"max_duration_hours": 8, "break_duration_minutes": 30},
            optimized_route=optimized_route,
            total_distance_km=12.5,
            estimated_duration_minutes=180,
            calculated_at=datetime.now(timezone.utc),
        )

        assert route.optimization_type == "shortest"
        assert route.vehicle_type == "truck"
        assert route.total_distance_km == 12.5
        assert route.estimated_duration_minutes == 180
        assert len(route.waypoints) == 2
        assert len(route.optimized_route) == 4


class TestEnums:
    """Test GIS enums."""

    def test_service_type_enum(self):
        """Test ServiceTypeEnum values."""
        assert ServiceTypeEnum.FIBER == "fiber"
        assert ServiceTypeEnum.WIRELESS == "wireless"
        assert ServiceTypeEnum.CABLE == "cable"
        assert ServiceTypeEnum.DSL == "dsl"
        assert ServiceTypeEnum.FIXED_WIRELESS == "fixed_wireless"

    def test_network_node_type_enum(self):
        """Test NetworkNodeTypeEnum values."""
        assert NetworkNodeTypeEnum.CORE_ROUTER == "core_router"
        assert NetworkNodeTypeEnum.DISTRIBUTION_ROUTER == "distribution_router"
        assert NetworkNodeTypeEnum.ACCESS_SWITCH == "access_switch"
        assert NetworkNodeTypeEnum.WIFI_AP == "wifi_ap"
        assert NetworkNodeTypeEnum.CELL_TOWER == "cell_tower"
        assert NetworkNodeTypeEnum.FIBER_SPLICE == "fiber_splice"
        assert NetworkNodeTypeEnum.POP == "pop"

    def test_coverage_status_enum(self):
        """Test CoverageStatusEnum values."""
        assert CoverageStatusEnum.EXCELLENT == "excellent"
        assert CoverageStatusEnum.GOOD == "good"
        assert CoverageStatusEnum.POOR == "poor"
        assert CoverageStatusEnum.NO_COVERAGE == "no_coverage"
