#!/usr/bin/env python3
"""
Production script to set up tenant isolation for DotMac Framework databases.
"""

import argparse
import logging
import os
import sys
from typing import Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from dotmac_shared.database.tenant_isolation import RLSPolicyManager, SchemaPerTenantManager

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class TenantIsolationSetup:
    """Set up tenant isolation for DotMac Framework databases."""

    def __init__(self, database_url: str, strategy: str = "rls"):
        self.database_url = database_url
        self.strategy = strategy
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)

    def setup_isolation_functions(self) -> None:
        """Create tenant isolation functions and triggers."""
        logger.info("Setting up tenant isolation functions...")

        try:
            RLSPolicyManager.create_tenant_policy_function(self.engine)
            logger.info("✅ Tenant isolation functions created")
        except Exception as e:
            logger.error(f"❌ Failed to create tenant isolation functions: {e}")
            raise

    def enable_rls_on_all_tables(self) -> None:
        """Enable RLS on all tenant-aware tables."""
        if self.strategy != "rls":
            logger.info("Skipping RLS setup (strategy is not RLS)")
            return

        logger.info("Enabling RLS on all tenant-aware tables...")

        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        tenant_aware_tables = []
        for table_name in tables:
            columns = [col["name"] for col in inspector.get_columns(table_name)]
            if "tenant_id" in columns:
                tenant_aware_tables.append(table_name)

        logger.info(f"Found {len(tenant_aware_tables)} tenant-aware tables")

        for table_name in tenant_aware_tables:
            try:
                RLSPolicyManager.enable_rls_on_table(self.engine, table_name)
                RLSPolicyManager.create_tenant_triggers(self.engine, table_name)
                logger.info(f"✅ Enabled RLS on {table_name}")
            except Exception as e:
                logger.error(f"❌ Failed to enable RLS on {table_name}: {e}")

    def create_tenant_indexes(self) -> None:
        """Create tenant-optimized indexes on all tables."""
        logger.info("Creating tenant-optimized indexes...")

        inspector = inspect(self.engine)
        tables = inspector.get_table_names()

        for table_name in tables:
            columns = [col["name"] for col in inspector.get_columns(table_name)]
            if "tenant_id" not in columns:
                continue

            try:
                from dotmac_shared.database.tenant_isolation import TenantIndexManager

                # Find additional columns that should be indexed with tenant_id
                additional_cols = []
                common_index_columns = ["created_at", "updated_at", "name", "email", "status", "type"]

                for col in common_index_columns:
                    if col in columns:
                        additional_cols.append(col)

                TenantIndexManager.create_tenant_indexes(self.engine, table_name, additional_cols)
                logger.info(f"✅ Created indexes for {table_name}")

            except Exception as e:
                logger.error(f"❌ Failed to create indexes for {table_name}: {e}")

    def validate_setup(self) -> bool:
        """Validate tenant isolation setup."""
        logger.info("Validating tenant isolation setup...")

        validation_passed = True

        try:
            # Check if tenant functions exist
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(
                        """
                    SELECT EXISTS (
                        SELECT 1 FROM pg_proc
                        WHERE proname = 'current_tenant_id'
                    )
                """
                    )
                ).scalar()

                if result:
                    logger.info("✅ Tenant isolation functions found")
                else:
                    logger.error("❌ Tenant isolation functions missing")
                    validation_passed = False

                # Check RLS policies if using RLS strategy
                if self.strategy == "rls":
                    rls_result = conn.execute(
                        text(
                            """
                        SELECT count(*) FROM pg_policy
                        WHERE polname LIKE 'tenant_isolation_%'
                    """
                        )
                    ).scalar()

                    if rls_result > 0:
                        logger.info(f"✅ Found {rls_result} RLS policies")
                    else:
                        logger.warning("⚠️  No RLS policies found")

                # Check tenant indexes
                index_result = conn.execute(
                    text(
                        """
                    SELECT count(*) FROM pg_indexes
                    WHERE indexname LIKE '%_tenant_%'
                """
                    )
                ).scalar()

                if index_result > 0:
                    logger.info(f"✅ Found {index_result} tenant-optimized indexes")
                else:
                    logger.warning("⚠️  No tenant-optimized indexes found")

        except Exception as e:
            logger.error(f"❌ Validation failed: {e}")
            validation_passed = False

        return validation_passed

    def setup_schema_per_tenant(self, tenant_ids: list[str]) -> None:
        """Set up schema-per-tenant isolation."""
        if self.strategy != "schema":
            logger.info("Skipping schema-per-tenant setup (strategy is not schema)")
            return

        logger.info(f"Setting up schema-per-tenant for {len(tenant_ids)} tenants...")

        schema_manager = SchemaPerTenantManager(self.engine)

        for tenant_id in tenant_ids:
            try:
                schema_manager.create_tenant_schema(tenant_id)
                logger.info(f"✅ Created schema for tenant {tenant_id}")
            except Exception as e:
                logger.error(f"❌ Failed to create schema for tenant {tenant_id}: {e}")

    def run_setup(self, tenant_ids: Optional[list[str]] = None) -> bool:
        """Run complete tenant isolation setup."""
        logger.info(f"Starting tenant isolation setup with strategy: {self.strategy}")

        try:
            # Step 1: Set up isolation functions
            self.setup_isolation_functions()

            # Step 2: Strategy-specific setup
            if self.strategy == "rls":
                self.enable_rls_on_all_tables()
            elif self.strategy == "schema" and tenant_ids:
                self.setup_schema_per_tenant(tenant_ids)

            # Step 3: Create tenant indexes
            self.create_tenant_indexes()

            # Step 4: Validate setup
            if self.validate_setup():
                logger.info("🎉 Tenant isolation setup completed successfully!")
                return True
            else:
                logger.error("❌ Tenant isolation setup validation failed")
                return False

        except Exception as e:
            logger.error(f"❌ Tenant isolation setup failed: {e}")
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Set up tenant isolation for DotMac databases")
    parser.add_argument(
        "--database-url", required=True, help="Database URL (e.g., postgresql://user:pass@host:5432/dbname)"
    )
    parser.add_argument(
        "--strategy", choices=["rls", "schema"], default="rls", help="Tenant isolation strategy (default: rls)"
    )
    parser.add_argument("--tenant-ids", nargs="*", help="List of tenant IDs (required for schema strategy)")
    parser.add_argument(
        "--validate-only", action="store_true", help="Only validate existing setup, don't create new isolation"
    )
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
        return 0

    # Validate arguments
    if args.strategy == "schema" and not args.tenant_ids:
        logger.error("Tenant IDs are required for schema-per-tenant strategy")
        return 1

    try:
        setup = TenantIsolationSetup(args.database_url, args.strategy)

        if args.validate_only:
            success = setup.validate_setup()
        else:
            success = setup.run_setup(args.tenant_ids)

        return 0 if success else 1

    except Exception as e:
        logger.error(f"Setup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
