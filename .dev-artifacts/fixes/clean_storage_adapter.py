"""
Clean Storage Adapter - DRY Migration
Production-ready storage adapter using standardized patterns.
"""

from typing import Any, Dict, Optional, Protocol
from abc import ABC, abstractmethod


class StorageProvider(Protocol):
    """Protocol for storage providers."""
    
    async def upload(self, key: str, data: bytes, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Upload data to storage."""
        ...
        
    async def download(self, key: str) -> bytes:
        """Download data from storage."""
        ...
        
    async def delete(self, key: str) -> bool:
        """Delete data from storage."""
        ...
        
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...


class BaseStorageAdapter(ABC):
    """Base storage adapter with common functionality."""
    
    def __init__(self, provider: StorageProvider):
        self.provider = provider
        
    @abstractmethod
    async def process_upload(self, key: str, data: bytes, **kwargs) -> Dict[str, Any]:
        """Process file upload with adapter-specific logic."""
        pass
        
    @abstractmethod
    async def process_download(self, key: str, **kwargs) -> bytes:
        """Process file download with adapter-specific logic.""" 
        pass


class LocalStorageAdapter(BaseStorageAdapter):
    """Local file system storage adapter."""
    
    async def process_upload(self, key: str, data: bytes, **kwargs) -> Dict[str, Any]:
        """Process upload to local storage."""
        url = await self.provider.upload(key, data, kwargs.get("metadata"))
        
        return {
            "key": key,
            "url": url,
            "size": len(data),
            "provider": "local",
            "uploaded_at": "2025-01-15T10:30:00Z",
        }
        
    async def process_download(self, key: str, **kwargs) -> bytes:
        """Process download from local storage."""
        return await self.provider.download(key)


class S3StorageAdapter(BaseStorageAdapter):
    """AWS S3 storage adapter."""
    
    async def process_upload(self, key: str, data: bytes, **kwargs) -> Dict[str, Any]:
        """Process upload to S3."""
        url = await self.provider.upload(key, data, kwargs.get("metadata"))
        
        return {
            "key": key,
            "url": url,
            "size": len(data),
            "provider": "s3",
            "bucket": kwargs.get("bucket", "default"),
            "uploaded_at": "2025-01-15T10:30:00Z",
        }
        
    async def process_download(self, key: str, **kwargs) -> bytes:
        """Process download from S3."""
        return await self.provider.download(key)


class StorageManager:
    """Manages multiple storage adapters."""
    
    def __init__(self):
        self.adapters: Dict[str, BaseStorageAdapter] = {}
        
    def register_adapter(self, name: str, adapter: BaseStorageAdapter):
        """Register a storage adapter."""
        self.adapters[name] = adapter
        
    def get_adapter(self, name: str) -> Optional[BaseStorageAdapter]:
        """Get a storage adapter by name."""
        return self.adapters.get(name)
        
    async def upload(self, adapter_name: str, key: str, data: bytes, **kwargs) -> Dict[str, Any]:
        """Upload using specified adapter."""
        adapter = self.get_adapter(adapter_name)
        if not adapter:
            raise ValueError(f"Unknown storage adapter: {adapter_name}")
            
        return await adapter.process_upload(key, data, **kwargs)
        
    async def download(self, adapter_name: str, key: str, **kwargs) -> bytes:
        """Download using specified adapter."""
        adapter = self.get_adapter(adapter_name)
        if not adapter:
            raise ValueError(f"Unknown storage adapter: {adapter_name}")
            
        return await adapter.process_download(key, **kwargs)


# Global storage manager instance
_storage_manager: Optional[StorageManager] = None


def get_storage_manager() -> StorageManager:
    """Get global storage manager instance."""
    global _storage_manager
    if _storage_manager is None:
        _storage_manager = StorageManager()
    return _storage_manager


# Export the storage classes
__all__ = [
    "StorageProvider",
    "BaseStorageAdapter", 
    "LocalStorageAdapter",
    "S3StorageAdapter",
    "StorageManager",
    "get_storage_manager",
]