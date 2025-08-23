"""Portal account management service."""

import logging
from typing import Optional, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from dotmac_isp.modules.identity.portal_service import (
    PortalAccountService as CorePortalService,
)
from dotmac_isp.modules.portal_management.models import PortalAccountType
from dotmac_isp.shared.exceptions import ServiceError
from .base_service import BaseIdentityService

logger = logging.getLogger(__name__)


class PortalService(BaseIdentityService):
    """Service wrapper for portal account operations."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize portal service."""
        super().__init__(db, tenant_id)
        self.core_portal_service = CorePortalService(db, str(self.tenant_id))

    async def create_portal_account(
        self, account_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new portal account."""
        try:
            result = await self.core_portal_service.create_portal_account(
                portal_id=account_data.get("portal_id"),
                password=account_data.get("password"),
                account_type=account_data.get(
                    "account_type", PortalAccountType.CUSTOMER
                ),
                customer_id=account_data.get("customer_id"),
                force_password_change=account_data.get("force_password_change", False),
                additional_data=account_data.get("additional_data", {}),
            )

            logger.info(f"Created portal account: {account_data.get('portal_id')}")
            return result

        except Exception as e:
            logger.error(f"Failed to create portal account: {e}")
            raise ServiceError(f"Portal account creation failed: {str(e)}")

    async def activate_portal_account(self, portal_id: str) -> bool:
        """Activate portal account."""
        try:
            result = await self.core_portal_service.activate_portal_account(portal_id)
            logger.info(f"Activated portal account: {portal_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to activate portal account {portal_id}: {e}")
            raise ServiceError(f"Portal account activation failed: {str(e)}")

    async def deactivate_portal_account(self, portal_id: str) -> bool:
        """Deactivate portal account."""
        try:
            result = await self.core_portal_service.deactivate_portal_account(portal_id)
            logger.info(f"Deactivated portal account: {portal_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to deactivate portal account {portal_id}: {e}")
            raise ServiceError(f"Portal account deactivation failed: {str(e)}")

    async def reset_portal_password(self, portal_id: str) -> str:
        """Reset portal account password."""
        try:
            result = await self.core_portal_service.reset_portal_password(portal_id)
            logger.info(f"Reset password for portal account: {portal_id}")
            return result

        except Exception as e:
            logger.error(
                f"Failed to reset password for portal account {portal_id}: {e}"
            )
            raise ServiceError(f"Portal password reset failed: {str(e)}")

    async def get_portal_account(self, portal_id: str) -> Optional[Dict[str, Any]]:
        """Get portal account information."""
        try:
            result = await self.core_portal_service.get_portal_account(portal_id)
            return result

        except Exception as e:
            logger.error(f"Failed to get portal account {portal_id}: {e}")
            raise ServiceError(f"Failed to retrieve portal account: {str(e)}")

    async def update_portal_account(
        self, portal_id: str, update_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update portal account information."""
        try:
            result = await self.core_portal_service.update_portal_account(
                portal_id, update_data
            )
            logger.info(f"Updated portal account: {portal_id}")
            return result

        except Exception as e:
            logger.error(f"Failed to update portal account {portal_id}: {e}")
            raise ServiceError(f"Portal account update failed: {str(e)}")

    async def authenticate_portal_user(
        self, portal_id: str, password: str
    ) -> Optional[Dict[str, Any]]:
        """Authenticate portal user."""
        try:
            result = await self.core_portal_service.authenticate_portal_user(
                portal_id, password
            )
            if result:
                logger.info(f"Portal authentication successful: {portal_id}")
            return result

        except Exception as e:
            logger.error(f"Portal authentication failed for {portal_id}: {e}")
            raise ServiceError(f"Portal authentication failed: {str(e)}")

    async def change_portal_password(
        self, portal_id: str, current_password: str, new_password: str
    ) -> bool:
        """Change portal account password."""
        try:
            result = await self.core_portal_service.change_portal_password(
                portal_id, current_password, new_password
            )
            logger.info(f"Changed password for portal account: {portal_id}")
            return result

        except Exception as e:
            logger.error(
                f"Failed to change password for portal account {portal_id}: {e}"
            )
            raise ServiceError(f"Portal password change failed: {str(e)}")

    async def get_customer_portal_accounts(self, customer_id: UUID) -> list:
        """Get all portal accounts for a customer."""
        try:
            result = await self.core_portal_service.get_customer_portal_accounts(
                customer_id
            )
            return result

        except Exception as e:
            logger.error(
                f"Failed to get portal accounts for customer {customer_id}: {e}"
            )
            raise ServiceError(f"Failed to retrieve customer portal accounts: {str(e)}")
