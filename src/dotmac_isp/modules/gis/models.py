"""
GIS Models leveraging DotMac shared base classes.
Following DRY patterns with proper inheritance.
"""

import enum
from uuid import UUID

from dotmac_isp.shared.database.base import BaseModel
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship


class ServiceTypeEnum(str, enum.Enum):
    """Service types for coverage analysis."""

    FIBER = "fiber"
    WIRELESS = "wireless"
    CABLE = "cable"
    DSL = "dsl"
    FIXED_WIRELESS = "fixed_wireless"


class NetworkNodeTypeEnum(str, enum.Enum):
    """Network node types from existing network visualization module."""

    CORE_ROUTER = "core_router"
    DISTRIBUTION_ROUTER = "distribution_router"
    ACCESS_SWITCH = "access_switch"
    WIFI_AP = "wifi_ap"
    CELL_TOWER = "cell_tower"
    FIBER_SPLICE = "fiber_splice"
    POP = "pop"


class CoverageStatusEnum(str, enum.Enum):
    """Coverage status for analysis."""

    EXCELLENT = "excellent"
    GOOD = "good"
    POOR = "poor"
    NO_COVERAGE = "no_coverage"


class ServiceArea(BaseModel):
    """
    Service area model leveraging DotMac base classes.
    Inherits: ID, timestamps, tenant isolation, geo coordinates
    """

    __tablename__ = "gis_service_areas"

    # GIS-specific fields
    polygon_coordinates = Column(JSONB, nullable=False, comment="Polygon coordinates as GeoJSON")
    service_types = Column(JSONB, nullable=False, comment="Available service types")
    population = Column(Integer, default=0, comment="Population in service area")
    households = Column(Integer, default=0, comment="Number of households")
    businesses = Column(Integer, default=0, comment="Number of businesses")
    coverage_percentage = Column(Float, default=0.0, comment="Coverage percentage")

    # Analysis metadata
    last_analyzed_at = Column(DateTime, nullable=True, comment="Last coverage analysis")
    analysis_metadata = Column(JSONB, default={}, comment="Analysis results metadata")

    # Relationships
    coverage_gaps = relationship("CoverageGap", back_populates="service_area")
    network_nodes = relationship("NetworkNode", back_populates="service_area")


class NetworkNode(BaseModel):
    """Network infrastructure node with GIS coordinates."""

    __tablename__ = "gis_network_nodes"

    node_type = Column(SQLEnum(NetworkNodeTypeEnum), nullable=False)
    ip_address = Column(String(45), nullable=True, comment="IPv4/IPv6 address")
    mac_address = Column(String(17), nullable=True, comment="MAC address")

    # Network properties
    bandwidth_mbps = Column(Integer, nullable=True, comment="Bandwidth in Mbps")
    coverage_radius_km = Column(Float, nullable=True, comment="Coverage radius for wireless")

    # Operational status
    operational_status = Column(String(20), default="active")
    last_seen_at = Column(DateTime, nullable=True)

    # Equipment details
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    firmware_version = Column(String(50), nullable=True)

    # References
    service_area_id = Column(UUID, ForeignKey("gis_service_areas.id"), nullable=True)

    # Relationships
    service_area = relationship("ServiceArea", back_populates="network_nodes")


class CoverageGap(BaseModel):
    """Coverage gap identified through analysis."""

    __tablename__ = "gis_coverage_gaps"

    service_area_id = Column(UUID, ForeignKey("gis_service_areas.id"), nullable=False)

    # Gap details
    gap_type = Column(String(50), nullable=False, comment="Type of coverage gap")
    severity = Column(String(20), nullable=False, comment="Gap severity level")
    polygon_coordinates = Column(JSONB, nullable=False, comment="Gap area coordinates")

    # Impact analysis
    affected_customers = Column(Integer, default=0, comment="Estimated affected customers")
    potential_revenue = Column(Float, default=0.0, comment="Potential annual revenue")
    buildout_cost = Column(Float, default=0.0, comment="Estimated buildout cost")
    priority_score = Column(Float, default=0.0, comment="Priority score for addressing")

    # Recommendations
    recommendations = Column(JSONB, default=[], comment="Recommended actions")

    # Relationships
    service_area = relationship("ServiceArea", back_populates="coverage_gaps")


class CoverageRecommendation(BaseModel):
    """Coverage improvement recommendations."""

    __tablename__ = "gis_coverage_recommendations"

    service_area_id = Column(UUID, ForeignKey("gis_service_areas.id"), nullable=True)

    # Recommendation details
    recommendation_type = Column(String(50), nullable=False, comment="Type of recommendation")
    priority = Column(String(20), nullable=False, comment="Priority level")
    description = Column(Text, nullable=False, comment="Detailed description")

    # Cost-benefit analysis
    estimated_cost = Column(Float, default=0.0, comment="Implementation cost")
    estimated_revenue = Column(Float, default=0.0, comment="Expected revenue impact")
    timeframe = Column(String(50), nullable=True, comment="Implementation timeframe")

    # Implementation details
    requirements = Column(JSONB, default=[], comment="Implementation requirements")
    affected_areas = Column(JSONB, default=[], comment="Areas affected by recommendation")

    # Status tracking
    status = Column(String(20), default="pending", comment="Implementation status")
    approved_at = Column(DateTime, nullable=True)
    implemented_at = Column(DateTime, nullable=True)


class Territory(BaseModel):
    """Sales/service territory management."""

    __tablename__ = "gis_territories"

    # Territory boundaries
    boundary_coordinates = Column(JSONB, nullable=False, comment="Territory boundary as GeoJSON")

    # Territory metadata
    territory_type = Column(String(50), default="sales", comment="Territory type")
    color = Column(String(7), nullable=True, comment="Display color (hex)")

    # Assignment
    assigned_user_id = Column(UUID, nullable=True, comment="Assigned user/technician")
    assigned_team = Column(String(100), nullable=True, comment="Assigned team")

    # Operational data
    customer_count = Column(Integer, default=0)
    revenue_target = Column(Float, default=0.0)
    actual_revenue = Column(Float, default=0.0)

    # Analysis data
    competitor_analysis = Column(JSONB, default={}, comment="Competitor data")
    demographics = Column(JSONB, default={}, comment="Demographic information")


class RouteOptimization(BaseModel):
    """Route optimization results for field operations."""

    __tablename__ = "gis_route_optimizations"

    # Route details
    start_coordinates = Column(JSONB, nullable=False, comment="Starting point")
    end_coordinates = Column(JSONB, nullable=True, comment="Ending point (optional)")
    waypoints = Column(JSONB, default=[], comment="Intermediate waypoints")

    # Optimization parameters
    optimization_type = Column(String(50), default="shortest", comment="Optimization goal")
    vehicle_type = Column(String(50), default="truck", comment="Vehicle type")
    constraints = Column(JSONB, default={}, comment="Route constraints")

    # Results
    optimized_route = Column(JSONB, nullable=True, comment="Optimized route coordinates")
    total_distance_km = Column(Float, nullable=True, comment="Total route distance")
    estimated_duration_minutes = Column(Integer, nullable=True, comment="Estimated travel time")

    # Metadata
    calculated_at = Column(DateTime, nullable=True)
    calculation_parameters = Column(JSONB, default={}, comment="Calculation settings used")


# Export all models for use by services and routers
__all__ = [
    "ServiceArea",
    "NetworkNode",
    "CoverageGap",
    "CoverageRecommendation",
    "Territory",
    "RouteOptimization",
    "ServiceTypeEnum",
    "NetworkNodeTypeEnum",
    "CoverageStatusEnum",
]
