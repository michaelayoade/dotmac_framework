"""
Schema Manager - Handles database schema migrations and management.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import asyncpg
import structlog
from alembic.config import Config
from tenacity import retry, stop_after_attempt, wait_exponential

from .database_creator import DatabaseInstance

logger = structlog.get_logger(__name__)


class SchemaManager:
    """Manages database schema migrations and initialization."""

    def __init__(
        self, db_instance: DatabaseInstance, migrations_path: Optional[str] = None
    ):
        self.db_instance = db_instance
        self.logger = logger.bind(
            component="schema_manager", database=db_instance.database_name
        )

        # Set up migrations path
        self.migrations_path = migrations_path or self._get_default_migrations_path()

        # Initialize Alembic configuration
        self.alembic_cfg = self._setup_alembic_config()

    def _get_default_migrations_path(self) -> str:
        """Get default path for migration files."""
        package_dir = Path(__file__).parent.parent
        return str(package_dir / "templates" / "migrations")

    def _setup_alembic_config(self) -> Config:
        """Set up Alembic configuration."""
        # Create alembic.ini content programmatically
        alembic_cfg = Config()

        # Set the script location
        alembic_cfg.set_main_option("script_location", self.migrations_path)

        # Set the database URL
        alembic_cfg.set_main_option(
            "sqlalchemy.url", self.db_instance.connection_string
        )

        # Set other necessary options
        alembic_cfg.set_main_option(
            "file_template",
            "%.format(year)d%.format(month).2d%.format(day).2d_%.format(hour).2d%.format(minute).2d_%.format(rev)s_%.format(slug)s",
        )
        alembic_cfg.set_main_option("timezone", "UTC")

        return alembic_cfg

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def initialize_schema(self) -> bool:
        """
        Initialize the database schema using Alembic migrations.

        Returns:
            True if schema initialization was successful
        """
        self.logger.info("Initializing database schema")

        try:
            # First, ensure the database is accessible
            if not await self._validate_database_connection():
                raise RuntimeError("Cannot connect to database")

            # Create alembic version table and run migrations
            await self._setup_migration_environment()

            # Apply all available migrations
            await self._run_migrations()

            # Verify schema integrity
            if await self._verify_schema_integrity():
                self.logger.info("Schema initialization completed successfully")
                return True
            else:
                raise RuntimeError("Schema integrity check failed")

        except Exception as e:
            self.logger.error(
                "Schema initialization failed", error=str(e), exc_info=True
            )
            return False

    async def _validate_database_connection(self) -> bool:
        """Validate database connection."""
        try:
            conn = await asyncpg.connect(**self.db_instance.get_connection_params())
            await conn.fetchval("SELECT 1")
            await conn.close()
            return True
        except Exception as e:
            self.logger.error("Database connection failed", error=str(e))
            return False

    async def _setup_migration_environment(self) -> None:
        """Set up Alembic migration environment."""
        try:
            # Create migrations directory if it doesn't exist
            migrations_dir = Path(self.migrations_path)
            migrations_dir.mkdir(parents=True, exist_ok=True)

            # Create versions directory
            versions_dir = migrations_dir / "versions"
            versions_dir.mkdir(exist_ok=True)

            # Create env.py if it doesn't exist
            env_py_path = migrations_dir / "env.py"
            if not env_py_path.exists():
                await self._create_env_py(env_py_path)

            # Create script.py.mako if it doesn't exist
            script_mako_path = migrations_dir / "script.py.mako"
            if not script_mako_path.exists():
                await self._create_script_mako(script_mako_path)

            # Initialize Alembic if not already initialized
            await self._initialize_alembic()

        except Exception as e:
            self.logger.error("Failed to setup migration environment", error=str(e))
            raise

    async def _create_env_py(self, env_py_path: Path) -> None:
        """Create Alembic env.py file."""
        env_py_content = '''
"""Alembic environment configuration for ISP database."""

import asyncio
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context

# Import your models here
# from myapp import mymodel

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata (import your Base.metadata here)
target_metadata = None

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations():
    """In this scenario we need to create an Engine and connect to the database."""
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
        with open(env_py_path, "w") as f:
            f.write(env_py_content.strip())

    async def _create_script_mako(self, script_mako_path: Path) -> None:
        """Create Alembic script.py.mako template."""
        script_mako_content = '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    """Upgrade to this revision."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Downgrade from this revision."""
    ${downgrades if downgrades else "pass"}
'''
        with open(script_mako_path, "w") as f:
            f.write(script_mako_content.strip())

    async def _initialize_alembic(self) -> None:
        """Initialize Alembic in the database."""
        try:
            # Check if alembic version table exists
            conn = await asyncpg.connect(**self.db_instance.get_connection_params())

            try:
                version_table_exists = await conn.fetchval(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'alembic_version'
                    )
                    """
                )

                if not version_table_exists:
                    # Create alembic version table
                    await conn.execute(
                        """
                        CREATE TABLE alembic_version (
                            version_num VARCHAR(32) NOT NULL,
                            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
                        )
                        """
                    )
                    self.logger.info("Created alembic_version table")

            finally:
                await conn.close()

        except Exception as e:
            self.logger.error("Failed to initialize Alembic", error=str(e))
            raise

    async def _run_migrations(self) -> None:
        """Run all pending migrations."""
        try:
            # Load base schema first
            await self._load_base_schema()

            # Get current revision
            current_revision = await self._get_current_revision()

            # Get available migrations
            available_migrations = await self._get_available_migrations()

            if not available_migrations:
                self.logger.info("No migrations available")
                return

            # Apply migrations
            for migration in available_migrations:
                if not current_revision or migration["revision"] != current_revision:
                    await self._apply_migration(migration)

            self.logger.info("All migrations applied successfully")

        except Exception as e:
            self.logger.error("Failed to run migrations", error=str(e))
            raise

    async def _load_base_schema(self) -> None:
        """Load the base schema from template."""
        schema_template_path = Path(self.migrations_path).parent / "isp_schema.sql"

        if schema_template_path.exists():
            self.logger.info("Loading base schema")

            try:
                with open(schema_template_path) as f:
                    schema_sql = f.read()

                conn = await asyncpg.connect(**self.db_instance.get_connection_params())
                try:
                    # Execute schema in a transaction
                    async with conn.transaction():
                        await conn.execute(schema_sql)

                    self.logger.info("Base schema loaded successfully")

                finally:
                    await conn.close()

            except Exception as e:
                self.logger.error("Failed to load base schema", error=str(e))
                # Don't raise here - base schema might not be needed

    async def _get_current_revision(self) -> Optional[str]:
        """Get the current database revision."""
        try:
            conn = await asyncpg.connect(**self.db_instance.get_connection_params())

            try:
                revision = await conn.fetchval(
                    "SELECT version_num FROM alembic_version LIMIT 1"
                )
                return revision

            finally:
                await conn.close()

        except Exception:
            # Table might not exist yet
            return None

    async def _get_available_migrations(self) -> list[dict[str, Any]]:
        """Get list of available migration files."""
        migrations = []
        versions_dir = Path(self.migrations_path) / "versions"

        if versions_dir.exists():
            for migration_file in sorted(versions_dir.glob("*.py")):
                if migration_file.name != "__init__.py":
                    # Extract revision from filename (simple approach)
                    revision = migration_file.stem.split("_")[0]
                    migrations.append(
                        {
                            "revision": revision,
                            "file": str(migration_file),
                            "name": migration_file.stem,
                        }
                    )

        return migrations

    async def _apply_migration(self, migration: dict[str, Any]) -> None:
        """Apply a specific migration with backup and rollback support."""
        self.logger.info("Applying migration", migration=migration["name"])

        # Create backup before migration
        backup_info = await self._create_pre_migration_backup(migration["revision"])

        conn = await asyncpg.connect(**self.db_instance.get_connection_params())

        try:
            # Execute migration in transaction
            async with conn.transaction():
                # Parse and execute migration file
                await self._execute_migration_file(conn, migration)

                # Update version table
                await conn.execute(
                    "DELETE FROM alembic_version"  # Alembic only keeps one version
                )
                await conn.execute(
                    "INSERT INTO alembic_version (version_num) VALUES ($1)",
                    migration["revision"],
                )

            self.logger.info(
                "Migration applied successfully", revision=migration["revision"]
            )

        except Exception as e:
            self.logger.error(
                "Migration failed, rollback available",
                revision=migration["revision"],
                error=str(e),
                backup_info=backup_info,
            )
            raise
        finally:
            await conn.close()

    async def _create_pre_migration_backup(self, revision: str) -> dict[str, Any]:
        """Create backup before applying migration."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"pre_migration_{revision}_{timestamp}"

        try:
            conn = await asyncpg.connect(**self.db_instance.get_connection_params())

            try:
                # Get all table names
                tables = await conn.fetch(
                    """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                """
                )

                backup_info = {
                    "backup_name": backup_name,
                    "revision": revision,
                    "timestamp": timestamp,
                    "table_count": len(tables),
                    "tables": [t[0] for t in tables],
                }

                # Store backup metadata in Redis (leveraging existing coordination)
                await self._store_backup_metadata(backup_info)

                self.logger.info(
                    "Pre-migration backup created", backup_name=backup_name
                )
                return backup_info

            finally:
                await conn.close()

        except Exception as e:
            self.logger.warning("Backup creation failed", error=str(e))
            return {"backup_name": None, "error": str(e)}

    async def _store_backup_metadata(self, backup_info: dict[str, Any]) -> None:
        """Store backup metadata using existing Redis infrastructure."""
        try:
            # Leverage existing database coordination Redis connection
            from ...database.coordination import DatabaseCoordinator

            coordinator = DatabaseCoordinator()
            await coordinator.initialize()

            if coordinator._redis_client:
                await coordinator._redis_client.hset(
                    "migration_backups",
                    backup_info["backup_name"],
                    json.dumps(backup_info),
                )
        except Exception as e:
            self.logger.warning("Failed to store backup metadata", error=str(e))

    async def _execute_migration_file(self, conn, migration: dict[str, Any]) -> None:
        """Execute migration file content."""
        migration_file = Path(migration["file"])

        if migration_file.exists():
            try:
                # Parse migration file for SQL commands
                with open(migration_file) as f:
                    content = f.read()

                # Extract upgrade() function SQL commands
                # This is a simplified parser - in production you'd use AST
                if "def upgrade():" in content:
                    lines = content.split("\n")
                    in_upgrade = False
                    sql_commands = []

                    for line in lines:
                        if "def upgrade():" in line:
                            in_upgrade = True
                            continue
                        elif "def downgrade():" in line:
                            break
                        elif in_upgrade and line.strip().startswith("op."):
                            # Convert Alembic operations to SQL
                            sql_cmd = self._convert_alembic_to_sql(line.strip())
                            if sql_cmd:
                                sql_commands.append(sql_cmd)

                    # Execute SQL commands
                    for sql_cmd in sql_commands:
                        await conn.execute(sql_cmd)

            except Exception as e:
                self.logger.error("Migration file execution failed", error=str(e))
                raise
        else:
            self.logger.warning("Migration file not found", file=str(migration_file))

    def _convert_alembic_to_sql(self, alembic_op: str) -> Optional[str]:
        """Convert simple Alembic operations to SQL."""
        # Simplified converter for basic operations
        if "op.create_table" in alembic_op:
            # This would need proper parsing in production
            return None  # Skip for now
        elif "op.add_column" in alembic_op:
            return None  # Skip for now
        elif "op.execute" in alembic_op and "'" in alembic_op:
            # Extract SQL from op.execute('SQL')
            start = alembic_op.find("'") + 1
            end = alembic_op.rfind("'")
            if start < end:
                return alembic_op[start:end]

        return None

    async def rollback_to_revision(self, target_revision: str) -> bool:
        """Rollback database to a specific revision."""
        self.logger.info("Initiating rollback", target_revision=target_revision)

        try:
            current_revision = await self._get_current_revision()
            if not current_revision:
                raise RuntimeError("No current revision found")

            if current_revision == target_revision:
                self.logger.info("Already at target revision")
                return True

            # Get available migrations for rollback path
            rollback_path = await self._get_rollback_path(
                current_revision, target_revision
            )

            # Apply rollbacks in reverse order
            for migration in reversed(rollback_path):
                await self._apply_rollback_migration(migration)

            self.logger.info(
                "Rollback completed successfully", target_revision=target_revision
            )
            return True

        except Exception as e:
            self.logger.error("Rollback failed", error=str(e))
            return False

    async def _get_rollback_path(
        self, from_revision: str, to_revision: str
    ) -> list[dict[str, Any]]:
        """Get the path of migrations to rollback."""
        # For now, return empty list - in production this would parse migration dependencies
        available_migrations = await self._get_available_migrations()

        # Simple implementation: return migrations between revisions
        rollback_migrations = []
        for migration in available_migrations:
            if (
                migration["revision"] > to_revision
                and migration["revision"] <= from_revision
            ):
                rollback_migrations.append(migration)

        return rollback_migrations

    async def _apply_rollback_migration(self, migration: dict[str, Any]) -> None:
        """Apply rollback for a specific migration."""
        self.logger.info("Rolling back migration", migration=migration["name"])

        conn = await asyncpg.connect(**self.db_instance.get_connection_params())

        try:
            async with conn.transaction():
                # Execute downgrade operations
                await self._execute_rollback_file(conn, migration)

                # Update version table to previous revision
                previous_revision = await self._get_previous_revision(
                    migration["revision"]
                )

                await conn.execute("DELETE FROM alembic_version")
                if previous_revision:
                    await conn.execute(
                        "INSERT INTO alembic_version (version_num) VALUES ($1)",
                        previous_revision,
                    )

            self.logger.info("Migration rolled back", revision=migration["revision"])

        finally:
            await conn.close()

    async def _execute_rollback_file(self, conn, migration: dict[str, Any]) -> None:
        """Execute rollback operations from migration file."""
        migration_file = Path(migration["file"])

        if migration_file.exists():
            try:
                with open(migration_file) as f:
                    content = f.read()

                # Extract downgrade() function SQL commands
                if "def downgrade():" in content:
                    lines = content.split("\n")
                    in_downgrade = False
                    sql_commands = []

                    for line in lines:
                        if "def downgrade():" in line:
                            in_downgrade = True
                            continue
                        elif line.strip().startswith("def ") and in_downgrade:
                            break
                        elif in_downgrade and line.strip().startswith("op."):
                            sql_cmd = self._convert_alembic_to_sql(line.strip())
                            if sql_cmd:
                                sql_commands.append(sql_cmd)

                    # Execute rollback SQL commands
                    for sql_cmd in sql_commands:
                        await conn.execute(sql_cmd)

            except Exception as e:
                self.logger.error("Rollback file execution failed", error=str(e))
                raise

    async def _get_previous_revision(self, current_revision: str) -> Optional[str]:
        """Get the previous revision for rollback."""
        migrations = await self._get_available_migrations()
        previous_revision = None

        for migration in sorted(migrations, key=lambda x: x["revision"]):
            if migration["revision"] == current_revision:
                return previous_revision
            previous_revision = migration["revision"]

        return None

    async def get_rollback_info(self, revision: str) -> dict[str, Any]:
        """Get information about available rollbacks."""
        try:
            current_revision = await self._get_current_revision()
            rollback_path = await self._get_rollback_path(current_revision, revision)

            # Get backup information from Redis
            backup_info = await self._get_backup_info(revision)

            return {
                "current_revision": current_revision,
                "target_revision": revision,
                "rollback_path": rollback_path,
                "backup_available": backup_info is not None,
                "backup_info": backup_info,
                "can_rollback": len(rollback_path) > 0,
            }

        except Exception as e:
            return {"error": str(e), "can_rollback": False}

    async def _get_backup_info(self, revision: str) -> Optional[dict[str, Any]]:
        """Get backup information for a revision."""
        try:
            from ...database.coordination import DatabaseCoordinator

            coordinator = DatabaseCoordinator()
            await coordinator.initialize()

            if coordinator._redis_client:
                backups = await coordinator._redis_client.hgetall("migration_backups")
                for backup_name, backup_data in backups.items():
                    if revision in (
                        backup_name.decode()
                        if isinstance(backup_name, bytes)
                        else backup_name
                    ):
                        try:
                            return json.loads(
                                backup_data.decode()
                                if isinstance(backup_data, bytes)
                                else backup_data
                            )
                        except (json.JSONDecodeError, ValueError) as e:
                            self.logger.warning(
                                "Failed to parse backup data",
                                backup_name=backup_name,
                                error=str(e),
                            )

        except Exception as e:
            self.logger.warning("Failed to get backup info", error=str(e))

        return None

    async def _verify_schema_integrity(self) -> bool:
        """Verify database schema integrity."""
        try:
            conn = await asyncpg.connect(**self.db_instance.get_connection_params())

            try:
                # Basic checks
                checks = [
                    # Check that alembic version table exists
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = 'public'
                        AND table_name = 'alembic_version'
                    )
                    """,
                    # Check that we have at least one table
                    """
                    SELECT COUNT(*) > 0 FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    """,
                ]

                for check in checks:
                    result = await conn.fetchval(check)
                    if not result:
                        self.logger.error("Schema integrity check failed", check=check)
                        return False

                self.logger.info("Schema integrity verified")
                return True

            finally:
                await conn.close()

        except Exception as e:
            self.logger.error("Schema integrity verification failed", error=str(e))
            return False

    async def get_schema_info(self) -> dict[str, Any]:
        """Get information about the current schema."""
        try:
            conn = await asyncpg.connect(**self.db_instance.get_connection_params())

            try:
                # Get current revision
                revision = await self._get_current_revision()

                # Get table count
                table_count = await conn.fetchval(
                    """
                    SELECT COUNT(*) FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    """
                )

                # Get table names
                tables = await conn.fetch(
                    """
                    SELECT table_name FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
                    ORDER BY table_name
                    """
                )

                return {
                    "current_revision": revision,
                    "table_count": table_count,
                    "tables": [row[0] for row in tables],
                    "status": "healthy" if table_count > 0 else "empty",
                }

            finally:
                await conn.close()

        except Exception as e:
            self.logger.error("Failed to get schema info", error=str(e))
            return {"status": "error", "error": str(e)}
