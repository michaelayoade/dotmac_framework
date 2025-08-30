"""DotMac Network Visualization Package

A comprehensive network topology mapping and visualization framework with GIS integration,
NetworkX graph processing, and interactive network representation tools.

This package provides:
- Graph-based network topology representation
- NetworkX integration for advanced graph algorithms
- GIS coordinate-based distance calculations
- Network resilience and critical infrastructure analysis
- Visual network representation tools
- Multi-tenant network topology management
"""

from .core.graph_topology import (
    AdvancedNetworkTopology,
    GraphAlgorithms,
    GraphEdge,
    GraphNode,
    GraphTopologySDK,
    NetworkGraph,
)
from .core.networkx_topology import NetworkXTopologyManager, NetworkXTopologySDK
from .exceptions import GISError, GraphError, NetworkVisualizationError, TopologyError
from .gis.coordinate_utils import CoordinateSystem, DistanceCalculator, GISUtils
from .visualization.network_renderer import NetworkRenderer, TopologyVisualizer

__version__ = "0.1.0"

__all__ = [
    # Core topology
    "GraphNode",
    "GraphEdge",
    "NetworkGraph",
    "GraphAlgorithms",
    "AdvancedNetworkTopology",
    "GraphTopologySDK",
    # NetworkX integration
    "NetworkXTopologyManager",
    "NetworkXTopologySDK",
    # Visualization
    "NetworkRenderer",
    "TopologyVisualizer",
    # GIS utilities
    "CoordinateSystem",
    "GISUtils",
    "DistanceCalculator",
    # Exceptions
    "NetworkVisualizationError",
    "TopologyError",
    "GraphError",
    "GISError",
]
