"""Tenant security and multi-tenant isolation for DotMac Framework.

This module provides comprehensive tenant security including data isolation,
resource quotas, security policies, and tenant-specific access controls.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from dotmac_shared.utils.datetime_utils import utc_now
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID, uuid4

from .permissions import Permission, Role, UserPermissions
from .rbac_engine import AccessDecision, PolicyRule, RBACEngine, TenantPolicy

logger = logging.getLogger(__name__)


class TenantStatus(str, Enum):
    """Tenant status."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"
    PENDING = "pending"
    TRIAL = "trial"


class SecurityLevel(str, Enum):
    """Tenant security level."""

    BASIC = "basic"
    STANDARD = "standard"
    HIGH = "high"
    ENTERPRISE = "enterprise"


class IsolationLevel(str, Enum):
    """Data isolation level."""

    SHARED = "shared"  # Shared database with tenant filtering
    DEDICATED = "dedicated"  # Dedicated database per tenant
    ENCRYPTED = "encrypted"  # Shared with field-level encryption


@dataclass
class ResourceQuota:
    """Resource quota configuration."""

    max_users: int = 100
    max_customers: int = 1000
    max_devices: int = 5000
    max_storage_gb: int = 10
    max_api_requests_per_minute: int = 1000
    max_concurrent_sessions: int = 50
    max_data_retention_days: int = 365

    # Feature limits
    max_integrations: int = 5
    max_webhooks: int = 10
    max_custom_fields: int = 20


@dataclass
class SecurityPolicy:
    """Tenant security policy."""

    password_policy: Dict[str, Any] = field(
        default_factory=lambda: {
            "min_length": 8,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_digits": True,
            "require_special": True,
            "password_history": 5,
            "max_age_days": 90,
        }
    )

    session_policy: Dict[str, Any] = field(
        default_factory=lambda: {
            "idle_timeout_minutes": 30,
            "absolute_timeout_hours": 8,
            "require_mfa": False,
            "trusted_ip_ranges": [],
            "block_concurrent_sessions": False,
        }
    )

    api_policy: Dict[str, Any] = field(
        default_factory=lambda: {
            "rate_limit_per_minute": 1000,
            "require_api_key": False,
            "allowed_origins": ["*"],
            "require_https": True,
        }
    )

    data_policy: Dict[str, Any] = field(
        default_factory=lambda: {
            "encryption_at_rest": True,
            "backup_encryption": True,
            "audit_logging": True,
            "data_retention_days": 365,
            "pii_encryption": False,
        }
    )


@dataclass
class TenantInfo:
    """Tenant information."""

    tenant_id: UUID
    name: str
    slug: str
    status: TenantStatus
    security_level: SecurityLevel
    isolation_level: IsolationLevel
    created_at: datetime
    updated_at: datetime

    # Configuration
    resource_quota: ResourceQuota = field(default_factory=ResourceQuota)
    security_policy: SecurityPolicy = field(default_factory=SecurityPolicy)

    # Metadata
    admin_email: str = ""
    subscription_plan: str = "basic"
    billing_contact: str = ""
    technical_contact: str = ""

    # Security tracking
    last_security_audit: Optional[datetime] = None
    failed_login_attempts: int = 0
    security_incidents: List[str] = field(default_factory=list)


@dataclass
class DataAccessContext:
    """Data access context for tenant isolation."""

    tenant_id: str
    user_id: str
    request_id: str
    operation: str  # read, write, delete
    resource_type: str
    resource_id: Optional[str] = None
    additional_filters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SecurityAuditEvent:
    """Security audit event."""

    event_id: str
    tenant_id: str
    user_id: Optional[str]
    event_type: str
    event_description: str
    timestamp: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    risk_level: str = "low"  # low, medium, high, critical
    additional_data: Dict[str, Any] = field(default_factory=dict)


class TenantSecurityService:
    """Tenant security and isolation service.

    Provides comprehensive multi-tenant security including:
    - Data isolation and access controls
    - Resource quota management
    - Security policy enforcement
    - Audit logging and compliance
    - Threat detection and response
    """

    def __init__(self, rbac_engine: Optional[RBACEngine] = None):
        """Initialize tenant security service.

        Args:
            rbac_engine: RBAC engine for access control
        """
        self.rbac_engine = rbac_engine or RBACEngine()

        # Tenant registry
        self.tenants: Dict[str, TenantInfo] = {}

        # Security tracking
        self.audit_events: List[SecurityAuditEvent] = []
        self.active_threats: Dict[str, List[Dict]] = {}
        self.resource_usage: Dict[str, Dict[str, int]] = {}

        # Isolation filters
        self.isolation_filters: Dict[str, Any] = {}

        logger.info("Tenant security service initialized")

    def register_tenant(
        self,
        tenant_id: Union[str, UUID],
        name: str,
        slug: str,
        security_level: SecurityLevel = SecurityLevel.STANDARD,
        isolation_level: IsolationLevel = IsolationLevel.SHARED,
        admin_email: str = "",
        subscription_plan: str = "basic",
    ) -> TenantInfo:
        """Register new tenant with security configuration.

        Args:
            tenant_id: Tenant identifier
            name: Tenant name
            slug: Tenant slug
            security_level: Security level
            isolation_level: Data isolation level
            admin_email: Admin email
            subscription_plan: Subscription plan

        Returns:
            Tenant information
        """
        tenant_uuid = UUID(str(tenant_id)) if isinstance(tenant_id, str) else tenant_id
        tenant_id_str = str(tenant_uuid)

        # Create tenant info with security-level appropriate defaults
        resource_quota = self._get_default_quota_for_plan(subscription_plan)
        security_policy = self._get_default_security_policy(security_level)

        tenant_info = TenantInfo(
            tenant_id=tenant_uuid,
            name=name,
            slug=slug,
            status=TenantStatus.ACTIVE,
            security_level=security_level,
            isolation_level=isolation_level,
            created_at=utc_now(),
            updated_at=utc_now(),
            resource_quota=resource_quota,
            security_policy=security_policy,
            admin_email=admin_email,
            subscription_plan=subscription_plan,
        )

        self.tenants[tenant_id_str] = tenant_info

        # Initialize security policies in RBAC engine
        self._initialize_tenant_security_policies(tenant_id_str, tenant_info)

        # Initialize resource tracking
        self.resource_usage[tenant_id_str] = {
            "users": 0,
            "customers": 0,
            "devices": 0,
            "storage_gb": 0,
            "api_requests": 0,
            "active_sessions": 0,
        }

        self._audit_event(
            tenant_id=tenant_id_str,
            event_type="tenant_registered",
            event_description=f"Tenant registered: {name}",
            risk_level="low",
        )

        logger.info(f"Registered tenant: {name} ({tenant_id_str})")
        return tenant_info

    def get_tenant_info(self, tenant_id: Union[str, UUID]) -> Optional[TenantInfo]:
        """Get tenant information.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Tenant information if found
        """
        tenant_id_str = str(tenant_id)
        return self.tenants.get(tenant_id_str)

    def validate_tenant_access(
        self, user_permissions: UserPermissions, requested_tenant_id: Union[str, UUID]
    ) -> bool:
        """Validate user access to specific tenant.

        Args:
            user_permissions: User permissions
            requested_tenant_id: Requested tenant ID

        Returns:
            True if access is allowed
        """
        requested_tenant_str = str(requested_tenant_id)

        # Check if user belongs to tenant
        if user_permissions.tenant_id != requested_tenant_str:
            # Check if user has cross-tenant access (super admin)
            if Role.SUPER_ADMIN in user_permissions.roles:
                return True

            # Check if user has platform admin access
            if (
                Role.PLATFORM_ADMIN in user_permissions.roles
                and self.rbac_engine.has_permission(
                    user_permissions, Permission.SYSTEM_ADMIN
                )
            ):
                return True

            return False

        # Check tenant status
        tenant_info = self.tenants.get(requested_tenant_str)
        if not tenant_info:
            return False

        if tenant_info.status not in [TenantStatus.ACTIVE, TenantStatus.TRIAL]:
            return False

        return True

    def create_data_access_context(
        self,
        tenant_id: Union[str, UUID],
        user_id: str,
        operation: str,
        resource_type: str,
        resource_id: Optional[str] = None,
    ) -> DataAccessContext:
        """Create data access context for tenant isolation.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            operation: Data operation (read, write, delete)
            resource_type: Resource type
            resource_id: Specific resource ID

        Returns:
            Data access context
        """
        return DataAccessContext(
            tenant_id=str(tenant_id),
            user_id=user_id,
            request_id=str(uuid4()),
            operation=operation,
            resource_type=resource_type,
            resource_id=resource_id,
            additional_filters=self._get_tenant_isolation_filters(str(tenant_id)),
        )

    def apply_tenant_isolation_filter(
        self, query: Dict[str, Any], context: DataAccessContext
    ) -> Dict[str, Any]:
        """Apply tenant isolation filter to data query.

        Args:
            query: Original query
            context: Data access context

        Returns:
            Query with tenant isolation applied
        """
        isolated_query = query.copy()

        # Always add tenant filter
        isolated_query["tenant_id"] = context.tenant_id

        # Apply additional isolation filters based on level
        tenant_info = self.tenants.get(context.tenant_id)
        if tenant_info:
            if tenant_info.isolation_level == IsolationLevel.ENCRYPTED:
                # Add encryption context
                isolated_query["_encryption_context"] = {
                    "tenant_id": context.tenant_id,
                    "user_id": context.user_id,
                }

            # Apply additional filters from context
            isolated_query.update(context.additional_filters)

        return isolated_query

    def check_resource_quota(
        self, tenant_id: Union[str, UUID], resource_type: str, requested_amount: int = 1
    ) -> bool:
        """Check if tenant has quota for resource.

        Args:
            tenant_id: Tenant identifier
            resource_type: Resource type
            requested_amount: Requested amount

        Returns:
            True if quota allows request
        """
        tenant_id_str = str(tenant_id)
        tenant_info = self.tenants.get(tenant_id_str)
        if not tenant_info:
            return False

        current_usage = self.resource_usage.get(tenant_id_str, {})
        quota = tenant_info.resource_quota

        quota_mapping = {
            "users": quota.max_users,
            "customers": quota.max_customers,
            "devices": quota.max_devices,
            "storage_gb": quota.max_storage_gb,
            "api_requests": quota.max_api_requests_per_minute,
            "active_sessions": quota.max_concurrent_sessions,
        }

        max_allowed = quota_mapping.get(resource_type)
        if max_allowed is None:
            return True  # No limit defined

        current = current_usage.get(resource_type, 0)
        return (current + requested_amount) <= max_allowed

    def increment_resource_usage(
        self, tenant_id: Union[str, UUID], resource_type: str, amount: int = 1
    ) -> bool:
        """Increment resource usage for tenant.

        Args:
            tenant_id: Tenant identifier
            resource_type: Resource type
            amount: Amount to increment

        Returns:
            True if increment was successful
        """
        tenant_id_str = str(tenant_id)

        # Check quota first
        if not self.check_resource_quota(tenant_id_str, resource_type, amount):
            self._audit_event(
                tenant_id=tenant_id_str,
                event_type="quota_exceeded",
                event_description=f"Resource quota exceeded: {resource_type}",
                risk_level="medium",
            )
            return False

        # Increment usage
        if tenant_id_str not in self.resource_usage:
            self.resource_usage[tenant_id_str] = {}

        current = self.resource_usage[tenant_id_str].get(resource_type, 0)
        self.resource_usage[tenant_id_str][resource_type] = current + amount

        return True

    def decrement_resource_usage(
        self, tenant_id: Union[str, UUID], resource_type: str, amount: int = 1
    ):
        """Decrement resource usage for tenant.

        Args:
            tenant_id: Tenant identifier
            resource_type: Resource type
            amount: Amount to decrement
        """
        tenant_id_str = str(tenant_id)

        if tenant_id_str in self.resource_usage:
            current = self.resource_usage[tenant_id_str].get(resource_type, 0)
            self.resource_usage[tenant_id_str][resource_type] = max(0, current - amount)

    def update_security_policy(
        self, tenant_id: Union[str, UUID], policy_updates: Dict[str, Any]
    ) -> bool:
        """Update tenant security policy.

        Args:
            tenant_id: Tenant identifier
            policy_updates: Policy updates

        Returns:
            True if update successful
        """
        tenant_id_str = str(tenant_id)
        tenant_info = self.tenants.get(tenant_id_str)
        if not tenant_info:
            return False

        # Update security policy
        if "password_policy" in policy_updates:
            tenant_info.security_policy.password_policy.update(
                policy_updates["password_policy"]
            )

        if "session_policy" in policy_updates:
            tenant_info.security_policy.session_policy.update(
                policy_updates["session_policy"]
            )

        if "api_policy" in policy_updates:
            tenant_info.security_policy.api_policy.update(policy_updates["api_policy"])

        if "data_policy" in policy_updates:
            tenant_info.security_policy.data_policy.update(
                policy_updates["data_policy"]
            )

        tenant_info.updated_at = utc_now()

        # Update RBAC policies
        self._update_tenant_security_policies(tenant_id_str, tenant_info)

        self._audit_event(
            tenant_id=tenant_id_str,
            event_type="security_policy_updated",
            event_description="Tenant security policy updated",
            risk_level="low",
        )

        return True

    def suspend_tenant(
        self, tenant_id: Union[str, UUID], reason: str = "Administrative action"
    ) -> bool:
        """Suspend tenant access.

        Args:
            tenant_id: Tenant identifier
            reason: Suspension reason

        Returns:
            True if suspension successful
        """
        tenant_id_str = str(tenant_id)
        tenant_info = self.tenants.get(tenant_id_str)
        if not tenant_info:
            return False

        tenant_info.status = TenantStatus.SUSPENDED
        tenant_info.updated_at = utc_now()

        # Add blocking policy
        self.rbac_engine.add_tenant_policy(TenantPolicy(tenant_id_str))
        self.rbac_engine.tenant_policies[tenant_id_str].add_rule(
            PolicyRule(
                name="tenant_suspended",
                condition="always",
                effect=AccessDecision.DENY,
                priority=1,
            )
        )

        self._audit_event(
            tenant_id=tenant_id_str,
            event_type="tenant_suspended",
            event_description=f"Tenant suspended: {reason}",
            risk_level="high",
        )

        logger.warning(
            f"Tenant suspended: {tenant_info.name} ({tenant_id_str}) - {reason}"
        )
        return True

    def reactivate_tenant(self, tenant_id: Union[str, UUID]) -> bool:
        """Reactivate suspended tenant.

        Args:
            tenant_id: Tenant identifier

        Returns:
            True if reactivation successful
        """
        tenant_id_str = str(tenant_id)
        tenant_info = self.tenants.get(tenant_id_str)
        if not tenant_info or tenant_info.status != TenantStatus.SUSPENDED:
            return False

        tenant_info.status = TenantStatus.ACTIVE
        tenant_info.updated_at = utc_now()

        # Remove blocking policy
        tenant_policy = self.rbac_engine.tenant_policies.get(tenant_id_str)
        if tenant_policy:
            tenant_policy.remove_rule("tenant_suspended")

        self._audit_event(
            tenant_id=tenant_id_str,
            event_type="tenant_reactivated",
            event_description="Tenant reactivated",
            risk_level="low",
        )

        logger.info(f"Tenant reactivated: {tenant_info.name} ({tenant_id_str})")
        return True

    def get_tenant_audit_events(
        self,
        tenant_id: Union[str, UUID],
        limit: int = 100,
        event_type: Optional[str] = None,
    ) -> List[SecurityAuditEvent]:
        """Get audit events for tenant.

        Args:
            tenant_id: Tenant identifier
            limit: Maximum events to return
            event_type: Filter by event type

        Returns:
            List of audit events
        """
        tenant_id_str = str(tenant_id)
        events = []

        for event in reversed(self.audit_events):
            if event.tenant_id != tenant_id_str:
                continue

            if event_type and event.event_type != event_type:
                continue

            events.append(event)

            if len(events) >= limit:
                break

        return events

    def detect_suspicious_activity(
        self,
        tenant_id: Union[str, UUID],
        user_id: str,
        activity_type: str,
        context: Dict[str, Any],
    ) -> bool:
        """Detect suspicious activity for tenant.

        Args:
            tenant_id: Tenant identifier
            user_id: User identifier
            activity_type: Activity type
            context: Activity context

        Returns:
            True if activity is suspicious
        """
        tenant_id_str = str(tenant_id)

        # Simple suspicious activity detection
        # Can be extended with ML models

        suspicious = False
        risk_level = "low"

        # Check for multiple failed logins
        if activity_type == "login_failed":
            recent_failures = sum(
                1
                for event in self.audit_events[-100:]
                if (
                    event.tenant_id == tenant_id_str
                    and event.user_id == user_id
                    and event.event_type == "login_failed"
                    and (utc_now() - event.timestamp).seconds < 3600
                )
            )

            if recent_failures >= 5:
                suspicious = True
                risk_level = "high"

        # Check for unusual access patterns
        elif activity_type == "unusual_access":
            ip_address = context.get("ip_address")
            if ip_address:
                recent_ips = {
                    event.ip_address
                    for event in self.audit_events[-50:]
                    if (
                        event.tenant_id == tenant_id_str
                        and event.user_id == user_id
                        and event.ip_address
                    )
                }

                if len(recent_ips) > 5:
                    suspicious = True
                    risk_level = "medium"

        if suspicious:
            self._audit_event(
                tenant_id=tenant_id_str,
                user_id=user_id,
                event_type="suspicious_activity",
                event_description=f"Suspicious activity detected: {activity_type}",
                risk_level=risk_level,
                additional_data=context,
            )

        return suspicious

    def _get_default_quota_for_plan(self, plan: str) -> ResourceQuota:
        """Get default resource quota for subscription plan."""
        plan_quotas = {
            "basic": ResourceQuota(
                max_users=10,
                max_customers=100,
                max_devices=500,
                max_storage_gb=5,
                max_api_requests_per_minute=500,
            ),
            "premium": ResourceQuota(
                max_users=50,
                max_customers=1000,
                max_devices=2000,
                max_storage_gb=25,
                max_api_requests_per_minute=2000,
            ),
            "enterprise": ResourceQuota(
                max_users=200,
                max_customers=10000,
                max_devices=10000,
                max_storage_gb=100,
                max_api_requests_per_minute=5000,
            ),
        }

        return plan_quotas.get(plan, ResourceQuota())

    def _get_default_security_policy(self, level: SecurityLevel) -> SecurityPolicy:
        """Get default security policy for security level."""
        if level == SecurityLevel.ENTERPRISE:
            return SecurityPolicy(
                password_policy={
                    "min_length": 12,
                    "require_uppercase": True,
                    "require_lowercase": True,
                    "require_digits": True,
                    "require_special": True,
                    "password_history": 10,
                    "max_age_days": 60,
                },
                session_policy={
                    "idle_timeout_minutes": 15,
                    "absolute_timeout_hours": 4,
                    "require_mfa": True,
                    "block_concurrent_sessions": True,
                },
                data_policy={
                    "encryption_at_rest": True,
                    "backup_encryption": True,
                    "audit_logging": True,
                    "data_retention_days": 2555,  # 7 years
                    "pii_encryption": True,
                },
            )

        return SecurityPolicy()  # Default policy

    def _initialize_tenant_security_policies(
        self, tenant_id: str, tenant_info: TenantInfo
    ):
        """Initialize security policies for tenant in RBAC engine."""
        tenant_policy = TenantPolicy(tenant_id)

        # Add security level based rules
        if tenant_info.security_level == SecurityLevel.HIGH:
            tenant_policy.add_rule(
                PolicyRule(
                    name="high_security_restrictions",
                    condition=f"tenant_id=='{tenant_id}'",
                    effect=AccessDecision.ALLOW,
                    priority=50,
                )
            )

        self.rbac_engine.add_tenant_policy(tenant_policy)

    def _update_tenant_security_policies(self, tenant_id: str, tenant_info: TenantInfo):
        """Update security policies for tenant."""
        # Re-initialize policies with updated configuration
        self._initialize_tenant_security_policies(tenant_id, tenant_info)

    def _get_tenant_isolation_filters(self, tenant_id: str) -> Dict[str, Any]:
        """Get tenant-specific isolation filters."""
        return self.isolation_filters.get(tenant_id, {})

    def _audit_event(
        self,
        tenant_id: str,
        event_type: str,
        event_description: str,
        user_id: Optional[str] = None,
        risk_level: str = "low",
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        additional_data: Optional[Dict[str, Any]] = None,
    ):
        """Record audit event."""
        event = SecurityAuditEvent(
            event_id=str(uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            event_description=event_description,
            timestamp=utc_now(),
            ip_address=ip_address,
            user_agent=user_agent,
            risk_level=risk_level,
            additional_data=additional_data or {},
        )

        self.audit_events.append(event)

        # Keep only recent events (last 10000)
        if len(self.audit_events) > 10000:
            self.audit_events = self.audit_events[-5000:]
