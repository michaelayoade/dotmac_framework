"""
Infrastructure Layer Interfaces
Define contracts for all external integrations
"""

from .cache_provider import ICacheProvider
from .deployment_provider import IDeploymentProvider
from .dns_provider import IDNSProvider
from .storage_provider import IStorageProvider

__all__ = ["IDeploymentProvider", "IDNSProvider", "ICacheProvider", "IStorageProvider"]
