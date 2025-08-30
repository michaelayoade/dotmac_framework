"""Graph Topology SDK - Advanced network analysis using custom graph implementation."""

import math
from collections import defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from ..exceptions import GraphError, TopologyError


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class GraphNode:
    """Represents a network node with attributes."""

    def __init__(self, node_id: str, **attributes):
        """Initialize graph node."""
        self.node_id = node_id
        self.attributes = attributes
        self.neighbors: Set[str] = set()

    def add_neighbor(self, neighbor_id: str):
        """Add neighbor to this node."""
        self.neighbors.add(neighbor_id)

    def remove_neighbor(self, neighbor_id: str):
        """Remove neighbor from this node."""
        self.neighbors.discard(neighbor_id)


class GraphEdge:
    """Represents a network link with properties."""

    def __init__(self, source: str, target: str, **attributes):
        """Initialize graph edge."""
        self.source = source
        self.target = target
        self.attributes = attributes

    def get_other_node(self, node_id: str) -> str:
        """Get the other end of the edge."""
        if node_id == self.source:
            return self.target
        elif node_id == self.target:
            return self.source
        else:
            raise GraphError(f"Node {node_id} not part of this edge")


class NetworkGraph:
    """Custom graph implementation for network topology."""

    def __init__(self, directed: bool = False):
        """Initialize network graph."""
        self.directed = directed
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[Tuple[str, str], GraphEdge] = {}
        self._node_edges: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    def add_node(self, node_id: str, **attributes):
        """Add node to graph."""
        if node_id not in self.nodes:
            self.nodes[node_id] = GraphNode(node_id, **attributes)
            self._node_edges[node_id] = []

    def add_edge(self, source: str, target: str, **attributes):
        """Add edge to graph."""
        # Ensure nodes exist
        self.add_node(source)
        self.add_node(target)

        # Add edge
        edge_key = (source, target)
        self.edges[edge_key] = GraphEdge(source, target, **attributes)

        # Update node relationships
        self.nodes[source].add_neighbor(target)
        self._node_edges[source].append(edge_key)

        if not self.directed:
            self.nodes[target].add_neighbor(source)
            self._node_edges[target].append(edge_key)

    def remove_node(self, node_id: str):
        """Remove node and all its edges."""
        if node_id not in self.nodes:
            return

        # Remove all edges connected to this node
        edges_to_remove = self._node_edges[node_id].copy()
        for edge_key in edges_to_remove:
            self.remove_edge(*edge_key)

        # Remove the node
        del self.nodes[node_id]
        del self._node_edges[node_id]

    def remove_edge(self, source: str, target: str):
        """Remove edge from graph."""
        edge_key = (source, target)
        if edge_key in self.edges:
            del self.edges[edge_key]

            # Update node relationships
            if source in self.nodes:
                self.nodes[source].remove_neighbor(target)
                self._node_edges[source] = [
                    e for e in self._node_edges[source] if e != edge_key
                ]

            if not self.directed and target in self.nodes:
                self.nodes[target].remove_neighbor(source)
                self._node_edges[target] = [
                    e for e in self._node_edges[target] if e != edge_key
                ]

    def get_neighbors(self, node_id: str) -> List[str]:
        """Get all neighbors of a node."""
        if node_id not in self.nodes:
            return []
        return list(self.nodes[node_id].neighbors)

    def get_edge_data(self, source: str, target: str) -> Optional[Dict[str, Any]]:
        """Get edge attributes."""
        edge_key = (source, target)
        if edge_key in self.edges:
            return self.edges[edge_key].attributes
        return None

    def copy(self) -> "NetworkGraph":
        """Create a copy of the graph."""
        new_graph = NetworkGraph(directed=self.directed)

        # Copy nodes
        for node_id, node in self.nodes.items():
            new_graph.add_node(node_id, **node.attributes)

        # Copy edges
        for edge_key, edge in self.edges.items():
            new_graph.add_edge(edge.source, edge.target, **edge.attributes)

        return new_graph


class GraphAlgorithms:
    """Network analysis algorithms."""

    @staticmethod
    def shortest_path(graph: NetworkGraph, source: str, target: str) -> List[str]:
        """Find shortest path using BFS."""
        if source not in graph.nodes or target not in graph.nodes:
            return []

        if source == target:
            return [source]

        queue = deque([(source, [source])])
        visited = {source}

        while queue:
            current, path = queue.popleft()

            for neighbor in graph.get_neighbors(current):
                if neighbor not in visited:
                    new_path = path + [neighbor]

                    if neighbor == target:
                        return new_path

                    visited.add(neighbor)
                    queue.append((neighbor, new_path))

        return []  # No path found

    @staticmethod
    def all_simple_paths(
        graph: NetworkGraph, source: str, target: str, max_length: int = 10
    ) -> List[List[str]]:
        """Find all simple paths between two nodes."""
        if source not in graph.nodes or target not in graph.nodes:
            return []

        if source == target:
            return [[source]]

        paths = []

        def dfs(current: str, path: List[str], visited: Set[str]):
            """Depth-first search for all paths."""
            if len(path) > max_length:
                return

            if current == target:
                paths.append(path[:])
                return

            for neighbor in graph.get_neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    path.append(neighbor)
                    dfs(neighbor, path, visited)
                    path.pop()
                    visited.remove(neighbor)

        dfs(source, [source], {source})
        return paths

    @staticmethod
    def connected_components(graph: NetworkGraph) -> List[Set[str]]:
        """Find all connected components."""
        visited = set()
        components = []

        for node_id in graph.nodes:
            if node_id not in visited:
                component = set()
                stack = [node_id]

                while stack:
                    current = stack.pop()
                    if current not in visited:
                        visited.add(current)
                        component.add(current)

                        for neighbor in graph.get_neighbors(current):
                            if neighbor not in visited:
                                stack.append(neighbor)

                components.append(component)

        return components

    @staticmethod
    def articulation_points(graph: NetworkGraph) -> List[str]:
        """Find articulation points (nodes whose removal disconnects the graph)."""
        if len(graph.nodes) <= 1:
            return []

        articulation_points = []

        for node_id in graph.nodes:
            # Create graph without this node
            temp_graph = graph.copy()
            temp_graph.remove_node(node_id)

            # Check if graph becomes disconnected
            original_components = len(GraphAlgorithms.connected_components(graph))
            new_components = len(GraphAlgorithms.connected_components(temp_graph))

            if new_components > original_components:
                articulation_points.append(node_id)

        return articulation_points

    @staticmethod
    def bridges(graph: NetworkGraph) -> List[Tuple[str, str]]:
        """Find bridge edges (edges whose removal disconnects the graph)."""
        bridges = []

        for edge_key in graph.edges:
            source, target = edge_key

            # Create graph without this edge
            temp_graph = graph.copy()
            temp_graph.remove_edge(source, target)

            # Check if graph becomes disconnected
            original_components = len(GraphAlgorithms.connected_components(graph))
            new_components = len(GraphAlgorithms.connected_components(temp_graph))

            if new_components > original_components:
                bridges.append(edge_key)

        return bridges

    @staticmethod
    def clustering_coefficient(graph: NetworkGraph) -> float:
        """Calculate average clustering coefficient."""
        if len(graph.nodes) < 3:
            return 0.0

        total_clustering = 0.0

        for node_id in graph.nodes:
            neighbors = graph.get_neighbors(node_id)
            if len(neighbors) < 2:
                continue

            # Count triangles
            triangles = 0
            possible_triangles = len(neighbors) * (len(neighbors) - 1) // 2

            for i, neighbor1 in enumerate(neighbors):
                for neighbor2 in neighbors[i + 1 :]:
                    if neighbor2 in graph.get_neighbors(neighbor1):
                        triangles += 1

            if possible_triangles > 0:
                total_clustering += triangles / possible_triangles

        return total_clustering / len(graph.nodes)

    @staticmethod
    def diameter(graph: NetworkGraph) -> int:
        """Calculate graph diameter (longest shortest path)."""
        components = GraphAlgorithms.connected_components(graph)
        if len(components) > 1:
            return float("inf")  # Disconnected graph

        max_distance = 0
        nodes = list(graph.nodes.keys())

        for i, source in enumerate(nodes):
            for target in nodes[i + 1 :]:
                path = GraphAlgorithms.shortest_path(graph, source, target)
                if path:
                    max_distance = max(max_distance, len(path) - 1)

        return max_distance


class AdvancedNetworkTopology:
    """Advanced network topology management with graph algorithms."""

    def __init__(self):
        """Initialize advanced topology manager."""
        self.graph = NetworkGraph()
        self.device_attributes: Dict[str, Dict[str, Any]] = {}
        self.link_attributes: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.topology_history: List[Dict[str, Any]] = []

    async def add_network_device(
        self, device_id: str, device_type: str, **attributes
    ) -> Dict[str, Any]:
        """Add network device to topology."""
        device_data = {
            "device_id": device_id,
            "device_type": device_type,
            "added_at": utc_now().isoformat(),
            **attributes,
        }

        self.graph.add_node(device_id, **device_data)
        self.device_attributes[device_id] = device_data

        self._log_topology_change("device_added", **device_data)

        return device_data

    async def add_network_link(
        self, device1: str, device2: str, **link_attributes
    ) -> Dict[str, Any]:
        """Add network link between devices."""
        if device1 not in self.graph.nodes or device2 not in self.graph.nodes:
            raise TopologyError("Both devices must exist before creating link")

        link_data = {
            "source": device1,
            "target": device2,
            "added_at": utc_now().isoformat(),
            **link_attributes,
        }

        # Add edge to graph (don't include source/target in attributes as they are parameters)
        edge_attributes = {
            k: v for k, v in link_data.items() if k not in ["source", "target"]
        }
        self.graph.add_edge(device1, device2, **edge_attributes)
        self.link_attributes[(device1, device2)] = link_data

        self._log_topology_change("link_added", **link_data)

        return link_data

    async def find_shortest_path(self, source: str, target: str) -> List[str]:
        """Find shortest path between devices."""
        return GraphAlgorithms.shortest_path(self.graph, source, target)

    async def analyze_network_reliability(self) -> Dict[str, Any]:
        """Comprehensive network reliability analysis."""
        components = GraphAlgorithms.connected_components(self.graph)
        clustering = GraphAlgorithms.clustering_coefficient(self.graph)
        diameter = GraphAlgorithms.diameter(self.graph)

        return {
            "total_devices": len(self.graph.nodes),
            "total_links": len(self.graph.edges),
            "connected_components": len(components),
            "is_fully_connected": len(components) == 1,
            "diameter": diameter,
            "clustering_coefficient": clustering,
            "density": (
                len(self.graph.edges)
                / (len(self.graph.nodes) * (len(self.graph.nodes) - 1) / 2)
                if len(self.graph.nodes) > 1
                else 0
            ),
            "analyzed_at": utc_now().isoformat(),
        }

    def _calculate_distance(
        self, location1: Dict[str, float], location2: Dict[str, float]
    ) -> float:
        """Calculate distance between two locations using Haversine formula."""
        lat1 = location1.get("latitude", 0)
        lon1 = location1.get("longitude", 0)
        lat2 = location2.get("latitude", 0)
        lon2 = location2.get("longitude", 0)

        # Convert to radians
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)

        # Haversine formula
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad

        a = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
        )
        c = 2 * math.asin(math.sqrt(a))

        # Earth radius in kilometers
        r = 6371

        return r * c

    def _log_topology_change(self, change_type: str, **details):
        """Log topology changes for history tracking."""
        change_record = {
            "change_id": str(uuid4()),
            "change_type": change_type,
            "timestamp": utc_now().isoformat(),
            "details": details,
        }

        self.topology_history.append(change_record)

        # Keep only last 1000 changes
        if len(self.topology_history) > 1000:
            self.topology_history = self.topology_history[-1000:]


class GraphTopologySDK:
    """Main SDK for advanced network topology management."""

    def __init__(self, tenant_id: str):
        """Initialize topology SDK."""
        self.tenant_id = tenant_id
        self.topology = AdvancedNetworkTopology()

    async def add_device(
        self, device_id: str, device_type: str, **attributes
    ) -> Dict[str, Any]:
        """Add network device to topology."""
        return await self.topology.add_network_device(
            device_id, device_type, tenant_id=self.tenant_id, **attributes
        )

    async def add_link(
        self, device1: str, device2: str, **attributes
    ) -> Dict[str, Any]:
        """Add network link."""
        return await self.topology.add_network_link(device1, device2, **attributes)

    async def get_network_health(self) -> Dict[str, Any]:
        """Get comprehensive network health assessment."""
        reliability = await self.topology.analyze_network_reliability()

        # Calculate overall health score
        health_score = 100.0

        # Deduct for network partitions
        if not reliability["is_fully_connected"]:
            health_score -= 30

        health_score = max(health_score, 0)

        return {
            "health_score": health_score,
            "health_status": (
                "excellent"
                if health_score >= 90
                else (
                    "good"
                    if health_score >= 70
                    else "fair" if health_score >= 50 else "poor"
                )
            ),
            "reliability_metrics": reliability,
            "assessment_time": utc_now().isoformat(),
        }
