"""
Management App Bootstrap Module
Handles one-time initialization of the management platform
"""

import os

from dotmac_management.models.tenant import ManagementTenant
from dotmac_shared.core.logging import get_logger
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dotmac.database.base import get_db_session_sync
from dotmac.platform.auth.core.password_service import PasswordService
from dotmac.platform.auth.models import Permission, Role, User

logger = get_logger(__name__)


class ManagementBootstrap:
    """Handles one-time bootstrap of Management platform"""

    def __init__(self):
        self.password_service = PasswordService()

    def should_bootstrap(self) -> bool:
        """Check if bootstrap is needed (no admin users exist)"""
        try:
            db = get_db_session_sync()
            try:
                admin_count = (
                    db.query(User)
                    .join(User.roles)
                    .filter(Role.name.in_(["super_admin", "platform_admin"]))
                    .count()
                )
                return admin_count == 0
            finally:
                db.close()
        except Exception:  # noqa: BLE001 - broad guard around DB/bootstrap state check
            logger.exception("Could not check bootstrap status")
            return True

    async def bootstrap_if_needed(self) -> bool:
        """Run bootstrap if needed, return True if bootstrap was performed"""
        if not self.should_bootstrap():
            logger.info("Management platform already bootstrapped, skipping")
            return False

        logger.info("Starting Management platform bootstrap...")

        # Get bootstrap credentials from environment
        admin_email = os.getenv("AUTH_ADMIN_EMAIL")
        admin_password = os.getenv("AUTH_INITIAL_ADMIN_PASSWORD")

        if not admin_email or not admin_password:
            logger.error("Bootstrap credentials not provided via environment variables")
            logger.error("Set AUTH_ADMIN_EMAIL and AUTH_INITIAL_ADMIN_PASSWORD")
            raise ValueError("Bootstrap credentials missing")

        # Validate email format
        if "@" not in admin_email:
            raise ValueError("Invalid admin email format")

        # Validate password strength
        if len(admin_password) < 12:
            raise ValueError("Admin password must be at least 12 characters")

        success = await self._perform_bootstrap(admin_email, admin_password)

        if success:
            logger.warning(
                "🔐 SECURITY NOTICE: Remove AUTH_ADMIN_EMAIL and AUTH_INITIAL_ADMIN_PASSWORD from environment after first login!"
            )

        return success

    async def _perform_bootstrap(self, admin_email: str, admin_password: str) -> bool:
        """Perform the actual bootstrap process"""
        try:
            db = get_db_session_sync()
            try:
                # Create core roles and permissions
                await self._create_core_roles_permissions(db)

                # Create platform admin user
                admin_user = await self._create_admin_user(
                    db, admin_email, admin_password
                )

                # Create management tenant
                await self._create_management_tenant(db, admin_user)

                # Commit all changes
                db.commit()

                logger.info("✅ Management platform bootstrap completed successfully")
                logger.info(f"🔑 Admin user created: {admin_email}")
                logger.info("🌐 Management portal ready")

                return True

            finally:
                db.close()

        except Exception:  # noqa: BLE001 - bootstrap orchestrator wants full trace
            logger.exception("Bootstrap failed")
            raise

    async def _create_core_roles_permissions(self, db: Session) -> None:
        """Create core roles and permissions for management platform"""

        # Core permissions
        permissions = [
            # Tenant management
            Permission(name="tenant.create", description="Create new tenants"),
            Permission(name="tenant.read", description="View tenant information"),
            Permission(name="tenant.update", description="Update tenant settings"),
            Permission(name="tenant.delete", description="Delete tenants"),
            Permission(
                name="tenant.provision", description="Provision tenant infrastructure"
            ),
            # User management
            Permission(name="user.create", description="Create users"),
            Permission(name="user.read", description="View users"),
            Permission(name="user.update", description="Update users"),
            Permission(name="user.delete", description="Delete users"),
            Permission(name="user.impersonate", description="Impersonate users"),
            # Platform administration
            Permission(
                name="platform.admin", description="Platform administration access"
            ),
            Permission(
                name="platform.settings", description="Manage platform settings"
            ),
            Permission(
                name="platform.monitoring", description="View platform monitoring"
            ),
            Permission(name="platform.billing", description="Manage billing settings"),
            # System operations
            Permission(name="system.deploy", description="Deploy system updates"),
            Permission(name="system.backup", description="Manage system backups"),
            Permission(name="system.logs", description="Access system logs"),
        ]

        for perm in permissions:
            existing = db.query(Permission).filter_by(name=perm.name).first()
            if not existing:
                db.add(perm)
                logger.debug(f"Created permission: {perm.name}")

        db.flush()  # Ensure permissions are available for role creation

        # Core roles
        roles_data = [
            {
                "name": "super_admin",
                "description": "Super administrator with full platform access",
                "permissions": [
                    "platform.admin",
                    "tenant.create",
                    "tenant.read",
                    "tenant.update",
                    "tenant.delete",
                    "tenant.provision",
                    "user.create",
                    "user.read",
                    "user.update",
                    "user.delete",
                    "user.impersonate",
                    "platform.settings",
                    "platform.monitoring",
                    "platform.billing",
                    "system.deploy",
                    "system.backup",
                    "system.logs",
                ],
            },
            {
                "name": "platform_admin",
                "description": "Platform administrator",
                "permissions": [
                    "tenant.create",
                    "tenant.read",
                    "tenant.update",
                    "tenant.provision",
                    "user.create",
                    "user.read",
                    "user.update",
                    "platform.monitoring",
                    "platform.billing",
                ],
            },
            {
                "name": "support_admin",
                "description": "Support administrator",
                "permissions": ["tenant.read", "user.read", "platform.monitoring"],
            },
        ]

        for role_data in roles_data:
            existing_role = db.query(Role).filter_by(name=role_data["name"]).first()
            if not existing_role:
                role = Role(
                    name=role_data["name"], description=role_data["description"]
                )

                # Add permissions to role
                for perm_name in role_data["permissions"]:
                    permission = db.query(Permission).filter_by(name=perm_name).first()
                    if permission:
                        role.permissions.append(permission)

                db.add(role)
                logger.debug(f"Created role: {role.name}")

        db.flush()

    async def _create_admin_user(self, db: Session, email: str, password: str) -> User:
        """Create the initial admin user"""

        # Check if user already exists
        existing_user = db.query(User).filter_by(email=email).first()
        if existing_user:
            logger.info(f"Admin user {email} already exists")
            return existing_user

        # Hash password
        password_hash = await self.password_service.hash_password(password)

        # Create user
        admin_user = User(
            email=email,
            password_hash=password_hash,
            first_name="Platform",
            last_name="Administrator",
            is_active=True,
            is_verified=True,  # Bootstrap user is pre-verified
            is_superuser=True,
        )

        # Assign super_admin role
        super_admin_role = db.query(Role).filter_by(name="super_admin").first()
        if super_admin_role:
            admin_user.roles.append(super_admin_role)

        try:
            db.add(admin_user)
            db.flush()
            logger.info(f"Created admin user: {email}")
            return admin_user

        except IntegrityError:
            db.rollback()
            # User might have been created by another process
            existing = db.query(User).filter_by(email=email).first()
            if existing:
                return existing
            raise

    async def _create_management_tenant(
        self, db: Session, admin_user: User
    ) -> ManagementTenant:
        """Create the management tenant"""

        existing = (
            db.query(ManagementTenant)
            .filter_by(tenant_id="management-platform")
            .first()
        )

        if existing:
            logger.info("Management tenant already exists")
            return existing

        tenant = ManagementTenant(
            tenant_id="management-platform",
            name="DotMac Management Platform",
            description="Core management platform tenant",
            status="active",
            owner_id=admin_user.id,
            settings={
                "max_tenants": -1,  # Unlimited
                "features": [
                    "tenant_management",
                    "user_management",
                    "billing",
                    "monitoring",
                ],
                "bootstrap_completed": True,
            },
        )

        db.add(tenant)
        db.flush()
        logger.info("Created management platform tenant")
        return tenant


# Bootstrap instance
bootstrap_manager = ManagementBootstrap()


async def run_bootstrap_if_needed() -> bool:
    """Convenience function to run bootstrap"""
    return await bootstrap_manager.bootstrap_if_needed()
