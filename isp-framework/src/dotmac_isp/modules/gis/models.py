"""GIS (Geographic Information System) database models."""

from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from enum import Enum
import json

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Enum as SQLEnum,
    Numeric,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

# PostGIS extensions for PostgreSQL
try:
    from geoalchemy2 import Geometry, Geography
    from geoalchemy2.functions import ST_AsGeoJSON, ST_Distance, ST_DWithin

    POSTGIS_AVAILABLE = True
except ImportError:
    # Fallback for environments without PostGIS
    POSTGIS_AVAILABLE = False
    Geometry = Text
    Geography = Text

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.database.base import StatusMixin, AuditMixin
from dotmac_isp.shared.models import AddressMixin


class LocationType(str, Enum):
    """GIS location types."""

    DATACENTER = "datacenter"
    POP = "pop"  # Point of Presence
    CUSTOMER_PREMISE = "customer_premise"
    FIBER_HUB = "fiber_hub"
    CELL_TOWER = "cell_tower"
    FIELD_OFFICE = "field_office"
    WAREHOUSE = "warehouse"
    JUNCTION_BOX = "junction_box"
    SPLICE_POINT = "splice_point"
    MANHOLE = "manhole"
    POLE = "pole"
    CABINET = "cabinet"


class DeviceLocationType(str, Enum):
    """Device location types within GIS."""

    INDOOR = "indoor"
    OUTDOOR = "outdoor"
    UNDERGROUND = "underground"
    AERIAL = "aerial"
    RACK_MOUNTED = "rack_mounted"
    POLE_MOUNTED = "pole_mounted"
    WALL_MOUNTED = "wall_mounted"


class FiberType(str, Enum):
    """Fiber optic cable types."""

    SINGLE_MODE = "single_mode"
    MULTI_MODE = "multi_mode"
    ARMORED = "armored"
    AERIAL = "aerial"
    UNDERGROUND = "underground"
    UNDERWATER = "underwater"


class CoverageType(str, Enum):
    """Service coverage types."""

    FIBER = "fiber"
    WIRELESS = "wireless"
    FIXED_WIRELESS = "fixed_wireless"
    SATELLITE = "satellite"
    DSL = "dsl"
    CABLE = "cable"


class OperationType(str, Enum):
    """Field operation types."""

    INSTALLATION = "installation"
    MAINTENANCE = "maintenance"
    REPAIR = "repair"
    INSPECTION = "inspection"
    UPGRADE = "upgrade"
    DECOMMISSION = "decommission"
    SURVEY = "survey"


class OperationStatus(str, Enum):
    """Field operation status."""

    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"
    RESCHEDULED = "rescheduled"


class GisLocation(TenantModel, StatusMixin, AuditMixin, AddressMixin):
    """GIS location model with geographic coordinates."""

    __tablename__ = "gis_locations"

    # Location identification
    name = Column(String(255), nullable=False, index=True)
    location_type = Column(SQLEnum(LocationType), nullable=False, index=True)
    external_id = Column(String(100), nullable=True, unique=True, index=True)

    # Geographic coordinates (using PostGIS if available)
    if POSTGIS_AVAILABLE:
        geometry = Column(Geometry("POINT", srid=4326), nullable=True, index=True)
    else:
        # Fallback to separate lat/lon columns
        latitude = Column(Numeric(precision=10, scale=8), nullable=True, index=True)
        longitude = Column(Numeric(precision=11, scale=8), nullable=True, index=True)

    elevation_meters = Column(Float, nullable=True)
    accuracy_meters = Column(Float, nullable=True)  # GPS accuracy

    # Location properties
    site_area_sqm = Column(Float, nullable=True)
    building_floors = Column(Integer, nullable=True)
    access_type = Column(String(50), nullable=True)  # public, private, restricted

    # Contact and access information
    site_contact_name = Column(String(255), nullable=True)
    site_contact_phone = Column(String(20), nullable=True)
    site_contact_email = Column(String(255), nullable=True)
    access_hours = Column(String(255), nullable=True)
    access_instructions = Column(Text, nullable=True)
    security_requirements = Column(Text, nullable=True)

    # Infrastructure details
    power_available = Column(Boolean, default=False, nullable=False)
    power_backup = Column(Boolean, default=False, nullable=False)
    climate_controlled = Column(Boolean, default=False, nullable=False)
    fiber_ready = Column(Boolean, default=False, nullable=False)

    # Service area information
    service_radius_meters = Column(Float, nullable=True)
    population_density = Column(Integer, nullable=True)  # People per square km
    building_count = Column(Integer, nullable=True)
    business_count = Column(Integer, nullable=True)

    # Additional metadata
    timezone = Column(String(50), nullable=True)
    region_code = Column(String(10), nullable=True)
    municipality = Column(String(100), nullable=True)
    zoning_type = Column(String(50), nullable=True)

    # GIS metadata
    data_source = Column(
        String(100), nullable=True
    )  # Survey, GPS, address_geocoding, etc.
    data_quality = Column(String(50), nullable=True)  # High, medium, low
    last_verified = Column(DateTime(timezone=True), nullable=True)

    # Custom fields and tags
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    devices = relationship("GisDevice", back_populates="location")
    customers = relationship("GisCustomer", back_populates="location")
    fiber_segments = relationship(
        "FiberSegment", foreign_keys="[FiberSegment.start_location_id]"
    )
    field_operations = relationship("FieldOperation", back_populates="location")

    @hybrid_property
    def coordinates(self) -> Optional[Dict[str, float]]:
        """Get coordinates as dictionary."""
        if POSTGIS_AVAILABLE and self.geometry:
            # Would extract lat/lon from PostGIS geometry
            pass
        elif hasattr(self, "latitude") and hasattr(self, "longitude"):
            if self.latitude and self.longitude:
                return {"lat": float(self.latitude), "lon": float(self.longitude)}
        return None

    def set_coordinates(self, latitude: float, longitude: float) -> None:
        """Set geographic coordinates."""
        if POSTGIS_AVAILABLE:
            # Set PostGIS geometry
            pass
        else:
            self.latitude = latitude
            self.longitude = longitude

    def __repr__(self):
        return f"<GisLocation(name='{self.name}', type='{self.location_type}')>"


class GisDevice(TenantModel, StatusMixin, AuditMixin):
    """Device location tracking within GIS system."""

    __tablename__ = "gis_devices"

    location_id = Column(
        UUID(as_uuid=True), ForeignKey("gis_locations.id"), nullable=False, index=True
    )
    network_device_id = Column(
        UUID(as_uuid=True), nullable=True, index=True
    )  # Link to network device

    # Device identification
    device_name = Column(String(255), nullable=False, index=True)
    device_type = Column(String(100), nullable=False, index=True)
    serial_number = Column(String(100), nullable=True)
    asset_tag = Column(String(100), nullable=True)

    # Physical location details
    location_type = Column(SQLEnum(DeviceLocationType), nullable=False)
    floor_level = Column(Integer, nullable=True)
    room_number = Column(String(50), nullable=True)
    rack_id = Column(String(50), nullable=True)
    rack_unit = Column(String(10), nullable=True)

    # Precise positioning within location
    offset_x_meters = Column(Float, nullable=True)  # X offset from location center
    offset_y_meters = Column(Float, nullable=True)  # Y offset from location center
    orientation_degrees = Column(Float, nullable=True)  # Device orientation
    height_meters = Column(Float, nullable=True)  # Height above ground/floor

    # Installation details
    installation_date = Column(DateTime(timezone=True), nullable=True)
    installation_method = Column(String(100), nullable=True)
    mounting_type = Column(String(100), nullable=True)

    # Access and maintenance
    maintenance_access = Column(
        String(100), nullable=True
    )  # Easy, difficult, restricted
    special_tools_required = Column(Boolean, default=False, nullable=False)
    safety_requirements = Column(Text, nullable=True)

    # Environmental conditions
    indoor_outdoor = Column(String(20), nullable=True)
    weatherproofing = Column(String(100), nullable=True)
    temperature_range = Column(String(50), nullable=True)

    # Additional metadata
    notes = Column(Text, nullable=True)
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    location = relationship("GisLocation", back_populates="devices")

    def __repr__(self):
        return f"<GisDevice(name='{self.device_name}', type='{self.device_type}', location='{self.location.name if self.location else 'Unknown'}')>"


class GisCustomer(TenantModel, StatusMixin, AuditMixin, AddressMixin):
    """Customer location information within GIS system."""

    __tablename__ = "gis_customers"

    location_id = Column(
        UUID(as_uuid=True), ForeignKey("gis_locations.id"), nullable=True, index=True
    )
    customer_id = Column(
        UUID(as_uuid=True), nullable=False, index=True
    )  # Link to customer record

    # Customer premise information
    premise_type = Column(
        String(50), nullable=True, index=True
    )  # residential, business, industrial
    building_type = Column(
        String(50), nullable=True
    )  # house, apartment, office, warehouse
    unit_number = Column(String(20), nullable=True)
    floor_number = Column(Integer, nullable=True)

    # Service delivery details
    service_entrance_type = Column(
        String(100), nullable=True
    )  # aerial, underground, building
    service_entrance_location = Column(String(255), nullable=True)
    demarcation_point = Column(String(255), nullable=True)

    # Access information
    property_access = Column(String(100), nullable=True)  # easy, gated, restricted
    key_holder_info = Column(Text, nullable=True)
    pet_information = Column(Text, nullable=True)
    special_instructions = Column(Text, nullable=True)

    # Site characteristics
    property_size_sqm = Column(Float, nullable=True)
    landscaping_notes = Column(Text, nullable=True)
    hazards_notes = Column(Text, nullable=True)

    # Service history
    first_service_date = Column(DateTime(timezone=True), nullable=True)
    last_service_visit = Column(DateTime(timezone=True), nullable=True)
    service_issues_count = Column(Integer, default=0, nullable=False)

    # Additional metadata
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    location = relationship("GisLocation", back_populates="customers")

    def __repr__(self):
        return f"<GisCustomer(customer_id='{self.customer_id}', premise='{self.premise_type}')>"


class FiberNetwork(TenantModel, StatusMixin, AuditMixin):
    """Fiber optic network infrastructure model."""

    __tablename__ = "fiber_networks"

    # Network identification
    network_name = Column(String(255), nullable=False, index=True)
    network_type = Column(
        String(100), nullable=False, index=True
    )  # backbone, distribution, access

    # Network specifications
    fiber_count = Column(Integer, nullable=False)
    fiber_type = Column(SQLEnum(FiberType), nullable=False)
    cable_specifications = Column(JSON, nullable=True)

    # Geographic coverage
    total_length_meters = Column(Float, nullable=True)

    if POSTGIS_AVAILABLE:
        network_geometry = Column(
            Geometry("MULTILINESTRING", srid=4326), nullable=True, index=True
        )

    # Network ownership and management
    owner = Column(String(255), nullable=True)
    operator = Column(String(255), nullable=True)
    maintenance_contact = Column(String(255), nullable=True)

    # Construction details
    construction_method = Column(
        String(100), nullable=True
    )  # aerial, underground, underwater
    construction_date = Column(DateTime(timezone=True), nullable=True)
    contractor = Column(String(255), nullable=True)

    # Capacity and utilization
    design_capacity = Column(Integer, nullable=True)  # Maximum services supported
    current_utilization = Column(Float, nullable=True)  # Percentage utilized
    available_strands = Column(Integer, nullable=True)

    # Additional metadata
    documentation_url = Column(String(500), nullable=True)
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    segments = relationship(
        "FiberSegment", back_populates="network", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<FiberNetwork(name='{self.network_name}', type='{self.network_type}', fibers={self.fiber_count})>"


class FiberSegment(TenantModel, StatusMixin, AuditMixin):
    """Individual fiber network segment model."""

    __tablename__ = "fiber_segments"

    network_id = Column(
        UUID(as_uuid=True), ForeignKey("fiber_networks.id"), nullable=False, index=True
    )
    start_location_id = Column(
        UUID(as_uuid=True), ForeignKey("gis_locations.id"), nullable=False, index=True
    )
    end_location_id = Column(
        UUID(as_uuid=True), ForeignKey("gis_locations.id"), nullable=False, index=True
    )

    # Segment identification
    segment_name = Column(String(255), nullable=False, index=True)
    segment_type = Column(String(100), nullable=False)  # trunk, distribution, drop

    # Physical properties
    length_meters = Column(Float, nullable=False)
    fiber_count = Column(Integer, nullable=False)
    cable_type = Column(String(100), nullable=True)

    if POSTGIS_AVAILABLE:
        segment_geometry = Column(
            Geometry("LINESTRING", srid=4326), nullable=True, index=True
        )

    # Installation details
    installation_method = Column(
        String(100), nullable=True
    )  # aerial, underground, direct_bury
    burial_depth_meters = Column(Float, nullable=True)
    conduit_type = Column(String(100), nullable=True)
    conduit_size = Column(String(50), nullable=True)

    # Connectivity
    splice_points = Column(JSON, nullable=True)  # Array of splice point coordinates
    access_points = Column(JSON, nullable=True)  # Array of access point locations

    # Capacity and utilization
    active_strands = Column(Integer, default=0, nullable=False)
    available_strands = Column(Integer, nullable=False)
    reserved_strands = Column(Integer, default=0, nullable=False)

    # Condition and maintenance
    condition_rating = Column(String(20), nullable=True)  # excellent, good, fair, poor
    last_inspection = Column(DateTime(timezone=True), nullable=True)
    next_maintenance = Column(DateTime(timezone=True), nullable=True)

    # Additional metadata
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    network = relationship("FiberNetwork", back_populates="segments")
    start_location = relationship("GisLocation", foreign_keys=[start_location_id], overlaps="fiber_segments")
    end_location = relationship("GisLocation", foreign_keys=[end_location_id])

    @hybrid_property
    def utilization_percentage(self) -> float:
        """Calculate strand utilization percentage."""
        if self.fiber_count > 0:
            return (self.active_strands / self.fiber_count) * 100
        return 0.0

    def __repr__(self):
        return f"<FiberSegment(name='{self.segment_name}', length={self.length_meters}m, fibers={self.fiber_count})>"


class ServiceCoverage(TenantModel, StatusMixin, AuditMixin):
    """Service coverage area model."""

    __tablename__ = "service_coverage"

    # Coverage identification
    coverage_name = Column(String(255), nullable=False, index=True)
    coverage_type = Column(SQLEnum(CoverageType), nullable=False, index=True)
    service_tier = Column(
        String(100), nullable=True, index=True
    )  # residential, business, enterprise

    # Coverage area
    if POSTGIS_AVAILABLE:
        coverage_geometry = Column(
            Geometry("POLYGON", srid=4326), nullable=True, index=True
        )

    area_sqkm = Column(Float, nullable=True)

    # Service capabilities
    max_download_mbps = Column(Integer, nullable=True)
    max_upload_mbps = Column(Integer, nullable=True)
    technology = Column(String(100), nullable=True)  # FTTH, FTTC, Wireless, etc.

    # Coverage statistics
    total_premises = Column(Integer, nullable=True)
    serviceable_premises = Column(Integer, nullable=True)
    active_customers = Column(Integer, default=0, nullable=False)

    # Network infrastructure
    serving_locations = Column(JSON, nullable=True)  # Array of serving location IDs
    backup_locations = Column(JSON, nullable=True)  # Array of backup location IDs

    # Coverage quality
    coverage_percentage = Column(Float, nullable=True)  # Percentage of area covered
    signal_strength_avg = Column(Float, nullable=True)  # Average signal strength
    reliability_percentage = Column(Float, nullable=True)  # Service reliability

    # Planning and deployment
    deployment_phase = Column(
        String(100), nullable=True
    )  # planned, construction, active, retired
    deployment_priority = Column(Integer, nullable=True)
    target_completion = Column(DateTime(timezone=True), nullable=True)

    # Additional metadata
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<ServiceCoverage(name='{self.coverage_name}', type='{self.coverage_type}', tier='{self.service_tier}')>"


class FieldOperation(TenantModel, StatusMixin, AuditMixin):
    """Field operations and work orders model."""

    __tablename__ = "field_operations"

    location_id = Column(
        UUID(as_uuid=True), ForeignKey("gis_locations.id"), nullable=False, index=True
    )
    customer_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    # Operation identification
    operation_id = Column(String(100), nullable=False, unique=True, index=True)
    operation_type = Column(SQLEnum(OperationType), nullable=False, index=True)
    operation_status = Column(
        SQLEnum(OperationStatus),
        default=OperationStatus.SCHEDULED,
        nullable=False,
        index=True,
    )

    # Scheduling
    scheduled_date = Column(DateTime(timezone=True), nullable=False, index=True)
    scheduled_time_window = Column(String(50), nullable=True)  # e.g., "09:00-12:00"
    estimated_duration_hours = Column(Float, nullable=True)

    # Assignment
    assigned_technician_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    technician_team = Column(JSON, nullable=True)  # Array of technician IDs

    # Work details
    work_description = Column(Text, nullable=False)
    required_skills = Column(JSON, nullable=True)  # Array of required skills
    required_equipment = Column(JSON, nullable=True)  # Array of required equipment
    safety_requirements = Column(Text, nullable=True)

    # Execution tracking
    actual_start_time = Column(DateTime(timezone=True), nullable=True)
    actual_end_time = Column(DateTime(timezone=True), nullable=True)
    actual_duration_hours = Column(Float, nullable=True)

    # Results and completion
    completion_notes = Column(Text, nullable=True)
    work_performed = Column(Text, nullable=True)
    materials_used = Column(JSON, nullable=True)
    issues_encountered = Column(Text, nullable=True)
    follow_up_required = Column(Boolean, default=False, nullable=False)

    # Quality and customer satisfaction
    quality_check_passed = Column(Boolean, nullable=True)
    customer_signature_url = Column(String(500), nullable=True)
    customer_satisfaction = Column(Integer, nullable=True)  # 1-5 rating

    # GPS tracking and route optimization
    route_planned = Column(JSON, nullable=True)  # Planned route coordinates
    route_actual = Column(JSON, nullable=True)  # Actual route taken
    travel_distance_km = Column(Float, nullable=True)
    travel_time_hours = Column(Float, nullable=True)

    # Additional metadata
    priority = Column(Integer, default=3, nullable=False)  # 1=urgent, 5=low
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    location = relationship("GisLocation", back_populates="field_operations")

    __table_args__ = (
        Index("ix_field_operations_scheduled", "scheduled_date", "operation_status"),
        Index(
            "ix_field_operations_technician",
            "assigned_technician_id",
            "operation_status",
        ),
    )

    @hybrid_property
    def duration_variance_hours(self) -> Optional[float]:
        """Calculate variance between estimated and actual duration."""
        if self.estimated_duration_hours and self.actual_duration_hours:
            return self.actual_duration_hours - self.estimated_duration_hours
        return None

    def __repr__(self):
        return f"<FieldOperation(id='{self.operation_id}', type='{self.operation_type}', status='{self.operation_status}')>"


class GisLayer(TenantModel, StatusMixin, AuditMixin):
    """GIS layer management for organizing geographic data."""

    __tablename__ = "gis_layers"

    # Layer identification
    layer_name = Column(String(255), nullable=False, index=True)
    layer_type = Column(
        String(100), nullable=False, index=True
    )  # point, line, polygon, raster
    data_source = Column(String(255), nullable=True)

    # Layer properties
    style_config = Column(JSON, nullable=True)  # Layer styling configuration
    visibility_default = Column(Boolean, default=True, nullable=False)
    zoom_min = Column(Integer, nullable=True)
    zoom_max = Column(Integer, nullable=True)

    # Layer metadata
    description = Column(Text, nullable=True)
    update_frequency = Column(
        String(50), nullable=True
    )  # daily, weekly, monthly, static
    last_updated = Column(DateTime(timezone=True), nullable=True)

    # Access control
    public_access = Column(Boolean, default=False, nullable=False)
    authorized_roles = Column(JSON, nullable=True)  # Array of role names

    # Relationships
    features = relationship(
        "GisFeature", back_populates="layer", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<GisLayer(name='{self.layer_name}', type='{self.layer_type}')>"


class GisFeature(TenantModel, AuditMixin):
    """Individual GIS feature within a layer."""

    __tablename__ = "gis_features"

    layer_id = Column(
        UUID(as_uuid=True), ForeignKey("gis_layers.id"), nullable=False, index=True
    )

    # Feature identification
    feature_name = Column(String(255), nullable=True, index=True)
    feature_type = Column(String(100), nullable=False, index=True)
    external_id = Column(String(100), nullable=True, index=True)

    # Geographic data
    if POSTGIS_AVAILABLE:
        geometry = Column(Geometry("GEOMETRY", srid=4326), nullable=False, index=True)

    # Feature properties
    properties = Column(JSON, nullable=True)  # GeoJSON-style properties

    # Display properties
    style_override = Column(JSON, nullable=True)  # Feature-specific styling
    label = Column(String(255), nullable=True)

    # Relationships
    layer = relationship("GisLayer", back_populates="features")

    def __repr__(self):
        return f"<GisFeature(name='{self.feature_name}', type='{self.feature_type}')>"


class NetworkAsset(TenantModel, StatusMixin, AuditMixin):
    """Network asset tracking with GIS integration."""

    __tablename__ = "network_assets"

    location_id = Column(
        UUID(as_uuid=True), ForeignKey("gis_locations.id"), nullable=True, index=True
    )

    # Asset identification
    asset_name = Column(String(255), nullable=False, index=True)
    asset_type = Column(String(100), nullable=False, index=True)
    asset_category = Column(String(100), nullable=True, index=True)
    manufacturer = Column(String(100), nullable=True)
    model = Column(String(100), nullable=True)
    serial_number = Column(String(100), nullable=True, unique=True)

    # Asset lifecycle
    purchase_date = Column(DateTime(timezone=True), nullable=True)
    installation_date = Column(DateTime(timezone=True), nullable=True)
    warranty_expires = Column(DateTime(timezone=True), nullable=True)
    expected_life_years = Column(Integer, nullable=True)

    # Financial information
    purchase_cost = Column(Numeric(precision=12, scale=2), nullable=True)
    current_value = Column(Numeric(precision=12, scale=2), nullable=True)
    depreciation_method = Column(String(50), nullable=True)

    # Physical condition
    condition_rating = Column(
        String(20), nullable=True
    )  # excellent, good, fair, poor, critical
    last_inspection = Column(DateTime(timezone=True), nullable=True)
    next_maintenance = Column(DateTime(timezone=True), nullable=True)

    # Utilization and capacity
    capacity_total = Column(Float, nullable=True)
    capacity_used = Column(Float, nullable=True)
    utilization_percentage = Column(Float, nullable=True)

    # Additional metadata
    custom_fields = Column(JSON, nullable=True)
    tags = Column(JSON, nullable=True)

    # Relationships
    location = relationship("GisLocation")

    def __repr__(self):
        return f"<NetworkAsset(name='{self.asset_name}', type='{self.asset_type}', serial='{self.serial_number}')>"
