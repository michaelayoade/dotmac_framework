"""
GIS Module Configuration - Integrates with DotMac settings system.
Follows existing configuration patterns for consistency.
"""

import os
from typing import Any, Optional

from dotmac_isp.core.settings import get_settings
from pydantic import BaseModel, Field


class GISConfig(BaseModel):
    """GIS module configuration following DotMac patterns."""

    # API Configuration
    api_base_url: str = Field(
        default="https://api.yourdomain.com",
        description="Base URL for external GIS APIs",
    )

    # Geocoding Services
    geocoding_provider: str = Field(
        default="nominatim",
        description="Geocoding service provider (nominatim, google, mapbox)",
    )
    google_maps_api_key: Optional[str] = Field(default=None, description="Google Maps API key for geocoding")
    mapbox_access_token: Optional[str] = Field(default=None, description="MapBox access token")

    # Coverage Analysis
    default_coverage_threshold: float = Field(
        default=95.0,
        ge=0.0,
        le=100.0,
        description="Default coverage threshold percentage",
    )

    # Route Optimization
    default_vehicle_speed_kmh: int = Field(
        default=60,
        ge=1,
        le=150,
        description="Default vehicle speed for route calculations",
    )

    service_time_per_stop_minutes: int = Field(default=30, ge=5, le=180, description="Default service time per stop")

    max_route_waypoints: int = Field(default=20, ge=2, le=100, description="Maximum waypoints per route optimization")

    # Caching Configuration
    topology_cache_ttl: int = Field(default=300, ge=60, le=3600, description="Topology data cache TTL in seconds")

    geocoding_cache_ttl: int = Field(
        default=86400,
        ge=3600,
        le=604800,
        description="Geocoding results cache TTL in seconds",
    )

    # Performance Limits
    max_coverage_analysis_area_km2: float = Field(
        default=1000.0,
        ge=1.0,
        le=10000.0,
        description="Maximum area for coverage analysis",
    )

    max_territory_area_km2: float = Field(default=5000.0, ge=1.0, le=50000.0, description="Maximum territory area")

    # Feature Flags
    enable_network_topology_integration: bool = Field(
        default=True, description="Enable integration with network topology module"
    )

    enable_advanced_coverage_analysis: bool = Field(default=True, description="Enable ML-powered coverage analysis")

    enable_real_time_geocoding: bool = Field(default=True, description="Enable real-time geocoding API calls")

    enable_route_optimization_caching: bool = Field(
        default=True, description="Enable caching of route optimization results"
    )

    # CDN Configuration for Map Assets
    map_tiles_cdn_url: str = Field(
        default="https://cdn.yourdomain.com/maps",
        description="CDN URL for map tiles and static assets",
    )

    marker_icons_cdn_url: str = Field(
        default="https://cdn.yourdomain.com/icons",
        description="CDN URL for map marker icons",
    )

    # Monitoring and Logging
    enable_performance_monitoring: bool = Field(
        default=True, description="Enable performance monitoring for GIS operations"
    )

    log_coverage_analyses: bool = Field(default=True, description="Log coverage analysis operations for audit")

    log_route_optimizations: bool = Field(default=False, description="Log route optimization requests")


def get_gis_config() -> GISConfig:
    """
    Get GIS configuration, integrating with DotMac settings system.
    Follows the same pattern as other DotMac modules.
    """
    # Get base DotMac settings
    get_settings()

    # Environment-specific overrides
    config_overrides = {}

    # API Configuration
    if os.getenv("GIS_API_BASE_URL"):
        config_overrides["api_base_url"] = os.getenv("GIS_API_BASE_URL")

    # Geocoding API Keys
    if os.getenv("GOOGLE_MAPS_API_KEY"):
        config_overrides["google_maps_api_key"] = os.getenv("GOOGLE_MAPS_API_KEY")

    if os.getenv("MAPBOX_ACCESS_TOKEN"):
        config_overrides["mapbox_access_token"] = os.getenv("MAPBOX_ACCESS_TOKEN")

    # Provider Selection
    if os.getenv("GEOCODING_PROVIDER"):
        config_overrides["geocoding_provider"] = os.getenv("GEOCODING_PROVIDER")

    # CDN Configuration
    if os.getenv("MAP_TILES_CDN_URL"):
        config_overrides["map_tiles_cdn_url"] = os.getenv("MAP_TILES_CDN_URL")

    if os.getenv("MARKER_ICONS_CDN_URL"):
        config_overrides["marker_icons_cdn_url"] = os.getenv("MARKER_ICONS_CDN_URL")

    # Performance and Feature Flags
    if os.getenv("MAX_COVERAGE_ANALYSIS_AREA") is not None:
        config_overrides["max_coverage_analysis_area_km2"] = float(os.getenv("MAX_COVERAGE_ANALYSIS_AREA"))

    if os.getenv("ENABLE_ADVANCED_COVERAGE_ANALYSIS") is not None:
        config_overrides["enable_advanced_coverage_analysis"] = (
            os.getenv("ENABLE_ADVANCED_COVERAGE_ANALYSIS").lower() == "true"
        )

    if os.getenv("ENABLE_REAL_TIME_GEOCODING") is not None:
        config_overrides["enable_real_time_geocoding"] = os.getenv("ENABLE_REAL_TIME_GEOCODING").lower() == "true"

    # Cache TTL Configuration
    if os.getenv("TOPOLOGY_CACHE_TTL"):
        config_overrides["topology_cache_ttl"] = int(os.getenv("TOPOLOGY_CACHE_TTL"))

    if os.getenv("GEOCODING_CACHE_TTL"):
        config_overrides["geocoding_cache_ttl"] = int(os.getenv("GEOCODING_CACHE_TTL"))

    return GISConfig(**config_overrides)


def get_environment_config() -> dict[str, Any]:
    """
    Get environment-specific GIS configuration.
    Returns configuration suitable for the current environment.
    """
    config = get_gis_config()
    base_settings = get_settings()

    # Production Configuration
    if base_settings.environment == "production":
        return {
            "api_base_url": config.api_base_url,
            "geocoding_provider": config.geocoding_provider,
            "enable_real_time_geocoding": config.enable_real_time_geocoding,
            "enable_performance_monitoring": True,
            "log_coverage_analyses": True,
            "log_route_optimizations": False,  # Reduce log volume in production
            "topology_cache_ttl": config.topology_cache_ttl,
            "geocoding_cache_ttl": config.geocoding_cache_ttl,
            "max_coverage_analysis_area_km2": config.max_coverage_analysis_area_km2,
            "map_tiles_cdn_url": config.map_tiles_cdn_url,
            "marker_icons_cdn_url": config.marker_icons_cdn_url,
        }

    # Development Configuration
    elif base_settings.environment == "development":
        return {
            "api_base_url": "http://localhost:8000",
            "geocoding_provider": "nominatim",  # Use free service for dev
            "enable_real_time_geocoding": False,  # Use cached/mock data
            "enable_performance_monitoring": True,
            "log_coverage_analyses": True,
            "log_route_optimizations": True,  # Verbose logging for dev
            "topology_cache_ttl": 60,  # Shorter cache for development
            "geocoding_cache_ttl": 3600,
            "max_coverage_analysis_area_km2": 100.0,  # Smaller limits for dev
            "map_tiles_cdn_url": "http://localhost:3000/maps",
            "marker_icons_cdn_url": "http://localhost:3000/icons",
        }

    # Testing Configuration
    else:
        return {
            "api_base_url": "http://test-api.local",
            "geocoding_provider": "mock",
            "enable_real_time_geocoding": False,  # Always use mock in tests
            "enable_performance_monitoring": False,
            "log_coverage_analyses": False,
            "log_route_optimizations": False,
            "topology_cache_ttl": 10,  # Very short cache for tests
            "geocoding_cache_ttl": 10,
            "max_coverage_analysis_area_km2": 10.0,  # Small limits for tests
            "map_tiles_cdn_url": "http://mock-cdn.local/maps",
            "marker_icons_cdn_url": "http://mock-cdn.local/icons",
        }


def validate_gis_configuration() -> bool:
    """
    Validate GIS module configuration.
    Returns True if configuration is valid, raises exception otherwise.
    """
    try:
        config = get_gis_config()

        # Validate required configuration based on provider
        if config.geocoding_provider == "google" and not config.google_maps_api_key:
            raise ValueError("Google Maps API key required when using Google geocoding")

        if config.geocoding_provider == "mapbox" and not config.mapbox_access_token:
            raise ValueError("MapBox access token required when using MapBox geocoding")

        # Validate CDN URLs are properly formatted
        if not config.map_tiles_cdn_url.startswith(("http://", "https://")):
            raise ValueError("Map tiles CDN URL must be a valid HTTP/HTTPS URL")

        if not config.marker_icons_cdn_url.startswith(("http://", "https://")):
            raise ValueError("Marker icons CDN URL must be a valid HTTP/HTTPS URL")

        return True

    except Exception as e:
        # Log configuration error for debugging
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"GIS configuration validation failed: {e}")
        raise


# Export configuration functions
__all__ = [
    "GISConfig",
    "get_gis_config",
    "get_environment_config",
    "validate_gis_configuration",
]
