"""
Tenant Admin Customer Management API endpoints.
Provides customer management functionality for tenant portal.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.services.tenant_service import TenantService
from .auth_dependencies import get_current_tenant_user

logger = logging.getLogger(__name__)

# Response Models
class CustomerService(BaseModel):
    service_id: str
    service_type: str
    service_name: str
    status: str
    created_at: datetime
    last_updated: datetime
    configuration: Dict[str, Any] = {}

class Customer(BaseModel):
    customer_id: str
    email: str
    first_name: str
    last_name: str
    company_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[Dict[str, str]] = None
    status: str
    created_at: datetime
    last_login: Optional[datetime] = None
    services: List[CustomerService] = []
    total_services: int = 0
    monthly_recurring_revenue: float = 0.0
    last_payment: Optional[datetime] = None
    payment_status: str = "current"

class CustomerList(BaseModel):
    customers: List[Customer]
    total_count: int
    page: int
    page_size: int
    has_more: bool

class CustomerStats(BaseModel):
    total_customers: int
    active_customers: int
    new_customers_this_month: int
    churned_customers_this_month: int
    average_revenue_per_customer: float
    total_monthly_revenue: float
    customer_growth_rate: float
    churn_rate: float

# Create router
tenant_customer_router = APIRouter()

@tenant_customer_router.get("/", response_model=CustomerList)
async def list_customers(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, description="Search by email, name, or company"),
    status: Optional[str] = Query(None, description="Filter by customer status"),
    sort_by: str = Query("created_at", description="Sort by field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_tenant_user)
):
    """
    Get paginated list of customers for the tenant.
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        tenant_service = TenantService(db)
        
        # Get customers with pagination and filters
        customers_data = await tenant_service.get_tenant_customers(
            tenant_id=tenant_id,
            page=page,
            page_size=page_size,
            search=search,
            status_filter=status,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        customers = []
        for customer_data in customers_data.get("customers", []):
            # Get customer services
            services = await tenant_service.get_customer_services(
                tenant_id, 
                customer_data.get("id")
            )
            
            customer_services = []
            total_mrr = 0.0
            
            for service in services:
                customer_service = CustomerService(
                    service_id=str(service.get("id")),
                    service_type=service.get("service_type", "unknown"),
                    service_name=service.get("service_name", "Unknown Service"),
                    status=service.get("status", "unknown"),
                    created_at=service.get("created_at", datetime.utcnow()),
                    last_updated=service.get("updated_at", datetime.utcnow()),
                    configuration=service.get("configuration", {})
                )
                customer_services.append(customer_service)
                total_mrr += service.get("monthly_cost", 0.0)
            
            customer = Customer(
                customer_id=str(customer_data.get("id")),
                email=customer_data.get("email", ""),
                first_name=customer_data.get("first_name", ""),
                last_name=customer_data.get("last_name", ""),
                company_name=customer_data.get("company_name"),
                phone=customer_data.get("phone"),
                address=customer_data.get("address"),
                status=customer_data.get("status", "active"),
                created_at=customer_data.get("created_at", datetime.utcnow()),
                last_login=customer_data.get("last_login"),
                services=customer_services,
                total_services=len(customer_services),
                monthly_recurring_revenue=total_mrr,
                last_payment=customer_data.get("last_payment"),
                payment_status=customer_data.get("payment_status", "current")
            )
            customers.append(customer)
        
        total_count = customers_data.get("total_count", 0)
        has_more = (page * page_size) < total_count
        
        return CustomerList(
            customers=customers,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_more=has_more
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list customers for {current_user.get('tenant_id')}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer list"
        )


@tenant_customer_router.get("/stats", response_model=CustomerStats)
async def get_customer_stats(
    period_days: int = Query(30, ge=1, le=365, description="Period in days for calculations"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_tenant_user)
):
    """
    Get customer statistics and metrics for the tenant.
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        tenant_service = TenantService(db)
        
        # Get overall customer stats
        customer_metrics = await tenant_service.get_customer_metrics(tenant_id, period_days)
        
        # Calculate derived metrics
        total_customers = customer_metrics.get("total_customers", 0)
        active_customers = customer_metrics.get("active_customers", 0)
        new_customers = customer_metrics.get("new_customers", 0)
        churned_customers = customer_metrics.get("churned_customers", 0)
        total_mrr = customer_metrics.get("total_monthly_revenue", 0.0)
        
        # Calculate growth rate and churn rate
        previous_period_customers = customer_metrics.get("previous_period_customers", total_customers)
        if previous_period_customers > 0:
            growth_rate = ((total_customers - previous_period_customers) / previous_period_customers) * 100
        else:
            growth_rate = 0.0
        
        if total_customers > 0:
            churn_rate = (churned_customers / total_customers) * 100
            avg_revenue_per_customer = total_mrr / active_customers if active_customers > 0 else 0.0
        else:
            churn_rate = 0.0
            avg_revenue_per_customer = 0.0
        
        return CustomerStats(
            total_customers=total_customers,
            active_customers=active_customers,
            new_customers_this_month=new_customers,
            churned_customers_this_month=churned_customers,
            average_revenue_per_customer=avg_revenue_per_customer,
            total_monthly_revenue=total_mrr,
            customer_growth_rate=growth_rate,
            churn_rate=churn_rate
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get customer stats for {current_user.get('tenant_id')}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer statistics"
        )


@tenant_customer_router.get("/{customer_id}", response_model=Customer)
async def get_customer_details(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_tenant_user)
):
    """
    Get detailed information about a specific customer.
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        tenant_service = TenantService(db)
        
        # Get customer details
        customer_data = await tenant_service.get_customer_by_id(tenant_id, customer_id)
        
        if not customer_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        # Get customer services
        services = await tenant_service.get_customer_services(tenant_id, customer_id)
        
        customer_services = []
        total_mrr = 0.0
        
        for service in services:
            customer_service = CustomerService(
                service_id=str(service.get("id")),
                service_type=service.get("service_type", "unknown"),
                service_name=service.get("service_name", "Unknown Service"),
                status=service.get("status", "unknown"),
                created_at=service.get("created_at", datetime.utcnow()),
                last_updated=service.get("updated_at", datetime.utcnow()),
                configuration=service.get("configuration", {})
            )
            customer_services.append(customer_service)
            total_mrr += service.get("monthly_cost", 0.0)
        
        return Customer(
            customer_id=str(customer_data.get("id")),
            email=customer_data.get("email", ""),
            first_name=customer_data.get("first_name", ""),
            last_name=customer_data.get("last_name", ""),
            company_name=customer_data.get("company_name"),
            phone=customer_data.get("phone"),
            address=customer_data.get("address"),
            status=customer_data.get("status", "active"),
            created_at=customer_data.get("created_at", datetime.utcnow()),
            last_login=customer_data.get("last_login"),
            services=customer_services,
            total_services=len(customer_services),
            monthly_recurring_revenue=total_mrr,
            last_payment=customer_data.get("last_payment"),
            payment_status=customer_data.get("payment_status", "current")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get customer {customer_id} for {current_user.get('tenant_id')}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer details"
        )


@tenant_customer_router.get("/{customer_id}/services")
async def get_customer_services(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_tenant_user)
):
    """
    Get all services for a specific customer.
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        tenant_service = TenantService(db)
        
        # Verify customer exists and belongs to tenant
        customer = await tenant_service.get_customer_by_id(tenant_id, customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        # Get services
        services = await tenant_service.get_customer_services(tenant_id, customer_id)
        
        service_list = []
        for service in services:
            service_detail = {
                "service_id": str(service.get("id")),
                "service_type": service.get("service_type"),
                "service_name": service.get("service_name"),
                "status": service.get("status"),
                "monthly_cost": service.get("monthly_cost", 0.0),
                "setup_date": service.get("created_at"),
                "last_updated": service.get("updated_at"),
                "configuration": service.get("configuration", {}),
                "usage_stats": await tenant_service.get_service_usage_stats(
                    tenant_id, 
                    service.get("id")
                ),
                "billing_info": {
                    "last_invoice_date": service.get("last_invoice_date"),
                    "next_invoice_date": service.get("next_invoice_date"),
                    "payment_status": service.get("payment_status", "current")
                }
            }
            service_list.append(service_detail)
        
        return {
            "customer_id": customer_id,
            "services": service_list,
            "total_services": len(service_list),
            "total_monthly_cost": sum(s.get("monthly_cost", 0) for s in services)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get services for customer {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer services"
        )


@tenant_customer_router.get("/{customer_id}/usage")
async def get_customer_usage(
    customer_id: str,
    period_days: int = Query(30, ge=1, le=365, description="Usage period in days"),
    db: AsyncSession = Depends(get_db),
    current_user: Dict[str, Any] = Depends(get_current_tenant_user)
):
    """
    Get usage statistics for a specific customer.
    """
    try:
        tenant_id = current_user["tenant_id"]
        
        tenant_service = TenantService(db)
        
        # Verify customer exists
        customer = await tenant_service.get_customer_by_id(tenant_id, customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )
        
        # Get usage data
        usage_data = await tenant_service.get_customer_usage_summary(
            tenant_id, 
            customer_id, 
            period_days
        )
        
        period_start = datetime.utcnow() - timedelta(days=period_days)
        
        return {
            "customer_id": customer_id,
            "period_start": period_start,
            "period_end": datetime.utcnow(),
            "data_usage_gb": usage_data.get("data_usage_gb", 0.0),
            "api_requests": usage_data.get("api_requests", 0),
            "login_sessions": usage_data.get("login_sessions", 0),
            "support_tickets": usage_data.get("support_tickets", 0),
            "service_uptime_percentage": usage_data.get("uptime_percentage", 100.0),
            "average_response_time_ms": usage_data.get("avg_response_time", 50.0),
            "peak_concurrent_users": usage_data.get("peak_concurrent_users", 1),
            "usage_by_service": usage_data.get("usage_by_service", {}),
            "daily_usage": usage_data.get("daily_breakdown", []),
            "cost_breakdown": {
                "base_service_cost": usage_data.get("base_cost", 0.0),
                "usage_charges": usage_data.get("usage_charges", 0.0),
                "overage_charges": usage_data.get("overage_charges", 0.0),
                "total_cost": usage_data.get("total_cost", 0.0)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get usage for customer {customer_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customer usage"
        )