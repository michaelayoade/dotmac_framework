"""RBAC (Role-Based Access Control) engine for DotMac Framework.

This module provides comprehensive role-based access control with hierarchical
permissions, multi-tenant support, and dynamic permission evaluation.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Union
from uuid import UUID

from .permissions import Permission, PermissionManager, Role, UserPermissions

logger = logging.getLogger(__name__)


class AccessDecision(Enum):
    """Access control decision."""

    ALLOW = "allow"
    DENY = "deny"
    ABSTAIN = "abstain"


@dataclass
class AccessRequest:
    """Access control request."""

    subject: str  # User ID
    resource: str  # Resource being accessed
    action: str  # Action being performed
    tenant_id: str  # Tenant context
    context: Dict[str, Any] = field(default_factory=dict)  # Additional context


@dataclass
class AccessResult:
    """Access control result."""

    decision: AccessDecision
    reason: str
    matched_permissions: List[str] = field(default_factory=list)
    matched_roles: List[str] = field(default_factory=list)
    execution_time_ms: float = 0.0


class PolicyRule:
    """Policy rule for access control."""

    def __init__(
        self,
        name: str,
        condition: str,
        effect: AccessDecision = AccessDecision.ALLOW,
        priority: int = 100,
    ):
        """Initialize policy rule.

        Args:
            name: Rule name
            condition: Rule condition expression
            effect: Rule effect (allow/deny)
            priority: Rule priority (lower = higher priority)
        """
        self.name = name
        self.condition = condition
        self.effect = effect
        self.priority = priority

    def evaluate(self, request: AccessRequest, context: Dict[str, Any]) -> bool:
        """Evaluate rule condition.

        Args:
            request: Access request
            context: Evaluation context

        Returns:
            True if rule matches
        """
        try:
            # Simple condition evaluation (can be extended)
            if self.condition == "always":
                return True
            elif self.condition == "never":
                return False
            elif self.condition.startswith("tenant_id=="):
                expected_tenant = self.condition.split("==")[1].strip("'\"")
                return request.tenant_id == expected_tenant
            elif self.condition.startswith("resource=="):
                expected_resource = self.condition.split("==")[1].strip("'\"")
                return request.resource == expected_resource

            # Add more condition types as needed
            return False

        except Exception as e:
            logger.error(f"Error evaluating rule {self.name}: {e}")
            return False


class TenantPolicy:
    """Tenant-specific access policy."""

    def __init__(self, tenant_id: str):
        """Initialize tenant policy.

        Args:
            tenant_id: Tenant identifier
        """
        self.tenant_id = tenant_id
        self.rules: List[PolicyRule] = []
        self.custom_permissions: Set[str] = set()
        self.blocked_actions: Set[str] = set()

    def add_rule(self, rule: PolicyRule):
        """Add policy rule."""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)

    def remove_rule(self, rule_name: str) -> bool:
        """Remove policy rule by name."""
        original_count = len(self.rules)
        self.rules = [r for r in self.rules if r.name != rule_name]
        return len(self.rules) < original_count

    def evaluate(
        self, request: AccessRequest, context: Dict[str, Any]
    ) -> Optional[AccessResult]:
        """Evaluate tenant policy.

        Args:
            request: Access request
            context: Evaluation context

        Returns:
            Access result if policy has a decision
        """
        for rule in self.rules:
            if rule.evaluate(request, context):
                return AccessResult(
                    decision=rule.effect,
                    reason=f"Matched tenant policy rule: {rule.name}",
                )

        return None


class RBACEngine:
    """Advanced RBAC engine with policy support.

    Provides hierarchical role-based access control with:
    - Multi-tenant permission isolation
    - Dynamic policy evaluation
    - Custom permission rules
    - Audit logging
    - Performance optimization
    """

    def __init__(self, permission_manager: Optional[PermissionManager] = None):
        """Initialize RBAC engine.

        Args:
            permission_manager: Permission manager instance
        """
        self.permission_manager = permission_manager or PermissionManager()
        self.tenant_policies: Dict[str, TenantPolicy] = {}
        self.global_policies: List[PolicyRule] = []

        # Caching for performance
        self._permission_cache: Dict[str, bool] = {}
        self._cache_enabled = True

        logger.info("RBAC engine initialized")

    def check_access(
        self,
        user_permissions: UserPermissions,
        resource: str,
        action: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AccessResult:
        """Check user access to resource/action.

        Args:
            user_permissions: User permissions
            resource: Resource being accessed
            action: Action being performed
            context: Additional context

        Returns:
            Access control result
        """
        import time

        start_time = time.perf_counter()

        context = context or {}
        request = AccessRequest(
            subject=user_permissions.user_id,
            resource=resource,
            action=action,
            tenant_id=user_permissions.tenant_id,
            context=context,
        )

        # Check cache first
        cache_key = f"{user_permissions.user_id}:{user_permissions.tenant_id}:{resource}:{action}"
        if self._cache_enabled and cache_key in self._permission_cache:
            decision = (
                AccessDecision.ALLOW
                if self._permission_cache[cache_key]
                else AccessDecision.DENY
            )
            return AccessResult(
                decision=decision,
                reason="Cached result",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )

        try:
            # 1. Check global deny policies first
            for rule in self.global_policies:
                if rule.effect == AccessDecision.DENY and rule.evaluate(
                    request, context
                ):
                    result = AccessResult(
                        decision=AccessDecision.DENY,
                        reason=f"Global deny policy: {rule.name}",
                        execution_time_ms=(time.perf_counter() - start_time) * 1000,
                    )
                    self._cache_result(cache_key, False)
                    return result

            # 2. Check tenant-specific policies
            tenant_policy = self.tenant_policies.get(user_permissions.tenant_id)
            if tenant_policy:
                # Check blocked actions
                if f"{resource}:{action}" in tenant_policy.blocked_actions:
                    result = AccessResult(
                        decision=AccessDecision.DENY,
                        reason="Action blocked by tenant policy",
                        execution_time_ms=(time.perf_counter() - start_time) * 1000,
                    )
                    self._cache_result(cache_key, False)
                    return result

                # Evaluate tenant policy rules
                policy_result = tenant_policy.evaluate(request, context)
                if policy_result and policy_result.decision == AccessDecision.DENY:
                    policy_result.execution_time_ms = (
                        time.perf_counter() - start_time
                    ) * 1000
                    self._cache_result(cache_key, False)
                    return policy_result

            # 3. Check standard RBAC permissions
            permission = Permission.from_resource_action(resource, action)
            if permission and self.permission_manager.check_permission(
                user_permissions, permission
            ):
                matched_permissions = [str(permission)]
                matched_roles = [str(role) for role in user_permissions.roles]

                result = AccessResult(
                    decision=AccessDecision.ALLOW,
                    reason="Standard RBAC permission granted",
                    matched_permissions=matched_permissions,
                    matched_roles=matched_roles,
                    execution_time_ms=(time.perf_counter() - start_time) * 1000,
                )
                self._cache_result(cache_key, True)
                return result

            # 4. Check custom tenant permissions
            if (
                tenant_policy
                and f"{resource}:{action}" in tenant_policy.custom_permissions
            ):
                result = AccessResult(
                    decision=AccessDecision.ALLOW,
                    reason="Custom tenant permission",
                    execution_time_ms=(time.perf_counter() - start_time) * 1000,
                )
                self._cache_result(cache_key, True)
                return result

            # 5. Check global allow policies
            for rule in self.global_policies:
                if rule.effect == AccessDecision.ALLOW and rule.evaluate(
                    request, context
                ):
                    result = AccessResult(
                        decision=AccessDecision.ALLOW,
                        reason=f"Global allow policy: {rule.name}",
                        execution_time_ms=(time.perf_counter() - start_time) * 1000,
                    )
                    self._cache_result(cache_key, True)
                    return result

            # Default deny
            result = AccessResult(
                decision=AccessDecision.DENY,
                reason="No matching permissions or policies",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )
            self._cache_result(cache_key, False)
            return result

        except Exception as e:
            logger.error(f"Error in access check: {e}")
            return AccessResult(
                decision=AccessDecision.DENY,
                reason=f"Internal error: {str(e)}",
                execution_time_ms=(time.perf_counter() - start_time) * 1000,
            )

    def has_permission(
        self, user_permissions: UserPermissions, permission: Union[Permission, str]
    ) -> bool:
        """Check if user has specific permission.

        Args:
            user_permissions: User permissions
            permission: Permission to check

        Returns:
            True if user has permission
        """
        if isinstance(permission, str):
            try:
                permission = Permission(permission)
            except ValueError:
                # Try to parse as resource:action
                parts = permission.split(":")
                if len(parts) == 2:
                    resource, action = parts
                    result = self.check_access(user_permissions, resource, action)
                    return result.decision == AccessDecision.ALLOW
                return False

        return self.permission_manager.check_permission(user_permissions, permission)

    def has_role(
        self, user_permissions: UserPermissions, role: Union[Role, str]
    ) -> bool:
        """Check if user has specific role.

        Args:
            user_permissions: User permissions
            role: Role to check

        Returns:
            True if user has role
        """
        if isinstance(role, str):
            try:
                role = Role(role)
            except ValueError:
                return False

        return role in user_permissions.roles

    def get_user_permissions_list(self, user_permissions: UserPermissions) -> List[str]:
        """Get list of all permissions for user.

        Args:
            user_permissions: User permissions

        Returns:
            List of permission strings
        """
        permissions = set()

        # Add explicit permissions
        permissions.update(str(p) for p in user_permissions.explicit_permissions)

        # Add role-based permissions
        for role in user_permissions.roles:
            role_permissions = self.permission_manager.get_role_permissions(role)
            permissions.update(str(p) for p in role_permissions)

        # Add tenant custom permissions
        tenant_policy = self.tenant_policies.get(user_permissions.tenant_id)
        if tenant_policy:
            permissions.update(tenant_policy.custom_permissions)

        return sorted(list(permissions))

    def get_user_roles_list(self, user_permissions: UserPermissions) -> List[str]:
        """Get list of all roles for user.

        Args:
            user_permissions: User permissions

        Returns:
            List of role strings
        """
        return [str(role) for role in user_permissions.roles]

    def add_tenant_policy(self, tenant_policy: TenantPolicy):
        """Add tenant-specific policy.

        Args:
            tenant_policy: Tenant policy to add
        """
        self.tenant_policies[tenant_policy.tenant_id] = tenant_policy
        self._clear_cache()
        logger.info(f"Added policy for tenant {tenant_policy.tenant_id}")

    def remove_tenant_policy(self, tenant_id: str) -> bool:
        """Remove tenant policy.

        Args:
            tenant_id: Tenant identifier

        Returns:
            True if policy was removed
        """
        if tenant_id in self.tenant_policies:
            del self.tenant_policies[tenant_id]
            self._clear_cache()
            logger.info(f"Removed policy for tenant {tenant_id}")
            return True
        return False

    def add_global_policy(self, rule: PolicyRule):
        """Add global policy rule.

        Args:
            rule: Policy rule to add
        """
        self.global_policies.append(rule)
        self.global_policies.sort(key=lambda r: r.priority)
        self._clear_cache()
        logger.info(f"Added global policy rule: {rule.name}")

    def remove_global_policy(self, rule_name: str) -> bool:
        """Remove global policy rule.

        Args:
            rule_name: Rule name to remove

        Returns:
            True if rule was removed
        """
        original_count = len(self.global_policies)
        self.global_policies = [r for r in self.global_policies if r.name != rule_name]

        if len(self.global_policies) < original_count:
            self._clear_cache()
            logger.info(f"Removed global policy rule: {rule_name}")
            return True
        return False

    def grant_tenant_permission(self, tenant_id: str, permission: str):
        """Grant custom permission to tenant.

        Args:
            tenant_id: Tenant identifier
            permission: Permission string (resource:action)
        """
        if tenant_id not in self.tenant_policies:
            self.tenant_policies[tenant_id] = TenantPolicy(tenant_id)

        self.tenant_policies[tenant_id].custom_permissions.add(permission)
        self._clear_cache()
        logger.info(f"Granted permission {permission} to tenant {tenant_id}")

    def revoke_tenant_permission(self, tenant_id: str, permission: str) -> bool:
        """Revoke custom permission from tenant.

        Args:
            tenant_id: Tenant identifier
            permission: Permission string

        Returns:
            True if permission was revoked
        """
        tenant_policy = self.tenant_policies.get(tenant_id)
        if tenant_policy and permission in tenant_policy.custom_permissions:
            tenant_policy.custom_permissions.discard(permission)
            self._clear_cache()
            logger.info(f"Revoked permission {permission} from tenant {tenant_id}")
            return True
        return False

    def block_tenant_action(self, tenant_id: str, action: str):
        """Block specific action for tenant.

        Args:
            tenant_id: Tenant identifier
            action: Action to block (resource:action)
        """
        if tenant_id not in self.tenant_policies:
            self.tenant_policies[tenant_id] = TenantPolicy(tenant_id)

        self.tenant_policies[tenant_id].blocked_actions.add(action)
        self._clear_cache()
        logger.info(f"Blocked action {action} for tenant {tenant_id}")

    def unblock_tenant_action(self, tenant_id: str, action: str) -> bool:
        """Unblock specific action for tenant.

        Args:
            tenant_id: Tenant identifier
            action: Action to unblock

        Returns:
            True if action was unblocked
        """
        tenant_policy = self.tenant_policies.get(tenant_id)
        if tenant_policy and action in tenant_policy.blocked_actions:
            tenant_policy.blocked_actions.discard(action)
            self._clear_cache()
            logger.info(f"Unblocked action {action} for tenant {tenant_id}")
            return True
        return False

    def bulk_check_permissions(
        self,
        user_permissions: UserPermissions,
        permission_requests: List[tuple[str, str]],  # [(resource, action), ...]
    ) -> Dict[str, bool]:
        """Check multiple permissions efficiently.

        Args:
            user_permissions: User permissions
            permission_requests: List of (resource, action) tuples

        Returns:
            Dictionary mapping "resource:action" to boolean result
        """
        results = {}

        for resource, action in permission_requests:
            key = f"{resource}:{action}"
            result = self.check_access(user_permissions, resource, action)
            results[key] = result.decision == AccessDecision.ALLOW

        return results

    def get_tenant_policy_summary(self, tenant_id: str) -> Dict[str, Any]:
        """Get summary of tenant policy.

        Args:
            tenant_id: Tenant identifier

        Returns:
            Policy summary dictionary
        """
        policy = self.tenant_policies.get(tenant_id)
        if not policy:
            return {"tenant_id": tenant_id, "exists": False}

        return {
            "tenant_id": tenant_id,
            "exists": True,
            "rules_count": len(policy.rules),
            "custom_permissions_count": len(policy.custom_permissions),
            "blocked_actions_count": len(policy.blocked_actions),
            "custom_permissions": sorted(list(policy.custom_permissions)),
            "blocked_actions": sorted(list(policy.blocked_actions)),
            "rules": [
                {
                    "name": rule.name,
                    "condition": rule.condition,
                    "effect": rule.effect.value,
                    "priority": rule.priority,
                }
                for rule in policy.rules
            ],
        }

    def enable_cache(self):
        """Enable permission result caching."""
        self._cache_enabled = True
        logger.info("Permission caching enabled")

    def disable_cache(self):
        """Disable permission result caching."""
        self._cache_enabled = False
        self._clear_cache()
        logger.info("Permission caching disabled")

    def _clear_cache(self):
        """Clear permission cache."""
        self._permission_cache.clear()

    def _cache_result(self, cache_key: str, result: bool):
        """Cache permission result."""
        if self._cache_enabled:
            self._permission_cache[cache_key] = result

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        return {"enabled": self._cache_enabled, "entries": len(self._permission_cache)}
