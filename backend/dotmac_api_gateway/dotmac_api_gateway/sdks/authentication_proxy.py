"""
Authentication Proxy SDK - Multi-provider authentication, JWT, OAuth2, API keys.
"""

import time
from datetime import datetime
from ..core.datetime_utils import utc_now_iso, utc_now, expires_in_days, expires_in_hours, time_ago_minutes, time_ago_hours, is_expired_iso
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
)


class AuthenticationProxyService:
    """In-memory service for authentication proxy operations."""

    def __init__(self):
        self._auth_policies: Dict[str, Dict[str, Any]] = {}
        self._auth_providers: Dict[str, Dict[str, Any]] = {}
        self._api_keys: Dict[str, Dict[str, Any]] = {}
        self._jwt_tokens: Dict[str, Dict[str, Any]] = {}
        self._oauth2_sessions: Dict[str, Dict[str, Any]] = {}

    async def create_auth_policy(self, **kwargs) -> Dict[str, Any]:
        """Create authentication policy."""
        policy_id = kwargs.get("policy_id") or str(uuid4())

        if policy_id in self._auth_policies:
            raise ConfigurationError(f"Auth policy already exists: {policy_id}")

        policy = {
            "policy_id": policy_id,
            "name": kwargs["name"],
            "auth_type": kwargs["auth_type"],  # jwt, oauth2, api_key, basic
            "provider_id": kwargs.get("provider_id"),
            "required_scopes": kwargs.get("required_scopes", []),
            "required_roles": kwargs.get("required_roles", []),
            "jwt_secret_key": kwargs.get("jwt_secret_key"),
            "jwt_algorithm": kwargs.get("jwt_algorithm", "HS256"),
            "jwt_issuer": kwargs.get("jwt_issuer"),
            "jwt_audience": kwargs.get("jwt_audience"),
            "oauth2_client_id": kwargs.get("oauth2_client_id"),
            "oauth2_client_secret": kwargs.get("oauth2_client_secret"),
            "oauth2_authorization_url": kwargs.get("oauth2_authorization_url"),
            "oauth2_token_url": kwargs.get("oauth2_token_url"),
            "api_key_header": kwargs.get("api_key_header", "X-API-Key"),
            "api_key_query_param": kwargs.get("api_key_query_param"),
            "enable_bearer_token": kwargs.get("enable_bearer_token", True),
            "enable_query_param": kwargs.get("enable_query_param", False),
            "token_ttl": kwargs.get("token_ttl", 3600),
            "refresh_enabled": kwargs.get("refresh_enabled", True),
            "status": kwargs.get("status", "active"),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "metadata": kwargs.get("metadata", {}),
        }

        self._auth_policies[policy_id] = policy
        return policy

    async def get_auth_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get authentication policy by ID."""
        return self._auth_policies.get(policy_id)

    async def update_auth_policy(self, policy_id: str, **updates) -> Dict[str, Any]:
        """Update authentication policy."""
        policy = self._auth_policies.get(policy_id)
        if not policy:
            raise ConfigurationError(f"Auth policy not found: {policy_id}")

        for key, value in updates.items():
            if key in policy:
                policy[key] = value

        policy["updated_at"] = utc_now_iso()
        return policy

    async def delete_auth_policy(self, policy_id: str) -> bool:
        """Delete authentication policy."""
        if policy_id not in self._auth_policies:
            raise ConfigurationError(f"Auth policy not found: {policy_id}")

        del self._auth_policies[policy_id]
        return True

    async def create_jwt_auth_provider(self, **kwargs) -> Dict[str, Any]:
        """Create JWT authentication provider."""
        provider_id = kwargs.get("provider_id") or str(uuid4())

        provider = {
            "provider_id": provider_id,
            "name": kwargs["name"],
            "type": "jwt",
            "secret_key": kwargs["secret_key"],
            "algorithm": kwargs.get("algorithm", "HS256"),
            "issuer": kwargs.get("issuer"),
            "audience": kwargs.get("audience", []),
            "expiration_seconds": kwargs.get("expiration_seconds", 3600),
            "verify_signature": kwargs.get("verify_signature", True),
            "verify_expiration": kwargs.get("verify_expiration", True),
            "verify_issuer": kwargs.get("verify_issuer", True),
            "verify_audience": kwargs.get("verify_audience", True),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }

        self._auth_providers[provider_id] = provider
        return provider

    async def create_oauth2_auth_provider(self, **kwargs) -> Dict[str, Any]:
        """Create OAuth2 authentication provider."""
        provider_id = kwargs.get("provider_id") or str(uuid4())

        provider = {
            "provider_id": provider_id,
            "name": kwargs["name"],
            "type": "oauth2",
            "client_id": kwargs["client_id"],
            "client_secret": kwargs["client_secret"],
            "authorization_url": kwargs["authorization_url"],
            "token_url": kwargs["token_url"],
            "userinfo_url": kwargs.get("userinfo_url"),
            "scope": kwargs.get("scope", "openid"),
            "redirect_uri": kwargs.get("redirect_uri"),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }

        self._auth_providers[provider_id] = provider
        return provider

    async def create_api_key_auth_provider(self, **kwargs) -> Dict[str, Any]:
        """Create API key authentication provider."""
        provider_id = kwargs.get("provider_id") or str(uuid4())

        provider = {
            "provider_id": provider_id,
            "name": kwargs["name"],
            "type": "api_key",
            "header_name": kwargs.get("header_name", "X-API-Key"),
            "query_param_name": kwargs.get("query_param_name"),
            "key_format": kwargs.get("key_format", "ak_[a-zA-Z0-9]{32}"),
            "allow_query_param": kwargs.get("allow_query_param", False),
            "allow_header": kwargs.get("allow_header", True),
            "key_prefix": kwargs.get("key_prefix", "ak_"),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
        }

        self._auth_providers[provider_id] = provider
        return provider

    async def generate_api_key(self, **kwargs) -> Dict[str, Any]:
        """Generate API key."""
        import secrets

        key_id = kwargs.get("key_id") or str(uuid4())
        api_key = f"ak_{secrets.token_urlsafe(32)}"

        key_data = {
            "key_id": key_id,
            "api_key": api_key,
            "name": kwargs.get("name", "API Key"),
            "description": kwargs.get("description", ""),
            "user_id": kwargs.get("user_id"),
            "tenant_id": kwargs.get("tenant_id"),
            "scopes": kwargs.get("scopes", []),
            "roles": kwargs.get("roles", []),
            "rate_limit": kwargs.get("rate_limit"),
            "expires_at": kwargs.get("expires_at"),
            "last_used_at": None,
            "usage_count": 0,
            "status": kwargs.get("status", "active"),
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "metadata": kwargs.get("metadata", {}),
        }

        self._api_keys[api_key] = key_data
        return key_data

    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key."""
        key_data = self._api_keys.get(api_key)
        if not key_data:
            return None

        if key_data["status"] != "active":
            return None

        # Check expiration
        if key_data.get("expires_at"):
            expires_at = datetime.fromisoformat(key_data["expires_at"])
            if utc_now() > expires_at:
                return None

        # Update usage statistics
        key_data["last_used_at"] = utc_now_iso()
        key_data["usage_count"] += 1

        return key_data

    async def revoke_api_key(self, api_key: str) -> bool:
        """Revoke API key."""
        key_data = self._api_keys.get(api_key)
        if not key_data:
            return False

        key_data["status"] = "revoked"
        key_data["updated_at"] = utc_now_iso()
        return True

    async def generate_jwt_token(self, **kwargs) -> Dict[str, Any]:
        """Generate JWT token."""
        import jwt as pyjwt

        token_id = str(uuid4())

        payload = {
            "sub": kwargs.get("user_id"),
            "iss": kwargs.get("issuer", "dotmac-api-gateway"),
            "aud": kwargs.get("audience", ["api"]),
            "iat": int(time.time()),
            "exp": int(time.time()) + kwargs.get("expires_in", 3600),
            "jti": token_id,
            "tenant_id": kwargs.get("tenant_id"),
            "scopes": kwargs.get("scopes", []),
            "roles": kwargs.get("roles", []),
        }

        secret_key = kwargs.get("secret_key", "default-secret")
        algorithm = kwargs.get("algorithm", "HS256")

        token = pyjwt.encode(payload, secret_key, algorithm=algorithm)

        token_data = {
            "token_id": token_id,
            "token": token,
            "payload": payload,
            "created_at": utc_now_iso(),
            "expires_at": datetime.fromtimestamp(payload["exp"]).isoformat(),
        }

        self._jwt_tokens[token_id] = token_data
        return token_data

    async def validate_jwt_token(self, token: str, secret_key: str, algorithm: str = "HS256") -> Optional[Dict[str, Any]]:
        """Validate JWT token."""
        import jwt as pyjwt

        try:
            payload = pyjwt.decode(token, secret_key, algorithms=[algorithm])
            return payload
        except pyjwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except pyjwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")

    async def authenticate_request(self, headers: Dict[str, str], query_params: Dict[str, str], policy_id: str) -> Dict[str, Any]:
        """Authenticate request based on policy."""
        policy = await self.get_auth_policy(policy_id)
        if not policy:
            raise ConfigurationError(f"Auth policy not found: {policy_id}")

        auth_type = policy["auth_type"]

        if auth_type == "jwt":
            return await self._authenticate_jwt(headers, policy)
        elif auth_type == "api_key":
            return await self._authenticate_api_key(headers, query_params, policy)
        elif auth_type == "oauth2":
            return await self._authenticate_oauth2(headers, policy)
        else:
            raise ConfigurationError(f"Unsupported auth type: {auth_type}")

    async def _authenticate_jwt(self, headers: Dict[str, str], policy: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate JWT token."""
        auth_header = headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            raise AuthenticationError("Missing or invalid Authorization header")

        token = auth_header[7:]  # Remove 'Bearer ' prefix

        try:
            payload = await self.validate_jwt_token(
                token,
                policy["jwt_secret_key"],
                policy["jwt_algorithm"]
            )

            # Check required scopes
            required_scopes = policy.get("required_scopes", [])
            if required_scopes:
                token_scopes = payload.get("scopes", [])
                if not all(scope in token_scopes for scope in required_scopes):
                    raise AuthorizationError("Insufficient scopes")

            # Check required roles
            required_roles = policy.get("required_roles", [])
            if required_roles:
                token_roles = payload.get("roles", [])
                if not any(role in token_roles for role in required_roles):
                    raise AuthorizationError("Insufficient roles")

            return {
                "auth_type": "jwt",
                "user_id": payload.get("sub"),
                "tenant_id": payload.get("tenant_id"),
                "scopes": payload.get("scopes", []),
                "roles": payload.get("roles", []),
                "payload": payload,
            }

        except Exception as e:
            raise AuthenticationError(f"JWT validation failed: {str(e)}")

    async def _authenticate_api_key(self, headers: Dict[str, str], query_params: Dict[str, str], policy: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate API key."""
        api_key = None

        # Check header
        if policy.get("enable_bearer_token", True):
            header_name = policy.get("api_key_header", "X-API-Key")
            api_key = headers.get(header_name)

        # Check query parameter
        if not api_key and policy.get("enable_query_param", False):
            query_param = policy.get("api_key_query_param", "api_key")
            api_key = query_params.get(query_param)

        if not api_key:
            raise AuthenticationError("Missing API key")

        key_data = await self.validate_api_key(api_key)
        if not key_data:
            raise AuthenticationError("Invalid API key")

        # Check required scopes
        required_scopes = policy.get("required_scopes", [])
        if required_scopes:
            key_scopes = key_data.get("scopes", [])
            if not all(scope in key_scopes for scope in required_scopes):
                raise AuthorizationError("Insufficient scopes")

        return {
            "auth_type": "api_key",
            "key_id": key_data["key_id"],
            "user_id": key_data.get("user_id"),
            "tenant_id": key_data.get("tenant_id"),
            "scopes": key_data.get("scopes", []),
            "roles": key_data.get("roles", []),
            "key_data": key_data,
        }

    async def _authenticate_oauth2(self, headers: Dict[str, str], policy: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate OAuth2 token."""
        # OAuth2 implementation would integrate with external OAuth2 providers
        # This is a simplified version
        auth_header = headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            raise AuthenticationError("Missing or invalid Authorization header")

        token = auth_header[7:]

        # In a real implementation, this would validate the token with the OAuth2 provider
        # For now, return a mock successful authentication
        return {
            "auth_type": "oauth2",
            "user_id": "oauth2_user",
            "tenant_id": policy.get("tenant_id"),
            "scopes": ["read", "write"],
            "roles": ["user"],
            "token": token,
        }


class AuthenticationProxySDK:
    """SDK for API Gateway authentication and authorization."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = AuthenticationProxyService()

    async def create_auth_policy(
        self,
        name: str,
        auth_type: str,
        required_scopes: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create authentication policy."""
        return await self._service.create_auth_policy(
            name=name,
            auth_type=auth_type,
            required_scopes=required_scopes or [],
            **kwargs
        )

    async def get_auth_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get authentication policy by ID."""
        return await self._service.get_auth_policy(policy_id)

    async def update_auth_policy(self, policy_id: str, **updates) -> Dict[str, Any]:
        """Update authentication policy."""
        return await self._service.update_auth_policy(policy_id, **updates)

    async def delete_auth_policy(self, policy_id: str) -> bool:
        """Delete authentication policy."""
        return await self._service.delete_auth_policy(policy_id)

    async def create_jwt_auth_provider(
        self,
        name: str,
        secret_key: str,
        algorithm: str = "HS256",
        **kwargs
    ) -> Dict[str, Any]:
        """Create JWT authentication provider."""
        return await self._service.create_jwt_auth_provider(
            name=name,
            secret_key=secret_key,
            algorithm=algorithm,
            **kwargs
        )

    async def create_oauth2_auth_provider(
        self,
        name: str,
        client_id: str,
        client_secret: str,
        authorization_url: str,
        token_url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Create OAuth2 authentication provider."""
        return await self._service.create_oauth2_auth_provider(
            name=name,
            client_id=client_id,
            client_secret=client_secret,
            authorization_url=authorization_url,
            token_url=token_url,
            **kwargs
        )

    async def create_api_key_auth_provider(
        self,
        name: str,
        header_name: str = "X-API-Key",
        **kwargs
    ) -> Dict[str, Any]:
        """Create API key authentication provider."""
        return await self._service.create_api_key_auth_provider(
            name=name,
            header_name=header_name,
            **kwargs
        )

    async def generate_api_key(
        self,
        name: str,
        user_id: str = None,
        scopes: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate API key."""
        return await self._service.generate_api_key(
            name=name,
            user_id=user_id,
            tenant_id=self.tenant_id,
            scopes=scopes or [],
            **kwargs
        )

    async def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """Validate API key."""
        return await self._service.validate_api_key(api_key)

    async def revoke_api_key(self, api_key: str) -> bool:
        """Revoke API key."""
        return await self._service.revoke_api_key(api_key)

    async def generate_jwt_token(
        self,
        user_id: str,
        scopes: List[str] = None,
        roles: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate JWT token."""
        return await self._service.generate_jwt_token(
            user_id=user_id,
            tenant_id=self.tenant_id,
            scopes=scopes or [],
            roles=roles or [],
            **kwargs
        )

    async def validate_jwt_token(self, token: str, secret_key: str, algorithm: str = "HS256") -> Optional[Dict[str, Any]]:
        """Validate JWT token."""
        return await self._service.validate_jwt_token(token, secret_key, algorithm)

    async def authenticate_request(
        self,
        headers: Dict[str, str],
        query_params: Dict[str, str],
        policy_id: str
    ) -> Dict[str, Any]:
        """Authenticate request based on policy."""
        return await self._service.authenticate_request(headers, query_params, policy_id)
