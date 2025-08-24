"""
Identity Account SDK - user accounts (create/disable), credentials, MFA factors.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from ..core.exceptions import AccountError
from ..models.accounts import (
    MFAFactorType,
)
from ..services.account_service import AccountService


class IdentityAccountSDK:
    """Small, composable SDK for identity account management."""

    def __init__(self, tenant_id: str):
        """  Init   operation."""
        self.tenant_id = tenant_id
        self._service = AccountService()

    async def create_account(
        self, username: str, email: str, password: Optional[str] = None, **kwargs
    ) -> Dict[str, Any]:
        """Create a new user account."""
        account = await self._service.create_account(
            tenant_id=self.tenant_id,
            username=username,
            email=email,
            password=password,
            **kwargs,
        )

        return {
            "account_id": str(account.id),
            "username": account.username,
            "email": account.email,
            "status": account.status.value,
            "created_at": account.created_at.isoformat(),
        }

    async def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """Get account by ID."""
        account = await self._service.get_account(UUID(account_id))
        if not account or account.tenant_id != self.tenant_id:
            return None

        return {
            "account_id": str(account.id),
            "username": account.username,
            "email": account.email,
            "status": account.status.value,
            "created_at": account.created_at.isoformat(),
            "last_login_at": (
                account.last_login_at.isoformat() if account.last_login_at else None
            ),
            "profile_id": str(account.profile_id) if account.profile_id else None,
            "organization_id": (
                str(account.organization_id) if account.organization_id else None
            ),
        }

    async def get_account_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get account by username."""
        account = await self._service.get_account_by_username(username)
        if not account or account.tenant_id != self.tenant_id:
            return None

        return await self.get_account(str(account.id))

    async def get_account_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get account by email."""
        account = await self._service.get_account_by_email(email)
        if not account or account.tenant_id != self.tenant_id:
            return None

        return await self.get_account(str(account.id))

    async def update_account(self, account_id: str, **updates) -> Dict[str, Any]:
        """Update account."""
        account = await self._service.update_account(UUID(account_id), **updates)
        if account.tenant_id != self.tenant_id:
            raise AccountError("Account not found in tenant")

        return await self.get_account(account_id)

    async def disable_account(self, account_id: str) -> Dict[str, Any]:
        """Disable account."""
        account = await self._service.disable_account(UUID(account_id))
        if account.tenant_id != self.tenant_id:
            raise AccountError("Account not found in tenant")

        return await self.get_account(account_id)

    async def enable_account(self, account_id: str) -> Dict[str, Any]:
        """Enable account."""
        account = await self._service.enable_account(UUID(account_id))
        if account.tenant_id != self.tenant_id:
            raise AccountError("Account not found in tenant")

        return await self.get_account(account_id)

    async def set_password(self, account_id: str, password: str) -> Dict[str, Any]:
        """Set account password."""
        credential = await self._service.set_password(UUID(account_id), password)

        return {
            "credential_id": str(credential.id),
            "account_id": str(credential.account_id),
            "credential_type": credential.credential_type.value,
            "created_at": credential.created_at.isoformat(),
        }

    async def authenticate(
        self, username_or_email: str, password: str
    ) -> Dict[str, Any]:
        """Authenticate user with username/email and password."""
        account = await self._service.authenticate(username_or_email, password)
        if account.tenant_id != self.tenant_id:
            raise AccountError("Account not found in tenant")

        return {
            "account_id": str(account.id),
            "username": account.username,
            "email": account.email,
            "status": account.status.value,
            "last_login_at": (
                account.last_login_at.isoformat() if account.last_login_at else None
            ),
        }

    async def add_mfa_factor(
        self,
        account_id: str,
        factor_type: str,
        factor_data: Dict[str, Any],
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Add MFA factor to account."""
        mfa_type = MFAFactorType(factor_type)
        factor = await self._service.add_mfa_factor(
            UUID(account_id), mfa_type, factor_data, name
        )

        return {
            "factor_id": str(factor.id),
            "account_id": str(factor.account_id),
            "factor_type": factor.factor_type.value,
            "name": factor.name,
            "is_verified": factor.is_verified,
            "created_at": factor.created_at.isoformat(),
        }

    async def verify_mfa(self, account_id: str, factor_id: str, code: str) -> bool:
        """Verify MFA code."""
        return await self._service.verify_mfa(UUID(account_id), UUID(factor_id), code)

    async def list_accounts(
        self, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List accounts for tenant."""
        accounts = await self._service.list_accounts(self.tenant_id, limit, offset)

        return [
            {
                "account_id": str(account.id),
                "username": account.username,
                "email": account.email,
                "status": account.status.value,
                "created_at": account.created_at.isoformat(),
                "last_login_at": (
                    account.last_login_at.isoformat() if account.last_login_at else None
                ),
            }
            for account in accounts
        ]
