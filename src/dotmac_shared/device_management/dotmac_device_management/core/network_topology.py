"""
Network Topology Management for DotMac Device Management Framework.

Provides network graph management with nodes, links, and path finding capabilities.
"""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from ..exceptions import NetworkTopologyError
from .models import Device, LinkType, NetworkLink, NetworkNode, NodeType


class NetworkTopologyManager:
    """Network topology manager for database operations."""

    def __init__(self, session: Session, tenant_id: str, timezone):
        self.session = session
        self.tenant_id = tenant_id

    async def create_node(
        self,
        node_id: str,
        node_type: str = NodeType.DEVICE,
        name: str = "",
        device_id: Optional[str] = None,
        site_id: Optional[str] = None,
        **kwargs,
    ) -> NetworkNode:
        """Create network topology node."""
        # Check if node already exists
        existing = (
            self.session.query(NetworkNode)
            .filter(
                and_(
                    NetworkNode.node_id == node_id,
                    NetworkNode.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

        if existing:
            raise NetworkTopologyError(f"Node already exists: {node_id}")

        # If device_id is provided, verify device exists
        if device_id:
            device = (
                self.session.query(Device)
                .filter(
                    and_(
                        Device.device_id == device_id,
                        Device.tenant_id == self.tenant_id,
                    )
                )
                .first()
            )

            if not device:
                raise NetworkTopologyError(f"Device not found: {device_id}")

        node = NetworkNode(
            tenant_id=self.tenant_id,
            node_id=node_id,
            node_type=node_type,
            name=name or node_id,
            description=kwargs.get("description", ""),
            device_id=device_id,
            site_id=site_id,
            x_coordinate=kwargs.get("x_coordinate"),
            y_coordinate=kwargs.get("y_coordinate"),
            z_coordinate=kwargs.get("z_coordinate"),
            status=kwargs.get("status", "active"),
            properties=kwargs.get("properties", {}),
            device_device_metadata=kwargs.get("metadata", {}),
        )

        self.session.add(node)
        self.session.commit()
        return node

    async def get_node(self, node_id: str) -> Optional[NetworkNode]:
        """Get network node by ID."""
        return (
            self.session.query(NetworkNode)
            .filter(
                and_(
                    NetworkNode.node_id == node_id,
                    NetworkNode.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    async def update_node(self, node_id: str, updates: dict[str, Any]) -> Optional[NetworkNode]:
        """Update network node."""
        node = await self.get_node(node_id)
        if not node:
            return None

        for key, value in updates.items():
            if hasattr(node, key) and key not in [
                "id",
                "tenant_id",
                "node_id",
                "created_at",
            ]:
                setattr(node, key, value)

        node.updated_at = datetime.now(timezone.utc)
        self.session.commit()
        return node

    async def delete_node(self, node_id: str) -> bool:
        """Delete network node and associated links."""
        node = await self.get_node(node_id)
        if not node:
            return False

        # Delete associated links
        self.session.query(NetworkLink).filter(
            and_(
                NetworkLink.tenant_id == self.tenant_id,
                or_(
                    NetworkLink.source_node_id == node_id,
                    NetworkLink.target_node_id == node_id,
                ),
            )
        ).delete()

        self.session.delete(node)
        self.session.commit()
        return True

    async def create_link(
        self,
        link_id: str,
        source_node_id: str,
        target_node_id: str,
        link_type: str = LinkType.PHYSICAL,
        **kwargs,
    ) -> NetworkLink:
        """Create network topology link."""
        # Check if link already exists
        existing = (
            self.session.query(NetworkLink)
            .filter(
                and_(
                    NetworkLink.link_id == link_id,
                    NetworkLink.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

        if existing:
            raise NetworkTopologyError(f"Link already exists: {link_id}")

        # Verify source and target nodes exist
        source_node = await self.get_node(source_node_id)
        if not source_node:
            raise NetworkTopologyError(f"Source node not found: {source_node_id}")

        target_node = await self.get_node(target_node_id)
        if not target_node:
            raise NetworkTopologyError(f"Target node not found: {target_node_id}")

        link = NetworkLink(
            tenant_id=self.tenant_id,
            link_id=link_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            source_port=kwargs.get("source_port"),
            target_port=kwargs.get("target_port"),
            link_type=link_type,
            bandwidth=kwargs.get("bandwidth"),
            latency_ms=kwargs.get("latency_ms"),
            cost=kwargs.get("cost", 1),
            status=kwargs.get("status", "active"),
            properties=kwargs.get("properties", {}),
            device_device_metadata=kwargs.get("metadata", {}),
        )

        self.session.add(link)
        self.session.commit()
        return link

    async def get_link(self, link_id: str) -> Optional[NetworkLink]:
        """Get network link by ID."""
        return (
            self.session.query(NetworkLink)
            .filter(
                and_(
                    NetworkLink.link_id == link_id,
                    NetworkLink.tenant_id == self.tenant_id,
                )
            )
            .first()
        )

    async def get_node_links(self, node_id: str) -> list[NetworkLink]:
        """Get all links connected to a node."""
        return (
            self.session.query(NetworkLink)
            .filter(
                and_(
                    NetworkLink.tenant_id == self.tenant_id,
                    or_(
                        NetworkLink.source_node_id == node_id,
                        NetworkLink.target_node_id == node_id,
                    ),
                )
            )
            .all()
        )

    async def get_node_neighbors(self, node_id: str) -> list[NetworkNode]:
        """Get neighboring nodes."""
        # Get all links connected to the node
        links = await self.get_node_links(node_id)

        neighbor_ids = set()
        for link in links:
            if link.source_node_id == node_id:
                neighbor_ids.add(link.target_node_id)
            else:
                neighbor_ids.add(link.source_node_id)

        # Get neighbor nodes
        neighbors = []
        for neighbor_id in neighbor_ids:
            neighbor = await self.get_node(neighbor_id)
            if neighbor:
                neighbors.append(neighbor)

        return neighbors

    async def find_shortest_path(self, source_node_id: str, target_node_id: str) -> list[str]:
        """Find shortest path between nodes using BFS."""
        if source_node_id == target_node_id:
            return [source_node_id]

        # Verify nodes exist
        source_node = await self.get_node(source_node_id)
        target_node = await self.get_node(target_node_id)

        if not source_node or not target_node:
            return []

        # Build adjacency list from database
        adjacency = {}
        all_links = (
            self.session.query(NetworkLink)
            .filter(
                and_(
                    NetworkLink.tenant_id == self.tenant_id,
                    NetworkLink.status == "active",
                )
            )
            .all()
        )

        for link in all_links:
            source = link.source_node_id
            target = link.target_node_id

            if source not in adjacency:
                adjacency[source] = set()
            if target not in adjacency:
                adjacency[target] = set()

            adjacency[source].add(target)
            adjacency[target].add(source)

        # BFS to find shortest path
        visited = set()
        queue = [(source_node_id, [source_node_id])]

        while queue:
            current, path = queue.pop(0)

            if current in visited:
                continue

            visited.add(current)

            for neighbor in adjacency.get(current, set()):
                if neighbor == target_node_id:
                    return path + [neighbor]

                if neighbor not in visited:
                    queue.append((neighbor, path + [neighbor]))

        return []  # No path found

    async def get_site_topology(self, site_id: str) -> dict[str, Any]:
        """Get topology for a specific site."""
        # Get all nodes for the site
        site_nodes = (
            self.session.query(NetworkNode)
            .filter(
                and_(
                    NetworkNode.site_id == site_id,
                    NetworkNode.tenant_id == self.tenant_id,
                )
            )
            .all()
        )

        site_node_ids = {node.node_id for node in site_nodes}

        # Get links within the site
        site_links = (
            self.session.query(NetworkLink)
            .filter(
                and_(
                    NetworkLink.tenant_id == self.tenant_id,
                    NetworkLink.source_node_id.in_(site_node_ids),
                    NetworkLink.target_node_id.in_(site_node_ids),
                )
            )
            .all()
        )

        return {
            "site_id": site_id,
            "nodes": site_nodes,
            "links": site_links,
            "node_count": len(site_nodes),
            "link_count": len(site_links),
        }

    async def get_topology_statistics(self) -> dict[str, Any]:
        """Get topology statistics."""
        total_nodes = self.session.query(NetworkNode).filter(NetworkNode.tenant_id == self.tenant_id).count()

        total_links = self.session.query(NetworkLink).filter(NetworkLink.tenant_id == self.tenant_id).count()

        # Node type breakdown
        from sqlalchemy import func

        node_type_results = (
            self.session.query(NetworkNode.node_type, func.count(NetworkNode.id))
            .filter(NetworkNode.tenant_id == self.tenant_id)
            .group_by(NetworkNode.node_type)
            .all()
        )

        node_types = dict(node_type_results)

        # Link type breakdown
        link_type_results = (
            self.session.query(NetworkLink.link_type, func.count(NetworkLink.id))
            .filter(NetworkLink.tenant_id == self.tenant_id)
            .group_by(NetworkLink.link_type)
            .all()
        )

        link_types = dict(link_type_results)

        return {
            "total_nodes": total_nodes,
            "total_links": total_links,
            "node_types": node_types,
            "link_types": link_types,
            "average_degree": (total_links * 2) / total_nodes if total_nodes > 0 else 0,
        }

    async def list_nodes(
        self,
        node_type: Optional[str] = None,
        site_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NetworkNode]:
        """List nodes with filtering."""
        query = self.session.query(NetworkNode).filter(NetworkNode.tenant_id == self.tenant_id)

        if node_type:
            query = query.filter(NetworkNode.node_type == node_type)
        if site_id:
            query = query.filter(NetworkNode.site_id == site_id)
        if status:
            query = query.filter(NetworkNode.status == status)

        return query.offset(offset).limit(limit).all()

    async def list_links(
        self,
        link_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[NetworkLink]:
        """List links with filtering."""
        query = self.session.query(NetworkLink).filter(NetworkLink.tenant_id == self.tenant_id)

        if link_type:
            query = query.filter(NetworkLink.link_type == link_type)
        if status:
            query = query.filter(NetworkLink.status == status)

        return query.offset(offset).limit(limit).all()


class NetworkTopologyService:
    """High-level service for network topology operations."""

    def __init__(self, session: Session, tenant_id: str):
        self.manager = NetworkTopologyManager(session, tenant_id)
        self.tenant_id = tenant_id

    async def build_device_topology(
        self, devices: list[dict[str, Any]], connections: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Build topology from device and connection data."""
        created_nodes = []
        created_links = []
        errors = []

        # Create nodes for devices
        for device_data in devices:
            try:
                node = await self.manager.create_node(
                    node_id=device_data["device_id"],
                    node_type=NodeType.DEVICE,
                    name=device_data.get("hostname", device_data["device_id"]),
                    device_id=device_data["device_id"],
                    site_id=device_data.get("site_id"),
                    x_coordinate=device_data.get("x_coordinate"),
                    y_coordinate=device_data.get("y_coordinate"),
                )
                created_nodes.append(node.node_id)
            except Exception as e:
                errors.append(
                    {
                        "type": "node_creation",
                        "device_id": device_data["device_id"],
                        "error": str(e),
                    }
                )

        # Create links for connections
        for connection in connections:
            try:
                link_id = f"{connection['source_device']}_{connection['target_device']}_{uuid.uuid4().hex[:8]}"
                link = await self.manager.create_link(
                    link_id=link_id,
                    source_node_id=connection["source_device"],
                    target_node_id=connection["target_device"],
                    source_port=connection.get("source_port"),
                    target_port=connection.get("target_port"),
                    link_type=connection.get("link_type", LinkType.PHYSICAL),
                    bandwidth=connection.get("bandwidth"),
                    latency_ms=connection.get("latency_ms"),
                )
                created_links.append(link.link_id)
            except Exception as e:
                errors.append(
                    {
                        "type": "link_creation",
                        "source": connection["source_device"],
                        "target": connection["target_device"],
                        "error": str(e),
                    }
                )

        return {
            "nodes_created": len(created_nodes),
            "links_created": len(created_links),
            "errors": len(errors),
            "created_nodes": created_nodes,
            "created_links": created_links,
            "error_details": errors,
        }

    async def discover_network_paths(self, source_device_id: str, target_device_id: str) -> dict[str, Any]:
        """Discover and analyze network paths between devices."""
        path = await self.manager.find_shortest_path(source_device_id, target_device_id)

        if not path:
            return {
                "source_device": source_device_id,
                "target_device": target_device_id,
                "path_found": False,
                "message": "No path found between devices",
            }

        # Get path details
        path_details = []
        total_latency = 0
        min_bandwidth = None

        for i, node_id in enumerate(path):
            node = await self.manager.get_node(node_id)
            step_info = {
                "hop": i + 1,
                "node_id": node_id,
                "name": node.name if node else "Unknown",
                "node_type": node.node_type if node else "unknown",
            }

            # Add link information for intermediate hops
            if i < len(path) - 1:
                next_node_id = path[i + 1]
                links = await self.manager.get_node_links(node_id)

                # Find the link to the next hop
                for link in links:
                    if (link.source_node_id == node_id and link.target_node_id == next_node_id) or (
                        link.source_node_id == next_node_id and link.target_node_id == node_id
                    ):
                        step_info["outgoing_link"] = {
                            "link_id": link.link_id,
                            "link_type": link.link_type,
                            "bandwidth": link.bandwidth,
                            "latency_ms": link.latency_ms,
                        }

                        # Accumulate path metrics
                        if link.latency_ms:
                            total_latency += link.latency_ms

                        if link.bandwidth:
                            try:
                                # Extract numeric bandwidth (assumes format like "1G", "10M")
                                bw_value = float(link.bandwidth.rstrip("GMK"))
                                if link.bandwidth.endswith("G"):
                                    bw_value *= 1000
                                elif link.bandwidth.endswith("K"):
                                    bw_value /= 1000

                                if min_bandwidth is None or bw_value < min_bandwidth:
                                    min_bandwidth = bw_value
                            except (ValueError, AttributeError):
                                pass
                        break

            path_details.append(step_info)

        return {
            "source_device": source_device_id,
            "target_device": target_device_id,
            "path_found": True,
            "hop_count": len(path) - 1,
            "path_details": path_details,
            "metrics": {
                "total_latency_ms": total_latency if total_latency > 0 else None,
                "bottleneck_bandwidth_mbps": min_bandwidth,
            },
        }

    async def get_device_connectivity(self, device_id: str) -> dict[str, Any]:
        """Get comprehensive connectivity information for a device."""
        node = await self.manager.get_node(device_id)
        if not node:
            return {"error": f"Device node not found: {device_id}"}

        neighbors = await self.manager.get_node_neighbors(device_id)
        links = await self.manager.get_node_links(device_id)

        # Analyze connectivity
        connectivity_summary = {
            "total_connections": len(links),
            "active_connections": len([link for link in links if link.status == "active"]),
            "connection_types": {},
            "bandwidth_summary": {},
        }

        # Group by connection types
        for link in links:
            link_type = link.link_type
            connectivity_summary["connection_types"][link_type] = (
                connectivity_summary["connection_types"].get(link_type, 0) + 1
            )

            # Bandwidth analysis
            if link.bandwidth:
                bw_key = link.bandwidth
                connectivity_summary["bandwidth_summary"][bw_key] = (
                    connectivity_summary["bandwidth_summary"].get(bw_key, 0) + 1
                )

        return {
            "device_id": device_id,
            "node_info": {
                "name": node.name,
                "node_type": node.node_type,
                "site_id": node.site_id,
                "status": node.status,
            },
            "connectivity_summary": connectivity_summary,
            "neighbors": [
                {
                    "node_id": neighbor.node_id,
                    "name": neighbor.name,
                    "node_type": neighbor.node_type,
                    "site_id": neighbor.site_id,
                }
                for neighbor in neighbors
            ],
            "links": [
                {
                    "link_id": link.link_id,
                    "connected_to": (link.target_node_id if link.source_node_id == device_id else link.source_node_id),
                    "link_type": link.link_type,
                    "bandwidth": link.bandwidth,
                    "status": link.status,
                }
                for link in links
            ],
        }

    async def analyze_network_redundancy(self, critical_devices: list[str]) -> dict[str, Any]:
        """Analyze network redundancy for critical devices."""
        redundancy_analysis = {
            "critical_devices": len(critical_devices),
            "single_points_of_failure": [],
            "redundancy_scores": {},
            "recommendations": [],
        }

        for device_id in critical_devices:
            await self.manager.get_node_neighbors(device_id)
            links = await self.manager.get_node_links(device_id)

            # Calculate redundancy score
            active_connections = len([link for link in links if link.status == "active"])
            redundancy_score = min(active_connections / 2, 1.0)  # Normalize to 0-1

            redundancy_analysis["redundancy_scores"][device_id] = {
                "score": redundancy_score,
                "active_connections": active_connections,
                "total_connections": len(links),
            }

            # Identify single points of failure
            if active_connections <= 1:
                redundancy_analysis["single_points_of_failure"].append(
                    {
                        "device_id": device_id,
                        "connections": active_connections,
                        "risk_level": "high" if active_connections == 0 else "medium",
                    }
                )

            # Generate recommendations
            if active_connections < 2:
                redundancy_analysis["recommendations"].append(
                    {
                        "device_id": device_id,
                        "recommendation": "Add redundant connections",
                        "priority": "high" if active_connections == 0 else "medium",
                    }
                )

        return redundancy_analysis
