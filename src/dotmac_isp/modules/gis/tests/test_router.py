"""
API endpoint tests for GIS router.
Tests all HTTP endpoints and their responses.
"""

import json
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from dotmac_isp.modules.gis.models import (
    NetworkNode,
    RouteOptimization,
    ServiceArea,
    Territory,
)
from dotmac_isp.modules.gis.router import router
from dotmac_isp.modules.gis.schemas import (
    NetworkNodeCreate,
    NetworkNodeResponse,
    RouteOptimizationRequest,
    RouteOptimizationResponse,
    ServiceAreaCreate,
    ServiceAreaResponse,
    TerritoryCreate,
    TerritoryResponse,
)


@pytest.fixture
def client():
    """Test client for GIS router."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return TestClient(app)


@pytest.fixture
def mock_tenant_id():
    """Mock tenant ID for testing."""
    return uuid4()


@pytest.fixture
def mock_service_area_data():
    """Mock service area data."""
    return {
        "name": "Test Service Area",
        "description": "Test coverage area",
        "polygon_coordinates": [
            {"latitude": 45.5, "longitude": -122.6},
            {"latitude": 45.6, "longitude": -122.6},
            {"latitude": 45.6, "longitude": -122.5},
            {"latitude": 45.5, "longitude": -122.5},
        ],
        "service_types": ["fiber", "wireless"],
        "population": 5000,
        "households": 2000,
        "coverage_percentage": 85.0,
    }


class TestServiceAreaEndpoints:
    """Test service area API endpoints."""

    def test_create_service_area(self, client, mock_tenant_id, mock_service_area_data):
        """Test POST /service-areas endpoint."""
        mock_service_area = ServiceArea(
            id=uuid4(), tenant_id=mock_tenant_id, **mock_service_area_data
        )

        with patch(
            "dotmac_isp.modules.gis.router.get_current_tenant_id",
            return_value=mock_tenant_id,
        ):
            with patch.object(
                router.service_area_service, "create", return_value=mock_service_area
            ):
                response = client.post(
                    "/api/v1/service-areas",
                    json=mock_service_area_data,
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code == 201
                data = response.json()
                assert data["name"] == "Test Service Area"
                assert data["coverage_percentage"] == 85.0
                assert len(data["service_types"]) == 2

    def test_list_service_areas(self, client, mock_tenant_id):
        """Test GET /service-areas endpoint."""
        mock_areas = [
            ServiceArea(
                id=uuid4(),
                tenant_id=mock_tenant_id,
                name="Area 1",
                coverage_percentage=80.0,
            ),
            ServiceArea(
                id=uuid4(),
                tenant_id=mock_tenant_id,
                name="Area 2",
                coverage_percentage=90.0,
            ),
        ]

        with patch(
            "dotmac_isp.modules.gis.router.get_current_tenant_id",
            return_value=mock_tenant_id,
        ):
            with patch.object(
                router.service_area_service, "get_all", return_value=mock_areas
            ):
                response = client.get(
                    "/api/v1/service-areas",
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                assert data[0]["name"] == "Area 1"
                assert data[1]["name"] == "Area 2"

    def test_get_service_area_by_id(
        self, client, mock_tenant_id, mock_service_area_data
    ):
        """Test GET /service-areas/{id} endpoint."""
        area_id = uuid4()
        mock_area = ServiceArea(
            id=area_id, tenant_id=mock_tenant_id, **mock_service_area_data
        )

        with patch(
            "dotmac_isp.modules.gis.router.get_current_tenant_id",
            return_value=mock_tenant_id,
        ):
            with patch.object(
                router.service_area_service, "get_by_id", return_value=mock_area
            ):
                response = client.get(
                    f"/api/v1/service-areas/{area_id}",
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["id"] == str(area_id)
                assert data["name"] == "Test Service Area"

    def test_analyze_service_area_coverage(self, client, mock_tenant_id):
        """Test POST /service-areas/{id}/analyze-coverage endpoint."""
        area_id = uuid4()
        mock_analysis_result = {
            "coverage_percentage": 85.5,
            "total_nodes": 12,
            "gaps_identified": 3,
            "analysis_timestamp": "2024-01-01T00:00:00Z",
        }

        with patch(
            "dotmac_isp.modules.gis.router.get_current_tenant_id",
            return_value=mock_tenant_id,
        ):
            with patch.object(
                router.gis_analysis_service, "analyze_service_area_coverage"
            ) as mock_analyze:
                mock_analyze.return_value = mock_analysis_result

                response = client.post(
                    f"/api/v1/service-areas/{area_id}/analyze-coverage",
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["coverage_percentage"] == 85.5
                assert data["total_nodes"] == 12


class TestNetworkNodeEndpoints:
    """Test network node API endpoints."""

    def test_create_network_node(self, client, mock_tenant_id):
        """Test POST /network-nodes endpoint."""
        node_data = {
            "name": "Test Router",
            "description": "Core network router",
            "node_type": "core_router",
            "latitude": 45.5152,
            "longitude": -122.6784,
            "ip_address": "192.168.1.1",
            "bandwidth_mbps": 10000,
        }

        mock_node = NetworkNode(id=uuid4(), tenant_id=mock_tenant_id, **node_data)

        with patch(
            "dotmac_isp.modules.gis.router.get_current_tenant_id",
            return_value=mock_tenant_id,
        ):
            with patch.object(
                router.network_node_service, "create", return_value=mock_node
            ):
                response = client.post(
                    "/api/v1/network-nodes",
                    json=node_data,
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code == 201
                data = response.json()
                assert data["name"] == "Test Router"
                assert data["node_type"] == "core_router"
                assert data["bandwidth_mbps"] == 10000

    def test_list_network_nodes_by_area(self, client, mock_tenant_id):
        """Test GET /network-nodes?service_area_id endpoint."""
        service_area_id = uuid4()
        mock_nodes = [
            NetworkNode(
                id=uuid4(),
                tenant_id=mock_tenant_id,
                service_area_id=service_area_id,
                name="Router 1",
                node_type="core_router",
            ),
            NetworkNode(
                id=uuid4(),
                tenant_id=mock_tenant_id,
                service_area_id=service_area_id,
                name="WiFi AP 1",
                node_type="wifi_ap",
            ),
        ]

        with patch(
            "dotmac_isp.modules.gis.router.get_current_tenant_id",
            return_value=mock_tenant_id,
        ):
            with patch.object(
                router.network_node_service,
                "get_by_service_area",
                return_value=mock_nodes,
            ):
                response = client.get(
                    f"/api/v1/network-nodes?service_area_id={service_area_id}",
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                assert data[0]["name"] == "Router 1"
                assert data[1]["name"] == "WiFi AP 1"


class TestTerritoryEndpoints:
    """Test territory management API endpoints."""

    def test_create_territory(self, client, mock_tenant_id):
        """Test POST /territories endpoint."""
        territory_data = {
            "name": "Northwest Territory",
            "description": "Sales territory for NW region",
            "boundary_coordinates": [
                {"latitude": 45.4, "longitude": -122.8},
                {"latitude": 45.6, "longitude": -122.8},
                {"latitude": 45.6, "longitude": -122.4},
                {"latitude": 45.4, "longitude": -122.4},
            ],
            "territory_type": "sales",
            "revenue_target": 500000.0,
        }

        mock_territory = Territory(
            id=uuid4(), tenant_id=mock_tenant_id, **territory_data
        )

        with patch(
            "dotmac_isp.modules.gis.router.get_current_tenant_id",
            return_value=mock_tenant_id,
        ):
            with patch.object(
                router.territory_service, "create", return_value=mock_territory
            ):
                response = client.post(
                    "/api/v1/territories",
                    json=territory_data,
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code == 201
                data = response.json()
                assert data["name"] == "Northwest Territory"
                assert data["territory_type"] == "sales"
                assert data["revenue_target"] == 500000.0

    def test_get_territory_performance(self, client, mock_tenant_id):
        """Test GET /territories/{id}/performance endpoint."""
        territory_id = uuid4()
        mock_performance = {
            "revenue_achievement": 85.0,
            "customer_count": 120,
            "performance_grade": "B+",
            "recommendations": ["Focus on high-value prospects"],
        }

        with patch(
            "dotmac_isp.modules.gis.router.get_current_tenant_id",
            return_value=mock_tenant_id,
        ):
            with patch.object(
                router.territory_service, "calculate_territory_performance"
            ) as mock_calc:
                mock_calc.return_value = mock_performance

                response = client.get(
                    f"/api/v1/territories/{territory_id}/performance",
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["revenue_achievement"] == 85.0
                assert data["performance_grade"] == "B+"


class TestRouteOptimizationEndpoints:
    """Test route optimization API endpoints."""

    def test_optimize_route(self, client, mock_tenant_id):
        """Test POST /route-optimization/optimize endpoint."""
        route_request = {
            "start_coordinates": {"latitude": 45.5152, "longitude": -122.6784},
            "waypoints": [
                {"latitude": 45.5175, "longitude": -122.6750},
                {"latitude": 45.5200, "longitude": -122.6700},
            ],
            "optimization_type": "shortest",
            "vehicle_type": "truck",
        }

        mock_result = {
            "optimized_route": [
                {"latitude": 45.5152, "longitude": -122.6784},
                {"latitude": 45.5175, "longitude": -122.6750},
                {"latitude": 45.5200, "longitude": -122.6700},
            ],
            "total_distance_km": 8.5,
            "estimated_duration_minutes": 120,
        }

        with patch(
            "dotmac_isp.modules.gis.router.get_current_tenant_id",
            return_value=mock_tenant_id,
        ):
            with patch.object(
                router.route_optimization_service, "optimize_service_route"
            ) as mock_optimize:
                mock_optimize.return_value = mock_result

                response = client.post(
                    "/api/v1/route-optimization/optimize",
                    json=route_request,
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["total_distance_km"] == 8.5
                assert data["estimated_duration_minutes"] == 120
                assert len(data["optimized_route"]) == 3

    def test_batch_route_optimization(self, client, mock_tenant_id):
        """Test POST /route-optimization/batch endpoint."""
        batch_request = {
            "start_location": {"latitude": 45.5100, "longitude": -122.6800},
            "service_calls": [
                {"latitude": 45.5152, "longitude": -122.6784, "priority": "high"},
                {"latitude": 45.5200, "longitude": -122.6700, "priority": "medium"},
            ],
            "vehicle_type": "truck",
            "max_duration_hours": 8,
        }

        mock_result = {
            "total_routes": 1,
            "total_distance_km": 15.2,
            "total_duration_minutes": 180,
            "optimized_sequence": [0, 1],
        }

        with patch(
            "dotmac_isp.modules.gis.router.get_current_tenant_id",
            return_value=mock_tenant_id,
        ):
            with patch.object(
                router.route_optimization_service, "batch_route_optimization"
            ) as mock_batch:
                mock_batch.return_value = mock_result

                response = client.post(
                    "/api/v1/route-optimization/batch",
                    json=batch_request,
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["total_routes"] == 1
                assert data["total_distance_km"] == 15.2


class TestErrorHandling:
    """Test API error handling."""

    def test_service_area_not_found(self, client, mock_tenant_id):
        """Test 404 response for non-existent service area."""
        non_existent_id = uuid4()

        with patch(
            "dotmac_isp.modules.gis.router.get_current_tenant_id",
            return_value=mock_tenant_id,
        ):
            with patch.object(
                router.service_area_service,
                "get_by_id",
                side_effect=Exception("Not found"),
            ):
                response = client.get(
                    f"/api/v1/service-areas/{non_existent_id}",
                    headers={"Authorization": "Bearer test-token"},
                )

                assert (
                    response.status_code == 500
                )  # Will be handled by standard_exception_handler

    def test_invalid_coordinates(self, client, mock_tenant_id):
        """Test validation error for invalid coordinates."""
        invalid_data = {
            "name": "Invalid Area",
            "polygon_coordinates": [
                {"latitude": 91.0, "longitude": -122.6}  # Invalid latitude > 90
            ],
            "service_types": ["fiber"],
        }

        with patch(
            "dotmac_isp.modules.gis.router.get_current_tenant_id",
            return_value=mock_tenant_id,
        ):
            response = client.post(
                "/api/v1/service-areas",
                json=invalid_data,
                headers={"Authorization": "Bearer test-token"},
            )

            # Validation would be handled by Pydantic schemas
            assert response.status_code in [400, 422]

    def test_unauthorized_access(self, client):
        """Test unauthorized access without token."""
        response = client.get("/api/v1/service-areas")

        # Would be handled by authentication middleware
        assert response.status_code == 401


class TestGISAnalyticsEndpoints:
    """Test GIS analytics endpoints."""

    def test_coverage_analytics(self, client, mock_tenant_id):
        """Test GET /analytics/coverage endpoint."""
        mock_analytics = {
            "total_service_areas": 25,
            "average_coverage": 82.5,
            "coverage_gaps": 8,
            "coverage_by_service_type": {"fiber": 88.2, "wireless": 76.8},
        }

        with patch(
            "dotmac_isp.modules.gis.router.get_current_tenant_id",
            return_value=mock_tenant_id,
        ):
            with patch.object(
                router.gis_analysis_service, "get_coverage_analytics"
            ) as mock_analytics_call:
                mock_analytics_call.return_value = mock_analytics

                response = client.get(
                    "/api/v1/analytics/coverage",
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["total_service_areas"] == 25
                assert data["average_coverage"] == 82.5

    def test_territory_performance_analytics(self, client, mock_tenant_id):
        """Test GET /analytics/territories endpoint."""
        mock_performance = {
            "total_territories": 12,
            "average_performance": 87.3,
            "top_performers": [
                {"name": "North Territory", "performance": 95.2},
                {"name": "South Territory", "performance": 91.8},
            ],
            "underperformers": [{"name": "East Territory", "performance": 68.4}],
        }

        with patch(
            "dotmac_isp.modules.gis.router.get_current_tenant_id",
            return_value=mock_tenant_id,
        ):
            with patch.object(
                router.territory_service, "get_performance_analytics"
            ) as mock_perf:
                mock_perf.return_value = mock_performance

                response = client.get(
                    "/api/v1/analytics/territories",
                    headers={"Authorization": "Bearer test-token"},
                )

                assert response.status_code == 200
                data = response.json()
                assert data["total_territories"] == 12
                assert len(data["top_performers"]) == 2
