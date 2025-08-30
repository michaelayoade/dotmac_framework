"""
Role-Based Access Control (RBAC) Implementation for Secrets Management

Comprehensive RBAC system with hierarchical roles, dynamic permissions,
policy evaluation, and fine-grained access control for secrets.
"""

import asyncio
import json
import re
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

# Safe datetime handling
try:
    from datetime import timezone

    UTC = timezone.utc

    def utcnow():
        """Get current UTC datetime."""
        return datetime.now(timezone.utc)

    def utc_now_iso():
        """Get current UTC datetime as ISO string."""
        return datetime.now(timezone.utc).isoformat()

    def expires_in_days(days: int):
        """Get datetime that expires in specified days."""
        return datetime.now(timezone.utc) + timedelta(days=days)

    def expires_in_hours(hours: int):
        """Get datetime that expires in specified hours."""
        return datetime.now(timezone.utc) + timedelta(hours=hours)

    def is_expired(dt: datetime):
        """Check if datetime is expired."""
        return datetime.now(timezone.utc) > dt

except ImportError:
    # Python < 3.7 fallback
    import pytz

    UTC = pytz.UTC

    def utcnow():
        return datetime.now(pytz.UTC)

    def utc_now_iso():
        return datetime.now(pytz.UTC).isoformat()

    def expires_in_days(days: int):
        return datetime.now(pytz.UTC) + timedelta(days=days)

    def expires_in_hours(hours: int):
        return datetime.now(pytz.UTC) + timedelta(hours=hours)

    def is_expired(dt: datetime):
        return datetime.now(pytz.UTC) > dt


# Handle optional dependencies gracefully
try:
    import structlog

    logger = structlog.get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)

try:
    from pydantic import BaseModel, Field

    PYDANTIC_AVAILABLE = True
except ImportError:
    BaseModel = object
    PYDANTIC_AVAILABLE = False


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
    ROTATE = "rotate"
    ENCRYPT = "encrypt"
    DECRYPT = "decrypt"


class ResourceType(Enum):
    """Types of resources that can be protected"""

    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    ORGANIZATION = "organization"
    TENANT = "tenant"
    CUSTOMER = "customer"
    SECRET = "secret"
    ENCRYPTION_KEY = "encryption_key"
    VAULT_PATH = "vault_path"
    API_KEY = "api_key"
    CERTIFICATE = "certificate"
    CONFIGURATION = "configuration"
    AUDIT_LOG = "audit_log"
    POLICY = "policy"


class PermissionScope(Enum):
    """Permission scope levels"""

    GLOBAL = "global"
    ORGANIZATION = "organization"
    TENANT = "tenant"
    RESOURCE = "resource"
    FIELD = "field"


class AccessDecision(Enum):
    """Access control decision outcomes"""

    ALLOW = "allow"
    DENY = "deny"
    ABSTAIN = "abstain"


@dataclass
class Permission:
    """Individual permission definition"""

    id: str
    name: str
    description: str
    resource_type: ResourceType
    action: PermissionAction
    scope: PermissionScope
    conditions: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=utcnow)

    def __str__(self) -> str:
        """String representation."""
        return f"{self.resource_type.value}:{self.action.value}"

    def matches(self, resource_type: str, action: str) -> bool:
        """Check if permission matches resource and action"""
        return self.resource_type.value == resource_type and self.action.value == action

    def evaluate_conditions(self, context: Dict[str, Any]) -> bool:
        """Evaluate permission conditions against context"""
        if not self.conditions:
            return True

        for condition_key, condition_value in self.conditions.items():
            context_value = context.get(condition_key)

            if isinstance(condition_value, dict):
                # Complex condition evaluation
                operator = condition_value.get("op", "eq")
                expected_value = condition_value.get("value")

                if operator == "eq":
                    if context_value != expected_value:
                        return False
                elif operator == "ne":
                    if context_value == expected_value:
                        return False
                elif operator == "in":
                    if context_value not in expected_value:
                        return False
                elif operator == "not_in":
                    if context_value in expected_value:
                        return False
                elif operator == "regex":
                    if not re.match(str(expected_value), str(context_value or "")):
                        return False
                elif operator == "gt":
                    if not (context_value and context_value > expected_value):
                        return False
                elif operator == "lt":
                    if not (context_value and context_value < expected_value):
                        return False
            else:
                # Simple equality check
                if context_value != condition_value:
                    return False

        return True


@dataclass
class Role:
    """Role definition with permissions and hierarchy"""

    id: str
    name: str
    description: str
    permissions: Set[str] = field(default_factory=set)
    parent_roles: Set[str] = field(default_factory=set)
    child_roles: Set[str] = field(default_factory=set)
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=utcnow)
    updated_at: Optional[datetime] = None

    def add_permission(self, permission_id: str) -> None:
        """Add a permission to this role"""
        self.permissions.add(permission_id)
        self.updated_at = utcnow()

    def remove_permission(self, permission_id: str) -> None:
        """Remove a permission from this role"""
        self.permissions.discard(permission_id)
        self.updated_at = utcnow()

    def add_parent_role(self, role_id: str) -> None:
        """Add a parent role (inherit permissions from)"""
        self.parent_roles.add(role_id)
        self.updated_at = utcnow()

    def remove_parent_role(self, role_id: str) -> None:
        """Remove a parent role"""
        self.parent_roles.discard(role_id)
        self.updated_at = utcnow()


@dataclass
class Subject:
    """Subject (user/service) requesting access"""

    id: str
    type: str  # user, service, system
    roles: Set[str] = field(default_factory=set)
    attributes: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    session_expires_at: Optional[datetime] = None

    def is_session_valid(self) -> bool:
        """Check if subject's session is still valid"""
        if not self.is_active:
            return False
        if self.session_expires_at and utcnow() > self.session_expires_at:
            return False
        return True

    def add_role(self, role_id: str) -> None:
        """Add a role to this subject"""
        self.roles.add(role_id)

    def remove_role(self, role_id: str) -> None:
        """Remove a role from this subject"""
        self.roles.discard(role_id)


@dataclass
class PolicyEvaluationContext:
    """Context for policy evaluation"""

    subject: Subject
    resource_type: str
    resource_id: Optional[str] = None
    action: str = ""
    environment: Dict[str, Any] = field(default_factory=dict)
    request_attributes: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for condition evaluation"""
        return {
            "subject_id": self.subject.id,
            "subject_type": self.subject.type,
            "subject_attributes": self.subject.attributes,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "environment": self.environment,
            "request_attributes": self.request_attributes,
            "timestamp": self.timestamp.isoformat(),
        }


class RBACManager:
    """
    Role-Based Access Control Manager for secrets management.

    Features:
    - Hierarchical role inheritance
    - Fine-grained permissions
    - Dynamic policy evaluation
    - Session management
    - Audit logging
    - Policy caching for performance
    """

    def __init__(
        self,
        audit_logger=None,
        cache_policies: bool = True,
        policy_cache_ttl: int = 1800,  # 30 minutes
        max_role_depth: int = 5,
    ):
        """
        Initialize the RBAC manager.

        Args:
            audit_logger: Logger for audit events
            cache_policies: Whether to cache policy evaluations
            policy_cache_ttl: Cache TTL in seconds
            max_role_depth: Maximum role hierarchy depth
        """
        self._audit_logger = audit_logger or logger
        self._cache_policies = cache_policies
        self._policy_cache_ttl = policy_cache_ttl
        self._max_role_depth = max_role_depth

        # Storage for RBAC entities
        self._permissions: Dict[str, Permission] = {}
        self._roles: Dict[str, Role] = {}
        self._subjects: Dict[str, Subject] = {}

        # Policy cache
        self._policy_cache: Dict[str, Dict[str, Any]] = {}

        # Built-in permissions and roles
        self._initialize_builtin_permissions()
        self._initialize_builtin_roles()

    def _initialize_builtin_permissions(self) -> None:
        """Initialize built-in permissions for secrets management"""
        builtin_permissions = [
            # Secret permissions
            Permission(
                id="secret:read",
                name="Read Secret",
                description="Read secret values",
                resource_type=ResourceType.SECRET,
                action=PermissionAction.READ,
                scope=PermissionScope.RESOURCE,
            ),
            Permission(
                id="secret:create",
                name="Create Secret",
                description="Create new secrets",
                resource_type=ResourceType.SECRET,
                action=PermissionAction.CREATE,
                scope=PermissionScope.TENANT,
            ),
            Permission(
                id="secret:update",
                name="Update Secret",
                description="Update existing secrets",
                resource_type=ResourceType.SECRET,
                action=PermissionAction.UPDATE,
                scope=PermissionScope.RESOURCE,
            ),
            Permission(
                id="secret:delete",
                name="Delete Secret",
                description="Delete secrets",
                resource_type=ResourceType.SECRET,
                action=PermissionAction.DELETE,
                scope=PermissionScope.RESOURCE,
            ),
            Permission(
                id="secret:rotate",
                name="Rotate Secret",
                description="Rotate secret values",
                resource_type=ResourceType.SECRET,
                action=PermissionAction.ROTATE,
                scope=PermissionScope.RESOURCE,
            ),
            # Encryption key permissions
            Permission(
                id="encryption_key:read",
                name="Read Encryption Key",
                description="Access encryption keys",
                resource_type=ResourceType.ENCRYPTION_KEY,
                action=PermissionAction.READ,
                scope=PermissionScope.RESOURCE,
            ),
            Permission(
                id="encryption_key:manage",
                name="Manage Encryption Key",
                description="Create and manage encryption keys",
                resource_type=ResourceType.ENCRYPTION_KEY,
                action=PermissionAction.MANAGE,
                scope=PermissionScope.TENANT,
            ),
            # Vault path permissions
            Permission(
                id="vault_path:read",
                name="Read Vault Path",
                description="Read from vault paths",
                resource_type=ResourceType.VAULT_PATH,
                action=PermissionAction.READ,
                scope=PermissionScope.RESOURCE,
            ),
            Permission(
                id="vault_path:write",
                name="Write Vault Path",
                description="Write to vault paths",
                resource_type=ResourceType.VAULT_PATH,
                action=PermissionAction.UPDATE,
                scope=PermissionScope.RESOURCE,
            ),
            # Role management permissions
            Permission(
                id="role:manage",
                name="Manage Roles",
                description="Create and manage roles",
                resource_type=ResourceType.ROLE,
                action=PermissionAction.MANAGE,
                scope=PermissionScope.ORGANIZATION,
            ),
            # Audit permissions
            Permission(
                id="audit_log:read",
                name="Read Audit Logs",
                description="Access audit logs",
                resource_type=ResourceType.AUDIT_LOG,
                action=PermissionAction.READ,
                scope=PermissionScope.TENANT,
            ),
        ]

        for permission in builtin_permissions:
            self._permissions[permission.id] = permission

    def _initialize_builtin_roles(self) -> None:
        """Initialize built-in roles for secrets management"""
        # Secret Reader role
        secret_reader = Role(
            id="secret_reader",
            name="Secret Reader",
            description="Can read secrets and audit logs",
            permissions={"secret:read", "audit_log:read"},
        )

        # Secret Manager role
        secret_manager = Role(
            id="secret_manager",
            name="Secret Manager",
            description="Can manage secrets but not encryption keys",
            permissions={
                "secret:read",
                "secret:create",
                "secret:update",
                "secret:rotate",
                "vault_path:read",
                "audit_log:read",
            },
        )

        # Secret Administrator role
        secret_admin = Role(
            id="secret_admin",
            name="Secret Administrator",
            description="Full secret management capabilities",
            permissions={
                "secret:read",
                "secret:create",
                "secret:update",
                "secret:delete",
                "secret:rotate",
                "encryption_key:read",
                "encryption_key:manage",
                "vault_path:read",
                "vault_path:write",
                "audit_log:read",
            },
        )

        # System Administrator role (inherits from secret admin)
        system_admin = Role(
            id="system_admin",
            name="System Administrator",
            description="Full system administration capabilities",
            permissions={"role:manage"},
            parent_roles={"secret_admin"},
        )

        roles = [secret_reader, secret_manager, secret_admin, system_admin]
        for role in roles:
            self._roles[role.id] = role
            # Set up parent-child relationships
            for parent_id in role.parent_roles:
                if parent_id in self._roles:
                    self._roles[parent_id].child_roles.add(role.id)

    def create_permission(
        self,
        permission_id: str,
        name: str,
        description: str,
        resource_type: ResourceType,
        action: PermissionAction,
        scope: PermissionScope,
        conditions: Optional[Dict[str, Any]] = None,
    ) -> Permission:
        """
        Create a new permission.

        Args:
            permission_id: Unique permission identifier
            name: Human-readable name
            description: Permission description
            resource_type: Type of resource
            action: Action being permitted
            scope: Permission scope
            conditions: Optional conditions for evaluation

        Returns:
            Created permission object
        """
        if permission_id in self._permissions:
            raise ValueError(f"Permission {permission_id} already exists")

        permission = Permission(
            id=permission_id,
            name=name,
            description=description,
            resource_type=resource_type,
            action=action,
            scope=scope,
            conditions=conditions,
        )

        self._permissions[permission_id] = permission

        self._audit_logger.info(
            "Permission created",
            permission_id=permission_id,
            resource_type=resource_type.value,
            action=action.value,
            scope=scope.value,
        )

        return permission

    def create_role(
        self,
        role_id: str,
        name: str,
        description: str,
        permissions: Optional[Set[str]] = None,
        parent_roles: Optional[Set[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Role:
        """
        Create a new role.

        Args:
            role_id: Unique role identifier
            name: Human-readable name
            description: Role description
            permissions: Set of permission IDs
            parent_roles: Set of parent role IDs
            metadata: Additional metadata

        Returns:
            Created role object
        """
        if role_id in self._roles:
            raise ValueError(f"Role {role_id} already exists")

        # Validate permissions exist
        permissions = permissions or set()
        for perm_id in permissions:
            if perm_id not in self._permissions:
                raise ValueError(f"Permission {perm_id} does not exist")

        # Validate parent roles exist and check for cycles
        parent_roles = parent_roles or set()
        for parent_id in parent_roles:
            if parent_id not in self._roles:
                raise ValueError(f"Parent role {parent_id} does not exist")
            if self._would_create_cycle(role_id, parent_id):
                raise ValueError(f"Adding parent role {parent_id} would create a cycle")

        role = Role(
            id=role_id,
            name=name,
            description=description,
            permissions=permissions,
            parent_roles=parent_roles,
            metadata=metadata or {},
        )

        self._roles[role_id] = role

        # Update parent-child relationships
        for parent_id in parent_roles:
            self._roles[parent_id].child_roles.add(role_id)

        self._audit_logger.info(
            "Role created",
            role_id=role_id,
            permissions=list(permissions),
            parent_roles=list(parent_roles),
        )

        return role

    def create_subject(
        self,
        subject_id: str,
        subject_type: str,
        roles: Optional[Set[str]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        session_duration: Optional[int] = None,
    ) -> Subject:
        """
        Create a new subject.

        Args:
            subject_id: Unique subject identifier
            subject_type: Type of subject (user, service, system)
            roles: Set of role IDs
            attributes: Subject attributes
            session_duration: Session duration in seconds

        Returns:
            Created subject object
        """
        if subject_id in self._subjects:
            raise ValueError(f"Subject {subject_id} already exists")

        # Validate roles exist
        roles = roles or set()
        for role_id in roles:
            if role_id not in self._roles:
                raise ValueError(f"Role {role_id} does not exist")

        session_expires_at = None
        if session_duration:
            session_expires_at = utcnow() + timedelta(seconds=session_duration)

        subject = Subject(
            id=subject_id,
            type=subject_type,
            roles=roles,
            attributes=attributes or {},
            session_expires_at=session_expires_at,
        )

        self._subjects[subject_id] = subject

        self._audit_logger.info(
            "Subject created",
            subject_id=subject_id,
            subject_type=subject_type,
            roles=list(roles),
            session_expires_at=(
                session_expires_at.isoformat() if session_expires_at else None
            ),
        )

        return subject

    def _would_create_cycle(self, role_id: str, parent_role_id: str) -> bool:
        """Check if adding a parent role would create a cycle"""
        visited = set()

        def has_cycle(current_role_id: str) -> bool:
            if current_role_id == role_id:
                return True
            if current_role_id in visited:
                return False

            visited.add(current_role_id)

            role = self._roles.get(current_role_id)
            if not role:
                return False

            for parent_id in role.parent_roles:
                if has_cycle(parent_id):
                    return True

            return False

        return has_cycle(parent_role_id)

    def get_effective_permissions(
        self, role_id: str, visited: Optional[Set[str]] = None
    ) -> Set[str]:
        """
        Get all effective permissions for a role (including inherited).

        Args:
            role_id: Role identifier
            visited: Set of visited roles (for cycle detection)

        Returns:
            Set of effective permission IDs
        """
        visited = visited or set()

        if role_id in visited or role_id not in self._roles:
            return set()

        if len(visited) > self._max_role_depth:
            logger.warning(f"Role hierarchy depth exceeded for role {role_id}")
            return set()

        visited.add(role_id)
        role = self._roles[role_id]

        # Start with direct permissions
        effective_permissions = role.permissions.copy()

        # Add permissions from parent roles
        for parent_role_id in role.parent_roles:
            parent_permissions = self.get_effective_permissions(
                parent_role_id, visited.copy()
            )
            effective_permissions.update(parent_permissions)

        return effective_permissions

    def get_subject_permissions(self, subject_id: str) -> Set[str]:
        """
        Get all effective permissions for a subject.

        Args:
            subject_id: Subject identifier

        Returns:
            Set of effective permission IDs
        """
        subject = self._subjects.get(subject_id)
        if not subject or not subject.is_session_valid():
            return set()

        all_permissions = set()
        for role_id in subject.roles:
            role_permissions = self.get_effective_permissions(role_id)
            all_permissions.update(role_permissions)

        return all_permissions

    async def check_access(
        self,
        subject_id: str,
        resource_type: str,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AccessDecision:
        """
        Check if a subject has access to perform an action on a resource.

        Args:
            subject_id: Subject identifier
            resource_type: Type of resource
            action: Action to perform
            resource_id: Specific resource identifier
            context: Additional context for evaluation

        Returns:
            Access decision (ALLOW, DENY, ABSTAIN)
        """
        # Get subject
        subject = self._subjects.get(subject_id)
        if not subject or not subject.is_session_valid():
            self._audit_logger.warning(
                "Access denied: invalid subject",
                subject_id=subject_id,
                resource_type=resource_type,
                action=action,
            )
            return AccessDecision.DENY

        # Check cache first
        if self._cache_policies:
            cache_key = f"{subject_id}:{resource_type}:{action}:{resource_id or 'none'}"
            cache_entry = self._policy_cache.get(cache_key)

            if cache_entry and utcnow() < cache_entry["expires_at"]:
                decision = AccessDecision(cache_entry["decision"])
                self._audit_logger.debug(
                    "Access decision from cache",
                    subject_id=subject_id,
                    resource_type=resource_type,
                    action=action,
                    decision=decision.value,
                )
                return decision

        # Create evaluation context
        eval_context = PolicyEvaluationContext(
            subject=subject,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            environment=context or {},
        )

        # Get subject's effective permissions
        subject_permissions = self.get_subject_permissions(subject_id)

        # Check if any permission allows this access
        decision = AccessDecision.DENY

        for permission_id in subject_permissions:
            permission = self._permissions.get(permission_id)
            if not permission:
                continue

            # Check if permission matches
            if permission.matches(resource_type, action):
                # Evaluate conditions
                if permission.evaluate_conditions(eval_context.to_dict()):
                    decision = AccessDecision.ALLOW
                    break

        # Cache the decision
        if self._cache_policies:
            self._policy_cache[cache_key] = {
                "decision": decision.value,
                "expires_at": utcnow() + timedelta(seconds=self._policy_cache_ttl),
                "evaluated_at": utcnow(),
            }

        # Audit the decision
        self._audit_logger.info(
            "Access control decision",
            subject_id=subject_id,
            subject_type=subject.type,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            decision=decision.value,
            permissions_checked=len(subject_permissions),
        )

        return decision

    async def is_allowed(
        self,
        subject_id: str,
        resource_type: str,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Check if access is allowed (convenience method).

        Args:
            subject_id: Subject identifier
            resource_type: Type of resource
            action: Action to perform
            resource_id: Specific resource identifier
            context: Additional context for evaluation

        Returns:
            True if access is allowed, False otherwise
        """
        decision = await self.check_access(
            subject_id, resource_type, action, resource_id, context
        )
        return decision == AccessDecision.ALLOW

    def assign_role_to_subject(self, subject_id: str, role_id: str) -> bool:
        """
        Assign a role to a subject.

        Args:
            subject_id: Subject identifier
            role_id: Role identifier

        Returns:
            True if successful, False otherwise
        """
        subject = self._subjects.get(subject_id)
        role = self._roles.get(role_id)

        if not subject or not role:
            return False

        subject.add_role(role_id)

        # Clear policy cache for this subject
        if self._cache_policies:
            keys_to_remove = [
                key
                for key in self._policy_cache.keys()
                if key.startswith(f"{subject_id}:")
            ]
            for key in keys_to_remove:
                del self._policy_cache[key]

        self._audit_logger.info(
            "Role assigned to subject",
            subject_id=subject_id,
            role_id=role_id,
        )

        return True

    def revoke_role_from_subject(self, subject_id: str, role_id: str) -> bool:
        """
        Revoke a role from a subject.

        Args:
            subject_id: Subject identifier
            role_id: Role identifier

        Returns:
            True if successful, False otherwise
        """
        subject = self._subjects.get(subject_id)

        if not subject:
            return False

        subject.remove_role(role_id)

        # Clear policy cache for this subject
        if self._cache_policies:
            keys_to_remove = [
                key
                for key in self._policy_cache.keys()
                if key.startswith(f"{subject_id}:")
            ]
            for key in keys_to_remove:
                del self._policy_cache[key]

        self._audit_logger.info(
            "Role revoked from subject",
            subject_id=subject_id,
            role_id=role_id,
        )

        return True

    def refresh_subject_session(self, subject_id: str, session_duration: int) -> bool:
        """
        Refresh a subject's session.

        Args:
            subject_id: Subject identifier
            session_duration: New session duration in seconds

        Returns:
            True if successful, False otherwise
        """
        subject = self._subjects.get(subject_id)

        if not subject:
            return False

        subject.session_expires_at = utcnow() + timedelta(seconds=session_duration)

        self._audit_logger.info(
            "Subject session refreshed",
            subject_id=subject_id,
            expires_at=subject.session_expires_at.isoformat(),
        )

        return True

    def list_subjects(self) -> List[Dict[str, Any]]:
        """List all subjects with metadata."""
        subjects = []
        for subject_id, subject in self._subjects.items():
            subjects.append(
                {
                    "id": subject.id,
                    "type": subject.type,
                    "roles": list(subject.roles),
                    "is_active": subject.is_active,
                    "session_valid": subject.is_session_valid(),
                    "session_expires_at": (
                        subject.session_expires_at.isoformat()
                        if subject.session_expires_at
                        else None
                    ),
                    "attributes": subject.attributes,
                }
            )
        return subjects

    def list_roles(self) -> List[Dict[str, Any]]:
        """List all roles with metadata."""
        roles = []
        for role_id, role in self._roles.items():
            roles.append(
                {
                    "id": role.id,
                    "name": role.name,
                    "description": role.description,
                    "permissions": list(role.permissions),
                    "parent_roles": list(role.parent_roles),
                    "child_roles": list(role.child_roles),
                    "is_active": role.is_active,
                    "created_at": role.created_at.isoformat(),
                    "updated_at": (
                        role.updated_at.isoformat() if role.updated_at else None
                    ),
                    "metadata": role.metadata,
                }
            )
        return roles

    def list_permissions(self) -> List[Dict[str, Any]]:
        """List all permissions with metadata."""
        permissions = []
        for perm_id, permission in self._permissions.items():
            permissions.append(
                {
                    "id": permission.id,
                    "name": permission.name,
                    "description": permission.description,
                    "resource_type": permission.resource_type.value,
                    "action": permission.action.value,
                    "scope": permission.scope.value,
                    "conditions": permission.conditions,
                    "created_at": permission.created_at.isoformat(),
                }
            )
        return permissions

    def clear_policy_cache(self) -> None:
        """Clear the policy evaluation cache."""
        self._policy_cache.clear()
        logger.info("Policy cache cleared")

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the RBAC system.

        Returns:
            Health status information
        """
        # Count active sessions
        active_sessions = sum(
            1 for subject in self._subjects.values() if subject.is_session_valid()
        )

        # Count expired sessions
        expired_sessions = len(self._subjects) - active_sessions

        # Count policy cache entries
        valid_cache_entries = 0
        expired_cache_entries = 0

        now = utcnow()
        for cache_entry in self._policy_cache.values():
            if now < cache_entry["expires_at"]:
                valid_cache_entries += 1
            else:
                expired_cache_entries += 1

        return {
            "healthy": True,
            "permissions": len(self._permissions),
            "roles": len(self._roles),
            "subjects": len(self._subjects),
            "active_sessions": active_sessions,
            "expired_sessions": expired_sessions,
            "policy_cache": {
                "enabled": self._cache_policies,
                "valid_entries": valid_cache_entries,
                "expired_entries": expired_cache_entries,
                "ttl_seconds": self._policy_cache_ttl,
            },
            "configuration": {
                "max_role_depth": self._max_role_depth,
                "cache_policies": self._cache_policies,
            },
        }
