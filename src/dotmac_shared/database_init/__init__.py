"""
Database Initialization Service for DotMac Framework

This package provides automated database setup for each ISP container, including:
- Per-container database creation (PostgreSQL instances)
- Schema migration execution for new databases
- Initial data seeding (admin users, default configs)
- Database health monitoring integration
- Backup configuration setup per database

Key Components:
- DatabaseCreator: Handles database and user creation
- SchemaManager: Manages schema migrations and updates
- SeedManager: Handles initial data seeding
- ConnectionValidator: Validates database connectivity and health
"""

from .core.connection_validator import ConnectionValidator, HealthStatus
from .core.database_creator import DatabaseCreator, DatabaseInstance
from .core.schema_manager import SchemaManager
from .core.seed_manager import SeedManager

__version__ = "1.0.0"
__all__ = [
    "DatabaseCreator",
    "DatabaseInstance",
    "SchemaManager",
    "SeedManager",
    "ConnectionValidator",
    "HealthStatus",
]
