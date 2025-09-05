"""
GIS Repository layer following DotMac DRY patterns.

Leverages shared repository patterns and database utilities for consistent
data access patterns across the GIS module.
"""

from typing import Any, Optional
from uuid import UUID

from dotmac_shared.db.operations import DatabaseOperations
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    CoverageGap,
    CoverageRecommendation,
    NetworkNode,
    NetworkNodeTypeEnum,
    RouteOptimization,
    ServiceArea,
    Territory,
)


class ServiceAreaRepository:
    """Service area repository with GIS-specific queries."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.db_ops = DatabaseOperations(db)
        self.model = ServiceArea

    # Standard CRUD operations using DatabaseOperations
    async def create(self, **kwargs) -> ServiceArea:
        """Create a new service area."""
        kwargs["tenant_id"] = self.tenant_id
        return await self.db_ops.create(self.model, **kwargs)

    async def get_by_id(self, id: UUID) -> Optional[ServiceArea]:
        """Get service area by ID."""
        return await self.db_ops.get_by_id(self.model, id)

    async def update(self, id: UUID, **kwargs) -> Optional[ServiceArea]:
        """Update service area."""
        return await self.db_ops.update(self.model, id, **kwargs)

    async def delete(self, id: UUID) -> bool:
        """Delete service area."""
        return await self.db_ops.delete(self.model, id)

    async def get_all(self, limit: Optional[int] = None, offset: Optional[int] = None) -> list[ServiceArea]:
        """Get all service areas for tenant."""
        areas = await self.db_ops.find_by(self.model, limit=limit, tenant_id=self.tenant_id, is_active=True)
        return areas

    async def find_by_service_types(self, service_types: list[str], active_only: bool = True) -> list[ServiceArea]:
        """Find service areas that support specific service types."""
        query = select(ServiceArea).where(ServiceArea.tenant_id == self.tenant_id)

        if active_only:
            query = query.where(ServiceArea.is_active is True)

        # Check if any of the requested service types are in the area's service_types
        if service_types:
            # Using JSONB containment for PostgreSQL or JSON_CONTAINS for MySQL
            conditions = []
            for service_type in service_types:
                conditions.append(func.json_extract(ServiceArea.service_types, "$[*]").like(f"%{service_type}%"))
            query = query.where(or_(*conditions))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_areas_needing_analysis(self, days_since_analysis: int = 90) -> list[ServiceArea]:
        """Find service areas that need coverage analysis."""
        from datetime import datetime, timedelta

        cutoff_date = datetime.utcnow() - timedelta(days=days_since_analysis)

        query = select(ServiceArea).where(
            ServiceArea.tenant_id == self.tenant_id,
            ServiceArea.is_active is True,
            or_(ServiceArea.last_analyzed_at.is_(None), ServiceArea.last_analyzed_at < cutoff_date),
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_areas_with_low_coverage(self, coverage_threshold: float = 80.0) -> list[ServiceArea]:
        """Find service areas with coverage below threshold."""
        query = select(ServiceArea).where(
            ServiceArea.tenant_id == self.tenant_id,
            ServiceArea.is_active is True,
            ServiceArea.coverage_percentage < coverage_threshold,
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_with_network_nodes(self, area_id: UUID) -> Optional[ServiceArea]:
        """Get service area with its network nodes loaded."""
        query = (
            select(ServiceArea)
            .where(ServiceArea.id == area_id, ServiceArea.tenant_id == self.tenant_id)
            .options(selectinload(ServiceArea.network_nodes))
        )

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_coverage_statistics(self) -> dict[str, Any]:
        """Get coverage statistics across all service areas."""
        query = select(
            func.count(ServiceArea.id).label("total_areas"),
            func.avg(ServiceArea.coverage_percentage).label("avg_coverage"),
            func.min(ServiceArea.coverage_percentage).label("min_coverage"),
            func.max(ServiceArea.coverage_percentage).label("max_coverage"),
            func.sum(ServiceArea.population).label("total_population"),
            func.sum(ServiceArea.households).label("total_households"),
            func.sum(ServiceArea.businesses).label("total_businesses"),
        ).where(ServiceArea.tenant_id == self.tenant_id, ServiceArea.is_active is True)

        result = await self.db.execute(query)
        row = result.first()

        return {
            "total_areas": row.total_areas or 0,
            "avg_coverage": float(row.avg_coverage or 0),
            "min_coverage": float(row.min_coverage or 0),
            "max_coverage": float(row.max_coverage or 0),
            "total_population": row.total_population or 0,
            "total_households": row.total_households or 0,
            "total_businesses": row.total_businesses or 0,
        }


class NetworkNodeRepository:
    """Network node repository with topology-aware queries."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.db_ops = DatabaseOperations(db)
        self.model = NetworkNode

    # Standard CRUD operations
    async def create(self, **kwargs) -> NetworkNode:
        """Create a new network node."""
        kwargs["tenant_id"] = self.tenant_id
        return await self.db_ops.create(self.model, **kwargs)

    async def get_by_id(self, id: UUID) -> Optional[NetworkNode]:
        """Get network node by ID."""
        return await self.db_ops.get_by_id(self.model, id)

    async def update(self, id: UUID, **kwargs) -> Optional[NetworkNode]:
        """Update network node."""
        return await self.db_ops.update(self.model, id, **kwargs)

    async def delete(self, id: UUID) -> bool:
        """Delete network node."""
        return await self.db_ops.delete(self.model, id)

    async def get_all(self, limit: Optional[int] = None) -> list[NetworkNode]:
        """Get all network nodes for tenant."""
        return await self.db_ops.find_by(self.model, limit=limit, tenant_id=self.tenant_id, is_active=True)

    async def find_by_node_type(self, node_type: NetworkNodeTypeEnum, active_only: bool = True) -> list[NetworkNode]:
        """Find network nodes by type."""
        query = select(NetworkNode).where(NetworkNode.tenant_id == self.tenant_id, NetworkNode.node_type == node_type)

        if active_only:
            query = query.where(NetworkNode.is_active is True, NetworkNode.operational_status == "active")

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_nodes_in_area(self, service_area_id: UUID, active_only: bool = True) -> list[NetworkNode]:
        """Find network nodes in a specific service area."""
        query = select(NetworkNode).where(
            NetworkNode.tenant_id == self.tenant_id, NetworkNode.service_area_id == service_area_id
        )

        if active_only:
            query = query.where(NetworkNode.is_active is True, NetworkNode.operational_status == "active")

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_nodes_with_capacity(
        self, min_bandwidth_mbps: int, node_types: Optional[list[NetworkNodeTypeEnum]] = None
    ) -> list[NetworkNode]:
        """Find nodes with minimum bandwidth capacity."""
        query = select(NetworkNode).where(
            NetworkNode.tenant_id == self.tenant_id,
            NetworkNode.is_active is True,
            NetworkNode.bandwidth_mbps >= min_bandwidth_mbps,
        )

        if node_types:
            query = query.where(NetworkNode.node_type.in_(node_types))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_offline_nodes(self, hours_offline: int = 24) -> list[NetworkNode]:
        """Find nodes that haven't been seen recently."""
        from datetime import datetime, timedelta, timezone

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_offline)

        query = select(NetworkNode).where(
            NetworkNode.tenant_id == self.tenant_id,
            NetworkNode.is_active is True,
            or_(NetworkNode.last_seen_at.is_(None), NetworkNode.last_seen_at < cutoff_time),
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_network_topology_summary(self) -> dict[str, Any]:
        """Get network topology summary statistics."""
        query = (
            select(
                NetworkNode.node_type,
                func.count(NetworkNode.id).label("count"),
                func.avg(NetworkNode.bandwidth_mbps).label("avg_bandwidth"),
                func.count(func.case((NetworkNode.operational_status == "active", 1), else_=None)).label(
                    "active_count"
                ),
            )
            .where(NetworkNode.tenant_id == self.tenant_id, NetworkNode.is_active is True)
            .group_by(NetworkNode.node_type)
        )

        result = await self.db.execute(query)
        rows = result.all()

        topology_summary = {}
        for row in rows:
            topology_summary[row.node_type.value] = {
                "total_count": row.count,
                "active_count": row.active_count,
                "avg_bandwidth_mbps": float(row.avg_bandwidth or 0),
            }

        return topology_summary


class CoverageGapRepository:
    """Coverage gap repository for analysis tracking."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.db_ops = DatabaseOperations(db)
        self.model = CoverageGap

    # Standard CRUD operations
    async def create(self, **kwargs) -> CoverageGap:
        kwargs["tenant_id"] = self.tenant_id
        return await self.db_ops.create(self.model, **kwargs)

    async def get_by_id(self, id: UUID) -> Optional[CoverageGap]:
        return await self.db_ops.get_by_id(self.model, id)

    async def update(self, id: UUID, **kwargs) -> Optional[CoverageGap]:
        return await self.db_ops.update(self.model, id, **kwargs)

    async def delete(self, id: UUID) -> bool:
        return await self.db_ops.delete(self.model, id)

    async def find_by_service_area(self, service_area_id: UUID, active_only: bool = True) -> list[CoverageGap]:
        """Find coverage gaps for a service area."""
        query = select(CoverageGap).where(
            CoverageGap.tenant_id == self.tenant_id, CoverageGap.service_area_id == service_area_id
        )

        if active_only:
            query = query.where(CoverageGap.is_active is True)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_high_priority_gaps(
        self, min_priority_score: float = 70.0, limit: Optional[int] = None
    ) -> list[CoverageGap]:
        """Find high priority coverage gaps."""
        query = (
            select(CoverageGap)
            .where(
                CoverageGap.tenant_id == self.tenant_id,
                CoverageGap.is_active is True,
                CoverageGap.priority_score >= min_priority_score,
            )
            .order_by(CoverageGap.priority_score.desc())
        )

        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_by_severity(self, severity: str, active_only: bool = True) -> list[CoverageGap]:
        """Find coverage gaps by severity level."""
        query = select(CoverageGap).where(CoverageGap.tenant_id == self.tenant_id, CoverageGap.severity == severity)

        if active_only:
            query = query.where(CoverageGap.is_active is True)

        result = await self.db.execute(query)
        return list(result.scalars().all())


class TerritoryRepository:
    """Territory repository with geographic queries."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.db_ops = DatabaseOperations(db)
        self.model = Territory

    # Standard CRUD operations
    async def create(self, **kwargs) -> Territory:
        kwargs["tenant_id"] = self.tenant_id
        return await self.db_ops.create(self.model, **kwargs)

    async def get_by_id(self, id: UUID) -> Optional[Territory]:
        return await self.db_ops.get_by_id(self.model, id)

    async def update(self, id: UUID, **kwargs) -> Optional[Territory]:
        return await self.db_ops.update(self.model, id, **kwargs)

    async def delete(self, id: UUID) -> bool:
        return await self.db_ops.delete(self.model, id)

    async def find_by_territory_type(self, territory_type: str, active_only: bool = True) -> list[Territory]:
        """Find territories by type."""
        query = select(Territory).where(
            Territory.tenant_id == self.tenant_id, Territory.territory_type == territory_type
        )

        if active_only:
            query = query.where(Territory.is_active is True)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_by_assigned_user(self, user_id: UUID, active_only: bool = True) -> list[Territory]:
        """Find territories assigned to a user."""
        query = select(Territory).where(Territory.tenant_id == self.tenant_id, Territory.assigned_user_id == user_id)

        if active_only:
            query = query.where(Territory.is_active is True)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_underperforming_territories(self, performance_threshold: float = 80.0) -> list[Territory]:
        """Find territories with revenue performance below threshold."""
        query = select(Territory).where(
            Territory.tenant_id == self.tenant_id,
            Territory.is_active is True,
            Territory.revenue_target > 0,
            (Territory.actual_revenue / Territory.revenue_target * 100) < performance_threshold,
        )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_territory_performance_summary(self) -> dict[str, Any]:
        """Get territory performance summary statistics."""
        query = select(
            func.count(Territory.id).label("total_territories"),
            func.sum(Territory.revenue_target).label("total_revenue_target"),
            func.sum(Territory.actual_revenue).label("total_actual_revenue"),
            func.sum(Territory.customer_count).label("total_customers"),
            func.avg(
                func.case(
                    (Territory.revenue_target > 0, Territory.actual_revenue / Territory.revenue_target * 100), else_=0
                )
            ).label("avg_performance"),
        ).where(Territory.tenant_id == self.tenant_id, Territory.is_active is True)

        result = await self.db.execute(query)
        row = result.first()

        return {
            "total_territories": row.total_territories or 0,
            "total_revenue_target": float(row.total_revenue_target or 0),
            "total_actual_revenue": float(row.total_actual_revenue or 0),
            "total_customers": row.total_customers or 0,
            "avg_performance_percent": float(row.avg_performance or 0),
            "overall_performance_percent": (
                (row.total_actual_revenue / row.total_revenue_target * 100)
                if row.total_revenue_target and row.total_revenue_target > 0
                else 0
            ),
        }


class RouteOptimizationRepository:
    """Route optimization repository for field operations."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.db_ops = DatabaseOperations(db)
        self.model = RouteOptimization

    # Standard CRUD operations
    async def create(self, **kwargs) -> RouteOptimization:
        kwargs["tenant_id"] = self.tenant_id
        return await self.db_ops.create(self.model, **kwargs)

    async def get_by_id(self, id: UUID) -> Optional[RouteOptimization]:
        return await self.db_ops.get_by_id(self.model, id)

    async def update(self, id: UUID, **kwargs) -> Optional[RouteOptimization]:
        return await self.db_ops.update(self.model, id, **kwargs)

    async def delete(self, id: UUID) -> bool:
        return await self.db_ops.delete(self.model, id)

    async def find_recent_optimizations(self, days: int = 30, limit: Optional[int] = None) -> list[RouteOptimization]:
        """Find recent route optimizations."""
        from datetime import datetime, timedelta, timezone

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(RouteOptimization)
            .where(RouteOptimization.tenant_id == self.tenant_id, RouteOptimization.calculated_at >= cutoff_date)
            .order_by(RouteOptimization.calculated_at.desc())
        )

        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_by_optimization_type(
        self, optimization_type: str, active_only: bool = True
    ) -> list[RouteOptimization]:
        """Find routes by optimization type."""
        query = select(RouteOptimization).where(
            RouteOptimization.tenant_id == self.tenant_id, RouteOptimization.optimization_type == optimization_type
        )

        if active_only:
            query = query.where(RouteOptimization.is_active is True)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_optimization_statistics(self) -> dict[str, Any]:
        """Get route optimization statistics."""
        query = select(
            func.count(RouteOptimization.id).label("total_routes"),
            func.avg(RouteOptimization.total_distance_km).label("avg_distance"),
            func.avg(RouteOptimization.estimated_duration_minutes).label("avg_duration"),
            func.count(func.distinct(RouteOptimization.optimization_type)).label("optimization_types"),
        ).where(RouteOptimization.tenant_id == self.tenant_id, RouteOptimization.is_active is True)

        result = await self.db.execute(query)
        row = result.first()

        return {
            "total_routes": row.total_routes or 0,
            "avg_distance_km": float(row.avg_distance or 0),
            "avg_duration_minutes": float(row.avg_duration or 0),
            "optimization_types_count": row.optimization_types or 0,
        }


class CoverageRecommendationRepository:
    """Coverage recommendation repository for improvement suggestions."""

    def __init__(self, db: AsyncSession, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.db_ops = DatabaseOperations(db)
        self.model = CoverageRecommendation

    # Standard CRUD operations
    async def create(self, **kwargs) -> CoverageRecommendation:
        kwargs["tenant_id"] = self.tenant_id
        return await self.db_ops.create(self.model, **kwargs)

    async def get_by_id(self, id: UUID) -> Optional[CoverageRecommendation]:
        return await self.db_ops.get_by_id(self.model, id)

    async def update(self, id: UUID, **kwargs) -> Optional[CoverageRecommendation]:
        return await self.db_ops.update(self.model, id, **kwargs)

    async def delete(self, id: UUID) -> bool:
        return await self.db_ops.delete(self.model, id)

    async def find_by_priority(self, priority: str, active_only: bool = True) -> list[CoverageRecommendation]:
        """Find recommendations by priority level."""
        query = select(CoverageRecommendation).where(
            CoverageRecommendation.tenant_id == self.tenant_id, CoverageRecommendation.priority == priority
        )

        if active_only:
            query = query.where(CoverageRecommendation.is_active is True)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_by_status(self, status: str, active_only: bool = True) -> list[CoverageRecommendation]:
        """Find recommendations by implementation status."""
        query = select(CoverageRecommendation).where(
            CoverageRecommendation.tenant_id == self.tenant_id, CoverageRecommendation.status == status
        )

        if active_only:
            query = query.where(CoverageRecommendation.is_active is True)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def find_pending_recommendations(self, limit: Optional[int] = None) -> list[CoverageRecommendation]:
        """Find pending recommendations ordered by priority."""
        # Priority order: critical, high, medium, low
        priority_order = func.case(
            (CoverageRecommendation.priority == "critical", 1),
            (CoverageRecommendation.priority == "high", 2),
            (CoverageRecommendation.priority == "medium", 3),
            (CoverageRecommendation.priority == "low", 4),
            else_=5,
        )

        query = (
            select(CoverageRecommendation)
            .where(
                CoverageRecommendation.tenant_id == self.tenant_id,
                CoverageRecommendation.is_active is True,
                CoverageRecommendation.status == "pending",
            )
            .order_by(priority_order, CoverageRecommendation.created_at)
        )

        if limit:
            query = query.limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())


# Export all repositories
__all__ = [
    "ServiceAreaRepository",
    "NetworkNodeRepository",
    "CoverageGapRepository",
    "TerritoryRepository",
    "RouteOptimizationRepository",
    "CoverageRecommendationRepository",
]
