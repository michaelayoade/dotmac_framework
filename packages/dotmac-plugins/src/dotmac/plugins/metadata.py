"""
Plugin metadata and version management system.

Provides comprehensive metadata structures for plugins including versioning,
author information, capabilities, and permission requirements.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from .types import PluginKind, PluginCapabilities


@dataclass(frozen=True)
class Version:
    """
    Semantic version representation with comparison support.
    
    Implements semantic versioning (semver) parsing and comparison
    for plugin version management and compatibility checking.
    """
    
    major: int
    minor: int
    patch: int
    pre_release: Optional[str] = None
    build_metadata: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate version components."""
        if self.major < 0 or self.minor < 0 or self.patch < 0:
            raise ValueError("Version components must be non-negative")
    
    @classmethod
    def parse(cls, version_string: str) -> "Version":
        """
        Parse version string into Version object.
        
        Supports semver format: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
        
        Args:
            version_string: Version string to parse
            
        Returns:
            Parsed Version object
            
        Raises:
            ValueError: If version string is invalid
        """
        # Semver regex pattern
        pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z\-\.]+))?(?:\+([0-9A-Za-z\-\.]+))?$'
        match = re.match(pattern, version_string.strip())
        
        if not match:
            raise ValueError(f"Invalid version string: {version_string}")
        
        major, minor, patch, pre_release, build_metadata = match.groups()
        
        return cls(
            major=int(major),
            minor=int(minor),
            patch=int(patch),
            pre_release=pre_release,
            build_metadata=build_metadata
        )
    
    def __str__(self) -> str:
        """String representation of version."""
        version_str = f"{self.major}.{self.minor}.{self.patch}"
        
        if self.pre_release:
            version_str += f"-{self.pre_release}"
        
        if self.build_metadata:
            version_str += f"+{self.build_metadata}"
        
        return version_str
    
    def __lt__(self, other: "Version") -> bool:
        """Less than comparison for version ordering."""
        if not isinstance(other, Version):
            return NotImplemented
        
        # Compare major.minor.patch
        self_core = (self.major, self.minor, self.patch)
        other_core = (other.major, other.minor, other.patch)
        
        if self_core != other_core:
            return self_core < other_core
        
        # Handle pre-release versions
        if self.pre_release is None and other.pre_release is None:
            return False
        elif self.pre_release is None:
            return False  # Release > pre-release
        elif other.pre_release is None:
            return True   # Pre-release < release
        else:
            return self.pre_release < other.pre_release
    
    def __le__(self, other: "Version") -> bool:
        """Less than or equal comparison."""
        return self < other or self == other
    
    def __gt__(self, other: "Version") -> bool:
        """Greater than comparison."""
        return not (self <= other)
    
    def __ge__(self, other: "Version") -> bool:
        """Greater than or equal comparison."""
        return not (self < other)
    
    def is_compatible(self, other: "Version") -> bool:
        """
        Check if versions are compatible (same major version).
        
        Args:
            other: Version to compare with
            
        Returns:
            True if versions are compatible
        """
        return self.major == other.major
    
    def is_prerelease(self) -> bool:
        """Check if this is a pre-release version."""
        return self.pre_release is not None


@dataclass(frozen=True)
class Author:
    """
    Plugin author information.
    
    Contains contact and identification information for plugin authors
    including validation of email and URL formats.
    """
    
    name: str
    email: Optional[str] = None
    url: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Validate author information."""
        if not self.name.strip():
            raise ValueError("Author name cannot be empty")
        
        if self.email and not self._is_valid_email(self.email):
            raise ValueError(f"Invalid email format: {self.email}")
        
        if self.url and not self._is_valid_url(self.url):
            raise ValueError(f"Invalid URL format: {self.url}")
    
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation."""
        try:
            result = urlparse(url)
            return bool(result.scheme and result.netloc)
        except Exception:
            return False
    
    def __str__(self) -> str:
        """String representation of author."""
        parts = [self.name]
        if self.email:
            parts.append(f"<{self.email}>")
        if self.url:
            parts.append(f"({self.url})")
        return " ".join(parts)


@dataclass
class PluginMetadata:
    """
    Comprehensive plugin metadata.
    
    Contains all metadata information for a plugin including identification,
    capabilities, permissions, and author information.
    """
    
    name: str
    version: Union[str, Version]
    kind: PluginKind
    author: Union[str, Author]
    description: str = ""
    homepage: Optional[str] = None
    repository: Optional[str] = None
    license: Optional[str] = None
    capabilities: PluginCapabilities = field(default_factory=dict)
    permissions_required: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    api_version: Optional[str] = None
    min_host_version: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    category: Optional[str] = None
    
    def __post_init__(self) -> None:
        """Post-initialization validation and normalization."""
        # Validate and normalize name
        if not self.name or not self.name.strip():
            raise ValueError("Plugin name cannot be empty")
        
        if not self._is_valid_plugin_name(self.name):
            raise ValueError(
                f"Invalid plugin name '{self.name}'. "
                "Names must contain only letters, numbers, hyphens, and underscores"
            )
        
        # Normalize version
        if isinstance(self.version, str):
            self.version = Version.parse(self.version)
        
        # Normalize author
        if isinstance(self.author, str):
            self.author = Author(name=self.author)
        
        # Validate URLs
        if self.homepage and not self._is_valid_url(self.homepage):
            raise ValueError(f"Invalid homepage URL: {self.homepage}")
        
        if self.repository and not self._is_valid_url(self.repository):
            raise ValueError(f"Invalid repository URL: {self.repository}")
        
        # Validate permissions
        self.permissions_required = [p.strip() for p in self.permissions_required if p.strip()]
        
        # Validate keywords
        self.keywords = [k.strip().lower() for k in self.keywords if k.strip()]
        
        # Set default API version if not specified
        if self.api_version is None:
            self.api_version = "1.0.0"
    
    def _is_valid_plugin_name(self, name: str) -> bool:
        """Validate plugin name format."""
        pattern = r'^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$|^[a-zA-Z0-9]$'
        return bool(re.match(pattern, name))
    
    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation."""
        try:
            result = urlparse(url)
            return bool(result.scheme and result.netloc)
        except Exception:
            return False
    
    def get_version(self) -> Version:
        """Get version as Version object."""
        return self.version
    
    def get_author(self) -> Author:
        """Get author as Author object."""
        return self.author
    
    def has_permission(self, permission: str) -> bool:
        """Check if plugin requires specific permission."""
        return permission in self.permissions_required
    
    def add_permission(self, permission: str) -> None:
        """Add required permission."""
        if permission and permission not in self.permissions_required:
            self.permissions_required.append(permission)
    
    def remove_permission(self, permission: str) -> None:
        """Remove required permission."""
        if permission in self.permissions_required:
            self.permissions_required.remove(permission)
    
    def has_capability(self, capability: str) -> bool:
        """Check if plugin has specific capability."""
        return capability in self.capabilities
    
    def get_capability(self, capability: str) -> Any:
        """Get capability value."""
        return self.capabilities.get(capability)
    
    def set_capability(self, capability: str, value: Any) -> None:
        """Set capability value."""
        self.capabilities[capability] = value
    
    def is_compatible_with(self, other: "PluginMetadata") -> bool:
        """
        Check if this plugin is compatible with another.
        
        Args:
            other: Other plugin metadata to check compatibility with
            
        Returns:
            True if plugins are compatible
        """
        # Same plugin name means incompatible (duplicate)
        if self.name == other.name:
            return False
        
        # Check API version compatibility
        if self.api_version and other.api_version:
            try:
                self_api = Version.parse(self.api_version)
                other_api = Version.parse(other.api_version)
                return self_api.is_compatible(other_api)
            except ValueError:
                # If version parsing fails, assume compatible
                pass
        
        return True
    
    def validate(self) -> List[str]:
        """
        Validate metadata completeness and consistency.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Check required fields
        if not self.description:
            errors.append("Description is required")
        
        # Check version format
        try:
            if isinstance(self.version, str):
                Version.parse(self.version)
        except ValueError as e:
            errors.append(f"Invalid version: {e}")
        
        # Check permissions format
        invalid_permissions = [
            p for p in self.permissions_required 
            if not isinstance(p, str) or not p.strip()
        ]
        if invalid_permissions:
            errors.append(f"Invalid permissions: {invalid_permissions}")
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary representation."""
        return {
            "name": self.name,
            "version": str(self.version),
            "kind": self.kind.value,
            "author": str(self.author),
            "description": self.description,
            "homepage": self.homepage,
            "repository": self.repository,
            "license": self.license,
            "capabilities": self.capabilities.copy(),
            "permissions_required": self.permissions_required.copy(),
            "dependencies": self.dependencies.copy(),
            "api_version": self.api_version,
            "min_host_version": self.min_host_version,
            "keywords": self.keywords.copy(),
            "category": self.category,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginMetadata":
        """Create metadata from dictionary representation."""
        # Handle kind conversion
        kind_value = data.get("kind", "custom")
        if isinstance(kind_value, str):
            try:
                kind = PluginKind(kind_value)
            except ValueError:
                kind = PluginKind.CUSTOM
        else:
            kind = kind_value
        
        return cls(
            name=data.get("name", ""),
            version=data.get("version", "0.0.0"),
            kind=kind,
            author=data.get("author", "Unknown"),
            description=data.get("description", ""),
            homepage=data.get("homepage"),
            repository=data.get("repository"),
            license=data.get("license"),
            capabilities=data.get("capabilities", {}),
            permissions_required=data.get("permissions_required", []),
            dependencies=data.get("dependencies", []),
            api_version=data.get("api_version"),
            min_host_version=data.get("min_host_version"),
            keywords=data.get("keywords", []),
            category=data.get("category"),
        )