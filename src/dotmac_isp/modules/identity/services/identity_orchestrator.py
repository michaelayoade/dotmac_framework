"""Identity orchestrator service that coordinates all identity domain services."""

import logging
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from dotmac.core.exceptions import ServiceError
from dotmac_isp.modules.identity import schemas
from dotmac_isp.modules.portal_management.models import PortalAccountType

from .portal_service import PortalService

logger = logging.getLogger(__name__)


class IdentityOrchestrator:
    """
    Orchestrator service that coordinates all identity domain services.

    This maintains the same interface as the original monolithic services
    while delegating to focused domain services internally.
    """

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize orchestrator with all domain services."""
        self.db = db
        self.tenant_id = tenant_id

        # Initialize domain services
        self.customer_service = CustomerService(db, tenant_id)
        self.user_service = UserService(db, tenant_id)
        self.auth_service = AuthService(db, tenant_id)
        self.portal_service = PortalService(db, tenant_id)

        logger.info(f"Initialized IdentityOrchestrator for tenant: {tenant_id}")

    # ===== CUSTOMER MANAGEMENT =====

    async def create_customer(self, customer_data: schemas.CustomerCreate) -> schemas.CustomerResponse:
        """Create a new customer with full data validation and business rules."""
        return await self.customer_service.create_customer(customer_data)

    async def get_customer(self, customer_id: UUID) -> schemas.CustomerResponse:
        """Get customer by ID."""
        return await self.customer_service.get_customer(customer_id)

    async def update_customer(self, customer_id: UUID, update_data: schemas.CustomerUpdate) -> schemas.CustomerResponse:
        """Update customer information."""
        return await self.customer_service.update_customer(customer_id, update_data)

    async def list_customers(
        self,
        filters: Optional[schemas.CustomerFilters] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> schemas.CustomerListResponse:
        """List customers with optional filtering."""
        return await self.customer_service.list_customers(filters, limit, offset)

    async def activate_customer(self, customer_id: UUID) -> schemas.CustomerResponse:
        """Activate customer account."""
        return await self.customer_service.activate_customer(customer_id)

    async def suspend_customer(self, customer_id: UUID) -> schemas.CustomerResponse:
        """Suspend customer account."""
        return await self.customer_service.suspend_customer(customer_id)

    # ===== USER MANAGEMENT =====

    async def create_user(self, user_data: schemas.UserCreate) -> schemas.UserResponse:
        """Create a new user account."""
        return await self.user_service.create_user(user_data)

    async def get_user(self, user_id: UUID) -> schemas.UserResponse:
        """Get user by ID."""
        return await self.user_service.get_user(user_id)

    async def get_user_by_username(self, username: str) -> Optional[schemas.UserResponse]:
        """Get user by username."""
        return await self.user_service.get_user_by_username(username)

    async def get_user_by_email(self, email: str) -> Optional[schemas.UserResponse]:
        """Get user by email."""
        return await self.user_service.get_user_by_email(email)

    async def update_user(self, user_id: UUID, update_data: schemas.UserUpdate) -> schemas.UserResponse:
        """Update user information."""
        return await self.user_service.update_user(user_id, update_data)

    async def deactivate_user(self, user_id: UUID) -> schemas.UserResponse:
        """Deactivate user account."""
        return await self.user_service.deactivate_user(user_id)

    async def activate_user(self, user_id: UUID) -> schemas.UserResponse:
        """Activate user account."""
        return await self.user_service.activate_user(user_id)

    async def verify_user(self, user_id: UUID) -> schemas.UserResponse:
        """Verify user account."""
        return await self.user_service.verify_user(user_id)

    # ===== AUTHENTICATION =====

    async def login(
        self,
        login_data: schemas.LoginRequest,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> schemas.LoginResponse:
        """Perform user login with JWT token generation."""
        return await self.auth_service.login(login_data, ip_address, user_agent)

    async def refresh_token(self, refresh_token: str) -> schemas.TokenResponse:
        """Refresh access token using refresh token."""
        return await self.auth_service.refresh_token(refresh_token)

    async def logout(self, access_token: str) -> bool:
        """Logout user by invalidating tokens."""
        return await self.auth_service.logout(access_token)

    async def verify_token(self, access_token: str) -> Optional[schemas.UserResponse]:
        """Verify access token and return user information."""
        return await self.auth_service.verify_token(access_token)

    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> bool:
        """Change user password with current password verification."""
        return await self.auth_service.change_password(user_id, current_password, new_password)

    async def request_password_reset(self, email: str) -> str:
        """Request password reset and return reset token."""
        return await self.auth_service.request_password_reset(email)

    async def reset_password(self, reset_token: str, new_password: str) -> bool:
        """Reset password using reset token."""
        return await self.auth_service.reset_password(reset_token, new_password)

    # ===== PORTAL MANAGEMENT =====

    async def create_portal_account(self, account_data: dict[str, Any]) -> dict[str, Any]:
        """Create a new portal account."""
        return await self.portal_service.create_portal_account(account_data)

    async def activate_portal_account(self, portal_id: str) -> bool:
        """Activate portal account."""
        return await self.portal_service.activate_portal_account(portal_id)

    async def get_portal_account(self, portal_id: str) -> Optional[dict[str, Any]]:
        """Get portal account information."""
        return await self.portal_service.get_portal_account(portal_id)

    async def authenticate_portal_user(self, portal_id: str, password: str) -> Optional[dict[str, Any]]:
        """Authenticate portal user."""
        return await self.portal_service.authenticate_portal_user(portal_id, password)

    # ===== ROLE MANAGEMENT =====

    async def assign_user_roles(self, user_id: UUID, role_names: list[str]) -> None:
        """Assign roles to user."""
        return await self.user_service.assign_user_roles(user_id, role_names)

    async def remove_user_roles(self, user_id: UUID, role_names: list[str]) -> None:
        """Remove roles from user."""
        return await self.user_service.remove_user_roles(user_id, role_names)

    async def get_user_roles(self, user_id: UUID) -> list[str]:
        """Get user roles."""
        return await self.user_service.get_user_roles(user_id)

    # ===== ORCHESTRATION METHODS =====

    async def handle_customer_onboarding(self, onboarding_data: dict[str, Any]) -> dict[str, Any]:
        """Handle complete customer onboarding workflow."""
        try:
            customer_data = onboarding_data.get("customer_data")
            user_data = onboarding_data.get("user_data")

            # Create customer
            customer_response = await self.customer_service.create_customer(customer_data)
            # Create user account if user data provided
            user_response = None
            if user_data:
                user_data_dict = user_data.model_copy()
                user_data_dict["customer_id"] = customer_response.id
                user_response = await self.user_service.create_user(schemas.UserCreate(**user_data_dict))
            # Create portal account
            portal_account = None
            if hasattr(customer_response, "portal_id") and customer_response.portal_id:
                portal_data = {
                    "portal_id": customer_response.portal_id,
                    "customer_id": customer_response.id,
                    "account_type": PortalAccountType.CUSTOMER,
                    "email": getattr(customer_response, "email", None),
                    "password": getattr(customer_response, "generated_password", None),
                    "first_name": customer_response.first_name,
                    "last_name": customer_response.last_name,
                    "is_active": True,
                }
                portal_account = await self.portal_service.create_portal_account(portal_data)
            return {
                "customer": customer_response,
                "user": user_response,
                "portal_account": portal_account,
                "onboarding_status": "completed",
            }

        except Exception as e:
            logger.error(f"Customer onboarding failed: {e}")
            raise ServiceError(f"Customer onboarding failed: {str(e)}") from e

    async def handle_user_authentication_flow(self, auth_data: dict[str, Any]) -> dict[str, Any]:
        """Handle complete user authentication flow with portal integration."""
        try:
            login_request = schemas.LoginRequest(**auth_data.get("login_data", {}))
            ip_address = auth_data.get("ip_address")
            user_agent = auth_data.get("user_agent")

            # Attempt standard user login
            login_response = None
            try:
                login_response = await self.auth_service.login(login_request, ip_address, user_agent)
            except Exception as e:
                logger.debug(f"Standard login failed, trying portal auth: {e}")

            # If standard login failed, try portal authentication
            portal_auth_response = None
            if not login_response:
                try:
                    portal_auth_response = await self.portal_service.authenticate_portal_user(
                        login_request.username, login_request.password
                    )
                except Exception as e:
                    logger.debug(f"Portal authentication also failed: {e}")

            if login_response:
                return {
                    "authentication_type": "user",
                    "login_response": login_response,
                    "status": "success",
                }
            elif portal_auth_response:
                return {
                    "authentication_type": "portal",
                    "portal_response": portal_auth_response,
                    "status": "success",
                }
            else:
                return {
                    "authentication_type": None,
                    "status": "failed",
                    "error": "Invalid credentials",
                }

        except Exception as e:
            logger.error(f"Authentication flow failed: {e}")
            raise ServiceError(f"Authentication flow failed: {str(e)}") from e

    async def handle_account_recovery(self, recovery_data: dict[str, Any]) -> dict[str, Any]:
        """Handle account recovery workflow."""
        try:
            email = recovery_data.get("email")
            recovery_type = recovery_data.get("type", "password")

            if recovery_type == "password":
                # Standard password reset
                reset_token = await self.auth_service.request_password_reset(email)

                # Also try portal password reset
                portal_reset = None
                try:
                    user = await self.user_service.get_user_by_email(email)
                    if user:
                        # Find portal account for user
                        customer = await self.customer_service.get_customer(user.id)  # This is simplified
                        if hasattr(customer, "portal_id"):
                            portal_reset = await self.portal_service.reset_portal_password(customer.portal_id)
                except Exception as e:
                    logger.debug(f"Portal password reset failed: {e}")

                return {
                    "recovery_type": "password",
                    "user_reset_token": reset_token,
                    "portal_reset_password": portal_reset,
                    "status": "initiated",
                }

            return {"recovery_type": recovery_type, "status": "not_supported"}

        except Exception as e:
            logger.error(f"Account recovery failed: {e}")
            raise ServiceError(f"Account recovery failed: {str(e)}") from e


# Maintain backward compatibility
CustomerService = IdentityOrchestrator  # Alias for the orchestrator
UserService = IdentityOrchestrator  # Alias for the orchestrator
AuthService = IdentityOrchestrator  # Alias for the orchestrator
