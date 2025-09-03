"""
Infrastructure Layer
External integrations and adapters
"""

from .factories.adapter_factory import AdapterFactory, get_adapter_factory, AdapterConfig
from .interfaces.deployment_provider import IDeploymentProvider, ApplicationConfig, ServiceConfig, DeploymentResult
from .interfaces.dns_provider import IDNSProvider, DNSValidationResult, SSLCertificateInfo, DNSRecord
from .interfaces.cache_provider import ICacheProvider, CacheConfig, CacheConnectionInfo
from .interfaces.storage_provider import IStorageProvider, StorageConfig, FileMetadata, StorageType

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