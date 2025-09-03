"""
Database Creator - Handles database and user creation for ISP containers.
"""

import asyncio
import logging
import secrets
import string
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

import asyncpg
import structlog
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger(__name__)


@dataclass
class DatabaseConfig:
    """Configuration for database creation."""

    host: str = "localhost"
    port: int = 5432
    admin_username: str = "postgres"
    admin_password: str = ""
    database_name: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_mode: str = "prefer"
    pool_size: int = 10
    max_overflow: int = 20


@dataclass
class DatabaseInstance:
    """Represents a created database instance."""

    isp_id: UUID
    database_name: str
    username: str
    password: str
    host: str
    port: int
    connection_string: str
    created_at: datetime
    status: str = "created"

    def get_connection_params(self) -> Dict[str, Any]:
        """Get connection parameters for asyncpg."""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database_name,
            "user": self.username,
            "password": self.password,
        }


class DatabaseCreator:
    """Creates and manages ISP databases."""

    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self.logger = logger.bind(component="database_creator")

    def _generate_secure_password(self, length: int = 32) -> str:
        """Generate a secure random password."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(alphabet) for _ in range(length))

    async def _get_admin_connection(self) -> asyncpg.Connection:
        """Get connection as database administrator."""
        return await asyncpg.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.admin_username,
            password=self.config.admin_password,
            database="postgres",  # Connect to default postgres database
        )

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def create_isp_database(
        self, isp_id: UUID, db_config: Optional[DatabaseConfig] = None
    ) -> DatabaseInstance:
        """
        Create a new database for an ISP container.

        Args:
            isp_id: Unique identifier for the ISP
            db_config: Database configuration (optional)

        Returns:
            DatabaseInstance with connection details
        """
        config = db_config or self.config

        # Generate database and user names
        database_name = f"isp_{str(isp_id).replace('-', '_')}"
        username = f"isp_user_{str(isp_id).replace('-', '_')}"
        password = self._generate_secure_password()

        self.logger.info(
            "Creating ISP database",
            isp_id=str(isp_id),
            database_name=database_name,
            username=username,
        )

        try:
            # Connect as admin to create database and user
            admin_conn = await self._get_admin_connection()

            try:
                # Check if database already exists
                existing_db = await admin_conn.fetchval(
                    "SELECT 1 FROM pg_database WHERE datname = $1", database_name
                )

                if existing_db:
                    self.logger.warning(
                        "Database already exists", database_name=database_name
                    )
                    # For existing databases, we'll return existing instance
                    # In production, you might want to handle this differently
                    return await self._get_existing_database_instance(
                        isp_id, database_name, admin_conn
                    )

                # Create user first
                await self._create_database_user(admin_conn, username, password)

                # Create database
                await self._create_database(admin_conn, database_name, username)

                # Configure database permissions and extensions
                await self._configure_database(database_name, username, password)

                # Create database instance object
                connection_string = (
                    f"postgresql://{username}:{password}@{config.host}:"
                    f"{config.port}/{database_name}"
                )

                db_instance = DatabaseInstance(
                    isp_id=isp_id,
                    database_name=database_name,
                    username=username,
                    password=password,
                    host=config.host,
                    port=config.port,
                    connection_string=connection_string,
                    created_at=datetime.now(timezone.utc),
                    status="created",
                )

                self.logger.info(
                    "ISP database created successfully",
                    isp_id=str(isp_id),
                    database_name=database_name,
                )

                return db_instance

            finally:
                await admin_conn.close()

        except Exception as e:
            self.logger.error(
                "Failed to create ISP database",
                isp_id=str(isp_id),
                error=str(e),
                exc_info=True,
            )
            raise

    async def _create_database_user(
        self, admin_conn: asyncpg.Connection, username: str, password: str
    ) -> None:
        """Create a database user."""
        # Check if user already exists
        existing_user = await admin_conn.fetchval(
            "SELECT 1 FROM pg_roles WHERE rolname = $1", username
        )

        if existing_user:
            self.logger.info("Database user already exists", username=username)
            # Update password for existing user
            await admin_conn.execute(
                f'ALTER USER "{username}" WITH PASSWORD $1', password
            )
        else:
            # Create new user
            await admin_conn.execute(
                f'CREATE USER "{username}" WITH PASSWORD $1 LOGIN CREATEDB', password
            )
            self.logger.info("Database user created", username=username)

    async def _create_database(
        self, admin_conn: asyncpg.Connection, database_name: str, owner: str
    ) -> None:
        """Create a database."""
        await admin_conn.execute(
            f'CREATE DATABASE "{database_name}" OWNER "{owner}" '
            f"ENCODING 'UTF8' LC_COLLATE 'en_US.UTF-8' LC_CTYPE 'en_US.UTF-8'"
        )

        # Grant all privileges to owner
        await admin_conn.execute(
            f'GRANT ALL PRIVILEGES ON DATABASE "{database_name}" TO "{owner}"'
        )

        self.logger.info("Database created", database_name=database_name)

    async def _configure_database(
        self, database_name: str, username: str, password: str
    ) -> None:
        """Configure database extensions and permissions."""
        # Connect to the new database to configure it
        db_conn = await asyncpg.connect(
            host=self.config.host,
            port=self.config.port,
            database=database_name,
            user=username,
            password=password,
        )

        try:
            # Create commonly needed extensions
            extensions = [
                "uuid-ossp",  # UUID functions
                "pg_trgm",  # Trigram matching for search
                "btree_gin",  # Additional indexing options
            ]

            for extension in extensions:
                try:
                    await db_conn.execute(
                        f'CREATE EXTENSION IF NOT EXISTS "{extension}"'
                    )
                    self.logger.debug("Extension created", extension=extension)
                except Exception as e:
                    # Some extensions might not be available, log but continue
                    self.logger.warning(
                        "Could not create extension", extension=extension, error=str(e)
                    )

            # Set up database-level configurations
            await db_conn.execute(
                "ALTER DATABASE $1 SET timezone TO 'UTC'", database_name
            )

            self.logger.info(
                "Database configured successfully", database_name=database_name
            )

        finally:
            await db_conn.close()

    async def _get_existing_database_instance(
        self, isp_id: UUID, database_name: str, admin_conn: asyncpg.Connection
    ) -> DatabaseInstance:
        """Get details for an existing database."""
        # This would typically retrieve stored credentials
        # For now, we'll raise an error for existing databases
        raise ValueError(
            f"Database {database_name} already exists. "
            "Cannot recreate without explicit force flag."
        )

    async def delete_isp_database(self, db_instance: DatabaseInstance) -> bool:
        """
        Delete an ISP database (use with caution).

        Args:
            db_instance: Database instance to delete

        Returns:
            True if deletion was successful
        """
        self.logger.warning(
            "Deleting ISP database",
            isp_id=str(db_instance.isp_id),
            database_name=db_instance.database_name,
        )

        try:
            admin_conn = await self._get_admin_connection()

            try:
                # Terminate active connections to the database
                await admin_conn.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = $1 AND pid <> pg_backend_pid()",
                    db_instance.database_name,
                )

                # Drop database
                await admin_conn.execute(
                    f'DROP DATABASE IF EXISTS "{db_instance.database_name}"'
                )

                # Drop user
                await admin_conn.execute(
                    f'DROP USER IF EXISTS "{db_instance.username}"'
                )

                self.logger.info(
                    "ISP database deleted successfully",
                    isp_id=str(db_instance.isp_id),
                    database_name=db_instance.database_name,
                )

                return True

            finally:
                await admin_conn.close()

        except Exception as e:
            self.logger.error(
                "Failed to delete ISP database",
                isp_id=str(db_instance.isp_id),
                error=str(e),
                exc_info=True,
            )
            return False

    async def list_isp_databases(self) -> Dict[str, Any]:
        """List all ISP databases."""
        try:
            admin_conn = await self._get_admin_connection()

            try:
                # Query for databases starting with 'isp_'
                databases = await admin_conn.fetch(
                    "SELECT datname, datowner FROM pg_database "
                    "WHERE datname LIKE 'isp_%' ORDER BY datname"
                )

                result = {"databases": [], "total_count": len(databases)}

                for db in databases:
                    # Get owner name
                    owner = await admin_conn.fetchval(
                        "SELECT rolname FROM pg_roles WHERE oid = $1", db["datowner"]
                    )

                    result["databases"].append({"name": db["datname"], "owner": owner})

                return result

            finally:
                await admin_conn.close()

        except Exception as e:
            self.logger.error(
                "Failed to list ISP databases", error=str(e), exc_info=True
            )
            raise

    async def validate_database_connection(self, db_instance: DatabaseInstance) -> bool:
        """Validate that we can connect to the database."""
        try:
            conn = await asyncpg.connect(**db_instance.get_connection_params())
            await conn.fetchval("SELECT 1")
            await conn.close()
            return True
        except Exception as e:
            self.logger.error(
                "Database connection validation failed",
                database_name=db_instance.database_name,
                error=str(e),
            )
            return False
