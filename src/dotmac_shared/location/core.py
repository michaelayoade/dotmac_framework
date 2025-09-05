"""
Core location services for the DotMac platform.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from .exceptions import (
    AddressNotFoundError,
    LocationNotFoundError,
    RouteOptimizationError,
)
from .models import (
    Address,
    Coordinates,
    Geofence,
    GeofenceEvent,
    Location,
    LocationSource,
    LocationUpdate,
    Route,
    RouteOptimizationRequest,
    RouteOptimizationResult,
    RouteWaypoint,
)
from .utils import (
    calculate_distance,
    calculate_route_distance,
    estimate_travel_time,
    find_nearest_coordinate,
)


class LocationService:
    """
    Core location service for managing GPS coordinates and location updates.
    """

    def __init__(self):
        self.location_cache: dict[str, Location] = {}
        self.cache_ttl = timedelta(minutes=5)
        self.location_history: dict[str, list[LocationUpdate]] = {}
        self.max_history_per_user = 1000

    def update_location(
        self,
        user_id: str,
        coordinates: Coordinates,
        source: LocationSource = LocationSource.GPS,
        work_order_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> LocationUpdate:
        """
        Update user location and create location update event.

        Args:
            user_id: User identifier
            coordinates: GPS coordinates
            source: Source of location data
            work_order_id: Optional work order ID
            metadata: Additional metadata

        Returns:
            LocationUpdate object
        """
        location = Location(
            coordinates=coordinates, source=source, metadata=metadata or {}
        )

        # Cache the location
        self.location_cache[user_id] = location

        # Create location update
        update = LocationUpdate(
            user_id=user_id,
            work_order_id=work_order_id,
            location=location,
            metadata=metadata or {},
        )

        # Add to history
        if user_id not in self.location_history:
            self.location_history[user_id] = []

        self.location_history[user_id].append(update)

        # Trim history if needed
        if len(self.location_history[user_id]) > self.max_history_per_user:
            self.location_history[user_id] = self.location_history[user_id][
                -self.max_history_per_user :
            ]

        return update

    def get_current_location(self, user_id: str) -> Optional[Location]:
        """
        Get current cached location for user.

        Args:
            user_id: User identifier

        Returns:
            Current location or None if not available
        """
        location = self.location_cache.get(user_id)

        # Check if location is stale
        if location and location.timestamp:
            age = datetime.now(timezone.utc) - location.timestamp
            if age > self.cache_ttl:
                return None

        return location

    def get_location_history(
        self,
        user_id: str,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> list[LocationUpdate]:
        """
        Get location history for user.

        Args:
            user_id: User identifier
            since: Only return updates since this time
            limit: Maximum number of updates to return

        Returns:
            List of location updates
        """
        history = self.location_history.get(user_id, [])

        if since:
            history = [update for update in history if update.created_at >= since]

        if limit:
            history = history[-limit:]

        return history

    def calculate_distance_between_users(
        self, user1_id: str, user2_id: str
    ) -> Optional[float]:
        """
        Calculate distance between two users based on their current locations.

        Args:
            user1_id: First user ID
            user2_id: Second user ID

        Returns:
            Distance in meters or None if locations not available
        """
        loc1 = self.get_current_location(user1_id)
        loc2 = self.get_current_location(user2_id)

        if not loc1 or not loc2:
            return None

        return calculate_distance(loc1.coordinates, loc2.coordinates)

    def find_nearby_users(
        self, user_id: str, radius_meters: float = 1000
    ) -> list[tuple[str, float]]:
        """
        Find users within specified radius of given user.

        Args:
            user_id: User to find nearby users for
            radius_meters: Search radius in meters

        Returns:
            List of tuples (user_id, distance_meters)
        """
        user_location = self.get_current_location(user_id)
        if not user_location:
            return []

        nearby_users = []

        for other_user_id, location in self.location_cache.items():
            if other_user_id == user_id:
                continue

            # Check if location is fresh
            age = datetime.now(timezone.utc) - location.timestamp
            if age > self.cache_ttl:
                continue

            distance = calculate_distance(
                user_location.coordinates, location.coordinates
            )
            if distance <= radius_meters:
                nearby_users.append((other_user_id, distance))

        # Sort by distance
        nearby_users.sort(key=lambda x: x[1])

        return nearby_users


class GeocodingService:
    """
    Service for converting addresses to coordinates and vice versa.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.geocoding_cache: dict[str, tuple[Coordinates, Address]] = {}
        self.reverse_geocoding_cache: dict[str, Address] = {}

    async def geocode_address(self, address: str) -> tuple[Coordinates, Address]:
        """
        Convert address string to coordinates and structured address.

        Args:
            address: Address string to geocode

        Returns:
            Tuple of (coordinates, structured_address)

        Raises:
            AddressNotFoundError: If address cannot be geocoded
        """
        # Check cache first
        cache_key = address.lower().strip()
        if cache_key in self.geocoding_cache:
            return self.geocoding_cache[cache_key]

        # In a real implementation, this would call a geocoding API
        # For now, return mock data for demo purposes
        if "123 main st" in cache_key:
            coords = Coordinates(40.7128, -74.0060, accuracy=10.0)
            addr = Address(
                street_number="123",
                street_name="Main St",
                city="New York",
                state="NY",
                postal_code="10001",
                country="USA",
                formatted_address="123 Main St, New York, NY 10001, USA",
            )

            # Cache result
            self.geocoding_cache[cache_key] = (coords, addr)
            return coords, addr

        raise AddressNotFoundError(f"Could not geocode address: {address}")

    async def reverse_geocode(self, coordinates: Coordinates) -> Address:
        """
        Convert coordinates to address information.

        Args:
            coordinates: GPS coordinates

        Returns:
            Structured address information

        Raises:
            LocationNotFoundError: If coordinates cannot be reverse geocoded
        """
        cache_key = f"{coordinates.latitude:.6f},{coordinates.longitude:.6f}"
        if cache_key in self.reverse_geocoding_cache:
            return self.reverse_geocoding_cache[cache_key]

        # In a real implementation, this would call a reverse geocoding API
        # For now, return mock data based on coordinates
        if (
            40.7 <= coordinates.latitude <= 40.8
            and -74.1 <= coordinates.longitude <= -74.0
        ):
            address = Address(
                street_name="Broadway",
                city="New York",
                state="NY",
                country="USA",
                formatted_address="Broadway, New York, NY, USA",
            )

            # Cache result
            self.reverse_geocoding_cache[cache_key] = address
            return address

        raise LocationNotFoundError(
            f"Could not reverse geocode coordinates: {coordinates.latitude}, {coordinates.longitude}"
        )

    async def batch_geocode(
        self, addresses: list[str]
    ) -> list[Optional[tuple[Coordinates, Address]]]:
        """
        Geocode multiple addresses in batch.

        Args:
            addresses: List of address strings

        Returns:
            List of results, with None for addresses that couldn't be geocoded
        """
        results = []

        for address in addresses:
            try:
                result = await self.geocode_address(address)
                results.append(result)
            except AddressNotFoundError:
                results.append(None)

        return results


class GeofencingService:
    """
    Service for managing geofences and detecting entry/exit events.
    """

    def __init__(self):
        self.geofences: dict[str, Geofence] = {}
        self.user_geofence_status: dict[
            str, dict[str, bool]
        ] = {}  # user_id -> geofence_id -> inside
        self.event_callbacks: list[callable] = []

    def create_geofence(self, geofence: Geofence) -> str:
        """
        Create a new geofence.

        Args:
            geofence: Geofence to create

        Returns:
            Geofence ID
        """
        self.geofences[geofence.id] = geofence
        return geofence.id

    def get_geofence(self, geofence_id: str) -> Optional[Geofence]:
        """Get geofence by ID."""
        return self.geofences.get(geofence_id)

    def update_geofence(self, geofence_id: str, updates: dict[str, Any]) -> bool:
        """
        Update geofence properties.

        Args:
            geofence_id: ID of geofence to update
            updates: Dictionary of updates

        Returns:
            True if updated successfully
        """
        geofence = self.geofences.get(geofence_id)
        if not geofence:
            return False

        for key, value in updates.items():
            if hasattr(geofence, key):
                setattr(geofence, key, value)

        return True

    def delete_geofence(self, geofence_id: str) -> bool:
        """
        Delete a geofence.

        Args:
            geofence_id: ID of geofence to delete

        Returns:
            True if deleted successfully
        """
        if geofence_id in self.geofences:
            del self.geofences[geofence_id]

            # Clean up user status
            for user_status in self.user_geofence_status.values():
                if geofence_id in user_status:
                    del user_status[geofence_id]

            return True

        return False

    def get_geofences_for_location(self, coordinates: Coordinates) -> list[Geofence]:
        """
        Get all geofences that contain the given location.

        Args:
            coordinates: Location to check

        Returns:
            List of geofences containing the location
        """
        containing_geofences = []

        for geofence in self.geofences.values():
            if not geofence.active:
                continue

            if geofence.contains_location(coordinates):
                containing_geofences.append(geofence)

        return containing_geofences

    def check_geofence_events(
        self, user_id: str, location_update: LocationUpdate
    ) -> list[GeofenceEvent]:
        """
        Check for geofence entry/exit events for a user location update.

        Args:
            user_id: User identifier
            location_update: Location update to check

        Returns:
            List of geofence events
        """
        events = []
        coordinates = location_update.location.coordinates

        # Initialize user status if needed
        if user_id not in self.user_geofence_status:
            self.user_geofence_status[user_id] = {}

        user_status = self.user_geofence_status[user_id]

        # Check all active geofences
        for geofence in self.geofences.values():
            if not geofence.active:
                continue

            geofence_id = geofence.id
            was_inside = user_status.get(geofence_id, False)
            is_inside = geofence.contains_location(coordinates)

            # Update status
            user_status[geofence_id] = is_inside

            # Generate events for status changes
            if not was_inside and is_inside:
                # Entry event
                event = GeofenceEvent(
                    geofence_id=geofence_id,
                    user_id=user_id,
                    work_order_id=location_update.work_order_id,
                    event_type="enter",
                    location=location_update.location,
                )
                events.append(event)

            elif was_inside and not is_inside:
                # Exit event
                event = GeofenceEvent(
                    geofence_id=geofence_id,
                    user_id=user_id,
                    work_order_id=location_update.work_order_id,
                    event_type="exit",
                    location=location_update.location,
                )
                events.append(event)

        # Trigger callbacks for events
        for event in events:
            self._trigger_event_callbacks(event)

        return events

    def add_event_callback(self, callback: callable) -> None:
        """Add callback function for geofence events."""
        self.event_callbacks.append(callback)

    def _trigger_event_callbacks(self, event: GeofenceEvent) -> None:
        """Trigger all registered event callbacks."""
        for callback in self.event_callbacks:
            try:
                callback(event)
            except Exception as e:
                # Log error but don't fail the event processing
                import logging

                logging.getLogger(__name__).info(
                    f"Error in geofence event callback: {e}"
                )


class RouteOptimizationService:
    """
    Service for optimizing routes and calculating optimal paths.
    """

    def __init__(self):
        self.optimization_cache: dict[str, RouteOptimizationResult] = {}

    def optimize_route(
        self, request: RouteOptimizationRequest
    ) -> RouteOptimizationResult:
        """
        Optimize a route based on the given request.

        Args:
            request: Route optimization request

        Returns:
            Optimized route result
        """
        waypoints = request.waypoints.copy()

        if not waypoints:
            raise RouteOptimizationError("No waypoints provided for optimization")

        # Simple nearest neighbor optimization (for demo)
        # In production, would use more sophisticated algorithms
        optimized_waypoints = self._nearest_neighbor_optimization(
            waypoints, request.start_location
        )

        # Calculate metrics
        original_distance = calculate_route_distance(waypoints) / 1000  # Convert to km
        optimized_distance = calculate_route_distance(optimized_waypoints) / 1000

        original_duration = estimate_travel_time(original_distance * 1000)
        optimized_duration = estimate_travel_time(optimized_distance * 1000)

        distance_saved = original_distance - optimized_distance
        time_saved = original_duration - optimized_duration
        efficiency_improvement = (
            (distance_saved / original_distance * 100) if original_distance > 0 else 0
        )

        # Create optimized route
        route_waypoints = []
        for i, coord in enumerate(optimized_waypoints):
            waypoint = RouteWaypoint(coordinates=coord, name=f"Stop {i+1}")
            route_waypoints.append(waypoint)

        optimized_route = Route(
            name="Optimized Route",
            waypoints=route_waypoints,
            total_distance=optimized_distance,
            total_duration=optimized_duration,
            optimized=True,
        )

        result = RouteOptimizationResult(
            optimized_route=optimized_route,
            original_distance=original_distance,
            optimized_distance=optimized_distance,
            original_duration=original_duration,
            optimized_duration=optimized_duration,
            distance_saved=distance_saved,
            time_saved=time_saved,
            efficiency_improvement=efficiency_improvement,
        )

        return result

    def _nearest_neighbor_optimization(
        self, waypoints: list[Coordinates], start_location: Optional[Coordinates] = None
    ) -> list[Coordinates]:
        """
        Simple nearest neighbor route optimization.

        Args:
            waypoints: List of waypoints to optimize
            start_location: Optional starting location

        Returns:
            Optimized list of waypoints
        """
        if len(waypoints) <= 2:
            return waypoints

        current = start_location or waypoints[0]
        remaining = waypoints.copy()
        optimized = []

        # If we have a start location that's not in waypoints, add current location
        if start_location and start_location not in waypoints:
            optimized.append(current)

        while remaining:
            # Find nearest unvisited waypoint
            nearest_coord, _ = find_nearest_coordinate(current, remaining)
            optimized.append(nearest_coord)
            remaining.remove(nearest_coord)
            current = nearest_coord

        return optimized

    def calculate_route_metrics(self, waypoints: list[Coordinates]) -> dict[str, Any]:
        """
        Calculate metrics for a route.

        Args:
            waypoints: List of route waypoints

        Returns:
            Dictionary of route metrics
        """
        if len(waypoints) < 2:
            return {
                "total_distance_km": 0.0,
                "estimated_duration_minutes": 0,
                "waypoint_count": len(waypoints),
                "average_segment_distance_km": 0.0,
            }

        total_distance_m = calculate_route_distance(waypoints)
        total_distance_km = total_distance_m / 1000.0
        estimated_duration = estimate_travel_time(total_distance_m)

        segment_distances = []
        for i in range(len(waypoints) - 1):
            segment_dist = calculate_distance(waypoints[i], waypoints[i + 1]) / 1000.0
            segment_distances.append(segment_dist)

        avg_segment_distance = (
            sum(segment_distances) / len(segment_distances)
            if segment_distances
            else 0.0
        )

        return {
            "total_distance_km": total_distance_km,
            "estimated_duration_minutes": estimated_duration,
            "waypoint_count": len(waypoints),
            "average_segment_distance_km": avg_segment_distance,
            "segment_distances_km": segment_distances,
        }
