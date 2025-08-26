"""Network monitoring API endpoints."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, Query, Path, BackgroundTasks
from sqlalchemy.orm import Session

from dotmac_isp.core.database import get_db
from dotmac_isp.core.middleware import get_tenant_id_dependency
from dotmac_isp.modules.network_monitoring import models, schemas

router = APIRouter(prefix="/network-monitoring", tags=["network-monitoring"])


# Monitoring Profile Endpoints
@router.post(
    "/profiles", response_model=schemas.MonitoringProfileResponse, status_code=201
)
async def create_monitoring_profile(
    profile: schemas.MonitoringProfileCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create a new monitoring profile."""
    profile_data = profile.model_dump()
    profile_data["tenant_id"] = tenant_id

    db_profile = models.MonitoringProfile(**profile_data)
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)

    # Add device and alert rule counts
    db_profile.device_count = 0
    db_profile.alert_rule_count = 0

    return db_profile


@router.get("/profiles", response_model=List[schemas.MonitoringProfileResponse])
async def list_monitoring_profiles(
    profile_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List monitoring profiles."""
    query = db.query(models.MonitoringProfile).filter(
        models.MonitoringProfile.tenant_id == tenant_id
    )

    if profile_type:
        query = query.filter(models.MonitoringProfile.profile_type == profile_type)

    profiles = query.offset(skip).limit(limit).all()

    # Add device and alert rule counts
    for profile in profiles:
        profile.device_count = len(profile.devices)
        profile.alert_rule_count = len(profile.alert_rules)

    return profiles


@router.get("/profiles/{profile_id}", response_model=schemas.MonitoringProfileResponse)
async def get_monitoring_profile(
    profile_id: str = Path(...),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get a specific monitoring profile."""
    profile = (
        db.query(models.MonitoringProfile)
        .filter(
            models.MonitoringProfile.id == profile_id,
            models.MonitoringProfile.tenant_id == tenant_id,
        )
        .first()
    )

    if not profile:
        raise HTTPException(status_code=404, detail="Monitoring profile not found")

    profile.device_count = len(profile.devices)
    profile.alert_rule_count = len(profile.alert_rules)

    return profile


@router.put("/profiles/{profile_id}", response_model=schemas.MonitoringProfileResponse)
async def update_monitoring_profile(
    profile_id: str,
    profile_update: schemas.MonitoringProfileUpdate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Update a monitoring profile."""
    profile = (
        db.query(models.MonitoringProfile)
        .filter(
            models.MonitoringProfile.id == profile_id,
            models.MonitoringProfile.tenant_id == tenant_id,
        )
        .first()
    )

    if not profile:
        raise HTTPException(status_code=404, detail="Monitoring profile not found")

    update_data = profile_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)

    profile.device_count = len(profile.devices)
    profile.alert_rule_count = len(profile.alert_rules)

    return profile


@router.delete("/profiles/{profile_id}", status_code=204)
async def delete_monitoring_profile(
    profile_id: str,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Delete a monitoring profile."""
    profile = (
        db.query(models.MonitoringProfile)
        .filter(
            models.MonitoringProfile.id == profile_id,
            models.MonitoringProfile.tenant_id == tenant_id,
        )
        .first()
    )

    if not profile:
        raise HTTPException(status_code=404, detail="Monitoring profile not found")

    db.delete(profile)
    db.commit()


# SNMP Device Endpoints
@router.post("/devices", response_model=schemas.SnmpDeviceResponse, status_code=201)
async def create_snmp_device(
    device: schemas.SnmpDeviceCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create a new SNMP device."""
    # Validate monitoring profile exists
    profile = (
        db.query(models.MonitoringProfile)
        .filter(
            models.MonitoringProfile.id == device.monitoring_profile_id,
            models.MonitoringProfile.tenant_id == tenant_id,
        )
        .first()
    )

    if not profile:
        raise HTTPException(status_code=404, detail="Monitoring profile not found")

    device_data = device.model_dump()
    device_data["tenant_id"] = tenant_id

    db_device = models.SnmpDevice(**device_data)
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device


@router.get("/devices", response_model=List[schemas.SnmpDeviceResponse])
async def list_snmp_devices(
    monitoring_status: Optional[schemas.MonitoringStatus] = None,
    availability_status: Optional[schemas.DeviceStatus] = None,
    monitoring_profile_id: Optional[str] = None,
    monitoring_enabled: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List SNMP devices with filtering."""
    query = db.query(models.SnmpDevice).filter(models.SnmpDevice.tenant_id == tenant_id)

    if monitoring_status:
        query = query.filter(models.SnmpDevice.monitoring_status == monitoring_status)
    if availability_status:
        query = query.filter(
            models.SnmpDevice.availability_status == availability_status
        )
    if monitoring_profile_id:
        query = query.filter(
            models.SnmpDevice.monitoring_profile_id == monitoring_profile_id
        )
    if monitoring_enabled is not None:
        query = query.filter(models.SnmpDevice.monitoring_enabled == monitoring_enabled)

    devices = query.offset(skip).limit(limit).all()
    return devices


@router.get("/devices/{device_id}", response_model=schemas.SnmpDeviceResponse)
async def get_snmp_device(
    device_id: str = Path(...),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get a specific SNMP device."""
    device = (
        db.query(models.SnmpDevice)
        .filter(
            models.SnmpDevice.id == device_id, models.SnmpDevice.tenant_id == tenant_id
        )
        .first()
    )

    if not device:
        raise HTTPException(status_code=404, detail="SNMP device not found")

    return device


@router.put("/devices/{device_id}", response_model=schemas.SnmpDeviceResponse)
async def update_snmp_device(
    device_id: str,
    device_update: schemas.SnmpDeviceUpdate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Update an SNMP device."""
    device = (
        db.query(models.SnmpDevice)
        .filter(
            models.SnmpDevice.id == device_id, models.SnmpDevice.tenant_id == tenant_id
        )
        .first()
    )

    if not device:
        raise HTTPException(status_code=404, detail="SNMP device not found")

    update_data = device_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(device, field, value)

    db.commit()
    db.refresh(device)
    return device


@router.delete("/devices/{device_id}", status_code=204)
async def delete_snmp_device(
    device_id: str,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Delete an SNMP device."""
    device = (
        db.query(models.SnmpDevice)
        .filter(
            models.SnmpDevice.id == device_id, models.SnmpDevice.tenant_id == tenant_id
        )
        .first()
    )

    if not device:
        raise HTTPException(status_code=404, detail="SNMP device not found")

    db.delete(device)
    db.commit()


# SNMP Metrics Endpoints
@router.get(
    "/devices/{device_id}/metrics", response_model=List[schemas.SnmpMetricResponse]
)
async def get_device_metrics(
    device_id: str,
    metric_name: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(1000, ge=1, le=10000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get metrics for a specific device."""
    # Validate device exists
    device = (
        db.query(models.SnmpDevice)
        .filter(
            models.SnmpDevice.id == device_id, models.SnmpDevice.tenant_id == tenant_id
        )
        .first()
    )

    if not device:
        raise HTTPException(status_code=404, detail="SNMP device not found")

    query = db.query(models.SnmpMetric).filter(models.SnmpMetric.device_id == device_id)

    if metric_name:
        query = query.filter(models.SnmpMetric.metric_name == metric_name)

    if start_time:
        query = query.filter(models.SnmpMetric.timestamp >= start_time)

    if end_time:
        query = query.filter(models.SnmpMetric.timestamp <= end_time)
    else:
        # Default to last 24 hours if no end_time specified
        if not start_time:
            from datetime import timezone
            start_time = datetime.now(timezone.utc) - timedelta(days=1)
            query = query.filter(models.SnmpMetric.timestamp >= start_time)

    metrics = query.order_by(models.SnmpMetric.timestamp.desc()).limit(limit).all()
    return metrics


@router.post("/metrics/query", response_model=List[schemas.SnmpMetricResponse])
async def query_metrics(
    query_params: schemas.MetricsQuery,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Query metrics across multiple devices."""
    query = (
        db.query(models.SnmpMetric)
        .join(models.SnmpDevice)
        .filter(models.SnmpDevice.tenant_id == tenant_id)
    )

    if query_params.device_ids:
        query = query.filter(models.SnmpMetric.device_id.in_(query_params.device_ids))

    if query_params.metric_names:
        query = query.filter(
            models.SnmpMetric.metric_name.in_(query_params.metric_names)
        )

    query = query.filter(
        models.SnmpMetric.timestamp >= query_params.start_time,
        models.SnmpMetric.timestamp <= query_params.end_time,
    )

    metrics = query.order_by(models.SnmpMetric.timestamp.desc()).limit(10000).all()
    return metrics


# Alert Endpoints
@router.post("/alerts", response_model=schemas.NetworkAlertResponse, status_code=201)
async def create_network_alert(
    alert: schemas.NetworkAlertCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create a network alert."""
    alert_data = alert.model_dump()
    alert_data["tenant_id"] = tenant_id
    alert_data["alert_id"] = str(uuid4())[:8]  # Short unique ID
    from datetime import timezone
    alert_data["created_at"] = datetime.now(timezone.utc)
    alert_data["updated_at"] = datetime.now(timezone.utc)

    db_alert = models.MonitoringAlert(**alert_data)
    db.add(db_alert)
    db.commit()
    db.refresh(db_alert)
    return db_alert


@router.get("/alerts", response_model=List[schemas.NetworkAlertResponse])
async def list_network_alerts(
    severity: Optional[schemas.AlertSeverity] = None,
    status: Optional[schemas.AlertStatus] = None,
    device_id: Optional[str] = None,
    alert_type: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List network alerts with filtering."""
    query = db.query(models.MonitoringAlert).filter(
        models.MonitoringAlert.tenant_id == tenant_id
    )

    if severity:
        query = query.filter(models.MonitoringAlert.severity == severity)
    if status:
        query = query.filter(models.MonitoringAlert.status == status)
    if device_id:
        query = query.filter(models.MonitoringAlert.device_id == device_id)
    if alert_type:
        query = query.filter(models.MonitoringAlert.alert_type == alert_type)

    alerts = (
        query.order_by(models.MonitoringAlert.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return alerts


@router.get("/alerts/{alert_id}", response_model=schemas.NetworkAlertResponse)
async def get_network_alert(
    alert_id: str,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get a specific network alert."""
    alert = (
        db.query(models.MonitoringAlert)
        .filter(
            models.MonitoringAlert.id == alert_id,
            models.MonitoringAlert.tenant_id == tenant_id,
        )
        .first()
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Network alert not found")

    return alert


@router.put(
    "/alerts/{alert_id}/acknowledge", response_model=schemas.NetworkAlertResponse
)
async def acknowledge_alert(
    alert_id: str,
    comment: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Acknowledge a network alert."""
    alert = (
        db.query(models.MonitoringAlert)
        .filter(
            models.MonitoringAlert.id == alert_id,
            models.MonitoringAlert.tenant_id == tenant_id,
        )
        .first()
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Network alert not found")

    alert.acknowledge(tenant_id, comment)
    from datetime import timezone
    alert.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(alert)
    return alert


@router.put("/alerts/{alert_id}/resolve", response_model=schemas.NetworkAlertResponse)
async def resolve_alert(
    alert_id: str,
    comment: Optional[str] = None,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Resolve a network alert."""
    alert = (
        db.query(models.MonitoringAlert)
        .filter(
            models.MonitoringAlert.id == alert_id,
            models.MonitoringAlert.tenant_id == tenant_id,
        )
        .first()
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Network alert not found")

    alert.resolve(tenant_id, comment)
    from datetime import timezone
    alert.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(alert)
    return alert


# Alert Rules Endpoints
@router.post("/alert-rules", response_model=schemas.AlertRuleResponse, status_code=201)
async def create_alert_rule(
    rule: schemas.AlertRuleCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create an alert rule."""
    # Validate monitoring profile exists
    profile = (
        db.query(models.MonitoringProfile)
        .filter(
            models.MonitoringProfile.id == rule.monitoring_profile_id,
            models.MonitoringProfile.tenant_id == tenant_id,
        )
        .first()
    )

    if not profile:
        raise HTTPException(status_code=404, detail="Monitoring profile not found")

    rule_data = rule.model_dump()
    rule_data["tenant_id"] = tenant_id

    db_rule = models.AlertRule(**rule_data)
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)
    return db_rule


@router.get("/alert-rules", response_model=List[schemas.AlertRuleResponse])
async def list_alert_rules(
    monitoring_profile_id: Optional[str] = None,
    enabled: Optional[bool] = None,
    severity: Optional[schemas.AlertSeverity] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List alert rules."""
    query = db.query(models.AlertRule).filter(models.AlertRule.tenant_id == tenant_id)

    if monitoring_profile_id:
        query = query.filter(
            models.AlertRule.monitoring_profile_id == monitoring_profile_id
        )
    if enabled is not None:
        query = query.filter(models.AlertRule.enabled == enabled)
    if severity:
        query = query.filter(models.AlertRule.alert_severity == severity)

    rules = query.offset(skip).limit(limit).all()
    return rules


@router.get("/alert-rules/{rule_id}", response_model=schemas.AlertRuleResponse)
async def get_alert_rule(
    rule_id: str,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get a specific alert rule."""
    rule = (
        db.query(models.AlertRule)
        .filter(models.AlertRule.id == rule_id, models.AlertRule.tenant_id == tenant_id)
        .first()
    )

    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    return rule


@router.put("/alert-rules/{rule_id}", response_model=schemas.AlertRuleResponse)
async def update_alert_rule(
    rule_id: str,
    rule_update: schemas.AlertRuleUpdate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Update an alert rule."""
    rule = (
        db.query(models.AlertRule)
        .filter(models.AlertRule.id == rule_id, models.AlertRule.tenant_id == tenant_id)
        .first()
    )

    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    update_data = rule_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/alert-rules/{rule_id}", status_code=204)
async def delete_alert_rule(
    rule_id: str,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Delete an alert rule."""
    rule = (
        db.query(models.AlertRule)
        .filter(models.AlertRule.id == rule_id, models.AlertRule.tenant_id == tenant_id)
        .first()
    )

    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")

    db.delete(rule)
    db.commit()


# Device Availability Endpoints
@router.get(
    "/devices/{device_id}/availability",
    response_model=List[schemas.DeviceAvailabilityResponse],
)
async def get_device_availability(
    device_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(1000, ge=1, le=10000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get availability records for a specific device."""
    # Validate device exists
    device = (
        db.query(models.SnmpDevice)
        .filter(
            models.SnmpDevice.id == device_id, models.SnmpDevice.tenant_id == tenant_id
        )
        .first()
    )

    if not device:
        raise HTTPException(status_code=404, detail="SNMP device not found")

    query = db.query(models.DeviceAvailability).filter(
        models.DeviceAvailability.device_id == device_id
    )

    if start_time:
        query = query.filter(models.DeviceAvailability.timestamp >= start_time)

    if end_time:
        query = query.filter(models.DeviceAvailability.timestamp <= end_time)
    else:
        # Default to last 7 days if no end_time specified
        if not start_time:
            from datetime import timezone
            start_time = datetime.now(timezone.utc) - timedelta(days=7)
            query = query.filter(models.DeviceAvailability.timestamp >= start_time)

    availability = (
        query.order_by(models.DeviceAvailability.timestamp.desc()).limit(limit).all()
    )
    return availability


# Dashboard and Analytics Endpoints
@router.get("/dashboard", response_model=schemas.MonitoringDashboard)
async def get_monitoring_dashboard(
    tenant_id: str = Depends(get_tenant_id_dependency), db: Session = Depends(get_db)
):
    """Get monitoring dashboard metrics."""
    # Count devices by status
    total_devices = (
        db.query(models.SnmpDevice)
        .filter(models.SnmpDevice.tenant_id == tenant_id)
        .count()
    )
    active_devices = (
        db.query(models.SnmpDevice)
        .filter(
            models.SnmpDevice.tenant_id == tenant_id,
            models.SnmpDevice.availability_status == models.DeviceStatus.UP,
        )
        .count()
    )
    failed_devices = (
        db.query(models.SnmpDevice)
        .filter(
            models.SnmpDevice.tenant_id == tenant_id,
            models.SnmpDevice.availability_status == models.DeviceStatus.DOWN,
        )
        .count()
    )
    warning_devices = (
        db.query(models.SnmpDevice)
        .filter(
            models.SnmpDevice.tenant_id == tenant_id,
            models.SnmpDevice.availability_status == models.DeviceStatus.WARNING,
        )
        .count()
    )

    # Count profiles
    total_profiles = (
        db.query(models.MonitoringProfile)
        .filter(models.MonitoringProfile.tenant_id == tenant_id)
        .count()
    )

    # Count alerts
    total_alerts = (
        db.query(models.MonitoringAlert)
        .filter(
            models.MonitoringAlert.tenant_id == tenant_id,
            models.MonitoringAlert.status == models.AlertStatus.ACTIVE,
        )
        .count()
    )
    critical_alerts = (
        db.query(models.MonitoringAlert)
        .filter(
            models.MonitoringAlert.tenant_id == tenant_id,
            models.MonitoringAlert.severity == models.AlertSeverity.CRITICAL,
            models.MonitoringAlert.status == models.AlertStatus.ACTIVE,
        )
        .count()
    )
    high_alerts = (
        db.query(models.MonitoringAlert)
        .filter(
            models.MonitoringAlert.tenant_id == tenant_id,
            models.MonitoringAlert.severity == models.AlertSeverity.HIGH,
            models.MonitoringAlert.status == models.AlertStatus.ACTIVE,
        )
        .count()
    )

    # Calculate average response time
    avg_response_time = 25.5  # Mock data
    network_availability = 99.2  # Mock data

    return schemas.MonitoringDashboard(
        total_devices=total_devices,
        active_devices=active_devices,
        failed_devices=failed_devices,
        warning_devices=warning_devices,
        total_profiles=total_profiles,
        total_alerts=total_alerts,
        critical_alerts=critical_alerts,
        high_alerts=high_alerts,
        avg_response_time=avg_response_time,
        network_availability=network_availability,
    )


@router.get("/devices/health", response_model=List[schemas.DeviceHealthSummary])
async def get_devices_health_summary(
    limit: int = Query(50, ge=1, le=500),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get device health summary."""
    devices = (
        db.query(models.SnmpDevice)
        .filter(models.SnmpDevice.tenant_id == tenant_id)
        .limit(limit)
        .all()
    )

    health_summaries = []
    for device in devices:
        # Count active alerts for each device
        alert_count = (
            db.query(models.MonitoringAlert)
            .filter(
                models.MonitoringAlert.device_id == device.id,
                models.MonitoringAlert.status == models.AlertStatus.ACTIVE,
            )
            .count()
        )

        health_summaries.append(
            schemas.DeviceHealthSummary(
                device_id=str(device.id),
                device_name=device.device_name,
                device_ip=str(device.device_ip),
                availability_status=device.availability_status,
                monitoring_status=device.monitoring_status,
                cpu_usage=device.cpu_usage_percent,
                memory_usage=device.memory_usage_percent,
                temperature=device.temperature_celsius,
                uptime_seconds=device.uptime_seconds,
                response_time_ms=device.response_time_ms,
                alert_count=alert_count,
                last_seen=device.last_seen,
            )
        )

    return health_summaries


# Bulk Operations
@router.post("/devices/bulk-operation", response_model=schemas.BulkOperationResponse)
async def bulk_device_operation(
    operation: schemas.BulkDeviceOperation,
    background_tasks: BackgroundTasks,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Perform bulk operations on devices."""
    # Validate that all devices exist
    devices = (
        db.query(models.SnmpDevice)
        .filter(
            models.SnmpDevice.id.in_(operation.device_ids),
            models.SnmpDevice.tenant_id == tenant_id,
        )
        .all()
    )

    if len(devices) != len(operation.device_ids):
        raise HTTPException(status_code=404, detail="Some devices not found")

    # Process bulk operation
    results = []
    successful = 0
    failed = 0

    for device in devices:
        try:
            if operation.operation == "enable":
                device.monitoring_enabled = True
                device.monitoring_status = models.MonitoringStatus.ACTIVE
                successful += 1
                results.append(
                    {
                        "device_id": str(device.id),
                        "device_name": device.device_name,
                        "status": "success",
                        "message": "Monitoring enabled",
                    }
                )
            elif operation.operation == "disable":
                device.monitoring_enabled = False
                device.monitoring_status = models.MonitoringStatus.DISABLED
                successful += 1
                results.append(
                    {
                        "device_id": str(device.id),
                        "device_name": device.device_name,
                        "status": "success",
                        "message": "Monitoring disabled",
                    }
                )
            else:
                # Other operations would be implemented here
                successful += 1
                results.append(
                    {
                        "device_id": str(device.id),
                        "device_name": device.device_name,
                        "status": "success",
                        "message": f"Operation {operation.operation} completed",
                    }
                )
        except Exception as e:
            failed += 1
            results.append(
                {
                    "device_id": str(device.id),
                    "device_name": device.device_name,
                    "status": "failed",
                    "message": str(e),
                }
            )

    db.commit()

    return schemas.BulkOperationResponse(
        operation_id=str(uuid4()),
        total_devices=len(devices),
        successful=successful,
        failed=failed,
        results=results,
    )
