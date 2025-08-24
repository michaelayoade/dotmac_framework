"""
NetworkX-based Network Topology SDK - Production network analysis
"""

import networkx as nx
import math
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

from ..core.datetime_utils import utc_now
from ..core.exceptions import TopologyError
from ..core.config import config


class NetworkXTopologyManager:
    """NetworkX-powered network topology with advanced graph algorithms"""

    def __init__(self, directed: bool = False):
        """  Init   operation."""
        self.graph = nx.DiGraph() if directed else nx.Graph()
        self.device_attributes: Dict[str, Dict[str, Any]] = {}
        self.link_attributes: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.topology_history: List[Dict[str, Any]] = []
        self._cache_ttl = config.topology_cache_ttl
        self._cached_results = {}
        self._cache_timestamps = {}

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached result is still valid"""
        if cache_key not in self._cache_timestamps:
            return False

        import time

        return (time.time() - self._cache_timestamps[cache_key]) < self._cache_ttl

    def _cache_result(self, cache_key: str, result: Any):
        """Cache computation result"""
        import time

        self._cached_results[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()

    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if valid"""
        if self._is_cache_valid(cache_key):
            return self._cached_results.get(cache_key)
        return None

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

        # Add to NetworkX graph
        self.graph.add_node(device_id, **device_data)
        self.device_attributes[device_id] = device_data

        # Clear relevant caches
        self._cached_results.clear()
        self._cache_timestamps.clear()

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

        # Add to NetworkX graph with edge attributes
        self.graph.add_edge(device1, device2, **link_data)
        self.link_attributes[(device1, device2)] = link_data

        # Clear relevant caches
        self._cached_results.clear()
        self._cache_timestamps.clear()

        self._log_topology_change(
            "link_added", source=device1, target=device2, **link_data
        )

        return link_data

    async def remove_network_device(self, device_id: str) -> Dict[str, Any]:
        """Remove device and all its links"""

        if device_id not in self.graph.nodes:
            raise TopologyError(f"Device not found: {device_id}")

        # Get connected devices before removal
        connected_devices = list(self.graph.neighbors(device_id))

        # Remove from NetworkX graph
        self.graph.remove_node(device_id)

        # Clean up attributes
        device_data = self.device_attributes.pop(device_id, {})

        # Remove link attributes
        links_removed = []
        for link_key in list(self.link_attributes.keys()):
            if device_id in link_key:
                links_removed.append(self.link_attributes.pop(link_key))

        # Clear caches
        self._cached_results.clear()
        self._cache_timestamps.clear()

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

    async def find_shortest_path(
        self, source: str, target: str, weight: Optional[str] = None
    ) -> List[str]:
        """Find shortest path between devices using NetworkX"""

        cache_key = f"shortest_path_{source}_{target}_{weight}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            if weight:
                path = nx.shortest_path(self.graph, source, target, weight=weight)
            else:
                path = nx.shortest_path(self.graph, source, target)

            self._cache_result(cache_key, path)
            return path
        except nx.NetworkXNoPath:
            return []
        except nx.NodeNotFound:
            return []

    async def find_all_simple_paths(
        self, source: str, target: str, max_length: int = 10
    ) -> List[List[str]]:
        """Find all simple paths between devices"""

        cache_key = f"all_paths_{source}_{target}_{max_length}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            paths = list(
                nx.all_simple_paths(self.graph, source, target, cutoff=max_length)
            )
            self._cache_result(cache_key, paths)
            return paths
        except nx.NodeNotFound:
            return []

    async def calculate_network_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive network metrics using NetworkX"""

        cache_key = "network_metrics"
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result

        if self.graph.number_of_nodes() == 0:
            return {"error": "Empty graph"}

        metrics = {
            "basic_stats": {
                "total_nodes": self.graph.number_of_nodes(),
                "total_edges": self.graph.number_of_edges(),
                "density": nx.density(self.graph),
                "is_connected": (
                    nx.is_connected(self.graph)
                    if not self.graph.is_directed()
                    else nx.is_weakly_connected(self.graph)
                ),
            }
        }

        # Connectivity metrics
        if nx.is_connected(self.graph):
            metrics["connectivity"] = {
                "diameter": nx.diameter(self.graph),
                "radius": nx.radius(self.graph),
                "center": list(nx.center(self.graph)),
                "periphery": list(nx.periphery(self.graph)),
            }
        else:
            metrics["connectivity"] = {
                "connected_components": nx.number_connected_components(self.graph),
                "largest_component_size": len(
                    max(nx.connected_components(self.graph), key=len)
                ),
            }

        # Centrality metrics (for smaller graphs)
        if self.graph.number_of_nodes() <= 100:  # Limit for performance
            metrics["centrality"] = {
                "betweenness": dict(nx.betweenness_centrality(self.graph)),
                "closeness": dict(nx.closeness_centrality(self.graph)),
                "degree": dict(nx.degree_centrality(self.graph)),
                "eigenvector": dict(
                    nx.eigenvector_centrality(self.graph, max_iter=1000)
                ),
            }

        # Clustering metrics
        metrics["clustering"] = {
            "average_clustering": nx.average_clustering(self.graph),
            "transitivity": nx.transitivity(self.graph),
        }

        # Node degree statistics
        degrees = [d for n, d in self.graph.degree()]
        if degrees:
            metrics["degree_stats"] = {
                "average_degree": sum(degrees) / len(degrees),
                "max_degree": max(degrees),
                "min_degree": min(degrees),
                "degree_distribution": {
                    str(degree): degrees.count(degree) for degree in set(degrees)
                },
            }

        metrics["calculated_at"] = utc_now().isoformat()

        self._cache_result(cache_key, metrics)
        return metrics

    async def identify_critical_nodes(self) -> List[Dict[str, Any]]:
        """Identify critical nodes using NetworkX algorithms"""

        cache_key = "critical_nodes"
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result

        critical_nodes = []

        if self.graph.number_of_nodes() == 0:
            return critical_nodes

        # Articulation points (cut vertices)
        articulation_points = set()
        if nx.is_connected(self.graph):
            articulation_points = set(nx.articulation_points(self.graph))

        # Calculate centrality scores for all nodes
        try:
            betweenness_centrality = nx.betweenness_centrality(self.graph)
            degree_centrality = nx.degree_centrality(self.graph)
        except:
            betweenness_centrality = {}
            degree_centrality = {}

        for node_id in self.graph.nodes():
            node_data = self.device_attributes.get(node_id, {})

            # Calculate criticality score
            is_articulation = node_id in articulation_points
            betweenness = betweenness_centrality.get(node_id, 0)
            degree = degree_centrality.get(node_id, 0)

            # Weighted criticality score
            criticality_score = (
                (1.0 if is_articulation else 0.0) * 0.5
                + betweenness * 0.3
                + degree * 0.2
            )

            if (
                criticality_score > 0.1
            ):  # Only include nodes with significant criticality
                critical_nodes.append(
                    {
                        "device_id": node_id,
                        "device_type": node_data.get("device_type", "unknown"),
                        "device_name": node_data.get("name", ""),
                        "is_articulation_point": is_articulation,
                        "betweenness_centrality": betweenness,
                        "degree_centrality": degree,
                        "degree": self.graph.degree(node_id),
                        "criticality_score": criticality_score,
                    }
                )

        # Sort by criticality score
        critical_nodes.sort(key=lambda x: x["criticality_score"], reverse=True)

        self._cache_result(cache_key, critical_nodes)
        return critical_nodes

    async def identify_critical_edges(self) -> List[Dict[str, Any]]:
        """Identify critical edges (bridges) using NetworkX"""

        cache_key = "critical_edges"
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result

        critical_edges = []

        if self.graph.number_of_edges() == 0:
            return critical_edges

        # Find bridge edges
        bridges = set()
        if nx.is_connected(self.graph):
            bridges = set(nx.bridges(self.graph))

        for edge in bridges:
            source, target = edge
            edge_data = self.graph.get_edge_data(source, target, {})

            critical_edges.append(
                {
                    "source": source,
                    "target": target,
                    "link_type": edge_data.get("link_type", "unknown"),
                    "bandwidth": edge_data.get("bandwidth", 0),
                    "utilization": edge_data.get("utilization", 0),
                    "is_bridge": True,
                    "edge_betweenness": self._calculate_edge_betweenness(
                        source, target
                    ),
                }
            )

        self._cache_result(cache_key, critical_edges)
        return critical_edges

    async def simulate_node_failure(self, node_id: str) -> Dict[str, Any]:
        """Simulate node failure and analyze impact"""

        if node_id not in self.graph.nodes():
            raise TopologyError(f"Node not found: {node_id}")

        # Create a copy of the graph without the failed node
        temp_graph = self.graph.copy()
        connected_before = list(self.graph.neighbors(node_id))
        temp_graph.remove_node(node_id)

        # Analyze impact
        if temp_graph.number_of_nodes() == 0:
            return {
                "failed_node": node_id,
                "total_impact": "complete_network_failure",
                "connected_components": 0,
                "largest_component_size": 0,
            }

        # Find connected components after failure
        if temp_graph.is_directed():
            components = list(nx.weakly_connected_components(temp_graph))
        else:
            components = list(nx.connected_components(temp_graph))

        # Find affected customers
        affected_customers = []
        isolated_nodes = []

        for component in components:
            if len(component) == 1:
                isolated_nodes.extend(component)

            for node in component:
                node_data = self.device_attributes.get(node, {})
                if node_data.get("device_type") == "customer_cpe":
                    affected_customers.append(
                        {
                            "device_id": node,
                            "customer_id": node_data.get("customer_id"),
                            "service_type": node_data.get("service_type", "unknown"),
                        }
                    )

        return {
            "failed_node": node_id,
            "connected_before_failure": connected_before,
            "network_partitions": len(components),
            "isolated_nodes": isolated_nodes,
            "affected_customers": affected_customers,
            "total_affected_customers": len(affected_customers),
            "largest_partition_size": (
                max(len(comp) for comp in components) if components else 0
            ),
            "network_still_connected": len(components) <= 1,
            "connectivity_impact": self._calculate_connectivity_impact(temp_graph),
            "simulation_time": utc_now().isoformat(),
        }

    async def find_redundant_paths(
        self, source: str, target: str, k: int = 3
    ) -> List[List[str]]:
        """Find k shortest (disjoint) paths for redundancy analysis"""

        cache_key = f"redundant_paths_{source}_{target}_{k}"
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result

        try:
            # For NetworkX 2.8+, use k_shortest_paths
            if hasattr(nx, "shortest_simple_paths"):
                paths = list(nx.shortest_simple_paths(self.graph, source, target))[:k]
            else:
                # Fallback to all_simple_paths with limited results
                all_paths = list(
                    nx.all_simple_paths(self.graph, source, target, cutoff=10)
                )
                # Sort by length and take k shortest
                all_paths.sort(key=len)
                paths = all_paths[:k]

            self._cache_result(cache_key, paths)
            return paths
        except nx.NetworkXNoPath:
            return []
        except nx.NodeNotFound:
            return []

    async def analyze_network_resilience(self) -> Dict[str, Any]:
        """Comprehensive network resilience analysis"""

        cache_key = "network_resilience"
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result

        resilience_analysis = {
            "overall_score": 0.0,
            "connectivity_resilience": {},
            "redundancy_analysis": {},
            "critical_infrastructure": {},
            "recommendations": [],
        }

        if self.graph.number_of_nodes() == 0:
            return resilience_analysis

        # Connectivity resilience
        if nx.is_connected(self.graph):
            try:
                node_connectivity = nx.node_connectivity(self.graph)
                edge_connectivity = nx.edge_connectivity(self.graph)

                resilience_analysis["connectivity_resilience"] = {
                    "node_connectivity": node_connectivity,
                    "edge_connectivity": edge_connectivity,
                    "connectivity_score": min(node_connectivity / 3.0, 1.0) * 0.3
                    + min(edge_connectivity / 3.0, 1.0) * 0.2,
                }
            except:
                resilience_analysis["connectivity_resilience"] = {
                    "node_connectivity": 0,
                    "edge_connectivity": 0,
                    "connectivity_score": 0.0,
                }
        else:
            resilience_analysis["connectivity_resilience"] = {
                "is_connected": False,
                "connectivity_score": 0.0,
            }

        # Redundancy analysis
        critical_nodes = await self.identify_critical_nodes()
        critical_edges = await self.identify_critical_edges()

        resilience_analysis["critical_infrastructure"] = {
            "critical_nodes_count": len(critical_nodes),
            "critical_edges_count": len(critical_edges),
            "critical_nodes": critical_nodes[:5],  # Top 5
            "critical_edges": critical_edges[:5],  # Top 5
        }

        # Calculate overall resilience score
        connectivity_score = resilience_analysis["connectivity_resilience"].get(
            "connectivity_score", 0.0
        )
        critical_ratio = (len(critical_nodes) + len(critical_edges)) / (
            self.graph.number_of_nodes() + self.graph.number_of_edges()
        )
        redundancy_score = max(0.0, 1.0 - critical_ratio)

        overall_score = connectivity_score * 0.6 + redundancy_score * 0.4
        resilience_analysis["overall_score"] = overall_score

        # Generate recommendations
        if overall_score < 0.5:
            resilience_analysis["recommendations"].append(
                "Network resilience is poor - consider adding redundant links"
            )
        if len(critical_nodes) > self.graph.number_of_nodes() * 0.2:
            resilience_analysis["recommendations"].append(
                "Too many critical nodes - distribute network functions"
            )
        if not nx.is_connected(self.graph):
            resilience_analysis["recommendations"].append(
                "Network is not fully connected - add bridging links"
            )

        resilience_analysis["analyzed_at"] = utc_now().isoformat()

        self._cache_result(cache_key, resilience_analysis)
        return resilience_analysis

    def _calculate_edge_betweenness(self, source: str, target: str) -> float:
        """Calculate edge betweenness centrality for a specific edge"""
        try:
            edge_betweenness = nx.edge_betweenness_centrality(self.graph)
            return edge_betweenness.get((source, target), 0.0)
        except:
            return 0.0

    def _calculate_connectivity_impact(self, temp_graph) -> Dict[str, Any]:
        """Calculate the impact on network connectivity"""
        if temp_graph.number_of_nodes() == 0:
            return {"impact": "total_failure"}

        original_connected = (
            nx.is_connected(self.graph)
            if not self.graph.is_directed()
            else nx.is_weakly_connected(self.graph)
        )
        new_connected = (
            nx.is_connected(temp_graph)
            if not temp_graph.is_directed()
            else nx.is_weakly_connected(temp_graph)
        )

        impact = {
            "connectivity_lost": original_connected and not new_connected,
            "components_before": (
                1 if original_connected else nx.number_connected_components(self.graph)
            ),
            "components_after": (
                nx.number_connected_components(temp_graph)
                if not temp_graph.is_directed()
                else nx.number_weakly_connected_components(temp_graph)
            ),
        }

        return impact

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

    async def export_graph_data(self, format: str = "json") -> Dict[str, Any]:
        """Export graph data in various formats"""

        if format == "json":
            return {
                "nodes": [
                    {"id": node, **self.graph.nodes[node]}
                    for node in self.graph.nodes()
                ],
                "edges": [
                    {"source": edge[0], "target": edge[1], **self.graph.edges[edge]}
                    for edge in self.graph.edges()
                ],
                "graph_stats": await self.calculate_network_metrics(),
                "exported_at": utc_now().isoformat(),
            }
        elif format == "gexf":
            # NetworkX GEXF format for visualization tools
            import io

            buffer = io.StringIO()
            nx.write_gexf(self.graph, buffer)
            return {"gexf_data": buffer.getvalue()}
        else:
            raise ValueError(f"Unsupported export format: {format}")


class NetworkXTopologySDK:
    """Main SDK for NetworkX-based network topology management"""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self.topology = NetworkXTopologyManager()

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

    async def get_network_analysis(self) -> Dict[str, Any]:
        """Get comprehensive network analysis"""

        metrics = await self.topology.calculate_network_metrics()
        critical_nodes = await self.topology.identify_critical_nodes()
        critical_edges = await self.topology.identify_critical_edges()
        resilience = await self.topology.analyze_network_resilience()

        return {
            "network_metrics": metrics,
            "critical_infrastructure": {
                "critical_nodes": critical_nodes[:10],  # Top 10
                "critical_edges": critical_edges[:10],  # Top 10
            },
            "resilience_analysis": resilience,
            "analysis_completed": utc_now().isoformat(),
        }

    async def plan_network_optimization(self) -> Dict[str, Any]:
        """Generate network optimization recommendations"""

        analysis = await self.get_network_analysis()
        recommendations = []

        # Analyze critical nodes
        critical_nodes = analysis["critical_infrastructure"]["critical_nodes"]
        if len(critical_nodes) > 0:
            top_critical = critical_nodes[0]
            if top_critical["criticality_score"] > 0.8:
                recommendations.append(
                    {
                        "type": "redundancy",
                        "priority": "high",
                        "description": f"Add redundant connections for critical device {top_critical['device_id']}",
                        "impact": "Reduces single point of failure risk",
                    }
                )

        # Analyze network connectivity
        resilience = analysis["resilience_analysis"]
        if resilience["overall_score"] < 0.6:
            recommendations.append(
                {
                    "type": "connectivity",
                    "priority": "medium",
                    "description": "Improve overall network connectivity and redundancy",
                    "impact": "Increases network resilience and uptime",
                }
            )

        # Analyze network density
        metrics = analysis["network_metrics"]
        density = metrics["basic_stats"]["density"]
        if density < 0.3:  # Low density networks
            recommendations.append(
                {
                    "type": "topology",
                    "priority": "low",
                    "description": "Consider adding more interconnections to increase network density",
                    "impact": "Improves fault tolerance and reduces average path length",
                }
            )

        return {
            "optimization_recommendations": recommendations,
            "current_network_score": resilience["overall_score"],
            "recommendations_count": len(recommendations),
            "generated_at": utc_now().isoformat(),
        }
