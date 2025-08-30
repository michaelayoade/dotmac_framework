"""GIS coordinate utilities and distance calculations."""

import math
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

from dotmac_shared.api.exception_handlers import standard_exception_handler

from ..exceptions import GISError


class CoordinateSystem(Enum):
    """Supported coordinate systems."""

    WGS84 = "WGS84"
    UTM = "UTM"
    MERCATOR = "MERCATOR"


class GISUtils:
    """GIS utility functions for network topology mapping."""

    @staticmethod
    def validate_coordinates(lat: float, lon: float) -> bool:
        """Validate latitude and longitude coordinates."""
        if not (-90 <= lat <= 90):
            return False
        if not (-180 <= lon <= 180):
            return False
        return True

    @staticmethod
    def normalize_coordinates(coordinates: Dict[str, float]) -> Dict[str, float]:
        """Normalize coordinate dictionary."""
        lat = coordinates.get("latitude", 0.0)
        lon = coordinates.get("longitude", 0.0)

        if not GISUtils.validate_coordinates(lat, lon):
            raise GISError(f"Invalid coordinates: lat={lat}, lon={lon}")

        return {"latitude": float(lat), "longitude": float(lon)}

    @staticmethod
    def degrees_to_radians(degrees: float) -> float:
        """Convert degrees to radians."""
        return math.radians(degrees)

    @staticmethod
    def radians_to_degrees(radians: float) -> float:
        """Convert radians to degrees."""
        return math.degrees(radians)

    @staticmethod
    def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing between two points in degrees."""
        lat1_rad = GISUtils.degrees_to_radians(lat1)
        lat2_rad = GISUtils.degrees_to_radians(lat2)
        dlon_rad = GISUtils.degrees_to_radians(lon2 - lon1)

        y = math.sin(dlon_rad) * math.cos(lat2_rad)
        x = math.cos(lat1_rad) * math.sin(lat2_rad) - math.sin(lat1_rad) * math.cos(
            lat2_rad
        ) * math.cos(dlon_rad)

        bearing_rad = math.atan2(y, x)
        bearing_deg = GISUtils.radians_to_degrees(bearing_rad)

        # Normalize to 0-360 degrees
        return (bearing_deg + 360) % 360

    @staticmethod
    def calculate_midpoint(
        lat1: float, lon1: float, lat2: float, lon2: float
    ) -> Tuple[float, float]:
        """Calculate midpoint between two coordinates."""
        lat1_rad = GISUtils.degrees_to_radians(lat1)
        lon1_rad = GISUtils.degrees_to_radians(lon1)
        lat2_rad = GISUtils.degrees_to_radians(lat2)
        dlon_rad = GISUtils.degrees_to_radians(lon2 - lon1)

        bx = math.cos(lat2_rad) * math.cos(dlon_rad)
        by = math.cos(lat2_rad) * math.sin(dlon_rad)

        lat_mid_rad = math.atan2(
            math.sin(lat1_rad) + math.sin(lat2_rad),
            math.sqrt((math.cos(lat1_rad) + bx) ** 2 + by**2),
        )

        lon_mid_rad = lon1_rad + math.atan2(by, math.cos(lat1_rad) + bx)

        return (
            GISUtils.radians_to_degrees(lat_mid_rad),
            GISUtils.radians_to_degrees(lon_mid_rad),
        )


class DistanceCalculator:
    """Advanced distance calculations for network topology."""

    # Earth radius in kilometers
    EARTH_RADIUS_KM = 6371.0
    EARTH_RADIUS_MILES = 3959.0

    @staticmethod
    def haversine_distance(
        lat1: float, lon1: float, lat2: float, lon2: float, unit: str = "km"
    ) -> float:
        """
        Calculate distance between two points using Haversine formula.

        Args:
            lat1, lon1: Latitude and longitude of first point
            lat2, lon2: Latitude and longitude of second point
            unit: Distance unit ('km' or 'miles')

        Returns:
            Distance in specified unit
        """
        # Validate coordinates
        if not all(
            GISUtils.validate_coordinates(lat, lon)
            for lat, lon in [(lat1, lon1), (lat2, lon2)]
        ):
            raise GISError("Invalid coordinates provided")

        # Convert to radians
        lat1_rad = GISUtils.degrees_to_radians(lat1)
        lon1_rad = GISUtils.degrees_to_radians(lon1)
        lat2_rad = GISUtils.degrees_to_radians(lat2)
        lon2_rad = GISUtils.degrees_to_radians(lon2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # Calculate distance
        if unit.lower() == "km":
            return DistanceCalculator.EARTH_RADIUS_KM * c
        elif unit.lower() == "miles":
            return DistanceCalculator.EARTH_RADIUS_MILES * c
        else:
            raise GISError(f"Unsupported unit: {unit}")

    @staticmethod
    def euclidean_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate simple Euclidean distance (for small distances).
        Note: This is approximate and should only be used for short distances.
        """
        # Convert degrees to approximate km (rough conversion)
        lat_diff = (lat2 - lat1) * 111.0  # ~111 km per degree latitude
        lon_diff = (lon2 - lon1) * 111.0 * math.cos(GISUtils.degrees_to_radians(lat1))

        return math.sqrt(lat_diff**2 + lon_diff**2)

    @staticmethod
    def calculate_distance_matrix(
        locations: List[Dict[str, float]], unit: str = "km"
    ) -> List[List[float]]:
        """
        Calculate distance matrix between all pairs of locations.

        Args:
            locations: List of location dictionaries with 'latitude' and 'longitude'
            unit: Distance unit

        Returns:
            2D matrix of distances
        """
        n = len(locations)
        matrix = [[0.0 for _ in range(n)] for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                loc1 = GISUtils.normalize_coordinates(locations[i])
                loc2 = GISUtils.normalize_coordinates(locations[j])

                distance = DistanceCalculator.haversine_distance(
                    loc1["latitude"],
                    loc1["longitude"],
                    loc2["latitude"],
                    loc2["longitude"],
                    unit,
                )

                matrix[i][j] = distance
                matrix[j][i] = distance  # Symmetric matrix

        return matrix

    @staticmethod
    def find_nearest_locations(
        reference: Dict[str, float],
        candidates: List[Dict[str, Union[float, str]]],
        max_distance: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[Dict[str, Union[str, float]]]:
        """
        Find nearest locations to a reference point.

        Args:
            reference: Reference location with latitude/longitude
            candidates: List of candidate locations with latitude/longitude and id
            max_distance: Maximum distance in km (optional)
            limit: Maximum number of results (optional)

        Returns:
            List of nearest locations sorted by distance
        """
        reference = GISUtils.normalize_coordinates(reference)
        results = []

        for candidate in candidates:
            try:
                candidate_coords = GISUtils.normalize_coordinates(candidate)
                distance = DistanceCalculator.haversine_distance(
                    reference["latitude"],
                    reference["longitude"],
                    candidate_coords["latitude"],
                    candidate_coords["longitude"],
                )

                if max_distance is None or distance <= max_distance:
                    result = {
                        "id": candidate.get("id", "unknown"),
                        "latitude": candidate_coords["latitude"],
                        "longitude": candidate_coords["longitude"],
                        "distance_km": distance,
                        "bearing": GISUtils.calculate_bearing(
                            reference["latitude"],
                            reference["longitude"],
                            candidate_coords["latitude"],
                            candidate_coords["longitude"],
                        ),
                    }
                    results.append(result)
            except GISError:
                # Skip invalid coordinates
                continue

        # Sort by distance
        results.sort(key=lambda x: x["distance_km"])

        # Apply limit
        if limit is not None:
            results = results[:limit]

        return results

    @staticmethod
    def calculate_coverage_area(
        center: Dict[str, float], radius_km: float, points: int = 32
    ) -> List[Dict[str, float]]:
        """
        Calculate points around a center location for coverage visualization.

        Args:
            center: Center location with latitude/longitude
            radius_km: Coverage radius in kilometers
            points: Number of points to generate around the circle

        Returns:
            List of points forming a circle
        """
        center = GISUtils.normalize_coordinates(center)
        circle_points = []

        for i in range(points):
            # Calculate bearing for this point
            bearing = (360.0 / points) * i
            bearing_rad = GISUtils.degrees_to_radians(bearing)

            # Calculate angular distance
            angular_distance = radius_km / DistanceCalculator.EARTH_RADIUS_KM

            # Calculate new coordinates
            center_lat_rad = GISUtils.degrees_to_radians(center["latitude"])
            center_lon_rad = GISUtils.degrees_to_radians(center["longitude"])

            point_lat_rad = math.asin(
                math.sin(center_lat_rad) * math.cos(angular_distance)
                + math.cos(center_lat_rad)
                * math.sin(angular_distance)
                * math.cos(bearing_rad)
            )

            point_lon_rad = center_lon_rad + math.atan2(
                math.sin(bearing_rad)
                * math.sin(angular_distance)
                * math.cos(center_lat_rad),
                math.cos(angular_distance)
                - math.sin(center_lat_rad) * math.sin(point_lat_rad),
            )

            circle_points.append(
                {
                    "latitude": GISUtils.radians_to_degrees(point_lat_rad),
                    "longitude": GISUtils.radians_to_degrees(point_lon_rad),
                }
            )

        return circle_points
