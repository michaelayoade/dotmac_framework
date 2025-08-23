"""
Role-Based Access Control (RBAC) Implementation

Comprehensive RBAC system with hierarchical roles, dynamic permissions,
policy evaluation, and fine-grained access control.
"""

import asyncio
import re
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from ..utils.datetime_compat import utcnow
from dotmac_isp.sdks.platform.utils.datetime_compat import (
    utcnow,
    utc_now_iso,
    expires_in_days,
    expires_in_hours,
    is_expired,
)
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel

logger = structlog.get_logger(__name__)


class PermissionAction(Enum):
    """Standard CRUD actions for permissions"""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    APPROVE = "approve"
    EXPORT = "export"
    IMPORT = "import"
    MANAGE = "manage"


class ResourceType(Enum):
    """Types of resources that can be protected"""

    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    ORGANIZATION = "organization"
    TENANT = "tenant"
    CUSTOMER = "customer"
    BILLING = "billing"
    NETWORK = "network"
    DEVICE = "device"
    SERVICE = "service"
    REPORT = "report"
    AUDIT_LOG = "audit_log"
    CONFIGURATION = "configuration"
    API_KEY = "api_key"
    WEBHOOK = "webhook"


class PermissionScope(Enum):
    """Permission scope levels"""

    GLOBAL = "global"
    ORGANIZATION = "organization"
    TENANT = "tenant"
    RESOURCE = "resource"
    FIELD = "field"


@dataclass
class Permission:
    """Individual permission definition"""

    id: str
    name: str
    description: str
    resource_type: ResourceType
    action: PermissionAction
    scope: PermissionScope
    conditions: dict[str, Any] | None = None

    def __str__(self) -> str:
        return f"{self.resource_type.value}:{self.action.value}"

    def matches(self, resource_type: str, action: str) -> bool:
        """Check if permission matches resource and action"""
        return self.resource_type.value == resource_type and self.action.value == action


@dataclass
class Role:
    """Role definition with permissions and hierarchy"""

    id: str
    name: str
    description: str
    permissions: set[str] = field(default_factory=set)
    parent_roles: set[str] = field(default_factory=set)
    is_system_role: bool = False
    is_active: bool = True
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)

    def add_permission(self, permission_id: str) -> None:
        """Add permission to role"""
        self.permissions.add(permission_id)
        self.updated_at = utcnow()

    def remove_permission(self, permission_id: str) -> None:
        """Remove permission from role"""
        self.permissions.discard(permission_id)
        self.updated_at = utcnow()

    def add_parent_role(self, role_id: str) -> None:
        """Add parent role for inheritance"""
        self.parent_roles.add(role_id)
        self.updated_at = utcnow()


@dataclass
class Subject:
    """Subject (user/service) with roles and context"""

    id: str
    type: str  # "user", "service", "api_key"
    roles: set[str] = field(default_factory=set)
    temporary_permissions: set[str] = field(default_factory=set)
    attributes: dict[str, Any] = field(default_factory=dict)
    session_context: dict[str, Any] | None = None

    def add_role(self, role_id: str) -> None:
        """Add role to subject"""
        self.roles.add(role_id)

    def remove_role(self, role_id: str) -> None:
        """Remove role from subject"""
        self.roles.discard(role_id)


class AccessDecision(Enum):
    """Access control decision"""

    PERMIT = "permit"
    DENY = "deny"
    NOT_APPLICABLE = "not_applicable"
    INDETERMINATE = "indeterminate"


@dataclass
class AccessRequest:
    """Access control request"""

    subject_id: str
    resource_type: str
    action: str
    resource_id: str | None = None
    context: dict[str, Any] | None = None

    def __str__(self) -> str:
        resource_ref = (
            f"{self.resource_type}:{self.resource_id}"
            if self.resource_id
            else self.resource_type
        )
        return f"{self.subject_id} -> {self.action} on {resource_ref}"


@dataclass
class AccessResponse:
    """Access control response"""

    decision: AccessDecision
    reason: str
    obligations: list[str] = field(default_factory=list)
    advice: list[str] = field(default_factory=list)
    evaluated_permissions: list[str] = field(default_factory=list)
    evaluation_time: float = 0.0


class PolicyRule(BaseModel):
    """Policy rule for dynamic access control"""

    id: str
    name: str
    description: str
    condition: str  # Python expression
    effect: str  # "permit" or "deny"
    priority: int = 100
    is_active: bool = True

    def evaluate(self, context: dict[str, Any]) -> bool:
        """Evaluate rule condition against context"""
        try:
            # Create safe evaluation context
            safe_context = {
                "subject": context.get("subject", {}),
                "resource": context.get("resource", {}),
                "action": context.get("action", ""),
                "environment": context.get("environment", {}),
                "time": utcnow(),
                "re": re,  # Allow regex operations
            }

            # Evaluate condition safely using AST
            return self._safe_evaluate_condition(safe_context)

        except Exception as e:
            logger.warning(
                "Policy rule evaluation failed",
                rule_id=self.id,
                condition=self.condition,
                error=str(e),
            )
            return False

    def _safe_evaluate_condition(self, context: dict[str, Any]) -> bool:
        """
        Safely evaluate policy condition using AST parsing instead of eval().

        Uses the extracted AST evaluator for better maintainability and security.
        """
        from .ast_evaluator import safe_evaluate

        try:
            return safe_evaluate(self.condition, context)
        except Exception as e:
            logger.warning(
                "Policy condition evaluation failed",
                rule_id=self.id,
                condition=self.condition,
                error=str(e),
            )
            return False


class PolicyEngine:
    """Policy evaluation engine"""

    def __init__(self):
        self.rules: dict[str, PolicyRule] = {}
        self.rule_cache: dict[str, tuple[bool, datetime]] = {}
        self.cache_ttl = timedelta(minutes=5)

    def add_rule(self, rule: PolicyRule) -> None:
        """Add policy rule"""
        self.rules[rule.id] = rule
        logger.info("Policy rule added", rule_id=rule.id, name=rule.name)

    def remove_rule(self, rule_id: str) -> None:
        """Remove policy rule"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            logger.info("Policy rule removed", rule_id=rule_id)

    def evaluate_rules(self, context: dict[str, Any]) -> list[PolicyRule]:
        """Evaluate all applicable rules"""
        applicable_rules = []

        for rule in self.rules.values():
            if not rule.is_active:
                continue

            # Check cache first
            cache_key = f"{rule.id}:{hash(str(context))}"
            cached_result = self.rule_cache.get(cache_key)

            if cached_result:
                result, timestamp = cached_result
                if utcnow() - timestamp < self.cache_ttl:
                    if result:
                        applicable_rules.append(rule)
                    continue

            # Evaluate rule
            if rule.evaluate(context):
                applicable_rules.append(rule)
                self.rule_cache[cache_key] = (True, utcnow())
            else:
                self.rule_cache[cache_key] = (False, utcnow())

        # Sort by priority (higher priority first)
        return sorted(applicable_rules, key=lambda r: r.priority, reverse=True)


class RBACManager:
    """Main RBAC management system"""

    def __init__(self):
        self.permissions: dict[str, Permission] = {}
        self.roles: dict[str, Role] = {}
        self.subjects: dict[str, Subject] = {}
        self.policy_engine = PolicyEngine()
        self.access_cache: dict[str, tuple[AccessResponse, datetime]] = {}
        self.cache_ttl = timedelta(minutes=5)
        self._lock = asyncio.Lock()

        # Setup default permissions and roles
        self._setup_default_permissions()
        self._setup_default_roles()
        self._setup_default_policies()

    def _setup_default_permissions(self) -> None:
        """Setup default system permissions"""
        default_permissions = [
            # User management
            Permission(
                "user.create",
                "Create User",
                "Create new users",
                ResourceType.USER,
                PermissionAction.CREATE,
                PermissionScope.ORGANIZATION,
            ),
            Permission(
                "user.read",
                "Read User",
                "View user information",
                ResourceType.USER,
                PermissionAction.READ,
                PermissionScope.ORGANIZATION,
            ),
            Permission(
                "user.update",
                "Update User",
                "Modify user information",
                ResourceType.USER,
                PermissionAction.UPDATE,
                PermissionScope.ORGANIZATION,
            ),
            Permission(
                "user.delete",
                "Delete User",
                "Remove users",
                ResourceType.USER,
                PermissionAction.DELETE,
                PermissionScope.ORGANIZATION,
            ),
            # Role management
            Permission(
                "role.create",
                "Create Role",
                "Create new roles",
                ResourceType.ROLE,
                PermissionAction.CREATE,
                PermissionScope.ORGANIZATION,
            ),
            Permission(
                "role.read",
                "Read Role",
                "View role information",
                ResourceType.ROLE,
                PermissionAction.READ,
                PermissionScope.ORGANIZATION,
            ),
            Permission(
                "role.update",
                "Update Role",
                "Modify roles",
                ResourceType.ROLE,
                PermissionAction.UPDATE,
                PermissionScope.ORGANIZATION,
            ),
            Permission(
                "role.delete",
                "Delete Role",
                "Remove roles",
                ResourceType.ROLE,
                PermissionAction.DELETE,
                PermissionScope.ORGANIZATION,
            ),
            # Customer management
            Permission(
                "customer.create",
                "Create Customer",
                "Create new customers",
                ResourceType.CUSTOMER,
                PermissionAction.CREATE,
                PermissionScope.TENANT,
            ),
            Permission(
                "customer.read",
                "Read Customer",
                "View customer information",
                ResourceType.CUSTOMER,
                PermissionAction.READ,
                PermissionScope.TENANT,
            ),
            Permission(
                "customer.update",
                "Update Customer",
                "Modify customer information",
                ResourceType.CUSTOMER,
                PermissionAction.UPDATE,
                PermissionScope.TENANT,
            ),
            Permission(
                "customer.delete",
                "Delete Customer",
                "Remove customers",
                ResourceType.CUSTOMER,
                PermissionAction.DELETE,
                PermissionScope.TENANT,
            ),
            # Billing management
            Permission(
                "billing.read",
                "Read Billing",
                "View billing information",
                ResourceType.BILLING,
                PermissionAction.READ,
                PermissionScope.TENANT,
            ),
            Permission(
                "billing.update",
                "Update Billing",
                "Modify billing settings",
                ResourceType.BILLING,
                PermissionAction.UPDATE,
                PermissionScope.TENANT,
            ),
            Permission(
                "billing.export",
                "Export Billing",
                "Export billing data",
                ResourceType.BILLING,
                PermissionAction.EXPORT,
                PermissionScope.TENANT,
            ),
            # Network management
            Permission(
                "network.read",
                "Read Network",
                "View network information",
                ResourceType.NETWORK,
                PermissionAction.READ,
                PermissionScope.TENANT,
            ),
            Permission(
                "network.update",
                "Update Network",
                "Modify network settings",
                ResourceType.NETWORK,
                PermissionAction.UPDATE,
                PermissionScope.TENANT,
            ),
            Permission(
                "network.manage",
                "Manage Network",
                "Full network management",
                ResourceType.NETWORK,
                PermissionAction.MANAGE,
                PermissionScope.TENANT,
            ),
            # Device management
            Permission(
                "device.read",
                "Read Device",
                "View device information",
                ResourceType.DEVICE,
                PermissionAction.READ,
                PermissionScope.TENANT,
            ),
            Permission(
                "device.update",
                "Update Device",
                "Modify device settings",
                ResourceType.DEVICE,
                PermissionAction.UPDATE,
                PermissionScope.TENANT,
            ),
            Permission(
                "device.manage",
                "Manage Device",
                "Full device management",
                ResourceType.DEVICE,
                PermissionAction.MANAGE,
                PermissionScope.TENANT,
            ),
            # Audit and compliance
            Permission(
                "audit.read",
                "Read Audit Logs",
                "View audit logs",
                ResourceType.AUDIT_LOG,
                PermissionAction.READ,
                PermissionScope.ORGANIZATION,
            ),
            Permission(
                "audit.export",
                "Export Audit Logs",
                "Export audit data",
                ResourceType.AUDIT_LOG,
                PermissionAction.EXPORT,
                PermissionScope.ORGANIZATION,
            ),
            # Configuration management
            Permission(
                "config.read",
                "Read Configuration",
                "View system configuration",
                ResourceType.CONFIGURATION,
                PermissionAction.READ,
                PermissionScope.GLOBAL,
            ),
            Permission(
                "config.update",
                "Update Configuration",
                "Modify system configuration",
                ResourceType.CONFIGURATION,
                PermissionAction.UPDATE,
                PermissionScope.GLOBAL,
            ),
        ]

        for perm in default_permissions:
            self.permissions[perm.id] = perm

    def _setup_default_roles(self) -> None:
        """Setup default system roles"""
        # Super Admin - Full system access
        super_admin = Role(
            id="super_admin",
            name="Super Administrator",
            description="Full system access",
            is_system_role=True,
        )
        super_admin.permissions = set(self.permissions.keys())

        # Organization Admin - Organization-level access
        org_admin = Role(
            id="org_admin",
            name="Organization Administrator",
            description="Organization-level administration",
            is_system_role=True,
        )
        org_admin.permissions = {
            "user.create",
            "user.read",
            "user.update",
            "user.delete",
            "role.create",
            "role.read",
            "role.update",
            "role.delete",
            "audit.read",
            "audit.export",
        }

        # Tenant Admin - Tenant-level access
        tenant_admin = Role(
            id="tenant_admin",
            name="Tenant Administrator",
            description="Tenant-level administration",
            is_system_role=True,
        )
        tenant_admin.permissions = {
            "customer.create",
            "customer.read",
            "customer.update",
            "customer.delete",
            "billing.read",
            "billing.update",
            "billing.export",
            "network.read",
            "network.update",
            "network.manage",
            "device.read",
            "device.update",
            "device.manage",
        }

        # Customer Service Representative
        csr = Role(
            id="customer_service",
            name="Customer Service Representative",
            description="Customer service operations",
            is_system_role=True,
        )
        csr.permissions = {
            "customer.read",
            "customer.update",
            "billing.read",
            "network.read",
            "device.read",
        }

        # Network Technician
        network_tech = Role(
            id="network_tech",
            name="Network Technician",
            description="Network operations and maintenance",
            is_system_role=True,
        )
        network_tech.permissions = {
            "network.read",
            "network.update",
            "device.read",
            "device.update",
            "device.manage",
        }

        # Billing Clerk
        billing_clerk = Role(
            id="billing_clerk",
            name="Billing Clerk",
            description="Billing operations",
            is_system_role=True,
        )
        billing_clerk.permissions = {
            "customer.read",
            "billing.read",
            "billing.update",
            "billing.export",
        }

        # Auditor - Read-only access for compliance
        auditor = Role(
            id="auditor",
            name="Auditor",
            description="Compliance and audit access",
            is_system_role=True,
        )
        auditor.permissions = {
            "user.read",
            "role.read",
            "customer.read",
            "billing.read",
            "network.read",
            "device.read",
            "audit.read",
            "audit.export",
            "config.read",
        }

        # Store roles
        for role in [
            super_admin,
            org_admin,
            tenant_admin,
            csr,
            network_tech,
            billing_clerk,
            auditor,
        ]:
            self.roles[role.id] = role

    def _setup_default_policies(self) -> None:
        """Setup default policy rules"""
        # Time-based access restrictions
        business_hours_rule = PolicyRule(
            id="business_hours",
            name="Business Hours Access",
            description="Restrict access outside business hours",
            condition="9 <= time.hour <= 17 and time.weekday() < 5",
            effect="permit",
            priority=50,
        )

        # Sensitive operations require higher privileges
        sensitive_ops_rule = PolicyRule(
            id="sensitive_operations",
            name="Sensitive Operations",
            description="Require admin role for sensitive operations",
            condition="action in ['delete', 'export'] and 'admin' in [r for r in subject.get('roles', [])]",
            effect="permit",
            priority=200,
        )

        # Tenant isolation
        tenant_isolation_rule = PolicyRule(
            id="tenant_isolation",
            name="Tenant Isolation",
            description="Ensure tenant data isolation",
            condition="subject.get('tenant_id') == resource.get('tenant_id') or 'super_admin' in subject.get('roles', [])",
            effect="permit",
            priority=100,
        )

        for rule in [business_hours_rule, sensitive_ops_rule, tenant_isolation_rule]:
            self.policy_engine.add_rule(rule)

    def add_permission(self, permission: Permission) -> None:
        """Add new permission"""
        self.permissions[permission.id] = permission
        logger.info(
            "Permission added", permission_id=permission.id, name=permission.name
        )

    def add_role(self, role: Role) -> None:
        """Add new role"""
        self.roles[role.id] = role
        logger.info("Role added", role_id=role.id, name=role.name)

    def add_subject(self, subject: Subject) -> None:
        """Add new subject"""
        self.subjects[subject.id] = subject
        logger.info("Subject added", subject_id=subject.id, type=subject.type)

    def assign_role(self, subject_id: str, role_id: str) -> bool:
        """Assign role to subject"""
        subject = self.subjects.get(subject_id)
        role = self.roles.get(role_id)

        if not subject or not role:
            return False

        subject.add_role(role_id)
        logger.info("Role assigned", subject_id=subject_id, role_id=role_id)
        return True

    def revoke_role(self, subject_id: str, role_id: str) -> bool:
        """Revoke role from subject"""
        subject = self.subjects.get(subject_id)
        if not subject:
            return False

        subject.remove_role(role_id)
        logger.info("Role revoked", subject_id=subject_id, role_id=role_id)
        return True

    def get_subject_permissions(self, subject_id: str) -> set[str]:
        """Get all permissions for a subject"""
        subject = self.subjects.get(subject_id)
        if not subject:
            return set()

        permissions = set(subject.temporary_permissions)

        # Get permissions from roles (including inheritance)
        for role_id in subject.roles:
            permissions.update(self._get_role_permissions(role_id))

        return permissions

    def _get_role_permissions(
        self, role_id: str, visited: set[str] | None = None
    ) -> set[str]:
        """Get permissions for role including inherited permissions"""
        if visited is None:
            visited = set()

        if role_id in visited:
            # Circular reference protection
            return set()

        visited.add(role_id)
        role = self.roles.get(role_id)
        if not role:
            return set()

        permissions = set(role.permissions)

        # Add permissions from parent roles
        for parent_role_id in role.parent_roles:
            permissions.update(
                self._get_role_permissions(parent_role_id, visited.copy())
            )

        return permissions

    async def check_access(self, request: AccessRequest) -> AccessResponse:
        """Check access based on RBAC and policies using modular evaluation."""
        start_time = time.time()

        # Initialize evaluator if not exists
        if not hasattr(self, "_access_evaluator"):
            from .access_control import AccessControlEvaluator

            self._access_evaluator = AccessControlEvaluator(
                subjects=self.subjects,
                permissions=self.permissions,
                policy_engine=self.policy_engine,
                get_subject_permissions_func=self.get_subject_permissions,
                cache_ttl=self.cache_ttl,
            )

        evaluator = self._access_evaluator
        cache_key = evaluator.cache_manager.generate_cache_key(request)

        # Check cache first
        cached_response = evaluator.check_cached_access(cache_key, start_time)
        if cached_response:
            return cached_response

        # Validate subject exists
        subject_error = evaluator.validate_subject(request, start_time)
        if subject_error:
            return subject_error

        # Check permission match
        permission_match, permission_error = evaluator.check_permission_match(
            request, cache_key, start_time
        )
        if permission_error:
            return permission_error

        # Get subject for policy evaluation
        subject = self.subjects[request.subject_id]

        # Evaluate policies
        policy_decision, policy_reason = evaluator.evaluate_policies(
            subject, request, cache_key
        )

        # Create final response
        response = evaluator.create_final_response(
            policy_decision, policy_reason, permission_match, cache_key, start_time
        )

        logger.debug(
            "Access check completed",
            subject_id=request.subject_id,
            resource=f"{request.resource_type}:{request.resource_id}",
            action=request.action,
            decision=response.decision.value,
            evaluation_time=response.evaluation_time,
        )

        return response

    @asynccontextmanager
    async def enforce_access(self, request: AccessRequest):
        """Context manager that enforces access control"""
        response = await self.check_access(request)

        if response.decision != AccessDecision.PERMIT:
            raise PermissionError(f"Access denied: {response.reason}")

        try:
            yield response
        except Exception as e:
            logger.error(
                "Operation failed after access granted",
                subject_id=request.subject_id,
                operation=f"{request.action} on {request.resource_type}",
                error=str(e),
            )
            raise

    def get_role_hierarchy(self, role_id: str) -> dict[str, Any]:
        """Get role hierarchy visualization"""

        def build_hierarchy(
            role_id: str, visited: set[str] | None = None
        ) -> dict[str, Any]:
            if visited is None:
                visited = set()

            if role_id in visited:
                return {"error": "circular_reference"}

            visited.add(role_id)
            role = self.roles.get(role_id)

            if not role:
                return {"error": "role_not_found"}

            children = []
            for parent_role_id in role.parent_roles:
                children.append(build_hierarchy(parent_role_id, visited.copy()))

            return {
                "id": role.id,
                "name": role.name,
                "permissions": list(role.permissions),
                "parent_roles": children,
            }

        return build_hierarchy(role_id)

    def get_effective_permissions(self, subject_id: str) -> dict[str, Any]:
        """Get effective permissions for subject with details"""
        subject = self.subjects.get(subject_id)
        if not subject:
            return {"error": "subject_not_found"}

        permission_details = {}
        effective_permissions = self.get_subject_permissions(subject_id)

        for perm_id in effective_permissions:
            permission = self.permissions.get(perm_id)
            if permission:
                permission_details[perm_id] = {
                    "name": permission.name,
                    "description": permission.description,
                    "resource_type": permission.resource_type.value,
                    "action": permission.action.value,
                    "scope": permission.scope.value,
                }

        return {
            "subject_id": subject_id,
            "subject_type": subject.type,
            "roles": list(subject.roles),
            "permissions": permission_details,
            "temporary_permissions": list(subject.temporary_permissions),
        }

    def cleanup_cache(self) -> None:
        """Clean up expired cache entries"""
        now = utcnow()
        expired_keys = []

        for key, (_, timestamp) in self.access_cache.items():
            if now - timestamp > self.cache_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self.access_cache[key]

        logger.debug("Cache cleanup completed", expired_entries=len(expired_keys))


# Decorators for RBAC enforcement
def require_permission(
    resource_type: str, action: str, rbac_manager_key: str = "rbac_manager"
):
    """Decorator to enforce RBAC permissions on functions"""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            # Extract RBAC manager and subject from kwargs
            rbac_manager = kwargs.get(rbac_manager_key)
            subject_id = kwargs.get("subject_id") or kwargs.get("user_id")

            if not rbac_manager or not subject_id:
                raise ValueError("RBAC manager and subject_id required")

            # Create access request
            request = AccessRequest(
                subject_id=subject_id,
                resource_type=resource_type,
                action=action,
                context=kwargs.get("context"),
            )

            # Enforce access
            async with rbac_manager.enforce_access(request):
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


def require_role(role_id: str, rbac_manager_key: str = "rbac_manager"):
    """Decorator to require specific role"""

    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            rbac_manager = kwargs.get(rbac_manager_key)
            subject_id = kwargs.get("subject_id") or kwargs.get("user_id")

            if not rbac_manager or not subject_id:
                raise ValueError("RBAC manager and subject_id required")

            subject = rbac_manager.subjects.get(subject_id)
            if not subject or role_id not in subject.roles:
                raise PermissionError(f"Role '{role_id}' required")

            return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            return asyncio.run(async_wrapper(*args, **kwargs))

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
