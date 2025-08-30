"""
DotMac Location Services

Comprehensive GPS, geolocation, and mapping services for the DotMac ISP platform.
Provides both backend Python services and frontend TypeScript integration.
"""

from .core import (
    GeocodingService,
    GeofencingService,
    LocationService,
    RouteOptimizationService,
)
from .exceptions import (
    GeocodingError,
    GeofenceError,
    LocationError,
    RouteOptimizationError,
)
from .models import (
    Address,
    Coordinates,
    Geofence,
    Location,
    LocationUpdate,
    Route,
    RouteOptimizationRequest,
    RouteOptimizationResult,
)
from .utils import (
    calculate_bearing,
    calculate_distance,
    calculate_midpoint,
    is_within_geofence,
    validate_coordinates,
)

__version__ = "1.0.0"

__all__ = [
    # Core services
    "LocationService",
    "GeocodingService",
    "RouteOptimizationService",
    "GeofencingService",
    # Data models
    "Coordinates",
    "Location",
    "Address",
    "Geofence",
    "Route",
    "LocationUpdate",
    "RouteOptimizationRequest",
    "RouteOptimizationResult",
    # Utility functions
    "calculate_distance",
    "calculate_bearing",
    "calculate_midpoint",
    "is_within_geofence",
    "validate_coordinates",
    # Exceptions
    "LocationError",
    "GeocodingError",
    "GeofenceError",
    "RouteOptimizationError",
]
