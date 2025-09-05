"""
Location utility functions and calculations.
"""

import math

from .models import Coordinates, Geofence


def calculate_distance(coord1: Coordinates, coord2: Coordinates) -> float:
    """
    Calculate the great circle distance between two coordinates using Haversine formula.

    Args:
        coord1: First coordinate
        coord2: Second coordinate

    Returns:
        Distance in meters
    """
    R = 6371e3  # Earth's radius in meters

    phi1 = math.radians(coord1.latitude)
    phi2 = math.radians(coord2.latitude)
    delta_phi = math.radians(coord2.latitude - coord1.latitude)
    delta_lambda = math.radians(coord2.longitude - coord1.longitude)

    a = math.sin(delta_phi / 2) * math.sin(delta_phi / 2) + math.cos(phi1) * math.cos(
        phi2
    ) * math.sin(delta_lambda / 2) * math.sin(delta_lambda / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def calculate_bearing(from_coord: Coordinates, to_coord: Coordinates) -> float:
    """
    Calculate the bearing (direction) from one coordinate to another.

    Args:
        from_coord: Starting coordinate
        to_coord: Destination coordinate

    Returns:
        Bearing in degrees (0-360)
    """
    phi1 = math.radians(from_coord.latitude)
    phi2 = math.radians(to_coord.latitude)
    delta_lambda = math.radians(to_coord.longitude - from_coord.longitude)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(
        delta_lambda
    )

    theta = math.atan2(y, x)
    return (math.degrees(theta) + 360) % 360


def calculate_midpoint(coord1: Coordinates, coord2: Coordinates) -> Coordinates:
    """
    Calculate the midpoint between two coordinates.

    Args:
        coord1: First coordinate
        coord2: Second coordinate

    Returns:
        Midpoint coordinates
    """
    phi1 = math.radians(coord1.latitude)
    phi2 = math.radians(coord2.latitude)
    delta_lambda = math.radians(coord2.longitude - coord1.longitude)

    lambda1 = math.radians(coord1.longitude)

    Bx = math.cos(phi2) * math.cos(delta_lambda)
    By = math.cos(phi2) * math.sin(delta_lambda)

    phi3 = math.atan2(
        math.sin(phi1) + math.sin(phi2),
        math.sqrt((math.cos(phi1) + Bx) * (math.cos(phi1) + Bx) + By * By),
    )
    lambda3 = lambda1 + math.atan2(By, math.cos(phi1) + Bx)

    return Coordinates(latitude=math.degrees(phi3), longitude=math.degrees(lambda3))


def is_within_geofence(coordinates: Coordinates, geofence: Geofence) -> bool:
    """
    Check if coordinates are within a geofence.

    Args:
        coordinates: Location to check
        geofence: Geofence to check against

    Returns:
        True if coordinates are within geofence
    """
    distance = calculate_distance(coordinates, geofence.center)
    return distance <= geofence.radius


def validate_coordinates(latitude: float, longitude: float) -> bool:
    """
    Validate if latitude and longitude are within valid ranges.

    Args:
        latitude: Latitude value
        longitude: Longitude value

    Returns:
        True if coordinates are valid
    """
    return (-90 <= latitude <= 90) and (-180 <= longitude <= 180)


def calculate_center_from_coordinates(coordinates: list[Coordinates]) -> Coordinates:
    """
    Calculate the center point from a list of coordinates.

    Args:
        coordinates: List of coordinates

    Returns:
        Center coordinate
    """
    if not coordinates:
        raise ValueError("Cannot calculate center from empty coordinates list")

    # Convert to Cartesian coordinates
    x = y = z = 0

    for coord in coordinates:
        lat_rad = math.radians(coord.latitude)
        lon_rad = math.radians(coord.longitude)

        x += math.cos(lat_rad) * math.cos(lon_rad)
        y += math.cos(lat_rad) * math.sin(lon_rad)
        z += math.sin(lat_rad)

    # Average
    total = len(coordinates)
    x /= total
    y /= total
    z /= total

    # Convert back to lat/lng
    center_lon = math.atan2(y, x)
    center_lat = math.atan2(z, math.sqrt(x * x + y * y))

    return Coordinates(
        latitude=math.degrees(center_lat), longitude=math.degrees(center_lon)
    )


def calculate_bounding_box(
    coordinates: list[Coordinates],
) -> tuple[Coordinates, Coordinates]:
    """
    Calculate bounding box (southwest and northeast corners) from coordinates.

    Args:
        coordinates: List of coordinates

    Returns:
        Tuple of (southwest, northeast) coordinates
    """
    if not coordinates:
        raise ValueError("Cannot calculate bounding box from empty coordinates list")

    min_lat = min(coord.latitude for coord in coordinates)
    max_lat = max(coord.latitude for coord in coordinates)
    min_lon = min(coord.longitude for coord in coordinates)
    max_lon = max(coord.longitude for coord in coordinates)

    southwest = Coordinates(latitude=min_lat, longitude=min_lon)
    northeast = Coordinates(latitude=max_lat, longitude=max_lon)

    return southwest, northeast


def calculate_route_distance(waypoints: list[Coordinates]) -> float:
    """
    Calculate total distance for a route with multiple waypoints.

    Args:
        waypoints: List of coordinates representing the route

    Returns:
        Total distance in meters
    """
    if len(waypoints) < 2:
        return 0.0

    total_distance = 0.0
    for i in range(len(waypoints) - 1):
        total_distance += calculate_distance(waypoints[i], waypoints[i + 1])

    return total_distance


def estimate_travel_time(
    distance_meters: float, average_speed_kmh: float = 50.0, traffic_factor: float = 1.2
) -> int:
    """
    Estimate travel time based on distance and average speed.

    Args:
        distance_meters: Distance in meters
        average_speed_kmh: Average speed in km/h
        traffic_factor: Traffic factor (1.0 = no traffic, >1.0 = slower)

    Returns:
        Estimated time in minutes
    """
    distance_km = distance_meters / 1000.0
    time_hours = (distance_km / average_speed_kmh) * traffic_factor
    return int(time_hours * 60)  # Convert to minutes


def find_nearest_coordinate(
    target: Coordinates, candidates: list[Coordinates]
) -> tuple[Coordinates, float]:
    """
    Find the nearest coordinate from a list of candidates.

    Args:
        target: Target coordinate
        candidates: List of candidate coordinates

    Returns:
        Tuple of (nearest_coordinate, distance_meters)
    """
    if not candidates:
        raise ValueError("Cannot find nearest from empty candidates list")

    nearest_coord = candidates[0]
    nearest_distance = calculate_distance(target, nearest_coord)

    for candidate in candidates[1:]:
        distance = calculate_distance(target, candidate)
        if distance < nearest_distance:
            nearest_distance = distance
            nearest_coord = candidate

    return nearest_coord, nearest_distance


def coordinates_within_radius(
    center: Coordinates, coordinates: list[Coordinates], radius_meters: float
) -> list[Coordinates]:
    """
    Filter coordinates that are within a specified radius of a center point.

    Args:
        center: Center coordinate
        coordinates: List of coordinates to filter
        radius_meters: Radius in meters

    Returns:
        List of coordinates within radius
    """
    return [
        coord
        for coord in coordinates
        if calculate_distance(center, coord) <= radius_meters
    ]


def format_coordinates(coordinates: Coordinates, precision: int = 6) -> str:
    """
    Format coordinates as a string with specified precision.

    Args:
        coordinates: Coordinates to format
        precision: Number of decimal places

    Returns:
        Formatted coordinate string
    """
    return (
        f"{coordinates.latitude:.{precision}f}, {coordinates.longitude:.{precision}f}"
    )


def parse_coordinates(coord_string: str) -> Coordinates:
    """
    Parse coordinates from a string format "lat, lon".

    Args:
        coord_string: String in format "latitude, longitude"

    Returns:
        Parsed coordinates

    Raises:
        ValueError: If string format is invalid
    """
    try:
        parts = coord_string.split(",")
        if len(parts) != 2:
            raise ValueError("Invalid coordinate format")

        lat = float(parts[0].strip())
        lon = float(parts[1].strip())

        if not validate_coordinates(lat, lon):
            raise ValueError("Coordinates out of valid range")

        return Coordinates(latitude=lat, longitude=lon)
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid coordinate string '{coord_string}': {e}") from e


def degrees_to_cardinal(degrees: float) -> str:
    """
    Convert degrees to cardinal direction (N, NE, E, SE, S, SW, W, NW).

    Args:
        degrees: Bearing in degrees (0-360)

    Returns:
        Cardinal direction string
    """
    directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    index = int((degrees + 22.5) / 45) % 8
    return directions[index]
