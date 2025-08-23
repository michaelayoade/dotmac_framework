"""Network Visualization API router."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from dotmac_isp.core.database import get_db
from dotmac_isp.modules.network_visualization.models import (
    VisualizationDashboard,
    NetworkDiagram,
    TopologyLayout,
    VisualizationWidget,
    DashboardLayout,
    NetworkMap,
)
from dotmac_isp.modules.network_visualization.schemas import (
    DashboardCreate,
    DashboardResponse,
    NetworkDiagramResponse,
    TopologyData,
    VisualizationWidgetResponse,
    NetworkMapResponse,
)
from dotmac_isp.modules.network_integration.models import (
    NetworkDevice,
    NetworkInterface,
    NetworkLocation,
    NetworkTopology,
)

router = APIRouter(prefix="/api/v1/visualization", tags=["Network Visualization"])


# Dashboard Management


@router.post("/dashboards", response_model=DashboardResponse)
async def create_dashboard(
    dashboard: DashboardCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new visualization dashboard."""
    db_dashboard = VisualizationDashboard(**dashboard.model_dump())
    db.add(db_dashboard)
    await db.commit()
    await db.refresh(db_dashboard)
    return DashboardResponse.model_validate(db_dashboard)


@router.get("/dashboards", response_model=List[DashboardResponse])
async def list_dashboards(
    dashboard_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List visualization dashboards with filtering."""
    query = select(VisualizationDashboard)

    filters = []
    if dashboard_type:
        filters.append(VisualizationDashboard.dashboard_type == dashboard_type)
    if search:
        filters.append(VisualizationDashboard.name.ilike(f"%{search}%"))

    if filters:
        query = query.where(and_(*filters))

    result = await db.execute(query)
    dashboards = result.scalars().all()

    return [DashboardResponse.model_validate(dashboard) for dashboard in dashboards]


@router.get("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: str = Path(...), db: AsyncSession = Depends(get_db)
):
    """Get a specific dashboard by ID."""
    result = await db.execute(
        select(VisualizationDashboard).where(VisualizationDashboard.id == dashboard_id)
    )
    dashboard = result.scalar_one_or_none()

    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Update access tracking
    dashboard.last_accessed = datetime.utcnow()
    dashboard.access_count += 1
    await db.commit()

    return DashboardResponse.model_validate(dashboard)


@router.get(
    "/dashboards/{dashboard_id}/widgets",
    response_model=List[VisualizationWidgetResponse],
)
async def get_dashboard_widgets(
    dashboard_id: str = Path(...), db: AsyncSession = Depends(get_db)
):
    """Get widgets for a dashboard."""
    # Verify dashboard exists
    dashboard_result = await db.execute(
        select(VisualizationDashboard).where(VisualizationDashboard.id == dashboard_id)
    )
    dashboard = dashboard_result.scalar_one_or_none()

    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")

    # Get widgets
    widgets_result = await db.execute(
        select(VisualizationWidget)
        .where(VisualizationWidget.dashboard_id == dashboard_id)
        .order_by(VisualizationWidget.position_y, VisualizationWidget.position_x)
    )
    widgets = widgets_result.scalars().all()

    return [VisualizationWidgetResponse.model_validate(widget) for widget in widgets]


# Network Topology Visualization


@router.get("/topology/data")
async def get_topology_data(
    device_types: Optional[List[str]] = Query(None),
    location_ids: Optional[List[str]] = Query(None),
    include_interfaces: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """Get network topology data for visualization."""
    # Build device query
    device_query = select(NetworkDevice)

    device_filters = []
    if device_types:
        device_filters.append(NetworkDevice.device_type.in_(device_types))
    if location_ids:
        device_filters.append(NetworkDevice.location_id.in_(location_ids))

    if device_filters:
        device_query = device_query.where(and_(*device_filters))

    # Get devices
    devices_result = await db.execute(device_query)
    devices = devices_result.scalars().all()

    # Get topology connections
    device_ids = [str(device.id) for device in devices]
    topology_query = select(NetworkTopology).where(
        and_(
            NetworkTopology.parent_device_id.in_(device_ids),
            NetworkTopology.child_device_id.in_(device_ids),
        )
    )

    topology_result = await db.execute(topology_query)
    connections = topology_result.scalars().all()

    # Build topology data structure
    nodes = []
    for device in devices:
        node_data = {
            "id": str(device.id),
            "name": device.name,
            "type": device.device_type,
            "vendor": device.vendor,
            "model": device.model,
            "status": device.status,
            "management_ip": (
                str(device.management_ip) if device.management_ip else None
            ),
            "location": (
                device.full_address if hasattr(device, "full_address") else None
            ),
            "coordinates": {"x": 0, "y": 0},  # Will be set by layout algorithm
        }

        if include_interfaces:
            # Get interfaces for this device
            interfaces_result = await db.execute(
                select(NetworkInterface).where(NetworkInterface.device_id == device.id)
            )
            interfaces = interfaces_result.scalars().all()
            node_data["interfaces"] = [
                {
                    "id": str(interface.id),
                    "name": interface.name,
                    "type": interface.interface_type,
                    "status": interface.operational_status,
                    "ip_address": (
                        str(interface.ip_address) if interface.ip_address else None
                    ),
                }
                for interface in interfaces
            ]

        nodes.append(node_data)

    # Build edges
    edges = []
    for connection in connections:
        edge_data = {
            "id": str(connection.id),
            "source": str(connection.parent_device_id),
            "target": str(connection.child_device_id),
            "type": connection.connection_type,
            "bandwidth": connection.bandwidth_mbps,
            "distance": connection.distance_meters,
            "cable_type": connection.cable_type,
        }
        edges.append(edge_data)

    return {
        "nodes": nodes,
        "edges": edges,
        "metadata": {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "generated_at": datetime.utcnow(),
        },
    }


@router.post("/topology/layout")
async def apply_topology_layout(
    layout_data: TopologyData,
    algorithm: str = Query(
        "force_directed", regex="^(force_directed|hierarchical|circular|grid)$"
    ),
    save_layout: bool = Query(False),
    layout_name: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Apply layout algorithm to topology data."""
    # This would implement various layout algorithms
    # For now, return a simple force-directed layout

    import random
    import math

    nodes = layout_data.nodes
    edges = layout_data.edges

    if algorithm == "force_directed":
        # Simple force-directed layout simulation
        for i, node in enumerate(nodes):
            angle = (i / len(nodes)) * 2 * math.pi
            radius = 200
            node["coordinates"] = {
                "x": radius * math.cos(angle),
                "y": radius * math.sin(angle),
            }

    elif algorithm == "hierarchical":
        # Simple hierarchical layout
        levels = {}
        for node in nodes:
            level = 0  # Would calculate actual hierarchy level
            if level not in levels:
                levels[level] = []
            levels[level].append(node)

        y_offset = 0
        for level, level_nodes in levels.items():
            x_offset = -(len(level_nodes) - 1) * 100 / 2
            for node in level_nodes:
                node["coordinates"] = {"x": x_offset, "y": y_offset}
                x_offset += 100
            y_offset += 150

    elif algorithm == "circular":
        # Circular layout
        for i, node in enumerate(nodes):
            angle = (i / len(nodes)) * 2 * math.pi
            radius = 250
            node["coordinates"] = {
                "x": radius * math.cos(angle),
                "y": radius * math.sin(angle),
            }

    elif algorithm == "grid":
        # Grid layout
        grid_size = math.ceil(math.sqrt(len(nodes)))
        for i, node in enumerate(nodes):
            row = i // grid_size
            col = i % grid_size
            node["coordinates"] = {
                "x": col * 150 - (grid_size - 1) * 75,
                "y": row * 150 - (grid_size - 1) * 75,
            }

    return {
        "nodes": nodes,
        "edges": edges,
        "algorithm_used": algorithm,
        "layout_applied_at": datetime.utcnow(),
    }


# Network Diagrams


@router.post("/diagrams", response_model=NetworkDiagramResponse)
async def create_network_diagram(
    diagram_data: Dict[str, Any], db: AsyncSession = Depends(get_db)
):
    """Create a new network diagram."""
    db_diagram = NetworkDiagram(**diagram_data)
    db.add(db_diagram)
    await db.commit()
    await db.refresh(db_diagram)
    return NetworkDiagramResponse.model_validate(db_diagram)


@router.get("/diagrams", response_model=List[NetworkDiagramResponse])
async def list_network_diagrams(
    diagram_type: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)
):
    """List network diagrams."""
    query = select(NetworkDiagram)

    if diagram_type:
        query = query.where(NetworkDiagram.diagram_type == diagram_type)

    result = await db.execute(query)
    diagrams = result.scalars().all()

    return [NetworkDiagramResponse.model_validate(diagram) for diagram in diagrams]


@router.get("/diagrams/{diagram_id}", response_model=NetworkDiagramResponse)
async def get_network_diagram(
    diagram_id: str = Path(...), db: AsyncSession = Depends(get_db)
):
    """Get a specific network diagram."""
    result = await db.execute(
        select(NetworkDiagram).where(NetworkDiagram.id == diagram_id)
    )
    diagram = result.scalar_one_or_none()

    if not diagram:
        raise HTTPException(status_code=404, detail="Network diagram not found")

    return NetworkDiagramResponse.model_validate(diagram)


# Geographic Network Maps


@router.get("/maps", response_model=List[NetworkMapResponse])
async def list_network_maps(
    map_type: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)
):
    """List network maps."""
    query = select(NetworkMap)

    if map_type:
        query = query.where(NetworkMap.map_type == map_type)

    result = await db.execute(query)
    maps = result.scalars().all()

    return [NetworkMapResponse.model_validate(map_obj) for map_obj in maps]


@router.get("/maps/{map_id}/data")
async def get_network_map_data(
    map_id: str = Path(...),
    include_devices: bool = Query(True),
    include_locations: bool = Query(True),
    include_coverage: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """Get data for a network map."""
    # Get map configuration
    map_result = await db.execute(select(NetworkMap).where(NetworkMap.id == map_id))
    network_map = map_result.scalar_one_or_none()

    if not network_map:
        raise HTTPException(status_code=404, detail="Network map not found")

    map_data = {
        "map_config": {
            "center": {
                "lat": network_map.center_latitude,
                "lon": network_map.center_longitude,
            },
            "zoom": network_map.default_zoom,
            "base_map": network_map.base_map_provider,
        },
        "layers": [],
    }

    # Add device layer
    if include_devices and network_map.show_device_markers:
        devices_result = await db.execute(
            select(NetworkDevice).where(NetworkDevice.management_ip.isnot(None))
        )
        devices = devices_result.scalars().all()

        device_markers = []
        for device in devices:
            # In a real implementation, you would have lat/lon coordinates for devices
            device_markers.append(
                {
                    "id": str(device.id),
                    "name": device.name,
                    "type": device.device_type,
                    "status": device.status,
                    "coordinates": {
                        "lat": 0.0,  # Would come from device location
                        "lon": 0.0,
                    },
                    "popup_data": {
                        "title": device.name,
                        "vendor": device.vendor,
                        "model": device.model,
                        "ip": (
                            str(device.management_ip) if device.management_ip else None
                        ),
                        "status": device.status,
                    },
                }
            )

        map_data["layers"].append(
            {"type": "markers", "name": "Network Devices", "data": device_markers}
        )

    # Add location layer
    if include_locations:
        locations_result = await db.execute(
            select(NetworkLocation).where(
                and_(
                    NetworkLocation.latitude.isnot(None),
                    NetworkLocation.longitude.isnot(None),
                )
            )
        )
        locations = locations_result.scalars().all()

        location_markers = []
        for location in locations:
            location_markers.append(
                {
                    "id": str(location.id),
                    "name": location.name,
                    "type": location.location_type,
                    "coordinates": {
                        "lat": float(location.latitude),
                        "lon": float(location.longitude),
                    },
                    "popup_data": {
                        "title": location.name,
                        "type": location.location_type,
                        "address": location.full_address,
                        "contact": location.contact_person,
                    },
                }
            )

        map_data["layers"].append(
            {"type": "markers", "name": "Network Locations", "data": location_markers}
        )

    return map_data


# Real-time Data Endpoints


@router.get("/realtime/device-status")
async def get_realtime_device_status(
    device_ids: Optional[List[str]] = Query(None), db: AsyncSession = Depends(get_db)
):
    """Get real-time device status data."""
    query = select(NetworkDevice)

    if device_ids:
        query = query.where(NetworkDevice.id.in_(device_ids))

    result = await db.execute(query)
    devices = result.scalars().all()

    status_data = []
    for device in devices:
        status_data.append(
            {
                "device_id": str(device.id),
                "name": device.name,
                "status": device.status,
                "uptime": (
                    device.uptime_seconds if hasattr(device, "uptime_seconds") else None
                ),
                "last_seen": device.updated_at.isoformat(),
                "cpu_usage": None,  # Would come from latest metrics
                "memory_usage": None,  # Would come from latest metrics
                "interface_count": 0,  # Would be calculated
            }
        )

    return {
        "devices": status_data,
        "timestamp": datetime.utcnow(),
        "total_devices": len(status_data),
    }


@router.get("/realtime/network-metrics")
async def get_realtime_network_metrics(
    metric_names: List[str] = Query(...),
    device_ids: Optional[List[str]] = Query(None),
    time_range: int = Query(3600, description="Time range in seconds"),
    db: AsyncSession = Depends(get_db),
):
    """Get real-time network metrics."""
    # This would query the metrics table for recent data
    # For now, return sample data

    current_time = datetime.utcnow()

    metrics_data = {"metrics": [], "time_range": time_range, "timestamp": current_time}

    for metric_name in metric_names:
        metric_data = {
            "name": metric_name,
            "unit": "percent" if "usage" in metric_name else "count",
            "data_points": [
                {
                    "timestamp": current_time.isoformat(),
                    "value": 75.5,  # Sample value
                    "device_id": device_ids[0] if device_ids else "sample",
                }
            ],
        }
        metrics_data["metrics"].append(metric_data)

    return metrics_data


@router.get("/alerts/visualization-data")
async def get_alert_visualization_data(
    severity_filter: Optional[List[str]] = Query(None),
    time_range: int = Query(86400, description="Time range in seconds"),
    group_by: str = Query("severity", regex="^(severity|device_type|location)$"),
    db: AsyncSession = Depends(get_db),
):
    """Get alert data for visualization."""
    # This would query alerts from the database
    # For now, return sample data

    alert_data = {
        "summary": {
            "total_alerts": 45,
            "critical": 5,
            "high": 12,
            "medium": 18,
            "low": 8,
            "info": 2,
        },
        "grouped_data": [
            {"group": "critical", "count": 5, "percentage": 11.1},
            {"group": "high", "count": 12, "percentage": 26.7},
            {"group": "medium", "count": 18, "percentage": 40.0},
            {"group": "low", "count": 8, "percentage": 17.8},
            {"group": "info", "count": 2, "percentage": 4.4},
        ],
        "time_series": [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "critical": 5,
                "high": 12,
                "medium": 18,
                "low": 8,
                "info": 2,
            }
        ],
        "group_by": group_by,
        "time_range": time_range,
        "generated_at": datetime.utcnow(),
    }

    return alert_data


# Dashboard Templates


@router.get("/templates/dashboards")
async def list_dashboard_templates(
    category: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)
):
    """List available dashboard templates."""
    # Return predefined dashboard templates
    templates = [
        {
            "id": "network_overview",
            "name": "Network Overview",
            "category": "monitoring",
            "description": "Comprehensive network status and performance overview",
            "preview_url": "/static/templates/network_overview_preview.png",
            "widgets": [
                {
                    "type": "counter",
                    "title": "Total Devices",
                    "position": {"x": 0, "y": 0, "w": 3, "h": 2},
                },
                {
                    "type": "counter",
                    "title": "Active Alerts",
                    "position": {"x": 3, "y": 0, "w": 3, "h": 2},
                },
                {
                    "type": "pie_chart",
                    "title": "Device Status",
                    "position": {"x": 6, "y": 0, "w": 6, "h": 4},
                },
                {
                    "type": "line_chart",
                    "title": "Network Traffic",
                    "position": {"x": 0, "y": 2, "w": 6, "h": 4},
                },
                {
                    "type": "alert_list",
                    "title": "Recent Alerts",
                    "position": {"x": 0, "y": 6, "w": 12, "h": 4},
                },
            ],
        },
        {
            "id": "device_monitoring",
            "name": "Device Monitoring",
            "category": "monitoring",
            "description": "Detailed device health and performance monitoring",
            "preview_url": "/static/templates/device_monitoring_preview.png",
            "widgets": [
                {
                    "type": "gauge",
                    "title": "CPU Usage",
                    "position": {"x": 0, "y": 0, "w": 3, "h": 3},
                },
                {
                    "type": "gauge",
                    "title": "Memory Usage",
                    "position": {"x": 3, "y": 0, "w": 3, "h": 3},
                },
                {
                    "type": "gauge",
                    "title": "Temperature",
                    "position": {"x": 6, "y": 0, "w": 3, "h": 3},
                },
                {
                    "type": "line_chart",
                    "title": "Interface Traffic",
                    "position": {"x": 0, "y": 3, "w": 9, "h": 4},
                },
                {
                    "type": "table",
                    "title": "Interface Status",
                    "position": {"x": 9, "y": 0, "w": 3, "h": 7},
                },
            ],
        },
        {
            "id": "geographic_view",
            "name": "Geographic Network View",
            "category": "geographic",
            "description": "Geographic visualization of network infrastructure",
            "preview_url": "/static/templates/geographic_view_preview.png",
            "widgets": [
                {
                    "type": "map",
                    "title": "Network Map",
                    "position": {"x": 0, "y": 0, "w": 12, "h": 8},
                },
                {
                    "type": "device_list",
                    "title": "Nearby Devices",
                    "position": {"x": 0, "y": 8, "w": 6, "h": 4},
                },
                {
                    "type": "counter",
                    "title": "Coverage Areas",
                    "position": {"x": 6, "y": 8, "w": 3, "h": 2},
                },
                {
                    "type": "counter",
                    "title": "Service Points",
                    "position": {"x": 9, "y": 8, "w": 3, "h": 2},
                },
            ],
        },
    ]

    if category:
        templates = [t for t in templates if t["category"] == category]

    return templates
