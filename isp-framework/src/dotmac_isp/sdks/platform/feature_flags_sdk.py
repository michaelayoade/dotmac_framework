"""
Feature Flags SDK for dotmac_platform.

Contract-first SDK for feature flag management with evaluation engine,
targeting rules, rollout strategies, caching, and audit logging.
"""

import asyncio
import hashlib
import json
import logging
import re
from datetime import datetime
from dotmac_isp.sdks.platform.utils.datetime_compat import (
    utcnow,
    utc_now_iso,
    expires_in_days,
    expires_in_hours,
    is_expired,
)
from typing import Any
from uuid import UUID, uuid4

from dotmac_isp.sdks.contracts.feature_flags import (
    FeatureFlag,
    FeatureFlagAuditLog,
    FeatureFlagCreateRequest,
    FeatureFlagEvaluationRequest,
    FeatureFlagEvaluationResponse,
    FeatureFlagEvaluationResult,
    FeatureFlagHealthCheck,
    FeatureFlagListRequest,
    FeatureFlagListResponse,
    FeatureFlagStats,
    FeatureFlagStatus,
    FeatureFlagUpdateRequest,
    RolloutConfig,
    RolloutStrategy,
    TargetingOperator,
    TargetingRule,
    UserContext,
)

logger = logging.getLogger(__name__)


class FeatureFlagsSDKConfig:
    """Configuration for Feature Flags SDK."""

    def __init__(
        self,
        cache_ttl: int = 300,
        evaluation_timeout: float = 1.0,
        enable_audit_logging: bool = True,
        default_rollout_percentage: float = 0.0,
    ):
        self.cache_ttl = cache_ttl
        self.evaluation_timeout = evaluation_timeout
        self.enable_audit_logging = enable_audit_logging
        self.default_rollout_percentage = default_rollout_percentage


class FeatureFlagsSDK:
    """
    Contract-first Feature Flags SDK with evaluation engine and targeting.

    Provides feature flag management, evaluation, targeting rules,
    rollout strategies, caching, and comprehensive audit logging.
    """

    def __init__(
        self,
        cache_sdk=None,
        database_sdk=None,
        tenant_id: UUID | None = None,
        enable_caching: bool = True,
        cache_ttl: int = 300,
        enable_audit_logging: bool = True,
        evaluation_timeout: float = 1.0,
    ):
        """Initialize Feature Flags SDK."""
        self.cache_sdk = cache_sdk
        self.database_sdk = database_sdk
        self.tenant_id = tenant_id
        self.enable_caching = enable_caching
        self.cache_ttl = cache_ttl
        self.enable_audit_logging = enable_audit_logging
        self.evaluation_timeout = evaluation_timeout

        # In-memory storage for testing/development
        self._flags: dict[str, dict[str, FeatureFlag]] = (
            {}
        )  # tenant_id -> flag_key -> flag
        self._stats: dict[str, dict[str, FeatureFlagStats]] = (
            {}
        )  # tenant_id -> flag_key -> stats
        self._audit_logs: list[FeatureFlagAuditLog] = []

        # Evaluation cache
        self._evaluation_cache: dict[str, dict[str, Any]] = {}  # cache_key -> result

        logger.info("FeatureFlagsSDK initialized")

    async def create_flag(
        self,
        request: FeatureFlagCreateRequest,
        tenant_id: UUID | None = None,
        created_by: str | None = None,
    ) -> FeatureFlag:
        """Create a new feature flag."""
        tenant_id = tenant_id or self.tenant_id
        if not tenant_id:
            raise ValueError("tenant_id is required")

        # Check if flag key already exists
        existing_flag = await self._get_flag_by_key(request.key, tenant_id)
        if existing_flag:
            raise ValueError(f"Feature flag with key '{request.key}' already exists")

        # Create feature flag
        flag = FeatureFlag(
            id=uuid4(),
            tenant_id=tenant_id,
            name=request.name,
            key=request.key,
            description=request.description,
            flag_type=request.flag_type,
            status=FeatureFlagStatus.ACTIVE,
            default_value=request.default_value,
            enabled_value=request.enabled_value,
            rollout_config=request.rollout_config,
            tags=request.tags,
            created_by=created_by,
            created_at=utcnow(),
            updated_at=utcnow(),
            expires_at=request.expires_at,
        )

        # Store flag
        await self._store_flag(flag)

        # Initialize stats
        stats = FeatureFlagStats(
            flag_key=flag.key,
            total_evaluations=0,
            enabled_evaluations=0,
            disabled_evaluations=0,
            unique_users=0,
            rollout_percentage=self._get_rollout_percentage(flag.rollout_config),
        )
        await self._store_stats(stats, tenant_id)

        # Audit log
        if self.enable_audit_logging:
            await self._log_audit(
                tenant_id=tenant_id,
                flag_key=flag.key,
                action="create_flag",
                user_id=created_by,
                new_value=flag.model_dump(),
            )

        # Clear cache
        if self.enable_caching:
            await self._clear_flag_cache(tenant_id)

        logger.info(f"Created feature flag: {flag.key} for tenant {tenant_id}")
        return flag

    async def update_flag(
        self,
        flag_key: str,
        request: FeatureFlagUpdateRequest,
        tenant_id: UUID | None = None,
        updated_by: str | None = None,
    ) -> FeatureFlag:
        """Update an existing feature flag."""
        tenant_id = tenant_id or self.tenant_id
        if not tenant_id:
            raise ValueError("tenant_id is required")

        # Get existing flag
        existing_flag = await self._get_flag_by_key(flag_key, tenant_id)
        if not existing_flag:
            raise ValueError(f"Feature flag '{flag_key}' not found")

        old_value = existing_flag.model_dump()

        # Update fields
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(existing_flag, field, value)

        existing_flag.updated_at = utcnow()

        # Store updated flag
        await self._store_flag(existing_flag)

        # Update stats if rollout config changed
        if "rollout_config" in update_data:
            stats = await self._get_stats(flag_key, tenant_id)
            if stats:
                stats.rollout_percentage = self._get_rollout_percentage(
                    existing_flag.rollout_config
                )
                await self._store_stats(stats, tenant_id)

        # Audit log
        if self.enable_audit_logging:
            await self._log_audit(
                tenant_id=tenant_id,
                flag_key=flag_key,
                action="update_flag",
                user_id=updated_by,
                old_value=old_value,
                new_value=existing_flag.model_dump(),
            )

        # Clear cache
        if self.enable_caching:
            await self._clear_flag_cache(tenant_id)
            await self._clear_evaluation_cache(flag_key, tenant_id)

        logger.info(f"Updated feature flag: {flag_key} for tenant {tenant_id}")
        return existing_flag

    async def get_flag(
        self,
        flag_key: str,
        tenant_id: UUID | None = None,
    ) -> FeatureFlag | None:
        """Get a feature flag by key."""
        tenant_id = tenant_id or self.tenant_id
        if not tenant_id:
            raise ValueError("tenant_id is required")

        return await self._get_flag_by_key(flag_key, tenant_id)

    async def list_flags(
        self,
        request: FeatureFlagListRequest,
        tenant_id: UUID | None = None,
    ) -> FeatureFlagListResponse:
        """List feature flags with filtering and pagination."""
        tenant_id = tenant_id or self.tenant_id
        if not tenant_id:
            raise ValueError("tenant_id is required")

        # Get all flags for tenant
        tenant_flags = self._flags.get(str(tenant_id), {})
        flags = list(tenant_flags.values())

        # Apply filters
        if request.status:
            flags = [f for f in flags if f.status == request.status]
        if request.flag_type:
            flags = [f for f in flags if f.flag_type == request.flag_type]
        if request.tags:
            flags = [f for f in flags if any(tag in f.tags for tag in request.tags)]

        # Sort by created_at desc
        flags.sort(key=lambda f: f.created_at or datetime.min, reverse=True)

        # Pagination
        total = len(flags)
        start_idx = (request.page - 1) * request.page_size
        end_idx = start_idx + request.page_size
        page_flags = flags[start_idx:end_idx]
        has_next = end_idx < total

        return FeatureFlagListResponse(
            flags=page_flags,
            page=request.page,
            page_size=request.page_size,
            total=total,
            has_next=has_next,
        )

    async def delete_flag(
        self,
        flag_key: str,
        tenant_id: UUID | None = None,
        deleted_by: str | None = None,
    ) -> bool:
        """Delete a feature flag."""
        tenant_id = tenant_id or self.tenant_id
        if not tenant_id:
            raise ValueError("tenant_id is required")

        # Get existing flag
        existing_flag = await self._get_flag_by_key(flag_key, tenant_id)
        if not existing_flag:
            return False

        old_value = existing_flag.model_dump()

        # Remove flag
        tenant_str = str(tenant_id)
        if tenant_str in self._flags and flag_key in self._flags[tenant_str]:
            del self._flags[tenant_str][flag_key]

        # Remove stats
        if tenant_str in self._stats and flag_key in self._stats[tenant_str]:
            del self._stats[tenant_str][flag_key]

        # Audit log
        if self.enable_audit_logging:
            await self._log_audit(
                tenant_id=tenant_id,
                flag_key=flag_key,
                action="delete_flag",
                user_id=deleted_by,
                old_value=old_value,
            )

        # Clear cache
        if self.enable_caching:
            await self._clear_flag_cache(tenant_id)
            await self._clear_evaluation_cache(flag_key, tenant_id)

        logger.info(f"Deleted feature flag: {flag_key} for tenant {tenant_id}")
        return True

    async def evaluate_flags(
        self,
        request: FeatureFlagEvaluationRequest,
        tenant_id: UUID | None = None,
    ) -> FeatureFlagEvaluationResponse:
        """Evaluate multiple feature flags for a user."""
        tenant_id = tenant_id or self.tenant_id
        if not tenant_id:
            raise ValueError("tenant_id is required")

        start_time = utcnow()
        results = []
        cached = False

        # Check cache first
        if self.enable_caching:
            cache_key = self._get_evaluation_cache_key(request, tenant_id)
            cached_result = await self._get_evaluation_cache(cache_key)
            if cached_result:
                cached = True
                results = [
                    FeatureFlagEvaluationResult(**r) for r in cached_result["results"]
                ]

        if not cached:
            # Evaluate each flag
            for flag_key in request.flag_keys:
                result = await self._evaluate_single_flag(
                    flag_key=flag_key,
                    user_context=request.user_context,
                    default_value=(
                        request.default_values.get(flag_key)
                        if request.default_values
                        else None
                    ),
                    tenant_id=tenant_id,
                )
                results.append(result)

            # Cache results
            if self.enable_caching:
                cache_data = {
                    "results": [r.model_dump() for r in results],
                    "user_id": request.user_context.user_id,
                }
                await self._set_evaluation_cache(cache_key, cache_data)

        # Calculate evaluation time
        evaluation_time = (utcnow() - start_time).total_seconds() * 1000

        response = FeatureFlagEvaluationResponse(
            results=results,
            user_id=request.user_context.user_id,
            evaluation_time_ms=evaluation_time,
            cached=cached,
        )

        # Update stats (async)
        if not cached:
            asyncio.create_task(
                self._update_evaluation_stats(
                    results, request.user_context.user_id, tenant_id
                )
            )

        return response

    async def get_flag_stats(
        self,
        flag_key: str,
        tenant_id: UUID | None = None,
    ) -> FeatureFlagStats | None:
        """Get feature flag usage statistics."""
        tenant_id = tenant_id or self.tenant_id
        if not tenant_id:
            raise ValueError("tenant_id is required")

        return await self._get_stats(flag_key, tenant_id)

    async def health_check(
        self, tenant_id: UUID | None = None
    ) -> FeatureFlagHealthCheck:
        """Perform health check."""
        tenant_id = tenant_id or self.tenant_id

        start_time = utcnow()

        # Count flags
        total_flags = 0
        active_flags = 0

        if tenant_id:
            tenant_flags = self._flags.get(str(tenant_id), {})
            total_flags = len(tenant_flags)
            active_flags = len(
                [
                    f
                    for f in tenant_flags.values()
                    if f.status == FeatureFlagStatus.ACTIVE
                ]
            )
        else:
            # Count across all tenants
            for tenant_flags in self._flags.values():
                total_flags += len(tenant_flags)
                active_flags += len(
                    [
                        f
                        for f in tenant_flags.values()
                        if f.status == FeatureFlagStatus.ACTIVE
                    ]
                )

        # Calculate metrics
        evaluations_per_second = 0.0  # Would be calculated from recent stats
        cache_hit_rate = 0.8  # Mock value
        response_time = (utcnow() - start_time).total_seconds() * 1000

        # Get last evaluation time
        last_evaluation = None
        if self._audit_logs:
            evaluation_logs = [
                log for log in self._audit_logs if log.action == "evaluate_flag"
            ]
            if evaluation_logs:
                last_evaluation = max(log.timestamp for log in evaluation_logs)

        return FeatureFlagHealthCheck(
            status="healthy",
            total_flags=total_flags,
            active_flags=active_flags,
            evaluations_per_second=evaluations_per_second,
            cache_hit_rate=cache_hit_rate,
            response_time_ms=response_time,
            last_evaluation=last_evaluation,
        )

    # Private methods

    async def _get_flag_by_key(
        self, flag_key: str, tenant_id: UUID
    ) -> FeatureFlag | None:
        """Get flag by key from storage."""
        tenant_str = str(tenant_id)
        return self._flags.get(tenant_str, {}).get(flag_key)

    async def _store_flag(self, flag: FeatureFlag) -> None:
        """Store flag in storage."""
        tenant_str = str(flag.tenant_id)
        if tenant_str not in self._flags:
            self._flags[tenant_str] = {}
        self._flags[tenant_str][flag.key] = flag

    async def _get_stats(
        self, flag_key: str, tenant_id: UUID
    ) -> FeatureFlagStats | None:
        """Get flag stats from storage."""
        tenant_str = str(tenant_id)
        return self._stats.get(tenant_str, {}).get(flag_key)

    async def _store_stats(self, stats: FeatureFlagStats, tenant_id: UUID) -> None:
        """Store flag stats."""
        tenant_str = str(tenant_id)
        if tenant_str not in self._stats:
            self._stats[tenant_str] = {}
        self._stats[tenant_str][stats.flag_key] = stats

    async def _log_audit(
        self,
        tenant_id: UUID,
        flag_key: str,
        action: str,
        user_id: str | None = None,
        user_context: UserContext | None = None,
        old_value: dict[str, Any] | None = None,
        new_value: dict[str, Any] | None = None,
        **kwargs,
    ) -> None:
        """Log audit event."""
        audit_log = FeatureFlagAuditLog(
            id=uuid4(),
            tenant_id=tenant_id,
            flag_key=flag_key,
            action=action,
            user_id=user_id,
            user_context=user_context,
            old_value=old_value,
            new_value=new_value,
            metadata=kwargs,
        )
        self._audit_logs.append(audit_log)

    async def _evaluate_single_flag(
        self,
        flag_key: str,
        user_context: UserContext,
        default_value: Any | None,
        tenant_id: UUID,
    ) -> FeatureFlagEvaluationResult:
        """Evaluate a single feature flag for a user."""
        # Get flag
        flag = await self._get_flag_by_key(flag_key, tenant_id)

        if not flag:
            # Flag not found, use default
            value = default_value if default_value is not None else False
            return FeatureFlagEvaluationResult(
                flag_key=flag_key,
                value=value,
                enabled=False,
                evaluation_reason="flag_not_found",
            )

        # Check if flag is active
        if flag.status != FeatureFlagStatus.ACTIVE:
            return FeatureFlagEvaluationResult(
                flag_key=flag_key,
                value=flag.default_value,
                enabled=False,
                evaluation_reason="flag_inactive",
            )

        # Check expiration
        if flag.expires_at and utcnow() > flag.expires_at:
            return FeatureFlagEvaluationResult(
                flag_key=flag_key,
                value=flag.default_value,
                enabled=False,
                evaluation_reason="flag_expired",
            )

        # Evaluate rollout config
        enabled, reason, matched_rule, rollout_percentage = (
            await self._evaluate_rollout(flag.rollout_config, user_context)
        )

        value = flag.enabled_value if enabled else flag.default_value

        # Audit log
        if self.enable_audit_logging:
            await self._log_audit(
                tenant_id=tenant_id,
                flag_key=flag_key,
                action="evaluate_flag",
                user_context=user_context,
                metadata={
                    "enabled": enabled,
                    "value": value,
                    "reason": reason,
                },
            )

        return FeatureFlagEvaluationResult(
            flag_key=flag_key,
            value=value,
            enabled=enabled,
            matched_rule=matched_rule,
            rollout_percentage=rollout_percentage,
            evaluation_reason=reason,
        )

    async def _evaluate_rollout(
        self,
        rollout_config: RolloutConfig,
        user_context: UserContext,
    ) -> tuple[bool, str, str | None, float | None]:
        """Evaluate rollout configuration."""
        strategy = rollout_config.strategy

        if strategy == RolloutStrategy.ALL_USERS:
            return True, "all_users", None, 100.0

        elif strategy == RolloutStrategy.PERCENTAGE:
            percentage = rollout_config.percentage or 0.0
            # Use consistent hash for user
            user_hash = int(
                hashlib.sha256(user_context.user_id.encode()).hexdigest()[:8], 16
            )
            user_percentage = (user_hash % 10000) / 100.0  # 0-99.99
            enabled = user_percentage < percentage
            return enabled, f"percentage_rollout_{percentage}%", None, percentage

        elif strategy == RolloutStrategy.USER_LIST:
            user_list = rollout_config.user_list or []
            enabled = user_context.user_id in user_list
            return enabled, "user_list", None, None

        elif strategy == RolloutStrategy.USER_ATTRIBUTES:
            targeting_rules = rollout_config.targeting_rules or []
            for rule in targeting_rules:
                if await self._evaluate_targeting_rule(rule, user_context):
                    return True, "targeting_rule", rule.description, None
            return False, "targeting_rule_no_match", None, None

        elif strategy == RolloutStrategy.GRADUAL:
            # Simplified gradual rollout - would need more sophisticated implementation
            utcnow()
            # For now, just use percentage if available
            percentage = rollout_config.percentage or 0.0
            user_hash = int(
                hashlib.sha256(user_context.user_id.encode()).hexdigest()[:8], 16
            )
            user_percentage = (user_hash % 10000) / 100.0
            enabled = user_percentage < percentage
            return enabled, f"gradual_rollout_{percentage}%", None, percentage

        return False, "unknown_strategy", None, None

    async def _evaluate_targeting_rule(
        self, rule: TargetingRule, user_context: UserContext
    ) -> bool:
        """
        Evaluate a targeting rule against user context.
        
        REFACTORED: Replaced 21-complexity if-elif chain with Strategy pattern.
        Complexity reduced from 21 to 3 McCabe score.
        """
        from .feature_flags.strategies import evaluate_targeting_rule
        
        attribute_value = user_context.attributes.get(rule.attribute)
        if attribute_value is None:
            return False

        return evaluate_targeting_rule(rule.operator, attribute_value, rule.value)

    def _get_rollout_percentage(self, rollout_config: RolloutConfig) -> float | None:
        """Get rollout percentage from config."""
        if rollout_config.strategy == RolloutStrategy.PERCENTAGE:
            return rollout_config.percentage
        elif rollout_config.strategy == RolloutStrategy.ALL_USERS:
            return 100.0
        return None

    def _get_evaluation_cache_key(
        self, request: FeatureFlagEvaluationRequest, tenant_id: UUID
    ) -> str:
        """Generate cache key for evaluation request."""
        key_data = {
            "tenant_id": str(tenant_id),
            "flag_keys": sorted(request.flag_keys),
            "user_id": request.user_context.user_id,
            "attributes": request.user_context.attributes,
            "groups": sorted(request.user_context.groups),
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return f"ff_eval:{hashlib.sha256(key_str.encode()).hexdigest()}"

    async def _get_evaluation_cache(self, cache_key: str) -> dict[str, Any] | None:
        """Get evaluation result from cache."""
        return self._evaluation_cache.get(cache_key)

    async def _set_evaluation_cache(self, cache_key: str, data: dict[str, Any]) -> None:
        """Set evaluation result in cache."""
        self._evaluation_cache[cache_key] = data

    async def _clear_flag_cache(self, tenant_id: UUID) -> None:
        """Clear flag-related cache entries."""
        # In a real implementation, would clear Redis cache
        pass

    async def _clear_evaluation_cache(self, flag_key: str, tenant_id: UUID) -> None:
        """Clear evaluation cache for a specific flag."""
        # Remove cache entries containing this flag
        keys_to_remove = []
        for cache_key in self._evaluation_cache:
            if flag_key in cache_key:  # Simplified check
                keys_to_remove.append(cache_key)

        for key in keys_to_remove:
            del self._evaluation_cache[key]

    async def _update_evaluation_stats(
        self,
        results: list[FeatureFlagEvaluationResult],
        user_id: str,
        tenant_id: UUID,
    ) -> None:
        """Update evaluation statistics."""
        for result in results:
            stats = await self._get_stats(result.flag_key, tenant_id)
            if stats:
                stats.total_evaluations += 1
                if result.enabled:
                    stats.enabled_evaluations += 1
                else:
                    stats.disabled_evaluations += 1
                stats.last_evaluation = utcnow()
                await self._store_stats(stats, tenant_id)
