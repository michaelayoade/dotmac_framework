"""
Storage Provider Interface
Abstract interface for storage providers (file systems, object storage, etc.)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, BinaryIO, Optional


class StorageType(str, Enum):
    """Storage service types"""

    FILE_SYSTEM = "filesystem"
    OBJECT_STORAGE = "object_storage"
    BLOCK_STORAGE = "block_storage"


@dataclass
class StorageConfig:
    """Storage service configuration"""

    name: str
    storage_type: StorageType
    size: str = "10GB"
    backup_enabled: bool = True
    encryption: bool = True
    access_mode: str = "ReadWriteOnce"
    configuration: dict[str, Any] = None

    def __post_init__(self):
        if self.configuration is None:
            self.configuration = {}


@dataclass
class FileMetadata:
    """File metadata information"""

    filename: str
    size: int
    content_type: str = ""
    last_modified: Optional[str] = None
    checksum: Optional[str] = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class IStorageProvider(ABC):
    """
    Abstract interface for storage providers.
    Handles file storage, object storage, and persistent volumes.
    """

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the storage provider"""
        pass

    @abstractmethod
    async def health_check(self) -> dict[str, Any]:
        """Check provider health"""
        pass

    @abstractmethod
    async def create_storage(self, config: StorageConfig) -> dict[str, Any]:
        """Create a new storage service"""
        pass

    @abstractmethod
    async def get_storage_info(self, storage_name: str) -> dict[str, Any]:
        """Get storage service information"""
        pass

    @abstractmethod
    async def get_storage_usage(self, storage_name: str) -> dict[str, Any]:
        """Get storage usage statistics"""
        pass

    # File operations

    @abstractmethod
    async def upload_file(
        self, storage_name: str, file_path: str, content: BinaryIO
    ) -> FileMetadata:
        """Upload file to storage"""
        pass

    @abstractmethod
    async def download_file(self, storage_name: str, file_path: str) -> BinaryIO:
        """Download file from storage"""
        pass

    @abstractmethod
    async def delete_file(self, storage_name: str, file_path: str) -> bool:
        """Delete file from storage"""
        pass

    @abstractmethod
    async def list_files(
        self, storage_name: str, prefix: str = ""
    ) -> list[FileMetadata]:
        """List files in storage"""
        pass

    @abstractmethod
    async def file_exists(self, storage_name: str, file_path: str) -> bool:
        """Check if file exists"""
        pass

    @abstractmethod
    async def get_file_metadata(
        self, storage_name: str, file_path: str
    ) -> FileMetadata:
        """Get file metadata"""
        pass

    # Backup and recovery

    @abstractmethod
    async def create_backup(self, storage_name: str) -> dict[str, Any]:
        """Create storage backup"""
        pass

    @abstractmethod
    async def restore_backup(self, storage_name: str, backup_id: str) -> bool:
        """Restore from backup"""
        pass

    @abstractmethod
    async def list_backups(self, storage_name: str) -> list[dict[str, Any]]:
        """List available backups"""
        pass

    # Storage management

    @abstractmethod
    async def resize_storage(self, storage_name: str, new_size: str) -> bool:
        """Resize storage capacity"""
        pass

    @abstractmethod
    async def remove_storage(self, storage_name: str) -> bool:
        """Remove storage service"""
        pass

    @abstractmethod
    def get_supported_storage_types(self) -> list[StorageType]:
        """Get supported storage types"""
        pass

    @abstractmethod
    async def cleanup(self) -> bool:
        """Cleanup provider resources"""
        pass
