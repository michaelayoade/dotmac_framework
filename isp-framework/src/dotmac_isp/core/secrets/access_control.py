"""
Access Control Helper - Extracted from RBAC for better maintainability.

This module provides helper classes for access control evaluation,
breaking down complex permission checking logic into manageable components.
"""

import logging
import time
from datetime import datetime, timedelta
from ..utils.datetime_compat import utcnow
from dotmac_isp.sdks.platform.utils.datetime_compat import (
    utcnow,
    utc_now_iso,
    expires_in_days,
    expires_in_hours,
    is_expired,
)
from typing import Any

from .rbac import (
    AccessDecision,
    AccessRequest,
    AccessResponse,
    Permission,
    PolicyRule,
    Subject,
)

logger = logging.getLogger(__name__)


class AccessCacheManager:
    """Manages access control caching for performance optimization."""

    def __init__(self, cache_ttl: timedelta = timedelta(minutes=5)):
        self.cache: dict[str, tuple[AccessResponse, datetime]] = {}
        self.cache_ttl = cache_ttl

    def generate_cache_key(self, request: AccessRequest) -> str:
        """Generate a cache key for the access request."""
        return f"{request.subject_id}:{request.resource_type}:{request.action}:{hash(str(request.context))}"

    def get_cached_response(self, cache_key: str) -> AccessResponse | None:
        """Get cached access response if still valid."""
        cached_response = self.cache.get(cache_key)

        if cached_response:
            response, timestamp = cached_response
            if utcnow() - timestamp < self.cache_ttl:
                return response

        return None

    def cache_response(self, cache_key: str, response: AccessResponse) -> None:
        """Cache an access response."""
        self.cache[cache_key] = (response, utcnow())

    def invalidate_subject_cache(self, subject_id: str) -> None:
        """Invalidate all cache entries for a specific subject."""
        keys_to_remove = [key for key in self.cache if key.startswith(f"{subject_id}:")]
        for key in keys_to_remove:
            del self.cache[key]


class PermissionMatcher:
    """Handles permission matching logic."""

    def __init__(self, permissions: dict[str, Permission]):
        self.permissions = permissions

    def find_matching_permission(
        self, subject_permissions: list[str], resource_type: str, action: str
    ) -> Permission | None:
        """Find the first permission that matches the resource type and action."""
        for perm_id in subject_permissions:
            permission = self.permissions.get(perm_id)
            if permission and permission.matches(resource_type, action):
                return permission
        return None


class PolicyContextBuilder:
    """Builds policy evaluation context from request and subject data."""

    @staticmethod
    def build_context(
        subject: Subject, request: AccessRequest, cache_key: str
    ) -> dict[str, Any]:
        """Build comprehensive policy evaluation context."""
        return {
            "subject": {
                "id": subject.id,
                "type": subject.type,
                "roles": list(subject.roles),
                "attributes": subject.attributes,
                **(subject.session_context or {}),
            },
            "resource": {
                "type": request.resource_type,
                "id": request.resource_id,
                **(request.context or {}),
            },
            "action": request.action,
            "environment": {"timestamp": utcnow().isoformat(), "request_id": cache_key},
        }


class PolicyDecisionMaker:
    """Handles policy rule evaluation and decision making."""

    @staticmethod
    def evaluate_policy_rules(
        applicable_rules: list[PolicyRule],
    ) -> tuple[AccessDecision, str]:
        """
        Evaluate policy rules and return decision.

        Args:
            applicable_rules: List of policy rules to evaluate

        Returns:
            Tuple of (decision, reason)
        """
        # Apply policy rules (first matching rule wins)
        for rule in applicable_rules:
            if rule.effect == "permit":
                return (
                    AccessDecision.PERMIT,
                    f"Policy rule '{rule.name}' permits access",
                )
            elif rule.effect == "deny":
                return AccessDecision.DENY, f"Policy rule '{rule.name}' denies access"

        return AccessDecision.NOT_APPLICABLE, ""

    @staticmethod
    def make_final_decision(
        policy_decision: AccessDecision,
        policy_reason: str,
        permission_match: Permission,
    ) -> tuple[AccessDecision, str]:
        """
        Make final access decision based on policy and permission results.

        Args:
            policy_decision: Policy evaluation result
            policy_reason: Policy evaluation reason
            permission_match: Matching permission

        Returns:
            Tuple of (final_decision, final_reason)
        """
        if policy_decision == AccessDecision.DENY:
            return AccessDecision.DENY, policy_reason
        elif policy_decision in (AccessDecision.PERMIT, AccessDecision.NOT_APPLICABLE):
            final_reason = f"Permission '{permission_match.id}' allows access"
            if policy_reason:
                final_reason += f" and {policy_reason}"
            return AccessDecision.PERMIT, final_reason
        else:
            return AccessDecision.DENY, "Access denied by default"


class AccessControlEvaluator:
    """Main access control evaluation orchestrator."""

    def __init__(
        self,
        subjects: dict[str, Subject],
        permissions: dict[str, Permission],
        policy_engine,
        get_subject_permissions_func,
        cache_ttl: timedelta = timedelta(minutes=5),
    ):
        self.subjects = subjects
        self.cache_manager = AccessCacheManager(cache_ttl)
        self.permission_matcher = PermissionMatcher(permissions)
        self.policy_engine = policy_engine
        self.get_subject_permissions = get_subject_permissions_func

    def check_cached_access(
        self, cache_key: str, start_time: float
    ) -> AccessResponse | None:
        """Check for cached access response."""
        cached_response = self.cache_manager.get_cached_response(cache_key)
        if cached_response:
            cached_response.evaluation_time = time.time() - start_time
            return cached_response
        return None

    def validate_subject(
        self, request: AccessRequest, start_time: float
    ) -> AccessResponse | None:
        """Validate that the subject exists."""
        subject = self.subjects.get(request.subject_id)
        if not subject:
            return AccessResponse(
                decision=AccessDecision.DENY,
                reason=f"Subject not found: {request.subject_id}",
                evaluation_time=time.time() - start_time,
            )
        return None

    def check_permission_match(
        self, request: AccessRequest, cache_key: str, start_time: float
    ) -> tuple[Permission | None, AccessResponse | None]:
        """Check for matching permissions."""
        subject_permissions = self.get_subject_permissions(request.subject_id)
        permission_match = self.permission_matcher.find_matching_permission(
            subject_permissions, request.resource_type, request.action
        )

        if not permission_match:
            response = AccessResponse(
                decision=AccessDecision.DENY,
                reason=f"No matching permission for {request.resource_type}:{request.action}",
                evaluation_time=time.time() - start_time,
            )
            self.cache_manager.cache_response(cache_key, response)
            return None, response

        return permission_match, None

    def evaluate_policies(
        self, subject: Subject, request: AccessRequest, cache_key: str
    ) -> tuple[AccessDecision, str]:
        """Evaluate applicable policies."""
        policy_context = PolicyContextBuilder.build_context(subject, request, cache_key)
        applicable_rules = self.policy_engine.evaluate_rules(policy_context)
        return PolicyDecisionMaker.evaluate_policy_rules(applicable_rules)

    def create_final_response(
        self,
        policy_decision: AccessDecision,
        policy_reason: str,
        permission_match: Permission,
        cache_key: str,
        start_time: float,
    ) -> AccessResponse:
        """Create the final access response."""
        final_decision, final_reason = PolicyDecisionMaker.make_final_decision(
            policy_decision, policy_reason, permission_match
        )

        response = AccessResponse(
            decision=final_decision,
            reason=final_reason,
            evaluated_permissions=[permission_match.id],
            evaluation_time=time.time() - start_time,
        )

        self.cache_manager.cache_response(cache_key, response)
        return response
