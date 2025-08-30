"""Exception hierarchy for DotMac Network Visualization package."""


class NetworkVisualizationError(Exception):
    """Base exception for network visualization package."""

    pass


class TopologyError(NetworkVisualizationError):
    """Exception for topology-related errors."""

    pass


class GraphError(NetworkVisualizationError):
    """Exception for graph processing errors."""

    pass


class GISError(NetworkVisualizationError):
    """Exception for GIS and coordinate system errors."""

    pass


class VisualizationError(NetworkVisualizationError):
    """Exception for visualization rendering errors."""

    pass


class NetworkXError(NetworkVisualizationError):
    """Exception for NetworkX integration errors."""

    pass


class CacheError(NetworkVisualizationError):
    """Exception for caching-related errors."""

    pass


class TenantError(NetworkVisualizationError):
    """Exception for tenant isolation errors."""

    pass
