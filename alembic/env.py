from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# Add the src directory to the path so we can import our models
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

"""
Model discovery for Alembic autogenerate

Many packages define their own `Base = declarative_base()`. We aggregate
all discovered SQLAlchemy metadata into a list so Alembic autogenerate can
compare across modules.
"""
from importlib import import_module
from typing import List

metadata_list: List = []

def _try_collect(module_name: str, base_attr: str = "Base") -> None:
    try:
        m = import_module(module_name)
        base = getattr(m, base_attr, None)
        if base is not None and hasattr(base, "metadata"):
            md = base.metadata
            if md not in metadata_list:
                metadata_list.append(md)
    except Exception as e:
        print(f"[alembic] Skipping metadata from {module_name}: {e}")

# Choose which models to collect based on SERVICE_TYPE environment variable
service_type = os.getenv("SERVICE_TYPE", "management")

if service_type == "isp":
    # ISP framework models only
    _try_collect("dotmac_isp.models")
else:
    # Management platform models (default)
    _try_collect("dotmac_management.models")

# Fallback to None if nothing found
target_metadata = metadata_list if metadata_list else None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url():
    """Get database URL from environment variable or config."""
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return database_url
    
    # Fallback to config
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Override sqlalchemy.url with environment variable if available
    configuration = config.get_section(config.config_ini_section)
    database_url = get_database_url()
    if database_url:
        configuration['sqlalchemy.url'] = database_url

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

        # Optionally apply RLS after successful migrations
        try:
            apply_rls = os.getenv("APPLY_RLS_AFTER_MIGRATION", "false").lower() == "true"
            if apply_rls:
                # Try to import and run scripts/setup_rls.apply_rls()
                from pathlib import Path
                import asyncio
                # Ensure project root is on sys.path for 'scripts' import
                project_root = Path(__file__).resolve().parent.parent
                if str(project_root) not in sys.path:
                    sys.path.insert(0, str(project_root))
                try:
                    from scripts.setup_rls import apply_rls as _apply_rls
                    print("[alembic] Applying RLS policies after migration...")
                    asyncio.run(_apply_rls())
                    print("[alembic] RLS policies applied.")
                except Exception as e:
                    print(f"[alembic] Skipping RLS setup: {e}")
        except Exception as e:
            print(f"[alembic] Error in RLS post-migration hook: {e}")


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
