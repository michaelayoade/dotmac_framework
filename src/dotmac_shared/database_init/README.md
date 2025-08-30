# Database Initialization Service

Automated database setup service for DotMac Framework ISP containers.

## Overview

This service provides automated database initialization for ISP containers, including:

- **Per-container database creation**: Creates dedicated PostgreSQL databases for each ISP
- **Schema management**: Executes migrations and maintains schema consistency
- **Data seeding**: Populates initial data (admin users, default configurations)
- **Health monitoring**: Validates database connectivity and performance
- **Backup setup**: Configures automated backup systems

## Key Components

### DatabaseCreator

- Creates PostgreSQL databases and users for ISP containers
- Manages database connection strings and credentials
- Handles database lifecycle operations

### SchemaManager

- Executes Alembic migrations for new databases
- Manages schema versions and updates
- Validates schema integrity

### SeedManager

- Seeds initial data (admin users, system configs)
- Handles data templates and customization
- Supports incremental seeding

### ConnectionValidator

- Tests database connectivity and performance
- Monitors database health status
- Provides health check endpoints

## Usage

```python
from dotmac_shared.database_init import (
    DatabaseCreator,
    SchemaManager,
    SeedManager,
    ConnectionValidator
)
import asyncio
from uuid import uuid4

async def setup_isp_database():
    # Configuration
    isp_id = uuid4()
    db_config = DatabaseConfig(
        host="localhost",
        port=5432,
        username="postgres",
        password="password",
        database_name=f"isp_{isp_id}"
    )

    # Create database
    creator = DatabaseCreator()
    db_instance = await creator.create_isp_database(isp_id, db_config)

    # Initialize schema
    schema_manager = SchemaManager(db_instance)
    await schema_manager.initialize_schema()

    # Seed initial data
    seed_manager = SeedManager(db_instance)
    await seed_manager.seed_initial_data()

    # Validate setup
    validator = ConnectionValidator(db_instance)
    health_status = await validator.validate_database_health()

    print(f"Database setup complete: {health_status}")

# Run setup
asyncio.run(setup_isp_database())
```

## API Reference

### Core Functions

```python
async def create_isp_database(
    isp_id: UUID,
    db_config: DatabaseConfig
) -> DatabaseInstance
```

Creates a new database instance for an ISP.

```python
async def initialize_schema(db_instance: DatabaseInstance) -> bool
```

Initializes the database schema using migrations.

```python
async def seed_initial_data(db_instance: DatabaseInstance) -> bool
```

Seeds the database with initial data.

```python
async def validate_database_health(db_instance: DatabaseInstance) -> HealthStatus
```

Validates database connectivity and health.

## Configuration

### Environment Variables

- `POSTGRES_HOST`: PostgreSQL host (default: localhost)
- `POSTGRES_PORT`: PostgreSQL port (default: 5432)
- `POSTGRES_ADMIN_USER`: Admin username (default: postgres)
- `POSTGRES_ADMIN_PASSWORD`: Admin password
- `REDIS_URL`: Redis connection string for coordination
- `BACKUP_ENABLED`: Enable automated backups (default: true)

### Database Templates

The service includes SQL templates for:

- **ISP Schema**: Core tables for ISP operations
- **Seed Data**: Default admin users and system configurations
- **Performance Indexes**: Optimized indexes for common queries

## Development

### Setup

```bash
cd /home/dotmac_framework/src/dotmac_shared/database_init
pip install -e .[dev]
```

### Testing

```bash
pytest tests/
```

### Type Checking

```bash
mypy dotmac_shared/database_init/
```

## Architecture

The service follows a modular architecture with clear separation of concerns:

```
database_init/
├── core/
│   ├── database_creator.py      # Database creation logic
│   ├── schema_manager.py        # Migration management
│   ├── seed_manager.py          # Initial data seeding
│   └── connection_validator.py  # Connection testing
├── templates/
│   ├── isp_schema.sql          # ISP database schema
│   ├── seed_data.sql           # Default data
│   └── indexes.sql             # Performance indexes
└── tests/
    └── test_database_init.py   # Comprehensive tests
```

## Error Handling

The service includes comprehensive error handling for:

- Connection failures
- Migration errors
- Seeding conflicts
- Schema validation issues
- Resource cleanup

All operations are designed to be idempotent and safely retryable.

## Security

- Database credentials are securely managed
- Row-level security is applied where appropriate
- Audit logging for all operations
- Input validation and sanitization
