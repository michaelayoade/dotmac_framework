"""
Production-ready API layer for user management with multi-app support.
Leverages RouterFactory for DRY patterns and includes tenant super admin capabilities.
"""

from .user_router import *
from .auth_router import *
from .tenant_admin_router import *

__all__ = [
    # User management routers
    "user_router",
    "profile_router", 
    "admin_router",
    
    # Authentication routers
    "auth_router",
    "session_router",
    "mfa_router",
    
    # Multi-app tenant administration
    "tenant_admin_router",
]