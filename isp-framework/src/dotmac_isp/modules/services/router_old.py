"""Services API router for ISP service provisioning and management."""

from datetime import datetime, date, timedelta
from typing import List, Optional
from uuid import UUID, uuid4
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from dotmac_isp.core.database import get_db
from dotmac_isp.core.middleware import get_tenant_id_dependency
from . import schemas
from .models import (
    ServicePlan,
    ServiceInstance,
    ProvisioningTask,
    ServiceAddon,
    ServiceUsage,
    ServiceAlert,
    ServiceInstanceAddon,
    ServiceType,
    ServiceStatus,
    ProvisioningStatus,
)

router = APIRouter(tags=["services"])
services_router = router  # Export with expected name


# Service Plans Endpoints
@router.get("/plans", response_model=List[schemas.ServicePlanResponse])
async def list_service_plans(
    service_type: Optional[ServiceType] = None,
    is_active: Optional[bool] = None,
    is_public: Optional[bool] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List all service plans with optional filtering."""

    # Mock implementation - return sample service plans
    plans = [
        {
            "id": uuid4(),
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "plan_code": "FIBER_100",
            "name": "Fiber Internet 100Mbps",
            "description": "High-speed fiber internet with 100Mbps download and upload",
            "service_type": "internet",
            "monthly_price": Decimal("49.99"),
            "setup_fee": Decimal("99.00"),
            "cancellation_fee": Decimal("0.00"),
            "download_speed": 100,
            "upload_speed": 100,
            "bandwidth_unit": "mbps",
            "data_allowance": None,  # Unlimited
            "features": {"static_ip": True, "wifi_included": True},
            "technical_specs": {"technology": "fiber", "guaranteed_speed": "95%"},
            "is_active": True,
            "is_public": True,
            "requires_approval": False,
            "min_contract_months": 12,
            "max_contract_months": 24,
        },
        {
            "id": uuid4(),
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "plan_code": "DSL_25",
            "name": "DSL Internet 25Mbps",
            "description": "Affordable DSL internet connection",
            "service_type": "internet",
            "monthly_price": Decimal("29.99"),
            "setup_fee": Decimal("49.00"),
            "cancellation_fee": Decimal("25.00"),
            "download_speed": 25,
            "upload_speed": 5,
            "bandwidth_unit": "mbps",
            "data_allowance": 500,  # 500 GB
            "features": {"wifi_included": False},
            "technical_specs": {"technology": "dsl"},
            "is_active": True,
            "is_public": True,
            "requires_approval": False,
            "min_contract_months": 0,
            "max_contract_months": None,
        },
        {
            "id": uuid4(),
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "plan_code": "BUSINESS_FIBER_500",
            "name": "Business Fiber 500Mbps",
            "description": "Enterprise-grade fiber connection with SLA",
            "service_type": "internet",
            "monthly_price": Decimal("199.99"),
            "setup_fee": Decimal("299.00"),
            "cancellation_fee": Decimal("500.00"),
            "download_speed": 500,
            "upload_speed": 500,
            "bandwidth_unit": "mbps",
            "data_allowance": None,
            "features": {"static_ip": True, "sla_99_9": True, "priority_support": True},
            "technical_specs": {
                "technology": "fiber",
                "guaranteed_speed": "99%",
                "sla": "99.9%",
            },
            "is_active": True,
            "is_public": False,
            "requires_approval": True,
            "min_contract_months": 24,
            "max_contract_months": 36,
        },
    ]

    # Apply filters
    if service_type:
        plans = [p for p in plans if p["service_type"] == service_type.value]
    if is_active is not None:
        plans = [p for p in plans if p["is_active"] == is_active]
    if is_public is not None:
        plans = [p for p in plans if p["is_public"] == is_public]

    return plans[skip : skip + limit]


@router.post(
    "/plans",
    response_model=schemas.ServicePlanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_service_plan(
    plan: schemas.ServicePlanCreate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Create a new service plan."""

    # Mock implementation
    return {
        "id": uuid4(),
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        **plan.dict(),
    }


@router.get("/plans/{plan_id}", response_model=schemas.ServicePlanResponse)
async def get_service_plan(
    plan_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get a specific service plan by ID."""

    # Mock implementation
    return {
        "id": plan_id,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "plan_code": "FIBER_100",
        "name": "Fiber Internet 100Mbps",
        "description": "High-speed fiber internet",
        "service_type": "internet",
        "monthly_price": Decimal("49.99"),
        "setup_fee": Decimal("99.00"),
        "cancellation_fee": Decimal("0.00"),
        "download_speed": 100,
        "upload_speed": 100,
        "bandwidth_unit": "mbps",
        "data_allowance": None,
        "features": {"static_ip": True},
        "technical_specs": {"technology": "fiber"},
        "is_active": True,
        "is_public": True,
        "requires_approval": False,
        "min_contract_months": 12,
        "max_contract_months": 24,
    }


# Service Instances Endpoints
@router.get("/instances", response_model=List[schemas.ServiceInstanceResponse])
async def list_service_instances(
    customer_id: Optional[UUID] = None,
    status: Optional[ServiceStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List all service instances with optional filtering."""

    # Mock implementation
    instances = [
        {
            "id": uuid4(),
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "service_number": "SVC-001001",
            "customer_id": uuid4(),
            "service_plan_id": uuid4(),
            "status": "active",
            "activation_date": datetime.utcnow() - timedelta(days=30),
            "suspension_date": None,
            "cancellation_date": None,
            "service_address": "123 Main St, Anytown, ST 12345",
            "service_coordinates": "40.7128,-74.0060",
            "assigned_ip": "192.168.1.100",
            "assigned_vlan": 100,
            "router_config": {"ssid": "Customer_WiFi", "security": "WPA3"},
            "contract_start_date": date.today() - timedelta(days=30),
            "contract_end_date": date.today() + timedelta(days=335),
            "monthly_price": Decimal("49.99"),
            "notes": "Standard residential installation",
            "custom_config": {},
        },
        {
            "id": uuid4(),
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "service_number": "SVC-001002",
            "customer_id": uuid4(),
            "service_plan_id": uuid4(),
            "status": "pending",
            "activation_date": None,
            "suspension_date": None,
            "cancellation_date": None,
            "service_address": "456 Oak Ave, Anytown, ST 12345",
            "service_coordinates": "40.7589,-73.9851",
            "assigned_ip": None,
            "assigned_vlan": None,
            "router_config": {},
            "contract_start_date": date.today(),
            "contract_end_date": date.today() + timedelta(days=365),
            "monthly_price": Decimal("29.99"),
            "notes": "Awaiting technician installation",
            "custom_config": {},
        },
    ]

    # Apply filters
    if customer_id:
        instances = [i for i in instances if i["customer_id"] == customer_id]
    if status:
        instances = [i for i in instances if i["status"] == status.value]

    return instances[skip : skip + limit]


@router.post(
    "/activate",
    response_model=schemas.ServiceActivationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def activate_service(
    activation_request: schemas.ServiceActivationRequest,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Activate a new service for a customer."""

    # Mock implementation - create service instance and provisioning task
    service_instance_id = uuid4()
    provisioning_task_id = uuid4()

    service_instance = {
        "id": service_instance_id,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "service_number": f"SVC-{datetime.now().strftime('%y%m%d%H%M%S')}",
        "customer_id": activation_request.customer_id,
        "service_plan_id": activation_request.service_plan_id,
        "status": "pending",
        "activation_date": None,
        "suspension_date": None,
        "cancellation_date": None,
        "service_address": activation_request.service_address,
        "service_coordinates": activation_request.service_coordinates,
        "assigned_ip": None,
        "assigned_vlan": None,
        "router_config": {},
        "contract_start_date": date.today(),
        "contract_end_date": date.today()
        + timedelta(
            days=(
                activation_request.contract_months * 30
                if activation_request.contract_months
                else 365
            )
        ),
        "monthly_price": Decimal("49.99"),  # Would get from service plan
        "notes": activation_request.installation_notes or "",
        "custom_config": {},
    }

    provisioning_task = {
        "id": provisioning_task_id,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "service_instance_id": service_instance_id,
        "task_type": "activate",
        "description": f"Activate service at {activation_request.service_address}",
        "status": "pending",
        "scheduled_date": activation_request.preferred_installation_date,
        "started_date": None,
        "completed_date": None,
        "assigned_technician_id": None,
        "task_data": {
            "customer_id": str(activation_request.customer_id),
            "service_plan_id": str(activation_request.service_plan_id),
            "requested_addons": [
                str(addon_id) for addon_id in activation_request.requested_addons
            ],
            "installation_notes": activation_request.installation_notes,
        },
        "result_data": {},
        "error_message": None,
    }

    return {
        "service_instance": service_instance,
        "provisioning_task": provisioning_task,
        "estimated_activation": activation_request.preferred_installation_date
        or datetime.utcnow() + timedelta(days=7),
        "total_setup_cost": Decimal("99.00"),
        "monthly_recurring_cost": Decimal("49.99"),
    }


@router.put(
    "/instances/{instance_id}/modify", response_model=schemas.ServiceInstanceResponse
)
async def modify_service(
    instance_id: UUID,
    modification_request: schemas.ServiceModificationRequest,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Modify an existing service instance."""

    # Mock implementation
    return {
        "id": instance_id,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow() - timedelta(days=30),
        "updated_at": datetime.utcnow(),
        "service_number": "SVC-001001",
        "customer_id": uuid4(),
        "service_plan_id": modification_request.new_service_plan_id or uuid4(),
        "status": "active",
        "activation_date": datetime.utcnow() - timedelta(days=30),
        "suspension_date": None,
        "cancellation_date": None,
        "service_address": modification_request.change_address
        or "123 Main St, Anytown, ST 12345",
        "service_coordinates": "40.7128,-74.0060",
        "assigned_ip": "192.168.1.100",
        "assigned_vlan": 100,
        "router_config": {"ssid": "Customer_WiFi"},
        "contract_start_date": date.today() - timedelta(days=30),
        "contract_end_date": date.today() + timedelta(days=335),
        "monthly_price": Decimal("59.99"),  # Updated price
        "notes": modification_request.modification_notes or "",
        "custom_config": {},
    }


@router.put(
    "/instances/{instance_id}/suspend", response_model=schemas.ServiceInstanceResponse
)
async def suspend_service(
    instance_id: UUID,
    reason: str = Query(..., min_length=1, max_length=500),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Suspend a service instance."""

    # Mock implementation
    return {
        "id": instance_id,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow() - timedelta(days=30),
        "updated_at": datetime.utcnow(),
        "service_number": "SVC-001001",
        "customer_id": uuid4(),
        "service_plan_id": uuid4(),
        "status": "suspended",
        "activation_date": datetime.utcnow() - timedelta(days=30),
        "suspension_date": datetime.utcnow(),
        "cancellation_date": None,
        "service_address": "123 Main St, Anytown, ST 12345",
        "service_coordinates": "40.7128,-74.0060",
        "assigned_ip": "192.168.1.100",
        "assigned_vlan": 100,
        "router_config": {},
        "contract_start_date": date.today() - timedelta(days=30),
        "contract_end_date": date.today() + timedelta(days=335),
        "monthly_price": Decimal("49.99"),
        "notes": f"Suspended: {reason}",
        "custom_config": {},
    }


@router.put(
    "/instances/{instance_id}/reactivate",
    response_model=schemas.ServiceInstanceResponse,
)
async def reactivate_service(
    instance_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Reactivate a suspended service instance."""

    # Mock implementation
    return {
        "id": instance_id,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow() - timedelta(days=30),
        "updated_at": datetime.utcnow(),
        "service_number": "SVC-001001",
        "customer_id": uuid4(),
        "service_plan_id": uuid4(),
        "status": "active",
        "activation_date": datetime.utcnow() - timedelta(days=30),
        "suspension_date": None,
        "cancellation_date": None,
        "service_address": "123 Main St, Anytown, ST 12345",
        "service_coordinates": "40.7128,-74.0060",
        "assigned_ip": "192.168.1.100",
        "assigned_vlan": 100,
        "router_config": {"ssid": "Customer_WiFi"},
        "contract_start_date": date.today() - timedelta(days=30),
        "contract_end_date": date.today() + timedelta(days=335),
        "monthly_price": Decimal("49.99"),
        "notes": "Service reactivated",
        "custom_config": {},
    }


# Provisioning Tasks Endpoints
@router.get("/provisioning", response_model=List[schemas.ProvisioningTaskResponse])
async def list_provisioning_tasks(
    status: Optional[ProvisioningStatus] = None,
    technician_id: Optional[UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """List provisioning tasks with optional filtering."""

    # Mock implementation
    tasks = [
        {
            "id": uuid4(),
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow() - timedelta(hours=2),
            "updated_at": datetime.utcnow(),
            "service_instance_id": uuid4(),
            "task_type": "activate",
            "description": "Install fiber connection at customer premises",
            "status": "pending",
            "scheduled_date": datetime.utcnow() + timedelta(days=1),
            "started_date": None,
            "completed_date": None,
            "assigned_technician_id": uuid4(),
            "task_data": {
                "priority": "normal",
                "equipment_needed": ["modem", "router"],
            },
            "result_data": {},
            "error_message": None,
        },
        {
            "id": uuid4(),
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow() - timedelta(days=1),
            "updated_at": datetime.utcnow(),
            "service_instance_id": uuid4(),
            "task_type": "modify",
            "description": "Upgrade service speed to 200Mbps",
            "status": "completed",
            "scheduled_date": datetime.utcnow() - timedelta(hours=4),
            "started_date": datetime.utcnow() - timedelta(hours=4),
            "completed_date": datetime.utcnow() - timedelta(hours=2),
            "assigned_technician_id": uuid4(),
            "task_data": {"old_speed": "100Mbps", "new_speed": "200Mbps"},
            "result_data": {"success": True, "new_config_applied": True},
            "error_message": None,
        },
    ]

    # Apply filters
    if status:
        tasks = [t for t in tasks if t["status"] == status.value]
    if technician_id:
        tasks = [t for t in tasks if t["assigned_technician_id"] == technician_id]

    return tasks[skip : skip + limit]


@router.put("/provisioning/{task_id}", response_model=schemas.ProvisioningTaskResponse)
async def update_provisioning_task(
    task_id: UUID,
    task_update: schemas.ProvisioningTaskUpdate,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Update a provisioning task."""

    # Mock implementation
    return {
        "id": task_id,
        "tenant_id": tenant_id,
        "created_at": datetime.utcnow() - timedelta(hours=2),
        "updated_at": datetime.utcnow(),
        "service_instance_id": uuid4(),
        "task_type": "activate",
        "description": "Install fiber connection at customer premises",
        "status": task_update.status or "in_progress",
        "scheduled_date": task_update.scheduled_date,
        "started_date": (
            datetime.utcnow()
            if task_update.status == ProvisioningStatus.IN_PROGRESS
            else None
        ),
        "completed_date": (
            datetime.utcnow()
            if task_update.status == ProvisioningStatus.COMPLETED
            else None
        ),
        "assigned_technician_id": task_update.assigned_technician_id or uuid4(),
        "task_data": task_update.task_data or {},
        "result_data": task_update.result_data or {},
        "error_message": task_update.error_message,
    }


# Service Usage and Analytics
@router.get("/usage/{instance_id}", response_model=List[schemas.ServiceUsageResponse])
async def get_service_usage(
    instance_id: UUID,
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    period: str = Query("daily", pattern="^(daily|weekly|monthly)$"),
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get service usage data for a specific instance."""

    # Mock implementation
    usage_data = []
    start = start_date or date.today() - timedelta(days=7)
    end = end_date or date.today()

    current = start
    while current <= end:
        usage_data.append(
            {
                "id": uuid4(),
                "tenant_id": tenant_id,
                "created_at": datetime.combine(current, datetime.min.time()),
                "updated_at": datetime.combine(current, datetime.min.time()),
                "service_instance_id": instance_id,
                "usage_date": current,
                "usage_period": period,
                "data_downloaded": Decimal(
                    str(3000 + (hash(str(current)) % 2000))
                ),  # Random-ish data
                "data_uploaded": Decimal(str(500 + (hash(str(current)) % 300))),
                "total_data": Decimal(str(3500 + (hash(str(current)) % 2300))),
                "avg_download_speed": Decimal("95.5"),
                "avg_upload_speed": Decimal("94.2"),
                "peak_download_speed": Decimal("99.8"),
                "peak_upload_speed": Decimal("99.1"),
                "uptime_percentage": Decimal("99.9"),
                "downtime_minutes": 0,
                "additional_metrics": {"latency_ms": 12.5, "jitter_ms": 1.2},
            }
        )
        current += timedelta(days=1)

    return usage_data


# Dashboard and Analytics
@router.get("/dashboard", response_model=schemas.ServiceDashboard)
async def get_service_dashboard(
    tenant_id: str = Depends(get_tenant_id_dependency), db: Session = Depends(get_db)
):
    """Get service dashboard metrics."""

    # Mock implementation
    return {
        "total_services": 1250,
        "active_services": 1180,
        "pending_activations": 45,
        "suspended_services": 20,
        "cancelled_services": 5,
        "monthly_revenue": Decimal("89450.75"),
        "avg_service_value": Decimal("71.56"),
        "churn_rate": Decimal("2.3"),
        "most_popular_plans": [
            {
                "plan_code": "FIBER_100",
                "plan_name": "Fiber 100Mbps",
                "subscriber_count": 450,
            },
            {"plan_code": "DSL_25", "plan_name": "DSL 25Mbps", "subscriber_count": 380},
            {
                "plan_code": "FIBER_200",
                "plan_name": "Fiber 200Mbps",
                "subscriber_count": 240,
            },
        ],
    }


# Bulk Operations
@router.post("/bulk-operation", response_model=schemas.BulkServiceOperationResponse)
async def bulk_service_operation(
    operation: schemas.BulkServiceOperation,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Perform bulk operations on multiple services."""

    # Mock implementation
    results = []
    successful = 0
    failed = 0

    for service_id in operation.service_instance_ids:
        try:
            # Mock operation - assume most succeed
            if hash(str(service_id)) % 10 != 0:  # 90% success rate
                results.append(
                    {
                        "service_instance_id": str(service_id),
                        "status": "success",
                        "message": f"Operation {operation.operation} completed successfully",
                    }
                )
                successful += 1
            else:
                results.append(
                    {
                        "service_instance_id": str(service_id),
                        "status": "error",
                        "message": "Service not found or already in requested state",
                    }
                )
                failed += 1
        except Exception as e:
            results.append(
                {
                    "service_instance_id": str(service_id),
                    "status": "error",
                    "message": str(e),
                }
            )
            failed += 1

    return {
        "total_requested": len(operation.service_instance_ids),
        "successful": successful,
        "failed": failed,
        "results": results,
        "operation_id": uuid4(),
    }


# Service Performance Metrics
@router.get(
    "/performance/{instance_id}", response_model=schemas.ServicePerformanceMetrics
)
async def get_service_performance(
    instance_id: UUID,
    tenant_id: str = Depends(get_tenant_id_dependency),
    db: Session = Depends(get_db),
):
    """Get performance metrics for a specific service instance."""

    # Mock implementation
    return {
        "service_instance_id": instance_id,
        "avg_uptime": Decimal("99.85"),
        "avg_download_speed": Decimal("95.2"),
        "avg_upload_speed": Decimal("94.8"),
        "total_data_usage": Decimal("245.7"),  # GB
        "recent_alerts": 2,
        "last_outage": datetime.utcnow() - timedelta(days=15),
        "customer_satisfaction": Decimal("8.5"),
    }
