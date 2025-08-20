"""
In-memory account service for identity management.
"""

import hashlib
from datetime import datetime, timedelta
from ..core.datetime_utils import utc_now, is_expired, expires_in_hours, expires_in_minutes
from typing import Dict, List, Optional
from uuid import UUID

from ..core.exceptions import (
    AccountDisabledError,
    AccountError,
    AccountNotFoundError,
    InvalidCredentialsError,
    MFARequiredError,
)
from ..models.accounts import (
    Account,
    AccountStatus,
    Credential,
    CredentialType,
    MFAFactor,
    MFAFactorType,
)


class AccountService:
    """In-memory service for account operations."""

    def __init__(self):
        self._accounts: Dict[UUID, Account] = {}
        self._credentials: Dict[UUID, List[Credential]] = {}
        self._mfa_factors: Dict[UUID, List[MFAFactor]] = {}
        self._username_index: Dict[str, UUID] = {}
        self._email_index: Dict[str, UUID] = {}

    async def create_account(
        self,
        tenant_id: str,
        username: str,
        email: str,
        password: Optional[str] = None,
        **kwargs
    ) -> Account:
        """Create a new account."""
        # Check for existing username/email
        if username in self._username_index:
            raise AccountError(f"Username already exists: {username}")
        if email in self._email_index:
            raise AccountError(f"Email already exists: {email}")

        account = Account(
            tenant_id=tenant_id,
            username=username,
            email=email,
            **kwargs
        )

        self._accounts[account.id] = account
        self._username_index[username] = account.id
        self._email_index[email] = account.id
        self._credentials[account.id] = []
        self._mfa_factors[account.id] = []

        # Create password credential if provided
        if password:
            await self.set_password(account.id, password)

        return account

    async def get_account(self, account_id: UUID) -> Optional[Account]:
        """Get account by ID."""
        return self._accounts.get(account_id)

    async def get_account_by_username(self, username: str) -> Optional[Account]:
        """Get account by username."""
        account_id = self._username_index.get(username)
        if account_id:
            return self._accounts.get(account_id)
        return None

    async def get_account_by_email(self, email: str) -> Optional[Account]:
        """Get account by email."""
        account_id = self._email_index.get(email)
        if account_id:
            return self._accounts.get(account_id)
        return None

    async def update_account(self, account_id: UUID, **updates) -> Account:
        """Update account."""
        account = self._accounts.get(account_id)
        if not account:
            raise AccountNotFoundError(str(account_id))

        # Handle username/email updates
        if "username" in updates and updates["username"] != account.username:
            if updates["username"] in self._username_index:
                raise AccountError(f"Username already exists: {updates['username']}")
            del self._username_index[account.username]
            self._username_index[updates["username"]] = account_id

        if "email" in updates and updates["email"] != account.email:
            if updates["email"] in self._email_index:
                raise AccountError(f"Email already exists: {updates['email']}")
            del self._email_index[account.email]
            self._email_index[updates["email"]] = account_id

        # Update account fields
        for key, value in updates.items():
            if hasattr(account, key):
                setattr(account, key, value)

        account.updated_at = utc_now()
        return account

    async def disable_account(self, account_id: UUID) -> Account:
        """Disable account."""
        return await self.update_account(account_id, status=AccountStatus.DISABLED)

    async def enable_account(self, account_id: UUID) -> Account:
        """Enable account."""
        return await self.update_account(account_id, status=AccountStatus.ACTIVE)

    async def set_password(self, account_id: UUID, password: str) -> Credential:
        """Set account password."""
        account = self._accounts.get(account_id)
        if not account:
            raise AccountNotFoundError(str(account_id))

        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        # Remove existing password credentials
        credentials = self._credentials[account_id]
        self._credentials[account_id] = [
            c for c in credentials if c.credential_type != CredentialType.PASSWORD
        ]

        # Create new password credential
        credential = Credential(
            account_id=account_id,
            tenant_id=account.tenant_id,
            credential_type=CredentialType.PASSWORD,
            credential_data=password_hash,
            name="Password"
        )

        self._credentials[account_id].append(credential)
        account.password_changed_at = utc_now()
        account.updated_at = utc_now()

        return credential

    async def verify_password(self, account_id: UUID, password: str) -> bool:
        """Verify account password."""
        credentials = self._credentials.get(account_id, [])
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        for credential in credentials:
            if (credential.credential_type == CredentialType.PASSWORD and
                credential.is_valid() and
                credential.credential_data == password_hash):
                credential.last_used_at = utc_now()
                credential.usage_count += 1
                return True

        return False

    async def authenticate(self, username_or_email: str, password: str) -> Account:
        """Authenticate user with username/email and password."""
        # Find account
        account = (await self.get_account_by_username(username_or_email) or
                  await self.get_account_by_email(username_or_email))

        if not account:
            raise InvalidCredentialsError()

        if not account.can_login():
            if account.is_locked():
                raise AccountError("Account is locked")
            else:
                raise AccountDisabledError(str(account.id))

        # Verify password
        if not await self.verify_password(account.id, password):
            account.failed_login_attempts += 1
            if account.failed_login_attempts >= 5:  # Lock after 5 failed attempts
                account.locked_until = utc_now() + timedelta(minutes=15)
                account.status = AccountStatus.LOCKED
            raise InvalidCredentialsError()

        # Check if MFA is required
        mfa_factors = self._mfa_factors.get(account.id, [])
        active_mfa = [f for f in mfa_factors if f.is_valid()]
        if active_mfa:
            raise MFARequiredError(str(account.id))

        # Successful login
        account.failed_login_attempts = 0
        account.locked_until = None
        account.last_login_at = utc_now()
        account.last_activity_at = utc_now()

        return account

    async def add_mfa_factor(
        self,
        account_id: UUID,
        factor_type: MFAFactorType,
        factor_data: Dict,
        name: Optional[str] = None
    ) -> MFAFactor:
        """Add MFA factor to account."""
        account = self._accounts.get(account_id)
        if not account:
            raise AccountNotFoundError(str(account_id))

        mfa_factor = MFAFactor(
            account_id=account_id,
            tenant_id=account.tenant_id,
            factor_type=factor_type,
            factor_data=factor_data,
            name=name or factor_type.value
        )

        if account_id not in self._mfa_factors:
            self._mfa_factors[account_id] = []

        self._mfa_factors[account_id].append(mfa_factor)
        return mfa_factor

    async def verify_mfa(self, account_id: UUID, factor_id: UUID, code: str) -> bool:
        """Verify MFA code."""
        mfa_factors = self._mfa_factors.get(account_id, [])

        for factor in mfa_factors:
            if factor.id == factor_id and factor.is_valid():
                # Simple verification logic (in real implementation, would verify TOTP, etc.)
                if factor.factor_type == MFAFactorType.BACKUP_CODES:
                    if code in factor.backup_codes and code not in factor.used_backup_codes:
                        factor.used_backup_codes.append(code)
                        factor.last_used_at = utc_now()
                        factor.usage_count += 1
                        return True
                # For demo purposes, accept any 6-digit code
                elif len(code) == 6 and code.isdigit():
                    factor.last_used_at = utc_now()
                    factor.usage_count += 1
                    return True

                factor.failed_attempts += 1
                return False

        return False

    async def list_accounts(self, tenant_id: str, limit: int = 100, offset: int = 0) -> List[Account]:
        """List accounts for tenant."""
        accounts = [
            account for account in self._accounts.values()
            if account.tenant_id == tenant_id
        ]
        return accounts[offset:offset + limit]
