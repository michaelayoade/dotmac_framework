import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add parent directory to path to import models
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Import models to ensure they are registered - explicit imports for security
from app.models.base import Base as ModelBase
from app.models.billing import (
    PricingPlan, Subscription, Invoice, Payment, UsageRecord, Commission
)
from app.models.deployment import (
    InfrastructureTemplate, Deployment, DeploymentEvent, DeploymentResource
)
from app.models.monitoring import (
    HealthCheck, Metric, Alert, SLARecord
)
from app.models.plugin import (
    PluginCategory, Plugin, PluginLicense, PluginUsage
)
from app.models.tenant import (
    Tenant, TenantConfiguration, TenantInvitation
)
from app.models.user import (
    User, UserSession, UserRole, UserInvitation
)
from app.models.partner import (
    Partner, PartnerCustomer, Commission, Territory, PartnerPerformanceMetrics
)
from app.database import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config
def get_url():
    return os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
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