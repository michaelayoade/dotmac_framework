# DotMac Network Visualization Package

A comprehensive network topology mapping and visualization framework with GIS integration, NetworkX graph processing, and interactive network representation tools.

## Overview

This package provides powerful tools for visualizing and analyzing network topologies in ISP and telecommunications environments. It combines custom graph algorithms with NetworkX integration, GIS coordinate utilities, and flexible visualization rendering.

## Features

### Core Graph Topology

- **Custom Graph Implementation**: High-performance graph data structures without external dependencies
- **Network Analysis Algorithms**: Shortest paths, connected components, articulation points, bridges
- **Clustering and Connectivity Metrics**: Network density, clustering coefficient, diameter calculations
- **Multi-tenant Support**: Tenant isolation and context management

### NetworkX Integration

- **Production-Ready Analysis**: Leverages NetworkX's advanced graph algorithms
- **Centrality Metrics**: Betweenness, closeness, degree, and eigenvector centrality
- **Network Resilience Analysis**: Connectivity scoring and critical infrastructure identification
- **Performance Caching**: Intelligent caching for expensive computations
- **Export Capabilities**: JSON and GEXF format support

### GIS Integration

- **Coordinate Systems**: WGS84, UTM, Mercator coordinate support
- **Distance Calculations**: Haversine formula for accurate geographic distances
- **Coverage Analysis**: Calculate coverage areas for wireless devices
- **Geographic Utilities**: Bearing calculation, midpoint finding, coordinate validation

### Visualization Rendering

- **Multiple Output Formats**: JSON, D3.js, Cytoscape.js formats
- **Geographic Layouts**: Map-based network visualization with bounds calculation
- **Path Visualization**: Multi-path route visualization with distance metrics
- **Coverage Visualization**: Wireless device coverage area rendering
- **Interactive Elements**: Node and edge styling based on device types

## Installation

The package is integrated into the DotMac Framework Poetry configuration:

```bash
# Install full DotMac framework (includes network visualization)
poetry install

# Or install with NetworkX for advanced features
poetry install --extras networkx
```

## Quick Start

### Basic Graph Operations

```python
from dotmac_network_visualization import NetworkGraph, GraphAlgorithms

# Create network graph
graph = NetworkGraph()

# Add network devices
graph.add_node("router1", device_type="core_router", name="Main Router")
graph.add_node("switch1", device_type="access_switch", name="Access Switch")

# Add network links
graph.add_edge("router1", "switch1", link_type="fiber", bandwidth=1000)

# Find shortest path
path = GraphAlgorithms.shortest_path(graph, "router1", "switch1")
print(f"Path: {path}")  # Output: ['router1', 'switch1']

# Analyze network connectivity
components = GraphAlgorithms.connected_components(graph)
print(f"Connected components: {len(components)}")
```

### Advanced Topology Management

```python
import asyncio
from dotmac_network_visualization import GraphTopologySDK

async def main():
    # Create topology SDK with tenant context
    sdk = GraphTopologySDK("tenant-123")

    # Add devices with geographic coordinates
    await sdk.add_device(
        "router1", "core_router",
        name="Portland POP",
        latitude=45.5152, longitude=-122.6784
    )

    await sdk.add_device(
        "router2", "distribution_router",
        name="Seattle POP",
        latitude=47.6062, longitude=-122.3321
    )

    # Add fiber link
    await sdk.add_link("router1", "router2",
                      link_type="fiber", bandwidth=100000)

    # Get network health assessment
    health = await sdk.get_network_health()
    print(f"Health Score: {health['health_score']}")
    print(f"Status: {health['health_status']}")

asyncio.run(main())
```

### GIS Distance Calculations

```python
from dotmac_network_visualization import DistanceCalculator, GISUtils

# Calculate distance between cities
portland = {"latitude": 45.5152, "longitude": -122.6784}
seattle = {"latitude": 47.6062, "longitude": -122.3321}

distance = DistanceCalculator.haversine_distance(
    portland["latitude"], portland["longitude"],
    seattle["latitude"], seattle["longitude"]
)

print(f"Distance: {distance:.1f} km")  # ~235 km

# Find nearest locations
reference = portland
candidates = [
    {"id": "site1", "latitude": 45.6, "longitude": -122.7},
    {"id": "site2", "latitude": 45.4, "longitude": -122.5}
]

nearest = DistanceCalculator.find_nearest_locations(
    reference, candidates, max_distance=50, limit=3
)

for site in nearest:
    print(f"{site['id']}: {site['distance_km']:.1f} km away")
```

### Network Visualization

```python
from dotmac_network_visualization import NetworkRenderer, TopologyVisualizer

# Create renderer
renderer = NetworkRenderer()

# Render for web visualization
json_data = renderer.render_graph_json(graph, include_positions=True)

# Export for D3.js
d3_data = renderer.render_d3_format(graph)

# Export for Cytoscape.js
cytoscape_data = renderer.render_cytoscape_format(graph)

# Create geographic visualization
visualizer = TopologyVisualizer()
geo_layout = visualizer.create_geographic_layout(graph)

# Visualize coverage areas
wireless_devices = [
    {"id": "ap1", "device_type": "wifi_ap",
     "latitude": 45.5, "longitude": -122.6, "coverage_radius_km": 0.5}
]

coverage_viz = visualizer.create_coverage_visualization(wireless_devices)
```

### NetworkX Integration

```python
from dotmac_network_visualization import NetworkXTopologySDK

async def networkx_analysis():
    sdk = NetworkXTopologySDK("tenant-456")

    # Build network
    await sdk.add_device("core1", "core_router")
    await sdk.add_device("dist1", "distribution_router")
    await sdk.add_device("access1", "access_switch")

    await sdk.add_link("core1", "dist1")
    await sdk.add_link("dist1", "access1")

    # Get comprehensive analysis
    analysis = await sdk.get_network_analysis()

    metrics = analysis["network_metrics"]
    print(f"Network density: {metrics['basic_stats']['density']:.3f}")
    print(f"Average clustering: {metrics['clustering']['average_clustering']:.3f}")

    # Critical infrastructure
    critical = analysis["critical_infrastructure"]["critical_nodes"]
    for node in critical[:3]:  # Top 3 critical nodes
        print(f"Critical: {node['device_id']} (score: {node['criticality_score']:.3f})")

asyncio.run(networkx_analysis())
```

## Architecture

### Package Structure

```
src/dotmac_network_visualization/
├── __init__.py              # Main package exports
├── core/                    # Core topology components
│   ├── graph_topology.py    # Custom graph implementation
│   └── networkx_topology.py # NetworkX integration
├── gis/                     # GIS utilities
│   └── coordinate_utils.py  # Distance and coordinate functions
├── visualization/           # Rendering components
│   └── network_renderer.py  # Multi-format rendering
├── exceptions.py            # Exception hierarchy
└── tests/                   # Test suite
    ├── test_graph_topology.py
    ├── test_networkx_topology.py
    ├── test_gis_utils.py
    ├── test_visualization.py
    └── test_integration.py
```

### Key Components

#### Graph Topology (Custom Implementation)

- **GraphNode**: Network device representation
- **GraphEdge**: Network link with properties
- **NetworkGraph**: Main graph container
- **GraphAlgorithms**: Analysis algorithms (BFS, DFS, connectivity)
- **AdvancedNetworkTopology**: High-level topology management
- **GraphTopologySDK**: Multi-tenant API wrapper

#### NetworkX Integration

- **NetworkXTopologyManager**: NetworkX-powered analysis
- **NetworkXTopologySDK**: Production-ready network analysis
- Advanced algorithms: centrality, clustering, resilience analysis
- Performance optimization with caching

#### GIS Utilities

- **CoordinateSystem**: Coordinate system enumerations
- **GISUtils**: Validation and coordinate transformations
- **DistanceCalculator**: Haversine distance calculations
- Coverage area calculations for wireless devices

#### Visualization

- **NetworkRenderer**: Multi-format graph rendering
- **TopologyVisualizer**: Geographic and coverage visualization
- Support for JSON, D3.js, Cytoscape.js formats

## Dependencies

### Required

- Python 3.12+
- Core Python libraries (math, collections, datetime, typing, uuid)

### Optional

- `networkx ^3.3`: Advanced graph algorithms and analysis
- `pytest ^7.4.4`: For running tests (development)

## Configuration

The package uses the DotMac Framework's unified configuration:

```python
# Access through framework config
from dotmac_isp.core.config import config

# Topology cache TTL
cache_ttl = config.topology_cache_ttl  # Default: 300 seconds

# Custom configuration
topology_config = {
    "cache_ttl": 600.0,
    "max_path_length": 10,
    "enable_geographic_calculations": True
}
```

## Error Handling

The package provides a structured exception hierarchy:

```python
from dotmac_network_visualization.exceptions import (
    NetworkVisualizationError,  # Base exception
    TopologyError,             # Topology management errors
    GraphError,                # Graph operation errors
    GISError,                  # Geographic calculation errors
    VisualizationError,        # Rendering errors
    NetworkXError,             # NetworkX integration errors
)

try:
    # Network operations
    pass
except TopologyError as e:
    print(f"Topology error: {e}")
except GISError as e:
    print(f"GIS calculation error: {e}")
```

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest src/dotmac_network_visualization/tests/ -v

# Run specific test categories
pytest src/dotmac_network_visualization/tests/test_graph_topology.py -v
pytest src/dotmac_network_visualization/tests/test_gis_utils.py -v
pytest src/dotmac_network_visualization/tests/test_visualization.py -v

# Run with coverage
pytest src/dotmac_network_visualization/tests/ --cov=src/dotmac_network_visualization

# Run integration tests
pytest src/dotmac_network_visualization/tests/test_integration.py -v
```

## Performance Considerations

### Graph Algorithms

- Custom implementation optimized for network topologies
- Efficient neighbor lookup using adjacency lists
- Memory-optimized edge storage

### NetworkX Integration

- Caching for expensive computations (centrality metrics)
- Size limits on intensive algorithms (eigenvector centrality: 100 nodes)
- Lazy evaluation of graph metrics

### GIS Calculations

- Haversine formula for accurate distance calculations
- Efficient coverage area computation using trigonometry
- Distance matrix optimization for multiple locations

### Visualization

- Lazy rendering - only compute positions when needed
- Format-specific optimizations (D3 uses indices, Cytoscape uses IDs)
- Memory-efficient large graph handling

## Integration with DotMac Framework

The Network Visualization Package integrates seamlessly with:

- **DotMac ISP Framework**: Network device and topology management
- **DotMac Management Platform**: Multi-tenant visualization dashboards
- **DotMac Shared Components**: Authentication, caching, observability
- **DotMac SDK Core**: HTTP client for external topology APIs

## Use Cases

### ISP Network Operations

- Physical network topology visualization
- Fiber route planning and optimization
- Critical infrastructure identification
- Network redundancy analysis

### Wireless Network Planning

- Coverage area visualization
- Site-to-site distance calculations
- Signal propagation modeling
- Interference analysis

### Network Monitoring

- Real-time topology status visualization
- Performance bottleneck identification
- Fault impact analysis
- Capacity planning visualization

### Geographic Network Analysis

- Multi-site connectivity planning
- Geographic redundancy assessment
- Disaster recovery route planning
- Regulatory compliance mapping

## Contributing

This package follows DotMac Framework development standards:

1. **Code Quality**: All code must pass linting (ruff, black, mypy)
2. **Testing**: Comprehensive test coverage for all features
3. **Documentation**: Clear docstrings and usage examples
4. **Type Safety**: Full type annotations using Python typing
5. **Performance**: Benchmark critical path operations

## License

MIT License - Part of the DotMac Framework ecosystem.

## Version History

- **v0.1.0**: Initial extraction from DotMac ISP Framework
  - Custom graph topology implementation
  - NetworkX integration with caching
  - GIS coordinate utilities
  - Multi-format visualization rendering
  - Comprehensive test suite
  - Geographic layout and coverage visualization
