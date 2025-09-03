"""
Interfaces and abstract base classes for secrets management
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from .types import SecretData, SecretKind, SecretMetadata, SecretValue


class SecretsProviderError(Exception):
    """Base exception for secrets provider errors"""
    pass


class SecretNotFoundError(SecretsProviderError):
    """Secret not found in provider"""
    pass


class SecretValidationError(SecretsProviderError):
    """Secret validation failed"""
    pass


class ProviderConnectionError(SecretsProviderError):
    """Failed to connect to secrets provider"""
    pass


class ProviderAuthenticationError(SecretsProviderError):
    """Authentication failed with secrets provider"""
    pass


class ProviderAuthorizationError(SecretsProviderError):
    """Authorization failed with secrets provider"""
    pass


class SecretExpiredError(SecretsProviderError):
    """Secret has expired"""
    pass


@runtime_checkable
class SecretsProvider(Protocol):
    """Interface for secrets providers"""
    
    async def get_secret(self, path: str) -> SecretData:
        """
        Retrieve a secret from the provider
        
        Args:
            path: Secret path/identifier
            
        Returns:
            Secret data as dictionary
            
        Raises:
            SecretNotFoundError: If secret doesn't exist
            ProviderConnectionError: If provider is unreachable
            ProviderAuthenticationError: If authentication fails
            ProviderAuthorizationError: If access is denied
        """
        ...
    
    async def list_secrets(self, path_prefix: str = "") -> List[str]:
        """
        List available secrets with optional path prefix filter
        
        Args:
            path_prefix: Optional path prefix to filter results
            
        Returns:
            List of secret paths
        """
        ...
    
    async def health_check(self) -> bool:
        """
        Check if provider is healthy and accessible
        
        Returns:
            True if healthy, False otherwise
        """
        ...


@runtime_checkable
class WritableSecretsProvider(SecretsProvider, Protocol):
    """Interface for providers that support writing secrets"""
    
    async def put_secret(self, path: str, data: SecretData) -> bool:
        """
        Store a secret in the provider
        
        Args:
            path: Secret path/identifier
            data: Secret data to store
            
        Returns:
            True if successful
            
        Raises:
            ProviderConnectionError: If provider is unreachable
            ProviderAuthenticationError: If authentication fails
            ProviderAuthorizationError: If access is denied
        """
        ...
    
    async def delete_secret(self, path: str) -> bool:
        """
        Delete a secret from the provider
        
        Args:
            path: Secret path/identifier
            
        Returns:
            True if successful or secret didn't exist
            
        Raises:
            ProviderConnectionError: If provider is unreachable
            ProviderAuthenticationError: If authentication fails
            ProviderAuthorizationError: If access is denied
        """
        ...


@runtime_checkable
class SecretValidator(Protocol):
    """Interface for secret validators"""
    
    def validate(self, secret_data: SecretData, kind: SecretKind) -> bool:
        """
        Validate secret data according to policy
        
        Args:
            secret_data: Secret data to validate
            kind: Type of secret being validated
            
        Returns:
            True if valid
            
        Raises:
            SecretValidationError: If validation fails
        """
        ...
    
    def get_validation_errors(self, secret_data: SecretData, kind: SecretKind) -> List[str]:
        """
        Get detailed validation errors
        
        Args:
            secret_data: Secret data to validate
            kind: Type of secret being validated
            
        Returns:
            List of validation error messages
        """
        ...


@runtime_checkable
class SecretCache(Protocol):
    """Interface for secret caching"""
    
    async def get(self, key: str) -> Optional[SecretValue]:
        """Get cached secret value"""
        ...
    
    async def set(self, key: str, value: SecretValue, ttl: int) -> bool:
        """Set cached secret value with TTL in seconds"""
        ...
    
    async def delete(self, key: str) -> bool:
        """Delete cached secret"""
        ...
    
    async def clear(self) -> bool:
        """Clear all cached secrets"""
        ...
    
    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        ...


@runtime_checkable
class KeyRotationPolicy(Protocol):
    """Interface for key rotation policies"""
    
    def should_rotate(self, metadata: SecretMetadata) -> bool:
        """
        Determine if a secret should be rotated
        
        Args:
            metadata: Secret metadata including creation/update dates
            
        Returns:
            True if secret should be rotated
        """
        ...
    
    def get_rotation_schedule(self, metadata: SecretMetadata) -> Optional[str]:
        """
        Get next rotation time as ISO string
        
        Args:
            metadata: Secret metadata
            
        Returns:
            ISO datetime string for next rotation, or None if no rotation needed
        """
        ...
    
    def get_warning_threshold(self) -> int:
        """
        Get warning threshold in days before rotation needed
        
        Returns:
            Number of days before rotation to start warning
        """
        ...


@runtime_checkable
class ObservabilityHook(Protocol):
    """Interface for observability hooks"""
    
    def record_secret_fetch(
        self, 
        kind: SecretKind, 
        source: str, 
        success: bool, 
        latency_ms: float,
        path: str = ""
    ) -> None:
        """Record secret fetch metrics"""
        ...
    
    def record_validation_failure(
        self, 
        kind: SecretKind, 
        reason: str, 
        path: str = ""
    ) -> None:
        """Record validation failure"""
        ...
    
    def record_cache_hit(self, path: str) -> None:
        """Record cache hit"""
        ...
    
    def record_cache_miss(self, path: str) -> None:
        """Record cache miss"""
        ...
    
    def record_provider_error(
        self, 
        provider_type: str, 
        error_type: str, 
        path: str = ""
    ) -> None:
        """Record provider error"""
        ...


class BaseSecretsProvider(ABC):
    """Base class for secrets providers with common functionality"""
    
    def __init__(self, timeout: int = 30, retry_attempts: int = 3) -> None:
        self.timeout = timeout
        self.retry_attempts = retry_attempts
        self._healthy = False
    
    @abstractmethod
    async def get_secret(self, path: str) -> SecretData:
        """Retrieve a secret from the provider"""
        pass
    
    async def list_secrets(self, path_prefix: str = "") -> List[str]:
        """Default implementation returns empty list"""
        return []
    
    async def health_check(self) -> bool:
        """Default health check implementation"""
        try:
            # Attempt to list secrets as a basic health check
            await self.list_secrets()
            self._healthy = True
            return True
        except Exception:
            self._healthy = False
            return False
    
    @property
    def is_healthy(self) -> bool:
        """Check if provider is currently healthy"""
        return self._healthy
    
    def _normalize_path(self, path: str) -> str:
        """Normalize secret path"""
        return path.strip().strip('/').replace('\\', '/')
    
    def _extract_secret_data(self, raw_data: Dict[str, Any]) -> SecretData:
        """Extract secret data from provider response"""
        # Handle different provider response formats
        if 'data' in raw_data and isinstance(raw_data['data'], dict):
            return raw_data['data']
        return raw_data


class BaseValidator(ABC):
    """Base class for secret validators"""
    
    def __init__(self) -> None:
        self.errors: List[str] = []
    
    @abstractmethod
    def validate(self, secret_data: SecretData, kind: SecretKind) -> bool:
        """Validate secret data"""
        pass
    
    def get_validation_errors(self, secret_data: SecretData, kind: SecretKind) -> List[str]:
        """Get validation errors after calling validate()"""
        return self.errors.copy()
    
    def _add_error(self, message: str) -> None:
        """Add validation error"""
        self.errors.append(message)
    
    def _clear_errors(self) -> None:
        """Clear validation errors"""
        self.errors.clear()


# Exception hierarchy for better error handling
class SecretsManagerError(Exception):
    """Base exception for SecretsManager"""
    pass


class ConfigurationError(SecretsManagerError):
    """Configuration error"""
    pass


class ProviderNotAvailableError(SecretsManagerError):
    """No suitable provider available"""
    pass