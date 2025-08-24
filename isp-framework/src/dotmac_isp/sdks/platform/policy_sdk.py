"""
Policy SDK for Platform using contract-first design with Pydantic v2.

Provides Policy Engine functionality with comprehensive policy evaluation,
rule matching, and attribute-based access control (ABAC).
"""

import logging
import re
from datetime import datetime
from typing import Any

from dotmac_isp.sdks.contracts.policy import (
    ConditionOperator,
    Policy,
    PolicyCondition,
    PolicyCreateRequest,
    PolicyEffect,
    PolicyEvaluationRequest,
    PolicyEvaluationResponse,
    PolicyEvaluationResult,
    PolicyListRequest,
    PolicyListResponse,
    PolicyRule,
    PolicyStatsResponse,
    PolicyType,
)
from dotmac_isp.sdks.contracts.transport import RequestContext
from dotmac_isp.sdks.platform.utils.datetime_compat import UTC

logger = logging.getLogger(__name__)


class PolicyError(Exception):
    """Base policy error."""

    pass


class PolicyNotFoundError(PolicyError):
    """Policy not found error."""

    pass


class PolicyEvaluationError(PolicyError):
    """Policy evaluation error."""

    pass


class InvalidPolicyError(PolicyError):
    """Invalid policy error."""

    pass


class PolicySDKConfig:
    """Policy SDK configuration."""

    def __init__(
        """  Init   operation."""
        self,
        cache_ttl: int = 600,  # 10 minutes
        max_evaluation_time_ms: int = 1000,  # 1 second
        enable_caching: bool = True,
        enable_audit_logging: bool = True,
        default_effect: PolicyEffect = PolicyEffect.DENY,
        evaluation_strategy: str = "first_applicable",  # first_applicable, deny_overrides, permit_overrides
    ):
        self.cache_ttl = cache_ttl
        self.max_evaluation_time_ms = max_evaluation_time_ms
        self.enable_caching = enable_caching
        self.enable_audit_logging = enable_audit_logging
        self.default_effect = default_effect
        self.evaluation_strategy = evaluation_strategy


class PolicySDK:
    """
    Contract-first Policy SDK with comprehensive policy evaluation and management.

    Features:
    - Attribute-based access control (ABAC)
    - Rule-based policy evaluation
    - Multiple evaluation strategies
    - Policy caching for performance
    - Audit logging for compliance
    - Tenant isolation support
    - Pattern matching for resources
    - Condition evaluation engine
    """

    def __init__(
        self,
        config: PolicySDKConfig | None = None,
        cache_sdk: Any | None = None,
        database_sdk: Any | None = None,
    ):
        """Initialize Policy SDK."""
        self.config = config or PolicySDKConfig()
        self.cache_sdk = cache_sdk
        self.database_sdk = database_sdk

        # In-memory stores for testing/fallback
        self._policies: dict[str, Policy] = {}

        # Performance tracking
        self._stats = {
            "evaluations": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "allow_decisions": 0,
            "deny_decisions": 0,
            "total_evaluation_time_ms": 0.0,
        }

        # Initialize default policies
        self._initialize_defaults()

    def _initialize_defaults(self) -> None:
        """Initialize default policies."""
        # Default admin policy
        admin_policy = Policy(
            id="default-admin-policy",
            name="Default Admin Policy",
            description="Default policy granting admin access to system administrators",
            type=PolicyType.RBAC,
            rules=[
                PolicyRule(
                    id="admin-rule-1",
                    name="Admin Full Access",
                    description="Grant full access to administrators",
                    effect=PolicyEffect.ALLOW,
                    resources=["*"],
                    actions=["*"],
                    conditions=[
                        PolicyCondition(
                            field="roles",
                            operator=ConditionOperator.CONTAINS,
                            value="admin",
                        )
                    ],
                    priority=1000,
                )
            ],
        )

        # Default user policy
        user_policy = Policy(
            id="default-user-policy",
            name="Default User Policy",
            description="Default policy for standard users",
            type=PolicyType.RBAC,
            rules=[
                PolicyRule(
                    id="user-rule-1",
                    name="User Profile Access",
                    description="Allow users to access their own profile",
                    effect=PolicyEffect.ALLOW,
                    resources=["users/{user_id}/*"],
                    actions=["read", "write"],
                    conditions=[
                        PolicyCondition(
                            field="user_id",
                            operator=ConditionOperator.EQUALS,
                            value="{subject.user_id}",
                        )
                    ],
                    priority=100,
                )
            ],
        )

        # Time-based access policy
        time_policy = Policy(
            id="default-time-policy",
            name="Business Hours Policy",
            description="Restrict access to business hours",
            type=PolicyType.TIME,
            rules=[
                PolicyRule(
                    id="time-rule-1",
                    name="Business Hours Only",
                    description="Allow access only during business hours",
                    effect=PolicyEffect.DENY,
                    resources=["sensitive/*"],
                    actions=["*"],
                    conditions=[
                        PolicyCondition(
                            field="environment.hour",
                            operator=ConditionOperator.LT,
                            value=9,
                        ),
                        PolicyCondition(
                            field="environment.hour",
                            operator=ConditionOperator.GT,
                            value=17,
                        ),
                    ],
                    priority=500,
                )
            ],
        )

        self._policies[admin_policy.id] = admin_policy
        self._policies[user_policy.id] = user_policy
        self._policies[time_policy.id] = time_policy

    async def _get_cache_key(
        self, key_type: str, identifier: str, tenant_id: str | None = None
    ) -> str:
        """Generate cache key with tenant isolation."""
        tenant_prefix = f"tenant:{tenant_id}:" if tenant_id else "global:"
        return f"policy:{tenant_prefix}{key_type}:{identifier}"

    async def _cache_get(self, key: str) -> Any | None:
        """Get value from cache."""
        if not self.cache_sdk or not self.config.enable_caching:
            return None

        try:
            result = await self.cache_sdk.get(key)
            if result is not None:
                self._stats["cache_hits"] += 1
            else:
                self._stats["cache_misses"] += 1
            return result
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
            self._stats["cache_misses"] += 1
            return None

    async def _cache_set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache."""
        if not self.cache_sdk or not self.config.enable_caching:
            return

        try:
            await self.cache_sdk.set(key, value, ttl or self.config.cache_ttl)
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")

    def _match_resource_pattern(self, resource: str, pattern: str) -> bool:
        """Check if resource matches pattern."""
        # Exact match
        if resource == pattern:
            return True

        # Wildcard match
        if pattern == "*":
            return True

        # Pattern with wildcards
        if "*" in pattern:
            # Convert glob pattern to regex
            regex_pattern = pattern.replace("*", ".*").replace("?", ".")
            try:
                return bool(re.match(f"^{regex_pattern}$", resource))
            except re.error:
                logger.warning(f"Invalid regex pattern: {regex_pattern}")
                return False

        # Path prefix match
        if pattern.endswith("/"):
            return resource.startswith(pattern)

        return False

    def _evaluate_condition(  # noqa: C901
        self,
        condition: PolicyCondition,
        subject: dict[str, Any],
        environment: dict[str, Any],
    ) -> bool:
        """Evaluate a single condition - refactored to reduce complexity."""
        # Import refactored version
        from .policy_sdk_refactored import evaluate_condition_refactored

        return evaluate_condition_refactored(condition, subject, environment)

    # Note: Original complex implementation removed for clarity

    def _get_nested_value(
        self, data: dict[str, Any], field_path: list[str]
    ) -> Any:  # noqa: C901
        """Get nested value from dictionary."""
        current = data
        for part in field_path:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    def _substitute_variables(
        self, text: str, subject: dict[str, Any], environment: dict[str, Any]
    ) -> str:
        """Substitute variables in text with actual values."""
        # Simple variable substitution for {subject.field} and {environment.field}
        import re

        def replace_var(match):
            """Replace Var operation."""
            var_path = match.group(1)
            parts = var_path.split(".")

            if parts[0] == "subject":
                value = self._get_nested_value(subject, parts[1:])
            elif parts[0] == "environment":
                value = self._get_nested_value(environment, parts[1:])
            else:
                value = self._get_nested_value(subject, parts)
                if value is None:
                    value = self._get_nested_value(environment, parts)

            return str(value) if value is not None else match.group(0)

        return re.sub(r"\{([^}]+)\}", replace_var, text)

    async def _evaluate_rule(
        self,
        rule: PolicyRule,
        resource: str,
        action: str,
        subject: dict[str, Any],
        environment: dict[str, Any],
    ) -> tuple[bool, str | None]:
        """Evaluate a single rule."""
        if not rule.is_active:
            return False, "Rule is inactive"

        # Check resource match
        resource_match = False
        for resource_pattern in rule.resources:
            # Substitute variables in resource pattern
            substituted_pattern = self._substitute_variables(
                resource_pattern, subject, environment
            )
            if self._match_resource_pattern(resource, substituted_pattern):
                resource_match = True
                break

        if not resource_match:
            return False, "Resource does not match"

        # Check action match
        action_match = action in rule.actions or "*" in rule.actions
        if not action_match:
            return False, "Action does not match"

        # Evaluate conditions (all must be true for rule to match)
        for condition in rule.conditions:
            if not self._evaluate_condition(condition, subject, environment):
                return (
                    False,
                    f"Condition failed: {condition.field} {condition.operator} {condition.value}",
                )

        return True, f"Rule matched: {rule.name}"

    async def _evaluate_policy(
        self,
        policy: Policy,
        resource: str,
        action: str,
        subject: dict[str, Any],
        environment: dict[str, Any],
    ) -> PolicyEvaluationResult:
        """Evaluate a single policy."""
        start_time = datetime.now(UTC)

        if not policy.is_active:
            end_time = datetime.now(UTC)
            evaluation_time = (end_time - start_time).total_seconds() * 1000

            return PolicyEvaluationResult(
                policy_id=policy.id,
                policy_name=policy.name,
                effect=PolicyEffect.DENY,
                matched_rules=[],
                evaluation_time_ms=evaluation_time,
                reason="Policy is inactive",
            )

        # Sort rules by priority (higher priority first)
        sorted_rules = sorted(policy.rules, key=lambda r: r.priority, reverse=True)

        matched_rules = []
        final_effect = PolicyEffect.DENY
        reasons = []

        for rule in sorted_rules:
            matches, reason = await self._evaluate_rule(
                rule, resource, action, subject, environment
            )

            if matches:
                matched_rules.append(rule.id)
                reasons.append(reason)

                # Apply evaluation strategy
                if self.config.evaluation_strategy == "first_applicable":
                    final_effect = rule.effect
                    break
                elif self.config.evaluation_strategy == "deny_overrides":
                    if rule.effect == PolicyEffect.DENY:
                        final_effect = PolicyEffect.DENY
                        break
                    else:
                        final_effect = PolicyEffect.ALLOW
                elif self.config.evaluation_strategy == "permit_overrides":
                    if rule.effect == PolicyEffect.ALLOW:
                        final_effect = PolicyEffect.ALLOW
                        break
                    else:
                        final_effect = PolicyEffect.DENY
        # noqa: C901, PLR0915
        end_time = datetime.now(UTC)
        evaluation_time = (
            end_time - start_time
        ).total_seconds() * 1000  # noqa: PLR0915, C901

        return PolicyEvaluationResult(
            policy_id=policy.id,
            policy_name=policy.name,
            effect=final_effect,
            matched_rules=matched_rules,
            evaluation_time_ms=evaluation_time,
            reason="; ".join(reasons) if reasons else "No matching rules",
        )

    async def evaluate(  # noqa: C901, PLR0915
        self,
        request: PolicyEvaluationRequest,
        context: RequestContext | None = None,
    ) -> PolicyEvaluationResponse:
        """Evaluate policies for access decision."""
        start_time = datetime.now(UTC)
        self._stats["evaluations"] += 1

        try:
            tenant_id = context.tenant_id if context else None
            subject_id = request.subject.get("user_id", "unknown")

            # Get policies to evaluate
            if request.policies:
                policies_to_evaluate = [
                    self._policies[policy_id]
                    for policy_id in request.policies
                    if policy_id in self._policies
                ]
            else:
                # Evaluate all active policies
                policies_to_evaluate = [
                    p for p in self._policies.values() if p.is_active
                ]

            # Evaluate each policy
            results = []
            for policy in policies_to_evaluate:
                result = await self._evaluate_policy(
                    policy,
                    request.resource,
                    request.action,
                    request.subject,
                    request.environment,
                )
                results.append(result)

            # Determine final decision based on evaluation strategy
            final_effect = self.config.default_effect
            allowed = False
            denial_reason = None

            if results:
                if self.config.evaluation_strategy == "first_applicable":
                    # Use the first policy that has matching rules
                    for result in results:
                        if result.matched_rules:
                            final_effect = result.effect
                            break
                elif self.config.evaluation_strategy == "deny_overrides":
                    # If any policy denies, final decision is deny
                    allow_results = [
                        r
                        for r in results
                        if r.effect == PolicyEffect.ALLOW and r.matched_rules
                    ]
                    deny_results = [
                        r
                        for r in results
                        if r.effect == PolicyEffect.DENY and r.matched_rules
                    ]

                    if deny_results:
                        final_effect = PolicyEffect.DENY
                    elif allow_results:
                        final_effect = PolicyEffect.ALLOW
                elif self.config.evaluation_strategy == "permit_overrides":
                    # If any policy allows, final decision is allow
                    allow_results = [
                        r
                        for r in results
                        if r.effect == PolicyEffect.ALLOW and r.matched_rules
                    ]
                    deny_results = [
                        r
                        for r in results
                        if r.effect == PolicyEffect.DENY and r.matched_rules
                    ]

                    if allow_results:
                        final_effect = PolicyEffect.ALLOW
                    elif deny_results:
                        final_effect = PolicyEffect.DENY

            allowed = final_effect == PolicyEffect.ALLOW

            if not allowed:
                denial_reason = "No matching allow policies found"
                if results:
                    deny_results = [
                        r
                        for r in results
                        if r.effect == PolicyEffect.DENY and r.matched_rules
                    ]
                    if deny_results:
                        denial_reason = (
                            f"Access denied by policy: {deny_results[0].policy_name}"
                        )

            # Update statistics
            if allowed:
                self._stats["allow_decisions"] += 1
            else:
                self._stats["deny_decisions"] += 1

            end_time = datetime.now(UTC)
            total_evaluation_time = (end_time - start_time).total_seconds() * 1000
            self._stats["total_evaluation_time_ms"] += total_evaluation_time

            # Audit logging
            if self.config.enable_audit_logging:
                logger.info(
                    f"Policy evaluation: subject={subject_id}, resource={request.resource}, "
                    f"action={request.action}, allowed={allowed}, policies={len(results)}, "
                    f"time={total_evaluation_time:.2f}ms, tenant={tenant_id}"
                )

            return PolicyEvaluationResponse(
                allowed=allowed,
                subject_id=subject_id,
                resource=request.resource,
                action=request.action,
                results=results,
                final_effect=final_effect,
                total_evaluation_time_ms=total_evaluation_time,
                policies_evaluated=len(results),
                denial_reason=denial_reason,
            )

        except Exception as e:
            logger.error(f"Policy evaluation failed: {e}")
            end_time = datetime.now(UTC)
            total_evaluation_time = (end_time - start_time).total_seconds() * 1000

            return PolicyEvaluationResponse(
                allowed=False,
                subject_id=request.subject.get("user_id", "unknown"),
                resource=request.resource,
                action=request.action,
                results=[],
                final_effect=PolicyEffect.DENY,
                total_evaluation_time_ms=total_evaluation_time,
                policies_evaluated=0,
                denial_reason=f"Evaluation error: {str(e)}",
            )

    async def create_policy(
        self,
        request: PolicyCreateRequest,
        context: RequestContext | None = None,
    ) -> Policy:
        """Create a new policy."""
        try:
            # Generate policy ID
            policy_id = f"policy-{len(self._policies) + 1}"

            # Create policy
            policy = Policy(
                id=policy_id,
                name=request.name,
                description=request.description,
                type=request.type,
                rules=request.rules,
                tags=request.tags,
            )

            # Validate policy
            await self._validate_policy(policy)

            # Store policy
            self._policies[policy_id] = policy

            # Clear cache
            tenant_id = context.tenant_id if context else None
            cache_key = await self._get_cache_key("policies", "all", tenant_id)
            await self._cache_delete(cache_key)

            # Audit logging
            if self.config.enable_audit_logging:
                logger.info(
                    f"Policy created: id={policy_id}, name={request.name}, "
                    f"type={request.type}, rules={len(request.rules)}, "
                    f"created_by={context.user_id if context else 'system'}"
                )

            return policy

        except Exception as e:
            logger.error(f"Policy creation failed: {e}")
            raise PolicyError(f"Failed to create policy: {str(e)}")

    async def _validate_policy(self, policy: Policy) -> None:
        """Validate policy structure and rules."""
        if not policy.rules:
            raise InvalidPolicyError("Policy must have at least one rule")

        # Validate rule names are unique
        rule_names = [rule.name for rule in policy.rules]
        if len(rule_names) != len(set(rule_names)):
            raise InvalidPolicyError("Rule names must be unique within policy")

        # Validate each rule
        for rule in policy.rules:
            if not rule.resources:
                raise InvalidPolicyError(
                    f"Rule {rule.name} must specify at least one resource"
                )
            if not rule.actions:
                raise InvalidPolicyError(
                    f"Rule {rule.name} must specify at least one action"
                )

    async def get_policy(self, policy_id: str) -> Policy | None:
        """Get policy by ID."""
        return self._policies.get(policy_id)

    async def list_policies(
        self,
        request: PolicyListRequest,
        context: RequestContext | None = None,
    ) -> PolicyListResponse:
        """List policies with filtering."""
        policies = list(self._policies.values())

        # Apply filters
        if request.type is not None:
            policies = [p for p in policies if p.type == request.type]

        if request.is_active is not None:
            policies = [p for p in policies if p.is_active == request.is_active]

        if request.tags:
            policies = [
                p for p in policies if all(tag in p.tags for tag in request.tags)
            ]

        if request.search:
            search_lower = request.search.lower()
            policies = [
                p
                for p in policies
                if search_lower in p.name.lower()
                or (p.description and search_lower in p.description.lower())
            ]

        # Apply pagination
        total = len(policies)
        start_idx = (request.page - 1) * request.page_size
        end_idx = start_idx + request.page_size
        paginated_policies = policies[start_idx:end_idx]

        return PolicyListResponse(
            policies=paginated_policies,
            page=request.page,
            page_size=request.page_size,
            total=total,
            has_next=end_idx < total,
        )

    async def get_stats(self) -> PolicyStatsResponse:
        """Get policy statistics."""
        policies = list(self._policies.values())
        active_policies = [p for p in policies if p.is_active]

        policies_by_type = {}
        for policy in policies:
            policy_type = policy.type.value
            policies_by_type[policy_type] = policies_by_type.get(policy_type, 0) + 1

        total_rules = sum(len(p.rules) for p in policies)

        avg_evaluation_time = (
            self._stats["total_evaluation_time_ms"] / self._stats["evaluations"]
            if self._stats["evaluations"] > 0
            else 0.0
        )

        return PolicyStatsResponse(
            total_policies=len(policies),
            active_policies=len(active_policies),
            policies_by_type=policies_by_type,
            total_rules=total_rules,
            evaluations_count=self._stats["evaluations"],
            avg_evaluation_time_ms=avg_evaluation_time,
        )

    async def health_check(self) -> dict[str, Any]:
        """Perform health check."""
        try:
            # Test policy evaluation
            test_request = PolicyEvaluationRequest(
                subject={"user_id": "health_check_user"},
                resource="test/resource",
                action="read",
            )

            start_time = datetime.now(UTC)
            await self.evaluate(test_request)
            end_time = datetime.now(UTC)

            response_time = (end_time - start_time).total_seconds() * 1000

            return {
                "status": "healthy",
                "response_time_ms": response_time,
                "policies_count": len(self._policies),
                "active_policies_count": len(
                    [p for p in self._policies.values() if p.is_active]
                ),
                "cache_enabled": self.config.enable_caching,
                "audit_enabled": self.config.enable_audit_logging,
            }

        except Exception as e:
            logger.error(f"Policy health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "policies_count": len(self._policies),
            }


__all__ = [
    "PolicySDKConfig",
    "PolicySDK",
    "PolicyError",
    "PolicyNotFoundError",
    "PolicyEvaluationError",
    "InvalidPolicyError",
]
