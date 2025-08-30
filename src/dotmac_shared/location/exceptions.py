"""
Location service exceptions.
"""


class LocationError(Exception):
    """Base exception for location-related errors."""

    pass


class InvalidCoordinatesError(LocationError):
    """Raised when coordinates are invalid."""

    pass


class LocationNotFoundError(LocationError):
    """Raised when location cannot be determined."""

    pass


class GeocodingError(LocationError):
    """Base exception for geocoding-related errors."""

    pass


class GeocodingServiceError(GeocodingError):
    """Raised when geocoding service is unavailable or returns error."""

    pass


class AddressNotFoundError(GeocodingError):
    """Raised when address cannot be geocoded."""

    pass


class GeofenceError(LocationError):
    """Base exception for geofence-related errors."""

    pass


class GeofenceNotFoundError(GeofenceError):
    """Raised when geofence is not found."""

    pass


class GeofenceValidationError(GeofenceError):
    """Raised when geofence data is invalid."""

    pass


class RouteOptimizationError(LocationError):
    """Base exception for route optimization errors."""

    pass


class RouteOptimizationServiceError(RouteOptimizationError):
    """Raised when route optimization service fails."""

    pass


class InvalidRouteError(RouteOptimizationError):
    """Raised when route data is invalid."""

    pass


class ServiceAreaError(LocationError):
    """Base exception for service area errors."""

    pass


class ServiceAreaNotFoundError(ServiceAreaError):
    """Raised when service area is not found."""

    pass


class LocationPermissionError(LocationError):
    """Raised when location permissions are not granted."""

    pass


class LocationTimeoutError(LocationError):
    """Raised when location request times out."""

    pass
