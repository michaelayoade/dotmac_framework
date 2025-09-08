"""
Secrets policy and OpenBao/Vault client stubs for tests.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

import httpx


class Environment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class SecretType(str, Enum):
    JWT_SECRET = "jwt_secret"
    DATABASE_CREDENTIAL = "database_credential"
    API_KEY = "api_key"
    ENCRYPTION_KEY = "encryption_key"
    OAUTH_SECRET = "oauth_secret"
    WEBHOOK_SECRET = "webhook_secret"


class SecretsEnvironmentError(Exception):
    pass


class SecretsRetrievalError(Exception):
    pass


class SecretsValidationError(Exception):
    pass


@dataclass
class SecretPolicy:
    secret_type: SecretType
    requires_vault_in_production: bool = True
    allows_env_fallback_in_dev: bool = True
    min_rotation_days: int = 90
    max_age_days: int = 365
    encryption_required: bool = False


@dataclass
class SecretMetadata:
    secret_type: SecretType
    path: str
    version: int
    created_at: str | None = None
    last_accessed: str | None = None
    rotation_scheduled: bool = False


@dataclass
class SecretAuditLog:
    secret_type: SecretType
    action: str
    path: str
    tenant_id: Any | None
    environment: Environment
    success: bool
    error_message: str | None = None


class OpenBaoClient:
    def __init__(self, vault_url: str, token: str, *, timeout: int = 30, max_retries: int = 3):
        self.vault_url = vault_url
        self.token = token
        self.timeout = timeout
        self.max_retries = max_retries

    async def get_secret(self, path: str, key: str) -> str:
        headers = {"X-Vault-Token": self.token}
        url = f"{self.vault_url}/v1/{path}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(url, headers=headers)
            except Exception as e:
                raise SecretsRetrievalError("Failed to retrieve secret") from e
        if resp.status_code == 404:
            raise SecretsRetrievalError("Secret not found")
        if resp.status_code != 200:
            raise SecretsRetrievalError("Failed to retrieve secret")
        data = resp.json()
        return data.get("data", {}).get("data", {}).get(key)

    async def store_secret(self, path: str, key: str, value: str) -> None:
        headers = {"X-Vault-Token": self.token}
        url = f"{self.vault_url}/v1/{path}"
        payload = {"data": {key: value}}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            await client.post(url, headers=headers, json=payload)

    async def health_check(self) -> bool:
        url = f"{self.vault_url}/v1/sys/health"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            return False
        data = resp.json()
        return not data.get("sealed", False) and not data.get("standby", False)


class HardenedSecretsManager:
    def __init__(self, environment: Environment, vault_client: OpenBaoClient | None):
        self.environment = environment
        self.vault_client = vault_client
        if self.environment in (Environment.PRODUCTION, Environment.STAGING) and self.vault_client is None:
            raise SecretsEnvironmentError("OpenBao/Vault client required in production")

    async def get_secret(
        self,
        secret_type: SecretType,
        category: str,
        key: str,
        tenant_id: Any | None = None,
    ) -> str:
        if self.environment == Environment.DEVELOPMENT and self.vault_client is None:
            env_key = f"{category}_{key}".upper()
            value = os.environ.get(env_key)
            if not value:
                raise SecretsRetrievalError("Secret not found")
            return value
        if not self.vault_client:
            raise SecretsEnvironmentError("Vault client not configured")
        tenant_path = f"/{tenant_id}" if tenant_id is not None else ""
        path = f"secret/{category}{tenant_path}/{key}"
        return await self.vault_client.get_secret(path, key)

    async def store_secret(self, secret_type: SecretType, category: str, key: str, value: str) -> None:
        if self.environment != Environment.PRODUCTION:
            raise SecretsEnvironmentError("Secret storage not allowed")
        if not self.vault_client:
            raise SecretsEnvironmentError("Vault client not configured")
        path = f"secret/{category}/{key}"
        await self.vault_client.store_secret(path, key, value)

    async def rotate_secret(self, secret_type: SecretType, category: str, key: str) -> str:
        import secrets

        new_value = secrets.token_urlsafe(32)
        await self.store_secret(secret_type, category, key, new_value)
        return new_value

    def validate_secret_strength(self, value: str, secret_type: SecretType) -> None:
        if len(value) < 8 or value.isalpha() or value.isdigit():
            raise SecretsValidationError("Secret does not meet strength requirements")

    def get_secret_policies(self) -> dict[SecretType, SecretPolicy]:
        return {
            SecretType.JWT_SECRET: SecretPolicy(SecretType.JWT_SECRET),
            SecretType.DATABASE_CREDENTIAL: SecretPolicy(SecretType.DATABASE_CREDENTIAL),
        }

    async def health_check(self) -> bool:
        if self.vault_client:
            return await self.vault_client.health_check()
        return True

    async def _store_audit_log(self, log: SecretAuditLog) -> None:
        return None


__all__ = [
    "Environment",
    "SecretType",
    "SecretsEnvironmentError",
    "SecretsRetrievalError",
    "SecretsValidationError",
    "SecretPolicy",
    "SecretMetadata",
    "SecretAuditLog",
    "OpenBaoClient",
    "HardenedSecretsManager",
]
