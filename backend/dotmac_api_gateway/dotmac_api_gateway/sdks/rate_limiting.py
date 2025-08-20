"""
Rate Limiting SDK - Token bucket, sliding window, quota management.
"""

import time
from datetime import datetime
from ..core.datetime_utils import utc_now_iso, utc_now, expires_in_days, expires_in_hours, time_ago_minutes, time_ago_hours, is_expired_iso
from typing import Any, Dict
from uuid import uuid4

from ..core.exceptions import ConfigurationError, RateLimitError


class RateLimitingService:
    """In-memory service for rate limiting operations."""

    def __init__(self):
        self._rate_limit_policies: Dict[str, Dict[str, Any]] = {}
        self._rate_limit_counters: Dict[str, Dict[str, Any]] = {}
        self._quotas: Dict[str, Dict[str, Any]] = {}

    async def create_rate_limit_policy(self, **kwargs) -> Dict[str, Any]:
        """Create rate limiting policy."""
        policy_id = kwargs.get("policy_id") or str(uuid4())

        policy = {
            "policy_id": policy_id,
            "name": kwargs["name"],
            "algorithm": kwargs.get("algorithm", "sliding_window"),  # token_bucket, sliding_window, fixed_window
            "requests_per_minute": kwargs.get("requests_per_minute", 1000),
            "requests_per_hour": kwargs.get("requests_per_hour"),
            "requests_per_day": kwargs.get("requests_per_day"),
            "burst_size": kwargs.get("burst_size", 100),
            "window_size_seconds": kwargs.get("window_size_seconds", 60),
            "refill_rate": kwargs.get("refill_rate", 1),
            "apply_per_user": kwargs.get("apply_per_user", True),
            "apply_per_api": kwargs.get("apply_per_api", False),
            "apply_per_ip": kwargs.get("apply_per_ip", False),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }

        self._rate_limit_policies[policy_id] = policy
        return policy

    async def check_rate_limit(self, policy_id: str, identifier: str) -> Dict[str, Any]:
        """Check rate limit for identifier."""
        policy = self._rate_limit_policies.get(policy_id)
        if not policy:
            raise ConfigurationError(f"Rate limit policy not found: {policy_id}")

        algorithm = policy["algorithm"]

        if algorithm == "token_bucket":
            return await self._check_token_bucket(policy, identifier)
        elif algorithm == "sliding_window":
            return await self._check_sliding_window(policy, identifier)
        elif algorithm == "fixed_window":
            return await self._check_fixed_window(policy, identifier)
        else:
            raise ConfigurationError(f"Unsupported algorithm: {algorithm}")

    async def _check_token_bucket(self, policy: Dict[str, Any], identifier: str) -> Dict[str, Any]:
        """Check token bucket rate limit."""
        key = f"{policy['policy_id']}:{identifier}"
        now = time.time()

        if key not in self._rate_limit_counters:
            self._rate_limit_counters[key] = {
                "tokens": policy["burst_size"],
                "last_refill": now,
                "requests_count": 0
            }

        counter = self._rate_limit_counters[key]

        # Refill tokens
        time_passed = now - counter["last_refill"]
        tokens_to_add = time_passed * (policy["requests_per_minute"] / 60.0)
        counter["tokens"] = min(policy["burst_size"], counter["tokens"] + tokens_to_add)
        counter["last_refill"] = now

        # Check if request is allowed
        if counter["tokens"] >= 1:
            counter["tokens"] -= 1
            counter["requests_count"] += 1

            return {
                "allowed": True,
                "tokens_remaining": int(counter["tokens"]),
                "requests_count": counter["requests_count"],
                "reset_time": None
            }
        else:
            raise RateLimitError(f"Rate limit exceeded for {identifier}")

    async def _check_sliding_window(self, policy: Dict[str, Any], identifier: str) -> Dict[str, Any]:
        """Check sliding window rate limit."""
        key = f"{policy['policy_id']}:{identifier}"
        now = time.time()
        window_size = policy["window_size_seconds"]
        window_start = now - window_size

        if key not in self._rate_limit_counters:
            self._rate_limit_counters[key] = {
                "requests": [],
                "requests_count": 0
            }

        counter = self._rate_limit_counters[key]

        # Remove old requests outside the window
        counter["requests"] = [req_time for req_time in counter["requests"] if req_time > window_start]

        # Check if request is allowed
        requests_per_minute = policy["requests_per_minute"]
        if len(counter["requests"]) < requests_per_minute:
            counter["requests"].append(now)
            counter["requests_count"] += 1

            return {
                "allowed": True,
                "requests_remaining": requests_per_minute - len(counter["requests"]),
                "requests_count": counter["requests_count"],
                "reset_time": int(counter["requests"][0] + window_size) if counter["requests"] else None
            }
        else:
            reset_time = int(counter["requests"][0] + window_size)
            raise RateLimitError(f"Rate limit exceeded for {identifier}. Reset at {reset_time}")

    async def _check_fixed_window(self, policy: Dict[str, Any], identifier: str) -> Dict[str, Any]:
        """Check fixed window rate limit."""
        key = f"{policy['policy_id']}:{identifier}"
        now = time.time()
        window_size = policy["window_size_seconds"]
        current_window = int(now // window_size) * window_size

        if key not in self._rate_limit_counters:
            self._rate_limit_counters[key] = {
                "window_start": current_window,
                "requests_count": 0,
                "total_requests": 0
            }

        counter = self._rate_limit_counters[key]

        # Reset counter if we're in a new window
        if counter["window_start"] != current_window:
            counter["window_start"] = current_window
            counter["requests_count"] = 0

        # Check if request is allowed
        requests_per_minute = policy["requests_per_minute"]
        if counter["requests_count"] < requests_per_minute:
            counter["requests_count"] += 1
            counter["total_requests"] += 1

            return {
                "allowed": True,
                "requests_remaining": requests_per_minute - counter["requests_count"],
                "requests_count": counter["total_requests"],
                "reset_time": int(current_window + window_size)
            }
        else:
            reset_time = int(current_window + window_size)
            raise RateLimitError(f"Rate limit exceeded for {identifier}. Reset at {reset_time}")


class RateLimitingSDK:
    """SDK for API Gateway rate limiting."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = RateLimitingService()

    async def create_rate_limit_policy(
        self,
        name: str,
        algorithm: str = "sliding_window",
        requests_per_minute: int = 1000,
        **kwargs
    ) -> Dict[str, Any]:
        """Create rate limiting policy."""
        return await self._service.create_rate_limit_policy(
            name=name,
            algorithm=algorithm,
            requests_per_minute=requests_per_minute,
            **kwargs
        )

    async def check_rate_limit(self, policy_id: str, identifier: str) -> Dict[str, Any]:
        """Check rate limit for identifier."""
        return await self._service.check_rate_limit(policy_id, identifier)
