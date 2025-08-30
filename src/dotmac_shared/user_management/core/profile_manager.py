"""
Profile Manager for Unified User Management.

Handles user profile data, preferences, and extended information across platforms.
Provides consistent profile management while supporting platform-specific customizations.
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.user_schemas import (
    ContactInformation,
    NotificationPreferences,
    UserPreferences,
    UserProfile,
    UserResponse,
    UserUpdate,
)
from .user_repository import UserRepository


class ProfileManager:
    """
    Manager for user profile operations.

    Handles profile data, preferences, contact information, and avatar management
    across both ISP Framework and Management Platform.
    """

    def __init__(
        self,
        db_session: AsyncSession,
        user_repository: Optional[UserRepository] = None,
        config: Dict[str, Any] = None,
    ):
        """Initialize profile manager."""
        self.db_session = db_session
        self.user_repository = user_repository or UserRepository(db_session)
        self.config = config or {}

        # Configuration defaults
        self.avatar_max_size = self.config.get(
            "avatar_max_size", 5 * 1024 * 1024
        )  # 5MB
        self.avatar_formats = self.config.get("avatar_formats", ["jpg", "png", "webp"])
        self.profile_validation_enabled = self.config.get(
            "profile_validation_enabled", True
        )

    # Profile Management
    async def get_user_profile(self, user_id: UUID) -> Optional[UserProfile]:
        """Get complete user profile."""

        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            return None

        # Extract profile data from user platform_specific data
        profile_data = (
            user.platform_specific.get("profile", {}) if user.platform_specific else {}
        )

        # Create UserProfile from stored data
        profile = UserProfile()

        # Personal information
        profile.title = profile_data.get("title")
        profile.middle_name = profile_data.get("middle_name")
        profile.date_of_birth = self._parse_date(profile_data.get("date_of_birth"))
        profile.gender = profile_data.get("gender")

        # Contact information
        contact_data = profile_data.get("contact", {})
        profile.contact = ContactInformation(
            phone=contact_data.get("phone"),
            mobile=contact_data.get("mobile"),
            address_line1=contact_data.get("address_line1"),
            address_line2=contact_data.get("address_line2"),
            city=contact_data.get("city"),
            state=contact_data.get("state"),
            postal_code=contact_data.get("postal_code"),
            country=contact_data.get("country"),
        )

        # Professional information
        profile.job_title = profile_data.get("job_title")
        profile.department = profile_data.get("department")
        profile.company = profile_data.get("company")

        # Profile metadata
        profile.avatar_url = profile_data.get("avatar_url")
        profile.bio = profile_data.get("bio")
        profile.website = profile_data.get("website")

        # Preferences
        preferences_data = profile_data.get("preferences", {})
        profile.preferences = self._create_user_preferences(preferences_data)

        # Platform-specific profile data
        profile.platform_specific = profile_data.get("platform_specific", {})

        return profile

    async def update_user_profile(
        self,
        user_id: UUID,
        profile_updates: Dict[str, Any],
        updated_by: Optional[UUID] = None,
    ) -> Optional[UserProfile]:
        """Update user profile information."""

        # Get current user
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            return None

        # Get current profile data
        current_platform_data = user.platform_specific or {}
        current_profile_data = current_platform_data.get("profile", {})

        # Validate profile updates
        if self.profile_validation_enabled:
            validation_result = await self._validate_profile_updates(profile_updates)
            if not validation_result["valid"]:
                raise ValueError(
                    f"Profile validation failed: {validation_result['errors']}"
                )

        # Apply updates to profile data
        updated_profile_data = self._apply_profile_updates(
            current_profile_data, profile_updates
        )

        # Update platform-specific data
        current_platform_data["profile"] = updated_profile_data
        current_platform_data["profile_updated_at"] = datetime.utcnow().isoformat()
        current_platform_data["profile_updated_by"] = (
            str(updated_by) if updated_by else None
        )

        # Update user record
        update_data = UserUpdate(platform_specific=current_platform_data)
        updated_user = await self.user_repository.update_user(user_id, update_data)

        if updated_user:
            # Record profile update event
            await self._record_profile_event(
                user_id,
                "profile_updated",
                {
                    "updates": list(profile_updates.keys()),
                    "updated_by": str(updated_by) if updated_by else None,
                },
            )

            return await self.get_user_profile(user_id)

        return None

    async def update_user_preferences(
        self,
        user_id: UUID,
        preferences: Dict[str, Any],
        updated_by: Optional[UUID] = None,
    ) -> Optional[UserPreferences]:
        """Update user preferences."""

        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            return None

        # Get current platform data
        current_platform_data = user.platform_specific or {}
        current_profile_data = current_platform_data.get("profile", {})
        current_preferences = current_profile_data.get("preferences", {})

        # Update preferences
        updated_preferences = {**current_preferences, **preferences}
        current_profile_data["preferences"] = updated_preferences
        current_platform_data["profile"] = current_profile_data

        # Update user record
        update_data = UserUpdate(platform_specific=current_platform_data)
        updated_user = await self.user_repository.update_user(user_id, update_data)

        if updated_user:
            # Record preferences update
            await self._record_profile_event(
                user_id,
                "preferences_updated",
                {
                    "updated_preferences": list(preferences.keys()),
                    "updated_by": str(updated_by) if updated_by else None,
                },
            )

            return self._create_user_preferences(updated_preferences)

        return None

    # Avatar Management
    async def upload_user_avatar(
        self, user_id: UUID, avatar_data: bytes, filename: str, content_type: str
    ) -> Optional[str]:
        """Upload and set user avatar."""

        # Validate avatar
        validation_result = await self._validate_avatar(
            avatar_data, filename, content_type
        )
        if not validation_result["valid"]:
            raise ValueError(f"Avatar validation failed: {validation_result['error']}")

        try:
            # Store avatar (implementation depends on storage system)
            avatar_url = await self._store_avatar(
                user_id, avatar_data, filename, content_type
            )

            # Update user profile with avatar URL
            profile_updates = {"avatar_url": avatar_url}
            await self.update_user_profile(user_id, profile_updates)

            # Record avatar upload
            await self._record_profile_event(
                user_id,
                "avatar_uploaded",
                {
                    "avatar_url": avatar_url,
                    "filename": filename,
                    "content_type": content_type,
                    "size": len(avatar_data),
                },
            )

            return avatar_url

        except Exception as e:
            await self._record_profile_event(
                user_id, "avatar_upload_failed", {"error": str(e), "filename": filename}
            )
            raise

    async def remove_user_avatar(self, user_id: UUID) -> bool:
        """Remove user avatar."""

        try:
            # Get current avatar URL
            profile = await self.get_user_profile(user_id)
            if not profile or not profile.avatar_url:
                return True

            # Remove avatar file
            await self._delete_avatar_file(profile.avatar_url)

            # Update profile to remove avatar URL
            profile_updates = {"avatar_url": None}
            await self.update_user_profile(user_id, profile_updates)

            # Record avatar removal
            await self._record_profile_event(
                user_id, "avatar_removed", {"previous_avatar_url": profile.avatar_url}
            )

            return True

        except Exception as e:
            await self._record_profile_event(
                user_id, "avatar_removal_failed", {"error": str(e)}
            )
            return False

    # Contact Information Management
    async def update_contact_information(
        self, user_id: UUID, contact_info: Dict[str, Any], verify_changes: bool = True
    ) -> Optional[ContactInformation]:
        """Update user contact information."""

        # Validate contact information
        if self.profile_validation_enabled:
            validation_result = await self._validate_contact_info(contact_info)
            if not validation_result["valid"]:
                raise ValueError(
                    f"Contact validation failed: {validation_result['errors']}"
                )

        # Update profile with contact information
        profile_updates = {"contact": contact_info}
        updated_profile = await self.update_user_profile(user_id, profile_updates)

        if updated_profile and verify_changes:
            # Trigger verification for phone/email changes
            await self._trigger_contact_verification(user_id, contact_info)

        return updated_profile.contact if updated_profile else None

    # Profile Search and Analytics
    async def search_profiles_by_criteria(
        self, criteria: Dict[str, Any], limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Search user profiles by various criteria."""

        # This would implement complex profile searching
        # For now, return empty list as placeholder
        return []

    async def get_profile_completion_status(self, user_id: UUID) -> Dict[str, Any]:
        """Get user profile completion status and suggestions."""

        profile = await self.get_user_profile(user_id)
        if not profile:
            return {"completion_percentage": 0, "missing_fields": []}

        # Define required/recommended fields
        required_fields = [
            "contact.phone",
            "contact.address_line1",
            "contact.city",
            "contact.state",
            "contact.country",
        ]

        optional_fields = [
            "title",
            "middle_name",
            "date_of_birth",
            "job_title",
            "company",
            "bio",
            "avatar_url",
        ]

        completed_required = 0
        completed_optional = 0
        missing_fields = []

        # Check required fields
        for field_path in required_fields:
            if self._has_field_value(profile, field_path):
                completed_required += 1
            else:
                missing_fields.append(field_path)

        # Check optional fields
        for field_path in optional_fields:
            if self._has_field_value(profile, field_path):
                completed_optional += 1

        # Calculate completion percentage
        total_fields = len(required_fields) + len(optional_fields)
        completed_fields = completed_required + completed_optional
        completion_percentage = int((completed_fields / total_fields) * 100)

        return {
            "completion_percentage": completion_percentage,
            "required_completed": completed_required,
            "required_total": len(required_fields),
            "optional_completed": completed_optional,
            "optional_total": len(optional_fields),
            "missing_fields": missing_fields,
            "recommendations": self._get_profile_recommendations(profile),
        }

    # Helper Methods
    def _create_user_preferences(
        self, preferences_data: Dict[str, Any]
    ) -> UserPreferences:
        """Create UserPreferences object from data."""

        # Notification preferences
        notification_data = preferences_data.get("notifications", {})
        notifications = NotificationPreferences(
            email=notification_data.get("email", True),
            sms=notification_data.get("sms", False),
            push=notification_data.get("push", True),
            in_app=notification_data.get("in_app", True),
            security_alerts=notification_data.get("security_alerts", True),
            account_updates=notification_data.get("account_updates", True),
            system_maintenance=notification_data.get("system_maintenance", False),
            marketing=notification_data.get("marketing", False),
            platform_specific=notification_data.get("platform_specific", {}),
        )

        return UserPreferences(
            language=preferences_data.get("language", "en-US"),
            timezone=preferences_data.get("timezone", "UTC"),
            theme=preferences_data.get("theme", "light"),
            date_format=preferences_data.get("date_format", "YYYY-MM-DD"),
            time_format=preferences_data.get("time_format", "24h"),
            notifications=notifications,
            platform_specific=preferences_data.get("platform_specific", {}),
        )

    def _apply_profile_updates(
        self, current_profile: Dict[str, Any], updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply profile updates to current profile data."""

        updated_profile = current_profile.copy()

        # Handle nested updates
        for key, value in updates.items():
            if key == "contact" and isinstance(value, dict):
                # Update contact information
                current_contact = updated_profile.get("contact", {})
                current_contact.update(value)
                updated_profile["contact"] = current_contact
            elif key == "preferences" and isinstance(value, dict):
                # Update preferences
                current_prefs = updated_profile.get("preferences", {})
                current_prefs.update(value)
                updated_profile["preferences"] = current_prefs
            elif key == "platform_specific" and isinstance(value, dict):
                # Update platform-specific data
                current_platform = updated_profile.get("platform_specific", {})
                current_platform.update(value)
                updated_profile["platform_specific"] = current_platform
            else:
                # Direct field update
                updated_profile[key] = value

        return updated_profile

    def _parse_date(self, date_str: Optional[str]) -> Optional[date]:
        """Parse date string to date object."""
        if not date_str:
            return None

        try:
            return datetime.fromisoformat(date_str).date()
        except (ValueError, TypeError):
            return None

    def _has_field_value(self, profile: UserProfile, field_path: str) -> bool:
        """Check if profile has value for nested field path."""

        parts = field_path.split(".")
        current = profile

        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
                if current is None:
                    return False
            else:
                return False

        # Check if final value is meaningful
        if isinstance(current, str):
            return bool(current.strip())
        elif isinstance(current, (list, dict)):
            return bool(current)
        else:
            return current is not None

    def _get_profile_recommendations(self, profile: UserProfile) -> List[str]:
        """Get profile completion recommendations."""

        recommendations = []

        if not profile.avatar_url:
            recommendations.append("Add a profile picture")

        if not profile.bio:
            recommendations.append("Add a bio to tell others about yourself")

        if not profile.contact.phone:
            recommendations.append("Add a phone number for account security")

        if not profile.contact.address_line1:
            recommendations.append("Complete your address information")

        if not profile.job_title and not profile.company:
            recommendations.append("Add professional information")

        return recommendations

    # Validation Methods
    async def _validate_profile_updates(
        self, updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate profile update data."""

        errors = []

        # Validate contact information
        if "contact" in updates:
            contact_validation = await self._validate_contact_info(updates["contact"])
            if not contact_validation["valid"]:
                errors.extend(contact_validation["errors"])

        # Validate date of birth
        if "date_of_birth" in updates:
            dob_str = updates["date_of_birth"]
            if dob_str and not self._parse_date(dob_str):
                errors.append("Invalid date of birth format")

        # Validate website URL
        if "website" in updates:
            website = updates["website"]
            if website and not self._is_valid_url(website):
                errors.append("Invalid website URL")

        return {"valid": len(errors) == 0, "errors": errors}

    async def _validate_contact_info(
        self, contact_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate contact information."""

        errors = []

        # Validate email format
        if "email" in contact_info:
            email = contact_info["email"]
            if email and not self._is_valid_email(email):
                errors.append("Invalid email format")

        # Validate phone numbers
        for phone_field in ["phone", "mobile"]:
            if phone_field in contact_info:
                phone = contact_info[phone_field]
                if phone and not self._is_valid_phone(phone):
                    errors.append(f"Invalid {phone_field} format")

        # Validate postal code
        if "postal_code" in contact_info:
            postal_code = contact_info["postal_code"]
            country = contact_info.get("country", "")
            if postal_code and not self._is_valid_postal_code(postal_code, country):
                errors.append("Invalid postal code format")

        return {"valid": len(errors) == 0, "errors": errors}

    async def _validate_avatar(
        self, avatar_data: bytes, filename: str, content_type: str
    ) -> Dict[str, Any]:
        """Validate avatar upload."""

        # Check file size
        if len(avatar_data) > self.avatar_max_size:
            return {
                "valid": False,
                "error": f"Avatar file too large. Maximum size is {self.avatar_max_size // 1024 // 1024}MB",
            }

        # Check file format
        file_extension = Path(filename).suffix.lower().lstrip(".")
        if file_extension not in self.avatar_formats:
            return {
                "valid": False,
                "error": f"Invalid avatar format. Supported formats: {', '.join(self.avatar_formats)}",
            }

        # Check content type
        valid_content_types = [f"image/{fmt}" for fmt in self.avatar_formats]
        if content_type not in valid_content_types:
            return {
                "valid": False,
                "error": f"Invalid content type. Expected one of: {', '.join(valid_content_types)}",
            }

        return {"valid": True}

    # Utility Methods
    def _is_valid_email(self, email: str) -> bool:
        """Basic email validation."""
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return re.match(pattern, email) is not None

    def _is_valid_phone(self, phone: str) -> bool:
        """Basic phone number validation."""
        import re

        # Remove common separators
        clean_phone = re.sub(r"[\s\-\(\)\+]", "", phone)
        # Check if it's all digits and reasonable length
        return clean_phone.isdigit() and 7 <= len(clean_phone) <= 15

    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation."""
        import re

        pattern = r"^https?://(?:[-\w.])+(?::[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$"
        return re.match(pattern, url) is not None

    def _is_valid_postal_code(self, postal_code: str, country: str) -> bool:
        """Basic postal code validation."""
        # Simplified validation - in practice, would use country-specific rules
        return len(postal_code.strip()) >= 3

    # Storage Methods (to be implemented)
    async def _store_avatar(
        self, user_id: UUID, avatar_data: bytes, filename: str, content_type: str
    ) -> str:
        """Store avatar file and return URL."""
        # Implementation would depend on storage backend (S3, local, etc.)
        return f"/avatars/{user_id}/{filename}"

    async def _delete_avatar_file(self, avatar_url: str):
        """Delete avatar file from storage."""
        # Implementation would depend on storage backend
        pass

    # Event Recording
    async def _record_profile_event(
        self, user_id: UUID, event_type: str, event_data: Dict[str, Any]
    ):
        """Record profile-related event."""
        # Implementation would create lifecycle event
        pass

    # Contact Verification
    async def _trigger_contact_verification(
        self, user_id: UUID, contact_changes: Dict[str, Any]
    ):
        """Trigger verification for contact information changes."""
        # Implementation would send verification emails/SMS
        pass
