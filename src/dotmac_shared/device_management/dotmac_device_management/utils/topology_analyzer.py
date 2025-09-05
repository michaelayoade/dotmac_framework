"""
Network Topology Analyzer utilities.

Provides advanced network topology analysis, path optimization, and redundancy detection.
"""

import heapq
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from ..exceptions import TopologyAnalysisError


@dataclass
class PathMetrics:
    """Metrics for a network path."""

    hops: int
    latency_ms: Optional[float]
    bandwidth_mbps: Optional[float]
    cost: int
    reliability_score: float


@dataclass
class RedundancyAnalysis:
    """Results of redundancy analysis."""

    single_points_of_failure: list[str]
    redundancy_paths: dict[str, list[list[str]]]
    critical_links: list[str]
    reliability_score: float


class TopologyAnalyzer:
    """Advanced network topology analyzer."""

    def __init__(self, timezone):
        """Initialize topology analyzer."""
        self.graph = defaultdict(dict)  # node_id -> {neighbor_id: link_data}
        self.nodes = {}  # node_id -> node_data
        self.links = {}  # link_id -> link_data
        self.node_attributes = defaultdict(dict)
        self.link_attributes = defaultdict(dict)

    def build_graph(self, nodes: list[dict[str, Any]], links: list[dict[str, Any]]):
        """Build internal graph representation from nodes and links."""
        self.graph.clear()
        self.nodes.clear()
        self.links.clear()

        # Store nodes
        for node in nodes:
            node_id = node["node_id"]
            self.nodes[node_id] = node
            self.node_attributes[node_id] = {
                "type": node.get("node_type", "device"),
                "site_id": node.get("site_id"),
                "status": node.get("status", "active"),
                "properties": node.get("properties", {}),
            }

        # Store links and build adjacency
        for link in links:
            link_id = link["link_id"]
            source = link["source_node_id"]
            target = link["target_node_id"]

            if source not in self.nodes or target not in self.nodes:
                continue  # Skip links to non-existent nodes

            self.links[link_id] = link

            # Build bidirectional graph
            link_data = {
                "link_id": link_id,
                "bandwidth": link.get("bandwidth"),
                "latency_ms": link.get("latency_ms", 0),
                "cost": link.get("cost", 1),
                "status": link.get("status", "active"),
                "link_type": link.get("link_type", "physical"),
            }

            self.graph[source][target] = link_data
            self.graph[target][source] = link_data

            self.link_attributes[link_id] = link_data

    def find_shortest_path(
        self, source: str, target: str, metric: str = "hops"
    ) -> Optional[list[str]]:
        """Find shortest path using different metrics."""
        if source not in self.nodes or target not in self.nodes:
            raise TopologyAnalysisError(f"Node not found: {source} or {target}")

        if metric == "hops":
            return self._bfs_shortest_path(source, target)
        elif metric == "cost":
            return self._dijkstra_shortest_path(source, target, "cost")
        elif metric == "latency":
            return self._dijkstra_shortest_path(source, target, "latency_ms")
        else:
            raise TopologyAnalysisError(f"Unknown metric: {metric}")

    def _bfs_shortest_path(self, source: str, target: str) -> Optional[list[str]]:
        """BFS for shortest hop path."""
        if source == target:
            return [source]

        visited = set()
        queue = deque([(source, [source])])

        while queue:
            node, path = queue.popleft()

            if node in visited:
                continue
            visited.add(node)

            for neighbor in self.graph.get(node, {}):
                if neighbor == target:
                    return path + [neighbor]

                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))

        return None

    def _dijkstra_shortest_path(
        self, source: str, target: str, weight_attr: str
    ) -> Optional[list[str]]:
        """Dijkstra's algorithm for weighted shortest path."""
        distances = {node: float("inf") for node in self.nodes}
        distances[source] = 0
        previous = {}
        pq = [(0, source)]
        visited = set()

        while pq:
            current_dist, current = heapq.heappop(pq)

            if current in visited:
                continue
            visited.add(current)

            if current == target:
                # Reconstruct path
                path = []
                while current in previous:
                    path.append(current)
                    current = previous[current]
                path.append(source)
                return list(reversed(path))

            for neighbor, link_data in self.graph.get(current, {}).items():
                if neighbor in visited:
                    continue

                weight = link_data.get(weight_attr, 1)
                if weight is None:
                    weight = 1

                distance = current_dist + weight

                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous[neighbor] = current
                    heapq.heappush(pq, (distance, neighbor))

        return None

    def find_all_paths(
        self, source: str, target: str, max_hops: int = 10
    ) -> list[list[str]]:
        """Find all paths between source and target up to max_hops."""
        if source not in self.nodes or target not in self.nodes:
            raise TopologyAnalysisError(f"Node not found: {source} or {target}")

        all_paths = []

        def dfs_paths(current: str, path: list[str], visited: set[str]):
            if len(path) > max_hops:
                return

            if current == target:
                all_paths.append(path.copy())
                return

            for neighbor in self.graph.get(current, {}):
                if neighbor not in visited:
                    visited.add(neighbor)
                    path.append(neighbor)
                    dfs_paths(neighbor, path, visited)
                    path.pop()
                    visited.remove(neighbor)

        dfs_paths(source, [source], {source})
        return all_paths

    def calculate_path_metrics(self, path: list[str]) -> PathMetrics:
        """Calculate comprehensive metrics for a path."""
        if len(path) < 2:
            return PathMetrics(0, 0, None, 0, 1.0)

        total_latency = 0
        min_bandwidth = None
        total_cost = 0
        active_links = 0

        for i in range(len(path) - 1):
            current = path[i]
            next_node = path[i + 1]

            link_data = self.graph.get(current, {}).get(next_node)
            if not link_data:
                continue

            # Accumulate latency
            latency = link_data.get("latency_ms", 0)
            if latency:
                total_latency += latency

            # Track minimum bandwidth
            bandwidth = link_data.get("bandwidth")
            if bandwidth:
                try:
                    # Parse bandwidth (assume format like "1G", "100M")
                    bw_value = float(bandwidth.rstrip("GMKgmk"))
                    if bandwidth.lower().endswith("g"):
                        bw_value *= 1000
                    elif bandwidth.lower().endswith("k"):
                        bw_value /= 1000

                    if min_bandwidth is None or bw_value < min_bandwidth:
                        min_bandwidth = bw_value
                except (ValueError, AttributeError):
                    pass

            # Accumulate cost
            total_cost += link_data.get("cost", 1)

            # Track active links for reliability
            if link_data.get("status") == "active":
                active_links += 1

        # Calculate reliability score (percentage of active links)
        total_links = len(path) - 1
        reliability_score = active_links / total_links if total_links > 0 else 1.0

        return PathMetrics(
            hops=len(path) - 1,
            latency_ms=total_latency if total_latency > 0 else None,
            bandwidth_mbps=min_bandwidth,
            cost=total_cost,
            reliability_score=reliability_score,
        )

    def analyze_redundancy(self, critical_nodes: list[str]) -> RedundancyAnalysis:
        """Analyze network redundancy for critical nodes."""
        single_points = []
        redundancy_paths = {}
        critical_links = []

        # Find single points of failure
        for node in critical_nodes:
            if node not in self.nodes:
                continue

            neighbors = list(self.graph.get(node, {}).keys())
            active_neighbors = [
                n for n in neighbors if self.graph[node][n].get("status") == "active"
            ]

            if len(active_neighbors) <= 1:
                single_points.append(node)

            # Find redundant paths to other critical nodes
            node_paths = {}
            for other_node in critical_nodes:
                if other_node != node:
                    paths = self.find_all_paths(node, other_node, max_hops=8)
                    if len(paths) > 1:
                        node_paths[other_node] = paths[:3]  # Keep top 3 paths

            if node_paths:
                redundancy_paths[node] = node_paths

        # Identify critical links (links whose failure isolates critical nodes)
        for link_id, link_data in self.links.items():
            source = link_data["source_node_id"]
            target = link_data["target_node_id"]

            # Temporarily remove link and check connectivity
            if source in self.graph and target in self.graph[source]:
                # Remove link temporarily
                source_link = self.graph[source].pop(target, None)
                target_link = self.graph[target].pop(source, None)

                # Check if any critical nodes become disconnected
                isolated = False
                for critical_node in critical_nodes:
                    if critical_node == source or critical_node == target:
                        continue

                    path_to_source = self._bfs_shortest_path(critical_node, source)
                    path_to_target = self._bfs_shortest_path(critical_node, target)

                    if not path_to_source or not path_to_target:
                        isolated = True
                        break

                if isolated:
                    critical_links.append(link_id)

                # Restore link
                if source_link:
                    self.graph[source][target] = source_link
                if target_link:
                    self.graph[target][source] = target_link

        # Calculate overall reliability score
        total_critical_pairs = len(critical_nodes) * (len(critical_nodes) - 1) // 2
        redundant_pairs = sum(len(paths) for paths in redundancy_paths.values())
        reliability_score = redundant_pairs / max(total_critical_pairs, 1)

        return RedundancyAnalysis(
            single_points_of_failure=single_points,
            redundancy_paths=redundancy_paths,
            critical_links=critical_links,
            reliability_score=min(reliability_score, 1.0),
        )

    def detect_loops(self) -> list[list[str]]:
        """Detect loops in the network topology."""
        visited = set()
        loops = []

        def dfs_detect_cycles(node: str, path: list[str], parent: Optional[str] = None):
            visited.add(node)
            path.append(node)

            for neighbor in self.graph.get(node, {}):
                if neighbor == parent:  # Skip back to parent in undirected graph
                    continue

                if neighbor in path:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    if len(cycle) > 3:  # Ignore trivial 2-node cycles
                        loops.append(cycle)
                elif neighbor not in visited:
                    dfs_detect_cycles(neighbor, path, node)

            path.pop()

        for node in self.nodes:
            if node not in visited:
                dfs_detect_cycles(node, [])

        return loops

    def calculate_centrality_metrics(self) -> dict[str, dict[str, float]]:
        """Calculate various centrality metrics for nodes."""
        centrality_metrics = {}

        for node in self.nodes:
            metrics = {}

            # Degree centrality
            degree = len(self.graph.get(node, {}))
            max_possible_degree = len(self.nodes) - 1
            metrics["degree_centrality"] = (
                degree / max_possible_degree if max_possible_degree > 0 else 0
            )

            # Betweenness centrality (simplified)
            betweenness = 0
            total_paths = 0

            for source in self.nodes:
                for target in self.nodes:
                    if source != target and source != node and target != node:
                        paths = self.find_all_paths(source, target, max_hops=6)
                        paths_through_node = [p for p in paths if node in p]

                        if paths:
                            total_paths += len(paths)
                            betweenness += len(paths_through_node)

            metrics["betweenness_centrality"] = betweenness / max(total_paths, 1)

            # Closeness centrality
            total_distance = 0
            reachable_nodes = 0

            for target in self.nodes:
                if target != node:
                    path = self._bfs_shortest_path(node, target)
                    if path:
                        total_distance += len(path) - 1
                        reachable_nodes += 1

            if reachable_nodes > 0:
                avg_distance = total_distance / reachable_nodes
                metrics["closeness_centrality"] = (
                    1 / avg_distance if avg_distance > 0 else 0
                )
            else:
                metrics["closeness_centrality"] = 0

            centrality_metrics[node] = metrics

        return centrality_metrics

    def generate_topology_report(self) -> dict[str, Any]:
        """Generate comprehensive topology analysis report."""
        report = {
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
            "topology_summary": {
                "total_nodes": len(self.nodes),
                "total_links": len(self.links),
                "node_types": {},
                "link_types": {},
            },
            "connectivity_analysis": {},
            "redundancy_analysis": {},
            "performance_analysis": {},
            "recommendations": [],
        }

        # Node and link type distribution
        for node in self.nodes.values():
            node_type = node.get("node_type", "unknown")
            report["topology_summary"]["node_types"][node_type] = (
                report["topology_summary"]["node_types"].get(node_type, 0) + 1
            )

        for link in self.links.values():
            link_type = link.get("link_type", "unknown")
            report["topology_summary"]["link_types"][link_type] = (
                report["topology_summary"]["link_types"].get(link_type, 0) + 1
            )

        # Connectivity analysis
        isolated_nodes = [
            node for node in self.nodes if len(self.graph.get(node, {})) == 0
        ]

        loops = self.detect_loops()

        report["connectivity_analysis"] = {
            "isolated_nodes": isolated_nodes,
            "loops_detected": len(loops),
            "loops": loops[:5],  # Show first 5 loops
            "average_degree": (
                sum(len(neighbors) for neighbors in self.graph.values())
                / len(self.nodes)
                if self.nodes
                else 0
            ),
        }

        # Centrality metrics
        centrality = self.calculate_centrality_metrics()

        # Find most central nodes
        most_central_by_degree = sorted(
            centrality.items(), key=lambda x: x[1]["degree_centrality"], reverse=True
        )[:5]

        most_central_by_betweenness = sorted(
            centrality.items(),
            key=lambda x: x[1]["betweenness_centrality"],
            reverse=True,
        )[:5]

        report["performance_analysis"] = {
            "most_connected_nodes": [
                {"node_id": node, "degree_centrality": metrics["degree_centrality"]}
                for node, metrics in most_central_by_degree
            ],
            "most_critical_nodes": [
                {
                    "node_id": node,
                    "betweenness_centrality": metrics["betweenness_centrality"],
                }
                for node, metrics in most_central_by_betweenness
            ],
        }

        # Generate recommendations
        if isolated_nodes:
            report["recommendations"].append(
                {
                    "type": "connectivity",
                    "priority": "high",
                    "message": f"Found {len(isolated_nodes)} isolated nodes that need connectivity",
                }
            )

        if len(loops) > 0:
            report["recommendations"].append(
                {
                    "type": "redundancy",
                    "priority": "medium",
                    "message": f"Detected {len(loops)} network loops - consider spanning tree protocols",
                }
            )

        avg_degree = report["connectivity_analysis"]["average_degree"]
        if avg_degree < 2:
            report["recommendations"].append(
                {
                    "type": "redundancy",
                    "priority": "medium",
                    "message": f"Low average connectivity ({avg_degree:.1f}) - consider adding redundant links",
                }
            )

        return report

    def find_optimal_placement(
        self, new_node_candidates: list[str], existing_connections: dict[str, list[str]]
    ) -> dict[str, Any]:
        """Find optimal placement for new network nodes."""
        placement_analysis = {
            "candidates": [],
            "recommended_placement": None,
            "analysis_criteria": [
                "connectivity_improvement",
                "redundancy_enhancement",
                "centrality_optimization",
            ],
        }

        for candidate in new_node_candidates:
            candidate_analysis = {
                "candidate_id": candidate,
                "connections": existing_connections.get(candidate, []),
                "metrics": {},
            }

            # Simulate adding the candidate
            original_graph = dict(self.graph)

            # Add candidate connections
            for neighbor in existing_connections.get(candidate, []):
                if neighbor in self.nodes:
                    self.graph[candidate][neighbor] = {"cost": 1, "status": "active"}
                    self.graph[neighbor][candidate] = {"cost": 1, "status": "active"}

            # Calculate improvement metrics
            # Connectivity improvement
            original_components = self._count_connected_components(original_graph)
            new_components = self._count_connected_components(self.graph)
            candidate_analysis["metrics"]["connectivity_improvement"] = max(
                0, original_components - new_components
            )

            # Average path length improvement
            avg_path_length = self._calculate_average_path_length()
            candidate_analysis["metrics"]["avg_path_length"] = avg_path_length

            # Centrality score
            self.nodes[candidate] = {"node_type": "device"}  # Temporary
            centrality = self.calculate_centrality_metrics()
            candidate_metrics = centrality.get(candidate, {})
            candidate_analysis["metrics"]["centrality_score"] = (
                candidate_metrics.get("degree_centrality", 0)
                + candidate_metrics.get("betweenness_centrality", 0)
                + candidate_metrics.get("closeness_centrality", 0)
            ) / 3

            placement_analysis["candidates"].append(candidate_analysis)

            # Restore original graph
            self.graph = original_graph
            if candidate in self.nodes:
                del self.nodes[candidate]

        # Find best candidate
        if placement_analysis["candidates"]:
            best_candidate = max(
                placement_analysis["candidates"],
                key=lambda x: (
                    x["metrics"]["connectivity_improvement"] * 2
                    + x["metrics"]["centrality_score"] * 1
                    + (1 / max(x["metrics"]["avg_path_length"], 0.1))
                ),
            )
            placement_analysis["recommended_placement"] = best_candidate

        return placement_analysis

    def _count_connected_components(self, graph: dict[str, dict[str, Any]]) -> int:
        """Count connected components in the graph."""
        visited = set()
        components = 0

        def dfs(node):
            visited.add(node)
            for neighbor in graph.get(node, {}):
                if neighbor not in visited:
                    dfs(neighbor)

        for node in graph:
            if node not in visited:
                dfs(node)
                components += 1

        return components

    def _calculate_average_path_length(self) -> float:
        """Calculate average shortest path length in the network."""
        total_distance = 0
        total_pairs = 0

        nodes_list = list(self.nodes.keys())
        for i, source in enumerate(nodes_list):
            for target in nodes_list[i + 1 :]:
                path = self._bfs_shortest_path(source, target)
                if path:
                    total_distance += len(path) - 1
                    total_pairs += 1

        return total_distance / max(total_pairs, 1)
