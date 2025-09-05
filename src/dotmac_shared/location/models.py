"""
Location service data models and types.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class LocationSource(str, Enum):
    """Source of location data."""

    GPS = "gps"
    NETWORK = "network"
    PASSIVE = "passive"
    MANUAL = "manual"
    GEOCODED = "geocoded"


class GeofenceType(str, Enum):
    """Types of geofences."""

    WORK_SITE = "work_site"
    SERVICE_AREA = "service_area"
    OFFICE = "office"
    WAREHOUSE = "warehouse"
    RESTRICTED = "restricted"
    CUSTOMER_PREMISES = "customer_premises"


class LocationAccuracy(str, Enum):
    """Location accuracy levels."""

    HIGH = "high"  # < 10m
    MEDIUM = "medium"  # 10-50m
    LOW = "low"  # > 50m
    UNKNOWN = "unknown"


@dataclass
class Coordinates:
    """GPS coordinates with optional metadata."""

    latitude: float
    longitude: float
    accuracy: Optional[float] = None  # meters
    altitude: Optional[float] = None  # meters above sea level
    heading: Optional[float] = None  # degrees (0-360)
    speed: Optional[float] = None  # m/s

    def __post_init__(self):
        # Validate coordinates
        if not (-90 <= self.latitude <= 90):
            raise ValueError(f"Invalid latitude: {self.latitude}. Must be between -90 and 90.")
        if not (-180 <= self.longitude <= 180):
            raise ValueError(f"Invalid longitude: {self.longitude}. Must be between -180 and 180.")

    @property
    def accuracy_level(self) -> LocationAccuracy:
        """Get accuracy level based on accuracy value."""
        if self.accuracy is None:
            return LocationAccuracy.UNKNOWN
        elif self.accuracy < 10:
            return LocationAccuracy.HIGH
        elif self.accuracy < 50:
            return LocationAccuracy.MEDIUM
        else:
            return LocationAccuracy.LOW

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "accuracy": self.accuracy,
            "altitude": self.altitude,
            "heading": self.heading,
            "speed": self.speed,
        }


@dataclass
class Address:
    """Structured address information."""

    street_number: Optional[str] = None
    street_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    formatted_address: Optional[str] = None

    def __str__(self) -> str:
        """Return formatted address string."""
        if self.formatted_address:
            return self.formatted_address

        parts = []
        if self.street_number and self.street_name:
            parts.append(f"{self.street_number} {self.street_name}")
        elif self.street_name:
            parts.append(self.street_name)

        if self.city:
            parts.append(self.city)
        if self.state:
            parts.append(self.state)
        if self.postal_code:
            parts.append(self.postal_code)

        return ", ".join(parts)


@dataclass
class Location:
    """Complete location information with coordinates and address."""

    coordinates: Coordinates
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: LocationSource = LocationSource.GPS
    address: Optional[Address] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def latitude(self) -> float:
        """Convenience property for latitude."""
        return self.coordinates.latitude

    @property
    def longitude(self) -> float:
        """Convenience property for longitude."""
        return self.coordinates.longitude

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "coordinates": self.coordinates.to_dict(),
            "timestamp": self.timestamp.isoformat(),
            "source": self.source.value,
            "address": self.address.__dict__ if self.address else None,
            "metadata": self.metadata,
        }


@dataclass
class LocationUpdate:
    """Location update event."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    work_order_id: Optional[str] = None
    location: Location = field(default_factory=lambda: Location(Coordinates(0, 0)))
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Geofence:
    """Geofence definition."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    center: Coordinates = field(default_factory=lambda: Coordinates(0, 0))
    radius: float = 100.0  # meters
    fence_type: GeofenceType = GeofenceType.WORK_SITE
    work_order_id: Optional[str] = None
    customer_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def contains_location(self, coordinates: Coordinates) -> bool:
        """Check if coordinates are within this geofence."""
        from .utils import calculate_distance

        distance = calculate_distance(self.center, coordinates)
        return distance <= self.radius


@dataclass
class RouteWaypoint:
    """A waypoint in a route."""

    coordinates: Coordinates
    name: Optional[str] = None
    work_order_id: Optional[str] = None
    estimated_arrival: Optional[datetime] = None
    estimated_duration: Optional[int] = None  # minutes
    address: Optional[Address] = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Route:
    """Route with multiple waypoints."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    waypoints: list[RouteWaypoint] = field(default_factory=list)
    total_distance: float = 0.0  # kilometers
    total_duration: int = 0  # minutes
    optimized: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_waypoint(self, waypoint: RouteWaypoint) -> None:
        """Add waypoint to route."""
        self.waypoints.append(waypoint)

    def get_coordinates_list(self) -> list[Coordinates]:
        """Get list of coordinates from waypoints."""
        return [wp.coordinates for wp in self.waypoints]


@dataclass
class RouteOptimizationRequest:
    """Request for route optimization."""

    start_location: Optional[Coordinates] = None
    end_location: Optional[Coordinates] = None
    waypoints: list[Coordinates] = field(default_factory=list)
    work_order_ids: list[str] = field(default_factory=list)
    constraints: dict[str, Any] = field(default_factory=dict)
    optimization_type: str = "distance"  # "distance", "time", "balanced"


@dataclass
class RouteOptimizationResult:
    """Result from route optimization."""

    optimized_route: Route
    original_distance: float  # km
    optimized_distance: float  # km
    original_duration: int  # minutes
    optimized_duration: int  # minutes
    distance_saved: float  # km
    time_saved: int  # minutes
    efficiency_improvement: float  # percentage
    optimization_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GeofenceEvent:
    """Geofence entry/exit event."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    geofence_id: str = ""
    user_id: str = ""
    work_order_id: Optional[str] = None
    event_type: str = "enter"  # "enter", "exit", "dwell"
    location: Location = field(default_factory=lambda: Location(Coordinates(0, 0)))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceArea:
    """ISP service area definition."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    boundary: list[Coordinates] = field(default_factory=list)  # Polygon vertices
    center: Optional[Coordinates] = None
    service_type: str = "fiber"  # "fiber", "wireless", "dsl"
    max_speed_mbps: Optional[int] = None
    coverage_level: str = "full"  # "full", "partial", "planned"
    technician_zones: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    active: bool = True

    def contains_location(self, coordinates: Coordinates) -> bool:
        """Check if coordinates are within service area using point-in-polygon algorithm."""
        if not self.boundary or len(self.boundary) < 3:
            return False

        x, y = coordinates.longitude, coordinates.latitude
        n = len(self.boundary)
        inside = False

        p1x, p1y = self.boundary[0].longitude, self.boundary[0].latitude
        for i in range(1, n + 1):
            p2x, p2y = self.boundary[i % n].longitude, self.boundary[i % n].latitude
            if y > min(p1y, p2y):
                if y <= max(p1y, p2y):
                    if x <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside
