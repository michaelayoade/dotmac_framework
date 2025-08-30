"""Identity module - Customer, user, and authentication management."""

# ARCHITECTURE IMPROVEMENT: Explicit imports replace wildcard imports
from .models import (
    AccountStatus,
    AuthToken,
    Customer,
    CustomerType,
    LoginAttempt,
    Role,
    User,
    UserRole,
)
from .repository import CustomerRepository, RoleRepository, UserRepository
from .schemas import (
    CustomerCreateAPI,
    CustomerUpdateAPI,
    RoleBase,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
    UserBase,
    UserCreate,
    UserResponse,
    UserUpdate,
)

# Import new service structure
from .services import (
    AuthService,
    CustomerService,
    IdentityOrchestrator,
    PortalService,
    UserService,
)

__all__ = [
    # New focused services
    "CustomerService",
    "UserService",
    "AuthService",
    "PortalService",
    "IdentityOrchestrator",
]
