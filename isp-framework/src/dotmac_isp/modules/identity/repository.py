"""Repository pattern for identity/customer database operations."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import and_, or_, func

from dotmac_isp.modules.identity.models import (
    Customer,
    User,
    Role,
    CustomerType,
    AccountStatus,
)
from dotmac_isp.shared.exceptions import NotFoundError, ConflictError, ValidationError


class CustomerRepository:
    """Repository for customer database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, customer_data: Dict[str, Any]) -> Customer:
        """Create a new customer in the database."""
        try:
            # Generate portal_id if not provided
            if not customer_data.get("portal_id"):
                customer_data["portal_id"] = self._generate_portal_id()

            customer = Customer(id=uuid4(), tenant_id=self.tenant_id, **customer_data)

            self.db.add(customer)
            self.db.commit()
            self.db.refresh(customer)
            return customer

        except IntegrityError as e:
            self.db.rollback()
            if "customer_number" in str(e):
                raise ConflictError(
                    f"Customer number {customer_data.get('customer_number')} already exists"
                )
            elif "portal_id" in str(e):
                raise ConflictError(
                    f"Portal ID {customer_data.get('portal_id')} already exists"
                )
            else:
                raise ConflictError("Customer creation failed due to data conflict")

    def get_by_id(self, customer_id: UUID) -> Optional[Customer]:
        """Get customer by ID."""
        return (
            self.db.query(Customer)
            .filter(
                and_(
                    Customer.id == customer_id,
                    Customer.tenant_id == self.tenant_id,
                    Customer.is_deleted == False,
                )
            )
            .first()
        )

    def get_by_customer_number(self, customer_number: str) -> Optional[Customer]:
        """Get customer by customer number."""
        return (
            self.db.query(Customer)
            .filter(
                and_(
                    Customer.customer_number == customer_number,
                    Customer.tenant_id == self.tenant_id,
                    Customer.is_deleted == False,
                )
            )
            .first()
        )

    def get_by_portal_id(self, portal_id: str) -> Optional[Customer]:
        """Get customer by portal ID."""
        return (
            self.db.query(Customer)
            .filter(
                and_(
                    Customer.portal_id == portal_id,
                    Customer.tenant_id == self.tenant_id,
                    Customer.is_deleted == False,
                )
            )
            .first()
        )

    def update(
        self, customer_id: UUID, update_data: Dict[str, Any]
    ) -> Optional[Customer]:
        """Update customer by ID."""
        customer = self.get_by_id(customer_id)
        if not customer:
            return None

        try:
            for key, value in update_data.items():
                if hasattr(customer, key):
                    setattr(customer, key, value)

            customer.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(customer)
            return customer

        except IntegrityError as e:
            self.db.rollback()
            if "customer_number" in str(e):
                raise ConflictError(
                    f"Customer number {update_data.get('customer_number')} already exists"
                )
            else:
                raise ConflictError("Customer update failed due to data conflict")

    def list(
        self,
        offset: int = 0,
        limit: int = 20,
        customer_type: Optional[CustomerType] = None,
        account_status: Optional[AccountStatus] = None,
        search_query: Optional[str] = None,
    ) -> List[Customer]:
        """List customers with filtering and pagination."""
        query = self.db.query(Customer).filter(
            and_(Customer.tenant_id == self.tenant_id, Customer.is_deleted == False)
        )

        # Apply filters
        if customer_type:
            query = query.filter(Customer.customer_type == customer_type.value)

        if account_status:
            query = query.filter(Customer.account_status == account_status.value)

        if search_query:
            search_term = f"%{search_query}%"
            query = query.filter(
                or_(
                    Customer.display_name.ilike(search_term),
                    Customer.customer_number.ilike(search_term),
                    Customer.email.ilike(search_term),
                    Customer.company_name.ilike(search_term),
                )
            )

        return query.offset(offset).limit(limit).all()

    def count(
        self,
        customer_type: Optional[CustomerType] = None,
        account_status: Optional[AccountStatus] = None,
        search_query: Optional[str] = None,
    ) -> int:
        """Count customers with filters."""
        query = self.db.query(func.count(Customer.id)).filter(
            and_(Customer.tenant_id == self.tenant_id, Customer.is_deleted == False)
        )

        # Apply same filters as list method
        if customer_type:
            query = query.filter(Customer.customer_type == customer_type.value)

        if account_status:
            query = query.filter(Customer.account_status == account_status.value)

        if search_query:
            search_term = f"%{search_query}%"
            query = query.filter(
                or_(
                    Customer.display_name.ilike(search_term),
                    Customer.customer_number.ilike(search_term),
                    Customer.email.ilike(search_term),
                    Customer.company_name.ilike(search_term),
                )
            )

        return query.scalar()

    def activate(self, customer_id: UUID) -> Optional[Customer]:
        """Activate customer account."""
        customer = self.get_by_id(customer_id)
        if not customer:
            return None

        if customer.account_status == AccountStatus.ACTIVE.value:
            raise ValidationError("Customer is already active")

        customer.account_status = AccountStatus.ACTIVE.value
        customer.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(customer)
        return customer

    def suspend(self, customer_id: UUID) -> Optional[Customer]:
        """Suspend customer account."""
        customer = self.get_by_id(customer_id)
        if not customer:
            return None

        if customer.account_status == AccountStatus.SUSPENDED.value:
            raise ValidationError("Customer is already suspended")

        customer.account_status = AccountStatus.SUSPENDED.value
        customer.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(customer)
        return customer

    def soft_delete(self, customer_id: UUID) -> bool:
        """Soft delete customer."""
        customer = self.get_by_id(customer_id)
        if not customer:
            return False

        customer.is_deleted = True
        customer.deleted_at = datetime.utcnow()
        customer.updated_at = datetime.utcnow()

        self.db.commit()
        return True

    def _generate_portal_id(self) -> str:
        """Generate a unique Portal ID."""
        import secrets
        import string

        max_attempts = 10
        for _ in range(max_attempts):
            # Generate 8-character alphanumeric ID
            characters = string.ascii_uppercase + string.digits
            # Exclude confusing characters: 0, O, I, 1
            characters = (
                characters.replace("0", "")
                .replace("O", "")
                .replace("I", "")
                .replace("1", "")
            )

            portal_id = "".join(secrets.choice(characters) for _ in range(8))

            # Check if this portal ID already exists
            existing = (
                self.db.query(Customer).filter(Customer.portal_id == portal_id).first()
            )
            if not existing:
                return portal_id

        raise RuntimeError("Could not generate unique portal ID after 10 attempts")


class UserRepository:
    """Repository for user database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, user_data: Dict[str, Any]) -> User:
        """Create a new user in the database."""
        try:
            user = User(id=uuid4(), tenant_id=self.tenant_id, **user_data)

            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            return user

        except IntegrityError as e:
            self.db.rollback()
            if "username" in str(e):
                raise ConflictError(
                    f"Username {user_data.get('username')} already exists"
                )
            elif "email" in str(e):
                raise ConflictError(f"Email {user_data.get('email')} already exists")
            else:
                raise ConflictError("User creation failed due to data conflict")

    def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        return (
            self.db.query(User)
            .filter(
                and_(
                    User.id == user_id,
                    User.tenant_id == self.tenant_id,
                    User.is_deleted == False,
                )
            )
            .first()
        )

    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        return (
            self.db.query(User)
            .filter(
                and_(
                    User.username == username,
                    User.tenant_id == self.tenant_id,
                    User.is_deleted == False,
                )
            )
            .first()
        )

    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return (
            self.db.query(User)
            .filter(
                and_(
                    User.email == email,
                    User.tenant_id == self.tenant_id,
                    User.is_deleted == False,
                )
            )
            .first()
        )

    def update(self, user_id: UUID, update_data: Dict[str, Any]) -> Optional[User]:
        """Update user by ID."""
        user = self.get_by_id(user_id)
        if not user:
            return None

        try:
            for key, value in update_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)

            user.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(user)
            return user

        except IntegrityError as e:
            self.db.rollback()
            if "username" in str(e):
                raise ConflictError(
                    f"Username {update_data.get('username')} already exists"
                )
            elif "email" in str(e):
                raise ConflictError(f"Email {update_data.get('email')} already exists")
            else:
                raise ConflictError("User update failed due to data conflict")

    def list(self, offset: int = 0, limit: int = 20) -> List[User]:
        """List users with pagination."""
        return (
            self.db.query(User)
            .filter(and_(User.tenant_id == self.tenant_id, User.is_deleted == False))
            .offset(offset)
            .limit(limit)
            .all()
        )

    def soft_delete(self, user_id: UUID) -> bool:
        """Soft delete user."""
        user = self.get_by_id(user_id)
        if not user:
            return False

        user.is_deleted = True
        user.deleted_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()

        self.db.commit()
        return True


class RoleRepository:
    """Repository for role database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, role_data: Dict[str, Any]) -> Role:
        """Create a new role in the database."""
        try:
            role = Role(id=uuid4(), tenant_id=self.tenant_id, **role_data)

            self.db.add(role)
            self.db.commit()
            self.db.refresh(role)
            return role

        except IntegrityError as e:
            self.db.rollback()
            if "name" in str(e):
                raise ConflictError(f"Role name {role_data.get('name')} already exists")
            else:
                raise ConflictError("Role creation failed due to data conflict")

    def get_by_id(self, role_id: UUID) -> Optional[Role]:
        """Get role by ID."""
        return (
            self.db.query(Role)
            .filter(
                and_(
                    Role.id == role_id,
                    Role.tenant_id == self.tenant_id,
                    Role.is_deleted == False,
                )
            )
            .first()
        )

    def get_by_name(self, name: str) -> Optional[Role]:
        """Get role by name."""
        return (
            self.db.query(Role)
            .filter(
                and_(
                    Role.name == name,
                    Role.tenant_id == self.tenant_id,
                    Role.is_deleted == False,
                )
            )
            .first()
        )

    def list(self) -> List[Role]:
        """List all roles."""
        return (
            self.db.query(Role)
            .filter(and_(Role.tenant_id == self.tenant_id, Role.is_deleted == False))
            .all()
        )

    def update(self, role_id: UUID, update_data: Dict[str, Any]) -> Optional[Role]:
        """Update role by ID."""
        role = self.get_by_id(role_id)
        if not role:
            return None

        try:
            for key, value in update_data.items():
                if hasattr(role, key):
                    setattr(role, key, value)

            role.updated_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(role)
            return role

        except IntegrityError as e:
            self.db.rollback()
            if "name" in str(e):
                raise ConflictError(
                    f"Role name {update_data.get('name')} already exists"
                )
            else:
                raise ConflictError("Role update failed due to data conflict")

    def soft_delete(self, role_id: UUID) -> bool:
        """Soft delete role."""
        role = self.get_by_id(role_id)
        if not role:
            return False

        role.is_deleted = True
        role.deleted_at = datetime.utcnow()
        role.updated_at = datetime.utcnow()

        self.db.commit()
        return True


class AuthTokenRepository:
    """Repository for authentication token database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, token_data: Dict[str, Any]) -> "AuthToken":
        """Create a new auth token."""
        from dotmac_isp.modules.identity.models import AuthToken

        token = AuthToken(id=uuid4(), tenant_id=self.tenant_id, **token_data)

        self.db.add(token)
        self.db.commit()
        self.db.refresh(token)
        return token

    def get_by_token_hash(self, token_hash: str) -> Optional["AuthToken"]:
        """Get token by hash."""
        from dotmac_isp.modules.identity.models import AuthToken

        return (
            self.db.query(AuthToken)
            .filter(
                and_(
                    AuthToken.token_hash == token_hash,
                    AuthToken.tenant_id == self.tenant_id,
                    AuthToken.is_revoked == False,
                )
            )
            .first()
        )

    def revoke_token(self, token_id: UUID) -> bool:
        """Revoke a specific token."""
        from dotmac_isp.modules.identity.models import AuthToken

        token = (
            self.db.query(AuthToken)
            .filter(
                and_(AuthToken.id == token_id, AuthToken.tenant_id == self.tenant_id)
            )
            .first()
        )

        if token:
            token.is_revoked = True
            token.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False

    def revoke_user_tokens(self, user_id: UUID) -> None:
        """Revoke all tokens for a user."""
        from dotmac_isp.modules.identity.models import AuthToken

        self.db.query(AuthToken).filter(
            and_(
                AuthToken.user_id == user_id,
                AuthToken.tenant_id == self.tenant_id,
                AuthToken.is_revoked == False,
            )
        ).update({"is_revoked": True, "updated_at": datetime.utcnow()})
        self.db.commit()

    def cleanup_expired_tokens(self) -> int:
        """Remove expired tokens and return count."""
        from dotmac_isp.modules.identity.models import AuthToken

        count = (
            self.db.query(AuthToken)
            .filter(
                and_(
                    AuthToken.tenant_id == self.tenant_id,
                    AuthToken.expires_at < datetime.utcnow(),
                )
            )
            .count()
        )

        self.db.query(AuthToken).filter(
            and_(
                AuthToken.tenant_id == self.tenant_id,
                AuthToken.expires_at < datetime.utcnow(),
            )
        ).delete()

        self.db.commit()
        return count


class LoginAttemptRepository:
    """Repository for login attempt database operations."""

    def __init__(self, db: Session, tenant_id: UUID):
        """  Init   operation."""
        self.db = db
        self.tenant_id = tenant_id

    def create(self, attempt_data: Dict[str, Any]) -> "LoginAttempt":
        """Create a new login attempt record."""
        from dotmac_isp.modules.identity.models import LoginAttempt

        attempt = LoginAttempt(id=uuid4(), tenant_id=self.tenant_id, **attempt_data)

        self.db.add(attempt)
        self.db.commit()
        self.db.refresh(attempt)
        return attempt

    def get_recent_attempts(
        self, username: str, minutes: int = 30
    ) -> List["LoginAttempt"]:
        """Get recent login attempts for a username."""
        from dotmac_isp.modules.identity.models import LoginAttempt

        since = datetime.utcnow() - timedelta(minutes=minutes)
        return (
            self.db.query(LoginAttempt)
            .filter(
                and_(
                    LoginAttempt.username == username,
                    LoginAttempt.tenant_id == self.tenant_id,
                    LoginAttempt.created_at >= since,
                )
            )
            .order_by(LoginAttempt.created_at.desc())
            .all()
        )

    def get_failed_attempts_count(self, username: str, minutes: int = 30) -> int:
        """Count failed login attempts for a username in recent time."""
        from dotmac_isp.modules.identity.models import LoginAttempt

        since = datetime.utcnow() - timedelta(minutes=minutes)
        return (
            self.db.query(LoginAttempt)
            .filter(
                and_(
                    LoginAttempt.username == username,
                    LoginAttempt.tenant_id == self.tenant_id,
                    LoginAttempt.success == False,
                    LoginAttempt.created_at >= since,
                )
            )
            .count()
        )

    def cleanup_old_attempts(self, days: int = 30) -> int:
        """Remove old login attempts and return count."""
        from dotmac_isp.modules.identity.models import LoginAttempt

        cutoff = datetime.utcnow() - timedelta(days=days)
        count = (
            self.db.query(LoginAttempt)
            .filter(
                and_(
                    LoginAttempt.tenant_id == self.tenant_id,
                    LoginAttempt.created_at < cutoff,
                )
            )
            .count()
        )

        self.db.query(LoginAttempt).filter(
            and_(
                LoginAttempt.tenant_id == self.tenant_id,
                LoginAttempt.created_at < cutoff,
            )
        ).delete()

        self.db.commit()
        return count
