"""
Tenant service for multi-tenant operations.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
import re

from sqlalchemy.ext.asyncio import AsyncSession

from ..database import database_transaction
from ..repositories.tenant import TenantRepository, TenantConfigurationRepository
from ..schemas.tenant import TenantCreate, TenantUpdate, TenantOnboardingRequest
from ..models.tenant import Tenant, TenantStatus
from ..core.exceptions import (
    TenantNotFoundError, TenantNameConflictError, TenantNotActiveError,
    BusinessLogicError, DatabaseError
)
from ..core.logging import get_logger, log_audit_event, log_security_event, log_function_call
from ..core.cache import cached, cache_invalidate, TenantCache

logger = get_logger(__name__)


class TenantService:
    """Service for tenant operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.tenant_repo = TenantRepository(db)
        self.config_repo = TenantConfigurationRepository(db)
    
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
                )
                
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
            )
    
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
            )
            
            # TODO: Trigger infrastructure deployment workflow
            # This would integrate with deployment service
            
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
            )
    
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
                )
                
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
                    )
                
                # TODO: Trigger status-specific workflows
                # e.g., send notifications, update billing, etc.
                
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
            )
    
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
            "timestamp": str(datetime.utcnow())
        }
        
        await self.config_repo.create({
            "tenant_id": tenant_id,
            "category": "audit",
            "key": f"status_change_{int(datetime.utcnow().timestamp())}",
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
        )
        
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
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to update tenant configuration: {e}")
            return False
    
    async def get_tenant_health_status(self, tenant_id: UUID) -> Optional[Dict[str, Any]]:
        """Get tenant health status."""
        # This would integrate with monitoring service
        # For now, return placeholder data
        
        tenant = await self.tenant_repo.get_by_id(tenant_id)
        if not tenant:
            return None
        
        # Placeholder health data
        return {
            "tenant_id": str(tenant_id),
            "health_score": 95,
            "status": "healthy",
            "uptime_percentage": 99.9,
            "response_time_ms": 150,
            "error_rate": 0.1,
            "last_health_check": datetime.utcnow(),
            "active_alerts": 0,
            "critical_issues": 0,
            "warnings": 1
        }
    
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
        )
    
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
            )
            
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
                    }
                )
                
                logger.info(f"Tenant {tenant_id} updated successfully by {updated_by}")
            
            return updated_tenant
            
        except Exception as e:
            logger.error(f"Failed to update tenant {tenant_id}: {e}", exc_info=True)
            raise
    
    async def check_slug_availability(self, slug: str, exclude_id: Optional[UUID] = None) -> bool:
        """Check if tenant slug is available."""
        return await self.tenant_repo.check_slug_availability(slug, exclude_id)