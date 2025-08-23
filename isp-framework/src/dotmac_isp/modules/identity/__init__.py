"""Identity module - Customer, user, and authentication management."""

# ARCHITECTURE IMPROVEMENT: Explicit imports replace wildcard imports
from .models import (
    UserRole, CustomerType, AccountStatus,
    User, Role, Customer, AuthToken, LoginAttempt
)
from .schemas import (
    UserBase, UserCreate, UserUpdate, UserResponse,
    RoleBase, RoleCreate, RoleUpdate, RoleResponse, 
    CustomerCreateAPI, CustomerUpdateAPI
)
from .repository import CustomerRepository, UserRepository, RoleRepository

# Import new service structure
from .services import (
    CustomerService,
    UserService,
    AuthService,
    PortalService,
    IdentityOrchestrator,
)

__all__ = [
    # New focused services
    "CustomerService",
    "UserService",
    "AuthService",
    "PortalService",
    "IdentityOrchestrator",
]
