"""
Integration tests for GIS services.
Tests service layer functionality and business logic.
"""

from datetime import datetime
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from dotmac_isp.modules.gis.models import (
    CoverageGap,
    NetworkNode,
    NetworkNodeTypeEnum,
    RouteOptimization,
    ServiceArea,
    Territory,
)
from dotmac_isp.modules.gis.services import (
    GISAnalysisService,
    RouteOptimizationService,
    TerritoryManagementService,
)


class TestGISAnalysisService:
    """Test GIS analysis service functionality."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock()

    @pytest.fixture
    def analysis_service(self, mock_db_session):
        """GIS analysis service instance."""
        return GISAnalysisService(db=mock_db_session)

    @pytest.mark.asyncio
    async def test_analyze_service_area_coverage(self, analysis_service):
        """Test service area coverage analysis."""
        tenant_id = uuid4()
        service_area_id = uuid4()

        # Mock service area
        mock_service_area = ServiceArea(
            id=service_area_id,
            tenant_id=tenant_id,
            name="Test Area",
            polygon_coordinates=[
                {"latitude": 45.5, "longitude": -122.6},
                {"latitude": 45.6, "longitude": -122.6},
                {"latitude": 45.6, "longitude": -122.5},
                {"latitude": 45.5, "longitude": -122.5},
            ],
            service_types=["fiber", "wireless"],
            population=5000,
            households=2000,
        )

        # Mock network nodes
        mock_nodes = [
            NetworkNode(
                tenant_id=tenant_id,
                service_area_id=service_area_id,
                name="Router 1",
                node_type=NetworkNodeTypeEnum.CORE_ROUTER,
                latitude=45.52,
                longitude=-122.58,
                coverage_radius_km=2.0,
            ),
            NetworkNode(
                tenant_id=tenant_id,
                service_area_id=service_area_id,
                name="WiFi AP 1",
                node_type=NetworkNodeTypeEnum.WIFI_AP,
                latitude=45.55,
                longitude=-122.57,
                coverage_radius_km=0.5,
            ),
        ]

        with patch.object(
            analysis_service.repository, "get_by_id", return_value=mock_service_area
        ):
            with patch.object(
                analysis_service, "_get_network_nodes", return_value=mock_nodes
            ):
                with patch.object(
                    analysis_service,
                    "_calculate_coverage_percentage",
                    return_value=85.5,
                ):

                    result = await analysis_service.analyze_service_area_coverage(
                        tenant_id=tenant_id, service_area_id=service_area_id
                    )

                    assert result is not None
                    assert result["coverage_percentage"] == 85.5
                    assert result["total_nodes"] == 2
                    assert "analysis_timestamp" in result

    @pytest.mark.asyncio
    async def test_identify_coverage_gaps(self, analysis_service):
        """Test coverage gap identification."""
        tenant_id = uuid4()
        service_area_id = uuid4()

        # Mock service area with poor coverage
        mock_service_area = ServiceArea(
            id=service_area_id,
            tenant_id=tenant_id,
            coverage_percentage=65.0,
            population=3000,
        )

        with patch.object(
            analysis_service.repository, "get_by_id", return_value=mock_service_area
        ):
            with patch.object(
                analysis_service, "_analyze_coverage_gaps"
            ) as mock_analyze:
                mock_analyze.return_value = [
                    {
                        "gap_type": "no_coverage",
                        "severity": "high",
                        "affected_customers": 200,
                        "potential_revenue": 180000.0,
                        "polygon_coordinates": [
                            {"latitude": 45.51, "longitude": -122.67},
                            {"latitude": 45.52, "longitude": -122.67},
                            {"latitude": 45.52, "longitude": -122.66},
                        ],
                    }
                ]

                gaps = await analysis_service.identify_coverage_gaps(
                    tenant_id=tenant_id, service_area_id=service_area_id
                )

                assert len(gaps) == 1
                assert gaps[0]["gap_type"] == "no_coverage"
                assert gaps[0]["affected_customers"] == 200

    @pytest.mark.asyncio
    async def test_generate_coverage_recommendations(self, analysis_service):
        """Test coverage recommendation generation."""
        tenant_id = uuid4()
        service_area_id = uuid4()

        # Mock coverage gaps
        mock_gaps = [
            CoverageGap(
                tenant_id=tenant_id,
                service_area_id=service_area_id,
                gap_type="no_coverage",
                severity="high",
                affected_customers=150,
                potential_revenue=135000.0,
                buildout_cost=250000.0,
            )
        ]

        with patch.object(
            analysis_service, "_get_coverage_gaps", return_value=mock_gaps
        ):
            recommendations = await analysis_service.generate_coverage_recommendations(
                tenant_id=tenant_id, service_area_id=service_area_id
            )

            assert len(recommendations) > 0
            assert recommendations[0]["priority"] in ["high", "medium", "low"]
            assert "estimated_cost" in recommendations[0]
            assert "estimated_revenue" in recommendations[0]


class TestTerritoryManagementService:
    """Test territory management service."""

    @pytest.fixture
    def mock_db_session(self):
        return Mock()

    @pytest.fixture
    def territory_service(self, mock_db_session):
        return TerritoryManagementService(db=mock_db_session)

    @pytest.mark.asyncio
    async def test_create_territory(self, territory_service):
        """Test territory creation."""
        tenant_id = uuid4()
        assigned_user_id = uuid4()

        territory_data = {
            "name": "Northwest Territory",
            "description": "Sales territory for NW Portland",
            "boundary_coordinates": [
                {"latitude": 45.4, "longitude": -122.8},
                {"latitude": 45.6, "longitude": -122.8},
                {"latitude": 45.6, "longitude": -122.4},
                {"latitude": 45.4, "longitude": -122.4},
            ],
            "territory_type": "sales",
            "assigned_user_id": assigned_user_id,
            "revenue_target": 500000.0,
        }

        mock_territory = Territory(id=uuid4(), tenant_id=tenant_id, **territory_data)

        with patch.object(
            territory_service.repository, "create", return_value=mock_territory
        ):
            result = await territory_service.create_territory(
                tenant_id=tenant_id, territory_data=territory_data
            )

            assert result.name == "Northwest Territory"
            assert result.territory_type == "sales"
            assert result.revenue_target == 500000.0

    @pytest.mark.asyncio
    async def test_calculate_territory_performance(self, territory_service):
        """Test territory performance calculation."""
        tenant_id = uuid4()
        territory_id = uuid4()

        mock_territory = Territory(
            id=territory_id,
            tenant_id=tenant_id,
            revenue_target=100000.0,
            actual_revenue=85000.0,
            customer_count=120,
        )

        with patch.object(
            territory_service.repository, "get_by_id", return_value=mock_territory
        ):
            performance = await territory_service.calculate_territory_performance(
                tenant_id=tenant_id, territory_id=territory_id
            )

            assert performance["revenue_achievement"] == 85.0  # 85k/100k * 100
            assert performance["customer_count"] == 120
            assert "performance_grade" in performance

    @pytest.mark.asyncio
    async def test_optimize_territory_boundaries(self, territory_service):
        """Test territory boundary optimization."""
        tenant_id = uuid4()

        # Mock existing territories
        mock_territories = [
            Territory(
                id=uuid4(),
                tenant_id=tenant_id,
                name="Territory A",
                customer_count=100,
                actual_revenue=50000.0,
            ),
            Territory(
                id=uuid4(),
                tenant_id=tenant_id,
                name="Territory B",
                customer_count=200,
                actual_revenue=120000.0,
            ),
        ]

        with patch.object(
            territory_service.repository, "get_by_tenant", return_value=mock_territories
        ):
            with patch.object(
                territory_service, "_calculate_optimal_boundaries"
            ) as mock_calc:
                mock_calc.return_value = {
                    "optimized_territories": 2,
                    "performance_improvement": 15.2,
                    "recommendations": ["Rebalance customer distribution"],
                }

                result = await territory_service.optimize_territory_boundaries(
                    tenant_id
                )

                assert result["optimized_territories"] == 2
                assert result["performance_improvement"] > 0


class TestRouteOptimizationService:
    """Test route optimization service."""

    @pytest.fixture
    def mock_db_session(self):
        return Mock()

    @pytest.fixture
    def route_service(self, mock_db_session):
        return RouteOptimizationService(db=mock_db_session)

    @pytest.mark.asyncio
    async def test_optimize_service_route(self, route_service):
        """Test service route optimization."""
        tenant_id = uuid4()

        route_request = {
            "start_coordinates": {"latitude": 45.5152, "longitude": -122.6784},
            "waypoints": [
                {"latitude": 45.5175, "longitude": -122.6750},
                {"latitude": 45.5200, "longitude": -122.6700},
            ],
            "optimization_type": "shortest",
            "vehicle_type": "truck",
            "constraints": {"max_duration_hours": 8},
        }

        with patch.object(route_service, "_calculate_optimal_route") as mock_calc:
            mock_calc.return_value = {
                "optimized_route": [
                    {"latitude": 45.5152, "longitude": -122.6784},
                    {"latitude": 45.5175, "longitude": -122.6750},
                    {"latitude": 45.5200, "longitude": -122.6700},
                ],
                "total_distance_km": 8.5,
                "estimated_duration_minutes": 120,
            }

            result = await route_service.optimize_service_route(
                tenant_id=tenant_id, route_request=route_request
            )

            assert result["total_distance_km"] == 8.5
            assert result["estimated_duration_minutes"] == 120
            assert len(result["optimized_route"]) == 3

    @pytest.mark.asyncio
    async def test_batch_route_optimization(self, route_service):
        """Test batch route optimization."""
        tenant_id = uuid4()

        # Multiple service calls
        service_calls = [
            {"latitude": 45.5152, "longitude": -122.6784, "priority": "high"},
            {"latitude": 45.5200, "longitude": -122.6700, "priority": "medium"},
            {"latitude": 45.5250, "longitude": -122.6650, "priority": "high"},
        ]

        with patch.object(route_service, "_optimize_multiple_destinations") as mock_opt:
            mock_opt.return_value = {
                "total_routes": 1,
                "total_distance_km": 15.2,
                "total_duration_minutes": 180,
                "optimized_sequence": [0, 2, 1],  # High priority first
            }

            result = await route_service.batch_route_optimization(
                tenant_id=tenant_id,
                service_calls=service_calls,
                start_location={"latitude": 45.5100, "longitude": -122.6800},
            )

            assert result["total_routes"] == 1
            assert result["optimized_sequence"] == [0, 2, 1]
            assert result["total_distance_km"] > 0


class TestGISServiceIntegration:
    """Test integration between GIS services."""

    @pytest.mark.asyncio
    async def test_coverage_analysis_to_territory_optimization(self):
        """Test workflow from coverage analysis to territory optimization."""
        tenant_id = uuid4()

        # Mock services
        mock_db = Mock()
        analysis_service = GISAnalysisService(db=mock_db)
        territory_service = TerritoryManagementService(db=mock_db)

        # Mock coverage analysis results
        coverage_results = {
            "low_coverage_areas": [
                {"area_id": uuid4(), "coverage_percentage": 45.0},
                {"area_id": uuid4(), "coverage_percentage": 62.0},
            ]
        }

        with patch.object(
            analysis_service, "analyze_tenant_coverage", return_value=coverage_results
        ):
            with patch.object(
                territory_service, "optimize_territory_boundaries"
            ) as mock_optimize:
                mock_optimize.return_value = {
                    "optimized_territories": 3,
                    "performance_improvement": 22.5,
                }

                # Simulate workflow
                coverage_data = await analysis_service.analyze_tenant_coverage(
                    tenant_id
                )
                optimization_result = (
                    await territory_service.optimize_territory_boundaries(tenant_id)
                )

                assert len(coverage_data["low_coverage_areas"]) == 2
                assert optimization_result["performance_improvement"] > 0
