"""
Graph Topology SDK - Advanced network analysis using NetworkX
"""

import math
import networkx as nx
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from ..core.datetime_utils import utc_now
from ..core.exceptions import TopologyError
from ..core.config import config


class GraphNode:
    """Represents a network node with attributes"""

    def __init__(self, node_id: str, **attributes):
        """  Init   operation."""
        self.node_id = node_id
        self.attributes = attributes
        self.neighbors: Set[str] = set()

    def add_neighbor(self, neighbor_id: str):
        """Add Neighbor operation."""
        self.neighbors.add(neighbor_id)

    def remove_neighbor(self, neighbor_id: str):
        """Remove Neighbor operation."""
        self.neighbors.discard(neighbor_id)


class GraphEdge:
    """Represents a network link with properties"""

    def __init__(self, source: str, target: str, **attributes):
        """  Init   operation."""
        self.source = source
        self.target = target
        self.attributes = attributes

    def get_other_node(self, node_id: str) -> str:
        """Get the other end of the edge"""
        if node_id == self.source:
            return self.target
        elif node_id == self.target:
            return self.source
        else:
            raise ValueError(f"Node {node_id} not part of this edge")


class NetworkGraph:
    """NetworkX-inspired graph implementation for network topology"""

    def __init__(self, directed: bool = False):
        """  Init   operation."""
        self.directed = directed
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: Dict[Tuple[str, str], GraphEdge] = {}
        self._node_edges: Dict[str, List[Tuple[str, str]]] = defaultdict(list)

    def add_node(self, node_id: str, **attributes):
        """Add node to graph"""
        if node_id not in self.nodes:
            self.nodes[node_id] = GraphNode(node_id, **attributes)
            self._node_edges[node_id] = []

    def add_edge(self, source: str, target: str, **attributes):
        """Add edge to graph"""
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
        """Remove node and all its edges"""
        if node_id not in self.nodes:
            return

        # Remove all edges connected to this node
        edges_to_remove = self._node_edges[node_id].model_copy()
        for edge_key in edges_to_remove:
            self.remove_edge(*edge_key)

        # Remove the node
        del self.nodes[node_id]
        del self._node_edges[node_id]

    def remove_edge(self, source: str, target: str):
        """Remove edge from graph"""
        edge_key = (source, target)
        if edge_key in self.edges:
            del self.edges[edge_key]

            # Update node relationships
            self.nodes[source].remove_neighbor(target)
            self._node_edges[source] = [
                e for e in self._node_edges[source] if e != edge_key
            ]

            if not self.directed:
                self.nodes[target].remove_neighbor(source)
                self._node_edges[target] = [
                    e for e in self._node_edges[target] if e != edge_key
                ]

    def get_neighbors(self, node_id: str) -> List[str]:
        """Get all neighbors of a node"""
        if node_id not in self.nodes:
            return []
        return list(self.nodes[node_id].neighbors)

    def get_edge_data(self, source: str, target: str) -> Optional[Dict[str, Any]]:
        """Get edge attributes"""
        edge_key = (source, target)
        if edge_key in self.edges:
            return self.edges[edge_key].attributes
        return None

    def copy(self) -> "NetworkGraph":
        """Create a copy of the graph"""
        new_graph = NetworkGraph(directed=self.directed)

        # Copy nodes
        for node_id, node in self.nodes.items():
            new_graph.add_node(node_id, **node.attributes)

        # Copy edges
        for edge_key, edge in self.edges.items():
            new_graph.add_edge(edge.source, edge.target, **edge.attributes)

        return new_graph


class GraphAlgorithms:
    """Network analysis algorithms inspired by NetworkX"""

    @staticmethod
    def shortest_path(graph: NetworkGraph, source: str, target: str) -> List[str]:
        """Find shortest path using BFS"""
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
                    queue.append((neighbor, new_path)

        return []  # No path found

    @staticmethod
    def all_simple_paths(
        graph: NetworkGraph, source: str, target: str, max_length: int = 10
    ) -> List[List[str]]:
        """Find all simple paths between two nodes"""
        if source not in graph.nodes or target not in graph.nodes:
            return []

        if source == target:
            return [[source]]

        paths = []

        def dfs(current: str, path: List[str], visited: Set[str]):
            """Dfs operation."""
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
        """Find all connected components"""
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
        """Find articulation points (nodes whose removal disconnects the graph)"""
        if len(graph.nodes) <= 1:
            return []

        articulation_points = []

        for node_id in graph.nodes:
            # Create graph without this node
            temp_graph = graph.model_copy()
            temp_graph.remove_node(node_id)

            # Check if graph becomes disconnected
            original_components = len(GraphAlgorithms.connected_components(graph)
            new_components = len(GraphAlgorithms.connected_components(temp_graph)

            if new_components > original_components:
                articulation_points.append(node_id)

        return articulation_points

    @staticmethod
    def bridges(graph: NetworkGraph) -> List[Tuple[str, str]]:
        """Find bridge edges (edges whose removal disconnects the graph)"""
        bridges = []

        for edge_key in graph.edges:
            source, target = edge_key

            # Create graph without this edge
            temp_graph = graph.model_copy()
            temp_graph.remove_edge(source, target)

            # Check if graph becomes disconnected
            original_components = len(GraphAlgorithms.connected_components(graph)
            new_components = len(GraphAlgorithms.connected_components(temp_graph)

            if new_components > original_components:
                bridges.append(edge_key)

        return bridges

    @staticmethod
    def node_connectivity(graph: NetworkGraph) -> int:
        """Calculate node connectivity (minimum nodes to remove to disconnect)"""
        if len(graph.nodes) <= 1:
            return 0

        components = GraphAlgorithms.connected_components(graph)
        if len(components) > 1:
            return 0  # Already disconnected

        # Find minimum cut
        min_connectivity = len(graph.nodes) - 1

        for node_id in graph.nodes:
            temp_graph = graph.model_copy()
            temp_graph.remove_node(node_id)

            new_components = GraphAlgorithms.connected_components(temp_graph)
            if len(new_components) > 1:
                min_connectivity = min(min_connectivity, 1)
            else:
                # Try removing additional nodes
                for second_node in temp_graph.nodes:
                    if second_node != node_id:
                        temp_graph2 = temp_graph.model_copy()
                        temp_graph2.remove_node(second_node)

                        components2 = GraphAlgorithms.connected_components(temp_graph2)
                        if len(components2) > 1:
                            min_connectivity = min(min_connectivity, 2)
                            break

        return min_connectivity

    @staticmethod
    def clustering_coefficient(graph: NetworkGraph) -> float:
        """Calculate average clustering coefficient"""
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
        """Calculate graph diameter (longest shortest path)"""
        components = GraphAlgorithms.connected_components(graph)
        if len(components) > 1:
            return float("inf")  # Disconnected graph

        max_distance = 0
        nodes = list(graph.nodes.keys()

        for i, source in enumerate(nodes):
            for target in nodes[i + 1 :]:
                path = GraphAlgorithms.shortest_path(graph, source, target)
                if path:
                    max_distance = max(max_distance, len(path) - 1)

        return max_distance


class AdvancedNetworkTopology:
    """Advanced network topology management with graph algorithms"""

    def __init__(self):
        """  Init   operation."""
        self.graph = NetworkGraph()
        self.device_attributes: Dict[str, Dict[str, Any]] = {}
        self.link_attributes: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.topology_history: List[Dict[str, Any]] = []

    async def add_network_device(
        self, device_id: str, device_type: str, **attributes
    ) -> Dict[str, Any]:
        """Add network device to topology"""

        device_data = {
            "device_id": device_id,
            "device_type": device_type,
            "added_at": utc_now().isoformat(),
            **attributes,
        }

        self.graph.add_node(device_id, **device_data)
        self.device_attributes[device_id] = device_data

        self._log_topology_change("device_added", device_id=device_id, **device_data)

        return device_data

    async def add_network_link(
        self, device1: str, device2: str, **link_attributes
    ) -> Dict[str, Any]:
        """Add network link between devices"""

        if device1 not in self.graph.nodes or device2 not in self.graph.nodes:
            raise TopologyError(f"Both devices must exist before creating link")

        link_data = {
            "source": device1,
            "target": device2,
            "added_at": utc_now().isoformat(),
            **link_attributes,
        }

        self.graph.add_edge(device1, device2, **link_data)
        self.link_attributes[(device1, device2)] = link_data

        self._log_topology_change(
            "link_added", source=device1, target=device2, **link_data
        )

        return link_data

    async def remove_network_device(self, device_id: str) -> Dict[str, Any]:
        """Remove device and all its links"""

        if device_id not in self.graph.nodes:
            raise TopologyError(f"Device not found: {device_id}")

        # Get connected devices before removal
        connected_devices = self.graph.get_neighbors(device_id)

        # Remove from graph
        self.graph.remove_node(device_id)

        # Clean up attributes
        device_data = self.device_attributes.pop(device_id, {})

        # Remove link attributes
        links_removed = []
        for link_key in list(self.link_attributes.keys():
            if device_id in link_key:
                links_removed.append(self.link_attributes.pop(link_key)

        self._log_topology_change(
            "device_removed",
            device_id=device_id,
            connected_devices=connected_devices,
            links_removed=len(links_removed),
        )

        return {
            "device_id": device_id,
            "connected_devices": connected_devices,
            "links_removed": len(links_removed),
            "removed_at": utc_now().isoformat(),
        }

    async def find_shortest_path(self, source: str, target: str) -> List[str]:
        """Find shortest path between devices"""
        return GraphAlgorithms.shortest_path(self.graph, source, target)

    async def find_all_paths(
        self, source: str, target: str, max_length: int = 10
    ) -> List[List[str]]:
        """Find all possible paths for redundancy analysis"""
        return GraphAlgorithms.all_simple_paths(self.graph, source, target, max_length)

    async def analyze_network_reliability(self) -> Dict[str, Any]:
        """Comprehensive network reliability analysis"""

        connectivity = GraphAlgorithms.node_connectivity(self.graph)
        components = GraphAlgorithms.connected_components(self.graph)
        clustering = GraphAlgorithms.clustering_coefficient(self.graph)
        diameter = GraphAlgorithms.diameter(self.graph)

        return {
            "total_devices": len(self.graph.nodes),
            "total_links": len(self.graph.edges),
            "connectivity": connectivity,
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

    async def identify_critical_devices(self) -> List[Dict[str, Any]]:
        """Find devices whose failure would partition the network"""

        articulation_points = GraphAlgorithms.articulation_points(self.graph)

        critical_devices = []
        for device_id in articulation_points:
            device_info = self.device_attributes.get(device_id, {})
            impact = await self.simulate_device_failure(device_id)

            critical_devices.append(
                {
                    "device_id": device_id,
                    "device_type": device_info.get("device_type", "unknown"),
                    "device_name": device_info.get("name", ""),
                    "connected_devices": len(self.graph.get_neighbors(device_id)),
                    "failure_impact": impact,
                    "criticality_score": self._calculate_criticality_score(
                        device_id, impact
                    ),
                }
            )

        return sorted(
            critical_devices, key=lambda x: x["criticality_score"], reverse=True
        )

    async def identify_critical_links(self) -> List[Dict[str, Any]]:
        """Find links whose failure would partition the network"""

        bridges = GraphAlgorithms.bridges(self.graph)

        critical_links = []
        for source, target in bridges:
            link_info = self.link_attributes.get((source, target), {})

            critical_links.append(
                {
                    "source": source,
                    "target": target,
                    "link_type": link_info.get("link_type", "unknown"),
                    "bandwidth": link_info.get("bandwidth", 0),
                    "utilization": link_info.get("utilization", 0),
                    "redundancy_available": len(
                        await self.find_all_paths(source, target, max_length=5)
                    )
                    > 1,
                }
            )

        return critical_links

    async def simulate_device_failure(self, device_id: str) -> Dict[str, Any]:
        """Simulate device failure and analyze impact"""

        if device_id not in self.graph.nodes:
            raise TopologyError(f"Device not found: {device_id}")

        # Create graph without the failed device
        temp_graph = self.graph.model_copy()
        connected_before = self.graph.get_neighbors(device_id)
        temp_graph.remove_node(device_id)

        # Analyze connectivity impact
        components = GraphAlgorithms.connected_components(temp_graph)

        isolated_devices = []
        for component in components:
            if len(component) == 1:
                isolated_devices.extend(component)

        # Find affected customer devices
        affected_customers = []
        for component in components:
            for node_id in component:
                node_data = self.device_attributes.get(node_id, {})
                if node_data.get("device_type") == "customer_cpe":
                    affected_customers.append(
                        {
                            "device_id": node_id,
                            "customer_id": node_data.get("customer_id"),
                            "service_type": node_data.get("service_type", "unknown"),
                        }
                    )

        return {
            "failed_device": device_id,
            "connected_before_failure": connected_before,
            "network_partitions": len(components),
            "isolated_devices": isolated_devices,
            "affected_customers": affected_customers,
            "total_affected_customers": len(affected_customers),
            "largest_partition_size": (
                max(len(comp) for comp in components) if components else 0
            ),
            "network_still_connected": len(components) <= 1,
            "simulation_time": utc_now().isoformat(),
        }

    async def optimize_network_paths(self) -> Dict[str, Any]:
        """Analyze and recommend network path optimizations"""

        optimization_recommendations = []

        # Find high-utilization links
        high_util_links = []
        for link_key, link_data in self.link_attributes.items():
            utilization = link_data.get("utilization", 0)
            capacity = link_data.get("capacity", 100)

            if capacity > 0 and utilization / capacity > 0.8:  # 80% threshold
                high_util_links.append(
                    {
                        "link": link_key,
                        "utilization": utilization,
                        "capacity": capacity,
                        "congestion_ratio": utilization / capacity,
                    }
                )

        # Find alternative paths for congested links
        for link_info in high_util_links:
            source, target = link_info["link"]
            alternative_paths = await self.find_all_paths(source, target, max_length=5)

            if len(alternative_paths) > 1:
                optimization_recommendations.append(
                    {
                        "congested_link": link_info["link"],
                        "congestion_ratio": link_info["congestion_ratio"],
                        "alternative_paths": alternative_paths[
                            1:
                        ],  # Exclude direct path
                        "recommendation": "Consider load balancing or traffic engineering",
                    }
                )
            else:
                optimization_recommendations.append(
                    {
                        "congested_link": link_info["link"],
                        "congestion_ratio": link_info["congestion_ratio"],
                        "alternative_paths": [],
                        "recommendation": "Consider capacity upgrade - no alternative paths available",
                    }
                )

        return {
            "high_utilization_links": high_util_links,
            "optimization_recommendations": optimization_recommendations,
            "total_optimizations_possible": len(
                [r for r in optimization_recommendations if r["alternative_paths"]]
            ),
            "analysis_completed": utc_now().isoformat(),
        }

    async def get_topology_stats(self) -> Dict[str, Any]:
        """Get comprehensive topology statistics"""

        device_types = {}
        for device_data in self.device_attributes.values():
            device_type = device_data.get("device_type", "unknown")
            device_types[device_type] = device_types.get(device_type, 0) + 1

        link_types = {}
        for link_data in self.link_attributes.values():
            link_type = link_data.get("link_type", "unknown")
            link_types[link_type] = link_types.get(link_type, 0) + 1

        reliability = await self.analyze_network_reliability()

        return {
            "topology_overview": {
                "total_devices": len(self.graph.nodes),
                "total_links": len(self.graph.edges),
                "device_types": device_types,
                "link_types": link_types,
            },
            "reliability_metrics": reliability,
            "topology_changes": len(self.topology_history),
            "last_change": (
                self.topology_history[-1]["timestamp"]
                if self.topology_history
                else None
            ),
            "stats_generated": utc_now().isoformat(),
        }

    def _calculate_criticality_score(
        self, device_id: str, failure_impact: Dict[str, Any]
    ) -> float:
        """Calculate device criticality score"""

        # Base score from connections
        connections = len(self.graph.get_neighbors(device_id)
        connection_score = min(connections / 10.0, 1.0)  # Normalize to 0-1

        # Impact score from failure simulation
        partitions = failure_impact.get("network_partitions", 1)
        customers_affected = failure_impact.get("total_affected_customers", 0)

        impact_score = min((partitions - 1) * 0.3 + customers_affected * 0.01, 1.0)

        # Device type importance
        device_data = self.device_attributes.get(device_id, {})
        device_type = device_data.get("device_type", "unknown")

        type_weights = {
            "core_router": 1.0,
            "distribution_router": 0.8,
            "access_switch": 0.6,
            "wifi_ap": 0.4,
            "customer_cpe": 0.2,
        }

        type_score = type_weights.get(device_type, 0.5)

        # Combined criticality score (0-1)
        return connection_score * 0.3 + impact_score * 0.5 + type_score * 0.2

    def _log_topology_change(self, change_type: str, **details):
        """Log topology changes for history tracking"""

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
    """Main SDK for advanced network topology management"""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.topology = AdvancedNetworkTopology()

    async def add_device(
        self, device_id: str, device_type: str, **attributes
    ) -> Dict[str, Any]:
        """Add network device to topology"""
        return await self.topology.add_network_device(
            device_id, device_type, tenant_id=self.tenant_id, **attributes
        )

    async def add_link(
        self, device1: str, device2: str, **attributes
    ) -> Dict[str, Any]:
        """Add network link"""
        return await self.topology.add_network_link(device1, device2, **attributes)

    async def get_network_health(self) -> Dict[str, Any]:
        """Get comprehensive network health assessment"""

        reliability = await self.topology.analyze_network_reliability()
        critical_devices = await self.topology.identify_critical_devices()
        critical_links = await self.topology.identify_critical_links()
        optimization = await self.topology.optimize_network_paths()

        # Calculate overall health score
        health_score = 100.0

        # Deduct for poor connectivity
        if reliability["connectivity"] < 2:
            health_score -= 20

        # Deduct for network partitions
        if not reliability["is_fully_connected"]:
            health_score -= 30

        # Deduct for high criticality
        if (
            len(critical_devices) > len(self.topology.graph.nodes) * 0.1
        ):  # More than 10% critical
            health_score -= 15

        # Deduct for congestion
        congested_links = len(optimization["high_utilization_links"])
        if congested_links > 0:
            health_score -= min(congested_links * 5, 25)

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
            "critical_devices": critical_devices[:5],  # Top 5 most critical
            "critical_links": critical_links[:5],  # Top 5 most critical
            "optimization_opportunities": len(
                optimization["optimization_recommendations"]
            ),
            "assessment_time": utc_now().isoformat(),
        }

    async def plan_network_expansion(
        self, new_sites: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Plan optimal network expansion"""

        expansion_recommendations = []

        for site in new_sites:
            site_id = site["site_id"]
            site_location = site.get("location", {})

            # Find best connection points in existing network
            connection_options = []

            for existing_device in self.topology.device_attributes:
                existing_data = self.topology.device_attributes[existing_device]
                existing_location = existing_data.get("location", {})

                # Calculate distance (simplified)
                distance = self._calculate_distance(site_location, existing_location)

                if distance <= site.get("max_connection_distance", 50):  # 50km default
                    # Analyze redundancy if connected to this device
                    redundancy_paths = await self.topology.find_all_paths(
                        site_id, existing_device, max_length=3
                    )

                    connection_options.append(
                        {
                            "target_device": existing_device,
                            "distance_km": distance,
                            "redundancy_paths": len(redundancy_paths),
                            "target_device_type": existing_data.get("device_type"),
                            "estimated_cost": distance * 1000,  # $1000 per km estimate
                        }
                    )

            # Sort by cost and redundancy
            connection_options.sort(
                key=lambda x: (x["estimated_cost"], -x["redundancy_paths"])
            )

            expansion_recommendations.append(
                {
                    "new_site": site_id,
                    "recommended_connections": connection_options[:3],  # Top 3 options
                    "total_options": len(connection_options),
                }
            )

        return {
            "expansion_plan": expansion_recommendations,
            "total_new_sites": len(new_sites),
            "planning_completed": utc_now().isoformat(),
        }

    def _calculate_distance(
        self, location1: Dict[str, float], location2: Dict[str, float]
    ) -> float:
        """Calculate distance between two locations (simplified)"""

        lat1 = location1.get("latitude", 0)
        lon1 = location1.get("longitude", 0)
        lat2 = location2.get("latitude", 0)
        lon2 = location2.get("longitude", 0)

        # Simplified distance calculation (not considering Earth curvature)
        lat_diff = lat2 - lat1
        lon_diff = lon2 - lon1

        return math.sqrt(lat_diff**2 + lon_diff**2) * 111  # Rough km conversion
