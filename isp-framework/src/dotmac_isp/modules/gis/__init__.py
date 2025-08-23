"""GIS (Geographic Information System) Module for DotMac ISP Framework.

This module provides comprehensive geographic information system capabilities for:
- Device location tracking and mapping
- Fiber network infrastructure visualization
- Service coverage area management
- Customer premise mapping
- Field technician operations and routing
- Network planning and capacity management
- Geographic analytics and reporting
"""

from .models import (
    GisLocation,
    GisDevice,
    GisCustomer,
    FiberNetwork,
    FiberSegment,
    ServiceCoverage,
    FieldOperation,
    GisLayer,
    GisFeature,
    NetworkAsset,
)
from .schemas import (
    GisLocationCreate,
    GisLocationUpdate,
    GisLocationResponse,
    GisDeviceCreate,
    GisDeviceResponse,
    FiberNetworkCreate,
    FiberNetworkResponse,
    ServiceCoverageCreate,
    ServiceCoverageResponse,
    FieldOperationCreate,
    FieldOperationResponse,
)
from .services import (
    GisLocationService,
    FiberNetworkService,
    ServiceCoverageService,
    FieldOperationService,
    GeospatialAnalyticsService,
)
from .utils import (
    calculate_distance,
    generate_coverage_polygon,
    find_nearest_assets,
    optimize_route,
    validate_coordinates,
)

__all__ = [
    # Models
    "GisLocation",
    "GisDevice",
    "GisCustomer",
    "FiberNetwork",
    "FiberSegment",
    "ServiceCoverage",
    "FieldOperation",
    "GisLayer",
    "GisFeature",
    "NetworkAsset",
    # Schemas
    "GisLocationCreate",
    "GisLocationUpdate",
    "GisLocationResponse",
    "GisDeviceCreate",
    "GisDeviceResponse",
    "FiberNetworkCreate",
    "FiberNetworkResponse",
    "ServiceCoverageCreate",
    "ServiceCoverageResponse",
    "FieldOperationCreate",
    "FieldOperationResponse",
    # Services
    "GisLocationService",
    "FiberNetworkService",
    "ServiceCoverageService",
    "FieldOperationService",
    "GeospatialAnalyticsService",
    # Utilities
    "calculate_distance",
    "generate_coverage_polygon",
    "find_nearest_assets",
    "optimize_route",
    "validate_coordinates",
]
