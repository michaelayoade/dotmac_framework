"""Service interfaces for identity domain."""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from .. import schemas
from ..models import Customer, CustomerType, User, UserRole, UserSession


class ICustomerService(ABC):
    """Interface for customer domain service."""

    @abstractmethod
    async def create_customer(
        self, customer_data: schemas.CustomerCreate
    ) -> schemas.CustomerResponse:
        """Create a new customer."""

    @abstractmethod
    async def get_customer(self, customer_id: UUID) -> schemas.CustomerResponse:
        """Get customer by ID."""

    @abstractmethod
    async def update_customer(
        self, customer_id: UUID, update_data: schemas.CustomerUpdate
    ) -> schemas.CustomerResponse:
        """Update customer information."""

    @abstractmethod
    async def deactivate_customer(self, customer_id: UUID, reason: str) -> bool:
        """Deactivate customer account."""

    @abstractmethod
    async def search_customers(
        self, filters: schemas.CustomerSearchFilters
    ) -> List[schemas.CustomerResponse]:
        """Search customers with filters."""

    @abstractmethod
    async def validate_customer_data(
        self, customer_data: schemas.CustomerCreate
    ) -> bool:
        """Validate customer creation data."""

    @abstractmethod
    async def generate_customer_number(self) -> str:
        """Generate unique customer number."""


class IUserService(ABC):
    """Interface for user domain service."""

    @abstractmethod
    async def create_user(self, user_data: schemas.UserCreate) -> schemas.UserResponse:
        """Create a new user."""

    @abstractmethod
    async def get_user(self, user_id: UUID) -> schemas.UserResponse:
        """Get user by ID."""

    @abstractmethod
    async def get_user_by_email(self, email: str) -> schemas.UserResponse:
        """Get user by email."""

    @abstractmethod
    async def update_user(
        self, user_id: UUID, update_data: schemas.UserUpdate
    ) -> schemas.UserResponse:
        """Update user information."""

    @abstractmethod
    async def change_password(
        self, user_id: UUID, current_password: str, new_password: str
    ) -> bool:
        """Change user password."""

    @abstractmethod
    async def reset_password(self, email: str) -> str:
        """Reset user password and return temporary password."""

    @abstractmethod
    async def assign_role(self, user_id: UUID, role: UserRole) -> bool:
        """Assign role to user."""

    @abstractmethod
    async def remove_role(self, user_id: UUID, role: UserRole) -> bool:
        """Remove role from user."""


class IAuthenticationService(ABC):
    """Interface for authentication domain service."""

    @abstractmethod
    async def authenticate_user(
        self, email: str, password: str
    ) -> schemas.AuthResponse:
        """Authenticate user and return tokens."""

    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> schemas.AuthResponse:
        """Refresh authentication token."""

    @abstractmethod
    async def logout_user(
        self, user_id: UUID, session_id: Optional[str] = None
    ) -> bool:
        """Logout user and invalidate session."""

    @abstractmethod
    async def validate_token(self, token: str) -> schemas.TokenValidation:
        """Validate authentication token."""

    @abstractmethod
    async def create_session(
        self, user_id: UUID, device_info: Dict[str, Any]
    ) -> UserSession:
        """Create user session."""

    @abstractmethod
    async def get_active_sessions(self, user_id: UUID) -> List[UserSession]:
        """Get active sessions for user."""

    @abstractmethod
    async def revoke_session(self, session_id: str) -> bool:
        """Revoke user session."""


class IAuthorizationService(ABC):
    """Interface for authorization domain service."""

    @abstractmethod
    async def check_permission(self, user_id: UUID, resource: str, action: str) -> bool:
        """Check if user has permission for resource action."""

    @abstractmethod
    async def get_user_permissions(self, user_id: UUID) -> List[str]:
        """Get all permissions for user."""

    @abstractmethod
    async def has_role(self, user_id: UUID, role: UserRole) -> bool:
        """Check if user has specific role."""

    @abstractmethod
    async def get_user_roles(self, user_id: UUID) -> List[UserRole]:
        """Get all roles for user."""

    @abstractmethod
    async def check_resource_access(
        self, user_id: UUID, resource_id: UUID, resource_type: str
    ) -> bool:
        """Check if user can access specific resource."""


class IPortalService(ABC):
    """Interface for portal management domain service."""

    @abstractmethod
    async def generate_portal_id(self, customer_id: UUID) -> str:
        """Generate unique portal ID for customer."""

    @abstractmethod
    async def create_portal_account(
        self, portal_data: schemas.PortalAccountCreate
    ) -> schemas.PortalAccountResponse:
        """Create portal account."""

    @abstractmethod
    async def get_portal_account(self, portal_id: str) -> schemas.PortalAccountResponse:
        """Get portal account by portal ID."""

    @abstractmethod
    async def update_portal_preferences(
        self, portal_id: str, preferences: Dict[str, Any]
    ) -> bool:
        """Update portal user preferences."""

    @abstractmethod
    async def reset_portal_access(self, portal_id: str) -> str:
        """Reset portal access and return new credentials."""


class IPasswordService(ABC):
    """Interface for password management domain service."""

    @abstractmethod
    def hash_password(self, password: str) -> str:
        """Hash password securely."""

    @abstractmethod
    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""

    @abstractmethod
    def generate_password(self, length: int = 12, include_symbols: bool = True) -> str:
        """Generate secure random password."""

    @abstractmethod
    def validate_password_strength(self, password: str) -> Dict[str, Any]:
        """Validate password strength and return requirements."""

    @abstractmethod
    def generate_reset_token(self) -> str:
        """Generate password reset token."""


class IUserValidationService(ABC):
    """Interface for user validation domain service."""

    @abstractmethod
    async def validate_email_format(self, email: str) -> bool:
        """Validate email format."""

    @abstractmethod
    async def validate_email_uniqueness(
        self, email: str, exclude_user_id: Optional[UUID] = None
    ) -> bool:
        """Validate email uniqueness."""

    @abstractmethod
    async def validate_username_uniqueness(
        self, username: str, exclude_user_id: Optional[UUID] = None
    ) -> bool:
        """Validate username uniqueness."""

    @abstractmethod
    async def validate_phone_format(self, phone: str) -> bool:
        """Validate phone number format."""

    @abstractmethod
    async def validate_customer_number_uniqueness(self, customer_number: str) -> bool:
        """Validate customer number uniqueness."""


class IIdentityEventService(ABC):
    """Interface for identity event handling service."""

    @abstractmethod
    async def publish_customer_created(self, customer: Customer) -> None:
        """Publish customer created event."""

    @abstractmethod
    async def publish_user_created(self, user: User) -> None:
        """Publish user created event."""

    @abstractmethod
    async def publish_user_authenticated(
        self, user: User, session: UserSession
    ) -> None:
        """Publish user authenticated event."""

    @abstractmethod
    async def publish_password_changed(self, user: User) -> None:
        """Publish password changed event."""

    @abstractmethod
    async def publish_account_deactivated(self, user_id: UUID, reason: str) -> None:
        """Publish account deactivated event."""


class IIdentityIntegrationService(ABC):
    """Interface for identity integration service."""

    @abstractmethod
    async def sync_with_external_system(self, user_id: UUID, system_name: str) -> bool:
        """Sync user with external system."""

    @abstractmethod
    async def import_users_from_ldap(
        self, ldap_query: str
    ) -> List[schemas.UserResponse]:
        """Import users from LDAP."""

    @abstractmethod
    async def sync_customer_with_billing(self, customer_id: UUID) -> bool:
        """Sync customer data with billing system."""

    @abstractmethod
    async def notify_crm_customer_change(
        self, customer_id: UUID, change_type: str
    ) -> bool:
        """Notify CRM system of customer changes."""
