"""Network Integration API router."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Path, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_

from dotmac_isp.core.database import get_db
from dotmac_isp.modules.network_integration.models import (
    NetworkDevice,
    NetworkInterface,
    NetworkLocation,
    NetworkMetric,
    NetworkTopology,
    DeviceConfiguration,
    NetworkAlert,
    DeviceGroup,
    NetworkService,
    MaintenanceWindow,
)

from dotmac_isp.modules.network_integration.schemas import (
    NetworkDeviceCreate,
    NetworkDeviceUpdate,
    NetworkDeviceResponse,
    NetworkLocationCreate,
    NetworkLocationUpdate,
    NetworkLocationResponse,
    NetworkMetricResponse,
    NetworkTopologyResponse,
    DeviceConfigurationCreate,
    DeviceConfigurationResponse,
    NetworkAlertResponse,
    DeviceGroupCreate,
    DeviceGroupResponse,
    NetworkServiceCreate,
    NetworkServiceResponse,
    MaintenanceWindowCreate,
    MaintenanceWindowResponse,
    PaginatedNetworkDeviceResponse,
    PaginatedNetworkLocationResponse,
    PaginatedNetworkAlertResponse,
)
from datetime import timezone

router = APIRouter(prefix="/api/v1/network", tags=["Network Integration"])
network_router = router  # Export with expected name


# Network Device Management


@router.post("/devices", response_model=NetworkDeviceResponse)
async def create_network_device(
    device: NetworkDeviceCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new network device."""
    db_device = NetworkDevice(**device.model_dump())
    db.add(db_device)
    await db.commit()
    await db.refresh(db_device)
    return NetworkDeviceResponse.model_validate(db_device)


@router.get("/devices", response_model=PaginatedNetworkDeviceResponse)
async def list_network_devices(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    device_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    vendor: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List network devices with pagination and filtering."""
    query = select(NetworkDevice)

    # Apply filters
    filters = []
    if device_type:
        filters.append(NetworkDevice.device_type == device_type)
    if status:
        filters.append(NetworkDevice.status == status)
    if vendor:
        filters.append(NetworkDevice.vendor == vendor)
    if search:
        filters.append(
            or_(
                NetworkDevice.name.ilike(f"%{search}%"),
                NetworkDevice.hostname.ilike(f"%{search}%"),
                NetworkDevice.serial_number.ilike(f"%{search}%"),
            )
        )

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    devices = result.scalars().all()

    return PaginatedNetworkDeviceResponse(
        items=[NetworkDeviceResponse.model_validate(device) for device in devices],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page,
    )


@router.get("/devices/{device_id}", response_model=NetworkDeviceResponse)
async def get_network_device(
    device_id: str = Path(...), db: AsyncSession = Depends(get_db)
):
    """Get a specific network device by ID."""
    result = await db.execute(
        select(NetworkDevice).where(NetworkDevice.id == device_id)
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="Network device not found")

    return NetworkDeviceResponse.model_validate(device)


@router.put("/devices/{device_id}", response_model=NetworkDeviceResponse)
async def update_network_device(
    device_id: str = Path(...),
    device_update: NetworkDeviceUpdate = None,
    db: AsyncSession = Depends(get_db),
):
    """Update a network device."""
    result = await db.execute(
        select(NetworkDevice).where(NetworkDevice.id == device_id)
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="Network device not found")

    # Update device fields
    update_data = device_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)

    await db.commit()
    await db.refresh(device)

    return NetworkDeviceResponse.model_validate(device)


@router.delete("/devices/{device_id}")
async def delete_network_device(
    device_id: str = Path(...), db: AsyncSession = Depends(get_db)
):
    """Delete a network device."""
    result = await db.execute(
        select(NetworkDevice).where(NetworkDevice.id == device_id)
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="Network device not found")

    await db.delete(device)
    await db.commit()

    return {"message": "Network device deleted successfully"}


# Network Location Management


@router.post("/locations", response_model=NetworkLocationResponse)
async def create_network_location(
    location: NetworkLocationCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new network location."""
    db_location = NetworkLocation(**location.model_dump())
    db.add(db_location)
    await db.commit()
    await db.refresh(db_location)
    return NetworkLocationResponse.model_validate(db_location)


@router.get("/locations", response_model=PaginatedNetworkLocationResponse)
async def list_network_locations(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    location_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List network locations with pagination and filtering."""
    query = select(NetworkLocation)

    # Apply filters
    filters = []
    if location_type:
        filters.append(NetworkLocation.location_type == location_type)
    if search:
        filters.append(
            or_(
                NetworkLocation.name.ilike(f"%{search}%"),
                NetworkLocation.code.ilike(f"%{search}%"),
                NetworkLocation.city.ilike(f"%{search}%"),
            )
        )

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    locations = result.scalars().all()

    return PaginatedNetworkLocationResponse(
        items=[
            NetworkLocationResponse.model_validate(location) for location in locations
        ],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page,
    )


@router.get("/locations/{location_id}", response_model=NetworkLocationResponse)
async def get_network_location(
    location_id: str = Path(...), db: AsyncSession = Depends(get_db)
):
    """Get a specific network location by ID."""
    result = await db.execute(
        select(NetworkLocation).where(NetworkLocation.id == location_id)
    )
    location = result.scalar_one_or_none()

    if not location:
        raise HTTPException(status_code=404, detail="Network location not found")

    return NetworkLocationResponse.model_validate(location)


# Network Metrics and Monitoring


@router.get("/devices/{device_id}/metrics", response_model=List[NetworkMetricResponse])
async def get_device_metrics(
    device_id: str = Path(...),
    metric_name: Optional[str] = Query(None),
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Get metrics for a specific device."""
    query = select(NetworkMetric).where(NetworkMetric.device_id == device_id)

    # Apply filters
    if metric_name:
        query = query.where(NetworkMetric.metric_name == metric_name)
    if start_time:
        query = query.where(NetworkMetric.timestamp >= start_time)
    if end_time:
        query = query.where(NetworkMetric.timestamp <= end_time)

    query = query.order_by(NetworkMetric.timestamp.desc()).limit(limit)

    result = await db.execute(query)
    metrics = result.scalars().all()

    return [NetworkMetricResponse.model_validate(metric) for metric in metrics]


@router.get("/metrics/aggregated")
async def get_aggregated_metrics(
    metric_name: str = Query(...),
    aggregation: str = Query("avg", regex="^(avg|sum|min|max|count)$"),
    interval: str = Query("1h", regex="^(5m|15m|1h|6h|24h)$"),
    start_time: datetime = Query(...),
    end_time: datetime = Query(...),
    device_ids: Optional[List[str]] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated metrics data."""
    # This would implement time-series aggregation
    # For now, return a placeholder response
    return {
        "metric_name": metric_name,
        "aggregation": aggregation,
        "interval": interval,
        "data_points": [],
        "start_time": start_time,
        "end_time": end_time,
    }


# Network Topology


@router.get("/topology", response_model=List[NetworkTopologyResponse])
async def get_network_topology(
    device_id: Optional[str] = Query(None),
    connection_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get network topology information."""
    query = select(NetworkTopology)

    # Apply filters
    filters = []
    if device_id:
        filters.append(
            or_(
                NetworkTopology.parent_device_id == device_id,
                NetworkTopology.child_device_id == device_id,
            )
        )
    if connection_type:
        filters.append(NetworkTopology.connection_type == connection_type)

    if filters:
        query = query.where(and_(*filters))

    result = await db.execute(query)
    topology_entries = result.scalars().all()

    return [NetworkTopologyResponse.model_validate(entry) for entry in topology_entries]


# Device Configuration Management


@router.post(
    "/devices/{device_id}/configurations", response_model=DeviceConfigurationResponse
)
async def create_device_configuration(
    device_id: str = Path(...),
    configuration: DeviceConfigurationCreate = None,
    db: AsyncSession = Depends(get_db),
):
    """Create a new device configuration."""
    # Verify device exists
    device_result = await db.execute(
        select(NetworkDevice).where(NetworkDevice.id == device_id)
    )
    device = device_result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="Network device not found")

    config_data = configuration.model_dump()
    config_data["device_id"] = device_id

    db_config = DeviceConfiguration(**config_data)
    db.add(db_config)
    await db.commit()
    await db.refresh(db_config)

    return DeviceConfigurationResponse.model_validate(db_config)


@router.get(
    "/devices/{device_id}/configurations",
    response_model=List[DeviceConfigurationResponse],
)
async def list_device_configurations(
    device_id: str = Path(...),
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """List configurations for a device."""
    query = select(DeviceConfiguration).where(
        DeviceConfiguration.device_id == device_id
    )

    if active_only:
        query = query.where(DeviceConfiguration.is_active == True)

    query = query.order_by(DeviceConfiguration.created_at.desc())

    result = await db.execute(query)
    configurations = result.scalars().all()

    return [
        DeviceConfigurationResponse.model_validate(config) for config in configurations
    ]


# Network Alerts


@router.get("/alerts", response_model=PaginatedNetworkAlertResponse)
async def list_network_alerts(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    severity: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    device_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List network alerts with pagination and filtering."""
    query = select(NetworkAlert)

    # Apply filters
    filters = []
    if severity:
        filters.append(NetworkAlert.severity == severity)
    if is_active is not None:
        filters.append(NetworkAlert.is_active == is_active)
    if device_id:
        filters.append(NetworkAlert.device_id == device_id)

    if filters:
        query = query.where(and_(*filters))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply pagination
    offset = (page - 1) * per_page
    query = (
        query.offset(offset).limit(per_page).order_by(NetworkAlert.created_at.desc())
    )

    result = await db.execute(query)
    alerts = result.scalars().all()

    return PaginatedNetworkAlertResponse(
        items=[NetworkAlertResponse.model_validate(alert) for alert in alerts],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page,
    )


@router.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str = Path(...),
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Acknowledge a network alert."""
    result = await db.execute(select(NetworkAlert).where(NetworkAlert.id == alert_id))
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Network alert not found")

    alert.acknowledge(user_id)
    await db.commit()

    return {"message": "Alert acknowledged successfully"}


@router.post("/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: str = Path(...),
    user_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a network alert."""
    result = await db.execute(select(NetworkAlert).where(NetworkAlert.id == alert_id))
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(status_code=404, detail="Network alert not found")

    alert.resolve()
    await db.commit()

    return {"message": "Alert resolved successfully"}


# Device Groups


@router.post("/device-groups", response_model=DeviceGroupResponse)
async def create_device_group(
    group: DeviceGroupCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new device group."""
    db_group = DeviceGroup(**group.model_dump())
    db.add(db_group)
    await db.commit()
    await db.refresh(db_group)
    return DeviceGroupResponse.model_validate(db_group)


@router.get("/device-groups", response_model=List[DeviceGroupResponse])
async def list_device_groups(
    group_type: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)
):
    """List device groups."""
    query = select(DeviceGroup)

    if group_type:
        query = query.where(DeviceGroup.group_type == group_type)

    result = await db.execute(query)
    groups = result.scalars().all()

    return [DeviceGroupResponse.model_validate(group) for group in groups]


# Network Services


@router.post("/services", response_model=NetworkServiceResponse)
async def create_network_service(
    service: NetworkServiceCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new network service."""
    db_service = NetworkService(**service.model_dump())
    db.add(db_service)
    await db.commit()
    await db.refresh(db_service)
    return NetworkServiceResponse.model_validate(db_service)


@router.get("/services", response_model=List[NetworkServiceResponse])
async def list_network_services(
    service_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List network services."""
    query = select(NetworkService)

    filters = []
    if service_type:
        filters.append(NetworkService.service_type == service_type)
    if status:
        filters.append(NetworkService.status == status)

    if filters:
        query = query.where(and_(*filters))

    result = await db.execute(query)
    services = result.scalars().all()

    return [NetworkServiceResponse.model_validate(service) for service in services]


# Maintenance Windows


@router.post("/maintenance-windows", response_model=MaintenanceWindowResponse)
async def create_maintenance_window(
    window: MaintenanceWindowCreate, db: AsyncSession = Depends(get_db)
):
    """Create a new maintenance window."""
    db_window = MaintenanceWindow(**window.model_dump())
    db.add(db_window)
    await db.commit()
    await db.refresh(db_window)
    return MaintenanceWindowResponse.model_validate(db_window)


@router.get("/maintenance-windows", response_model=List[MaintenanceWindowResponse])
async def list_maintenance_windows(
    upcoming_only: bool = Query(False),
    maintenance_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """List maintenance windows."""
    query = select(MaintenanceWindow)

    filters = []
    if upcoming_only:
        filters.append(MaintenanceWindow.start_time >= datetime.now(timezone.utc))
    if maintenance_type:
        filters.append(MaintenanceWindow.maintenance_type == maintenance_type)

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(MaintenanceWindow.start_time)

    result = await db.execute(query)
    windows = result.scalars().all()

    return [MaintenanceWindowResponse.model_validate(window) for window in windows]


# Network Discovery and Health Checks


@router.post("/devices/{device_id}/discovery")
async def discover_device_interfaces(
    device_id: str = Path(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """Trigger interface discovery for a device."""
    # Verify device exists
    result = await db.execute(
        select(NetworkDevice).where(NetworkDevice.id == device_id)
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="Network device not found")

    # Add background task for discovery
    if background_tasks:
        background_tasks.add_task(run_interface_discovery, device_id)

    return {"message": "Interface discovery initiated", "device_id": device_id}


@router.post("/devices/{device_id}/health-check")
async def perform_device_health_check(
    device_id: str = Path(...),
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """Perform health check on a device."""
    # Verify device exists
    result = await db.execute(
        select(NetworkDevice).where(NetworkDevice.id == device_id)
    )
    device = result.scalar_one_or_none()

    if not device:
        raise HTTPException(status_code=404, detail="Network device not found")

    # Add background task for health check
    if background_tasks:
        background_tasks.add_task(run_device_health_check, device_id)

    return {"message": "Health check initiated", "device_id": device_id}


@router.get("/dashboard/summary")
async def get_network_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """Get network dashboard summary statistics."""
    # Get device counts by status
    device_status_query = select(
        NetworkDevice.status, func.count(NetworkDevice.id).label("count")
    ).group_by(NetworkDevice.status)

    device_status_result = await db.execute(device_status_query)
    device_status = {row.status: row.count for row in device_status_result}

    # Get active alerts count by severity
    alert_severity_query = (
        select(NetworkAlert.severity, func.count(NetworkAlert.id).label("count"))
        .where(NetworkAlert.is_active == True)
        .group_by(NetworkAlert.severity)
    )

    alert_severity_result = await db.execute(alert_severity_query)
    alert_severity = {row.severity: row.count for row in alert_severity_result}

    # Get total device count
    total_devices_result = await db.execute(select(func.count(NetworkDevice.id)))
    total_devices = total_devices_result.scalar()

    # Get total locations count
    total_locations_result = await db.execute(select(func.count(NetworkLocation.id)))
    total_locations = total_locations_result.scalar()

    return {
        "total_devices": total_devices,
        "total_locations": total_locations,
        "device_status": device_status,
        "alert_severity": alert_severity,
        "timestamp": datetime.now(timezone.utc),
    }


# Background task functions (these would be implemented in separate modules)


async def run_interface_discovery(device_id: str):
    """Background task to discover device interfaces."""
    # This would implement SNMP-based interface discovery
    pass


async def run_device_health_check(device_id: str):
    """Background task to perform device health check."""
    # This would implement comprehensive device health check
    pass
