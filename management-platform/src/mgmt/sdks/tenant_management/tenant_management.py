"""
Tenant Management SDK for Management Platform.

This module provides comprehensive tenant lifecycle management for the
multi-tenant SaaS platform, including onboarding, configuration, and monitoring.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
import logging

from pydantic import BaseModel, Field, ConfigDict, validator
from pydantic.types import UUID4
from enum import Enum

logger = logging.getLogger(__name__, timezone)


class TenantStatusEnum(str, Enum):
    """Tenant status enumeration."""
    PENDING = "pending"
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    MAINTENANCE = "maintenance"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SubscriptionTierEnum(str, Enum):
    """Subscription tier enumeration."""
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"


class BillingCycleEnum(str, Enum):
    """Billing cycle enumeration."""
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class IsolationLevelEnum(str, Enum):
    """Tenant isolation level enumeration."""
    SHARED = "shared"
    DEDICATED_DB = "dedicated_db"
    DEDICATED_INSTANCE = "dedicated_instance"
    DEDICATED_INFRASTRUCTURE = "dedicated_infrastructure"


class TenantCreate(BaseModel):
    """Tenant creation schema."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    name: str = Field(..., min_length=1, max_length=100)
    display_name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    primary_contact_email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')
    primary_contact_name: str = Field(..., min_length=1, max_length=100)
    business_phone: Optional[str] = Field(None, max_length=20)
    business_address: Optional[str] = Field(None, max_length=500)
    subscription_tier: SubscriptionTierEnum = Field(default=SubscriptionTierEnum.STARTER)
    billing_email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    billing_cycle: BillingCycleEnum = Field(default=BillingCycleEnum.MONTHLY)
    custom_domain: Optional[str] = None
    ssl_enabled: bool = Field(default=True)
    backup_retention_days: int = Field(default=30, ge=1, le=365)
    max_customers: int = Field(default=1000, ge=1)
    max_services: int = Field(default=10000, ge=1)
    max_storage_gb: int = Field(default=100, ge=1)
    max_bandwidth_mbps: int = Field(default=1000, ge=1)
    isolation_level: IsolationLevelEnum = Field(default=IsolationLevelEnum.SHARED)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    custom_settings: Dict[str, Any] = Field(default_factory=dict)


class TenantUpdate(BaseModel):
    """Tenant update schema."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    display_name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    primary_contact_email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    primary_contact_name: Optional[str] = Field(None, min_length=1, max_length=100)
    business_phone: Optional[str] = Field(None, max_length=20)
    business_address: Optional[str] = Field(None, max_length=500)
    billing_email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    billing_cycle: Optional[BillingCycleEnum] = None
    custom_domain: Optional[str] = None
    ssl_enabled: Optional[bool] = None
    backup_retention_days: Optional[int] = Field(None, ge=1, le=365)
    max_customers: Optional[int] = Field(None, ge=1)
    max_services: Optional[int] = Field(None, ge=1)
    max_storage_gb: Optional[int] = Field(None, ge=1)
    max_bandwidth_mbps: Optional[int] = Field(None, ge=1)
    metadata: Optional[Dict[str, Any]] = None
    custom_settings: Optional[Dict[str, Any]] = None


class TenantOnboardingRequest(BaseModel):
    """Complete tenant onboarding request."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    tenant_info: TenantCreate
    preferred_cloud_provider: str = Field(default="aws")
    preferred_region: str = Field(default="us-east-1")
    instance_size: str = Field(default="medium")
    enabled_features: List[str] = Field(default_factory=list)
    branding_config: Optional[Dict[str, Any]] = None
    integration_requirements: Optional[Dict[str, Any]] = None


class TenantConfigurationCreate(BaseModel):
    """Tenant configuration creation schema."""
    model_config = ConfigDict(str_strip_whitespace=True)
    
    category: str = Field(..., min_length=1, max_length=50)
    configuration_key: str = Field(..., min_length=1, max_length=100)
    configuration_value: Dict[str, Any]
    is_active: bool = Field(default=True)


class TenantResponse(BaseModel):
    """Tenant response schema."""
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID4
    tenant_id: str
    name: str
    display_name: str
    description: str
    primary_contact_email: str
    primary_contact_name: str
    business_phone: Optional[str] = None
    business_address: Optional[str] = None
    subscription_tier: str
    billing_email: Optional[str] = None
    billing_cycle: str
    custom_domain: Optional[str] = None
    ssl_enabled: bool
    backup_retention_days: int
    max_customers: int
    max_services: int
    max_storage_gb: int
    max_bandwidth_mbps: int
    isolation_level: str
    status: str
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime] = None
    suspended_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    custom_settings: Dict[str, Any] = Field(default_factory=dict)


class TenantHealthStatus(BaseModel):
    """Tenant health status schema."""
    model_config = ConfigDict(from_attributes=True)
    
    tenant_id: str
    status: str
    last_health_check: datetime
    health_score: int = Field(ge=0, le=100)
    uptime_percentage: Optional[float] = Field(None, ge=0, le=1)
    response_time_ms: Optional[int] = None
    error_rate: Optional[float] = Field(None, ge=0, le=1)
    resource_utilization: Dict[str, float] = Field(default_factory=dict)
    active_alerts: int = Field(default=0, ge=0)
    critical_issues: int = Field(default=0, ge=0)
    recommendations: List[str] = Field(default_factory=list)


class TenantListFilters(BaseModel):
    """Tenant list filters."""
    status: Optional[TenantStatusEnum] = None
    subscription_tier: Optional[SubscriptionTierEnum] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=1000)
    search_query: Optional[str] = None
    order_by: str = Field(default="created_at")
    order_desc: bool = Field(default=True)


class TenantManagementService:
    """In-memory tenant management service for demonstration."""
    
    def __init__(self):
        self._tenants: Dict[str, Dict[str, Any]] = {}
        self._configurations: Dict[str, List[Dict[str, Any]]] = {}
        self._usage_metrics: Dict[str, List[Dict[str, Any]]] = {}


class TenantManagementSDK:
    """
    Tenant Management SDK for SaaS platform operations.
    
    Provides comprehensive tenant lifecycle management including
    onboarding, configuration, monitoring, and resource management.
    """
    
    def __init__(self, platform_context: Optional[Dict[str, Any]] = None):
        """
        Initialize tenant management SDK.
        
        Args:
            platform_context: Platform-level authentication context
        """
        self.platform_context = platform_context or {}
        self._service = TenantManagementService()
        logger.info("Initialized TenantManagementSDK")
    
    async def create_tenant(
        self, 
        tenant_data: TenantCreate, 
        created_by: Optional[str] = None
    ) -> TenantResponse:
        """
        Create a new tenant with proper multi-tenant isolation setup.
        
        Args:
            tenant_data: Tenant creation data
            created_by: User ID who created the tenant
            
        Returns:
            Created tenant instance
            
        Raises:
            Exception: If tenant creation fails
        """
        try:
            # Generate unique tenant ID
            tenant_id = f"tenant_{uuid4().hex[:12]}"
            tenant_uuid = uuid4()
            now = datetime.now(timezone.utc)
            
            # Validate tenant name uniqueness (simplified)
            for existing_tenant in self._service._tenants.values():
                if existing_tenant["name"] == tenant_data.name:
                    raise ValueError(f"Tenant name '{tenant_data.name}' already exists")
            
            tenant_dict = {
                "id": tenant_uuid,
                "tenant_id": tenant_id,
                "name": tenant_data.name,
                "display_name": tenant_data.display_name,
                "description": tenant_data.description,
                "primary_contact_email": tenant_data.primary_contact_email,
                "primary_contact_name": tenant_data.primary_contact_name,
                "business_phone": tenant_data.business_phone,
                "business_address": tenant_data.business_address,
                "subscription_tier": tenant_data.subscription_tier.value,
                "billing_email": tenant_data.billing_email or tenant_data.primary_contact_email,
                "billing_cycle": tenant_data.billing_cycle.value,
                "custom_domain": tenant_data.custom_domain,
                "ssl_enabled": tenant_data.ssl_enabled,
                "backup_retention_days": tenant_data.backup_retention_days,
                "max_customers": tenant_data.max_customers,
                "max_services": tenant_data.max_services,
                "max_storage_gb": tenant_data.max_storage_gb,
                "max_bandwidth_mbps": tenant_data.max_bandwidth_mbps,
                "isolation_level": tenant_data.isolation_level.value,
                "status": TenantStatusEnum.PENDING.value,
                "created_at": now,
                "updated_at": now,
                "activated_at": None,
                "suspended_at": None,
                "cancelled_at": None,
                "metadata": tenant_data.metadata,
                "custom_settings": tenant_data.custom_settings,
                "created_by": created_by,
            }
            
            self._service._tenants[tenant_id] = tenant_dict
            self._service._configurations[tenant_id] = []
            
            logger.info(f"Created new tenant: {tenant_id} ({tenant_data.display_name})")
            
            return TenantResponse(**tenant_dict)
            
        except Exception as e:
            logger.error(f"Tenant creation failed: {e}")
            raise
    
    async def get_tenant_by_id(self, tenant_id: str) -> Optional[TenantResponse]:
        """
        Get tenant by tenant ID.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Tenant instance or None if not found
        """
        tenant_data = self._service._tenants.get(tenant_id)
        if not tenant_data:
            return None
        
        return TenantResponse(**tenant_data)
    
    async def get_tenant_by_uuid(self, tenant_uuid: UUID4) -> Optional[TenantResponse]:
        """Get tenant by UUID."""
        for tenant_data in self._service._tenants.values():
            if tenant_data["id"] == tenant_uuid:
                return TenantResponse(**tenant_data)
        return None
    
    async def list_tenants(self, filters: TenantListFilters) -> Tuple[List[TenantResponse], int]:
        """
        List tenants with filtering, pagination, and search.
        
        Args:
            filters: List filters and pagination parameters
            
        Returns:
            Tuple of (tenants list, total count)
        """
        filtered_tenants = []
        
        for tenant_data in self._service._tenants.values():
            # Apply filters
            if filters.status and tenant_data["status"] != filters.status.value:
                continue
            if filters.subscription_tier and tenant_data["subscription_tier"] != filters.subscription_tier.value:
                continue
            if filters.search_query:
                search_fields = [
                    tenant_data.get("name", ""),
                    tenant_data.get("display_name", ""),
                    tenant_data.get("primary_contact_email", ""),
                ]
                if not any(filters.search_query.lower() in field.lower() for field in search_fields):
                    continue
            
            filtered_tenants.append(tenant_data)
        
        # Sort tenants
        reverse_order = filters.order_desc
        if filters.order_by == "created_at":
            filtered_tenants.sort(key=lambda x: x["created_at"], reverse=reverse_order)
        elif filters.order_by == "name":
            filtered_tenants.sort(key=lambda x: x["name"], reverse=reverse_order)
        elif filters.order_by == "status":
            filtered_tenants.sort(key=lambda x: x["status"], reverse=reverse_order)
        
        total_count = len(filtered_tenants)
        
        # Apply pagination
        start_index = (filters.page - 1) * filters.page_size
        end_index = start_index + filters.page_size
        paginated_tenants = filtered_tenants[start_index:end_index]
        
        return [TenantResponse(**tenant) for tenant in paginated_tenants], total_count
    
    async def update_tenant(
        self, 
        tenant_id: str, 
        tenant_data: TenantUpdate, 
        updated_by: Optional[str] = None
    ) -> Optional[TenantResponse]:
        """
        Update tenant information.
        
        Args:
            tenant_id: Tenant identifier
            tenant_data: Update data
            updated_by: User ID who updated the tenant
            
        Returns:
            Updated tenant instance or None if not found
        """
        tenant_dict = self._service._tenants.get(tenant_id)
        if not tenant_dict:
            return None
        
        # Update fields that have values
        update_data = tenant_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if value is not None:
                tenant_dict[field] = value
        
        tenant_dict["updated_at"] = datetime.now(timezone.utc)
        
        logger.info(f"Updated tenant: {tenant_id} by {updated_by}")
        
        return TenantResponse(**tenant_dict)
    
    async def update_tenant_status(
        self,
        tenant_id: str,
        new_status: TenantStatusEnum,
        reason: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> Optional[TenantResponse]:
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
        tenant_dict = self._service._tenants.get(tenant_id)
        if not tenant_dict:
            return None
        
        old_status = tenant_dict["status"]
        tenant_dict["status"] = new_status.value
        tenant_dict["updated_at"] = datetime.now(timezone.utc)
        
        # Update lifecycle timestamps
        if new_status == TenantStatusEnum.ACTIVE and old_status != TenantStatusEnum.ACTIVE.value:
            tenant_dict["activated_at"] = datetime.now(timezone.utc)
            tenant_dict["suspended_at"] = None
        elif new_status == TenantStatusEnum.SUSPENDED:
            tenant_dict["suspended_at"] = datetime.now(timezone.utc)
        elif new_status == TenantStatusEnum.CANCELLED:
            tenant_dict["cancelled_at"] = datetime.now(timezone.utc)
        
        logger.info(
            f"Updated tenant {tenant_id} status from {old_status} to {new_status.value}"
            f"{f' (reason: {reason})' if reason else ''} by {updated_by}"
        )
        
        return TenantResponse(**tenant_dict)
    
    async def onboard_tenant(
        self, 
        onboarding_request: TenantOnboardingRequest, 
        created_by: Optional[str] = None
    ) -> TenantResponse:
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
        
        # Store configurations
        for config in configurations:
            await self.create_tenant_configuration(tenant.tenant_id, config, created_by)
        
        logger.info(f"Completed onboarding for tenant: {tenant.tenant_id}")
        
        return tenant
    
    async def create_tenant_configuration(
        self,
        tenant_id: str,
        config_data: TenantConfigurationCreate,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a tenant configuration."""
        config_dict = {
            "id": uuid4(),
            "tenant_id": tenant_id,
            "category": config_data.category,
            "configuration_key": config_data.configuration_key,
            "configuration_value": config_data.configuration_value,
            "is_active": config_data.is_active,
            "created_at": datetime.now(timezone.utc),
            "created_by": created_by,
        }
        
        if tenant_id not in self._service._configurations:
            self._service._configurations[tenant_id] = []
        
        self._service._configurations[tenant_id].append(config_dict)
        
        return config_dict
    
    async def get_tenant_health_status(self, tenant_id: str) -> Optional[TenantHealthStatus]:
        """
        Calculate and return tenant health status.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Tenant health status or None if tenant not found
        """
        tenant_dict = self._service._tenants.get(tenant_id)
        if not tenant_dict:
            return None
        
        # Calculate health score based on various factors
        health_score = self._calculate_health_score(tenant_dict)
        
        # Mock metrics (would come from actual monitoring in production)
        uptime_percentage = 0.999 if tenant_dict["status"] == TenantStatusEnum.ACTIVE.value else 0.5
        response_time_ms = 150
        error_rate = 0.001
        
        # Determine resource utilization
        resource_utilization = {
            "cpu": 45.2,
            "memory": 62.8,
            "storage": 34.5,
            "bandwidth": 28.9
        }
        
        # Mock alerts and issues
        active_alerts = 0
        critical_issues = 0
        recommendations = []
        
        if tenant_dict["status"] != TenantStatusEnum.ACTIVE.value:
            critical_issues += 1
            recommendations.append(f"Tenant is in {tenant_dict['status']} status")
        
        if uptime_percentage < 0.99:
            active_alerts += 1
            recommendations.append("Low uptime detected - check infrastructure health")
        
        return TenantHealthStatus(
            tenant_id=tenant_id,
            status=tenant_dict["status"],
            last_health_check=datetime.now(timezone.utc),
            health_score=health_score,
            uptime_percentage=uptime_percentage,
            response_time_ms=response_time_ms,
            error_rate=error_rate,
            resource_utilization=resource_utilization,
            active_alerts=active_alerts,
            critical_issues=critical_issues,
            recommendations=recommendations,
        )
    
    def _calculate_health_score(self, tenant_dict: Dict[str, Any]) -> int:
        """
        Calculate tenant health score (0-100).
        
        Args:
            tenant_dict: Tenant data dictionary
            
        Returns:
            Health score from 0-100
        """
        score = 100
        
        # Status penalties
        status = tenant_dict["status"]
        if status == TenantStatusEnum.SUSPENDED.value:
            score -= 50
        elif status == TenantStatusEnum.MAINTENANCE.value:
            score -= 20
        elif status == TenantStatusEnum.FAILED.value:
            score = 0
        elif status == TenantStatusEnum.CANCELLED.value:
            score = 0
        elif status != TenantStatusEnum.ACTIVE.value:
            score -= 30
        
        # Additional factors would be calculated here in production
        
        return max(0, min(100, int(score)))