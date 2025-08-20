"""
Database migration management for platform integration.
"""

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory

from .config import get_config
from .database import get_engine
from .exceptions import BillingError

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database migrations for the billing system."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize migration manager."""
        self.project_root = Path(__file__).parent.parent.parent
        self.config_path = config_path or self.project_root / "alembic.ini"
        self.alembic_config = None
        self._setup_alembic_config()

    def _setup_alembic_config(self):
        """Setup Alembic configuration."""
        if not self.config_path.exists():
            raise BillingError(f"Alembic config not found: {self.config_path}")

        self.alembic_config = Config(str(self.config_path))

        # Set database URL from billing config
        billing_config = get_config()
        database_url = billing_config.get_database_url()
        self.alembic_config.set_main_option("sqlalchemy.url", database_url)

        # Set script location relative to project root
        script_location = self.project_root / "migrations"
        self.alembic_config.set_main_option("script_location", str(script_location))

    def get_current_revision(self) -> Optional[str]:
        """Get current database revision."""
        try:
            engine = get_engine()
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                return context.get_current_revision()
        except Exception as e:
            logger.error(f"Failed to get current revision: {e}")
            return None

    def get_head_revision(self) -> Optional[str]:
        """Get latest available revision."""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_config)
            return script_dir.get_current_head()
        except Exception as e:
            logger.error(f"Failed to get head revision: {e}")
            return None

    def get_migration_history(self) -> List[Dict[str, Any]]:
        """Get migration history."""
        try:
            script_dir = ScriptDirectory.from_config(self.alembic_config)
            revisions = []

            for revision in script_dir.walk_revisions():
                revisions.append({
                    "revision": revision.revision,
                    "down_revision": revision.down_revision,
                    "branch_labels": revision.branch_labels,
                    "message": revision.doc,
                    "create_date": getattr(revision, "create_date", None)
                })

            return revisions
        except Exception as e:
            logger.error(f"Failed to get migration history: {e}")
            return []

    def check_migration_status(self) -> Dict[str, Any]:
        """Check current migration status."""
        current = self.get_current_revision()
        head = self.get_head_revision()

        status = {
            "current_revision": current,
            "head_revision": head,
            "up_to_date": current == head,
            "needs_upgrade": current != head,
            "database_exists": current is not None
        }

        if not status["database_exists"]:
            status["action_required"] = "Initialize database"
        elif status["needs_upgrade"]:
            status["action_required"] = "Run migrations"
        else:
            status["action_required"] = "None"

        return status

    def initialize_database(self) -> bool:
        """Initialize database with latest schema."""
        try:
            logger.info("Initializing database schema...")

            # Create all tables
            from ..models.base import Base
            engine = get_engine()
            Base.metadata.create_all(bind=engine)

            # Mark as current revision
            command.stamp(self.alembic_config, "head")

            logger.info("Database initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False

    def run_migrations(self, target_revision: Optional[str] = None) -> bool:
        """Run database migrations."""
        try:
            logger.info(f"Running migrations to {target_revision or 'head'}...")

            # Run migrations
            command.upgrade(self.alembic_config, target_revision or "head")

            logger.info("Migrations completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to run migrations: {e}")
            return False

    def rollback_migration(self, target_revision: str) -> bool:
        """Rollback to specific revision."""
        try:
            logger.info(f"Rolling back to revision {target_revision}...")

            # Rollback
            command.downgrade(self.alembic_config, target_revision)

            logger.info("Rollback completed successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to rollback migration: {e}")
            return False

    def create_migration(self, message: str, autogenerate: bool = True) -> Optional[str]:
        """Create a new migration."""
        try:
            logger.info(f"Creating migration: {message}")

            # Generate migration
            revision = command.revision(
                self.alembic_config,
                message=message,
                autogenerate=autogenerate
            )

            logger.info(f"Migration created: {revision}")
            return revision

        except Exception as e:
            logger.error(f"Failed to create migration: {e}")
            return None

    def validate_database_schema(self) -> Dict[str, Any]:
        """Validate database schema against models."""
        try:
            from ..models.base import Base
            engine = get_engine()

            # Get current schema from database
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)

                # Compare with model schema
                # This is a simplified validation
                validation_result = {
                    "valid": True,
                    "issues": [],
                    "current_revision": context.get_current_revision(),
                    "model_metadata": len(Base.metadata.tables)
                }

                # Check if all model tables exist
                existing_tables = set(engine.table_names())
                model_tables = set(Base.metadata.tables.keys())

                missing_tables = model_tables - existing_tables
                if missing_tables:
                    validation_result["valid"] = False
                    validation_result["issues"].append(f"Missing tables: {missing_tables}")

                extra_tables = existing_tables - model_tables
                if extra_tables:
                    validation_result["issues"].append(f"Extra tables: {extra_tables}")

                return validation_result

        except Exception as e:
            logger.error(f"Failed to validate schema: {e}")
            return {
                "valid": False,
                "issues": [f"Validation error: {str(e)}"],
                "current_revision": None,
                "model_metadata": 0
            }

    def backup_database(self, backup_path: Optional[str] = None) -> bool:
        """Create database backup before migrations."""
        try:
            if backup_path is None:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"backup_billing_{timestamp}.sql"

            config = get_config()
            database_url = config.get_database_url()

            # Extract connection details (simplified for PostgreSQL)
            if "postgresql" in database_url:
                # Use pg_dump for PostgreSQL
                cmd = [
                    "pg_dump",
                    database_url,
                    "-f", backup_path,
                    "--verbose"
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"Database backup created: {backup_path}")
                    return True
                else:
                    logger.error(f"Backup failed: {result.stderr}")
                    return False
            else:
                logger.warning("Backup only supported for PostgreSQL")
                return False

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False

    def tenant_safe_migration(self, tenant_id: Optional[str] = None) -> bool:
        """Run tenant-safe migrations with validation."""
        try:
            logger.info("Running tenant-safe migration...")

            # Check current status
            status = self.check_migration_status()
            if status["up_to_date"]:
                logger.info("Database already up to date")
                return True

            # Validate schema before migration
            validation = self.validate_database_schema()
            if not validation["valid"]:
                logger.warning(f"Schema validation issues: {validation['issues']}")

            # Create backup in production
            config = get_config()
            if config.is_production():
                backup_success = self.backup_database()
                if not backup_success:
                    logger.error("Backup failed, aborting migration")
                    return False

            # Run migrations
            success = self.run_migrations()

            if success:
                # Validate after migration
                post_validation = self.validate_database_schema()
                if not post_validation["valid"]:
                    logger.error(f"Post-migration validation failed: {post_validation['issues']}")
                    return False

                logger.info("Tenant-safe migration completed successfully")
                return True
            else:
                return False

        except Exception as e:
            logger.error(f"Tenant-safe migration failed: {e}")
            return False


# Global migration manager instance
_migration_manager: Optional[MigrationManager] = None


def get_migration_manager() -> MigrationManager:
    """Get global migration manager instance."""
    global _migration_manager
    if _migration_manager is None:
        _migration_manager = MigrationManager()
    return _migration_manager


def set_migration_manager(manager: MigrationManager):
    """Set global migration manager instance."""
    global _migration_manager
    _migration_manager = manager
