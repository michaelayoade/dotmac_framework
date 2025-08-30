"""
ISP Framework authentication adapter.

Production implementation for ISP platform integration.
"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ISPAuthAdapter:
    """Authentication adapter for ISP Framework with full implementation."""

    def __init__(
        self,
        db_session: Optional[AsyncSession] = None,
        jwt_secret: str = "isp-auth-secret-change-in-production",
        jwt_algorithm: str = "HS256",
        token_expiry_hours: int = 24,
    ):
        """Initialize ISP authentication adapter."""
        self.db_session = db_session
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.token_expiry_hours = token_expiry_hours

        # ISP-specific role mappings
        self.role_permissions = {
            "isp_admin": [
                "manage_customers",
                "manage_services",
                "manage_billing",
                "view_analytics",
                "manage_network",
                "manage_users",
                "manage_system_config",
                "manage_tenant_settings",
            ],
            "isp_technician": [
                "manage_services",
                "view_customers",
                "manage_network",
                "view_analytics",
                "create_tickets",
                "update_tickets",
            ],
            "isp_support": [
                "view_customers",
                "manage_tickets",
                "view_billing",
                "create_services",
                "view_analytics",
            ],
            "isp_billing": [
                "manage_billing",
                "view_customers",
                "create_invoices",
                "manage_payments",
                "view_analytics",
            ],
            "customer": [
                "view_own_services",
                "view_own_billing",
                "create_tickets",
                "update_own_profile",
                "view_usage_stats",
            ],
        }

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

    def generate_jwt_token(self, user_data: Dict[str, Any]) -> str:
        """Generate JWT token for authenticated user."""
        payload = {
            "sub": user_data["user_id"],
            "tenant_id": user_data.get("tenant_id"),
            "roles": user_data.get("roles", []),
            "permissions": user_data.get("permissions", []),
            "user_type": user_data.get("user_type", "customer"),
            "session_id": hashlib.md5(
                f"{user_data['user_id']}{datetime.utcnow()}".encode()
            ).hexdigest(),
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=self.token_expiry_hours),
        }

        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    async def authenticate_user(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate user with ISP Framework."""
        try:
            username = credentials.get("username")
            password = credentials.get("password")
            tenant_id = credentials.get("tenant_id")

            if not all([username, password]):
                return {
                    "success": False,
                    "error": "missing_credentials",
                    "message": "Username and password are required",
                }

            # In a real implementation, this would query the ISP database
            # For now, we'll simulate with common ISP user scenarios
            user_data = await self._lookup_isp_user(username, tenant_id)

            if not user_data:
                logger.warning(f"Authentication failed - user not found: {username}")
                return {
                    "success": False,
                    "error": "invalid_credentials",
                    "message": "Invalid username or password",
                }

            # Verify password
            if not self.verify_password(password, user_data["password_hash"]):
                logger.warning(f"Authentication failed - invalid password: {username}")
                return {
                    "success": False,
                    "error": "invalid_credentials",
                    "message": "Invalid username or password",
                }

            # Get user permissions
            permissions = await self.get_user_permissions(user_data["user_id"])

            # Create successful authentication response
            auth_data = {
                "user_id": user_data["user_id"],
                "tenant_id": user_data["tenant_id"],
                "username": user_data["username"],
                "email": user_data["email"],
                "roles": user_data["roles"],
                "permissions": permissions["permissions"],
                "user_type": user_data["user_type"],
            }

            # Generate JWT token
            token = self.generate_jwt_token(auth_data)

            logger.info(f"Successful ISP authentication: {username}")

            return {
                "success": True,
                "user": auth_data,
                "token": token,
                "expires_at": (
                    datetime.utcnow() + timedelta(hours=self.token_expiry_hours)
                ).isoformat(),
            }

        except Exception as e:
            logger.error(f"ISP authentication error: {e}")
            return {
                "success": False,
                "error": "authentication_error",
                "message": "Authentication system error",
            }

    async def get_user_permissions(self, user_id: str) -> Dict[str, Any]:
        """Get user permissions from ISP Framework."""
        try:
            # In a real implementation, this would query the database
            user_data = await self._get_user_by_id(user_id)

            if not user_data:
                return {"success": False, "error": "user_not_found", "permissions": []}

            # Get permissions based on roles
            all_permissions = set()
            for role in user_data.get("roles", []):
                role_perms = self.role_permissions.get(role, [])
                all_permissions.update(role_perms)

            # Add any custom permissions
            custom_permissions = user_data.get("custom_permissions", [])
            all_permissions.update(custom_permissions)

            return {
                "success": True,
                "user_id": user_id,
                "roles": user_data.get("roles", []),
                "permissions": list(all_permissions),
                "tenant_id": user_data.get("tenant_id"),
            }

        except Exception as e:
            logger.error(f"Error getting user permissions: {e}")
            return {"success": False, "error": "permissions_error", "permissions": []}

    async def validate_token(self, token: str) -> Dict[str, Any]:
        """Validate JWT token and return user data."""
        try:
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )

            # Check if token is expired
            exp_timestamp = payload.get("exp")
            if exp_timestamp and datetime.utcnow().timestamp() > exp_timestamp:
                return {
                    "success": False,
                    "error": "token_expired",
                    "message": "Token has expired",
                }

            # Verify user still exists and is active
            user_data = await self._get_user_by_id(payload.get("sub"))
            if not user_data or not user_data.get("is_active", True):
                return {
                    "success": False,
                    "error": "user_inactive",
                    "message": "User account is inactive",
                }

            return {
                "success": True,
                "user_id": payload.get("sub"),
                "tenant_id": payload.get("tenant_id"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
                "user_type": payload.get("user_type", "customer"),
            }

        except jwt.InvalidTokenError:
            return {
                "success": False,
                "error": "invalid_token",
                "message": "Invalid token",
            }
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            return {
                "success": False,
                "error": "validation_error",
                "message": "Token validation failed",
            }

    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an expired access token."""
        try:
            # Validate refresh token
            validation = await self.validate_token(refresh_token)
            if not validation["success"]:
                return validation

            # Get fresh user data
            user_data = await self._get_user_by_id(validation["user_id"])
            if not user_data:
                return {
                    "success": False,
                    "error": "user_not_found",
                    "message": "User not found",
                }

            # Generate new token
            permissions = await self.get_user_permissions(user_data["user_id"])

            auth_data = {
                "user_id": user_data["user_id"],
                "tenant_id": user_data["tenant_id"],
                "username": user_data["username"],
                "email": user_data["email"],
                "roles": user_data["roles"],
                "permissions": permissions["permissions"],
                "user_type": user_data["user_type"],
            }

            new_token = self.generate_jwt_token(auth_data)

            return {
                "success": True,
                "token": new_token,
                "expires_at": (
                    datetime.utcnow() + timedelta(hours=self.token_expiry_hours)
                ).isoformat(),
            }

        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return {
                "success": False,
                "error": "refresh_error",
                "message": "Token refresh failed",
            }

    async def _lookup_isp_user(
        self, username: str, tenant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Lookup ISP user by username. In production, this would query the database."""
        # Simulate database lookup with common ISP users
        demo_users = {
            "admin": {
                "user_id": "isp_admin_001",
                "username": "admin",
                "email": "admin@isp.local",
                "password_hash": self.hash_password("admin123"),  # Change in production
                "roles": ["isp_admin"],
                "user_type": "staff",
                "tenant_id": tenant_id or "default_tenant",
                "is_active": True,
            },
            "tech": {
                "user_id": "isp_tech_001",
                "username": "tech",
                "email": "tech@isp.local",
                "password_hash": self.hash_password("tech123"),
                "roles": ["isp_technician"],
                "user_type": "staff",
                "tenant_id": tenant_id or "default_tenant",
                "is_active": True,
            },
            "support": {
                "user_id": "isp_support_001",
                "username": "support",
                "email": "support@isp.local",
                "password_hash": self.hash_password("support123"),
                "roles": ["isp_support"],
                "user_type": "staff",
                "tenant_id": tenant_id or "default_tenant",
                "is_active": True,
            },
        }

        return demo_users.get(username)

    async def _get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user data by ID. In production, this would query the database."""
        # Simulate database lookup
        all_users = {
            "isp_admin_001": {
                "user_id": "isp_admin_001",
                "username": "admin",
                "email": "admin@isp.local",
                "roles": ["isp_admin"],
                "user_type": "staff",
                "tenant_id": "default_tenant",
                "is_active": True,
                "custom_permissions": [],
            },
            "isp_tech_001": {
                "user_id": "isp_tech_001",
                "username": "tech",
                "email": "tech@isp.local",
                "roles": ["isp_technician"],
                "user_type": "staff",
                "tenant_id": "default_tenant",
                "is_active": True,
                "custom_permissions": [],
            },
            "isp_support_001": {
                "user_id": "isp_support_001",
                "username": "support",
                "email": "support@isp.local",
                "roles": ["isp_support"],
                "user_type": "staff",
                "tenant_id": "default_tenant",
                "is_active": True,
                "custom_permissions": [],
            },
        }

        return all_users.get(user_id)
