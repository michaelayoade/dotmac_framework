"""
Infrastructure Layer
External integrations and adapters
"""

from .factories.adapter_factory import AdapterConfig, AdapterFactory, get_adapter_factory
from .interfaces.cache_provider import CacheConfig, CacheConnectionInfo, ICacheProvider
from .interfaces.deployment_provider import ApplicationConfig, DeploymentResult, IDeploymentProvider, ServiceConfig
from .interfaces.dns_provider import DNSRecord, DNSValidationResult, IDNSProvider, SSLCertificateInfo
from .interfaces.storage_provider import FileMetadata, IStorageProvider, StorageConfig, StorageType

__all__ = [
    # Factory
    "AdapterFactory",
    "get_adapter_factory",
    "AdapterConfig",
    # Interfaces
    "IDeploymentProvider",
    "IDNSProvider",
    "ICacheProvider",
    "IStorageProvider",
    # Data Classes
    "ApplicationConfig",
    "ServiceConfig",
    "DeploymentResult",
    "DNSValidationResult",
    "SSLCertificateInfo",
    "DNSRecord",
    "CacheConfig",
    "CacheConnectionInfo",
    "StorageConfig",
    "FileMetadata",
    "StorageType",
]
