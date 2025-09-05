"""
Seed Manager - Handles initial data seeding for ISP databases.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import asyncpg
import structlog
from jinja2 import Environment, FileSystemLoader, TemplateNotFound
from tenacity import retry, stop_after_attempt, wait_exponential

from .database_creator import DatabaseInstance

logger = structlog.get_logger(__name__)


class SeedManager:
    """Manages initial data seeding for ISP databases."""

    def __init__(
        self, db_instance: DatabaseInstance, templates_path: Optional[str] = None
    ):
        self.db_instance = db_instance
        self.logger = logger.bind(
            component="seed_manager", database=db_instance.database_name
        )

        # Set up templates path
        self.templates_path = templates_path or self._get_default_templates_path()

        # Initialize Jinja2 environment for template rendering
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_path),
            autoescape=False,  # We're generating SQL, not HTML
        )

    def _get_default_templates_path(self) -> str:
        """Get default path for seed data templates."""
        package_dir = Path(__file__).parent.parent
        return str(package_dir / "templates")

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def seed_initial_data(
        self, custom_data: Optional[dict[str, Any]] = None
    ) -> bool:
        """
        Seed the database with initial data.

        Args:
            custom_data: Custom data to override defaults

        Returns:
            True if seeding was successful
        """
        self.logger.info("Starting initial data seeding")

        try:
            # Validate database connection
            if not await self._validate_database_connection():
                raise RuntimeError("Cannot connect to database")

            # Generate default data context
            seed_context = await self._generate_seed_context(custom_data)

            # Seed data in order of dependencies
            await self._seed_system_data(seed_context)
            await self._seed_admin_users(seed_context)
            await self._seed_default_configurations(seed_context)
            await self._seed_sample_data(seed_context)

            # Verify seeded data
            if await self._verify_seeded_data():
                self.logger.info("Initial data seeding completed successfully")
                return True
            else:
                raise RuntimeError("Data verification failed")

        except Exception as e:
            self.logger.error(
                "Initial data seeding failed", error=str(e), exc_info=True
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

    async def _generate_seed_context(
        self, custom_data: Optional[dict[str, Any]] = None
    ) -> dict[str, Any]:
        """Generate context data for seeding templates."""
        context = {
            "isp_id": str(self.db_instance.isp_id),
            "database_name": self.db_instance.database_name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "admin_user": {
                "id": str(uuid4()),
                "username": "admin",
                "email": f"admin@{self.db_instance.database_name}.local",
                "password_hash": "$2b$12$rQiU9KrJ4wS.8P2L9jN.2eHgF5J9Lv3M7c4K6d8E0qW2rT5yU9iO",  # "admin123"
                "full_name": "System Administrator",
                "is_active": True,
                "is_superuser": True,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            "system_config": {
                "company_name": f"ISP {self.db_instance.isp_id}",
                "default_timezone": "UTC",
                "default_currency": "USD",
                "default_language": "en",
                "system_email": f"system@{self.db_instance.database_name}.local",
                "support_email": f"support@{self.db_instance.database_name}.local",
            },
            "service_plans": [
                {
                    "id": str(uuid4()),
                    "name": "Basic Internet",
                    "description": "Basic residential internet service",
                    "speed_download": 25,
                    "speed_upload": 3,
                    "data_limit_gb": None,
                    "monthly_price": 39.99,
                    "is_active": True,
                },
                {
                    "id": str(uuid4()),
                    "name": "Premium Internet",
                    "description": "High-speed residential internet service",
                    "speed_download": 100,
                    "speed_upload": 10,
                    "data_limit_gb": None,
                    "monthly_price": 69.99,
                    "is_active": True,
                },
                {
                    "id": str(uuid4()),
                    "name": "Business Internet",
                    "description": "Business-grade internet with SLA",
                    "speed_download": 200,
                    "speed_upload": 50,
                    "data_limit_gb": None,
                    "monthly_price": 149.99,
                    "is_active": True,
                },
            ],
        }

        # Override with custom data if provided
        if custom_data:
            context.update(custom_data)

        return context

    async def _seed_system_data(self, context: dict[str, Any]) -> None:
        """Seed system-level data."""
        self.logger.info("Seeding system data")

        try:
            # Load and render system data template
            sql_content = await self._load_template("system_data.sql", context)

            if sql_content:
                await self._execute_sql(sql_content, "System data seeding")

        except TemplateNotFound:
            self.logger.info("No system data template found, skipping")
        except Exception as e:
            self.logger.error("Failed to seed system data", error=str(e))
            raise

    async def _seed_admin_users(self, context: dict[str, Any]) -> None:
        """Seed admin users."""
        self.logger.info("Seeding admin users")

        try:
            # Load and render admin users template
            sql_content = await self._load_template("admin_users.sql", context)

            if sql_content:
                await self._execute_sql(sql_content, "Admin users seeding")

            # Also create admin user directly if template doesn't exist
            await self._create_default_admin_user(context)

        except TemplateNotFound:
            # Create admin user directly
            await self._create_default_admin_user(context)
        except Exception as e:
            self.logger.error("Failed to seed admin users", error=str(e))
            raise

    async def _create_default_admin_user(self, context: dict[str, Any]) -> None:
        """Create default admin user directly."""
        admin = context["admin_user"]

        conn = await asyncpg.connect(**self.db_instance.get_connection_params())

        try:
            # Check if users table exists
            table_exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'users'
                )
                """
            )

            if table_exists:
                # Check if admin user already exists
                existing_admin = await conn.fetchval(
                    "SELECT id FROM users WHERE username = $1 OR email = $2",
                    admin["username"],
                    admin["email"],
                )

                if not existing_admin:
                    await conn.execute(
                        """
                        INSERT INTO users (
                            id, username, email, password_hash, full_name,
                            is_active, is_superuser, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                        """,
                        admin["id"],
                        admin["username"],
                        admin["email"],
                        admin["password_hash"],
                        admin["full_name"],
                        admin["is_active"],
                        admin["is_superuser"],
                        admin["created_at"],
                    )

                    self.logger.info(
                        "Default admin user created", username=admin["username"]
                    )
                else:
                    self.logger.info("Admin user already exists")
            else:
                self.logger.info("Users table not found, skipping admin user creation")

        finally:
            await conn.close()

    async def _seed_default_configurations(self, context: dict[str, Any]) -> None:
        """Seed default configurations."""
        self.logger.info("Seeding default configurations")

        try:
            # Load and render configurations template
            sql_content = await self._load_template("default_configs.sql", context)

            if sql_content:
                await self._execute_sql(sql_content, "Default configurations seeding")

            # Also create configurations directly
            await self._create_default_configurations(context)

        except TemplateNotFound:
            # Create configurations directly
            await self._create_default_configurations(context)
        except Exception as e:
            self.logger.error("Failed to seed default configurations", error=str(e))
            raise

    async def _create_default_configurations(self, context: dict[str, Any]) -> None:
        """Create default configurations directly."""
        conn = await asyncpg.connect(**self.db_instance.get_connection_params())

        try:
            # Check if configurations table exists
            table_exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'configurations'
                )
                """
            )

            if table_exists:
                config = context["system_config"]

                # Insert configurations
                for key, value in config.items():
                    await conn.execute(
                        """
                        INSERT INTO configurations (key, value, description, created_at)
                        VALUES ($1, $2, $3, $4)
                        ON CONFLICT (key) DO NOTHING
                        """,
                        key,
                        str(value),
                        f"Default {key} configuration",
                        datetime.now(timezone.utc),
                    )

                self.logger.info("Default configurations created")
            else:
                self.logger.info("Configurations table not found, skipping")

        finally:
            await conn.close()

    async def _seed_sample_data(self, context: dict[str, Any]) -> None:
        """Seed sample data (service plans, etc.)."""
        self.logger.info("Seeding sample data")

        try:
            # Load and render sample data template
            sql_content = await self._load_template("sample_data.sql", context)

            if sql_content:
                await self._execute_sql(sql_content, "Sample data seeding")

            # Also create sample data directly
            await self._create_sample_service_plans(context)

        except TemplateNotFound:
            # Create sample data directly
            await self._create_sample_service_plans(context)
        except Exception as e:
            self.logger.error("Failed to seed sample data", error=str(e))
            raise

    async def _create_sample_service_plans(self, context: dict[str, Any]) -> None:
        """Create sample service plans directly."""
        conn = await asyncpg.connect(**self.db_instance.get_connection_params())

        try:
            # Check if service_plans table exists
            table_exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'service_plans'
                )
                """
            )

            if table_exists:
                for plan in context["service_plans"]:
                    await conn.execute(
                        """
                        INSERT INTO service_plans (
                            id, name, description, speed_download, speed_upload,
                            data_limit_gb, monthly_price, is_active, created_at
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                        ON CONFLICT (id) DO NOTHING
                        """,
                        plan["id"],
                        plan["name"],
                        plan["description"],
                        plan["speed_download"],
                        plan["speed_upload"],
                        plan["data_limit_gb"],
                        plan["monthly_price"],
                        plan["is_active"],
                        datetime.now(timezone.utc),
                    )

                self.logger.info("Sample service plans created")
            else:
                self.logger.info("Service plans table not found, skipping")

        finally:
            await conn.close()

    async def _load_template(
        self, template_name: str, context: dict[str, Any]
    ) -> Optional[str]:
        """Load and render a SQL template."""
        try:
            template = self.jinja_env.get_template(template_name)
            return template.render(context)
        except TemplateNotFound:
            self.logger.debug("Template not found", template=template_name)
            raise
        except Exception as e:
            self.logger.error(
                "Failed to render template", template=template_name, error=str(e)
            )
            raise

    async def _execute_sql(self, sql_content: str, description: str) -> None:
        """Execute SQL content."""
        conn = await asyncpg.connect(**self.db_instance.get_connection_params())

        try:
            async with conn.transaction():
                # Split SQL by semicolon and execute each statement
                statements = [
                    stmt.strip() for stmt in sql_content.split(";") if stmt.strip()
                ]

                for stmt in statements:
                    if stmt:
                        await conn.execute(stmt)

                self.logger.info("SQL executed successfully", description=description)

        finally:
            await conn.close()

    async def _verify_seeded_data(self) -> bool:
        """Verify that seeded data was inserted correctly."""
        try:
            conn = await asyncpg.connect(**self.db_instance.get_connection_params())

            try:
                verification_queries = [
                    # Check if we have any data in common tables
                    ("users", "SELECT COUNT(*) FROM users WHERE is_superuser = true"),
                    ("configurations", "SELECT COUNT(*) FROM configurations"),
                    (
                        "service_plans",
                        "SELECT COUNT(*) FROM service_plans WHERE is_active = true",
                    ),
                ]

                results = {}
                for table_name, query in verification_queries:
                    try:
                        count = await conn.fetchval(query)
                        results[table_name] = count if count is not None else 0
                    except Exception:
                        # Table might not exist
                        results[table_name] = -1  # Indicates table not found

                # Log verification results
                self.logger.info("Data verification results", results=results)

                # Consider seeding successful if at least some data was inserted
                return any(count > 0 for count in results.values())

            finally:
                await conn.close()

        except Exception as e:
            self.logger.error("Data verification failed", error=str(e))
            return False

    async def get_seed_status(self) -> dict[str, Any]:
        """Get status of seeded data."""
        try:
            conn = await asyncpg.connect(**self.db_instance.get_connection_params())

            try:
                # Get counts from various tables
                status_queries = {
                    "admin_users": "SELECT COUNT(*) FROM users WHERE is_superuser = true",
                    "total_users": "SELECT COUNT(*) FROM users",
                    "configurations": "SELECT COUNT(*) FROM configurations",
                    "service_plans": "SELECT COUNT(*) FROM service_plans",
                    "active_service_plans": "SELECT COUNT(*) FROM service_plans WHERE is_active = true",
                }

                status = {}
                for key, query in status_queries.items():
                    try:
                        count = await conn.fetchval(query)
                        status[key] = count if count is not None else 0
                    except Exception:
                        status[key] = None  # Table doesn't exist

                return {
                    "status": (
                        "seeded"
                        if any(v and v > 0 for v in status.values())
                        else "empty"
                    ),
                    "details": status,
                }

            finally:
                await conn.close()

        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def reset_seed_data(self) -> bool:
        """Reset/clear seeded data (use with caution)."""
        self.logger.warning("Resetting seed data")

        try:
            conn = await asyncpg.connect(**self.db_instance.get_connection_params())

            try:
                # Clear seeded data from common tables
                clear_queries = [
                    "DELETE FROM service_plans WHERE created_at >= CURRENT_DATE",
                    "DELETE FROM configurations WHERE created_at >= CURRENT_DATE",
                    "DELETE FROM users WHERE is_superuser = true AND username = 'admin'",
                ]

                async with conn.transaction():
                    for query in clear_queries:
                        try:
                            await conn.execute(query)
                        except Exception as e:
                            self.logger.warning(
                                "Failed to execute clear query",
                                query=query,
                                error=str(e),
                            )

                self.logger.info("Seed data reset completed")
                return True

            finally:
                await conn.close()

        except Exception as e:
            self.logger.error("Failed to reset seed data", error=str(e))
            return False
