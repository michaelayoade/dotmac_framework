"""
Customer repository for customer management operations.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, asc, desc, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ..models.customer import (
    Customer,
    CustomerService,
    CustomerStatus,
    CustomerUsageRecord,
    ServiceStatus,
    ServiceUsageRecord,
)
from ..repositories.base import BaseRepository


class CustomerRepository(BaseRepository[Customer]):
    """Repository for customer operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Customer)

    async def get_by_email(self, tenant_id: UUID, email: str) -> Optional[Customer]:
        """Get customer by email within tenant."""
        result = await self.db.execute(
            select(Customer).where(
                and_(Customer.tenant_id == tenant_id, Customer.email == email)
            )
        )
        return result.scalars().first()

    async def get_tenant_customers(
        self,
        tenant_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Dict[str, Any]:
        """Get paginated list of customers for a tenant with search and filtering."""

        # Base query
        query = select(Customer).where(Customer.tenant_id == tenant_id)

        # Apply search filter
        if search:
            search_term = f"%{search.lower()}%"
            query = query.where(
                or_(
                    func.lower(Customer.first_name).contains(search_term),
                    func.lower(Customer.last_name).contains(search_term),
                    func.lower(Customer.email).contains(search_term),
                    func.lower(Customer.company_name).contains(search_term),
                )
            )

        # Apply status filter
        if status_filter:
            query = query.where(Customer.status == status_filter)

        # Apply sorting
        sort_column = getattr(Customer, sort_by, Customer.created_at)
        if sort_order == "asc":
            query = query.order_by(asc(sort_column))
        else:
            query = query.order_by(desc(sort_column))

        # Count total results
        count_query = select(func.count(Customer.id)).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query with relationships loaded
        query = query.options(
            selectinload(Customer.services), selectinload(Customer.usage_records)
        )
        result = await self.db.execute(query)
        customers = result.scalars().all()

        return {
            "customers": customers,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total_count,
        }

    async def get_customer_metrics(
        self, tenant_id: UUID, period_days: int = 30
    ) -> Dict[str, Any]:
        """Get customer metrics and statistics for a tenant."""

        period_start = datetime.now(timezone.utc) - timedelta(days=period_days)

        # Total customers
        total_query = select(func.count(Customer.id)).where(
            Customer.tenant_id == tenant_id
        )
        total_result = await self.db.execute(total_query)
        total_customers = total_result.scalar() or 0

        # Active customers
        active_query = select(func.count(Customer.id)).where(
            and_(
                Customer.tenant_id == tenant_id,
                Customer.status == CustomerStatus.ACTIVE,
            )
        )
        active_result = await self.db.execute(active_query)
        active_customers = active_result.scalar() or 0

        # New customers in period
        new_query = select(func.count(Customer.id)).where(
            and_(Customer.tenant_id == tenant_id, Customer.created_at >= period_start)
        )
        new_result = await self.db.execute(new_query)
        new_customers = new_result.scalar() or 0

        # Churned customers (became inactive in period)
        churn_query = select(func.count(Customer.id)).where(
            and_(
                Customer.tenant_id == tenant_id,
                Customer.status != CustomerStatus.ACTIVE,
                Customer.updated_at >= period_start,
            )
        )
        churn_result = await self.db.execute(churn_query)
        churned_customers = churn_result.scalar() or 0

        # Total MRR (from active services)
        mrr_query = select(func.sum(CustomerService.monthly_cost)).where(
            and_(
                CustomerService.tenant_id == tenant_id,
                CustomerService.status == ServiceStatus.ACTIVE,
            )
        )
        mrr_result = await self.db.execute(mrr_query)
        total_mrr = float(mrr_result.scalar() or 0)

        # Previous period customers for growth calculation
        previous_period_start = period_start - timedelta(days=period_days)
        prev_query = select(func.count(Customer.id)).where(
            and_(
                Customer.tenant_id == tenant_id,
                Customer.created_at < period_start,
                Customer.created_at >= previous_period_start,
            )
        )
        prev_result = await self.db.execute(prev_query)
        previous_period_customers = prev_result.scalar() or 0

        return {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "new_customers": new_customers,
            "churned_customers": churned_customers,
            "total_monthly_revenue": total_mrr,
            "previous_period_customers": previous_period_customers + total_customers,
        }

    async def get_customer_with_services(
        self, tenant_id: UUID, customer_id: UUID
    ) -> Optional[Customer]:
        """Get customer with all services loaded."""
        result = await self.db.execute(
            select(Customer)
            .where(and_(Customer.tenant_id == tenant_id, Customer.id == customer_id))
            .options(
                selectinload(Customer.services), selectinload(Customer.usage_records)
            )
        )
        return result.scalars().first()

    async def get_customer_services(
        self, tenant_id: UUID, customer_id: UUID
    ) -> List[CustomerService]:
        """Get all services for a specific customer."""
        result = await self.db.execute(
            select(CustomerService)
            .where(
                and_(
                    CustomerService.tenant_id == tenant_id,
                    CustomerService.customer_id == customer_id,
                )
            )
            .options(selectinload(CustomerService.usage_records))
            .order_by(desc(CustomerService.created_at))
        )
        return result.scalars().all()

    async def get_customer_usage_summary(
        self, tenant_id: UUID, customer_id: UUID, period_days: int = 30
    ) -> Optional[CustomerUsageRecord]:
        """Get usage summary for a customer in the specified period."""

        period_start = datetime.now(timezone.utc) - timedelta(days=period_days)

        result = await self.db.execute(
            select(CustomerUsageRecord)
            .where(
                and_(
                    CustomerUsageRecord.tenant_id == tenant_id,
                    CustomerUsageRecord.customer_id == customer_id,
                    CustomerUsageRecord.period_start >= period_start,
                )
            )
            .order_by(desc(CustomerUsageRecord.period_start))
            .limit(1)
        )
        return result.scalars().first()


class CustomerServiceRepository(BaseRepository[CustomerService]):
    """Repository for customer service operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, CustomerService)

    async def get_service_usage_stats(
        self, tenant_id: UUID, service_id: UUID
    ) -> Dict[str, Any]:
        """Get usage statistics for a specific service."""

        # Get latest usage record
        usage_result = await self.db.execute(
            select(ServiceUsageRecord)
            .where(
                and_(
                    ServiceUsageRecord.tenant_id == tenant_id,
                    ServiceUsageRecord.service_id == service_id,
                )
            )
            .order_by(desc(ServiceUsageRecord.recorded_at))
            .limit(1)
        )
        latest_usage = usage_result.scalars().first()

        if latest_usage:
            return {
                "data_usage_gb": float(latest_usage.data_usage_gb),
                "monthly_usage_gb": float(latest_usage.monthly_usage_gb),
                "peak_usage_date": latest_usage.peak_usage_date,
                "uptime_percentage": float(latest_usage.uptime_percentage),
                "last_usage": latest_usage.last_usage,
                "response_time_ms": float(latest_usage.response_time_ms),
                "error_count": latest_usage.error_count,
                "success_count": latest_usage.success_count,
                "service_metrics": latest_usage.service_metrics,
            }
        else:
            # Return default/empty stats if no usage data
            return {
                "data_usage_gb": 0.0,
                "monthly_usage_gb": 0.0,
                "peak_usage_date": None,
                "uptime_percentage": 100.0,
                "last_usage": None,
                "response_time_ms": 0.0,
                "error_count": 0,
                "success_count": 0,
                "service_metrics": {},
            }
