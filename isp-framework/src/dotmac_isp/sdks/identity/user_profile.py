"""
User Profile SDK - display name, avatar, locale, timezone.
"""

from typing import Any, Dict, Optional
from uuid import UUID

from ..core.exceptions import ProfileError
from ..models.profiles import UserProfile
from ..utils.datetime_compat import utcnow


class UserProfileService:
    """In-memory service for user profile operations."""

    def __init__(self):
        self._profiles: Dict[UUID, UserProfile] = {}
        self._account_profiles: Dict[UUID, UUID] = {}

    async def create_profile(
        self, account_id: UUID, tenant_id: str, **kwargs
    ) -> UserProfile:
        """Create user profile."""
        profile = UserProfile(account_id=account_id, tenant_id=tenant_id, **kwargs)

        self._profiles[profile.id] = profile
        self._account_profiles[account_id] = profile.id
        return profile

    async def get_profile(self, profile_id: UUID) -> Optional[UserProfile]:
        """Get profile by ID."""
        return self._profiles.get(profile_id)

    async def get_profile_by_account(self, account_id: UUID) -> Optional[UserProfile]:
        """Get profile by account ID."""
        profile_id = self._account_profiles.get(account_id)
        if profile_id:
            return self._profiles.get(profile_id)
        return None

    async def update_profile(self, profile_id: UUID, **updates) -> UserProfile:
        """Update profile."""
        profile = self._profiles.get(profile_id)
        if not profile:
            raise ProfileError(f"Profile not found: {profile_id}")

        for key, value in updates.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        profile.updated_at = profile.updated_at.__class__.utcnow()
        return profile


class UserProfileSDK:
    """Small, composable SDK for user profile management."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        self._service = UserProfileService()

    async def create_profile(
        self,
        account_id: str,
        display_name: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Create user profile."""
        profile = await self._service.create_profile(
            account_id=UUID(account_id),
            tenant_id=self.tenant_id,
            display_name=display_name,
            first_name=first_name,
            last_name=last_name,
            **kwargs,
        )

        return {
            "profile_id": str(profile.id),
            "account_id": str(profile.account_id),
            "display_name": profile.display_name,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "locale": profile.locale,
            "timezone": profile.timezone,
            "created_at": profile.created_at.isoformat(),
        }

    async def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get profile by ID."""
        profile = await self._service.get_profile(UUID(profile_id))
        if not profile or profile.tenant_id != self.tenant_id:
            return None

        return {
            "profile_id": str(profile.id),
            "account_id": str(profile.account_id),
            "display_name": profile.display_name,
            "first_name": profile.first_name,
            "last_name": profile.last_name,
            "middle_name": profile.middle_name,
            "preferred_name": profile.preferred_name,
            "title": profile.title,
            "pronouns": profile.pronouns,
            "avatar_url": profile.avatar_url,
            "locale": profile.locale,
            "timezone": profile.timezone,
            "language": profile.language,
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.updated_at.isoformat(),
            "custom_fields": profile.custom_fields,
        }

    async def get_profile_by_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get profile by account ID."""
        profile = await self._service.get_profile_by_account(UUID(account_id))
        if not profile or profile.tenant_id != self.tenant_id:
            return None

        return await self.get_profile(str(profile.id))

    async def update_profile(self, profile_id: str, **updates) -> Dict[str, Any]:
        """Update profile."""
        profile = await self._service.update_profile(UUID(profile_id), **updates)
        if profile.tenant_id != self.tenant_id:
            raise ProfileError("Profile not found in tenant")

        return await self.get_profile(profile_id)

    async def update_display_name(
        self, profile_id: str, display_name: str
    ) -> Dict[str, Any]:
        """Update display name."""
        return await self.update_profile(profile_id, display_name=display_name)

    async def update_avatar(self, profile_id: str, avatar_url: str) -> Dict[str, Any]:
        """Update avatar URL."""
        return await self.update_profile(profile_id, avatar_url=avatar_url)

    async def update_locale(
        self, profile_id: str, locale: str, timezone: str
    ) -> Dict[str, Any]:
        """Update locale and timezone."""
        return await self.update_profile(profile_id, locale=locale, timezone=timezone)

    async def update_language(self, profile_id: str, language: str) -> Dict[str, Any]:
        """Update language preference."""
        return await self.update_profile(profile_id, language=language)
