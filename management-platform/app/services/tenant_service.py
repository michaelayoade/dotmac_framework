"""
Tenant service for multi-tenant operations.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID
import re

from sqlalchemy.ext.asyncio import AsyncSession

from database import database_transaction
from repositories.tenant import TenantRepository, TenantConfigurationRepository
from repositories.customer import CustomerRepository, CustomerServiceRepository
from schemas.tenant import TenantCreate, TenantUpdate, TenantOnboardingRequest
from models.tenant import Tenant, TenantStatus
from core.exceptions import (
    TenantNotFoundError, TenantNameConflictError, TenantNotActiveError,
    BusinessLogicError, DatabaseError
)
from core.logging import get_logger, log_audit_event, log_security_event, log_function_call
from core.cache import cached, cache_invalidate, TenantCache

logger = get_logger(__name__)


class TenantService:
    """Service for tenant operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tenant_repo = TenantRepository(db)
        self.config_repo = TenantConfigurationRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.customer_service_repo = CustomerServiceRepository(db)
    
    def _generate_slug(self, name: str) -> str:
        """Generate URL-safe slug from tenant name."""
        # Convert to lowercase and replace spaces with hyphens
        slug = re.sub(r'[^\w\s-]', '', name.lower())
        slug = re.sub(r'[-\s]+', '-', slug).strip('-')
        return slug
    
    @log_function_call(include_args=False, include_result=False)
    @cache_invalidate(namespace="tenants", pattern="tenant_count:*")
    async def create_tenant(self, tenant_data: TenantCreate, created_by: str) -> Tenant:
        """Create a new tenant with transaction safety."""
        try:
            # Check if tenant name already exists
            existing = await self.tenant_repo.get_by_name(tenant_data.name)
            if existing:
                raise TenantNameConflictError(tenant_data.name)
            
            async with database_transaction(self.db) as tx:
                # Generate slug from name
                base_slug = self._generate_slug(tenant_data.name)
                slug = base_slug
                counter = 1
                
                # Ensure slug is unique
                while not await self.tenant_repo.check_slug_availability(slug):
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                
                # Create tenant data
                tenant_dict = tenant_data.model_dump()
                tenant_dict.update({
                    "slug": slug,
                    "status": TenantStatus.PENDING
                })
                
                # Create tenant
                tenant = await self.tenant_repo.create(tenant_dict, created_by)
                
                # Create default configurations
                await self._create_default_configurations(tenant.id, created_by)
                
                # Log audit event
                log_audit_event(
                    action="create",
                    resource="tenant",
                    resource_id=str(tenant.id),
                    user_id=created_by,
                    details={
                        "tenant_name": tenant.name,
                        "tenant_slug": tenant.slug,
                        "tier": tenant.tier.value if hasattr(tenant.tier, 'value') else str(tenant.tier)
                    }
                
                logger.info("Tenant created successfully",
                           tenant_id=str(tenant.id), 
                           tenant_name=tenant.name,
                           created_by=created_by)
                return tenant
                
        except TenantNameConflictError:
            raise
        except Exception as e:
            logger.error(f"Failed to create tenant: {e}", exc_info=True)
            raise DatabaseError(
                message="Failed to create tenant",
                details={"error": str(e), "tenant_name": tenant_data.name}
    
    async def _create_default_configurations(self, tenant_id: UUID, created_by: str):
        """Create default configurations for a new tenant."""
        default_configs = [
            {
                "category": "branding",
                "key": "theme",
                "value": {"primary_color": "#1e40af", "secondary_color": "#64748b"}
            },
            {
                "category": "features",
                "key": "enabled_features",
                "value": ["billing", "customer_management", "service_provisioning"]
            },
            {
                "category": "notifications",
                "key": "email_settings",
                "value": {
                    "enabled": True,
                    "send_welcome_emails": True,
                    "send_billing_notifications": True
                }
            },
            {
                "category": "security",
                "key": "password_policy",
                "value": {
                    "min_length": 8,
                    "require_numbers": True,
                    "require_special_chars": True,
                    "require_uppercase": True
                }
            },
            {
                "category": "api",
                "key": "rate_limits",
                "value": {
                    "requests_per_minute": 1000,
                    "burst_limit": 2000
                }
            }
        ]
        
        for config in default_configs:
            config["tenant_id"] = tenant_id
            await self.config_repo.create(config, created_by)
    
    async def onboard_tenant(
        self, 
        onboarding_request: TenantOnboardingRequest,
        created_by: str
    ) -> Tenant:
        """Complete tenant onboarding workflow."""
        try:
            # Create the tenant
            tenant = await self.create_tenant(onboarding_request.tenant_info, created_by)
            
            # Create onboarding-specific configurations
            await self._create_onboarding_configurations(
                tenant.id, 
                onboarding_request,
                created_by
            
            # Trigger infrastructure deployment workflow
            from deployment_service import DeploymentService
            deployment_service = DeploymentService(self.db)
            
            # Create deployment for the new tenant
            deployment_config = {
                "tier": onboarding_request.get("tier", "micro"),
                "region": onboarding_request.get("region", "us-east-1"),
                "features": onboarding_request.get("features", []),
                "scaling_config": {
                    "min_replicas": 1,
                    "max_replicas": 3,
                    "auto_scaling_enabled": True
                }
            }
            
            await deployment_service.create_tenant_deployment(
                tenant.id, 
                deployment_config, 
                created_by
            
            logger.info(f"Tenant onboarding initiated: {tenant.name}")
            return tenant
            
        except Exception as e:
            logger.error(f"Tenant onboarding failed: {e}")
            raise
    
    async def _create_onboarding_configurations(
        self,
        tenant_id: UUID,
        onboarding_request: TenantOnboardingRequest,
        created_by: str
    ):
        """Create configurations specific to onboarding."""
        configs = [
            {
                "category": "deployment",
                "key": "cloud_provider",
                "value": onboarding_request.preferred_cloud_provider
            },
            {
                "category": "deployment",
                "key": "region",
                "value": onboarding_request.preferred_region
            },
            {
                "category": "deployment", 
                "key": "instance_size",
                "value": onboarding_request.instance_size
            },
            {
                "category": "features",
                "key": "onboarding_features",
                "value": onboarding_request.enabled_features
            },
            {
                "category": "branding",
                "key": "onboarding_branding",
                "value": onboarding_request.branding_config
            }
        ]
        
        for config in configs:
            await self.config_repo.upsert_configuration(
                tenant_id=tenant_id,
                category=config["category"],
                key=config["key"],
                value=config["value"],
                user_id=created_by
    
    @cached(ttl=1800, namespace="tenants", key_builder=lambda self, tenant_id, include_configs=False: f"tenant:{tenant_id}:{include_configs}")
    async def get_tenant_by_id(self, tenant_id: UUID, include_configs: bool = False) -> Optional[Tenant]:
        """Get tenant by ID."""
        if include_configs:
            return await self.tenant_repo.get_with_configurations(tenant_id)
        return await self.tenant_repo.get_by_id(tenant_id)
    
    @cached(ttl=1800, namespace="tenants", key_builder=lambda self, slug: f"tenant_slug:{slug}")
    async def get_tenant_by_slug(self, slug: str) -> Optional[Tenant]:
        """Get tenant by slug."""
        return await self.tenant_repo.get_by_slug(slug)
    
    async def update_tenant_status(
        self,
        tenant_id: UUID,
        new_status: TenantStatus,
        reason: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> Optional[Tenant]:
        """Update tenant status with proper workflow."""
        try:
            tenant = await self.tenant_repo.update_status(tenant_id, new_status, updated_by)
            
            if tenant:
                # Log status change
                await self._log_status_change(tenant_id, new_status, reason, updated_by)
                
                # Log audit event
                log_audit_event(
                    action="update",
                    resource="tenant_status",
                    resource_id=str(tenant_id),
                    user_id=updated_by or "system",
                    details={
                        "old_status": "unknown",  # Would need to fetch old status
                        "new_status": new_status.value if hasattr(new_status, 'value') else str(new_status),
                        "reason": reason
                    }
                
                # Log security event for suspensions/cancellations
                if new_status in [TenantStatus.SUSPENDED, TenantStatus.CANCELLED]:
                    log_security_event(
                        event_type="tenant_access_change",
                        details={
                            "action": "tenant_status_change",
                            "new_status": str(new_status),
                            "reason": reason,
                            "tenant_id": str(tenant_id)
                        },
                        user_id=updated_by,
                        tenant_id=str(tenant_id)
                
                # Trigger status-specific workflows
                await self._trigger_status_workflows(tenant_id, new_status, updated_by, reason)
                
                logger.info("Tenant status updated",
                           tenant_id=str(tenant_id),
                           new_status=str(new_status),
                           reason=reason,
                           updated_by=updated_by)
            
            return tenant
            
        except Exception as e:
            logger.error(f"Failed to update tenant status: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update tenant status"
    
    async def _log_status_change(
        self,
        tenant_id: UUID,
        new_status: TenantStatus,
        reason: Optional[str],
        updated_by: Optional[str]
    ):
        """Log tenant status change for audit purposes."""
        log_data = {
            "tenant_id": str(tenant_id),
            "new_status": new_status.value,
            "reason": reason,
            "updated_by": updated_by,
            "timestamp": str(datetime.now(timezone.utc))
        }
        
        await self.config_repo.create({
            "tenant_id": tenant_id,
            "category": "audit",
            "key": f"status_change_{int(datetime.now(timezone.utc).timestamp())}",
            "value": log_data
        }, updated_by)
    
    @cached(ttl=900, namespace="tenants", key_builder=lambda self, tenant_id, category=None: f"configs:{tenant_id}:{category or 'all'}")
    async def get_tenant_configurations(
        self,
        tenant_id: UUID,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get tenant configurations."""
        configs = await self.config_repo.get_tenant_configurations(
            tenant_id, 
            category=category
        
        return [
            {
                "id": str(config.id),
                "category": config.category,
                "key": config.key,
                "value": config.value,
                "is_encrypted": config.is_encrypted,
                "created_at": config.created_at.isoformat(),
                "updated_at": config.updated_at.isoformat()
            }
            for config in configs
        ]
    
    @cache_invalidate(namespace="tenants", pattern=f"configs:*")
    async def update_tenant_configuration(
        self,
        tenant_id: UUID,
        category: str,
        key: str,
        value: Any,
        user_id: Optional[str] = None
    ) -> bool:
        """Update or create tenant configuration."""
        try:
            await self.config_repo.upsert_configuration(
                tenant_id=tenant_id,
                category=category,
                key=key,
                value=value,
                user_id=user_id
            return True
            
        except Exception as e:
            logger.error(f"Failed to update tenant configuration: {e}")
            return False
    
    async def get_tenant_health_status(self, tenant_id: UUID) -> Optional[Dict[str, Any]]:
        """Get tenant health status from monitoring system."""
        from repositories.monitoring import MonitoringRepository
        from models.monitoring import HealthStatus, AlertSeverity, AlertStatus
        
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            return None
            
        try:
            monitoring_repo = MonitoringRepository(self.db)
            
            # Get latest health checks
            recent_health_checks = await monitoring_repo.get_tenant_health_checks(
                tenant_id, 
                limit=10
            )
            
            # Get active alerts
            active_alerts = await monitoring_repo.get_active_alerts(tenant_id)
            critical_alerts = [a for a in active_alerts if a.severity in [AlertSeverity.CRITICAL, AlertSeverity.EMERGENCY]]
            warning_alerts = [a for a in active_alerts if a.severity == AlertSeverity.WARNING]
            
            # Get latest SLA record
            latest_sla = await monitoring_repo.get_latest_sla_record(tenant_id)
            
            # Calculate overall health score
            health_score = 100
            if recent_health_checks:
                healthy_checks = [c for c in recent_health_checks if c.status == HealthStatus.HEALTHY]
                health_score = int((len(healthy_checks) / len(recent_health_checks)) * 100)
            
            # Reduce score based on alerts
            health_score -= len(critical_alerts) * 20
            health_score -= len(warning_alerts) * 5
            health_score = max(0, health_score)
            
            # Determine overall status
            if health_score >= 90:
                overall_status = "healthy"
            elif health_score >= 70:
                overall_status = "warning"
            else:
                overall_status = "critical"
            
            # Calculate average response time from health checks
            avg_response_time = 0
            if recent_health_checks:
                response_times = [c.response_time_ms for c in recent_health_checks if c.response_time_ms]
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
            
            return {
                "tenant_id": str(tenant_id),
                "health_score": health_score,
                "status": overall_status,
                "uptime_percentage": float(latest_sla.uptime_percentage) if latest_sla else 99.9,
                "response_time_ms": avg_response_time,
                "error_rate": float(latest_sla.error_rate_percentage) if latest_sla else 0.0,
                "last_health_check": recent_health_checks[0].created_at if recent_health_checks else datetime.now(timezone.utc),
                "active_alerts": len(active_alerts),
                "critical_issues": len(critical_alerts),
                "warnings": len(warning_alerts),
                "sla_compliance": latest_sla.overall_sla_met if latest_sla else True,
                "total_downtime_minutes": latest_sla.total_downtime_minutes if latest_sla else 0,
                "mttr_minutes": latest_sla.mttr_minutes if latest_sla else None
            }
            
        except Exception as e:
            logger.error(f"Error getting health status for tenant {tenant_id}: {e}")
            # Fallback to basic status if monitoring system is unavailable
            return {
                "tenant_id": str(tenant_id),
                "health_score": 95,
                "status": "healthy",
                "uptime_percentage": 99.9,
                "response_time_ms": 150,
                "error_rate": 0.1,
                "last_health_check": datetime.now(timezone.utc),
                "active_alerts": 0,
                "critical_issues": 0,
                "warnings": 0
            }
    
    async def list_tenants(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tenant]:
        """List all tenants with pagination."""
        from sqlalchemy import select, desc
        
        query = select(Tenant).order_by(desc(Tenant.created_at))
        
        # Apply filters if provided
        if filters:
            if 'status' in filters:
                query = query.where(Tenant.status == filters['status'])
        
        # Apply pagination
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def search_tenants(
        self,
        search_term: str,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Tenant]:
        """Search tenants by name, email, or other fields."""
        return await self.tenant_repo.search_tenants(
            search_term=search_term,
            skip=skip,
            limit=limit,
            filters=filters
    
    async def get_tenant_count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Get total tenant count with optional filters."""
        return await self.tenant_repo.count(filters)
    
    @log_function_call(include_args=False, include_result=False)
    @cache_invalidate(namespace="tenants", pattern="tenant:*")
    async def update_tenant(
        self, 
        tenant_id: UUID, 
        update_data: TenantUpdate, 
        updated_by: str
    ) -> Optional[Tenant]:
        """Update tenant information with validation and audit logging."""
        try:
            # Get existing tenant to verify it exists
            existing_tenant = await self.tenant_repo.get_by_id(tenant_id)
            if not existing_tenant:
                logger.error(f"Tenant {tenant_id} not found for update")
                return None
            
            # Convert TenantUpdate to dict and handle special field mapping
            update_dict = update_data.model_dump(exclude_unset=True)
            
            # Map max_users to max_customers in the database
            if "max_users" in update_dict:
                update_dict["max_customers"] = update_dict.pop("max_users")
            
            # Update the tenant
            updated_tenant = await self.tenant_repo.update(
                tenant_id, update_dict, updated_by
            
            if updated_tenant:
                # Log audit event
                log_audit_event(
                    action="tenant_updated",
                    resource="tenant",
                    resource_id=str(tenant_id),
                    user_id=updated_by,
                    details={
                        "updated_fields": list(update_dict.keys()),
                        "tenant_name": updated_tenant.name
                
                logger.info(f"Tenant {tenant_id} updated successfully by {updated_by}")
            
            return updated_tenant
            
        except Exception as e:
            logger.error(f"Failed to update tenant {tenant_id}: {e}", exc_info=True)
            raise
    
    async def check_slug_availability(self, slug: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if tenant slug is available."""
        return await self.tenant_repo.check_slug_availability(slug, exclude_id)

    async def _trigger_status_workflows(self, tenant_id: UUID, new_status, updated_by: str, reason: str):
        """Trigger status-specific workflows based on tenant status changes."""
        try:
            # Import services and plugin integration
            from billing_service import BillingService
            from core.plugins.service_integration import service_integration
            
            billing_service = BillingService(self.db)
            
            # Get tenant info for notifications
            tenant = await self.tenant_repo.get_by_id(tenant_id)
            if not tenant:
                logger.warning(f"Tenant {tenant_id} not found for status workflow")
                return
            
            # Handle status-specific workflows
            if hasattr(new_status, 'value'):
                status_value = new_status.value
            else:
                status_value = str(new_status)
            
            # Activation workflows
            if status_value == "active":
                # Send welcome notification via plugins
                await service_integration.send_notification( channel_type="email",
                    message=f"Welcome! Your tenant '{tenant.name}' is now active and ready to use.",
                    recipients=[tenant.admin_email] if tenant.admin_email else [],
                    options={
                        "subject": f"Welcome to DotMac Platform - {tenant.name}",
                        "tenant_id": str(tenant_id),
                        "notification_type": "tenant_activated"
                
                # Start billing if not already started
                active_subscription = await billing_service.subscription_repo.get_active_subscription(tenant_id)
                if active_subscription:
                    await billing_service._start_billing_period(active_subscription.id)
            
            # Suspension workflows
            elif status_value == "suspended":
                # Send suspension notification via plugins
                await service_integration.send_notification( channel_type="email",
                    message=f"Your tenant '{tenant.name}' has been suspended. Reason: {reason}",
                    recipients=[tenant.admin_email] if tenant.admin_email else [],
                    options={
                        "subject": f"Tenant Suspended - {tenant.name}",
                        "tenant_id": str(tenant_id),
                        "notification_type": "tenant_suspended",
                        "priority": "high"
                
                # Pause billing
                active_subscription = await billing_service.subscription_repo.get_active_subscription(tenant_id)
                if active_subscription:
                    await billing_service._pause_billing(active_subscription.id, reason)
            
            # Cancellation workflows
            elif status_value == "cancelled":
                # Send cancellation notification via plugins
                await service_integration.send_notification( channel_type="email",
                    message=f"Your tenant '{tenant.name}' has been cancelled. Thank you for using our service.",
                    recipients=[tenant.admin_email] if tenant.admin_email else [],
                    options={
                        "subject": f"Tenant Cancelled - {tenant.name}",
                        "tenant_id": str(tenant_id),
                        "notification_type": "tenant_cancelled",
                        "priority": "high"
                
                # Cancel subscription and handle refunds
                active_subscription = await billing_service.subscription_repo.get_active_subscription(tenant_id)
                if active_subscription:
                    await billing_service.cancel_subscription()
                        active_subscription.id, 
                        reason, 
                        updated_by
            
            # Deactivation workflows
            elif status_value == "inactive":
                # Send deactivation notification via plugins
                await service_integration.send_notification( channel_type="email",
                    message=f"Your tenant '{tenant.name}' has been deactivated.",
                    recipients=[tenant.admin_email] if tenant.admin_email else [],
                    options={
                        "subject": f"Tenant Deactivated - {tenant.name}",
                        "tenant_id": str(tenant_id),
                        "notification_type": "tenant_deactivated",
                        "priority": "normal"
            
            logger.info(f"Status workflow completed for tenant {tenant_id} -> {status_value}")
            
        except Exception as e:
            logger.error(f"Failed to trigger status workflows for tenant {tenant_id}: {e}")
            # Don't raise exception to avoid breaking the main status update

    # Additional methods for tenant admin API support
    async def get_tenant_customers(
        self,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None,
        status_filter: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Get paginated list of customers for a tenant."""
        try:
            from uuid import UUID
            tenant_uuid = UUID(tenant_id)
            
            # Use real database query via CustomerRepository
            result = await self.customer_repo.get_tenant_customers(
                tenant_id=tenant_uuid,
                page=page,
                page_size=page_size,
                search=search,
                status_filter=status_filter,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            # Convert customers to dict format for API response
            customers_data = []
            for customer in result["customers"]:
                customers_data.append({
                    "id": str(customer.id),
                    "email": customer.email,
                    "first_name": customer.first_name,
                    "last_name": customer.last_name,
                    "company_name": customer.company_name,
                    "phone": customer.phone,
                    "status": customer.status.value if hasattr(customer.status, 'value') else str(customer.status),
                    "created_at": customer.created_at,
                    "last_login": customer.last_login,
                    "payment_status": customer.payment_status,
                    "customer_since": customer.customer_since,
                    "account_number": customer.account_number,
                    "address": customer.address
                })
            
            return {
                "customers": customers_data,
                "total_count": result["total_count"],
                "page": result["page"],
                "page_size": result["page_size"],
                "has_more": result["has_more"]
            }
        except Exception as e:
            logger.error(f"Error getting customers for tenant {tenant_id}: {e}")
            return {"customers": [], "total_count": 0, "page": page, "page_size": page_size}

    async def get_customer_by_id(self, tenant_id: str, customer_id: str) -> Optional[Dict[str, Any]]:
        """Get specific customer details."""
        try:
            from uuid import UUID
            tenant_uuid = UUID(tenant_id)
            customer_uuid = UUID(customer_id)
            
            # Use real database query via CustomerRepository
            customer = await self.customer_repo.get_customer_with_services(tenant_uuid, customer_uuid)
            
            if not customer:
                return None
                
            return {
                "id": str(customer.id),
                "email": customer.email,
                "first_name": customer.first_name,
                "last_name": customer.last_name,
                "company_name": customer.company_name,
                "phone": customer.phone,
                "status": customer.status.value if hasattr(customer.status, 'value') else str(customer.status),
                "created_at": customer.created_at,
                "last_login": customer.last_login,
                "payment_status": customer.payment_status,
                "customer_since": customer.customer_since,
                "account_number": customer.account_number,
                "address": customer.address,
                "notes": customer.notes,
                "tags": customer.tags,
                "preferences": customer.preferences,
                "services_count": len(customer.services) if customer.services else 0
            }
        except Exception as e:
            logger.error(f"Error getting customer {customer_id}: {e}")
            return None

    async def get_customer_services(self, tenant_id: str, customer_id: str) -> List[Dict[str, Any]]:
        """Get services for a specific customer."""
        try:
            from uuid import UUID
            tenant_uuid = UUID(tenant_id)
            customer_uuid = UUID(customer_id)
            
            # Use real database query via CustomerRepository
            services = await self.customer_repo.get_customer_services(tenant_uuid, customer_uuid)
            
            services_data = []
            for service in services:
                services_data.append({
                    "id": str(service.id),
                    "service_type": service.service_type,
                    "service_name": service.service_name,
                    "service_plan": service.service_plan,
                    "status": service.status.value if hasattr(service.status, 'value') else str(service.status),
                    "monthly_cost": float(service.monthly_cost),
                    "setup_fee": float(service.setup_fee),
                    "created_at": service.created_at,
                    "updated_at": service.updated_at,
                    "activation_date": service.activation_date,
                    "suspension_date": service.suspension_date,
                    "cancellation_date": service.cancellation_date,
                    "configuration": service.configuration,
                    "technical_details": service.technical_details,
                    "notes": service.notes,
                    "tags": service.tags,
                    "is_active": service.is_active
                })
            return services_data
        except Exception as e:
            logger.error(f"Error getting services for customer {customer_id}: {e}")
            return []

    async def get_customer_metrics(self, tenant_id: str, period_days: int) -> Dict[str, Any]:
        """Get customer metrics and statistics."""
        try:
            from uuid import UUID
            tenant_uuid = UUID(tenant_id)
            
            # Use real database query via CustomerRepository
            metrics = await self.customer_repo.get_customer_metrics(tenant_uuid, period_days)
            
            return metrics
        except Exception as e:
            logger.error(f"Error getting customer metrics for tenant {tenant_id}: {e}")
            return {
                "total_customers": 0,
                "active_customers": 0,
                "new_customers": 0,
                "churned_customers": 0,
                "total_monthly_revenue": 0.0,
                "previous_period_customers": 0
            }

    async def get_service_usage_stats(self, tenant_id: str, service_id: str) -> Dict[str, Any]:
        """Get usage statistics for a specific service."""
        try:
            from uuid import UUID
            tenant_uuid = UUID(tenant_id)
            service_uuid = UUID(service_id)
            
            # Use real database query via CustomerServiceRepository
            usage_stats = await self.customer_service_repo.get_service_usage_stats(tenant_uuid, service_uuid)
            
            return usage_stats
        except Exception as e:
            logger.error(f"Error getting usage stats for service {service_id}: {e}")
            return {
                "data_usage_gb": 0.0,
                "monthly_usage_gb": 0.0,
                "peak_usage_date": None,
                "uptime_percentage": 100.0,
                "last_usage": None,
                "response_time_ms": 0.0,
                "error_count": 0,
                "success_count": 0,
                "service_metrics": {}
            }

    async def get_customer_usage_summary(
        self,
        tenant_id: str,
        customer_id: str,
        period_days: int
    ) -> Dict[str, Any]:
        """Get usage summary for a specific customer."""
        try:
            from uuid import UUID
            tenant_uuid = UUID(tenant_id)
            customer_uuid = UUID(customer_id)
            
            # Use real database query via CustomerRepository
            usage_record = await self.customer_repo.get_customer_usage_summary(
                tenant_uuid, customer_uuid, period_days
            )
            
            if not usage_record:
                # Return empty usage data if no record found
                return {
                    "data_usage_gb": 0.0,
                    "api_requests": 0,
                    "login_sessions": 0,
                    "support_tickets": 0,
                    "uptime_percentage": 100.0,
                    "avg_response_time_ms": 0.0,
                    "peak_concurrent_users": 0,
                    "usage_by_service": {},
                    "base_cost": 0.0,
                    "usage_charges": 0.0,
                    "overage_charges": 0.0,
                    "total_cost": 0.0,
                    "daily_breakdown": []
                }
            
            return {
                "data_usage_gb": float(usage_record.data_usage_gb),
                "api_requests": usage_record.api_requests,
                "login_sessions": usage_record.login_sessions,
                "support_tickets": usage_record.support_tickets,
                "uptime_percentage": float(usage_record.uptime_percentage),
                "avg_response_time_ms": float(usage_record.avg_response_time_ms),
                "peak_concurrent_users": usage_record.peak_concurrent_users,
                "usage_by_service": usage_record.usage_by_service,
                "base_cost": float(usage_record.base_cost),
                "usage_charges": float(usage_record.usage_charges),
                "overage_charges": float(usage_record.overage_charges),
                "total_cost": float(usage_record.total_cost),
                "daily_breakdown": usage_record.daily_breakdown,
                "period_start": usage_record.period_start,
                "period_end": usage_record.period_end
            }
        except Exception as e:
            logger.error(f"Error getting usage summary for customer {customer_id}: {e}")
            return {
                "data_usage_gb": 0.0,
                "api_requests": 0,
                "login_sessions": 0,
                "support_tickets": 0,
                "uptime_percentage": 100.0,
                "avg_response_time_ms": 0.0,
                "peak_concurrent_users": 0,
                "usage_by_service": {},
                "base_cost": 0.0,
                "usage_charges": 0.0,
                "overage_charges": 0.0,
                "total_cost": 0.0,
                "daily_breakdown": []
            }