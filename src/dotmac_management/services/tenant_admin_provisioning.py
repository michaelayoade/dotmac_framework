"""
Tenant Admin Provisioning Service
Handles creation of ISP admin accounts and initial setup
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from dotmac.communications.notifications import UnifiedNotificationService as NotificationService
from dotmac_management.models.tenant import CustomerTenant
from dotmac_shared.core.error_utils import service_operation
from dotmac_shared.core.logging import get_logger
from dotmac_shared.security.secrets import SecretsManager
from dotmac_shared.validation.common_validators import CommonValidators
from pydantic import (
    BaseModel,
    ConfigDict,
    field_validator,
)

logger = get_logger(__name__)


class AdminCredentials(BaseModel):
    """Admin credentials with validation"""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str
    email: str
    password: str
    first_name: str
    last_name: str
    tenant_id: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        return CommonValidators.validate_email(v)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        return CommonValidators.validate_username(v)


class TenantAdminProvisioningService:
    """Creates and configures ISP instance admin accounts"""

    def __init__(self):
        self.secrets_manager = SecretsManager()
        self.notification_service = NotificationService()

    @service_operation("tenant_admin")
    async def create_tenant_admin(self, tenant: CustomerTenant) -> dict[str, Any]:
        """
        Create admin account for newly provisioned ISP instance

        Returns admin credentials and setup information
        """
        try:
            logger.info(f"Creating admin account for tenant {tenant.tenant_id}")

            # Generate secure admin credentials
            admin_creds = await self._generate_admin_credentials(tenant)

            # Create admin user in ISP instance
            admin_user = await self._create_isp_admin_user(tenant, admin_creds)

            # Send welcome email with credentials
            await self._send_admin_welcome_email(tenant, admin_creds)

            # Generate initial JWT for immediate access
            initial_jwt = await self._generate_initial_jwt(tenant, admin_user)

            return {
                "admin_user_id": admin_user["id"],
                "username": admin_creds.username,
                "email": admin_creds.email,
                "initial_jwt": initial_jwt,
                "portal_url": f"https://{tenant.subdomain}.{self._get_domain_suffix()}",
                "credentials_sent": True,
            }

        except Exception as e:
            logger.error(f"Failed to create tenant admin for {tenant.tenant_id}: {e}")
            raise

    async def _generate_admin_credentials(self, tenant: CustomerTenant) -> AdminCredentials:
        """Generate secure admin credentials"""

        # Use provided admin info from tenant signup
        username = f"{tenant.subdomain}_admin"
        email = tenant.admin_email

        # Generate secure password
        password = self._generate_secure_password()

        return AdminCredentials(
            username=username,
            email=email,
            password=password,
            first_name=tenant.admin_name.split(" ")[0] if " " in tenant.admin_name else tenant.admin_name,
            last_name=" ".join(tenant.admin_name.split(" ")[1:]) if " " in tenant.admin_name else "",
            tenant_id=tenant.tenant_id,
        )

    @service_operation("tenant_admin")
    async def _create_isp_admin_user(self, tenant: CustomerTenant, admin_creds: AdminCredentials) -> dict[str, Any]:
        """Create admin user in ISP instance via API"""

        # Hash password for storage
        password_hash = hashlib.pbkdf2_hmac(
            "sha256", admin_creds.password.encode("utf-8"), tenant.tenant_id.encode("utf-8"), 100000
        ).hex()

        # Prepare user creation payload
        user_payload = {
            "username": admin_creds.username,
            "email": admin_creds.email,
            "password_hash": password_hash,
            "first_name": admin_creds.first_name,
            "last_name": admin_creds.last_name,
            "is_active": True,
            "is_superuser": True,
            "portal_type": "admin",
            "permissions": [
                "admin:full_access",
                "customers:manage",
                "services:manage",
                "billing:manage",
                "analytics:view",
                "system:configure",
            ],
            "user_metadata": {
                "created_by": "management_platform",
                "tenant_provisioning": True,
                "initial_admin": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        }

        # Get ISP instance URL
        isp_url = await self._get_isp_instance_url(tenant)

        # Create user via ISP API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{isp_url}/api/v1/admin/users",
                json=user_payload,
                headers={
                    "Authorization": f"Bearer {await self._get_management_api_token()}",
                    "Content-Type": "application/json",
                },
            )

            if response.status_code != 201:
                raise Exception(f"Failed to create admin user: {response.text}")

            return response.json()["data"]

    async def _send_admin_welcome_email(self, tenant: CustomerTenant, admin_creds: AdminCredentials):
        """Send welcome email with admin credentials"""

        portal_url = f"https://{tenant.subdomain}.{self._get_domain_suffix()}"

        await self.notification_service.send_email(
            to_email=admin_creds.email,
            subject=f"Your {tenant.company_name} ISP Portal is Ready!",
            template="tenant_admin_welcome",
            data={
                "admin_name": f"{admin_creds.first_name} {admin_creds.last_name}",
                "company_name": tenant.company_name,
                "portal_url": portal_url,
                "username": admin_creds.username,
                "password": admin_creds.password,
                "subdomain": tenant.subdomain,
                "plan": tenant.plan.title(),
                "next_steps": [
                    "Log into your ISP portal using the credentials above",
                    "Complete the setup wizard to configure your services",
                    "Add your first service plans and pricing",
                    "Configure your network infrastructure (NAS/routers)",
                    "Start adding customers to your ISP",
                ],
                "support_email": "support@dotmac.com",
                "password_expires_days": 30,
            },
        )

        logger.info(f"Welcome email sent to {admin_creds.email} for tenant {tenant.tenant_id}")

    async def _generate_initial_jwt(self, tenant: CustomerTenant, admin_user: dict[str, Any]) -> str:
        """Generate JWT token for immediate admin access"""

        from dotmac.platform.auth.core.jwt_service import JWTService

        jwt_service = JWTService()

        # Create JWT payload
        payload = {
            "user_id": admin_user["id"],
            "tenant_id": tenant.tenant_id,
            "email": admin_user["email"],
            "username": admin_user["username"],
            "is_superuser": True,
            "portal_type": "admin",
            "permissions": admin_user.get("permissions", []),
            "token_type": "access",
            "initial_setup": True,
        }

        # Generate token valid for 24 hours for initial setup
        return await jwt_service.create_access_token(data=payload, expires_delta=timedelta(hours=24))

    async def _get_isp_instance_url(self, tenant: CustomerTenant) -> str:
        """Get ISP instance URL from tenant configuration"""

        domain_suffix = self._get_domain_suffix()
        return f"https://{tenant.subdomain}.{domain_suffix}"

    async def _get_management_api_token(self) -> str:
        """Get management platform API token for ISP communication"""

        from dotmac.platform.auth.core.jwt_service import JWTService

        jwt_service = JWTService()

        # Create management platform service token
        payload = {"service": "management_platform", "scope": "tenant_provisioning", "token_type": "service"}

        return await jwt_service.create_access_token(data=payload, expires_delta=timedelta(hours=1))

    def _generate_secure_password(self) -> str:
        """Generate secure password for admin account"""

        # Generate cryptographically secure password
        password_chars = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$%^&*"  # noqa: S105 - character set
        password = "".join(secrets.choice(password_chars) for _ in range(16))

        # Ensure password contains required character types
        if not any(c.isupper() for c in password):
            password = password[:-1] + secrets.choice("ABCDEFGHJKMNPQRSTUVWXYZ")
        if not any(c.islower() for c in password):
            password = password[:-1] + secrets.choice("abcdefghijkmnpqrstuvwxyz")
        if not any(c.isdigit() for c in password):
            password = password[:-1] + secrets.choice("23456789")
        if not any(c in "!@#$%^&*" for c in password):
            password = password[:-1] + secrets.choice("!@#$%^&*")

        return password

    def _get_domain_suffix(self) -> str:
        """Get domain suffix for tenant URLs"""
        import os

        return os.getenv("TENANT_DOMAIN_SUFFIX", "yourdomain.com")
