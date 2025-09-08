"""
Main entry point for the Database Initialization Service.

This module provides a command-line interface for database initialization operations.
"""

import argparse
import asyncio
import json
import sys
from uuid import UUID, uuid4

import structlog

from . import (
    ConnectionValidator,
    DatabaseCreator,
    HealthStatus,
    SchemaManager,
    SeedManager,
)
from .core.database_creator import DatabaseConfig

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


async def create_database_command(args) -> int:
    """Create a new ISP database."""
    try:
        config = DatabaseConfig(
            host=args.host,
            port=args.port,
            admin_username=args.admin_username,
            admin_password=args.admin_password,
        )

        creator = DatabaseCreator(config)
        isp_id = UUID(args.isp_id) if args.isp_id else uuid4()

        logger.info("Creating ISP database", isp_id=str(isp_id))

        db_instance = await creator.create_isp_database(isp_id, config)

        result = {
            "success": True,
            "isp_id": str(db_instance.isp_id),
            "database_name": db_instance.database_name,
            "username": db_instance.username,
            "connection_string": db_instance.connection_string,
            "created_at": db_instance.created_at.isoformat(),
        }

        logger.info(json.dumps(result, indent=2))
        logger.info("Database created successfully", database_name=db_instance.database_name)

        return 0

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }
        logger.info(json.dumps(error_result, indent=2))
        logger.error("Failed to create database", error=str(e), exc_info=True)
        return 1


async def initialize_schema_command(args) -> int:
    """Initialize database schema."""
    try:
        from .core.database_creator import DatabaseInstance

        # Reconstruct database instance from arguments
        db_instance = DatabaseInstance(
            isp_id=UUID(args.isp_id),
            database_name=args.database_name,
            username=args.username,
            password=args.password,
            host=args.host,
            port=args.port,
            connection_string=f"postgresql://{args.username}:{args.password}@{args.host}:{args.port}/{args.database_name}",
            created_at=None,  # Not needed for schema initialization
            status="existing",
        )

        schema_manager = SchemaManager(db_instance)

        logger.info("Initializing database schema", database_name=args.database_name)

        success = await schema_manager.initialize_schema()

        # Get schema info
        schema_info = await schema_manager.get_schema_info()

        result = {"success": success, "schema_info": schema_info}

        logger.info(json.dumps(result, indent=2))

        if success:
            logger.info("Schema initialized successfully")
            return 0
        else:
            logger.error("Schema initialization failed")
            return 1

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }
        logger.info(json.dumps(error_result, indent=2))
        logger.error("Failed to initialize schema", error=str(e), exc_info=True)
        return 1


async def seed_data_command(args) -> int:
    """Seed initial data."""
    try:
        from .core.database_creator import DatabaseInstance

        # Reconstruct database instance from arguments
        db_instance = DatabaseInstance(
            isp_id=UUID(args.isp_id),
            database_name=args.database_name,
            username=args.username,
            password=args.password,
            host=args.host,
            port=args.port,
            connection_string=f"postgresql://{args.username}:{args.password}@{args.host}:{args.port}/{args.database_name}",
            created_at=None,
            status="existing",
        )

        seed_manager = SeedManager(db_instance)

        # Load custom data if provided
        custom_data = None
        if args.custom_data:
            with open(args.custom_data) as f:
                custom_data = json.load(f)

        logger.info("Seeding initial data", database_name=args.database_name)

        success = await seed_manager.seed_initial_data(custom_data)

        # Get seed status
        seed_status = await seed_manager.get_seed_status()

        result = {"success": success, "seed_status": seed_status}

        logger.info(json.dumps(result, indent=2))

        if success:
            logger.info("Data seeded successfully")
            return 0
        else:
            logger.error("Data seeding failed")
            return 1

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }
        logger.info(json.dumps(error_result, indent=2))
        logger.error("Failed to seed data", error=str(e), exc_info=True)
        return 1


async def validate_health_command(args) -> int:
    """Validate database health."""
    try:
        from .core.database_creator import DatabaseInstance

        # Reconstruct database instance from arguments
        db_instance = DatabaseInstance(
            isp_id=UUID(args.isp_id),
            database_name=args.database_name,
            username=args.username,
            password=args.password,
            host=args.host,
            port=args.port,
            connection_string=f"postgresql://{args.username}:{args.password}@{args.host}:{args.port}/{args.database_name}",
            created_at=None,
            status="existing",
        )

        validator = ConnectionValidator(db_instance)

        logger.info("Validating database health", database_name=args.database_name)

        health_result = await validator.validate_database_health()

        result = {
            "status": health_result.status.value,
            "response_time_ms": health_result.response_time_ms,
            "timestamp": health_result.timestamp.isoformat(),
            "details": health_result.details,
            "error": health_result.error,
        }

        logger.info(json.dumps(result, indent=2))

        # Clean up resources
        await validator.cleanup()

        if health_result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]:
            logger.info("Health validation completed", status=health_result.status.value)
            return 0
        else:
            logger.error("Database is unhealthy", status=health_result.status.value)
            return 1

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }
        logger.info(json.dumps(error_result, indent=2))
        logger.error("Failed to validate health", error=str(e), exc_info=True)
        return 1


async def full_initialization_command(args) -> int:
    """Perform full database initialization (create + schema + seed + validate)."""
    try:
        config = DatabaseConfig(
            host=args.host,
            port=args.port,
            admin_username=args.admin_username,
            admin_password=args.admin_password,
        )

        creator = DatabaseCreator(config)
        isp_id = UUID(args.isp_id) if args.isp_id else uuid4()

        # Step 1: Create database
        logger.info("Step 1: Creating database", isp_id=str(isp_id))
        db_instance = await creator.create_isp_database(isp_id, config)

        # Step 2: Initialize schema
        logger.info("Step 2: Initializing schema")
        schema_manager = SchemaManager(db_instance)
        schema_success = await schema_manager.initialize_schema()

        if not schema_success:
            raise RuntimeError("Schema initialization failed")

        # Step 3: Seed data
        logger.info("Step 3: Seeding initial data")
        seed_manager = SeedManager(db_instance)

        custom_data = None
        if args.custom_data:
            with open(args.custom_data) as f:
                custom_data = json.load(f)

        seed_success = await seed_manager.seed_initial_data(custom_data)

        if not seed_success:
            raise RuntimeError("Data seeding failed")

        # Step 4: Validate health
        logger.info("Step 4: Validating database health")
        validator = ConnectionValidator(db_instance)
        health_result = await validator.validate_database_health()

        # Compile results
        result = {
            "success": True,
            "isp_id": str(db_instance.isp_id),
            "database_name": db_instance.database_name,
            "username": db_instance.username,
            "connection_string": db_instance.connection_string,
            "created_at": db_instance.created_at.isoformat(),
            "schema_initialized": schema_success,
            "data_seeded": seed_success,
            "health_status": health_result.status.value,
            "health_details": health_result.details,
        }

        logger.info(json.dumps(result, indent=2))

        # Clean up resources
        await validator.cleanup()

        logger.info("Full initialization completed successfully")
        return 0

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__,
        }
        logger.info(json.dumps(error_result, indent=2))
        logger.error("Full initialization failed", error=str(e), exc_info=True)
        return 1


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Database Initialization Service for DotMac Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full initialization
  python -m dotmac_shared.database_init full-init --host localhost --admin-password secret

  # Create database only
  python -m dotmac_shared.database_init create --host localhost --admin-password secret --isp-id 12345678-1234-1234-1234-123456789012

  # Initialize schema only
  python -m dotmac_shared.database_init init-schema --database-name isp_12345 --username isp_user --password userpass

  # Seed data only
  python -m dotmac_shared.database_init seed --database-name isp_12345 --username isp_user --password userpass

  # Check health
  python -m dotmac_shared.database_init health --database-name isp_12345 --username isp_user --password userpass
        """,
    )

    # Global arguments
    parser.add_argument("--host", default="localhost", help="Database host")
    parser.add_argument("--port", type=int, default=5432, help="Database port")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create database command
    create_parser = subparsers.add_parser("create", help="Create a new ISP database")
    create_parser.add_argument("--admin-username", default="postgres", help="Database admin username")
    create_parser.add_argument("--admin-password", required=True, help="Database admin password")
    create_parser.add_argument("--isp-id", help="ISP UUID (generated if not provided)")
    create_parser.set_defaults(func=create_database_command)

    # Initialize schema command
    schema_parser = subparsers.add_parser("init-schema", help="Initialize database schema")
    schema_parser.add_argument("--database-name", required=True, help="Database name")
    schema_parser.add_argument("--username", required=True, help="Database username")
    schema_parser.add_argument("--password", required=True, help="Database password")
    schema_parser.add_argument("--isp-id", required=True, help="ISP UUID")
    schema_parser.set_defaults(func=initialize_schema_command)

    # Seed data command
    seed_parser = subparsers.add_parser("seed", help="Seed initial data")
    seed_parser.add_argument("--database-name", required=True, help="Database name")
    seed_parser.add_argument("--username", required=True, help="Database username")
    seed_parser.add_argument("--password", required=True, help="Database password")
    seed_parser.add_argument("--isp-id", required=True, help="ISP UUID")
    seed_parser.add_argument("--custom-data", help="Path to custom seed data JSON file")
    seed_parser.set_defaults(func=seed_data_command)

    # Health validation command
    health_parser = subparsers.add_parser("health", help="Validate database health")
    health_parser.add_argument("--database-name", required=True, help="Database name")
    health_parser.add_argument("--username", required=True, help="Database username")
    health_parser.add_argument("--password", required=True, help="Database password")
    health_parser.add_argument("--isp-id", required=True, help="ISP UUID")
    health_parser.set_defaults(func=validate_health_command)

    # Full initialization command
    full_parser = subparsers.add_parser("full-init", help="Perform full database initialization")
    full_parser.add_argument("--admin-username", default="postgres", help="Database admin username")
    full_parser.add_argument("--admin-password", required=True, help="Database admin password")
    full_parser.add_argument("--isp-id", help="ISP UUID (generated if not provided)")
    full_parser.add_argument("--custom-data", help="Path to custom seed data JSON file")
    full_parser.set_defaults(func=full_initialization_command)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Configure logging level
    import logging

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    # Run the async command
    return asyncio.run(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
