"""
Tenant Management Service - Core business logic for ISP customer lifecycle management.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from uuid import UUID, uuid4

from sqlalchemy import and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select

from .models import (
    Tenant,
    TenantStatus,
    TenantConfiguration,
    TenantDeployment,
    TenantUsageMetrics,
)
from .schemas import (
    TenantCreate,
    TenantUpdate,
    TenantOnboardingRequest,
    TenantConfigurationCreate,
    TenantConfigurationUpdate,
    TenantHealthStatus,
)

logger = logging.getLogger(__name__)


class TenantManagementService:
    """
    Service for managing ISP customer tenants with multi-tenant isolation.
    
    This service handles the complete lifecycle of ISP customers from
    onboarding to cancellation, including resource management, billing
    integration, and tenant isolation enforcement.
    """
    
    def __init__(self, db_session: AsyncSession):
        self.db = db_session
    
    async def create_tenant(self, tenant_data: TenantCreate, created_by: Optional[str] = None) -> Tenant:
        """
        Create a new tenant with proper multi-tenant isolation setup.
        
        Args:
            tenant_data: Tenant creation data
            created_by: User ID who created the tenant
            
        Returns:
            Created tenant instance
        """
        # Generate unique tenant ID
        tenant_id = f"tenant_{uuid4().hex[:12]}"
        
        # Create tenant record
        tenant = Tenant(
            tenant_id=tenant_id,
            name=tenant_data.name,
            display_name=tenant_data.display_name,
            description=tenant_data.description,
            primary_contact_email=tenant_data.primary_contact_email,
            primary_contact_name=tenant_data.primary_contact_name,
            business_phone=tenant_data.business_phone,
            business_address=tenant_data.business_address,
            subscription_tier=tenant_data.subscription_tier,
            billing_email=tenant_data.billing_email,
            billing_cycle=tenant_data.billing_cycle,
            custom_domain=tenant_data.custom_domain,
            ssl_enabled=tenant_data.ssl_enabled,
            backup_retention_days=tenant_data.backup_retention_days,
            max_customers=tenant_data.max_customers,
            max_services=tenant_data.max_services,
            max_storage_gb=tenant_data.max_storage_gb,
            max_bandwidth_mbps=tenant_data.max_bandwidth_mbps,
            isolation_level=tenant_data.isolation_level,
            metadata=tenant_data.metadata or {},
            custom_settings=tenant_data.custom_settings or {},
            status=TenantStatus.PENDING,
        )
        
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        
        logger.info(f"Created new tenant: {tenant.tenant_id} ({tenant.display_name})")
        
        return tenant
    
    async def get_tenant_by_id(self, tenant_id: str, include_configs: bool = False) -> Optional[Tenant]:
        """
        Get tenant by tenant ID with optional configurations.
        
        Args:
            tenant_id: Tenant identifier
            include_configs: Whether to include tenant configurations
            
        Returns:
            Tenant instance or None if not found
        """
        query = select(Tenant).where(Tenant.tenant_id == tenant_id)
        
        if include_configs:
            query = query.options(selectinload(Tenant.configurations))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_tenant_by_uuid(self, tenant_uuid: UUID, include_configs: bool = False) -> Optional[Tenant]:
        """Get tenant by UUID."""
        query = select(Tenant).where(Tenant.id == tenant_uuid)
        
        if include_configs:
            query = query.options(selectinload(Tenant.configurations))
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def list_tenants(
        self,
        status: Optional[TenantStatus] = None,
        subscription_tier: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
        search_query: Optional[str] = None,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> Tuple[List[Tenant], int]:
        """
        List tenants with filtering, pagination, and search.
        
        Args:
            status: Filter by tenant status
            subscription_tier: Filter by subscription tier
            page: Page number (1-based)
            page_size: Items per page
            search_query: Search in name, display_name, or email
            order_by: Field to order by
            order_desc: Whether to order descending
            
        Returns:
            Tuple of (tenants list, total count)
        """
        query = select(Tenant)
        count_query = select(func.count(Tenant.id))
        
        # Apply filters
        filters = []
        if status:
            filters.append(Tenant.status == status)
        if subscription_tier:
            filters.append(Tenant.subscription_tier == subscription_tier)
        if search_query:
            search_filter = or_(
                Tenant.name.ilike(f"%{search_query}%"),
                Tenant.display_name.ilike(f"%{search_query}%"),
                Tenant.primary_contact_email.ilike(f"%{search_query}%"),
            )
            filters.append(search_filter)
        
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))
        
        # Apply ordering
        order_field = getattr(Tenant, order_by, Tenant.created_at)
        if order_desc:
            query = query.order_by(desc(order_field))
        else:
            query = query.order_by(order_field)
        
        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)
        
        # Execute queries
        tenants_result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        
        tenants = tenants_result.scalars().all()
        total_count = count_result.scalar()
        
        return tenants, total_count
    
    async def update_tenant(self, tenant_id: str, tenant_data: TenantUpdate, updated_by: Optional[str] = None) -> Optional[Tenant]:
        """
        Update tenant information.
        
        Args:
            tenant_id: Tenant identifier
            tenant_data: Update data
            updated_by: User ID who updated the tenant
            
        Returns:
            Updated tenant instance or None if not found
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None
        
        # Update fields that have values
        update_data = tenant_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(tenant, field, value)
        
        tenant.updated_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(tenant)
        
        logger.info(f"Updated tenant: {tenant.tenant_id} by {updated_by}")
        
        return tenant
    
    async def update_tenant_status(
        self,
        tenant_id: str,
        new_status: TenantStatus,
        reason: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> Optional[Tenant]:
        """
        Update tenant status with proper lifecycle tracking.
        
        Args:
            tenant_id: Tenant identifier
            new_status: New status to set
            reason: Reason for status change
            updated_by: User who made the change
            
        Returns:
            Updated tenant or None if not found
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None
        
        old_status = tenant.status
        tenant.status = new_status
        tenant.updated_at = datetime.utcnow()
        
        # Update lifecycle timestamps
        if new_status == TenantStatus.ACTIVE and old_status != TenantStatus.ACTIVE:
            tenant.activated_at = datetime.utcnow()
            tenant.suspended_at = None
        elif new_status == TenantStatus.SUSPENDED:
            tenant.suspended_at = datetime.utcnow()
        elif new_status == TenantStatus.CANCELLED:
            tenant.cancelled_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(tenant)
        
        logger.info(
            f"Updated tenant {tenant.tenant_id} status from {old_status} to {new_status}"
            f"{f' (reason: {reason})' if reason else ''} by {updated_by}"
        )
        
        return tenant
    
    async def delete_tenant(self, tenant_id: str, deleted_by: Optional[str] = None) -> bool:
        """
        Soft delete a tenant by setting status to CANCELLED.
        
        Args:
            tenant_id: Tenant identifier
            deleted_by: User who deleted the tenant
            
        Returns:
            True if deleted, False if not found
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return False
        
        tenant.status = TenantStatus.CANCELLED
        tenant.cancelled_at = datetime.utcnow()
        tenant.updated_at = datetime.utcnow()
        
        await self.db.commit()
        
        logger.info(f"Deleted (cancelled) tenant: {tenant.tenant_id} by {deleted_by}")
        
        return True
    
    async def onboard_tenant(self, onboarding_request: TenantOnboardingRequest, created_by: Optional[str] = None) -> Tenant:
        """
        Complete tenant onboarding workflow.
        
        This method handles the full onboarding process including:
        - Tenant creation
        - Configuration setup
        - Infrastructure provisioning request
        - Initial deployment setup
        
        Args:
            onboarding_request: Complete onboarding request data
            created_by: User who initiated onboarding
            
        Returns:
            Created tenant with initial configurations
        """
        # Create the tenant
        tenant = await self.create_tenant(onboarding_request.tenant_info, created_by)
        
        # Set up initial configurations
        configurations = []
        
        # Deployment preferences
        deployment_config = TenantConfigurationCreate(
            category="deployment",
            configuration_key="preferences",
            configuration_value={
                "cloud_provider": onboarding_request.preferred_cloud_provider,
                "region": onboarding_request.preferred_region,
                "instance_size": onboarding_request.instance_size,
            },
        )
        configurations.append(deployment_config)
        
        # Feature configuration
        if onboarding_request.enabled_features:
            feature_config = TenantConfigurationCreate(
                category="features",
                configuration_key="enabled_features",
                configuration_value={"features": onboarding_request.enabled_features},
            )
            configurations.append(feature_config)
        
        # Branding configuration
        if onboarding_request.branding_config:
            branding_config = TenantConfigurationCreate(
                category="branding",
                configuration_key="branding_settings",
                configuration_value=onboarding_request.branding_config,
            )
            configurations.append(branding_config)
        
        # Integration requirements
        if onboarding_request.integration_requirements:
            integration_config = TenantConfigurationCreate(
                category="integrations",
                configuration_key="requirements",
                configuration_value=onboarding_request.integration_requirements,
            )
            configurations.append(integration_config)
        
        # Create all configurations
        for config in configurations:
            await self.create_tenant_configuration(tenant.id, config, created_by)
        
        logger.info(f"Completed onboarding for tenant: {tenant.tenant_id}")
        
        return tenant
    
    async def create_tenant_configuration(
        self,
        tenant_uuid: UUID,
        config_data: TenantConfigurationCreate,
        created_by: Optional[str] = None,
    ) -> TenantConfiguration:
        """Create a tenant configuration."""
        config = TenantConfiguration(
            tenant_id=tenant_uuid,
            category=config_data.category,
            configuration_key=config_data.configuration_key,
            configuration_value=config_data.configuration_value,
            is_active=config_data.is_active,
            created_by=created_by,
        )
        
        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)
        
        return config
    
    async def get_tenant_configurations(
        self,
        tenant_id: str,
        category: Optional[str] = None,
        active_only: bool = True,
    ) -> List[TenantConfiguration]:
        """Get tenant configurations with optional filtering."""
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return []
        
        query = select(TenantConfiguration).where(TenantConfiguration.tenant_id == tenant.id)
        
        if category:
            query = query.where(TenantConfiguration.category == category)
        if active_only:
            query = query.where(TenantConfiguration.is_active == True)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_tenant_health_status(self, tenant_id: str) -> Optional[TenantHealthStatus]:
        """
        Calculate and return tenant health status.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Tenant health status or None if tenant not found
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return None
        
        # Get latest metrics for health calculation
        metrics_query = (
            select(TenantUsageMetrics)
            .where(TenantUsageMetrics.tenant_id == tenant.id)
            .order_by(desc(TenantUsageMetrics.metric_date))
            .limit(1)
        )
        result = await self.db.execute(metrics_query)
        latest_metrics = result.scalar_one_or_none()
        
        # Calculate health score based on various factors
        health_score = self._calculate_health_score(tenant, latest_metrics)
        
        # Determine resource utilization
        resource_utilization = {}
        if latest_metrics:
            if tenant.max_customers > 0:
                resource_utilization["customers"] = (latest_metrics.active_customers / tenant.max_customers) * 100
            if tenant.max_storage_gb > 0:
                resource_utilization["storage"] = (latest_metrics.storage_used_gb / tenant.max_storage_gb) * 100
        
        # Mock alerts and issues (in real implementation, these would come from monitoring)
        active_alerts = 0
        critical_issues = 0
        recommendations = []
        
        if tenant.status != TenantStatus.ACTIVE:
            critical_issues += 1
            recommendations.append(f"Tenant is in {tenant.status.value} status")
        
        if latest_metrics and latest_metrics.uptime_percentage and latest_metrics.uptime_percentage < 9900:  # < 99%
            active_alerts += 1
            recommendations.append("Low uptime detected - check infrastructure health")
        
        return TenantHealthStatus(
            tenant_id=tenant.tenant_id,
            status=tenant.status,
            last_health_check=datetime.utcnow(),
            health_score=health_score,
            uptime_percentage=latest_metrics.uptime_percentage / 100 if latest_metrics and latest_metrics.uptime_percentage else None,
            response_time_ms=latest_metrics.avg_response_time_ms if latest_metrics else None,
            error_rate=latest_metrics.error_rate_percentage / 100 if latest_metrics and latest_metrics.error_rate_percentage else None,
            resource_utilization=resource_utilization,
            active_alerts=active_alerts,
            critical_issues=critical_issues,
            recommendations=recommendations,
        )
    
    def _calculate_health_score(self, tenant: Tenant, metrics: Optional[TenantUsageMetrics]) -> int:
        """
        Calculate tenant health score (0-100).
        
        Args:
            tenant: Tenant instance
            metrics: Latest usage metrics
            
        Returns:
            Health score from 0-100
        """
        score = 100
        
        # Status penalties
        if tenant.status == TenantStatus.SUSPENDED:
            score -= 50
        elif tenant.status == TenantStatus.MAINTENANCE:
            score -= 20
        elif tenant.status == TenantStatus.FAILED:
            score = 0
        elif tenant.status == TenantStatus.CANCELLED:
            score = 0
        elif tenant.status != TenantStatus.ACTIVE:
            score -= 30
        
        if metrics:
            # Uptime score (0-30 points)
            if metrics.uptime_percentage is not None:
                uptime_score = min(30, (metrics.uptime_percentage / 10000) * 30)
                score = score - 30 + uptime_score
            
            # Performance score (0-20 points)
            if metrics.avg_response_time_ms is not None:
                if metrics.avg_response_time_ms <= 200:
                    perf_score = 20
                elif metrics.avg_response_time_ms <= 500:
                    perf_score = 15
                elif metrics.avg_response_time_ms <= 1000:
                    perf_score = 10
                else:
                    perf_score = 5
                score = score - 20 + perf_score
            
            # Error rate penalty
            if metrics.error_rate_percentage is not None:
                error_penalty = min(15, (metrics.error_rate_percentage / 100) * 15)
                score -= error_penalty
        
        return max(0, min(100, int(score)))
    
    async def get_tenant_usage_summary(self, tenant_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get tenant usage summary for specified period.
        
        Args:
            tenant_id: Tenant identifier
            days: Number of days to include in summary
            
        Returns:
            Usage summary dictionary
        """
        tenant = await self.get_tenant_by_id(tenant_id)
        if not tenant:
            return {}
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # Get metrics for the period
        metrics_query = (
            select(TenantUsageMetrics)
            .where(
                and_(
                    TenantUsageMetrics.tenant_id == tenant.id,
                    TenantUsageMetrics.metric_date >= since_date,
                )
            )
            .order_by(TenantUsageMetrics.metric_date)
        )
        result = await self.db.execute(metrics_query)
        metrics = result.scalars().all()
        
        if not metrics:
            return {"message": "No usage data available"}
        
        # Calculate summary statistics
        latest_metrics = metrics[-1]
        total_api_requests = sum(m.api_requests for m in metrics)
        avg_response_time = sum(m.avg_response_time_ms or 0 for m in metrics if m.avg_response_time_ms) / len([m for m in metrics if m.avg_response_time_ms])
        avg_uptime = sum(m.uptime_percentage or 0 for m in metrics if m.uptime_percentage) / len([m for m in metrics if m.uptime_percentage])
        
        return {
            "tenant_id": tenant.tenant_id,
            "period_days": days,
            "current_usage": {
                "active_customers": latest_metrics.active_customers,
                "active_services": latest_metrics.active_services,
                "storage_used_gb": latest_metrics.storage_used_gb,
                "bandwidth_used_gb": latest_metrics.bandwidth_used_gb,
            },
            "limits": {
                "max_customers": tenant.max_customers,
                "max_services": tenant.max_services,
                "max_storage_gb": tenant.max_storage_gb,
                "max_bandwidth_mbps": tenant.max_bandwidth_mbps,
            },
            "utilization": {
                "customers_percent": (latest_metrics.active_customers / tenant.max_customers * 100) if tenant.max_customers > 0 else 0,
                "services_percent": (latest_metrics.active_services / tenant.max_services * 100) if tenant.max_services > 0 else 0,
                "storage_percent": (latest_metrics.storage_used_gb / tenant.max_storage_gb * 100) if tenant.max_storage_gb > 0 else 0,
            },
            "performance": {
                "total_api_requests": total_api_requests,
                "avg_response_time_ms": int(avg_response_time) if avg_response_time else None,
                "avg_uptime_percent": round(avg_uptime / 100, 2) if avg_uptime else None,
            },
        }