"""
Profile-related models for SDKs.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from dataclasses import dataclass


class ProfileVisibility(str, Enum):
    """Profile visibility enumeration."""
    
    PUBLIC = "public"
    PRIVATE = "private"
    FRIENDS = "friends"
    ORGANIZATION = "organization"


class ProfileStatus(str, Enum):
    """Profile status enumeration."""
    
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"
    ARCHIVED = "archived"


@dataclass
class UserProfile:
    """User profile model."""
    
    id: UUID
    user_id: UUID
    display_name: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    bio: Optional[str]
    avatar_url: Optional[str]
    timezone: str
    language: str
    visibility: ProfileVisibility
    status: ProfileStatus
    preferences: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
    last_active_at: Optional[datetime] = None
    
    def __init__(self, **kwargs):
        """  Init   operation."""
        self.id = kwargs.get('id', uuid4())
        self.user_id = kwargs.get('user_id')
        self.display_name = kwargs.get('display_name')
        self.first_name = kwargs.get('first_name')
        self.last_name = kwargs.get('last_name')
        self.bio = kwargs.get('bio')
        self.avatar_url = kwargs.get('avatar_url')
        self.timezone = kwargs.get('timezone', 'UTC')
        self.language = kwargs.get('language', 'en')
        self.visibility = kwargs.get('visibility', ProfileVisibility.PRIVATE)
        self.status = kwargs.get('status', ProfileStatus.ACTIVE)
        self.preferences = kwargs.get('preferences') or {}
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.updated_at = kwargs.get('updated_at', datetime.utcnow())
        self.last_active_at = kwargs.get('last_active_at')
    
    def get_full_name(self) -> str:
        """Get full name from first and last name."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.display_name or "Unknown User"
    
    def is_active(self) -> bool:
        """Check if profile is active."""
        return self.status == ProfileStatus.ACTIVE
    
    def is_public(self) -> bool:
        """Check if profile is public."""
        return self.visibility == ProfileVisibility.PUBLIC
    
    def update_last_active(self) -> None:
        """Update last active timestamp."""
        self.last_active_at = datetime.utcnow()
    
    def set_preference(self, key: str, value: Any) -> None:
        """Set a preference value."""
        self.preferences[key] = value
        self.updated_at = datetime.utcnow()
    
    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a preference value."""
        return self.preferences.get(key, default)
    
    def activate(self) -> None:
        """Activate the profile."""
        self.status = ProfileStatus.ACTIVE
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Deactivate the profile."""
        self.status = ProfileStatus.INACTIVE
        self.updated_at = datetime.utcnow()
    
    def suspend(self) -> None:
        """Suspend the profile."""
        self.status = ProfileStatus.SUSPENDED
        self.updated_at = datetime.utcnow()