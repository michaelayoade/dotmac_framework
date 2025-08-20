"""
Authorization hooks for RBAC/policy enforcement on workflow operations.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

import structlog
from pydantic import BaseModel, Field

from .tenant_isolation import TenantContext, TenantIsolationError

logger = structlog.get_logger(__name__)


class Operation(str, Enum):
    """Workflow operations that require authorization."""

    # Workflow operations
    CREATE_WORKFLOW = "workflow:create"
    READ_WORKFLOW = "workflow:read"
    UPDATE_WORKFLOW = "workflow:update"
    DELETE_WORKFLOW = "workflow:delete"
    EXECUTE_WORKFLOW = "workflow:execute"

    # Execution operations
    READ_EXECUTION = "execution:read"
    CANCEL_EXECUTION = "execution:cancel"
    RETRY_EXECUTION = "execution:retry"
    SIGNAL_EXECUTION = "execution:signal"

    # Step operations
    READ_STEP = "step:read"
    RETRY_STEP = "step:retry"
    SKIP_STEP = "step:skip"

    # Schedule operations
    CREATE_SCHEDULE = "schedule:create"
    READ_SCHEDULE = "schedule:read"
    UPDATE_SCHEDULE = "schedule:update"
    DELETE_SCHEDULE = "schedule:delete"
    TRIGGER_SCHEDULE = "schedule:trigger"
    PAUSE_SCHEDULE = "schedule:pause"
    RESUME_SCHEDULE = "schedule:resume"

    # Queue operations
    READ_QUEUE = "queue:read"
    MANAGE_QUEUE = "queue:manage"
    REPLAY_DLQ = "queue:replay_dlq"

    # Admin operations
    VIEW_METRICS = "admin:view_metrics"
    MANAGE_TENANTS = "admin:manage_tenants"
    VIEW_LOGS = "admin:view_logs"


class ResourceType(str, Enum):
    """Resource types for authorization."""

    WORKFLOW = "workflow"
    EXECUTION = "execution"
    STEP = "step"
    SCHEDULE = "schedule"
    QUEUE = "queue"
    TENANT = "tenant"


class AuthorizationDecision(str, Enum):
    """Authorization decision outcomes."""

    ALLOW = "allow"
    DENY = "deny"
    ABSTAIN = "abstain"  # Policy doesn't apply


class AuthorizationContext(BaseModel):
    """Context for authorization decisions."""

    tenant_context: TenantContext
    operation: Operation
    resource_type: ResourceType
    resource_id: Optional[str] = None
    resource_attributes: Dict[str, Any] = Field(default_factory=dict)
    request_attributes: Dict[str, Any] = Field(default_factory=dict)
    environment_attributes: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        extra = "allow"


class AuthorizationResult(BaseModel):
    """Result of authorization check."""

    decision: AuthorizationDecision
    reason: str
    policy_id: Optional[str] = None
    obligations: List[str] = Field(default_factory=list)  # Actions that must be taken
    advice: List[str] = Field(default_factory=list)  # Recommended actions

    @property
    def is_allowed(self) -> bool:
        """Check if access is allowed."""
        return self.decision == AuthorizationDecision.ALLOW


class AuthorizationPolicy(ABC):
    """Abstract base class for authorization policies."""

    def __init__(self, policy_id: str, priority: int = 0):
        self.policy_id = policy_id
        self.priority = priority  # Higher priority policies are evaluated first

    @abstractmethod
    async def evaluate(self, context: AuthorizationContext) -> AuthorizationResult:
        """Evaluate the policy against the authorization context."""
        pass

    def applies_to(self, context: AuthorizationContext) -> bool:
        """Check if this policy applies to the given context."""
        return True  # Default: policy applies to all contexts


class RoleBasedPolicy(AuthorizationPolicy):
    """Role-based access control policy."""

    def __init__(
        self,
        policy_id: str,
        role_permissions: Dict[str, List[Operation]],
        priority: int = 100
    ):
        super().__init__(policy_id, priority)
        self.role_permissions = role_permissions

    async def evaluate(self, context: AuthorizationContext) -> AuthorizationResult:
        """Evaluate RBAC policy."""
        user_roles = context.tenant_context.roles
        required_operation = context.operation

        # Check if any user role has the required permission
        for role in user_roles:
            allowed_operations = self.role_permissions.get(role, [])
            if required_operation in allowed_operations:
                return AuthorizationResult(
                    decision=AuthorizationDecision.ALLOW,
                    reason=f"Role '{role}' has permission for operation '{required_operation.value}'",
                    policy_id=self.policy_id
                )

        return AuthorizationResult(
            decision=AuthorizationDecision.DENY,
            reason=f"No role has permission for operation '{required_operation.value}'",
            policy_id=self.policy_id
        )


class ResourceOwnershipPolicy(AuthorizationPolicy):
    """Policy that allows access to resources owned by the user."""

    def __init__(self, policy_id: str = "resource_ownership", priority: int = 200):
        super().__init__(policy_id, priority)

    async def evaluate(self, context: AuthorizationContext) -> AuthorizationResult:
        """Evaluate resource ownership policy."""
        user_id = context.tenant_context.user_id
        resource_owner = context.resource_attributes.get("owner_id")

        if not user_id or not resource_owner:
            return AuthorizationResult(
                decision=AuthorizationDecision.ABSTAIN,
                reason="Missing user_id or resource owner information",
                policy_id=self.policy_id
            )

        if user_id == resource_owner:
            return AuthorizationResult(
                decision=AuthorizationDecision.ALLOW,
                reason=f"User '{user_id}' owns the resource",
                policy_id=self.policy_id
            )

        return AuthorizationResult(
            decision=AuthorizationDecision.DENY,
            reason=f"User '{user_id}' does not own the resource",
            policy_id=self.policy_id
        )


class TimeBasedPolicy(AuthorizationPolicy):
    """Policy that restricts access based on time."""

    def __init__(
        self,
        policy_id: str,
        allowed_hours: List[int],  # Hours 0-23
        timezone: str = "UTC",
        priority: int = 50
    ):
        super().__init__(policy_id, priority)
        self.allowed_hours = allowed_hours
        self.timezone = timezone

    async def evaluate(self, context: AuthorizationContext) -> AuthorizationResult:
        """Evaluate time-based policy."""
        current_time = datetime.now(timezone.utc)
        current_hour = current_time.hour

        if current_hour in self.allowed_hours:
            return AuthorizationResult(
                decision=AuthorizationDecision.ALLOW,
                reason=f"Current hour {current_hour} is within allowed hours",
                policy_id=self.policy_id
            )

        return AuthorizationResult(
            decision=AuthorizationDecision.DENY,
            reason=f"Current hour {current_hour} is not within allowed hours {self.allowed_hours}",
            policy_id=self.policy_id
        )


class AttributeBasedPolicy(AuthorizationPolicy):
    """Attribute-based access control policy."""

    def __init__(
        self,
        policy_id: str,
        rules: List[Dict[str, Any]],
        priority: int = 150
    ):
        super().__init__(policy_id, priority)
        self.rules = rules

    async def evaluate(self, context: AuthorizationContext) -> AuthorizationResult:
        """Evaluate ABAC policy using rules."""
        for rule in self.rules:
            if await self._evaluate_rule(rule, context):
                decision = AuthorizationDecision(rule.get("decision", "allow"))
                return AuthorizationResult(
                    decision=decision,
                    reason=rule.get("reason", "Rule matched"),
                    policy_id=self.policy_id
                )

        return AuthorizationResult(
            decision=AuthorizationDecision.ABSTAIN,
            reason="No rules matched",
            policy_id=self.policy_id
        )

    async def _evaluate_rule(self, rule: Dict[str, Any], context: AuthorizationContext) -> bool:
        """Evaluate a single ABAC rule."""
        conditions = rule.get("conditions", [])

        for condition in conditions:
            attribute_path = condition.get("attribute")
            operator = condition.get("operator", "equals")
            expected_value = condition.get("value")

            # Get attribute value from context
            actual_value = self._get_attribute_value(attribute_path, context)

            # Evaluate condition
            if not self._evaluate_condition(actual_value, operator, expected_value):
                return False

        return True

    def _get_attribute_value(self, attribute_path: str, context: AuthorizationContext) -> Any:
        """Get attribute value from context using dot notation."""
        parts = attribute_path.split(".")
        value = context

        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None

        return value

    def _evaluate_condition(self, actual: Any, operator: str, expected: Any) -> bool:
        """Evaluate a condition based on operator."""
        if operator == "equals":
            return actual == expected
        elif operator == "not_equals":
            return actual != expected
        elif operator == "in":
            return actual in expected if isinstance(expected, (list, set)) else False
        elif operator == "not_in":
            return actual not in expected if isinstance(expected, (list, set)) else True
        elif operator == "greater_than":
            return actual > expected if isinstance(actual, (int, float)) else False
        elif operator == "less_than":
            return actual < expected if isinstance(actual, (int, float)) else False
        elif operator == "contains":
            return expected in actual if isinstance(actual, (str, list)) else False
        else:
            return False


class PolicyDecisionPoint:
    """Central policy decision point for authorization."""

    def __init__(self):
        self.policies: List[AuthorizationPolicy] = []
        self.policy_combination_algorithm = "deny_overrides"  # deny_overrides, permit_overrides, first_applicable
        self._lock = asyncio.Lock()

    async def add_policy(self, policy: AuthorizationPolicy):
        """Add a policy to the PDP."""
        async with self._lock:
            self.policies.append(policy)
            # Sort by priority (higher priority first)
            self.policies.sort(key=lambda p: p.priority, reverse=True)

        logger.info("Policy added to PDP", policy_id=policy.policy_id, priority=policy.priority)

    async def remove_policy(self, policy_id: str) -> bool:
        """Remove a policy from the PDP."""
        async with self._lock:
            for i, policy in enumerate(self.policies):
                if policy.policy_id == policy_id:
                    del self.policies[i]
                    logger.info("Policy removed from PDP", policy_id=policy_id)
                    return True

        return False

    async def evaluate(self, context: AuthorizationContext) -> AuthorizationResult:
        """Evaluate authorization request against all applicable policies."""
        applicable_policies = [p for p in self.policies if p.applies_to(context)]

        if not applicable_policies:
            return AuthorizationResult(
                decision=AuthorizationDecision.DENY,
                reason="No applicable policies found"
            )

        # Evaluate policies based on combination algorithm
        if self.policy_combination_algorithm == "deny_overrides":
            return await self._deny_overrides(applicable_policies, context)
        elif self.policy_combination_algorithm == "permit_overrides":
            return await self._permit_overrides(applicable_policies, context)
        elif self.policy_combination_algorithm == "first_applicable":
            return await self._first_applicable(applicable_policies, context)
        else:
            raise ValueError(f"Unknown policy combination algorithm: {self.policy_combination_algorithm}")

    async def _deny_overrides(
        self,
        policies: List[AuthorizationPolicy],
        context: AuthorizationContext
    ) -> AuthorizationResult:
        """Deny overrides: if any policy denies, the result is deny."""
        results = []

        for policy in policies:
            try:
                result = await policy.evaluate(context)
                results.append(result)

                if result.decision == AuthorizationDecision.DENY:
                    return result  # Immediate deny

            except Exception as e:
                logger.error(
                    "Policy evaluation error",
                    policy_id=policy.policy_id,
                    error=str(e)
                )

        # If no deny, look for allow
        for result in results:
            if result.decision == AuthorizationDecision.ALLOW:
                return result

        # Default deny
        return AuthorizationResult(
            decision=AuthorizationDecision.DENY,
            reason="No policy allowed access"
        )

    async def _permit_overrides(
        self,
        policies: List[AuthorizationPolicy],
        context: AuthorizationContext
    ) -> AuthorizationResult:
        """Permit overrides: if any policy allows, the result is allow."""
        results = []

        for policy in policies:
            try:
                result = await policy.evaluate(context)
                results.append(result)

                if result.decision == AuthorizationDecision.ALLOW:
                    return result  # Immediate allow

            except Exception as e:
                logger.error(
                    "Policy evaluation error",
                    policy_id=policy.policy_id,
                    error=str(e)
                )

        # If no allow, look for deny
        for result in results:
            if result.decision == AuthorizationDecision.DENY:
                return result

        # Default deny
        return AuthorizationResult(
            decision=AuthorizationDecision.DENY,
            reason="No policy allowed access"
        )

    async def _first_applicable(
        self,
        policies: List[AuthorizationPolicy],
        context: AuthorizationContext
    ) -> AuthorizationResult:
        """First applicable: return result of first policy that doesn't abstain."""
        for policy in policies:
            try:
                result = await policy.evaluate(context)

                if result.decision != AuthorizationDecision.ABSTAIN:
                    return result

            except Exception as e:
                logger.error(
                    "Policy evaluation error",
                    policy_id=policy.policy_id,
                    error=str(e)
                )

        # Default deny if all policies abstain
        return AuthorizationResult(
            decision=AuthorizationDecision.DENY,
            reason="All policies abstained"
        )


class AuthorizationHook:
    """Authorization hook for workflow operations."""

    def __init__(self, pdp: PolicyDecisionPoint):
        self.pdp = pdp
        self.audit_log: List[Dict[str, Any]] = []
        self._audit_lock = asyncio.Lock()

    async def check_authorization(
        self,
        tenant_context: TenantContext,
        operation: Operation,
        resource_type: ResourceType,
        resource_id: Optional[str] = None,
        resource_attributes: Optional[Dict[str, Any]] = None,
        request_attributes: Optional[Dict[str, Any]] = None
    ) -> AuthorizationResult:
        """Check authorization for an operation."""
        context = AuthorizationContext(
            tenant_context=tenant_context,
            operation=operation,
            resource_type=resource_type,
            resource_id=resource_id,
            resource_attributes=resource_attributes or {},
            request_attributes=request_attributes or {},
            environment_attributes={
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "request_id": tenant_context.request_id
            }
        )

        # Evaluate authorization
        result = await self.pdp.evaluate(context)

        # Audit log
        await self._log_authorization_decision(context, result)

        logger.info(
            "Authorization check completed",
            tenant_id=tenant_context.tenant_id,
            user_id=tenant_context.user_id,
            operation=operation.value,
            resource_type=resource_type.value,
            resource_id=resource_id,
            decision=result.decision.value,
            reason=result.reason
        )

        return result

    async def _log_authorization_decision(
        self,
        context: AuthorizationContext,
        result: AuthorizationResult
    ):
        """Log authorization decision for audit purposes."""
        audit_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "tenant_id": context.tenant_context.tenant_id,
            "user_id": context.tenant_context.user_id,
            "request_id": context.tenant_context.request_id,
            "operation": context.operation.value,
            "resource_type": context.resource_type.value,
            "resource_id": context.resource_id,
            "decision": result.decision.value,
            "reason": result.reason,
            "policy_id": result.policy_id,
            "ip_address": context.tenant_context.ip_address,
            "user_agent": context.tenant_context.user_agent
        }

        async with self._audit_lock:
            self.audit_log.append(audit_entry)

            # Keep only recent audit entries
            if len(self.audit_log) > 10000:
                self.audit_log = self.audit_log[-5000:]

    async def get_audit_log(
        self,
        tenant_context: TenantContext,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Get audit log entries (admin operation)."""
        # Check if user has admin permissions
        auth_result = await self.check_authorization(
            tenant_context=tenant_context,
            operation=Operation.VIEW_LOGS,
            resource_type=ResourceType.TENANT
        )

        if not auth_result.is_allowed:
            raise TenantIsolationError("Insufficient permissions to view audit logs")

        # Filter audit log
        filtered_entries = []
        for entry in self.audit_log[-limit:]:
            # Apply tenant isolation unless user is super admin
            if not tenant_context.has_role("super_admin"):
                if entry["tenant_id"] != tenant_context.tenant_id:
                    continue

            # Apply additional filters
            if filters:
                match = True
                for key, value in filters.items():
                    if entry.get(key) != value:
                        match = False
                        break
                if not match:
                    continue

            filtered_entries.append(entry)

        return filtered_entries


def create_default_policies() -> List[AuthorizationPolicy]:
    """Create default authorization policies."""

    # Default role permissions
    role_permissions = {
        "admin": [
            Operation.CREATE_WORKFLOW,
            Operation.READ_WORKFLOW,
            Operation.UPDATE_WORKFLOW,
            Operation.DELETE_WORKFLOW,
            Operation.EXECUTE_WORKFLOW,
            Operation.READ_EXECUTION,
            Operation.CANCEL_EXECUTION,
            Operation.RETRY_EXECUTION,
            Operation.SIGNAL_EXECUTION,
            Operation.READ_STEP,
            Operation.RETRY_STEP,
            Operation.SKIP_STEP,
            Operation.CREATE_SCHEDULE,
            Operation.READ_SCHEDULE,
            Operation.UPDATE_SCHEDULE,
            Operation.DELETE_SCHEDULE,
            Operation.TRIGGER_SCHEDULE,
            Operation.PAUSE_SCHEDULE,
            Operation.RESUME_SCHEDULE,
            Operation.READ_QUEUE,
            Operation.MANAGE_QUEUE,
            Operation.REPLAY_DLQ,
            Operation.VIEW_METRICS,
        ],
        "operator": [
            Operation.READ_WORKFLOW,
            Operation.EXECUTE_WORKFLOW,
            Operation.READ_EXECUTION,
            Operation.CANCEL_EXECUTION,
            Operation.RETRY_EXECUTION,
            Operation.SIGNAL_EXECUTION,
            Operation.READ_STEP,
            Operation.RETRY_STEP,
            Operation.READ_SCHEDULE,
            Operation.TRIGGER_SCHEDULE,
            Operation.PAUSE_SCHEDULE,
            Operation.RESUME_SCHEDULE,
            Operation.READ_QUEUE,
            Operation.REPLAY_DLQ,
        ],
        "viewer": [
            Operation.READ_WORKFLOW,
            Operation.READ_EXECUTION,
            Operation.READ_STEP,
            Operation.READ_SCHEDULE,
            Operation.READ_QUEUE,
        ],
        "super_admin": list(Operation),  # All operations
    }

    return [
        RoleBasedPolicy("default_rbac", role_permissions),
        ResourceOwnershipPolicy(),
        TimeBasedPolicy("business_hours", list(range(9, 18)))  # 9 AM to 6 PM
    ]
