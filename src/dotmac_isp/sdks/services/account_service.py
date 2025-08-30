"""
Account service for SDK operations.

This is a minimal implementation for SDK compatibility.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from ..models.accounts import Account, AccountStatus, MFAFactor, MFAFactorType


class AccountService:
    """Simple in-memory account service for SDK operations."""

    def __init__(self, timezone):
        """Init   operation."""
        self._accounts: Dict[UUID, Account] = {}
        self._mfa_factors: Dict[UUID, List[MFAFactor]] = {}

    async def create_account(
        self, username: str, email: str, password: Optional[str] = None, **kwargs
    ) -> Account:
        """Create a new account."""
        account = Account(username=username, email=email, **kwargs)
        self._accounts[account.id] = account
        self._mfa_factors[account.id] = []
        return account

    async def get_account(self, account_id: UUID) -> Optional[Account]:
        """Get account by ID."""
        return self._accounts.get(account_id)

    async def get_account_by_username(self, username: str) -> Optional[Account]:
        """Get account by username."""
        for account in self._accounts.values():
            if account.username == username:
                return account
        return None

    async def get_account_by_email(self, email: str) -> Optional[Account]:
        """Get account by email."""
        for account in self._accounts.values():
            if account.email == email:
                return account
        return None

    async def update_account(self, account_id: UUID, **updates) -> Optional[Account]:
        """Update account."""
        account = self._accounts.get(account_id)
        if account:
            for key, value in updates.items():
                if hasattr(account, key):
                    setattr(account, key, value)
            account.updated_at = datetime.now(timezone.utc)
        return account

    async def delete_account(self, account_id: UUID) -> bool:
        """Delete account."""
        if account_id in self._accounts:
            del self._accounts[account_id]
            if account_id in self._mfa_factors:
                del self._mfa_factors[account_id]
            return True
        return False

    async def add_mfa_factor(
        self,
        account_id: UUID,
        factor_type: MFAFactorType,
        factor_data: Dict[str, Any],
        name: str,
    ) -> MFAFactor:
        """Add MFA factor to account."""
        factor = MFAFactor(
            account_id=account_id,
            factor_type=factor_type,
            name=name,
            metadata=factor_data,
        )
        if account_id not in self._mfa_factors:
            self._mfa_factors[account_id] = []

        self._mfa_factors[account_id].append(factor)
        return factor

    async def get_mfa_factors(self, account_id: UUID) -> List[MFAFactor]:
        """Get MFA factors for account."""
        return self._mfa_factors.get(account_id, [])

    async def remove_mfa_factor(self, account_id: UUID, factor_id: UUID) -> bool:
        """Remove MFA factor from account."""
        factors = self._mfa_factors.get(account_id, [])
        for i, factor in enumerate(factors):
            if factor.id == factor_id:
                factors.pop(i)
                return True
        return False

    async def verify_mfa_factor(self, account_id: UUID, factor_id: UUID) -> bool:
        """Verify MFA factor."""
        factors = self._mfa_factors.get(account_id, [])
        for factor in factors:
            if factor.id == factor_id:
                factor.is_verified = True
                factor.last_used_at = datetime.now(timezone.utc)
                return True
        return False
