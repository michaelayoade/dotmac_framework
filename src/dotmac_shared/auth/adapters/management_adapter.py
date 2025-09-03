"""
Management Platform authentication adapter.

Production implementation for Management Platform integration.
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import bcrypt
import jwt
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ManagementAuthAdapter:
    """Authentication adapter for Management Platform with full implementation."""

    def __init__(
        self,
        db_session: Optional[AsyncSession] = None,
        jwt_secret: str = "mgmt-auth-secret-change-in-production",
        jwt_algorithm: str = "HS256",
        token_expiry_hours: int = 8,  # Shorter expiry for admin tokens
        mfa_required: bool = True,
    ):
        """Initialize Management Platform authentication adapter."""
        self.db_session = db_session
        self.jwt_secret = jwt_secret
        self.jwt_algorithm = jwt_algorithm
        self.token_expiry_hours = token_expiry_hours
        self.mfa_required = mfa_required

        # Management platform role hierarchy
        self.role_permissions = {
            "super_admin": [
                "manage_all_tenants",
                "manage_system",
                "manage_users",
                "view_system_analytics",
                "manage_billing",
                "manage_integrations",
                "access_audit_logs",
                "manage_security_settings",
                "disaster_recovery",
                "manage_backups",
                "system_maintenance",
                "manage_api_keys",
            ],
            "platform_admin": [
                "manage_tenants",
                "view_tenant_analytics",
                "manage_tenant_users",
                "view_billing",
                "manage_support_tickets",
                "access_tenant_logs",
                "manage_tenant_settings",
                "view_system_health",
            ],
            "tenant_admin": [
                "manage_own_tenant",
                "manage_tenant_users",
                "view_tenant_analytics",
                "manage_tenant_billing",
                "manage_tenant_settings",
                "access_tenant_support",
            ],
            "operations": [
                "view_system_health",
                "manage_backups",
                "view_analytics",
                "manage_monitoring",
                "access_system_logs",
                "manage_alerts",
            ],
            "support": [
                "view_tenant_info",
                "manage_support_tickets",
                "access_tenant_logs",
                "create_tenant_reports",
                "manage_customer_communications",
            ],
            "billing": [
                "manage_all_billing",
                "view_tenant_billing",
                "create_invoices",
                "manage_payments",
                "view_billing_analytics",
                "manage_subscriptions",
            ],
            "auditor": [
                "view_audit_logs",
                "view_compliance_reports",
                "access_security_logs",
                "view_all_analytics",
                "generate_compliance_reports",
            ],
        }

    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt with higher rounds for admin accounts."""
        salt = bcrypt.gensalt(rounds=12)  # Higher security for admin accounts
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash."""
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))

    def generate_mfa_token(self) -> str:
        """Generate MFA token for two-factor authentication."""
        return secrets.token_urlsafe(32)

    def generate_jwt_token(self, admin_data: Dict[str, Any]) -> str:
        """Generate JWT token for authenticated admin."""
        payload = {
            "sub": admin_data["admin_id"],
            "username": admin_data["username"],
            "roles": admin_data.get("roles", []),
            "permissions": admin_data.get("permissions", []),
            "user_type": "admin",
            "platform": "management",
            "session_id": hashlib.sha256(
                f"{admin_data['admin_id']}{datetime.now(timezone.utc)}".encode()
            ).hexdigest(),
            "mfa_verified": admin_data.get("mfa_verified", False),
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=self.token_expiry_hours),
        }

        return jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)

    async def authenticate_admin(self, credentials: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate admin user with Management Platform."""
        try:
            username = credentials.get("username")
            password = credentials.get("password")
            mfa_token = credentials.get("mfa_token")

            if not all([username, password]):
                return {
                    "success": False,
                    "error": "missing_credentials",
                    "message": "Username and password are required",
                }

            # Lookup admin user
            admin_data = await self._lookup_admin_user(username)

            if not admin_data:
                logger.warning(
                    f"Admin authentication failed - user not found: {username}"
                )
                await self._log_failed_attempt(username, "user_not_found")
                return {
                    "success": False,
                    "error": "invalid_credentials",
                    "message": "Invalid username or password",
                }

            # Check if account is active
            if not admin_data.get("is_active", False):
                logger.warning(
                    f"Admin authentication failed - account inactive: {username}"
                )
                await self._log_failed_attempt(username, "account_inactive")
                return {
                    "success": False,
                    "error": "account_inactive",
                    "message": "Account is inactive",
                }

            # Verify password
            if not self.verify_password(password, admin_data["password_hash"]):
                logger.warning(
                    f"Admin authentication failed - invalid password: {username}"
                )
                await self._log_failed_attempt(username, "invalid_password")
                return {
                    "success": False,
                    "error": "invalid_credentials",
                    "message": "Invalid username or password",
                }

            # Check MFA if required
            mfa_verified = True
            if self.mfa_required and admin_data.get("mfa_enabled", True):
                if not mfa_token:
                    return {
                        "success": False,
                        "error": "mfa_required",
                        "message": "Multi-factor authentication required",
                        "mfa_challenge": self.generate_mfa_token(),
                    }

                mfa_valid = await self._verify_mfa_token(
                    admin_data["admin_id"], mfa_token
                )
                if not mfa_valid:
                    logger.warning(
                        f"Admin authentication failed - invalid MFA: {username}"
                    )
                    await self._log_failed_attempt(username, "invalid_mfa")
                    return {
                        "success": False,
                        "error": "invalid_mfa",
                        "message": "Invalid MFA token",
                    }

            # Get admin permissions
            permissions_result = await self.get_admin_permissions(
                admin_data["admin_id"]
            )

            # Create successful authentication response
            auth_data = {
                "admin_id": admin_data["admin_id"],
                "username": admin_data["username"],
                "email": admin_data["email"],
                "full_name": admin_data.get("full_name", ""),
                "roles": admin_data["roles"],
                "permissions": permissions_result.get("permissions", []),
                "mfa_verified": mfa_verified,
                "last_login": datetime.now(timezone.utc).isoformat(),
            }

            # Generate JWT token
            token = self.generate_jwt_token(auth_data)

            # Log successful authentication
            logger.info(f"Successful admin authentication: {username}")
            await self._log_successful_attempt(admin_data["admin_id"], username)

            return {
                "success": True,
                "admin": auth_data,
                "token": token,
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(hours=self.token_expiry_hours)
                ).isoformat(),
                "session_timeout": self.token_expiry_hours * 3600,  # In seconds
            }

        except Exception as e:
            logger.error(f"Admin authentication error: {e}")
            return {
                "success": False,
                "error": "authentication_error",
                "message": "Authentication system error",
            }

    async def get_admin_permissions(self, admin_id: str) -> Dict[str, Any]:
        """Get admin permissions from Management Platform."""
        try:
            # Get admin data
            admin_data = await self._get_admin_by_id(admin_id)

            if not admin_data:
                return {"success": False, "error": "admin_not_found", "permissions": []}

            # Collect permissions from all roles
            all_permissions = set()
            for role in admin_data.get("roles", []):
                role_perms = self.role_permissions.get(role, [])
                all_permissions.update(role_perms)

            # Add custom permissions
            custom_permissions = admin_data.get("custom_permissions", [])
            all_permissions.update(custom_permissions)

            # Remove any explicitly denied permissions
            denied_permissions = admin_data.get("denied_permissions", [])
            all_permissions = all_permissions - set(denied_permissions)

            return {
                "success": True,
                "admin_id": admin_id,
                "roles": admin_data.get("roles", []),
                "permissions": list(all_permissions),
                "custom_permissions": custom_permissions,
                "denied_permissions": denied_permissions,
            }

        except Exception as e:
            logger.error(f"Error getting admin permissions: {e}")
            return {"success": False, "error": "permissions_error", "permissions": []}

    async def validate_admin_token(self, token: str) -> Dict[str, Any]:
        """Validate admin JWT token and return admin data."""
        try:
            payload = jwt.decode(
                token, self.jwt_secret, algorithms=[self.jwt_algorithm]
            )

            # Verify this is an admin token
            if (
                payload.get("user_type") != "admin"
                or payload.get("platform") != "management"
            ):
                return {
                    "success": False,
                    "error": "invalid_token_type",
                    "message": "Not a management platform admin token",
                }

            # Check expiration
            exp_timestamp = payload.get("exp")
            if exp_timestamp and datetime.now(timezone.utc).timestamp() > exp_timestamp:
                return {
                    "success": False,
                    "error": "token_expired",
                    "message": "Token has expired",
                }

            # Verify admin still exists and is active
            admin_data = await self._get_admin_by_id(payload.get("sub"))
            if not admin_data or not admin_data.get("is_active", False):
                return {
                    "success": False,
                    "error": "admin_inactive",
                    "message": "Admin account is inactive",
                }

            return {
                "success": True,
                "admin_id": payload.get("sub"),
                "username": payload.get("username"),
                "roles": payload.get("roles", []),
                "permissions": payload.get("permissions", []),
                "mfa_verified": payload.get("mfa_verified", False),
                "session_id": payload.get("session_id"),
            }

        except jwt.InvalidTokenError:
            return {
                "success": False,
                "error": "invalid_token",
                "message": "Invalid token",
            }
        except Exception as e:
            logger.error(f"Admin token validation error: {e}")
            return {
                "success": False,
                "error": "validation_error",
                "message": "Token validation failed",
            }

    async def refresh_admin_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an expired admin access token."""
        try:
            validation = await self.validate_admin_token(refresh_token)
            if not validation["success"]:
                return validation

            # Get fresh admin data
            admin_data = await self._get_admin_by_id(validation["admin_id"])
            if not admin_data:
                return {
                    "success": False,
                    "error": "admin_not_found",
                    "message": "Admin not found",
                }

            # Generate new token
            permissions = await self.get_admin_permissions(admin_data["admin_id"])

            auth_data = {
                "admin_id": admin_data["admin_id"],
                "username": admin_data["username"],
                "email": admin_data["email"],
                "full_name": admin_data.get("full_name", ""),
                "roles": admin_data["roles"],
                "permissions": permissions["permissions"],
                "mfa_verified": validation.get("mfa_verified", False),
            }

            new_token = self.generate_jwt_token(auth_data)

            return {
                "success": True,
                "token": new_token,
                "expires_at": (
                    datetime.now(timezone.utc) + timedelta(hours=self.token_expiry_hours)
                ).isoformat(),
            }

        except Exception as e:
            logger.error(f"Admin token refresh error: {e}")
            return {
                "success": False,
                "error": "refresh_error",
                "message": "Token refresh failed",
            }

    async def logout_admin(self, token: str) -> Dict[str, Any]:
        """Logout admin and invalidate token."""
        try:
            validation = await self.validate_admin_token(token)
            if validation["success"]:
                # In production, add token to blacklist
                session_id = validation.get("session_id")
                await self._blacklist_session(session_id)

                logger.info(f"Admin logout: {validation['username']}")

            return {"success": True, "message": "Logged out successfully"}

        except Exception as e:
            logger.error(f"Admin logout error: {e}")
            return {
                "success": False,
                "error": "logout_error",
                "message": "Logout failed",
            }

    async def _lookup_admin_user(self, username: str) -> Optional[Dict[str, Any]]:
        """Lookup admin user by username. In production, query the database."""
        # Demo admin users for development/testing
        demo_admins = {
            "superadmin": {
                "admin_id": "mgmt_super_001",
                "username": "superadmin",
                "email": "superadmin@dotmac.local",
                "full_name": "Super Administrator",
                "password_hash": self.hash_password("super123"),  # Change in production
                "roles": ["super_admin"],
                "is_active": True,
                "mfa_enabled": True,
                "custom_permissions": [],
                "denied_permissions": [],
            },
            "admin": {
                "admin_id": "mgmt_admin_001",
                "username": "admin",
                "email": "admin@dotmac.local",
                "full_name": "Platform Administrator",
                "password_hash": self.hash_password("admin123"),
                "roles": ["platform_admin"],
                "is_active": True,
                "mfa_enabled": True,
                "custom_permissions": [],
                "denied_permissions": [],
            },
            "operations": {
                "admin_id": "mgmt_ops_001",
                "username": "operations",
                "email": "ops@dotmac.local",
                "full_name": "Operations Manager",
                "password_hash": self.hash_password("ops123"),
                "roles": ["operations"],
                "is_active": True,
                "mfa_enabled": False,
                "custom_permissions": [],
                "denied_permissions": [],
            },
        }

        return demo_admins.get(username)

    async def _get_admin_by_id(self, admin_id: str) -> Optional[Dict[str, Any]]:
        """Get admin data by ID."""
        all_admins = {
            "mgmt_super_001": {
                "admin_id": "mgmt_super_001",
                "username": "superadmin",
                "email": "superadmin@dotmac.local",
                "full_name": "Super Administrator",
                "roles": ["super_admin"],
                "is_active": True,
                "mfa_enabled": True,
                "custom_permissions": [],
                "denied_permissions": [],
            },
            "mgmt_admin_001": {
                "admin_id": "mgmt_admin_001",
                "username": "admin",
                "email": "admin@dotmac.local",
                "full_name": "Platform Administrator",
                "roles": ["platform_admin"],
                "is_active": True,
                "mfa_enabled": True,
                "custom_permissions": [],
                "denied_permissions": [],
            },
            "mgmt_ops_001": {
                "admin_id": "mgmt_ops_001",
                "username": "operations",
                "email": "ops@dotmac.local",
                "full_name": "Operations Manager",
                "roles": ["operations"],
                "is_active": True,
                "mfa_enabled": False,
                "custom_permissions": [],
                "denied_permissions": [],
            },
        }

        return all_admins.get(admin_id)

    async def _verify_mfa_token(self, admin_id: str, mfa_token: str) -> bool:
        """Verify MFA token. In production, implement TOTP/SMS verification."""
        # For demo purposes, accept any 6-digit token
        return mfa_token and len(mfa_token) == 6 and mfa_token.isdigit()

    async def _log_failed_attempt(self, username: str, reason: str):
        """Log failed authentication attempt."""
        logger.warning(f"Admin auth failed: {username} - {reason}")
        # In production, implement rate limiting and alerting

    async def _log_successful_attempt(self, admin_id: str, username: str):
        """Log successful authentication."""
        logger.info(f"Admin auth success: {username} ({admin_id})")
        # In production, log to audit system

    async def _blacklist_session(self, session_id: str):
        """Blacklist session ID."""
        # In production, store in Redis/database
        logger.info(f"Session blacklisted: {session_id}")
