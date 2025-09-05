"""
Authentication manager for WebSocket connections.
"""

import asyncio
import logging
import time
from typing import Any, Optional

import aiohttp

from .types import AuthResult, UserInfo

logger = logging.getLogger(__name__)

# Try to import JWT support (optional dependency)
try:
    import jwt

    JWT_AVAILABLE = True
except ImportError:
    jwt = None
    JWT_AVAILABLE = False


class AuthManager:
    """Manages WebSocket authentication."""

    def __init__(self, config):
        self.config = config
        self._user_cache: dict[str, tuple[UserInfo, float]] = {}  # user_id -> (info, expire_time)
        self._token_cache: dict[
            str, tuple[AuthResult, float]
        ] = {}  # token -> (result, expire_time)

        if config.require_token and not JWT_AVAILABLE:
            logger.warning("JWT authentication required but PyJWT not available")

    async def authenticate_token(self, token: str) -> AuthResult:
        """Authenticate a JWT token."""
        if not self.config.enabled:
            return AuthResult.success_result(
                UserInfo(user_id="anonymous", tenant_id=self.config.default_tenant_id)
            )

        # Check cache first
        if token in self._token_cache:
            cached_result, expire_time = self._token_cache[token]
            if time.time() < expire_time:
                return cached_result
            else:
                # Remove expired entry
                del self._token_cache[token]

        try:
            if not JWT_AVAILABLE:
                return AuthResult.failure_result("JWT library not available")

            if not self.config.jwt_secret_key:
                return AuthResult.failure_result("JWT secret not configured")

            # Decode JWT token
            payload = jwt.decode(
                token, self.config.jwt_secret_key, algorithms=[self.config.jwt_algorithm]
            )

            # Extract user information
            user_id = payload.get("sub") or payload.get("user_id")
            if not user_id:
                return AuthResult.failure_result("Token missing user ID")

            user_info = UserInfo(
                user_id=str(user_id),
                username=payload.get("username"),
                email=payload.get("email"),
                tenant_id=payload.get("tenant_id"),
                roles=payload.get("roles", []),
                permissions=payload.get("permissions", []),
                extra_data={
                    k: v
                    for k, v in payload.items()
                    if k
                    not in [
                        "sub",
                        "user_id",
                        "username",
                        "email",
                        "tenant_id",
                        "roles",
                        "permissions",
                        "exp",
                        "iat",
                        "iss",
                    ]
                },
            )

            # Check required permissions
            if self.config.require_permissions:
                missing_perms = [
                    perm
                    for perm in self.config.require_permissions
                    if not user_info.has_permission(perm)
                ]
                if missing_perms:
                    return AuthResult.failure_result(f"Missing permissions: {missing_perms}")

            result = AuthResult.success_result(
                user_info, token_type="jwt", expires_at=payload.get("exp"), auth_method="jwt"
            )

            # Cache result
            cache_ttl = min(
                self.config.user_cache_ttl_seconds,
                (payload.get("exp", time.time() + 3600) - time.time()),
            )
            if cache_ttl > 0:
                self._token_cache[token] = (result, time.time() + cache_ttl)

            return result

        except jwt.ExpiredSignatureError:
            return AuthResult.failure_result("Token expired")
        except jwt.InvalidTokenError as e:
            return AuthResult.failure_result(f"Invalid token: {e}")
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return AuthResult.failure_result("Authentication failed")

    async def authenticate_api_key(self, api_key: str) -> AuthResult:
        """Authenticate using API key (placeholder for custom implementation)."""
        # This would typically validate against a database or external service
        # For now, just return a failure
        return AuthResult.failure_result("API key authentication not implemented")

    async def resolve_user(self, user_id: str) -> Optional[UserInfo]:
        """Resolve user information by ID."""
        # Check cache first
        if user_id in self._user_cache:
            user_info, expire_time = self._user_cache[user_id]
            if time.time() < expire_time:
                return user_info
            else:
                # Remove expired entry
                del self._user_cache[user_id]

        # Try to resolve via external service
        if self.config.user_resolver_url:
            try:
                user_info = await self._resolve_user_external(user_id)
                if user_info:
                    # Cache result
                    expire_time = time.time() + self.config.user_cache_ttl_seconds
                    self._user_cache[user_id] = (user_info, expire_time)
                    return user_info
            except Exception as e:
                logger.error(f"Error resolving user {user_id}: {e}")

        return None

    async def _resolve_user_external(self, user_id: str) -> Optional[UserInfo]:
        """Resolve user via external HTTP service."""
        try:
            timeout = aiohttp.ClientTimeout(total=5)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                url = f"{self.config.user_resolver_url.rstrip('/')}/users/{user_id}"
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return UserInfo(
                            user_id=data["user_id"],
                            username=data.get("username"),
                            email=data.get("email"),
                            tenant_id=data.get("tenant_id"),
                            roles=data.get("roles", []),
                            permissions=data.get("permissions", []),
                            extra_data=data.get("extra_data", {}),
                        )
                    else:
                        logger.warning(
                            f"User resolver returned status {response.status} for user {user_id}"
                        )

        except asyncio.TimeoutError:
            logger.warning(f"User resolver timeout for user {user_id}")
        except Exception as e:
            logger.error(f"User resolver error for user {user_id}: {e}")

        return None

    def extract_token_from_headers(self, headers: dict[str, str]) -> Optional[str]:
        """Extract token from request headers."""
        auth_header = headers.get(self.config.token_header, "")

        if auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix
        elif auth_header.startswith("Token "):
            return auth_header[6:]  # Remove "Token " prefix
        elif auth_header:
            return auth_header  # Use as-is

        return None

    def extract_token_from_query(self, query_params: dict[str, str]) -> Optional[str]:
        """Extract token from query parameters."""
        return query_params.get(self.config.token_query_param)

    async def validate_websocket_auth(self, websocket, path: str) -> AuthResult:
        """Validate authentication for WebSocket connection."""
        if not self.config.enabled:
            return AuthResult.success_result(UserInfo(user_id="anonymous", tenant_id="default"))

        # Extract token from headers or query params
        token = None

        # Check headers first
        if hasattr(websocket, "request_headers"):
            headers = {k: v for k, v in websocket.request_headers.raw}
            token = self.extract_token_from_headers(headers)

        # Check query parameters if no header token
        if not token and hasattr(websocket, "path"):
            try:
                from urllib.parse import parse_qs, urlparse

                parsed_url = urlparse(websocket.path)
                query_params = {k: v[0] for k, v in parse_qs(parsed_url.query).items()}
                token = self.extract_token_from_query(query_params)
            except Exception:
                pass

        if not token:
            if self.config.require_token:
                return AuthResult.failure_result("Authentication token required")
            else:
                # Allow anonymous connection
                return AuthResult.success_result(UserInfo(user_id="anonymous", tenant_id="default"))

        # Authenticate token
        return await self.authenticate_token(token)

    def cleanup_cache(self):
        """Clean up expired cache entries."""
        current_time = time.time()

        # Clean token cache
        expired_tokens = [
            token
            for token, (_, expire_time) in self._token_cache.items()
            if expire_time < current_time
        ]
        for token in expired_tokens:
            del self._token_cache[token]

        # Clean user cache
        expired_users = [
            user_id
            for user_id, (_, expire_time) in self._user_cache.items()
            if expire_time < current_time
        ]
        for user_id in expired_users:
            del self._user_cache[user_id]

        if expired_tokens or expired_users:
            logger.debug(
                f"Cleaned up {len(expired_tokens)} expired tokens and {len(expired_users)} expired users"
            )

    def get_stats(self) -> dict[str, Any]:
        """Get authentication manager statistics."""
        return {
            "enabled": self.config.enabled,
            "require_token": self.config.require_token,
            "cached_tokens": len(self._token_cache),
            "cached_users": len(self._user_cache),
            "jwt_available": JWT_AVAILABLE,
            "user_resolver_configured": bool(self.config.user_resolver_url),
        }
