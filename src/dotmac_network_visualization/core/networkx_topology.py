"""NetworkX-based Network Topology SDK - Production network analysis."""

import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple
from uuid import uuid4

try:
    import networkx as nx

    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

from dotmac_shared.api.exception_handlers import standard_exception_handler

from ..exceptions import NetworkXError, TopologyError


def utc_now() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(timezone.utc)


class NetworkXTopologyManager:
    """NetworkX-powered network topology with advanced graph algorithms."""

    def __init__(self, directed: bool = False, cache_ttl: float = 300.0):
        """Initialize NetworkX topology manager."""
        if not NETWORKX_AVAILABLE:
            raise NetworkXError(
                "NetworkX is not available. Install with: pip install networkx"
            )

        self.graph = nx.DiGraph() if directed else nx.Graph()
        self.device_attributes: Dict[str, Dict[str, Any]] = {}
        self.link_attributes: Dict[Tuple[str, str], Dict[str, Any]] = {}
        self.topology_history: List[Dict[str, Any]] = []
        self._cache_ttl = cache_ttl
        self._cached_results = {}
        self._cache_timestamps = {}

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached result is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        return (time.time() - self._cache_timestamps[cache_key]) < self._cache_ttl

    def _cache_result(self, cache_key: str, result: Any):
        """Cache computation result."""
        self._cached_results[cache_key] = result
        self._cache_timestamps[cache_key] = time.time()

    def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Get cached result if valid."""
        if self._is_cache_valid(cache_key):
            return self._cached_results.get(cache_key)
        return None

    def clear_cache(self):
        """Clear all cached results."""
        self._cached_results.clear()
        self._cache_timestamps.clear()

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

        # Add to NetworkX graph
        self.graph.add_node(device_id, **device_data)
        self.device_attributes[device_id] = device_data

        # Clear relevant caches
        self.clear_cache()
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

        # Add to NetworkX graph with edge attributes
        self.graph.add_edge(device1, device2, **link_data)
        self.link_attributes[(device1, device2)] = link_data

        # Clear relevant caches
        self.clear_cache()
        self._log_topology_change("link_added", **link_data)

        return link_data

    async def remove_network_device(self, device_id: str) -> Dict[str, Any]:
        """Remove device and all its links."""
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
        self.clear_cache()
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
        """Find shortest path between devices using NetworkX."""
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

    async def calculate_network_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive network metrics using NetworkX."""
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
        if nx.is_connected(self.graph) and not self.graph.is_directed():
            try:
                metrics["connectivity"] = {
                    "diameter": nx.diameter(self.graph),
                    "radius": nx.radius(self.graph),
                    "center": list(nx.center(self.graph)),
                    "periphery": list(nx.periphery(self.graph)),
                }
            except Exception:
                metrics["connectivity"] = {
                    "error": "Could not calculate connectivity metrics"
                }
        else:
            if self.graph.is_directed():
                components = nx.weakly_connected_components(self.graph)
            else:
                components = nx.connected_components(self.graph)

            metrics["connectivity"] = {
                "connected_components": (
                    nx.number_connected_components(self.graph)
                    if not self.graph.is_directed()
                    else nx.number_weakly_connected_components(self.graph)
                ),
                "largest_component_size": (
                    len(max(components, key=len)) if components else 0
                ),
            }

        # Centrality metrics (for smaller graphs)
        if self.graph.number_of_nodes() <= 100:  # Limit for performance
            try:
                metrics["centrality"] = {
                    "betweenness": dict(nx.betweenness_centrality(self.graph)),
                    "closeness": dict(nx.closeness_centrality(self.graph)),
                    "degree": dict(nx.degree_centrality(self.graph)),
                }
                # Eigenvector centrality can fail, so handle separately
                try:
                    metrics["centrality"]["eigenvector"] = dict(
                        nx.eigenvector_centrality(self.graph, max_iter=1000)
                    )
                except Exception:
                    metrics["centrality"]["eigenvector"] = {}
            except Exception:
                metrics["centrality"] = {
                    "error": "Could not calculate centrality metrics"
                }

        # Clustering metrics
        try:
            metrics["clustering"] = {
                "average_clustering": nx.average_clustering(self.graph),
                "transitivity": nx.transitivity(self.graph),
            }
        except Exception:
            metrics["clustering"] = {"error": "Could not calculate clustering metrics"}

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
        """Identify critical nodes using NetworkX algorithms."""
        cache_key = "critical_nodes"
        cached_result = self._get_cached_result(cache_key)
        if cached_result is not None:
            return cached_result

        critical_nodes = []
        if self.graph.number_of_nodes() == 0:
            return critical_nodes

        # Articulation points (cut vertices)
        articulation_points = set()
        if nx.is_connected(self.graph) and not self.graph.is_directed():
            try:
                articulation_points = set(nx.articulation_points(self.graph))
            except Exception:
                pass

        # Calculate centrality scores for all nodes
        try:
            betweenness_centrality = nx.betweenness_centrality(self.graph)
            degree_centrality = nx.degree_centrality(self.graph)
        except Exception:
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

    async def export_graph_data(self, format: str = "json") -> Dict[str, Any]:
        """Export graph data in various formats."""
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
        else:
            raise ValueError(f"Unsupported export format: {format}")

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


class NetworkXTopologySDK:
    """Main SDK for NetworkX-based network topology management."""

    def __init__(self, tenant_id: str):
        """Initialize NetworkX topology SDK."""
        self.tenant_id = tenant_id
        self.topology = NetworkXTopologyManager()

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

    async def get_network_analysis(self) -> Dict[str, Any]:
        """Get comprehensive network analysis."""
        metrics = await self.topology.calculate_network_metrics()
        critical_nodes = await self.topology.identify_critical_nodes()

        return {
            "network_metrics": metrics,
            "critical_infrastructure": {
                "critical_nodes": critical_nodes[:10],  # Top 10
            },
            "analysis_completed": utc_now().isoformat(),
        }
