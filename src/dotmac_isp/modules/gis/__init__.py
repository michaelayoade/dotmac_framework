"""
GIS and Mapping Module for DotMac ISP Framework

Leverages existing DotMac systems:
- RouterFactory for DRY API patterns
- Base schemas for validation
- Network visualization module for topology
- Standard authentication and dependencies
- Multi-tenant isolation
"""

from .models import (
    CoverageGap,
    CoverageRecommendation,
    NetworkNode,
    RouteOptimization,
    ServiceArea,
    Territory,
)
from .router import gis_router
from .schemas import (
    CoverageAnalysisRequest,
    CoverageAnalysisResponse,
    NetworkNodeCreate,
    NetworkNodeResponse,
    NetworkNodeUpdate,
    RouteOptimizationRequest,
    RouteOptimizationResponse,
    ServiceAreaCreate,
    ServiceAreaResponse,
    ServiceAreaUpdate,
    TerritoryCreate,
    TerritoryResponse,
    TerritoryUpdate,
)
from .services import (
    GeocodingService,
    RouteOptimizationService,
    ServiceCoverageService,
    TerritoryManagementService,
)

__all__ = [
    # Models
    "ServiceArea",
    "NetworkNode",
    "CoverageGap",
    "CoverageRecommendation",
    "Territory",
    "RouteOptimization",
    # Schemas
    "ServiceAreaCreate",
    "ServiceAreaUpdate",
    "ServiceAreaResponse",
    "NetworkNodeCreate",
    "NetworkNodeUpdate",
    "NetworkNodeResponse",
    "CoverageAnalysisRequest",
    "CoverageAnalysisResponse",
    "TerritoryCreate",
    "TerritoryUpdate",
    "TerritoryResponse",
    "RouteOptimizationRequest",
    "RouteOptimizationResponse",
    # Services
    "ServiceCoverageService",
    "TerritoryManagementService",
    "RouteOptimizationService",
    "GeocodingService",
    # Router
    "gis_router",
]
