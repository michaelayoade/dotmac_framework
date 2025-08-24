"""Identity service layer for customer and user management."""

from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from dotmac_isp.shared.base_service import BaseTenantService
from dotmac_isp.modules.identity import models, schemas
from dotmac_isp.modules.identity.portal_id_generator import get_portal_id_generator
from dotmac_isp.modules.identity.portal_service import PortalAccountService
from dotmac_isp.shared.exceptions import (
    ServiceError,
    EntityNotFoundError,
    ValidationError,
    BusinessRuleError,
    ConflictError,
)


class CustomerService(BaseTenantService[models.Customer, schemas.CustomerCreate, schemas.CustomerUpdate, schemas.CustomerResponse]):
    """Service for customer management operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(
            db=db,
            model_class=models.Customer,
            create_schema=schemas.CustomerCreate,
            update_schema=schemas.CustomerUpdate,
            response_schema=schemas.CustomerResponse,
            tenant_id=tenant_id
        )
        self.portal_service = PortalAccountService(db, tenant_id)

    async def _validate_create_rules(self, data: schemas.CustomerCreate) -> None:
        """Validate business rules for customer creation."""
        # Check for duplicate email
        if await self.repository.exists({'email': data.email}):
            raise BusinessRuleError(
                f"Customer with email {data.email} already exists",
                rule_name="unique_customer_email"
            )
        
        # Validate customer type and plan compatibility
        if data.customer_type == models.CustomerType.ENTERPRISE and not data.plan_id:
            raise ValidationError("Enterprise customers must have a plan assigned")

    async def _validate_update_rules(self, entity: models.Customer, data: schemas.CustomerUpdate) -> None:
        """Validate business rules for customer updates."""
        # Prevent status changes if customer has active services
        if data.status == models.AccountStatus.CANCELLED:
            # Check for active services (would need services module integration)
            pass

    async def _post_create_hook(self, entity: models.Customer, data: schemas.CustomerCreate) -> None:
        """Generate portal ID and create portal account after customer creation."""
        try:
            # Generate unique portal ID
            existing_portal_ids = await self._get_existing_portal_ids()
            portal_id = get_portal_id_generator().generate_portal_id(existing_portal_ids)
            
            # Update customer with portal ID
            await self.repository.update(entity.id, {'portal_id': portal_id}, commit=True)
            
            # Create portal account
            await self.portal_service.create_customer_portal_account(entity.id, portal_id)
            
        except Exception as e:
            self._logger.error(f"Failed to create portal account for customer {entity.id}: {e}")
            # Don't fail the entire customer creation, but log the issue
            pass

    async def _get_existing_portal_ids(self) -> List[str]:
        """Get all existing portal IDs to ensure uniqueness."""
        customers = await self.list(filters={})
        return [c.portal_id for c in customers if c.portal_id]


class UserService(BaseTenantService[models.User, schemas.UserCreate, schemas.UserUpdate, schemas.UserResponse]):
    """Service for user management operations."""

    def __init__(self, db: Session, tenant_id: str):
        super().__init__(
            db=db,
            model_class=models.User,
            create_schema=schemas.UserCreate,
            update_schema=schemas.UserUpdate,
            response_schema=schemas.UserResponse,
            tenant_id=tenant_id
        )

    async def _validate_create_rules(self, data: schemas.UserCreate) -> None:
        """Validate business rules for user creation."""
        # Check for duplicate username
        if await self.repository.exists({'username': data.username}):
            raise BusinessRuleError(
                f"Username {data.username} already exists",
                rule_name="unique_username"
            )
        
        # Check for duplicate email
        if await self.repository.exists({'email': data.email}):
            raise BusinessRuleError(
                f"Email {data.email} already exists", 
                rule_name="unique_user_email"
            )

    async def _validate_update_rules(self, entity: models.User, data: schemas.UserUpdate) -> None:
        """Validate business rules for user updates."""
        # Validate email uniqueness if being changed
        if data.email and data.email != entity.email:
            if await self.repository.exists({'email': data.email}):
                raise BusinessRuleError(
                    f"Email {data.email} already exists",
                    rule_name="unique_user_email"
                )

    async def _pre_create_hook(self, data: schemas.UserCreate) -> None:
        """Hash password before user creation."""
        if hasattr(data, 'password'):
            from dotmac_isp.shared.auth import hash_password
            data.password_hash = hash_password(data.password)
            # Remove plain password from data
            delattr(data, 'password')


# Legacy service for backward compatibility
class IdentityService:
    """Legacy identity service - use CustomerService and UserService instead."""

    def __init__(self, db: Session, tenant_id: str):
        self.db = db
        self.tenant_id = tenant_id
        self.customer_service = CustomerService(db, tenant_id)
        self.user_service = UserService(db, tenant_id)

    async def create_customer(
        self, customer_data: schemas.CustomerCreate
    ) -> schemas.CustomerResponse:
        """
        Create a new customer with full data validation and business rules.

        Args:
            customer_data: Customer creation data

        Returns:
            Created customer response

        Raises:
            ValidationError: Invalid customer data
            ConflictError: Customer already exists
            ServiceError: Service operation failed
        """
        try:
            # Validate business rules
            self._validate_customer_creation_sync(customer_data)

            # Generate portal ID for the customer using configurable generator
            existing_portal_ids = self._get_existing_portal_ids()
            portal_id = get_portal_id_generator().generate_portal_id(
                existing_portal_ids
            )

            # Generate secure password for the customer
            generated_password = self._generate_secure_password()

            # Prepare customer data for repository
            repo_data = {
                "customer_number": customer_data.customer_number,
                "display_name": (
                    customer_data.display_name
                    or f"{customer_data.first_name} {customer_data.last_name}"
                ),
                "customer_type": (
                    customer_data.customer_type.value
                    if hasattr(customer_data.customer_type, "value")
                    else customer_data.customer_type
                ),
                "account_status": models.AccountStatus.PENDING.value,
                "first_name": customer_data.first_name,
                "last_name": customer_data.last_name,
                "company_name": getattr(customer_data, "company_name", None),
                "email": getattr(customer_data, "email", None),
                "phone": getattr(customer_data, "phone", None),
                "portal_id": portal_id,
            }

            # Create customer in database
            db_customer = self.customer_repo.create(repo_data)

            # Create Portal Account for the customer
            try:
                portal_account = await self.portal_service.create_portal_account(
                    portal_id=portal_id,
                    password=generated_password,
                    account_type=PortalAccountType.CUSTOMER,
                    customer_id=db_customer.id,
                    force_password_change=False,  # Don't force change for generated passwords
                )

                # Activate the Portal Account immediately for new customers
                await self.portal_service.activate_portal_account(portal_id)

            except Exception as e:
                # Log error but don't fail customer creation
                import logging

                logging.warning(f"Failed to create Portal Account for {portal_id}: {e}")

            # Convert customer_type string to enum for response
            customer_type_enum = (
                models.CustomerType(customer_data.customer_type)
                if isinstance(customer_data.customer_type, str)
                else customer_data.customer_type
            )

            return self._build_customer_response_from_db(
                db_customer, customer_type_enum, generated_password
            )

        except ValidationError:
            raise
        except ConflictError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to create customer: {str(e)}")

    async def get_customer(self, customer_id: UUID) -> schemas.CustomerResponse:
        """
        Get customer by ID with full data enrichment.

        Args:
            customer_id: Customer identifier

        Returns:
            Customer response with enriched data

        Raises:
            NotFoundError: Customer not found
            ServiceError: Service operation failed
        """
        try:
            sdk_customer = await self.sdk_registry.customers.get_customer(customer_id)

            if not sdk_customer:
                raise NotFoundError(f"Customer {customer_id} not found")

            return self._build_customer_response_from_sdk(sdk_customer)

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to get customer: {str(e)}")

    async def update_customer(
        self, customer_id: UUID, customer_data: schemas.CustomerUpdate
    ) -> schemas.CustomerResponse:
        """
        Update customer with validation and business rules.

        Args:
            customer_id: Customer identifier
            customer_data: Update data

        Returns:
            Updated customer response

        Raises:
            NotFoundError: Customer not found
            ValidationError: Invalid update data
            ServiceError: Service operation failed
        """
        try:
            # Validate update data
            await self._validate_customer_update(customer_id, customer_data)

            # Convert to SDK update schema
            sdk_updates = CustomerUpdate(
                display_name=customer_data.display_name,
                customer_type=(
                    (
                        customer_data.customer_type.value
                        if hasattr(customer_data.customer_type, "value")
                        else customer_data.customer_type
                    )
                    if customer_data.customer_type
                    else None
                ),
                tags=getattr(customer_data, "tags", None),
                custom_fields=getattr(customer_data, "custom_fields", None),
            )

            # Update customer using SDK
            updated_customer = await self.sdk_registry.customers.update_customer(
                customer_id, sdk_updates
            )

            if not updated_customer:
                raise NotFoundError(f"Customer {customer_id} not found")

            return self._build_customer_response_from_sdk(updated_customer)

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            raise ServiceError(f"Failed to update customer: {str(e)}")

    async def list_customers(
        self,
        filters: Optional[schemas.CustomerFilters] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[schemas.CustomerResponse]:
        """
        List customers with filtering and pagination.

        Args:
            filters: Optional customer filters
            limit: Maximum number of results
            offset: Results offset

        Returns:
            List of customer responses

        Raises:
            ServiceError: Service operation failed
        """
        try:
            # Convert filters to SDK format
            sdk_filters = CustomerListFilters(
                customer_type=(
                    (
                        filters.customer_type.value
                        if hasattr(filters.customer_type, "value")
                        else filters.customer_type
                    )
                    if filters and filters.customer_type
                    else None
                ),
                state=(
                    filters.account_status.value
                    if filters and filters.account_status
                    else None
                ),
                limit=limit,
                offset=offset,
            )

            # Get customers from SDK
            sdk_customers = await self.sdk_registry.customers.list_customers(
                sdk_filters
            )

            # Convert to API responses
            return [
                self._build_customer_response_from_sdk(customer)
                for customer in sdk_customers
            ]

        except Exception as e:
            raise ServiceError(f"Failed to list customers: {str(e)}")

    async def activate_customer(self, customer_id: UUID) -> schemas.CustomerResponse:
        """
        Activate customer account.

        Args:
            customer_id: Customer identifier

        Returns:
            Updated customer response

        Raises:
            NotFoundError: Customer not found
            ValidationError: Customer cannot be activated
            ServiceError: Service operation failed
        """
        try:
            # Validate activation is allowed
            await self._validate_customer_activation(customer_id)

            # Activate customer using SDK
            activated_customer = await self.sdk_registry.customers.activate_customer(
                customer_id
            )

            if not activated_customer:
                raise NotFoundError(f"Customer {customer_id} not found")

            return self._build_customer_response_from_sdk(activated_customer)

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            raise ServiceError(f"Failed to activate customer: {str(e)}")

    async def suspend_customer(self, customer_id: UUID) -> schemas.CustomerResponse:
        """
        Suspend customer account.

        Args:
            customer_id: Customer identifier

        Returns:
            Updated customer response

        Raises:
            NotFoundError: Customer not found
            ValidationError: Customer cannot be suspended
            ServiceError: Service operation failed
        """
        try:
            # Validate suspension is allowed
            await self._validate_customer_suspension(customer_id)

            # Suspend customer using SDK
            suspended_customer = await self.sdk_registry.customers.suspend_customer(
                customer_id
            )

            if not suspended_customer:
                raise NotFoundError(f"Customer {customer_id} not found")

            return self._build_customer_response_from_sdk(suspended_customer)

        except (NotFoundError, ValidationError):
            raise
        except Exception as e:
            raise ServiceError(f"Failed to suspend customer: {str(e)}")

    # Private helper methods
    async def _validate_customer_creation(
        self, customer_data: schemas.CustomerCreate
    ) -> None:
        """Validate customer creation business rules."""
        # Check if customer number already exists
        if customer_data.customer_number:
            existing = await self._check_customer_number_exists(
                customer_data.customer_number
            )
            if existing:
                raise ConflictError(
                    f"Customer number {customer_data.customer_number} already exists"
                )

        # Note: Email is not unique across customers as per user requirements

    async def _validate_customer_update(
        self, customer_id: UUID, customer_data: schemas.CustomerUpdate
    ) -> None:
        """Validate customer update business rules."""
        # Ensure customer exists
        existing = await self.sdk_registry.customers.get_customer(customer_id)
        if not existing:
            raise NotFoundError(f"Customer {customer_id} not found")

        # Note: Email is not unique across customers as per user requirements

    async def _validate_customer_activation(self, customer_id: UUID) -> None:
        """Validate customer can be activated."""
        customer = await self.sdk_registry.customers.get_customer(customer_id)
        if not customer:
            raise NotFoundError(f"Customer {customer_id} not found")

        if customer.state == "active":
            raise ValidationError("Customer is already active")

    async def _validate_customer_suspension(self, customer_id: UUID) -> None:
        """Validate customer can be suspended."""
        customer = await self.sdk_registry.customers.get_customer(customer_id)
        if not customer:
            raise NotFoundError(f"Customer {customer_id} not found")

        if customer.state == "suspended":
            raise ValidationError("Customer is already suspended")

    async def _check_customer_number_exists(self, customer_number: str) -> bool:
        """Check if customer number already exists."""
        try:
            filters = CustomerListFilters(limit=1, offset=0)
            customers = await self.sdk_registry.customers.list_customers(filters)
            return any(c.customer_number == customer_number for c in customers)
        except Exception:
            return False

    async def _check_customer_email_exists(
        self, email: str, exclude_id: Optional[UUID] = None
    ) -> bool:
        """Check if customer email already exists."""
        try:
            filters = CustomerListFilters(limit=100, offset=0)
            customers = await self.sdk_registry.customers.list_customers(filters)
            for customer in customers:
                if (
                    customer.custom_fields.get("email") == email
                    and customer.customer_id != exclude_id
                ):
                    return True
            return False
        except Exception:
            return False

    def _get_existing_portal_ids(self) -> set:
        """Get set of existing Portal IDs to avoid duplicates."""
        try:
            # Get all customers to check for existing Portal IDs
            customers = self.customer_repo.list(
                limit=10000
            )  # Get all existing customers
            return {customer.portal_id for customer in customers if customer.portal_id}
        except Exception:
            return set()  # Return empty set if unable to fetch

    def get_portal_id_configuration(self) -> dict:
        """Get current Portal ID generation configuration."""
        return get_portal_id_generator().get_configuration_summary()

    def _generate_secure_password(self) -> str:
        """Generate a secure, memorable password for Portal accounts.

        Format: WordWordNumber! (e.g., "BlueSky47!")
        This is more user-friendly while maintaining security.
        """
        import secrets

        # Common words for password generation (avoiding offensive terms)
        words = [
            "Blue",
            "Green",
            "Red",
            "Gold",
            "Silver",
            "Bright",
            "Clear",
            "Fresh",
            "Quick",
            "Swift",
            "Strong",
            "Smart",
            "Cool",
            "Warm",
            "Light",
            "Dark",
            "Sky",
            "Star",
            "Moon",
            "Sun",
            "Wave",
            "Wind",
            "Fire",
            "Rain",
            "Oak",
            "Pine",
            "Rose",
            "Lily",
            "Tiger",
            "Eagle",
            "Wolf",
            "Bear",
            "River",
            "Ocean",
            "Lake",
            "Hill",
            "Rock",
            "Peak",
            "Valley",
            "Field",
        ]

        # Select two random words
        word1 = secrets.choice(words)
        word2 = secrets.choice(
            [w for w in words if w != word1]
        )  # Ensure different words

        # Generate 2-digit number
        number = secrets.randbelow(90) + 10  # 10-99

        # Add special character
        special_chars = "!@#$%"
        special = secrets.choice(special_chars)

        return f"{word1}{word2}{number}{special}"

    def _build_customer_response(
        self,
        sdk_customer: CustomerResponse,
        original_data: schemas.CustomerCreate,
        customer_type_enum: Optional[models.CustomerType] = None,
        portal_id: Optional[str] = None,
        portal_password: Optional[str] = None,
    ) -> schemas.CustomerResponse:
        """Build customer response from SDK response and original data."""
        return schemas.CustomerResponse(
            id=sdk_customer.customer_id,  # Keep UUID as id
            portal_id=portal_id or "TEMP-ID",  # Primary portal identifier (string)
            portal_password=portal_password,  # Include generated password
            customer_id=sdk_customer.customer_id,
            customer_number=sdk_customer.customer_number,
            display_name=sdk_customer.display_name,
            customer_type=customer_type_enum
            or models.CustomerType(original_data.customer_type),
            customer_segment=sdk_customer.customer_segment,
            state=sdk_customer.state,
            account_status=models.AccountStatus.PENDING,
            first_name=getattr(original_data, "first_name", None),
            last_name=getattr(original_data, "last_name", None),
            company_name=getattr(original_data, "company_name", None),
            email=getattr(original_data, "email", None),
            phone=getattr(original_data, "phone", None),
            tags=sdk_customer.tags,
            custom_fields=sdk_customer.custom_fields,
            created_at=sdk_customer.created_at,
            updated_at=sdk_customer.updated_at,
            tenant_id=uuid4(),  # Generate UUID for tenant_id
        )

    def _build_customer_response_from_sdk(
        self, sdk_customer: CustomerResponse
    ) -> schemas.CustomerResponse:
        """Build customer response from SDK response only."""
        return schemas.CustomerResponse(
            id=sdk_customer.customer_id,
            customer_id=sdk_customer.customer_id,
            customer_number=sdk_customer.customer_number,
            display_name=sdk_customer.display_name,
            customer_type=models.CustomerType(sdk_customer.customer_type),
            customer_segment=sdk_customer.customer_segment,
            state=sdk_customer.state,
            account_status=models.AccountStatus(sdk_customer.state),
            tags=sdk_customer.tags,
            custom_fields=sdk_customer.custom_fields,
            created_at=sdk_customer.created_at,
            updated_at=sdk_customer.updated_at,
            prospect_date=sdk_customer.prospect_date,
            activation_date=sdk_customer.activation_date,
            churn_date=sdk_customer.churn_date,
            monthly_recurring_revenue=sdk_customer.monthly_recurring_revenue,
            lifetime_value=sdk_customer.lifetime_value,
            tenant_id=uuid4(),  # Generate UUID for tenant_id
        )

    def _build_customer_response_from_db(
        self,
        db_customer: models.Customer,
        customer_type_enum: models.CustomerType,
        portal_password: Optional[str] = None,
    ) -> schemas.CustomerResponse:
        """Build customer response from database model."""
        return schemas.CustomerResponse(
            id=db_customer.id,
            portal_id=db_customer.portal_id,
            portal_password=portal_password,
            customer_id=db_customer.id,
            customer_number=db_customer.customer_number,
            display_name=db_customer.display_name,
            customer_type=customer_type_enum,
            customer_segment="basic",  # Default segment
            state="active",  # Default state
            account_status=models.AccountStatus(db_customer.account_status),
            first_name=db_customer.first_name,
            last_name=db_customer.last_name,
            company_name=db_customer.company_name,
            email=db_customer.email,
            phone=db_customer.phone,
            tags=[],  # Default empty tags
            custom_fields={},  # Default empty custom fields
            created_at=db_customer.created_at,
            updated_at=db_customer.updated_at,
            tenant_id=db_customer.tenant_id,
        )

    def _validate_customer_creation_sync(
        self, customer_data: schemas.CustomerCreate
    ) -> None:
        """Validate customer creation business rules (synchronous)."""
        # Check if customer number already exists
        if customer_data.customer_number:
            existing = self.customer_repo.get_by_customer_number(
                customer_data.customer_number
            )
            if existing:
                raise ConflictError(
                    f"Customer number {customer_data.customer_number} already exists"
                )

        # Note: Email is not unique across customers as per user requirements


class UserService:
    """Service layer for user management operations."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize user service with database session."""
        self.db = db
        self.settings = get_settings()
        self.tenant_id = UUID(tenant_id) if tenant_id else UUID(self.settings.tenant_id)
        self.user_repo = UserRepository(db, self.tenant_id)
        self.role_repo = RoleRepository(db, self.tenant_id)

    async def create_user(self, user_data: schemas.UserCreate) -> schemas.UserResponse:
        """Create a new user."""
        try:
            # Check if username already exists
            existing_user = self.user_repo.get_by_username(user_data.username)
            if existing_user:
                raise ConflictError(f"Username {user_data.username} already exists")

            # Check if email already exists
            existing_email = self.user_repo.get_by_email(user_data.email)
            if existing_email:
                raise ConflictError(f"Email {user_data.email} already exists")

            # Hash password
            password_hash = self._hash_password(user_data.password)

            # Create user data
            create_data = {
                "username": user_data.username,
                "email": user_data.email,
                "password_hash": password_hash,
                "first_name": user_data.first_name,
                "last_name": user_data.last_name,
                "timezone": user_data.timezone,
                "language": user_data.language,
                "is_active": True,
                "is_verified": False,
            }

            # Create user
            user = self.user_repo.create(create_data)

            # Assign roles if provided
            if user_data.role_ids:
                for role_id in user_data.role_ids:
                    role = self.role_repo.get_by_id(role_id)
                    if role:
                        # Add role to user's roles collection
                        user.roles.append(role)
                
                # Commit the role assignments
                self.db.commit()
                self.db.refresh(user)

            return self._build_user_response(user)

        except (ConflictError, ValidationError):
            raise
        except Exception as e:
            raise ServiceError(f"Failed to create user: {str(e)}")

    async def get_user(self, user_id: UUID) -> schemas.UserResponse:
        """Get user by ID."""
        try:
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User {user_id} not found")

            return self._build_user_response(user)

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to get user: {str(e)}")

    async def update_user(
        self, user_id: UUID, user_data: schemas.UserUpdate
    ) -> schemas.UserResponse:
        """Update user."""
        try:
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User {user_id} not found")

            # Check for username conflicts if username is being updated
            if user_data.username and user_data.username != user.username:
                existing_user = self.user_repo.get_by_username(user_data.username)
                if existing_user:
                    raise ConflictError(f"Username {user_data.username} already exists")

            # Check for email conflicts if email is being updated
            if user_data.email and user_data.email != user.email:
                existing_email = self.user_repo.get_by_email(user_data.email)
                if existing_email:
                    raise ConflictError(f"Email {user_data.email} already exists")

            # Build update data
            update_dict = {}
            for field in [
                "username",
                "email",
                "first_name",
                "last_name",
                "timezone",
                "language",
                "is_active",
            ]:
                value = getattr(user_data, field, None)
                if value is not None:
                    update_dict[field] = value

            # Update user
            updated_user = self.user_repo.update(user_id, update_dict)

            # Handle role updates if provided
            if user_data.role_ids is not None:
                # Clear existing roles
                updated_user.roles.clear()
                
                # Add new roles
                for role_id in user_data.role_ids:
                    role = self.role_repo.get_by_id(role_id)
                    if role:
                        updated_user.roles.append(role)
                
                # Commit the role changes
                self.db.commit()
                self.db.refresh(updated_user)

            return self._build_user_response(updated_user)

        except (NotFoundError, ConflictError, ValidationError):
            raise
        except Exception as e:
            raise ServiceError(f"Failed to update user: {str(e)}")

    async def delete_user(self, user_id: UUID) -> None:
        """Delete user."""
        try:
            user = self.user_repo.get_by_id(user_id)
            if not user:
                raise NotFoundError(f"User {user_id} not found")

            # Soft delete user
            success = self.user_repo.soft_delete(user_id)
            if not success:
                raise ServiceError("Failed to delete user")

        except NotFoundError:
            raise
        except Exception as e:
            raise ServiceError(f"Failed to delete user: {str(e)}")

    async def list_users(
        self, limit: int = 20, offset: int = 0
    ) -> List[schemas.UserResponse]:
        """List users with pagination."""
        try:
            users = self.user_repo.list(offset=offset, limit=limit)
            return [self._build_user_response(user) for user in users]

        except Exception as e:
            raise ServiceError(f"Failed to list users: {str(e)}")

    def _build_user_response(self, user: models.User) -> schemas.UserResponse:
        """Build user response from database model."""
        return schemas.UserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone_primary=getattr(user, "phone_primary", None),
            phone_secondary=getattr(user, "phone_secondary", None),
            timezone=user.timezone,
            language=user.language,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login=user.last_login,
            avatar_url=user.avatar_url,
            roles=[
                {
                    "id": role.id,
                    "name": role.name,
                    "description": role.description,
                    "is_system_role": role.is_system_role,
                }
                for role in user.roles
            ],
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        import bcrypt

        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        import bcrypt

        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


class AuthService:
    """Service layer for authentication operations."""

    def __init__(self, db: Session, tenant_id: Optional[str] = None):
        """Initialize auth service with database session."""
        self.db = db
        self.settings = get_settings()
        self.tenant_id = UUID(tenant_id) if tenant_id else UUID(self.settings.tenant_id)
        self.user_repo = UserRepository(db, self.tenant_id)
        self.token_repo = AuthTokenRepository(db, self.tenant_id)
        self.login_attempt_repo = LoginAttemptRepository(db, self.tenant_id)

    async def login(
        self,
        login_data: schemas.LoginRequest,
        ip_address: str = None,
        user_agent: str = None,
    ) -> schemas.LoginResponse:
        """Authenticate user and return tokens."""
        try:
            # Find user by username or email
            user = self.user_repo.get_by_username(login_data.username)
            if not user:
                user = self.user_repo.get_by_email(login_data.username)

            # Log login attempt
            await self._log_login_attempt(
                login_data.username,
                ip_address,
                user_agent,
                success=False,
                user_id=user.id if user else None,
            )

            if not user:
                raise ValidationError("Invalid username or password")

            # Check if user is active
            if not user.is_active:
                raise ValidationError("Account is deactivated")

            # Check if user is locked
            if user.is_locked:
                raise ValidationError("Account is temporarily locked")

            # Verify password
            if not self._verify_password(login_data.password, user.password_hash):
                # Increment failed attempts
                await self._handle_failed_login(user)
                raise ValidationError("Invalid username or password")

            # Reset failed attempts on successful login
            await self._reset_failed_attempts(user)

            # Generate tokens
            access_token = self._generate_jwt_token(user, "access")
            refresh_token = self._generate_jwt_token(user, "refresh")

            # Store tokens
            await self._store_tokens(
                user, access_token, refresh_token, ip_address, user_agent
            )

            # Update last login
            await self._update_last_login(user)

            # Log successful attempt
            await self._log_login_attempt(
                login_data.username,
                ip_address,
                user_agent,
                success=True,
                user_id=user.id,
            )

            return schemas.LoginResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                expires_in=3600,  # 1 hour
                user=self._build_user_response(user),
            )

        except ValidationError:
            raise
        except Exception as e:
            raise ServiceError(f"Login failed: {str(e)}")

    async def refresh_token(
        self, refresh_data: schemas.TokenRefreshRequest
    ) -> schemas.LoginResponse:
        """Refresh access token."""
        try:
            # Validate refresh token
            payload = self._decode_jwt_token(refresh_data.refresh_token)
            if payload.get("token_type") != "refresh":
                raise ValidationError("Invalid token type")

            user_id = payload.get("user_id")
            if not user_id:
                raise ValidationError("Invalid token")

            # Get user
            user = self.user_repo.get_by_id(UUID(user_id))
            if not user or not user.is_active:
                raise ValidationError("User not found or inactive")

            # Check if refresh token exists and is valid
            token_hash = self._hash_token(refresh_data.refresh_token)
            stored_token = self.token_repo.get_by_token_hash(token_hash)
            if not stored_token or not stored_token.is_valid:
                raise ValidationError("Invalid or expired refresh token")

            # Generate new tokens
            new_access_token = self._generate_jwt_token(user, "access")
            new_refresh_token = self._generate_jwt_token(user, "refresh")

            # Revoke old refresh token
            self.token_repo.revoke_token(stored_token.id)

            # Store new tokens
            await self._store_tokens(user, new_access_token, new_refresh_token)

            return schemas.LoginResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                token_type="bearer",
                expires_in=3600,
                user=self._build_user_response(user),
            )

        except ValidationError:
            raise
        except Exception as e:
            raise ServiceError(f"Token refresh failed: {str(e)}")

    async def logout(self, token: str) -> None:
        """Logout user and invalidate tokens."""
        try:
            # Decode token to get user info
            payload = self._decode_jwt_token(token)
            user_id = payload.get("user_id")

            if user_id:
                # Revoke all tokens for this user
                self.token_repo.revoke_user_tokens(UUID(user_id))

        except Exception as e:
            # Log error but don't fail logout
            import logging

            logging.warning(f"Error during logout: {e}")

    async def request_password_reset(
        self, reset_data: schemas.PasswordResetRequest
    ) -> None:
        """Request password reset."""
        try:
            # Find user by email
            user = self.user_repo.get_by_email(reset_data.email)
            if not user:
                # Don't reveal if email exists or not for security
                return

            # Generate reset token
            reset_token = self._generate_jwt_token(
                user, "reset", expires_in=3600
            )  # 1 hour

            # Store reset token
            token_hash = self._hash_token(reset_token)
            token_data = {
                "user_id": user.id,
                "token_hash": token_hash,
                "token_type": "reset",
                "expires_at": datetime.utcnow() + timedelta(hours=1),
            }
            self.token_repo.create(token_data)

            # Send password reset email
            from dotmac_isp.core.tasks import send_email_notification
            
            # Prepare email context
            reset_link = f"https://portal.example.com/reset-password?token={reset_token}"
            
            email_context = {
                "user_name": user.first_name or user.username,
                "reset_link": reset_link,
                "reset_token": reset_token,
                "expires_in": "1 hour",
                "company_name": "DotMac ISP",
            }
            
            # Send email asynchronously
            send_email_notification.delay(
                recipient=user.email,
                subject="Password Reset Request - DotMac ISP",
                template="password_reset",
                context=email_context,
            )
            
            # Also log for debugging (remove in production)
            import logging
            logging.info(f"Password reset email sent to {reset_data.email}")

        except Exception as e:
            # Log error but don't expose to user for security
            import logging

            logging.error(f"Password reset request failed: {e}")

    async def confirm_password_reset(
        self, confirm_data: schemas.PasswordResetConfirm
    ) -> None:
        """Confirm password reset."""
        try:
            # Validate reset token
            payload = self._decode_jwt_token(confirm_data.token)
            if payload.get("token_type") != "reset":
                raise ValidationError("Invalid token type")

            user_id = payload.get("user_id")
            if not user_id:
                raise ValidationError("Invalid token")

            # Get user
            user = self.user_repo.get_by_id(UUID(user_id))
            if not user:
                raise ValidationError("User not found")

            # Check if reset token exists and is valid
            token_hash = self._hash_token(confirm_data.token)
            stored_token = self.token_repo.get_by_token_hash(token_hash)
            if (
                not stored_token
                or not stored_token.is_valid
                or stored_token.token_type != "reset"
            ):
                raise ValidationError("Invalid or expired reset token")

            # Update password
            new_password_hash = self._hash_password(confirm_data.new_password)
            self.user_repo.update(user.id, {"password_hash": new_password_hash})

            # Revoke the reset token
            self.token_repo.revoke_token(stored_token.id)

            # Revoke all existing auth tokens for security
            self.token_repo.revoke_user_tokens(user.id)

        except ValidationError:
            raise
        except Exception as e:
            raise ServiceError(f"Password reset confirmation failed: {str(e)}")

    # Helper methods for JWT and authentication
    def _generate_jwt_token(
        self, user: models.User, token_type: str, expires_in: int = None
    ) -> str:
        """Generate JWT token."""
        import jwt
        from datetime import timedelta

        if expires_in is None:
            expires_in = (
                3600
                if token_type == "access"
                else 86400 if token_type == "refresh" else 3600
            )

        payload = {
            "user_id": str(user.id),
            "username": user.username,
            "token_type": token_type,
            "exp": datetime.utcnow() + timedelta(seconds=expires_in),
            "iat": datetime.utcnow(),
            "tenant_id": str(user.tenant_id),
        }

        # Use a secret key (in production, this should be from environment)
        secret_key = getattr(self.settings, "jwt_secret_key", "your-secret-key")
        return jwt.encode(payload, secret_key, algorithm="HS256")

    def _decode_jwt_token(self, token: str) -> dict:
        """Decode JWT token."""
        import jwt

        secret_key = getattr(self.settings, "jwt_secret_key", "your-secret-key")
        try:
            return jwt.decode(token, secret_key, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            raise ValidationError("Token has expired")
        except jwt.InvalidTokenError:
            raise ValidationError("Invalid token")

    def _hash_token(self, token: str) -> str:
        """Hash token for storage."""
        import hashlib

        return hashlib.sha256(token.encode()).hexdigest()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        import bcrypt

        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), password_hash.encode("utf-8")
            )
        except Exception:
            return False

    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        import bcrypt

        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def _build_user_response(self, user: models.User) -> schemas.UserResponse:
        """Build user response from database model."""
        return schemas.UserResponse(
            id=user.id,
            tenant_id=user.tenant_id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            phone_primary=getattr(user, "phone_primary", None),
            phone_secondary=getattr(user, "phone_secondary", None),
            timezone=user.timezone,
            language=user.language,
            is_active=user.is_active,
            is_verified=user.is_verified,
            last_login=user.last_login,
            avatar_url=user.avatar_url,
            roles=[
                {
                    "id": role.id,
                    "name": role.name,
                    "description": role.description,
                    "is_system_role": role.is_system_role,
                }
                for role in user.roles
            ],
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def _store_tokens(
        self,
        user: models.User,
        access_token: str,
        refresh_token: str,
        ip_address: str = None,
        user_agent: str = None,
    ):
        """Store tokens in database."""
        tokens = [
            {
                "user_id": user.id,
                "token_hash": self._hash_token(access_token),
                "token_type": "access",
                "expires_at": datetime.utcnow() + timedelta(hours=1),
                "ip_address": ip_address,
                "user_agent": user_agent,
            },
            {
                "user_id": user.id,
                "token_hash": self._hash_token(refresh_token),
                "token_type": "refresh",
                "expires_at": datetime.utcnow() + timedelta(days=7),
                "ip_address": ip_address,
                "user_agent": user_agent,
            },
        ]

        for token_data in tokens:
            self.token_repo.create(token_data)

    async def _log_login_attempt(
        self,
        username: str,
        ip_address: str,
        user_agent: str,
        success: bool,
        user_id: UUID = None,
        failure_reason: str = None,
    ):
        """Log login attempt."""
        attempt_data = {
            "username": username,
            "ip_address": ip_address or "unknown",
            "user_agent": user_agent,
            "success": success,
            "user_id": user_id,
            "failure_reason": failure_reason,
        }
        self.login_attempt_repo.create(attempt_data)

    async def _handle_failed_login(self, user: models.User):
        """Handle failed login attempt."""
        failed_attempts = int(user.failed_login_attempts) + 1
        update_data = {"failed_login_attempts": str(failed_attempts)}

        # Lock account after 5 failed attempts for 30 minutes
        if failed_attempts >= 5:
            update_data["locked_until"] = datetime.utcnow() + timedelta(minutes=30)

        self.user_repo.update(user.id, update_data)

    async def _reset_failed_attempts(self, user: models.User):
        """Reset failed login attempts."""
        self.user_repo.update(
            user.id, {"failed_login_attempts": "0", "locked_until": None}
        )

    async def _update_last_login(self, user: models.User):
        """Update user's last login timestamp."""
        self.user_repo.update(user.id, {"last_login": datetime.utcnow()})
