"""
Network Topology SDK - nodes/links/ports graph management
"""

from datetime import datetime
from dotmac_isp.sdks.core.datetime_utils import utc_now, utc_now_iso
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from ..core.exceptions import TopologyError


class NetworkTopologyService:
    """In-memory service for network topology operations."""

    def __init__(self):
        self._nodes: Dict[str, Dict[str, Any]] = {}
        self._links: Dict[str, Dict[str, Any]] = {}
        self._ports: Dict[str, Dict[str, Any]] = {}
        self._node_links: Dict[str, List[str]] = {}  # node_id -> link_ids
        self._adjacency: Dict[str, Set[str]] = {}  # node_id -> connected node_ids

    async def add_node(self, **kwargs) -> Dict[str, Any]:
        """Add node to topology."""
        node_id = kwargs.get("node_id") or str(uuid4())

        if node_id in self._nodes:
            raise TopologyError(f"Node already exists: {node_id}")

        node = {
            "node_id": node_id,
            "node_type": kwargs.get("node_type", "device"),  # device, site, logical
            "device_id": kwargs.get("device_id"),
            "site_id": kwargs.get("site_id"),
            "name": kwargs.get("name", ""),
            "description": kwargs.get("description", ""),
            "coordinates": kwargs.get("coordinates", {}),  # x, y for visualization
            "properties": kwargs.get("properties", {}),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._nodes[node_id] = node
        self._node_links[node_id] = []
        self._adjacency[node_id] = set()

        return node

    async def add_link(self, **kwargs) -> Dict[str, Any]:
        """Add link between nodes."""
        link_id = kwargs.get("link_id") or str(uuid4())
        source_node = kwargs["source_node"]
        target_node = kwargs["target_node"]

        if source_node not in self._nodes:
            raise TopologyError(f"Source node not found: {source_node}")

        if target_node not in self._nodes:
            raise TopologyError(f"Target node not found: {target_node}")

        if link_id in self._links:
            raise TopologyError(f"Link already exists: {link_id}")

        link = {
            "link_id": link_id,
            "source_node": source_node,
            "target_node": target_node,
            "source_port": kwargs.get("source_port"),
            "target_port": kwargs.get("target_port"),
            "link_type": kwargs.get(
                "link_type", "physical"
            ),  # physical, logical, virtual
            "bandwidth": kwargs.get("bandwidth"),
            "latency": kwargs.get("latency"),
            "cost": kwargs.get("cost", 1),
            "status": kwargs.get("status", "active"),
            "properties": kwargs.get("properties", {}),
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }

        self._links[link_id] = link

        # Update adjacency
        self._node_links[source_node].append(link_id)
        self._node_links[target_node].append(link_id)
        self._adjacency[source_node].add(target_node)
        self._adjacency[target_node].add(source_node)

        return link

    async def find_path(self, source: str, target: str) -> List[str]:
        """Find shortest path between nodes using BFS."""
        if source not in self._nodes or target not in self._nodes:
            raise TopologyError("Source or target node not found")

        if source == target:
            return [source]

        visited = set()
        queue = [(source, [source])]

        while queue:
            current, path = queue.pop(0)

            if current in visited:
                continue

            visited.add(current)

            for neighbor in self._adjacency.get(current, set()):
                if neighbor == target:
                    return path + [neighbor]

                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))

        return []  # No path found


class NetworkTopologySDK:
    """Minimal, reusable SDK for network topology management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = NetworkTopologyService()

    async def add_node(
        self,
        node_id: str,
        node_type: str = "device",
        device_id: Optional[str] = None,
        site_id: Optional[str] = None,
        name: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Add node to topology."""
        node = await self._service.add_node(
            node_id=node_id,
            node_type=node_type,
            device_id=device_id,
            site_id=site_id,
            name=name or node_id,
            tenant_id=self.tenant_id,
            **kwargs,
        )

        return {
            "node_id": node["node_id"],
            "node_type": node["node_type"],
            "device_id": node["device_id"],
            "site_id": node["site_id"],
            "name": node["name"],
            "description": node["description"],
            "coordinates": node["coordinates"],
            "status": node["status"],
            "created_at": node["created_at"],
        }

    async def add_link(
        self,
        source_node: str,
        target_node: str,
        link_type: str = "physical",
        source_port: Optional[str] = None,
        target_port: Optional[str] = None,
        bandwidth: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Add link between nodes."""
        link = await self._service.add_link(
            source_node=source_node,
            target_node=target_node,
            source_port=source_port,
            target_port=target_port,
            link_type=link_type,
            bandwidth=bandwidth,
            **kwargs,
        )

        return {
            "link_id": link["link_id"],
            "source_node": link["source_node"],
            "target_node": link["target_node"],
            "source_port": link["source_port"],
            "target_port": link["target_port"],
            "link_type": link["link_type"],
            "bandwidth": link["bandwidth"],
            "latency": link["latency"],
            "cost": link["cost"],
            "status": link["status"],
            "created_at": link["created_at"],
        }

    async def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Get node by ID."""
        node = self._service._nodes.get(node_id)
        if not node:
            return None

        return {
            "node_id": node["node_id"],
            "node_type": node["node_type"],
            "device_id": node["device_id"],
            "site_id": node["site_id"],
            "name": node["name"],
            "description": node["description"],
            "coordinates": node["coordinates"],
            "properties": node["properties"],
            "status": node["status"],
            "created_at": node["created_at"],
            "updated_at": node["updated_at"],
        }

    async def get_node_neighbors(self, node_id: str) -> List[Dict[str, Any]]:
        """Get neighboring nodes."""
        if node_id not in self._service._nodes:
            raise TopologyError(f"Node not found: {node_id}")

        neighbors = []
        for neighbor_id in self._service._adjacency.get(node_id, set()):
            neighbor = self._service._nodes[neighbor_id]
            neighbors.append(
                {
                    "node_id": neighbor["node_id"],
                    "name": neighbor["name"],
                    "node_type": neighbor["node_type"],
                    "device_id": neighbor["device_id"],
                    "status": neighbor["status"],
                }
            )

        return neighbors

    async def get_node_links(self, node_id: str) -> List[Dict[str, Any]]:
        """Get all links connected to a node."""
        if node_id not in self._service._nodes:
            raise TopologyError(f"Node not found: {node_id}")

        link_ids = self._service._node_links.get(node_id, [])
        links = []

        for link_id in link_ids:
            link = self._service._links[link_id]
            links.append(
                {
                    "link_id": link["link_id"],
                    "source_node": link["source_node"],
                    "target_node": link["target_node"],
                    "source_port": link["source_port"],
                    "target_port": link["target_port"],
                    "link_type": link["link_type"],
                    "bandwidth": link["bandwidth"],
                    "status": link["status"],
                }
            )

        return links

    async def find_shortest_path(self, source: str, target: str) -> Dict[str, Any]:
        """Find shortest path between nodes."""
        path = await self._service.find_path(source, target)

        if not path:
            return {
                "source": source,
                "target": target,
                "path_found": False,
                "path": [],
                "hop_count": 0,
            }

        # Get path details
        path_details = []
        for i, node_id in enumerate(path):
            node = self._service._nodes[node_id]
            path_details.append(
                {
                    "hop": i + 1,
                    "node_id": node_id,
                    "name": node["name"],
                    "node_type": node["node_type"],
                }
            )

        return {
            "source": source,
            "target": target,
            "path_found": True,
            "path": path_details,
            "hop_count": len(path) - 1,
        }

    async def get_topology_summary(self) -> Dict[str, Any]:
        """Get topology summary statistics."""
        total_nodes = len(self._service._nodes)
        total_links = len(self._service._links)

        node_types = {}
        for node in self._service._nodes.values():
            node_type = node["node_type"]
            node_types[node_type] = node_types.get(node_type, 0) + 1

        link_types = {}
        for link in self._service._links.values():
            link_type = link["link_type"]
            link_types[link_type] = link_types.get(link_type, 0) + 1

        return {
            "total_nodes": total_nodes,
            "total_links": total_links,
            "node_types": node_types,
            "link_types": link_types,
            "average_degree": (total_links * 2) / total_nodes if total_nodes > 0 else 0,
        }

    async def get_site_topology(self, site_id: str) -> Dict[str, Any]:
        """Get topology for a specific site."""
        site_nodes = [
            node
            for node in self._service._nodes.values()
            if node.get("site_id") == site_id
        ]

        site_node_ids = {node["node_id"] for node in site_nodes}

        # Find links within the site
        site_links = []
        for link in self._service._links.values():
            if (
                link["source_node"] in site_node_ids
                and link["target_node"] in site_node_ids
            ):
                site_links.append(link)

        return {
            "site_id": site_id,
            "nodes": [
                {
                    "node_id": node["node_id"],
                    "name": node["name"],
                    "node_type": node["node_type"],
                    "device_id": node["device_id"],
                    "status": node["status"],
                }
                for node in site_nodes
            ],
            "links": [
                {
                    "link_id": link["link_id"],
                    "source_node": link["source_node"],
                    "target_node": link["target_node"],
                    "link_type": link["link_type"],
                    "status": link["status"],
                }
                for link in site_links
            ],
            "node_count": len(site_nodes),
            "link_count": len(site_links),
        }
