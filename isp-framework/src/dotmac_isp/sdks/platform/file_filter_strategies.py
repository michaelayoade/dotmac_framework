"""
File storage filter strategies using Strategy pattern.
Replaces the 19-complexity _matches_filters method with focused filter strategies.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class FileMetadata:
    """File metadata for type hints."""
    tenant_id: str
    bucket: str
    key: str
    content_type: str
    owner_id: str
    created_at: datetime
    size_bytes: int
    tags: Dict[str, str]


@dataclass  
class FileListRequest:
    """File list request for type hints."""
    bucket: Optional[str] = None
    prefix: Optional[str] = None
    content_type: Optional[str] = None
    owner_id: Optional[str] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    min_size_bytes: Optional[int] = None
    max_size_bytes: Optional[int] = None
    tags: Dict[str, str] = None


class FileFilterStrategy(ABC):
    """Base strategy for file metadata filtering."""
    
    @abstractmethod
    def matches(self, metadata: FileMetadata, request: FileListRequest) -> bool:
        """Check if file metadata matches this filter criteria."""
        pass


class BucketFilterStrategy(FileFilterStrategy):
    """Filter files by bucket name."""
    
    def matches(self, metadata: FileMetadata, request: FileListRequest) -> bool:
        """Check if file bucket matches request bucket."""
        if request.bucket is None:
            return True
        return metadata.bucket == request.bucket


class PrefixFilterStrategy(FileFilterStrategy):
    """Filter files by key prefix."""
    
    def matches(self, metadata: FileMetadata, request: FileListRequest) -> bool:
        """Check if file key starts with requested prefix."""
        if request.prefix is None:
            return True
        return metadata.key.startswith(request.prefix)


class ContentTypeFilterStrategy(FileFilterStrategy):
    """Filter files by content type."""
    
    def matches(self, metadata: FileMetadata, request: FileListRequest) -> bool:
        """Check if file content type matches request."""
        if request.content_type is None:
            return True
        return metadata.content_type == request.content_type


class OwnerFilterStrategy(FileFilterStrategy):
    """Filter files by owner ID."""
    
    def matches(self, metadata: FileMetadata, request: FileListRequest) -> bool:
        """Check if file owner matches request."""
        if request.owner_id is None:
            return True
        return metadata.owner_id == request.owner_id


class CreationDateFilterStrategy(FileFilterStrategy):
    """Filter files by creation date range."""
    
    def matches(self, metadata: FileMetadata, request: FileListRequest) -> bool:
        """Check if file creation date is within requested range."""
        # Check after date
        if request.created_after and metadata.created_at < request.created_after:
            return False
        
        # Check before date  
        if request.created_before and metadata.created_at > request.created_before:
            return False
        
        return True


class FileSizeFilterStrategy(FileFilterStrategy):
    """Filter files by size range."""
    
    def matches(self, metadata: FileMetadata, request: FileListRequest) -> bool:
        """Check if file size is within requested range."""
        # Check minimum size
        if request.min_size_bytes and metadata.size_bytes < request.min_size_bytes:
            return False
        
        # Check maximum size
        if request.max_size_bytes and metadata.size_bytes > request.max_size_bytes:
            return False
        
        return True


class TagsFilterStrategy(FileFilterStrategy):
    """Filter files by tags."""
    
    def matches(self, metadata: FileMetadata, request: FileListRequest) -> bool:
        """Check if file tags match all requested tags."""
        if not request.tags:
            return True
        
        if not metadata.tags:
            return False
        
        # All requested tags must match
        for key, value in request.tags.items():
            if metadata.tags.get(key) != value:
                return False
        
        return True


class FileFilterMatcher:
    """
    File filter matcher using Strategy pattern.
    
    REFACTORED: Replaces 19-complexity _matches_filters method with 
    focused, testable filter strategies (Complexity: 3).
    """
    
    def __init__(self):
        """Initialize with default filter strategies."""
        self.strategies = [
            BucketFilterStrategy(),
            PrefixFilterStrategy(),
            ContentTypeFilterStrategy(),
            OwnerFilterStrategy(),
            CreationDateFilterStrategy(),
            FileSizeFilterStrategy(),
            TagsFilterStrategy(),
        ]
    
    def matches_filters(self, metadata: FileMetadata, request: FileListRequest) -> bool:
        """
        Check if file metadata matches request filters using all strategies.
        
        COMPLEXITY REDUCTION: This method replaces the original 19-complexity 
        method with a simple iteration over strategies (Complexity: 2).
        
        Args:
            metadata: File metadata to check
            request: Request with filter criteria
            
        Returns:
            True if file matches all filter criteria
        """
        # Step 1: Apply all filter strategies (Complexity: 1)
        for strategy in self.strategies:
            if not strategy.matches(metadata, request):
                return False
        
        # Step 2: Return match result (Complexity: 1) 
        return True
    
    def add_filter_strategy(self, strategy: FileFilterStrategy) -> None:
        """Add a custom filter strategy."""
        self.strategies.append(strategy)
    
    def remove_filter_strategy(self, strategy_class: type) -> bool:
        """Remove a filter strategy by class type."""
        original_count = len(self.strategies)
        self.strategies = [s for s in self.strategies if not isinstance(s, strategy_class)]
        return len(self.strategies) < original_count
    
    def get_active_strategies(self) -> list[str]:
        """Get list of active filter strategy names."""
        return [strategy.__class__.__name__ for strategy in self.strategies]


class AdvancedFileFilterMatcher(FileFilterMatcher):
    """
    Advanced file filter matcher with additional filtering capabilities.
    Extends the basic matcher with more sophisticated filters.
    """
    
    def __init__(self):
        """Initialize with advanced filter strategies."""
        super().__init__()
        
        # Add advanced strategies
        self.strategies.extend([
            FileExtensionFilterStrategy(),
            FileNamePatternStrategy(),
            ModificationDateStrategy(),
        ])


class FileExtensionFilterStrategy(FileFilterStrategy):
    """Filter files by file extension."""
    
    def matches(self, metadata: FileMetadata, request: FileListRequest) -> bool:
        """Check if file extension matches requested extensions."""
        # This would require extension to FileListRequest, but shows extensibility
        extensions = getattr(request, 'allowed_extensions', None)
        if not extensions:
            return True
        
        # Extract extension from key
        file_extension = metadata.key.split('.')[-1].lower() if '.' in metadata.key else ''
        return file_extension in [ext.lower() for ext in extensions]


class FileNamePatternStrategy(FileFilterStrategy):
    """Filter files by filename pattern matching."""
    
    def matches(self, metadata: FileMetadata, request: FileListRequest) -> bool:
        """Check if filename matches pattern."""
        import re
        
        pattern = getattr(request, 'filename_pattern', None)
        if not pattern:
            return True
        
        # Extract filename from key
        filename = metadata.key.split('/')[-1]
        
        try:
            return bool(re.search(pattern, filename, re.IGNORECASE))
        except re.error:
            # Invalid regex pattern - don't filter
            return True


class ModificationDateStrategy(FileFilterStrategy):
    """Filter files by modification date (if available in metadata)."""
    
    def matches(self, metadata: FileMetadata, request: FileListRequest) -> bool:
        """Check if file modification date matches criteria."""
        modified_after = getattr(request, 'modified_after', None)
        modified_before = getattr(request, 'modified_before', None)
        modified_at = getattr(metadata, 'modified_at', None)
        
        if not modified_at:
            return True  # No modification date to filter on
        
        # Check after date
        if modified_after and modified_at < modified_after:
            return False
        
        # Check before date  
        if modified_before and modified_at > modified_before:
            return False
        
        return True


def create_file_filter_matcher() -> FileFilterMatcher:
    """
    Factory function to create a configured file filter matcher.
    
    This is the main entry point for replacing the 19-complexity method.
    """
    return FileFilterMatcher()


def create_advanced_file_filter_matcher() -> AdvancedFileFilterMatcher:
    """
    Factory function to create an advanced file filter matcher.
    
    Use this for more sophisticated file filtering scenarios.
    """
    return AdvancedFileFilterMatcher()