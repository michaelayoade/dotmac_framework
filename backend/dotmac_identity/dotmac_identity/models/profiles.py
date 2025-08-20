"""
User profile models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from ..core.datetime_utils import utc_now, is_expired, expires_in_hours, expires_in_minutes
from typing import Any, Dict, Optional
from uuid import UUID, uuid4


@dataclass
class UserProfile:
    """User profile model for display information."""
    id: UUID = field(default_factory=uuid4)
    account_id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""

    # Display information
    display_name: str = ""
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    middle_name: Optional[str] = None

    # Avatar and media
    avatar_url: Optional[str] = None
    avatar_data: Optional[bytes] = None

    # Localization
    locale: str = "en_US"
    timezone: str = "UTC"
    language: str = "en"

    # Contact preferences
    preferred_name: Optional[str] = None
    title: Optional[str] = None
    pronouns: Optional[str] = None

    # Metadata
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)

    # Additional profile data
    custom_fields: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_full_name(self) -> str:
        """Get full name from components."""
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.middle_name:
            parts.append(self.middle_name)
        if self.last_name:
            parts.append(self.last_name)
        return " ".join(parts) if parts else self.display_name

    def get_display_name(self) -> str:
        """Get the best display name."""
        if self.preferred_name:
            return self.preferred_name
        if self.display_name:
            return self.display_name
        return self.get_full_name() or "Unknown User"
