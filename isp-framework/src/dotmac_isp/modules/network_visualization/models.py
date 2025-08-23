"""Network visualization database models."""

from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

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
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property

from dotmac_isp.shared.database.base import TenantModel
from dotmac_isp.shared.database.base import StatusMixin, AuditMixin


class DashboardType(str, Enum):
    """Dashboard types."""

    NETWORK_OVERVIEW = "network_overview"
    DEVICE_MONITORING = "device_monitoring"
    TOPOLOGY_VIEW = "topology_view"
    GEOGRAPHIC_VIEW = "geographic_view"
    PERFORMANCE_METRICS = "performance_metrics"
    ALERTS_INCIDENTS = "alerts_incidents"
    CAPACITY_PLANNING = "capacity_planning"
    CUSTOM = "custom"


class WidgetType(str, Enum):
    """Visualization widget types."""

    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    GAUGE = "gauge"
    COUNTER = "counter"
    TABLE = "table"
    MAP = "map"
    TOPOLOGY = "topology"
    STATUS_INDICATOR = "status_indicator"
    ALERT_LIST = "alert_list"
    DEVICE_LIST = "device_list"
    NETWORK_DIAGRAM = "network_diagram"


class LayoutType(str, Enum):
    """Layout types for network diagrams."""

    HIERARCHICAL = "hierarchical"
    FORCE_DIRECTED = "force_directed"
    CIRCULAR = "circular"
    GRID = "grid"
    GEOGRAPHIC = "geographic"
    CUSTOM = "custom"


class VisualizationDashboard(TenantModel, StatusMixin, AuditMixin):
    """Network visualization dashboard model."""

    __tablename__ = "visualization_dashboards"

    # Dashboard identification
    name = Column(String(255), nullable=False, index=True)
    dashboard_type = Column(SQLEnum(DashboardType), nullable=False, index=True)

    # Dashboard configuration
    layout_config = Column(JSON, nullable=True)  # Grid layout configuration
    refresh_interval = Column(Integer, default=30, nullable=False)  # Seconds
    auto_refresh_enabled = Column(Boolean, default=True, nullable=False)

    # Display settings
    theme = Column(String(50), default="light", nullable=False)
    show_toolbar = Column(Boolean, default=True, nullable=False)
    show_legend = Column(Boolean, default=True, nullable=False)
    full_screen_mode = Column(Boolean, default=False, nullable=False)

    # Access control
    is_public = Column(Boolean, default=False, nullable=False)
    allowed_roles = Column(JSON, nullable=True)  # List of allowed role names
    allowed_users = Column(JSON, nullable=True)  # List of allowed user IDs

    # Dashboard state
    last_accessed = Column(DateTime(timezone=True), nullable=True)
    access_count = Column(Integer, default=0, nullable=False)

    # Additional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    widgets = relationship(
        "VisualizationWidget", back_populates="dashboard", cascade="all, delete-orphan"
    )
    layouts = relationship(
        "DashboardLayout", back_populates="dashboard", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<VisualizationDashboard(name='{self.name}', type='{self.dashboard_type}')>"


class NetworkDiagram(TenantModel, StatusMixin, AuditMixin):
    """Network topology diagram model."""

    __tablename__ = "network_diagrams"

    # Diagram identification
    name = Column(String(255), nullable=False, index=True)
    diagram_type = Column(
        String(100), nullable=False, index=True
    )  # physical, logical, service

    # Diagram scope
    include_device_types = Column(JSON, nullable=True)  # Device types to include
    include_locations = Column(JSON, nullable=True)  # Location IDs to include
    include_networks = Column(JSON, nullable=True)  # Network IDs to include

    # Layout configuration
    layout_type = Column(
        SQLEnum(LayoutType), default=LayoutType.FORCE_DIRECTED, nullable=False
    )
    layout_settings = Column(JSON, nullable=True)  # Layout-specific settings

    # Visual settings
    node_styling = Column(JSON, nullable=True)  # Node appearance configuration
    edge_styling = Column(JSON, nullable=True)  # Edge appearance configuration
    background_config = Column(JSON, nullable=True)  # Background and grid settings

    # Interaction settings
    zoom_enabled = Column(Boolean, default=True, nullable=False)
    pan_enabled = Column(Boolean, default=True, nullable=False)
    node_selection_enabled = Column(Boolean, default=True, nullable=False)

    # Data refresh
    auto_refresh_enabled = Column(Boolean, default=True, nullable=False)
    refresh_interval = Column(Integer, default=60, nullable=False)  # Seconds
    last_refreshed = Column(DateTime(timezone=True), nullable=True)

    # Diagram data (cached)
    topology_data = Column(JSON, nullable=True)  # Cached topology data
    node_positions = Column(JSON, nullable=True)  # Saved node positions

    # Additional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    layouts = relationship(
        "TopologyLayout", back_populates="diagram", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<NetworkDiagram(name='{self.name}', type='{self.diagram_type}')>"


class TopologyLayout(TenantModel, AuditMixin):
    """Saved topology layout configurations."""

    __tablename__ = "topology_layouts"

    diagram_id = Column(
        UUID(as_uuid=True),
        ForeignKey("network_diagrams.id"),
        nullable=False,
        index=True,
    )

    # Layout identification
    layout_name = Column(String(255), nullable=False, index=True)
    is_default = Column(Boolean, default=False, nullable=False)

    # Layout data
    node_positions = Column(JSON, nullable=False)  # Node position data
    view_settings = Column(JSON, nullable=True)  # Zoom, pan, etc.
    layout_algorithm = Column(String(100), nullable=True)  # Algorithm used

    # Layout metadata
    description = Column(Text, nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)

    # Relationships
    diagram = relationship("NetworkDiagram", back_populates="layouts")

    def __repr__(self):
        return f"<TopologyLayout(name='{self.layout_name}', diagram='{self.diagram.name if self.diagram else 'Unknown'}')>"


class VisualizationWidget(TenantModel, StatusMixin, AuditMixin):
    """Individual visualization widget model."""

    __tablename__ = "visualization_widgets"

    dashboard_id = Column(
        UUID(as_uuid=True),
        ForeignKey("visualization_dashboards.id"),
        nullable=False,
        index=True,
    )

    # Widget identification
    widget_name = Column(String(255), nullable=False, index=True)
    widget_type = Column(SQLEnum(WidgetType), nullable=False, index=True)

    # Widget position and size
    position_x = Column(Integer, default=0, nullable=False)
    position_y = Column(Integer, default=0, nullable=False)
    width = Column(Integer, default=4, nullable=False)  # Grid units
    height = Column(Integer, default=3, nullable=False)  # Grid units

    # Data configuration
    data_source = Column(String(255), nullable=False)  # Data source identifier
    data_query = Column(JSON, nullable=True)  # Query parameters
    data_filters = Column(JSON, nullable=True)  # Data filters

    # Display configuration
    title = Column(String(255), nullable=True)
    show_title = Column(Boolean, default=True, nullable=False)
    chart_config = Column(JSON, nullable=True)  # Chart-specific configuration
    color_scheme = Column(String(50), nullable=True)

    # Refresh settings
    auto_refresh = Column(Boolean, default=True, nullable=False)
    refresh_interval = Column(Integer, default=30, nullable=False)  # Seconds

    # Interaction settings
    clickable = Column(Boolean, default=False, nullable=False)
    drill_down_enabled = Column(Boolean, default=False, nullable=False)
    drill_down_config = Column(JSON, nullable=True)

    # Additional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    # Relationships
    dashboard = relationship("VisualizationDashboard", back_populates="widgets")

    def __repr__(self):
        return f"<VisualizationWidget(name='{self.widget_name}', type='{self.widget_type}')>"


class DashboardLayout(TenantModel, AuditMixin):
    """Saved dashboard layout configurations."""

    __tablename__ = "dashboard_layouts"

    dashboard_id = Column(
        UUID(as_uuid=True),
        ForeignKey("visualization_dashboards.id"),
        nullable=False,
        index=True,
    )

    # Layout identification
    layout_name = Column(String(255), nullable=False, index=True)
    is_default = Column(Boolean, default=False, nullable=False)

    # Layout configuration
    grid_config = Column(JSON, nullable=False)  # Grid layout configuration
    widget_positions = Column(JSON, nullable=False)  # Widget positions and sizes

    # Display settings
    theme_override = Column(String(50), nullable=True)
    custom_css = Column(Text, nullable=True)

    # Layout metadata
    description = Column(Text, nullable=True)
    last_used = Column(DateTime(timezone=True), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)

    # Relationships
    dashboard = relationship("VisualizationDashboard", back_populates="layouts")

    def __repr__(self):
        return f"<DashboardLayout(name='{self.layout_name}', dashboard='{self.dashboard.name if self.dashboard else 'Unknown'}')>"


class NetworkMap(TenantModel, StatusMixin, AuditMixin):
    """Geographic network map model."""

    __tablename__ = "network_maps"

    # Map identification
    name = Column(String(255), nullable=False, index=True)
    map_type = Column(
        String(100), nullable=False, index=True
    )  # infrastructure, coverage, service

    # Geographic bounds
    center_latitude = Column(Float, nullable=True)
    center_longitude = Column(Float, nullable=True)
    default_zoom = Column(Integer, default=10, nullable=False)

    # Map configuration
    base_map_provider = Column(String(100), default="openstreetmap", nullable=False)
    show_device_markers = Column(Boolean, default=True, nullable=False)
    show_fiber_routes = Column(Boolean, default=True, nullable=False)
    show_coverage_areas = Column(Boolean, default=False, nullable=False)
    show_customer_locations = Column(Boolean, default=False, nullable=False)

    # Layer configuration
    enabled_layers = Column(JSON, nullable=True)  # List of enabled map layers
    layer_styles = Column(JSON, nullable=True)  # Layer styling configuration

    # Interactive features
    popup_enabled = Column(Boolean, default=True, nullable=False)
    popup_template = Column(JSON, nullable=True)  # Popup content template
    click_actions = Column(JSON, nullable=True)  # Actions on map click

    # Data filters
    location_filters = Column(JSON, nullable=True)  # Location filtering rules
    device_filters = Column(JSON, nullable=True)  # Device filtering rules

    # Auto-refresh
    auto_refresh_enabled = Column(Boolean, default=True, nullable=False)
    refresh_interval = Column(Integer, default=300, nullable=False)  # Seconds
    last_refreshed = Column(DateTime(timezone=True), nullable=True)

    # Additional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
    custom_fields = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<NetworkMap(name='{self.name}', type='{self.map_type}')>"


class VisualizationTemplate(TenantModel, StatusMixin, AuditMixin):
    """Visualization template for creating dashboards."""

    __tablename__ = "visualization_templates"

    # Template identification
    template_name = Column(String(255), nullable=False, index=True)
    template_category = Column(String(100), nullable=False, index=True)

    # Template content
    dashboard_config = Column(JSON, nullable=False)  # Dashboard configuration
    widget_configs = Column(JSON, nullable=False)  # Widget configurations
    layout_config = Column(JSON, nullable=True)  # Layout configuration

    # Template metadata
    preview_image_url = Column(String(500), nullable=True)
    usage_count = Column(Integer, default=0, nullable=False)

    # Template settings
    is_system_template = Column(Boolean, default=False, nullable=False)
    is_public = Column(Boolean, default=False, nullable=False)

    # Additional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)

    def __repr__(self):
        return f"<VisualizationTemplate(name='{self.template_name}', category='{self.template_category}')>"


class VisualizationTheme(TenantModel, StatusMixin, AuditMixin):
    """Custom visualization themes."""

    __tablename__ = "visualization_themes"

    # Theme identification
    theme_name = Column(String(255), nullable=False, index=True)
    base_theme = Column(String(50), default="light", nullable=False)

    # Color configuration
    color_palette = Column(JSON, nullable=False)  # Primary color palette
    chart_colors = Column(JSON, nullable=True)  # Chart-specific colors
    status_colors = Column(JSON, nullable=True)  # Status indicator colors

    # Typography
    font_family = Column(String(100), nullable=True)
    font_sizes = Column(JSON, nullable=True)  # Font size configuration

    # Layout styling
    background_colors = Column(JSON, nullable=True)
    border_styles = Column(JSON, nullable=True)
    spacing_config = Column(JSON, nullable=True)

    # Theme metadata
    is_default = Column(Boolean, default=False, nullable=False)
    usage_count = Column(Integer, default=0, nullable=False)

    # Additional metadata
    description = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)

    def __repr__(self):
        return (
            f"<VisualizationTheme(name='{self.theme_name}', base='{self.base_theme}')>"
        )


class AlertVisualization(TenantModel, AuditMixin):
    """Alert visualization configuration."""

    __tablename__ = "alert_visualizations"

    # Alert visualization identification
    name = Column(String(255), nullable=False, index=True)
    visualization_type = Column(String(100), nullable=False, index=True)

    # Alert filtering
    alert_filters = Column(JSON, nullable=True)  # Alert filtering criteria
    severity_filters = Column(JSON, nullable=True)  # Severity filtering
    device_filters = Column(JSON, nullable=True)  # Device filtering

    # Visualization configuration
    display_config = Column(JSON, nullable=False)  # Display configuration
    grouping_config = Column(JSON, nullable=True)  # Alert grouping rules
    sorting_config = Column(JSON, nullable=True)  # Sorting configuration

    # Auto-refresh
    auto_refresh_enabled = Column(Boolean, default=True, nullable=False)
    refresh_interval = Column(Integer, default=30, nullable=False)  # Seconds

    # Additional metadata
    description = Column(Text, nullable=True)

    def __repr__(self):
        return f"<AlertVisualization(name='{self.name}', type='{self.visualization_type}')>"
